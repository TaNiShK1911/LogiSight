"""Add copilot_memory_embeddings table and vector index

Revision ID: 007_copilot_memory_embeddings
Revises: 006_vector_index
Create Date: 2026-08-06

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "007_copilot_memory_embeddings"
down_revision = "006_vector_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create table with standard columns
    op.create_table(
        "copilot_memory_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("memory_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["memory_event_id"],
            ["copilot_memory_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["copilot_sessions.id"],
            ondelete="CASCADE",
        ),
    )
    
    # Create an index on tenant_id for basic filtering
    op.create_index(
        "ix_copilot_memory_embeddings_tenant_id",
        "copilot_memory_embeddings",
        ["tenant_id"],
        unique=False,
    )

    # 2. Add native VECTOR(1536) column
    op.execute(
        "ALTER TABLE copilot_memory_embeddings "
        "ADD COLUMN IF NOT EXISTS embedding_v VECTOR(1536) NULL"
    )

    # 3. Create a distributed vector index with tenant_id prefix
    op.execute(
        "CREATE VECTOR INDEX IF NOT EXISTS ix_copilot_memory_embeddings_vector "
        "ON copilot_memory_embeddings (tenant_id, embedding_v)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_copilot_memory_embeddings_vector")
    op.drop_index(
        "ix_copilot_memory_embeddings_tenant_id", table_name="copilot_memory_embeddings"
    )
    op.drop_table("copilot_memory_embeddings")
