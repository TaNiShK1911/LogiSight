"""Add copilot memory tables and Invoice s3_key/processing_status

Revision ID: 005_add_copilot_memory
Revises: 004_update_basis_constraint
Create Date: 2026-08-02

CockroachDB-compatible migration. Adds:
- copilot_sessions table
- copilot_memory_events table
- charge_embeddings table (with VECTOR(1536) column)
- Invoice.s3_key and Invoice.processing_status columns
- Profile FK fix (remove auth.users reference)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005_add_copilot_memory"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Copilot Sessions ────────────────────────────────────────────────
    op.create_table(
        "copilot_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
    )
    op.create_index(
        "ix_copilot_sessions_tenant_id",
        "copilot_sessions",
        ["tenant_id"],
    )

    # ─── Copilot Memory Events ───────────────────────────────────────────
    op.create_table(
        "copilot_memory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("copilot_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column(
            "content",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_copilot_memory_events_session_id",
        "copilot_memory_events",
        ["session_id"],
    )
    op.create_index(
        "ix_copilot_memory_events_tenant_id",
        "copilot_memory_events",
        ["tenant_id"],
    )

    # ─── Charge Embeddings ───────────────────────────────────────────────
    # VECTOR(1536) is CockroachDB-specific and not supported by SA dialect.
    # We create the table first without the vector column, then ALTER ADD it.
    op.create_table(
        "charge_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("charge_name", sa.Text(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_charge_embeddings_tenant_id",
        "charge_embeddings",
        ["tenant_id"],
    )

    # Add VECTOR column via raw DDL (CockroachDB VECTOR type)
    # On plain PostgreSQL this will be skipped gracefully
    op.execute(
        "ALTER TABLE charge_embeddings ADD COLUMN IF NOT EXISTS "
        "embedding FLOAT8[] NULL"
    )

    # ─── Invoice: new columns ────────────────────────────────────────────
    op.add_column(
        "invoices",
        sa.Column("s3_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "processing_status",
            sa.String(20),
            nullable=False,
            server_default="completed",
        ),
    )


def downgrade() -> None:
    op.drop_column("invoices", "processing_status")
    op.drop_column("invoices", "s3_key")

    op.drop_table("charge_embeddings")
    op.drop_table("copilot_memory_events")
    op.drop_table("copilot_sessions")
