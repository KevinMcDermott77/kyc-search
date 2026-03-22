from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.models import Filing, Psc, User
from app.routers.companies import _get_or_fetch_company
from app.schemas.ownership import OwnershipTreeOut
from app.services import ingestion
from app.services.ownership_graph import build_ownership_tree, node_to_dict

router = APIRouter(prefix="/ownership", tags=["ownership"])

CH_BASE = "https://find-and-update.company-information.service.gov.uk/company"


async def _ensure_pscs_fetched(
    number: str,
    db: AsyncSession,
    ch,
    user_id: int,
    visited: set[str] | None = None,
    depth: int = 0,
) -> None:
    """
    Ensure PSCs and filing history are in the DB for a company, then
    recursively do the same for any corporate-linked companies (up to depth 4).
    Fetching filing history surfaces confirmation statements (CS01) and
    annual returns as an audit trail alongside PSC data.
    """
    if visited is None:
        visited = set()
    if number in visited or depth > 4:
        return
    visited.add(number)

    # Fetch company profile
    company = await _get_or_fetch_company(number, db, ch, user_id)

    # Fetch PSCs if not already in DB
    existing_pscs = await db.execute(
        select(Psc).where(Psc.company_id == company.id).limit(1)
    )
    if not existing_pscs.scalar_one_or_none():
        try:
            raw_pscs = await ch.get_pscs(number)
            await ingestion.ingest_pscs(
                db, company, raw_pscs.get("items") or [],
                source="companies_house", user_id=user_id,
            )
            await db.commit()
        except Exception:
            pass

    # Fetch filing history (confirmation statements CS01, annual returns AR01)
    existing_filings = await db.execute(
        select(Filing).where(Filing.company_id == company.id).limit(1)
    )
    if not existing_filings.scalar_one_or_none():
        try:
            raw_filings = await ch.get_filings(number)
            await ingestion.ingest_filings(
                db, company, raw_filings.get("items") or [],
                source="companies_house", user_id=user_id,
            )
            await db.commit()
        except Exception:
            pass

    # Recurse into any corporate PSC linked companies
    linked_result = await db.execute(
        select(Psc.linked_company_number).where(
            Psc.company_id == company.id,
            Psc.linked_company_number.is_not(None),
            Psc.ceased_on.is_(None),
        )
    )
    for (linked_number,) in linked_result.fetchall():
        if linked_number:
            await _ensure_pscs_fetched(linked_number, db, ch, user_id, visited, depth + 1)


@router.get("/{number}", response_model=OwnershipTreeOut)
async def get_ownership_tree(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    # Fetch company + PSCs + filings, recurse into linked corporate parents/subsidiaries
    await _ensure_pscs_fetched(number, db, ch, current_user.id)

    root = await build_ownership_tree(db, number)

    return OwnershipTreeOut(
        root=node_to_dict(root) if root else None,
        ch_sources={
            "profile": f"{CH_BASE}/{number}",
            "pscs": f"{CH_BASE}/{number}/persons-with-significant-control",
            "filings": f"{CH_BASE}/{number}/filing-history",
        },
    )
