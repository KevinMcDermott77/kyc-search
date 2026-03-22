from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class AddressOut(BaseModel):
    address_line_1: str | None = None
    address_line_2: str | None = None
    locality: str | None = None
    postal_code: str | None = None
    country: str | None = None


class CompanyOut(BaseModel):
    company_number: str
    company_name: str
    company_status: str | None
    company_type: str | None
    date_of_creation: date | None
    date_of_cessation: date | None
    registered_office_address: dict | None
    sic_codes: list | None
    accounts_overdue: bool
    confirmation_statement_overdue: bool
    has_charges: bool
    has_insolvency_history: bool
    jurisdiction: str | None
    risk_flags: list | None
    total_officers: int
    total_pscs: int
    cached_at: datetime

    model_config = {"from_attributes": True}


class CompanySearchResult(BaseModel):
    company_number: str
    company_name: str
    company_status: str | None = None
    company_type: str | None = None
    date_of_creation: str | None = None
    registered_office_address: dict | None = None
    snippet: str | None = None


class CompanySearchResponse(BaseModel):
    items: list[CompanySearchResult]
    total_results: int
    items_per_page: int
    start_index: int


class OfficerOut(BaseModel):
    id: int
    name: str
    role: str
    appointed_on: date | None
    resigned_on: date | None
    nationality: str | None
    occupation: str | None
    birth_month: int | None
    birth_year: int | None
    service_address_line1: str | None
    service_address_locality: str | None
    service_address_postal_code: str | None
    service_address_country: str | None

    model_config = {"from_attributes": True}


class PscOut(BaseModel):
    id: int
    name: str
    kind: str
    linked_company_number: str | None
    natures_of_control: list | None
    notified_on: date | None
    ceased_on: date | None
    birth_month: int | None = None
    birth_year: int | None = None
    nationality: str | None
    country_of_residence: str | None

    model_config = {"from_attributes": True}


class FilingOut(BaseModel):
    id: int
    transaction_id: str
    description: str | None
    category: str | None
    type: str | None
    date: date | None
    document_url: str | None

    model_config = {"from_attributes": True}
