"""
Ingest Companies House data into the local database.
Handles upserts so repeated calls stay idempotent.
"""

from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Company, Filing, Officer, Psc
from app.services.risk_flags import compute_risk_flags


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


async def ingest_company(
    db: AsyncSession,
    raw: dict,
    source: str,
    user_id: int | None = None,
) -> Company:
    number = raw["company_number"]
    stmt = select(Company).where(Company.company_number == number)
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    addr = raw.get("registered_office_address") or {}
    accounts_overdue = (raw.get("accounts") or {}).get("overdue", False)
    cs_overdue = (raw.get("confirmation_statement") or {}).get("overdue", False)

    if company is None:
        company = Company(company_number=number)
        db.add(company)

    company.company_name = raw.get("company_name", "")
    company.company_status = raw.get("company_status")
    company.company_type = raw.get("type")
    company.date_of_creation = _parse_date(raw.get("date_of_creation"))
    company.date_of_cessation = _parse_date(raw.get("date_of_cessation"))
    company.registered_office_address = addr
    company.sic_codes = raw.get("sic_codes") or []
    company.accounts_overdue = accounts_overdue
    company.confirmation_statement_overdue = cs_overdue
    company.has_charges = raw.get("has_charges", False)
    company.has_insolvency_history = raw.get("has_insolvency_history", False)
    company.jurisdiction = raw.get("jurisdiction")
    company.last_full_fetch = datetime.now(timezone.utc)

    await db.flush()

    # Compute risk flags (partial — full compute needs officers/pscs)
    company.risk_flags = compute_risk_flags(company, [], [])

    await db.flush()

    log = AuditLog(
        user_id=user_id,
        action="FETCH_COMPANY",
        target=number,
        source=source,
        endpoint=f"/company/{number}",
    )
    db.add(log)

    return company


async def ingest_officers(
    db: AsyncSession,
    company: Company,
    raw_items: list[dict],
    source: str,
    user_id: int | None = None,
) -> list[Officer]:
    # Delete existing officers for this company and re-insert
    await db.execute(delete(Officer).where(Officer.company_id == company.id))

    officers = []
    for item in raw_items:
        dob = item.get("date_of_birth") or {}
        addr = item.get("address") or {}
        links = item.get("links") or {}
        officer_link = (links.get("officer") or {}).get("appointments", "")

        off = Officer(
            company_id=company.id,
            company_number=company.company_number,
            officer_id=officer_link,
            name=item.get("name", ""),
            role=item.get("officer_role", ""),
            appointed_on=_parse_date(item.get("appointed_on")),
            resigned_on=_parse_date(item.get("resigned_on")),
            nationality=item.get("nationality"),
            occupation=item.get("occupation"),
            birth_month=dob.get("month"),
            birth_year=dob.get("year"),
            service_address_line1=addr.get("address_line_1") or addr.get("premises"),
            service_address_locality=addr.get("locality"),
            service_address_postal_code=addr.get("postal_code"),
            service_address_country=addr.get("country"),
        )
        db.add(off)
        officers.append(off)

    company.total_officers = len(officers)
    await db.flush()

    log = AuditLog(
        user_id=user_id,
        action="FETCH_OFFICERS",
        target=company.company_number,
        source=source,
        endpoint=f"/company/{company.company_number}/officers",
    )
    db.add(log)

    return officers


async def ingest_pscs(
    db: AsyncSession,
    company: Company,
    raw_items: list[dict],
    source: str,
    user_id: int | None = None,
) -> list[Psc]:
    await db.execute(delete(Psc).where(Psc.company_id == company.id))

    pscs = []
    for item in raw_items:
        dob = item.get("date_of_birth") or {}
        identification = item.get("identification") or {}

        # Determine linked company number for corporate PSCs
        linked_number: str | None = None
        kind = item.get("kind", "")
        if "corporate" in kind or "legal" in kind:
            linked_number = identification.get("registration_number")

        psc = Psc(
            company_id=company.id,
            company_number=company.company_number,
            psc_id=(item.get("links") or {}).get("self"),
            name=item.get("name", ""),
            kind=kind,
            linked_company_number=linked_number,
            natures_of_control=item.get("natures_of_control") or [],
            notified_on=_parse_date(item.get("notified_on")),
            ceased_on=_parse_date(item.get("ceased_on")),
            birth_month=dob.get("month"),
            birth_year=dob.get("year"),
            nationality=item.get("nationality"),
            country_of_residence=item.get("country_of_residence"),
        )
        db.add(psc)
        pscs.append(psc)

    company.total_pscs = len(pscs)
    await db.flush()

    log = AuditLog(
        user_id=user_id,
        action="FETCH_PSCS",
        target=company.company_number,
        source=source,
        endpoint=f"/company/{company.company_number}/persons-with-significant-control",
    )
    db.add(log)

    return pscs


async def ingest_filings(
    db: AsyncSession,
    company: Company,
    raw_items: list[dict],
    source: str,
    user_id: int | None = None,
) -> list[Filing]:
    existing_stmt = select(Filing.transaction_id).where(Filing.company_id == company.id)
    existing_result = await db.execute(existing_stmt)
    existing_ids = {row[0] for row in existing_result.fetchall()}

    filings = []
    for item in raw_items:
        tx_id = item.get("transaction_id", "")
        if tx_id in existing_ids:
            continue
        f = Filing(
            company_id=company.id,
            company_number=company.company_number,
            transaction_id=tx_id,
            description=item.get("description"),
            category=item.get("category"),
            type=item.get("type"),
            date=_parse_date(item.get("date")),
            document_url=(item.get("links") or {}).get("document_metadata"),
        )
        db.add(f)
        filings.append(f)

    log = AuditLog(
        user_id=user_id,
        action="FETCH_FILINGS",
        target=company.company_number,
        source=source,
        endpoint=f"/company/{company.company_number}/filing-history",
    )
    db.add(log)

    return filings
