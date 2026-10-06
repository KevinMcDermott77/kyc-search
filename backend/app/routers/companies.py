from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.models import Company, Filing, Officer, Psc, User
from app.schemas.company import CompanyOut, FilingOut, OfficerOut, PscOut
from app.services import ingestion
from app.services.risk_flags import compute_risk_flags

router = APIRouter(prefix="/companies", tags=["companies"])

CACHE_TTL_SECONDS = 3600  # Re-fetch from CH after 1 hour


async def _get_or_fetch_company(
    number: str,
    db: AsyncSession,
    ch,
    user_id: int,
) -> Company:
    from datetime import datetime, timezone, timedelta

    result = await db.execute(select(Company).where(Company.company_number == number))
    company = result.scalar_one_or_none()

    stale = (
        company is None
        or company.last_full_fetch is None
        or (datetime.now(timezone.utc) - company.last_full_fetch) > timedelta(seconds=CACHE_TTL_SECONDS)
    )

    if stale:
        raw = await ch.get_company(number)
        source = "mock" if hasattr(ch, "_is_mock") else "companies_house"
        company = await ingestion.ingest_company(db, raw, source=source, user_id=user_id)
        await db.commit()
        await db.refresh(company)

    return company


@router.get("/{number}", response_model=CompanyOut)
async def get_company(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)
    return company


@router.get("/{number}/officers", response_model=list[OfficerOut])
async def get_officers(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)

    result = await db.execute(select(Officer).where(Officer.company_id == company.id))
    officers = list(result.scalars().all())

    if not officers:
        raw = await ch.get_officers(number)
        officers = await ingestion.ingest_officers(db, company, raw.get("items") or [], source="companies_house", user_id=current_user.id)
        # Update risk flags with officer data
        psc_result = await db.execute(select(Psc).where(Psc.company_id == company.id))
        pscs = list(psc_result.scalars().all())
        company.risk_flags = compute_risk_flags(company, officers, pscs)
        await db.commit()

    return officers


@router.get("/{number}/pscs", response_model=list[PscOut])
async def get_pscs(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)

    result = await db.execute(select(Psc).where(Psc.company_id == company.id))
    pscs = list(result.scalars().all())

    if not pscs:
        raw = await ch.get_pscs(number)
        pscs = await ingestion.ingest_pscs(db, company, raw.get("items") or [], source="companies_house", user_id=current_user.id)
        await db.commit()

    return pscs


@router.get("/{number}/pscs/statements")
async def get_psc_statements(
    number: str,
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    """Proxy CH persons-with-significant-control-statements (all pages)."""
    return await ch.get_psc_statements(number)


@router.get("/{number}/exemptions")
async def get_exemptions(
    number: str,
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    """Proxy CH PSC exemptions."""
    return await ch.get_exemptions(number)


@router.get("/{number}/filings", response_model=list[FilingOut])
async def get_filings(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)

    result = await db.execute(select(Filing).where(Filing.company_id == company.id))
    filings = list(result.scalars().all())

    if not filings:
        raw = await ch.get_filings(number)
        filings = await ingestion.ingest_filings(db, company, raw.get("items") or [], source="companies_house", user_id=current_user.id)
        await db.commit()

    return filings


@router.get("/{number}/filings/{transaction_id}/document")
async def get_filing_document(
    number: str,
    transaction_id: str,
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    """Proxy the CH document API to download a filing PDF."""
    try:
        pdf_bytes = await ch.get_filing_document(number, transaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={transaction_id}.pdf"},
    )
