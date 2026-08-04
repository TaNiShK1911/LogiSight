"""
Tier-1 charge mapping: dictionary / alias match against buyer Charge Master (LogiSight).
Falls back to SYSTEM standard charge master if no client-specific match found.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Charge, ChargeAlias, Company
from app.schemas import MappingTier

# Set up logging
logger = logging.getLogger(__name__)


def _normalize_charge_name(name: str) -> str:
    """Normalize charge name for better matching."""
    # Convert to lowercase and strip
    normalized = name.lower().strip()

    # Remove common prefixes/suffixes
    normalized = re.sub(r'^(charge for|fee for|cost of)\s+', '', normalized)
    normalized = re.sub(r'\s+(charge|fee|cost)$', '', normalized)

    # Remove special characters but keep spaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


async def _get_system_company_id(session: AsyncSession) -> int | None:
    """Get the SYSTEM company ID for standard charge master."""
    result = await session.execute(
        select(Company.id).where(Company.short_name == "SYSTEM")
    )
    system_company = result.scalar_one_or_none()
    return int(system_company) if system_company else None


async def _try_match_in_company(
    session: AsyncSession,
    raw: str,
    raw_normalized: str,
    company_id: int,
) -> tuple[int | None, str | None]:
    """
    Try to match a raw charge name against a specific company's charge master.
    Returns (charge_id, charge_name) or (None, None) if no match.
    """
    raw_l = raw.strip().lower()

    # Try direct match on charge name or short_name (exact)
    r1 = await session.execute(
        select(Charge).where(
            Charge.company_id == company_id,
            or_(
                func.lower(Charge.name) == raw_l,
                func.lower(Charge.short_name) == raw_l,
            ),
        )
    )
    direct = r1.scalar_one_or_none()
    if direct:
        return int(direct.id), direct.name

    # Try alias match (exact)
    r2 = await session.execute(
        select(Charge)
        .join(ChargeAlias, ChargeAlias.charge_id == Charge.id)
        .where(
            Charge.company_id == company_id,
            func.lower(ChargeAlias.alias) == raw_l,
        )
        .limit(1)
    )
    via_alias = r2.scalar_one_or_none()
    if via_alias:
        return int(via_alias.id), via_alias.name

    # Try fuzzy match using normalized names
    r3 = await session.execute(
        select(Charge).where(
            Charge.company_id == company_id,
            Charge.is_active == True,
        )
    )
    all_charges = list(r3.scalars().all())

    # Check if normalized raw name matches any normalized charge name
    for charge in all_charges:
        charge_normalized = _normalize_charge_name(charge.name)
        if charge_normalized == raw_normalized:
            return int(charge.id), charge.name

    return None, None


async def resolve_raw_charge_name(
    session: AsyncSession,
    raw: str,
    buyer_company_id: int,
) -> tuple[int | None, str | None, MappingTier, bool, float | None]:
    """
    Returns (mapped_charge_id, mapped_charge_name, tier, low_confidence, similarity_score).

    Matching strategy:
    1. Try exact/fuzzy match in buyer's company charge master
    2. If no match, fall back to SYSTEM standard charge master
    3. If still no match, return UNMAPPED
    """
    raw_l = raw.strip().lower()
    raw_normalized = _normalize_charge_name(raw)

    logger.info(f"[MAPPING] Attempting to map: '{raw}' (normalized: '{raw_normalized}') for company_id={buyer_company_id}")

    if not raw_l:
        logger.warning(f"[MAPPING] Empty charge name after normalization")
        return None, None, MappingTier.UNMAPPED, True, None

    # Step 1: Try to match in buyer's company charge master
    charge_id, charge_name = await _try_match_in_company(
        session, raw, raw_normalized, buyer_company_id
    )

    if charge_id:
        logger.info(f"[MAPPING] ✓ Client match found: charge_id={charge_id}, name='{charge_name}'")
        return charge_id, charge_name, MappingTier.DICTIONARY, False, None

    logger.debug(f"[MAPPING] No match in client charge master, trying SYSTEM standard charges...")

    # Step 2: Fall back to SYSTEM standard charge master
    system_company_id = await _get_system_company_id(session)

    if system_company_id:
        charge_id, charge_name = await _try_match_in_company(
            session, raw, raw_normalized, system_company_id
        )

        if charge_id:
            logger.info(f"[MAPPING] ✓ SYSTEM standard match found: charge_id={charge_id}, name='{charge_name}'")
            return charge_id, charge_name, MappingTier.DICTIONARY, False, None

    logger.info(f"[MAPPING] No dictionary match found, trying VECTOR matching...")

    # Step 3: Vector similarity matching using Bedrock Titan embeddings
    try:
        vector_result = await _try_vector_match(session, raw, buyer_company_id)
        if vector_result is not None:
            v_charge_id, v_charge_name, v_similarity = vector_result
            logger.info(
                f"[MAPPING] ✓ VECTOR match found: charge_id={v_charge_id}, "
                f"name='{v_charge_name}', similarity={v_similarity:.3f}"
            )
            low_conf = v_similarity < 0.90  # Mark as low confidence if < 0.90
            return v_charge_id, v_charge_name, MappingTier.VECTOR, low_conf, v_similarity
    except Exception as e:
        logger.warning(f"[MAPPING] Vector matching failed (non-fatal): {e}")

    logger.warning(f"[MAPPING] ✗ No match found for '{raw}' in client or SYSTEM charge master or vectors")

    # Debug: Show what aliases exist for this company
    debug_aliases = await session.execute(
        select(ChargeAlias.alias)
        .join(Charge, Charge.id == ChargeAlias.charge_id)
        .where(Charge.company_id == buyer_company_id)
        .limit(10)
    )
    existing_aliases = [a[0] for a in debug_aliases.fetchall()]
    logger.debug(f"[MAPPING] Sample client aliases: {existing_aliases}")

    return None, None, MappingTier.UNMAPPED, True, None


async def _try_vector_match(
    session: AsyncSession,
    raw_charge_name: str,
    company_id: int,
    threshold: float = 0.85,
) -> tuple[int, str, float] | None:
    """
    Try to match a charge name via cosine similarity against stored embeddings
    using CockroachDB's native distributed vector index.

    Uses the <=> operator (cosine distance) which returns values in [0, 2]:
      0 = identical vectors, 2 = opposite vectors.
    We convert to similarity = 1 - distance so existing threshold logic
    (>= 0.85 for match, < 0.90 for low confidence) works unchanged.

    Returns (charge_id, charge_name, similarity) or None.
    """
    from app.models.copilot_memory import ChargeEmbedding

    # Check if there are any embeddings for this tenant
    count_result = await session.execute(
        select(func.count(ChargeEmbedding.id)).where(
            ChargeEmbedding.tenant_id == company_id
        )
    )
    embedding_count = count_result.scalar() or 0

    if embedding_count == 0:
        logger.debug("[MAPPING] No charge embeddings found for this tenant")
        return None

    # Generate embedding for the raw charge name via Bedrock Titan
    from app.services.bedrock_client import generate_embedding
    import asyncio

    query_embedding = await asyncio.to_thread(generate_embedding, raw_charge_name)

    # Build the vector literal string for CockroachDB: '[0.1,0.2,...]'
    vec_literal = "[" + ",".join(str(f) for f in query_embedding) + "]"

    # SQL-side vector search using CockroachDB's native <=> cosine distance
    # operator.  The distributed vector index (ix_charge_embeddings_vector)
    # accelerates this query.  We compute similarity = 1 - cosine_distance
    # so that higher = more similar, consistent with the threshold logic.
    from sqlalchemy import text

    result = await session.execute(
        text("""
            SELECT charge_name,
                   1.0 - (embedding_v <=> CAST(:query_vec AS VECTOR)) AS similarity
            FROM charge_embeddings
            WHERE tenant_id = :tenant_id
              AND embedding_v IS NOT NULL
            ORDER BY embedding_v <=> CAST(:query_vec AS VECTOR)
            LIMIT 1
        """),
        {"tenant_id": company_id, "query_vec": vec_literal},
    )

    row = result.fetchone()
    if row is None:
        return None

    matched_name, similarity = row[0], float(row[1])

    if similarity < threshold:
        logger.debug(
            f"[MAPPING] Best vector match '{matched_name}' has similarity "
            f"{similarity:.3f} < threshold {threshold} — skipping"
        )
        return None

    # Look up the actual Charge record by name
    charge_result = await session.execute(
        select(Charge).where(
            Charge.company_id == company_id,
            func.lower(Charge.name) == matched_name.lower(),
            Charge.is_active == True,
        ).limit(1)
    )
    charge = charge_result.scalar_one_or_none()

    if charge is None:
        # Embedding exists but the charge was deleted or deactivated
        logger.debug(
            f"[MAPPING] Vector matched '{matched_name}' but no active Charge found"
        )
        return None

    return int(charge.id), charge.name, similarity
