from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Filing(Base):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    company_number: Mapped[str] = mapped_column(String(20), index=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[str | None] = mapped_column(String(100))
    date: Mapped[date | None] = mapped_column(Date)
    document_url: Mapped[str | None] = mapped_column(String(500))
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
