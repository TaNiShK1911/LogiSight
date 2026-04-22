"""Initial LogiSight schema: companies through tracking_events.

Revision ID: 001
Revises:
Create Date: 2026-04-18

Matches SQLAlchemy models in app/models.py and frontend Supabase core tables.
Requires existing Supabase auth schema (profiles.id -> auth.users.id).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("type IN ('client', 'forwarder')", name="ck_companies_type"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_id", sa.BigInteger(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("name", sa.Text(), server_default="", nullable=False),
        sa.Column("role", sa.Text(), server_default="client", nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('super_admin', 'client', 'forwarder')",
            name="ck_profiles_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_profiles_company_id", "profiles", ["company_id"], unique=False)

    op.create_table(
        "countries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("short_name"),
    )

    op.create_table(
        "currencies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("short_name"),
    )

    op.create_table(
        "airports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("iata_code", sa.Text(), nullable=False),
        sa.Column("country_id", sa.BigInteger(), sa.ForeignKey("countries.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iata_code"),
    )

    op.create_table(
        "charges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", name="uq_charges_company_id_name"),
        sa.UniqueConstraint("company_id", "short_name", name="uq_charges_company_id_short_name"),
    )
    op.create_index("idx_charges_company_id", "charges", ["company_id"], unique=False)

    op.create_table(
        "charge_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "charge_id",
            sa.BigInteger(),
            sa.ForeignKey("charges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("charge_id", "alias", name="uq_charge_aliases_charge_id_alias"),
    )
    op.create_index("idx_charge_aliases_charge_id", "charge_aliases", ["charge_id"], unique=False)

    op.create_table(
        "quotes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("forwarder_id", sa.BigInteger(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("buyer_id", sa.BigInteger(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("quote_ref", sa.Text(), nullable=False),
        sa.Column("origin_airport_id", sa.BigInteger(), sa.ForeignKey("airports.id"), nullable=True),
        sa.Column(
            "destination_airport_id",
            sa.BigInteger(),
            sa.ForeignKey("airports.id"),
            nullable=True,
        ),
        sa.Column("tracking_number", sa.Text(), nullable=False),
        sa.Column("gross_weight", sa.Numeric(), server_default="0", nullable=False),
        sa.Column("volumetric_weight", sa.Numeric(), server_default="0", nullable=False),
        sa.Column("chargeable_weight", sa.Numeric(), server_default="0", nullable=False),
        sa.Column("currency_id", sa.BigInteger(), sa.ForeignKey("currencies.id"), nullable=True),
        sa.Column("status", sa.Text(), server_default="SUBMITTED", nullable=False),
        sa.Column("rejection_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('SUBMITTED', 'ACCEPTED', 'REJECTED')",
            name="ck_quotes_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_ref"),
    )
    op.create_index("idx_quotes_forwarder_id", "quotes", ["forwarder_id"], unique=False)
    op.create_index("idx_quotes_buyer_id", "quotes", ["buyer_id"], unique=False)

    op.create_table(
        "quote_charges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "quote_id",
            sa.BigInteger(),
            sa.ForeignKey("quotes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_charge_name", sa.Text(), nullable=False),
        sa.Column("mapped_charge_id", sa.BigInteger(), sa.ForeignKey("charges.id"), nullable=True),
        sa.Column("mapped_charge_name", sa.Text(), nullable=True),
        sa.Column("similarity_score", sa.Numeric(), nullable=True),
        sa.Column("mapping_tier", sa.Text(), server_default="UNMAPPED", nullable=False),
        sa.Column("low_confidence", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rate", sa.Numeric(), server_default="0", nullable=False),
        sa.Column("basis", sa.Text(), server_default="Per Shipment", nullable=False),
        sa.Column("qty", sa.Numeric(), server_default="1", nullable=False),
        sa.Column("amount", sa.Numeric(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "mapping_tier IN ('DICTIONARY','VECTOR','LLM','HUMAN','UNMAPPED')",
            name="ck_quote_charges_mapping_tier",
        ),
        sa.CheckConstraint(
            "basis IN ('Per KG','Per Shipment','Per CBM')",
            name="ck_quote_charges_basis",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_quote_charges_quote_id", "quote_charges", ["quote_id"], unique=False)

    op.create_table(
        "invoices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("quote_id", sa.BigInteger(), sa.ForeignKey("quotes.id"), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("file_path", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_invoices_quote_id", "invoices", ["quote_id"], unique=False)

    op.create_table(
        "invoice_charges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_charge_name", sa.Text(), nullable=False),
        sa.Column("mapped_charge_id", sa.BigInteger(), sa.ForeignKey("charges.id"), nullable=True),
        sa.Column("mapped_charge_name", sa.Text(), nullable=True),
        sa.Column("similarity_score", sa.Numeric(), nullable=True),
        sa.Column("mapping_tier", sa.Text(), server_default="UNMAPPED", nullable=False),
        sa.Column("low_confidence", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rate", sa.Numeric(), server_default="0", nullable=False),
        sa.Column("basis", sa.Text(), server_default="Per Shipment", nullable=False),
        sa.Column("qty", sa.Numeric(), server_default="1", nullable=False),
        sa.Column("amount", sa.Numeric(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "mapping_tier IN ('DICTIONARY','VECTOR','LLM','HUMAN','UNMAPPED')",
            name="ck_invoice_charges_mapping_tier",
        ),
        sa.CheckConstraint(
            "basis IN ('Per KG','Per Shipment','Per CBM')",
            name="ck_invoice_charges_basis",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_invoice_charges_invoice_id", "invoice_charges", ["invoice_id"], unique=False)

    op.create_table(
        "anomalies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("invoice_charge_id", sa.BigInteger(), sa.ForeignKey("invoice_charges.id"), nullable=True),
        sa.Column("flag_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("variance", sa.Numeric(), nullable=True),
        sa.CheckConstraint(
            "flag_type IN ("
            "'AMOUNT_MISMATCH','RATE_MISMATCH','BASIS_MISMATCH',"
            "'UNEXPECTED_CHARGE','MISSING_CHARGE','DUPLICATE_INVOICE')",
            name="ck_anomalies_flag_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_anomalies_invoice_id", "anomalies", ["invoice_id"], unique=False)

    op.create_table(
        "tracking_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "quote_id",
            sa.BigInteger(),
            sa.ForeignKey("quotes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("location", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.Text(), server_default="", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tracking_events_quote_id", "tracking_events", ["quote_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_tracking_events_quote_id", table_name="tracking_events")
    op.drop_table("tracking_events")
    op.drop_index("idx_anomalies_invoice_id", table_name="anomalies")
    op.drop_table("anomalies")
    op.drop_index("idx_invoice_charges_invoice_id", table_name="invoice_charges")
    op.drop_table("invoice_charges")
    op.drop_index("idx_invoices_quote_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("idx_quote_charges_quote_id", table_name="quote_charges")
    op.drop_table("quote_charges")
    op.drop_index("idx_quotes_buyer_id", table_name="quotes")
    op.drop_index("idx_quotes_forwarder_id", table_name="quotes")
    op.drop_table("quotes")
    op.drop_index("idx_charge_aliases_charge_id", table_name="charge_aliases")
    op.drop_table("charge_aliases")
    op.drop_index("idx_charges_company_id", table_name="charges")
    op.drop_table("charges")
    op.drop_table("airports")
    op.drop_table("currencies")
    op.drop_table("countries")
    op.drop_index("idx_profiles_company_id", table_name="profiles")
    op.drop_table("profiles")
    op.drop_table("companies")
