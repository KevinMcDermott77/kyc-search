from __future__ import annotations

from pydantic import BaseModel


class OwnershipNodeOut(BaseModel):
    company_number: str
    company_name: str
    company_status: str | None
    ch_url: str
    natures_of_control: list[str]
    percentage_label: str
    children: list[OwnershipNodeOut]

    model_config = {"from_attributes": True}


OwnershipNodeOut.model_rebuild()


class OwnershipTreeOut(BaseModel):
    root: OwnershipNodeOut | None
    ch_sources: dict[str, str] = {}
