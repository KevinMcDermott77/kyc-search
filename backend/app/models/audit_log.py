from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))  # SEARCH, FETCH_COMPANY, FETCH_OFFICERS, etc.
    target: Mapped[str | None] = mapped_column(String(200))  # company number or search query
    source: Mapped[str] = mapped_column(String(50))  # "cache" | "companies_house" | "mock"
    endpoint: Mapped[str | None] = mapped_column(String(300))
    status_code: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
