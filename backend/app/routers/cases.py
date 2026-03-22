from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.dependencies import get_admin_user, get_current_user
from app.models import User
from app.models.case import Case, CaseNote

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateCaseRequest(BaseModel):
    company_number: str
    company_name: str
    risk_score: int | None = None
    risk_label: str | None = None
    screening_snapshot: dict | None = None


class UpdateCaseRequest(BaseModel):
    status: str | None = None
    assigned_to_id: int | None = None


class AddNoteRequest(BaseModel):
    text: str


def _case_out(case: Case) -> dict:
    return {
        "id": case.id,
        "company_number": case.company_number,
        "company_name": case.company_name,
        "status": case.status,
        "risk_score": case.risk_score,
        "risk_label": case.risk_label,
        "screening_snapshot": case.screening_snapshot,
        "assigned_to_id": case.assigned_to_id,
        "assigned_to_email": case.assigned_to.email if case.assigned_to else None,
        "created_by_id": case.created_by_id,
        "created_by_email": case.created_by.email if case.created_by else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "notes": [
            {
                "id": n.id,
                "text": n.text,
                "user_email": n.user.email if n.user else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in (case.notes or [])
        ],
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_case(
    body: CreateCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = Case(
        company_number=body.company_number,
        company_name=body.company_name,
        risk_score=body.risk_score,
        risk_label=body.risk_label,
        screening_snapshot=body.screening_snapshot,
        created_by_id=current_user.id,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    # Re-fetch with relationships
    result = await db.execute(
        select(Case)
        .where(Case.id == case.id)
        .options(
            selectinload(Case.notes).selectinload(CaseNote.user),
            selectinload(Case.created_by),
            selectinload(Case.assigned_to),
        )
    )
    case = result.scalar_one()
    return _case_out(case)


@router.get("")
async def list_cases(
    status_filter: str | None = Query(None, alias="status"),
    company_number: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Case).options(
        selectinload(Case.created_by),
        selectinload(Case.assigned_to),
    ).order_by(Case.created_at.desc())

    if status_filter:
        q = q.where(Case.status == status_filter)
    if company_number:
        q = q.where(Case.company_number == company_number)

    page_size = 20
    q = q.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    cases = result.scalars().all()

    return [
        {
            "id": c.id,
            "company_number": c.company_number,
            "company_name": c.company_name,
            "status": c.status,
            "risk_score": c.risk_score,
            "risk_label": c.risk_label,
            "assigned_to_email": c.assigned_to.email if c.assigned_to else None,
            "created_by_email": c.created_by.email if c.created_by else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cases
    ]


@router.get("/{case_id}")
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.notes).selectinload(CaseNote.user),
            selectinload(Case.created_by),
            selectinload(Case.assigned_to),
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_out(case)


@router.patch("/{case_id}")
async def update_case(
    case_id: int,
    body: UpdateCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.notes).selectinload(CaseNote.user),
            selectinload(Case.created_by),
            selectinload(Case.assigned_to),
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    valid_statuses = {"pending", "approved", "flagged", "closed"}
    if body.status is not None:
        if body.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        case.status = body.status
    if body.assigned_to_id is not None:
        case.assigned_to_id = body.assigned_to_id

    case.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(case)

    # Re-fetch to get fresh relationships
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.notes).selectinload(CaseNote.user),
            selectinload(Case.created_by),
            selectinload(Case.assigned_to),
        )
    )
    case = result.scalar_one()
    return _case_out(case)


@router.post("/{case_id}/notes", status_code=201)
async def add_note(
    case_id: int,
    body: AddNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    note = CaseNote(case_id=case_id, user_id=current_user.id, text=body.text.strip())
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return {
        "id": note.id,
        "text": note.text,
        "user_email": current_user.email,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.delete(case)
    await db.commit()
