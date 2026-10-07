import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.models import Company, Filing, Officer, Psc, User
from app.schemas.company import CompanyOut, FilingOut, OfficerOut, PscOut
from app.services import ingestion
from app.services.risk_flags import compute_risk_flags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])

CACHE_TTL_SECONDS = 3600  # Re-fetch from CH after 1 hour
STORED_LIST_TTL = timedelta(hours=24)  # Officers / PSCs are refetched after 24 hours
PAGINATED_SINCE = datetime.now(timezone.utc)  # see _needs_refetch


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _get_or_fetch_company(
    number: str,
    db: AsyncSession,
    ch,
    user_id: int,
) -> Company:
    result = await db.execute(select(Company).where(Company.company_number == number))
    company = result.scalar_one_or_none()

    stale = (
        company is None
        or company.last_full_fetch is None
        or (datetime.now(timezone.utc) - _as_utc(company.last_full_fetch)) > timedelta(seconds=CACHE_TTL_SECONDS)
    )

    if stale:
        raw = await ch.get_company(number)
        source = "mock" if hasattr(ch, "_is_mock") else "companies_house"
        try:
            company = await ingestion.ingest_company(db, raw, source=source, user_id=user_id)
            await db.commit()
        except IntegrityError:
            # A concurrent request (e.g. /officers and /pscs fired together) inserted
            # this company first; its row is as fresh as ours, so use it.
            logger.info("Concurrent insert of company %s, reusing stored row", number)
            await db.rollback()
            result = await db.execute(select(Company).where(Company.company_number == number))
            return result.scalar_one()
        await db.refresh(company)

    return company


@router.get("/{number}/raw")
async def get_company_raw(
    number: str,
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    """Companies House's company profile as CH sends it, always live, never stored."""
    raw = await ch.get_company(number)
    fetched_at = datetime.now(timezone.utc)
    return JSONResponse(content=raw, headers={"X-Fetched-At": fetched_at.isoformat()})


@router.get("/{number}/officers/raw")
async def get_officers_raw(
    number: str,
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    """Companies House's officer list as CH sends it (all pages merged), always live, never stored."""
    raw = await ch.get_officers(number)
    fetched_at = datetime.now(timezone.utc)
    return JSONResponse(content=raw, headers={"X-Fetched-At": fetched_at.isoformat()})


@router.get("/{number}", response_model=CompanyOut)
async def get_company(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)
    return company


def _stored_fetched_at(rows: list[Officer] | list[Psc]) -> datetime | None:
    """When the stored set was fetched: the oldest row's cached_at (rows are replaced as a set)."""
    if not rows:
        return None
    return min(_as_utc(row.cached_at) for row in rows)


def _needs_refetch(fetched_at: datetime | None, fresh: bool) -> bool:
    if fresh or fetched_at is None:
        return True
    # Rows written before this process started may come from the pre-pagination
    # client (first page only), so they are refetched once.
    if fetched_at < PAGINATED_SINCE:
        return True
    return datetime.now(timezone.utc) - fetched_at > STORED_LIST_TTL


@router.get("/{number}/officers", response_model=list[OfficerOut])
async def get_officers(
    number: str,
    response: Response,
    fresh: bool = Query(False, description="Always fetch live from Companies House"),
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)

    result = await db.execute(select(Officer).where(Officer.company_id == company.id))
    officers = list(result.scalars().all())
    fetched_at = _stored_fetched_at(officers)

    if _needs_refetch(fetched_at, fresh):
        raw = await ch.get_officers(number)
        fetched_at = datetime.now(timezone.utc)
        officers = await ingestion.ingest_officers(db, company, raw.get("items") or [], source="companies_house", user_id=current_user.id)
        # Update risk flags with officer data
        psc_result = await db.execute(select(Psc).where(Psc.company_id == company.id))
        pscs = list(psc_result.scalars().all())
        company.risk_flags = compute_risk_flags(company, officers, pscs)
        await db.commit()

    response.headers["X-Fetched-At"] = fetched_at.isoformat()
    return officers


@router.get("/{number}/pscs", response_model=list[PscOut])
async def get_pscs(
    number: str,
    response: Response,
    fresh: bool = Query(False, description="Always fetch live from Companies House"),
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)

    result = await db.execute(select(Psc).where(Psc.company_id == company.id))
    pscs = list(result.scalars().all())
    fetched_at = _stored_fetched_at(pscs)

    if _needs_refetch(fetched_at, fresh):
        raw = await ch.get_pscs(number)
        fetched_at = datetime.now(timezone.utc)
        pscs = await ingestion.ingest_pscs(db, company, raw.get("items") or [], source="companies_house", user_id=current_user.id)
        await db.commit()

    response.headers["X-Fetched-At"] = fetched_at.isoformat()
    return pscs


@router.get("/{number}/pscs/raw")
async def get_pscs_raw(
    number: str,
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    """Companies House's PSC list as CH sends it (all pages merged), always live, never stored."""
    raw = await ch.get_pscs(number)
    fetched_at = datetime.now(timezone.utc)
    return JSONResponse(content=raw, headers={"X-Fetched-At": fetched_at.isoformat()})


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
