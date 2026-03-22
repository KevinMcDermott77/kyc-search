"""
Screening service — runs three checks per company:
1. UK OFSI sanctions list (live Cabinet Office API, no key needed)
2. PEP risk indicators (occupation + role keyword matching)
3. FATF high-risk country flags (officers + PSCs nationality / country of residence)
4. Sector risk from SIC codes
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.models import Officer, Psc, Company

# ── FATF lists (as of 2025 Q1) ───────────────────────────────────────────────

FATF_HIGH_RISK = {
    "iran", "north korea", "dprk", "democratic people's republic of korea",
    "myanmar", "burma",
}

FATF_GREY = {
    "algeria", "angola", "bulgaria", "burkina faso", "cameroon",
    "democratic republic of congo", "dr congo", "drc",
    "haiti", "jamaica", "kenya", "mali", "monaco",
    "mozambique", "namibia", "nigeria", "philippines",
    "senegal", "south africa", "south sudan", "syria",
    "tanzania", "venezuela", "vietnam", "yemen",
    "laos", "lao pdr",
}

# ── PEP keyword lists ────────────────────────────────────────────────────────

PEP_OCCUPATION_KEYWORDS = [
    "minister", "secretary of state", "politician", "member of parliament",
    "mp", "senator", "congressman", "governor", "ambassador", "diplomat",
    "consul", "president", "prime minister", "chancellor", "treasurer",
    "judge", "magistrate", "prosecutor", "attorney general",
    "chief executive", "chief officer",  # only of public bodies
    "official", "civil servant", "government",
]

PEP_ROLE_KEYWORDS = [
    "head of state", "head of government", "senior official",
]


# ── SIC sector risk map ──────────────────────────────────────────────────────

# risk: 'high' | 'medium' | 'low'
# Source: FATF sector risk guidance, UK NRA 2020, HMRC supervised sector guidance

SIC_RISK_MAP: dict[str, dict] = {
    # Money services / financial
    "64191": {"risk": "high", "label": "Banks", "reason": "High-value transactions, cross-border exposure"},
    "64192": {"risk": "high", "label": "Building Societies", "reason": "Mortgage fraud, savings risk"},
    "64921": {"risk": "high", "label": "Credit Granting", "reason": "Consumer credit, fraud risk"},
    "64999": {"risk": "high", "label": "Financial Services (Other)", "reason": "Broad financial exposure"},
    "66120": {"risk": "high", "label": "Security & Commodity Contracts Dealing", "reason": "Market manipulation risk"},
    "66190": {"risk": "high", "label": "Money Services / Forex", "reason": "FATF high-risk: currency exchange, remittance"},
    "66300": {"risk": "medium", "label": "Fund Management", "reason": "Investment fund layering risk"},

    # Real estate
    "68100": {"risk": "high", "label": "Buying & Selling Own Real Estate", "reason": "FATF: property frequently used for ML"},
    "68201": {"risk": "high", "label": "Letting (Own Property)", "reason": "Rental income layering risk"},
    "68209": {"risk": "high", "label": "Letting (Other Property)", "reason": "Property management ML risk"},
    "68310": {"risk": "high", "label": "Real Estate Agents", "reason": "FATF: estate agents are an HMRC supervised sector"},
    "68320": {"risk": "medium", "label": "Property Management", "reason": "Service charge / rent diversion risk"},

    # Gambling
    "92000": {"risk": "high", "label": "Gambling / Betting", "reason": "FATF high-risk: cash-intensive, layering vehicle"},
    "92110": {"risk": "high", "label": "Casinos", "reason": "FATF high-risk: significant ML risk"},
    "92120": {"risk": "high", "label": "Arcades", "reason": "Cash-intensive gambling"},

    # Precious metals / gems / luxury
    "46720": {"risk": "high", "label": "Precious Metals Wholesale", "reason": "HMRC supervised sector: high ML risk"},
    "47770": {"risk": "high", "label": "Jewellery & Watches Retail", "reason": "High-value goods, cash purchases"},
    "47710": {"risk": "medium", "label": "Clothing Retail", "reason": "Potential trade-based ML"},
    "47760": {"risk": "medium", "label": "Flowers / Luxury Retail", "reason": "Luxury goods exposure"},
    "47991": {"risk": "medium", "label": "Market Stalls", "reason": "Cash-intensive retail"},

    # Professional services
    "69101": {"risk": "high", "label": "Barristers", "reason": "HMRC supervised: legal services gateway to structures"},
    "69102": {"risk": "high", "label": "Solicitors", "reason": "HMRC supervised: conveyancing, company formation"},
    "69201": {"risk": "high", "label": "Accounting", "reason": "HMRC supervised: financial statement risk"},
    "69202": {"risk": "high", "label": "Auditing", "reason": "HMRC supervised: sign-off risk"},
    "69209": {"risk": "medium", "label": "Tax Consultancy", "reason": "Tax evasion facilitation risk"},
    "70229": {"risk": "medium", "label": "Business Consultancy", "reason": "Corporate structuring risk"},

    # Construction
    "41100": {"risk": "medium", "label": "Property Development", "reason": "Development finance, invoice fraud risk"},
    "41201": {"risk": "medium", "label": "Construction (Commercial)", "reason": "Subcontractor fraud, CIS scheme"},
    "41202": {"risk": "medium", "label": "Construction (Domestic)", "reason": "Cash payments, VAT fraud"},
    "43210": {"risk": "medium", "label": "Electrical Contractors", "reason": "Labour subcontracting fraud"},
    "43290": {"risk": "medium", "label": "Other Construction Installation", "reason": "Cash-intensive trades"},
    "43999": {"risk": "medium", "label": "Specialist Construction", "reason": "Subcontractor structures"},

    # Import/export / trade
    "46900": {"risk": "medium", "label": "Non-specialised Wholesale Trade", "reason": "Trade-based ML, mis-invoicing risk"},
    "51100": {"risk": "medium", "label": "Air Transport", "reason": "Cross-border movement of goods"},
    "52290": {"risk": "medium", "label": "Other Transport Support", "reason": "Freight forwarding risk"},

    # Crypto / fintech
    "63990": {"risk": "high", "label": "Other Information Services", "reason": "May include crypto/fintech activity"},
    "62020": {"risk": "medium", "label": "IT Consultancy", "reason": "Software-facilitated fraud risk"},
    "64110": {"risk": "high", "label": "Central Banking", "reason": "Systemic risk"},

    # Automotive
    "45111": {"risk": "high", "label": "New Car Sales", "reason": "HMRC supervised: high-value dealer sector"},
    "45112": {"risk": "high", "label": "Used Car Sales", "reason": "HMRC supervised: cash-intensive, trade fraud"},

    # Healthcare (lower risk generally)
    "86100": {"risk": "low", "label": "Hospitals", "reason": ""},
    "86210": {"risk": "low", "label": "General Medical Practice", "reason": ""},
    "86900": {"risk": "low", "label": "Other Health Activities", "reason": ""},
}

# Fallback for unknown SIC ranges
_SIC_RANGE_RISK = [
    (("01000", "03999"), "low", "Agriculture, Forestry & Fishing"),
    (("05000", "09999"), "low", "Mining & Quarrying"),
    (("10000", "33999"), "low", "Manufacturing"),
    (("35000", "39999"), "low", "Utilities & Waste"),
    (("41000", "43999"), "medium", "Construction"),
    (("45000", "47999"), "medium", "Wholesale & Retail"),
    (("49000", "53999"), "low", "Transport & Storage"),
    (("55000", "56999"), "medium", "Hospitality"),
    (("58000", "63999"), "low", "Information & Communication"),
    (("64000", "66999"), "high", "Financial & Insurance"),
    (("68000", "68999"), "high", "Real Estate"),
    (("69000", "75999"), "medium", "Professional Services"),
    (("77000", "82999"), "medium", "Admin & Support"),
    (("84000", "84999"), "low", "Public Administration"),
    (("85000", "85999"), "low", "Education"),
    (("86000", "88999"), "low", "Health & Social Work"),
    (("90000", "93999"), "medium", "Arts, Entertainment & Recreation"),
    (("94000", "96999"), "low", "Other Service Activities"),
]


def _sic_risk(sic: str) -> dict:
    """Look up the risk for a SIC code."""
    if sic in SIC_RISK_MAP:
        return SIC_RISK_MAP[sic]
    for ((lo, hi), risk, label) in _SIC_RANGE_RISK:
        if lo <= sic <= hi:
            return {"risk": risk, "label": label, "reason": ""}
    return {"risk": "low", "label": "Unknown sector", "reason": ""}


def _country_risk(country: str | None) -> str | None:
    """Return 'high' or 'elevated' if this country is FATF-listed, else None."""
    if not country:
        return None
    c = country.lower().strip()
    if c in FATF_HIGH_RISK:
        return "high"
    if c in FATF_GREY:
        return "elevated"
    return None


def _is_pep_indicator(occupation: str | None, role: str | None) -> bool:
    text = f"{occupation or ''} {role or ''}".lower()
    return any(kw in text for kw in PEP_OCCUPATION_KEYWORDS + PEP_ROLE_KEYWORDS)


# ── OFSI sanctions lookup ────────────────────────────────────────────────────

OFSI_API = "https://api.sanctions.cabinetoffice.gov.uk/v1/search"
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


async def _check_adverse_media(company_name: str, client: httpx.AsyncClient) -> dict:
    """Query GDELT for recent news articles mentioning this company."""
    try:
        resp = await client.get(
            GDELT_API,
            params={
                "query": f'"{company_name}"',
                "mode": "ArtList",
                "maxrecords": "10",
                "timespan": "1y",
                "format": "json",
            },
            timeout=8.0,
        )
        if resp.status_code != 200:
            return {"articles": [], "source": "GDELT Project", "error": f"HTTP {resp.status_code}"}
        data = resp.json()
        articles = []
        for a in data.get("articles") or []:
            articles.append({
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "domain": a.get("domain", ""),
                "date": a.get("seendate", ""),
                "sourcecountry": a.get("sourcecountry", ""),
            })
        return {"articles": articles, "source": "GDELT Project"}
    except Exception:
        return {"articles": [], "source": "GDELT Project", "error": "Unavailable"}


async def _check_sanctions(name: str, client: httpx.AsyncClient) -> list[dict]:
    """Query OFSI API for a person/entity name. Returns list of hits."""
    try:
        resp = await client.get(
            OFSI_API,
            params={"names[]": name},
            timeout=6.0,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        hits = []
        for r in data.get("results") or []:
            hits.append({
                "name": r.get("name", name),
                "regime": r.get("regime", "UK"),
                "entity_type": r.get("entityType", "Unknown"),
                "unique_id": r.get("uniqueId", ""),
            })
        return hits
    except Exception:
        return []


# ── Main screening function ──────────────────────────────────────────────────

async def screen_company(
    company: "Company",
    officers: list["Officer"],
    pscs: list["Psc"],
) -> dict:
    """
    Run all screening checks and return a structured result dict.
    """
    active_officers = [o for o in officers if not o.resigned_on]
    active_pscs = [p for p in pscs if not p.ceased_on]

    # Collect unique names to screen (individuals only)
    names_to_check: list[tuple[str, str]] = []  # (name, type)
    for o in active_officers:
        if o.name:
            names_to_check.append((o.name, "officer"))
    for p in active_pscs:
        if p.name and p.kind and "individual" in p.kind.lower():
            names_to_check.append((p.name, "psc"))
    # Also screen company name
    names_to_check.append((company.company_name, "company"))

    # Deduplicate
    seen: set[str] = set()
    unique_names = []
    for name, kind in names_to_check:
        key = name.lower().strip()
        if key not in seen:
            seen.add(key)
            unique_names.append((name, kind))

    # Run sanctions checks + adverse media concurrently
    sanctions_results: list[dict] = []
    async with httpx.AsyncClient() as client:
        sanctions_tasks = [_check_sanctions(name, client) for name, _ in unique_names]
        all_results = await asyncio.gather(
            *sanctions_tasks,
            _check_adverse_media(company.company_name, client),
        )
    all_hits = all_results[:-1]
    adverse_media_result: dict = all_results[-1]  # type: ignore[assignment]

    for (name, kind), hits in zip(unique_names, all_hits):
        sanctions_results.append({
            "name": name,
            "type": kind,
            "hits": hits,
            "match": len(hits) > 0,
        })

    # PEP indicators
    pep_findings: list[dict] = []
    for o in active_officers:
        if _is_pep_indicator(o.occupation, o.role):
            pep_findings.append({
                "name": o.name,
                "type": "officer",
                "role": o.role,
                "occupation": o.occupation,
                "nationality": o.nationality,
            })
    for p in active_pscs:
        if _is_pep_indicator(None, p.kind):
            pep_findings.append({
                "name": p.name,
                "type": "psc",
                "role": p.kind,
                "occupation": None,
                "nationality": p.nationality,
            })

    # Country risk
    country_risks: list[dict] = []
    seen_countries: set[str] = set()

    def _add_country_risk(person_name: str, person_type: str, country: str | None):
        if not country:
            return
        risk = _country_risk(country)
        if risk and country.lower() not in seen_countries:
            seen_countries.add(country.lower())
            country_risks.append({
                "country": country,
                "risk": risk,
                "list": "FATF High-Risk" if risk == "high" else "FATF Grey List",
                "flagged_for": person_name,
                "person_type": person_type,
            })

    for o in active_officers:
        _add_country_risk(o.name, "officer", o.nationality)
        _add_country_risk(o.name, "officer", o.service_address_country)
    for p in active_pscs:
        _add_country_risk(p.name, "psc", p.nationality)
        _add_country_risk(p.name, "psc", p.country_of_residence)

    # Sector risk from SIC codes
    sector_risks: list[dict] = []
    for sic in (company.sic_codes or []):
        info = _sic_risk(sic)
        sector_risks.append({
            "sic_code": sic,
            "sector_label": info["label"],
            "risk": info["risk"],
            "reason": info["reason"],
        })

    # Overall risk score (simple rules-based)
    score = 0
    sanctions_hits = [r for r in sanctions_results if r["match"]]
    if sanctions_hits:
        score += 50 * len(sanctions_hits)
    if pep_findings:
        score += 20
    high_countries = [c for c in country_risks if c["risk"] == "high"]
    elevated_countries = [c for c in country_risks if c["risk"] == "elevated"]
    score += len(high_countries) * 20
    score += len(elevated_countries) * 8
    high_sectors = [s for s in sector_risks if s["risk"] == "high"]
    medium_sectors = [s for s in sector_risks if s["risk"] == "medium"]
    score += len(high_sectors) * 10
    score += len(medium_sectors) * 4

    score = min(score, 100)

    if score >= 60:
        risk_label = "HIGH"
        risk_color = "red"
    elif score >= 30:
        risk_label = "MEDIUM"
        risk_color = "yellow"
    else:
        risk_label = "LOW"
        risk_color = "green"

    return {
        "overall_score": score,
        "overall_label": risk_label,
        "overall_color": risk_color,
        "sanctions": sanctions_results,
        "pep_indicators": pep_findings,
        "country_risks": country_risks,
        "sector_risks": sector_risks,
        "adverse_media": adverse_media_result,
        "screened_names": len(unique_names),
        "sanctions_api_source": "UK OFSI Consolidated Sanctions List (Cabinet Office)",
        "pep_source": "Occupation & role keyword analysis",
        "country_source": "FATF High-Risk & Monitored Jurisdictions (2025 Q1)",
        "sector_source": "FATF Sector Risk Guidance / UK National Risk Assessment 2020",
        "adverse_media_source": "GDELT Project news index",
    }
