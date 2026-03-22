from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_number: Mapped[str] = mapped_column(String(20), index=True)
    company_name: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), server_default="pending")  # pending/approved/flagged/closed
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_label: Mapped[str | None] = mapped_column(String(20), nullable=True)  # LOW/MEDIUM/HIGH
    screening_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    notes: Mapped[list["CaseNote"]] = relationship("CaseNote", back_populates="case", order_by="CaseNote.created_at", cascade="all, delete-orphan")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])  # type: ignore[name-defined]
    assigned_to: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to_id])  # type: ignore[name-defined]


class CaseNote(Base):
    __tablename__ = "case_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped["Case"] = relationship("Case", back_populates="notes")
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
