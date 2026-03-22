from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_ch_client, get_current_user
from app.models import AuditLog, User
from app.schemas.company import CompanySearchResponse, CompanySearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=CompanySearchResponse)
async def search_companies(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    ch=Depends(get_ch_client),
    current_user: User = Depends(get_current_user),
):
    items_per_page = 20
    start_index = (page - 1) * items_per_page

    raw = await ch.search_companies(q, items_per_page=items_per_page, start_index=start_index)

    items = [
        CompanySearchResult(
            company_number=item.get("company_number", ""),
            company_name=item.get("title", item.get("company_name", "")),
            company_status=item.get("company_status"),
            company_type=item.get("company_type"),
            date_of_creation=item.get("date_of_creation"),
            registered_office_address=item.get("registered_office_address"),
            snippet=item.get("snippet"),
        )
        for item in (raw.get("items") or [])
    ]

    log = AuditLog(
        user_id=current_user.id,
        action="SEARCH",
        target=q,
        source="companies_house",
        endpoint="/search/companies",
        status_code=200,
    )
    db.add(log)
    await db.commit()

    return CompanySearchResponse(
        items=items,
        total_results=raw.get("total_results", len(items)),
        items_per_page=items_per_page,
        start_index=start_index,
    )
