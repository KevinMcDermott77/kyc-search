"""Add cases and case_notes tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-01

"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_number", sa.String(20), nullable=False),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_label", sa.String(20), nullable=True),
        sa.Column("screening_snapshot", sa.JSON(), nullable=True),
        sa.Column("assigned_to_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cases_company_number", "cases", ["company_number"])
    op.create_index("ix_cases_created_at", "cases", ["created_at"])

    op.create_table(
        "case_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"])


def downgrade() -> None:
    op.drop_table("case_notes")
    op.drop_table("cases")
