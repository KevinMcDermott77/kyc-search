from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Psc(Base):
    __tablename__ = "pscs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    company_number: Mapped[str] = mapped_column(String(20), index=True)
    psc_id: Mapped[str | None] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(100))  # individual / corporate-entity / legal-person
    # For corporate PSCs — links to another company in our DB
    linked_company_number: Mapped[str | None] = mapped_column(String(20), index=True)
    natures_of_control: Mapped[list | None] = mapped_column(JSON)
    notified_on: Mapped[date | None] = mapped_column(Date)
    ceased_on: Mapped[date | None] = mapped_column(Date)
    # Privacy: birth month+year only, never day
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100))
    country_of_residence: Mapped[str | None] = mapped_column(String(100))
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
