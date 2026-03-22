from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.models import Officer, Psc, User
from app.routers.companies import _get_or_fetch_company
from app.services import ingestion
from app.services.screening import screen_company

router = APIRouter(prefix="/screening", tags=["screening"])


@router.get("/{number}")
async def get_screening(
    number: str,
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    company = await _get_or_fetch_company(number, db, ch, current_user.id)

    # Ensure officers and PSCs are in DB
    officers_result = await db.execute(select(Officer).where(Officer.company_id == company.id))
    officers = list(officers_result.scalars().all())
    if not officers:
        raw = await ch.get_officers(number)
        officers = await ingestion.ingest_officers(
            db, company, raw.get("items") or [],
            source="companies_house", user_id=current_user.id,
        )
        await db.commit()

    pscs_result = await db.execute(select(Psc).where(Psc.company_id == company.id))
    pscs = list(pscs_result.scalars().all())
    if not pscs:
        raw = await ch.get_pscs(number)
        pscs = await ingestion.ingest_pscs(
            db, company, raw.get("items") or [],
            source="companies_house", user_id=current_user.id,
        )
        await db.commit()

    result = await screen_company(company, officers, pscs)
    return result
