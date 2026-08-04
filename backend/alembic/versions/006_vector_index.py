"""Add native VECTOR(1536) column and vector index to charge_embeddings

Revision ID: 006_vector_index
Revises: c4eebdb0c177
Create Date: 2026-08-04

This migration fixes the charge_embeddings table so it uses CockroachDB's
native VECTOR type instead of a plain FLOAT8[] column.

Steps:
  1. Add a new `embedding_v VECTOR(1536)` column.
  2. Backfill from the old `embedding FLOAT8[]` column if any rows exist
     (defensive — the table is empty today, but written for safety).
  3. Drop the old `embedding` column.
  4. Create a distributed vector index with `tenant_id` as a prefix column
     so similarity queries are scoped per tenant.

The vector index enables SQL-side cosine distance queries using the <=>
operator:
    SELECT id, charge_name, 1.0 - (embedding_v <=> :q::VECTOR) AS similarity
    FROM charge_embeddings
    WHERE tenant_id = :tid
    ORDER BY embedding_v <=> :q::VECTOR
    LIMIT k
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "006_vector_index"
down_revision = "c4eebdb0c177"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add native VECTOR(1536) column
    op.execute(
        "ALTER TABLE charge_embeddings "
        "ADD COLUMN IF NOT EXISTS embedding_v VECTOR(1536) NULL"
    )

    # 2. Backfill: copy FLOAT8[] data into the new VECTOR column (defensive).
    #    CockroachDB can cast an array literal to VECTOR. We convert via
    #    array_to_string to build a VECTOR literal '[x,y,z,...]'.
    #    Only runs on rows that have the old column populated.
    op.execute(
        """
        UPDATE charge_embeddings
        SET embedding_v = ('[' || array_to_string(embedding, ',') || ']')::VECTOR
        WHERE embedding IS NOT NULL
          AND embedding_v IS NULL
        """
    )

    # 3. Drop the old FLOAT8[] column
    op.execute(
        "ALTER TABLE charge_embeddings DROP COLUMN IF EXISTS embedding"
    )

    # 4. Create a distributed vector index with tenant_id prefix.
    #    The prefix column scopes vector search per tenant for performance.
    op.execute(
        "CREATE VECTOR INDEX IF NOT EXISTS ix_charge_embeddings_vector "
        "ON charge_embeddings (tenant_id, embedding_v)"
    )


def downgrade() -> None:
    # Drop the vector index
    op.execute(
        "DROP INDEX IF EXISTS ix_charge_embeddings_vector"
    )

    # Re-add the old FLOAT8[] column
    op.execute(
        "ALTER TABLE charge_embeddings "
        "ADD COLUMN IF NOT EXISTS embedding FLOAT8[] NULL"
    )

    # Backfill old column from VECTOR (reverse conversion)
    # VECTOR -> text -> strip brackets -> string_to_array -> FLOAT8[]
    op.execute(
        """
        UPDATE charge_embeddings
        SET embedding = string_to_array(
            trim(both '[]' from embedding_v::TEXT), ','
        )::FLOAT8[]
        WHERE embedding_v IS NOT NULL
          AND embedding IS NULL
        """
    )

    # Drop the VECTOR column
    op.execute(
        "ALTER TABLE charge_embeddings DROP COLUMN IF EXISTS embedding_v"
    )
