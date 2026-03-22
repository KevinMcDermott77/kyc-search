"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Companies
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_number", sa.String(20), nullable=False, unique=True),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("company_status", sa.String(50), nullable=True),
        sa.Column("company_type", sa.String(100), nullable=True),
        sa.Column("date_of_creation", sa.Date(), nullable=True),
        sa.Column("date_of_cessation", sa.Date(), nullable=True),
        sa.Column("registered_office_address", sa.JSON(), nullable=True),
        sa.Column("sic_codes", sa.JSON(), nullable=True),
        sa.Column("accounts_overdue", sa.Boolean(), server_default="false"),
        sa.Column("confirmation_statement_overdue", sa.Boolean(), server_default="false"),
        sa.Column("has_charges", sa.Boolean(), server_default="false"),
        sa.Column("has_insolvency_history", sa.Boolean(), server_default="false"),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("last_full_fetch", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("total_officers", sa.Integer(), server_default="0"),
        sa.Column("total_pscs", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_companies_company_number", "companies", ["company_number"])

    # Officers
    op.create_table(
        "officers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True),
        sa.Column("company_number", sa.String(20), index=True),
        sa.Column("officer_id", sa.String(200), nullable=True),
        sa.Column("name", sa.String(500)),
        sa.Column("role", sa.String(100)),
        sa.Column("appointed_on", sa.Date(), nullable=True),
        sa.Column("resigned_on", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("occupation", sa.String(200), nullable=True),
        sa.Column("birth_month", sa.Integer(), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("service_address_line1", sa.String(300), nullable=True),
        sa.Column("service_address_locality", sa.String(200), nullable=True),
        sa.Column("service_address_postal_code", sa.String(20), nullable=True),
        sa.Column("service_address_country", sa.String(100), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # PSCs
    op.create_table(
        "pscs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True),
        sa.Column("company_number", sa.String(20), index=True),
        sa.Column("psc_id", sa.String(200), nullable=True),
        sa.Column("name", sa.String(500)),
        sa.Column("kind", sa.String(100)),
        sa.Column("linked_company_number", sa.String(20), nullable=True, index=True),
        sa.Column("natures_of_control", sa.JSON(), nullable=True),
        sa.Column("notified_on", sa.Date(), nullable=True),
        sa.Column("ceased_on", sa.Date(), nullable=True),
        sa.Column("birth_month", sa.Integer(), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("country_of_residence", sa.String(100), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Filings
    op.create_table(
        "filings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True),
        sa.Column("company_number", sa.String(20), index=True),
        sa.Column("transaction_id", sa.String(100), unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("type", sa.String(100), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Audit logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100)),
        sa.Column("target", sa.String(200), nullable=True),
        sa.Column("source", sa.String(50)),
        sa.Column("endpoint", sa.String(300), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("filings")
    op.drop_table("pscs")
    op.drop_table("officers")
    op.drop_table("companies")
    op.drop_table("users")
