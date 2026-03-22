from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Officer(Base):
    __tablename__ = "officers"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    company_number: Mapped[str] = mapped_column(String(20), index=True)
    officer_id: Mapped[str | None] = mapped_column(String(200))  # CH internal ID
    name: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(100))  # director, secretary, etc.
    appointed_on: Mapped[date | None] = mapped_column(Date)
    resigned_on: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(100))
    occupation: Mapped[str | None] = mapped_column(String(200))
    # Privacy: birth month+year only, never day; service address only, never home
    birth_month: Mapped[int | None] = mapped_column(Integer)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    service_address_line1: Mapped[str | None] = mapped_column(String(300))
    service_address_locality: Mapped[str | None] = mapped_column(String(200))
    service_address_postal_code: Mapped[str | None] = mapped_column(String(20))
    service_address_country: Mapped[str | None] = mapped_column(String(100))
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
