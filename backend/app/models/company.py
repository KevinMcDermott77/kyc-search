from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    company_status: Mapped[str | None] = mapped_column(String(50))
    company_type: Mapped[str | None] = mapped_column(String(100))
    date_of_creation: Mapped[date | None] = mapped_column(Date)
    date_of_cessation: Mapped[date | None] = mapped_column(Date)
    registered_office_address: Mapped[dict | None] = mapped_column(JSON)
    sic_codes: Mapped[list | None] = mapped_column(JSON)
    accounts_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_statement_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    has_charges: Mapped[bool] = mapped_column(Boolean, default=False)
    has_insolvency_history: Mapped[bool] = mapped_column(Boolean, default=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    last_full_fetch: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # Risk summary stored as JSON for quick access
    risk_flags: Mapped[list | None] = mapped_column(JSON)
    # Total officers / PSCs cached to avoid extra queries
    total_officers: Mapped[int] = mapped_column(Integer, default=0)
    total_pscs: Mapped[int] = mapped_column(Integer, default=0)
