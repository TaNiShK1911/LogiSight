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
    Try to match a charge name via cosine similarity against stored embeddings.
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

    # Generate embedding for the raw charge name
    from app.services.bedrock_client import generate_embedding
    import asyncio
    import math

    query_embedding = await asyncio.to_thread(generate_embedding, raw_charge_name)

    # Fetch all embeddings for this tenant (fine for reasonable counts < 10K)
    from sqlalchemy import text

    rows = await session.execute(
        text("""
            SELECT id, charge_name, embedding
            FROM charge_embeddings
            WHERE tenant_id = :tenant_id AND embedding IS NOT NULL
        """),
        {"tenant_id": company_id},
    )

    best_match: tuple[str, float] | None = None
    for row in rows:
        stored_name = row[1]
        stored_embedding = row[2]

        if not stored_embedding or len(stored_embedding) != len(query_embedding):
            continue

        # Cosine similarity
        dot = sum(a * b for a, b in zip(query_embedding, stored_embedding))
        norm_a = math.sqrt(sum(a * a for a in query_embedding))
        norm_b = math.sqrt(sum(b * b for b in stored_embedding))

        if norm_a == 0 or norm_b == 0:
            continue

        similarity = dot / (norm_a * norm_b)

        if similarity >= threshold:
            if best_match is None or similarity > best_match[1]:
                best_match = (stored_name, similarity)

    if best_match is None:
        return None

    # Look up the charge by name
    matched_name, matched_similarity = best_match
    charge_result = await session.execute(
        select(Charge).where(
            Charge.company_id == company_id,
            func.lower(Charge.name) == matched_name.lower(),
            Charge.is_active == True,
        ).limit(1)
    )
    charge = charge_result.scalar_one_or_none()

    if charge is None:
        return None

    return int(charge.id), charge.name, matched_similarity
