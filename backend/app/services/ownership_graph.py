"""
Recursively build an ownership tree from PSC data.
Starts from a given company and traverses corporate PSCs upward
and linked companies downward.

Uses visited set to prevent cycles (max depth 5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Psc

MAX_DEPTH = 5
CH_BASE = "https://find-and-update.company-information.service.gov.uk/company"


@dataclass
class OwnershipNode:
    company_number: str
    company_name: str
    company_status: str | None
    ch_url: str = ""
    natures_of_control: list[str] = field(default_factory=list)
    percentage_label: str = ""
    children: list["OwnershipNode"] = field(default_factory=list)


def _control_to_label(natures: list[str]) -> str:
    for n in natures:
        if "75-to-100" in n:
            return "75–100%"
        if "50-to-75" in n:
            return "50–75%"
        if "25-to-50" in n:
            return "25–50%"
    if natures:
        return "Significant control"
    return ""


async def _get_company(db: AsyncSession, number: str) -> Company | None:
    result = await db.execute(select(Company).where(Company.company_number == number))
    return result.scalar_one_or_none()


async def _get_active_pscs(db: AsyncSession, company_number: str) -> list[Psc]:
    result = await db.execute(
        select(Psc).where(
            Psc.company_number == company_number,
            Psc.ceased_on.is_(None),
        )
    )
    return list(result.scalars().all())


async def _get_subsidiaries(db: AsyncSession, parent_number: str) -> list[Psc]:
    """Find PSC records in other companies that name this company as corporate owner."""
    result = await db.execute(
        select(Psc).where(
            Psc.linked_company_number == parent_number,
            Psc.ceased_on.is_(None),
        )
    )
    return list(result.scalars().all())


async def build_ownership_tree(
    db: AsyncSession,
    root_number: str,
    depth: int = 0,
    visited: set[str] | None = None,
) -> OwnershipNode | None:
    if visited is None:
        visited = set()

    if depth > MAX_DEPTH or root_number in visited:
        return None

    visited.add(root_number)

    company = await _get_company(db, root_number)
    if company is None:
        return OwnershipNode(
            company_number=root_number,
            company_name=f"Unknown ({root_number})",
            company_status=None,
            ch_url=f"{CH_BASE}/{root_number}",
        )

    node = OwnershipNode(
        company_number=company.company_number,
        company_name=company.company_name,
        company_status=company.company_status,
        ch_url=f"{CH_BASE}/{company.company_number}",
    )

    # Corporate PSCs of this company = parent owners
    pscs = await _get_active_pscs(db, root_number)
    for psc in pscs:
        if psc.linked_company_number and psc.linked_company_number not in visited:
            child = await build_ownership_tree(db, psc.linked_company_number, depth + 1, visited)
            if child:
                child.natures_of_control = psc.natures_of_control or []
                child.percentage_label = _control_to_label(psc.natures_of_control or [])
                node.children.append(child)

    # Companies where this company is the named corporate PSC = subsidiaries
    subsidiaries = await _get_subsidiaries(db, root_number)
    for sub_psc in subsidiaries:
        sub_number = sub_psc.company_number
        if sub_number not in visited:
            sub_node = await build_ownership_tree(db, sub_number, depth + 1, visited)
            if sub_node:
                sub_node.natures_of_control = sub_psc.natures_of_control or []
                sub_node.percentage_label = _control_to_label(sub_psc.natures_of_control or [])
                node.children.append(sub_node)

    return node


def node_to_dict(node: OwnershipNode) -> dict:
    return {
        "company_number": node.company_number,
        "company_name": node.company_name,
        "company_status": node.company_status,
        "ch_url": node.ch_url,
        "natures_of_control": node.natures_of_control,
        "percentage_label": node.percentage_label,
        "children": [node_to_dict(c) for c in node.children],
    }
