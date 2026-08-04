"""
Backfill charge_embeddings with Bedrock Titan Embeddings.

Iterates over Charge and ChargeAlias rows for every tenant (company),
generates a 1536-dim embedding via Bedrock Titan, and inserts into the
charge_embeddings table using the native VECTOR(1536) column.

Idempotent: skips charges that already have an embedding row
(matched on tenant_id + charge_name).

Usage:
    cd backend
    python -m scripts.backfill_charge_embeddings
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add parent directory to path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Charge, ChargeAlias, Company


def _get_database_url() -> str:
    """Resolve DATABASE_URL for async connection."""
    url = os.environ.get("COCKROACHDB_URL", "") or os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: COCKROACHDB_URL or DATABASE_URL environment variable not set")
        sys.exit(1)

    if url.startswith("cockroachdb://"):
        url = url.replace("cockroachdb://", "cockroachdb+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "cockroachdb+asyncpg://", 1)

    # asyncpg doesn't support sslmode in query string
    if "sslmode=verify-full" in url:
        url = url.replace("?sslmode=verify-full", "")
        url = url.replace("&sslmode=verify-full", "")

    return url


async def backfill_embeddings():
    """Generate and insert embeddings for all charges and aliases."""
    from dotenv import load_dotenv
    load_dotenv()

    from app.services.bedrock_client import generate_embedding

    db_url = _get_database_url()
    connect_args = (
        {"ssl": "require"}
        if "cockroachlabs.cloud" in os.environ.get("COCKROACHDB_URL", "")
        else {}
    )
    engine = create_async_engine(db_url, echo=False, connect_args=connect_args)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_inserted = 0
    total_skipped = 0

    async with async_session() as session:
        # Get all companies (tenants)
        companies_result = await session.execute(select(Company))
        companies = list(companies_result.scalars().all())
        print(f"Found {len(companies)} companies to process")

        for company in companies:
            company_id = int(company.id)
            print(f"\n--- Processing company: {company.name} (id={company_id}) ---")

            # Get all active charges for this company
            charges_result = await session.execute(
                select(Charge).where(
                    Charge.company_id == company_id,
                    Charge.is_active == True,
                )
            )
            charges = list(charges_result.scalars().all())

            # Collect all names to embed: charge names + alias names
            names_to_embed: list[tuple[str, str]] = []  # (name, source)

            for charge in charges:
                names_to_embed.append((charge.name, "charge_master"))

                # Get aliases for this charge
                aliases_result = await session.execute(
                    select(ChargeAlias).where(ChargeAlias.charge_id == charge.id)
                )
                aliases = list(aliases_result.scalars().all())
                for alias in aliases:
                    names_to_embed.append((alias.alias, "charge_alias"))

            print(f"  Found {len(names_to_embed)} names/aliases to embed")

            for charge_name, source in names_to_embed:
                # Idempotency check: skip if embedding already exists
                existing = await session.execute(
                    text("""
                        SELECT 1 FROM charge_embeddings
                        WHERE tenant_id = :tenant_id
                          AND charge_name = :charge_name
                        LIMIT 1
                    """),
                    {"tenant_id": company_id, "charge_name": charge_name},
                )
                if existing.fetchone() is not None:
                    total_skipped += 1
                    continue

                # Generate embedding via Bedrock Titan
                try:
                    embedding = generate_embedding(charge_name)
                except Exception as e:
                    print(f"  [!] Failed to embed '{charge_name}': {e}")
                    continue

                # Build VECTOR literal for CockroachDB
                vec_literal = "[" + ",".join(str(f) for f in embedding) + "]"

                # Insert into charge_embeddings with VECTOR column
                # Use CAST() instead of ::VECTOR to avoid asyncpg $N parameter conflict
                await session.execute(
                    text("""
                        INSERT INTO charge_embeddings
                            (id, tenant_id, charge_name, source, embedding_v, created_at)
                        VALUES
                            (:id, :tenant_id, :charge_name, :source,
                             CAST(:embedding_v AS VECTOR), now())
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": company_id,
                        "charge_name": charge_name,
                        "source": source,
                        "embedding_v": vec_literal,
                    },
                )
                total_inserted += 1
                print(f"  [+] Embedded: '{charge_name}' ({source})")

        await session.commit()

    print(f"\n{'=' * 50}")
    print(f"Backfill complete!")
    print(f"  Inserted: {total_inserted}")
    print(f"  Skipped (already existed): {total_skipped}")


if __name__ == "__main__":
    asyncio.run(backfill_embeddings())
