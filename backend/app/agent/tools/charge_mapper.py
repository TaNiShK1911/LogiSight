"""
Autopilot Agent Tool: Charge Mapper

Maps raw invoice charge names to the tenant's Charge Master using a three-tier strategy:
  1. Exact / alias match (existing dictionary logic)
  2. Semantic embedding similarity via Qwen text-embedding-v3
  3. Unmapped → flag for HITL-1 checkpoint

Uses qwen-plus for fuzzy match reasoning when needed.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
SEMANTIC_SIMILARITY_THRESHOLD = 0.85  # Below this → HITL-1


def _get_qwen_embeddings():
    """Return Qwen text-embedding-v3 via OpenAI-compatible endpoint."""
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
        base_url=DASHSCOPE_BASE_URL,
        model="text-embedding-v3",
    )


async def _semantic_similarity_match(
    raw_name: str,
    master_names: list[str],
) -> tuple[str | None, float]:
    """
    Compute cosine similarity between raw_name and all charge master names
    using Qwen text-embedding-v3. Returns (best_match, score) or (None, 0.0).
    """
    if not master_names or not os.environ.get("DASHSCOPE_API_KEY"):
        return None, 0.0

    try:
        import numpy as np
        embedder = _get_qwen_embeddings()

        # Embed the query + all candidates in one batch
        all_texts = [raw_name] + master_names
        vectors = await embedder.aembed_documents(all_texts)

        query_vec = np.array(vectors[0])
        candidate_vecs = np.array(vectors[1:])

        # Cosine similarity
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return None, 0.0

        scores = candidate_vecs @ query_vec / (
            np.linalg.norm(candidate_vecs, axis=1) * query_norm + 1e-10
        )
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score >= SEMANTIC_SIMILARITY_THRESHOLD:
            return master_names[best_idx], best_score
        return None, best_score

    except Exception as exc:
        logger.warning(f"[TOOL:charge_mapper] Semantic similarity failed: {exc}")
        return None, 0.0


@tool
async def tool_map_charges_to_master(tenant_id: str, line_items_json: str) -> str:
    """
    Map extracted invoice charge names to the tenant's Charge Master.

    Strategy:
    1. Exact name / alias dictionary match (fast, deterministic)
    2. Semantic embedding similarity with Qwen text-embedding-v3
    3. Unmapped → tagged for HITL-1 review

    Args:
        tenant_id: The integer company ID of the client (buyer) tenant.
        line_items_json: JSON string from tool_parse_invoice_pdf — list of charge dicts.

    Returns:
        JSON string list where each item has the original fields plus:
        {
            "mapped_charge_id": int | null,
            "mapped_charge_name": str | null,
            "mapping_tier": "DICTIONARY" | "SEMANTIC" | "UNMAPPED",
            "similarity_score": float | null,
            "requires_hitl": bool
        }
    """
    from app.database import async_session_factory
    from app.models import Charge, ChargeAlias
    from app.services.charge_mapping import resolve_raw_charge_name
    from sqlalchemy import select

    logger.info(f"[TOOL:charge_mapper] Mapping charges for tenant_id={tenant_id}")

    try:
        payload = json.loads(line_items_json)
        charges = payload if isinstance(payload, list) else payload.get("charges", [])
    except (json.JSONDecodeError, KeyError) as exc:
        return json.dumps({"error": f"Invalid line_items_json: {exc}", "mapped_items": []})

    results: list[dict[str, Any]] = []

    async with async_session_factory() as db:
        # Pre-fetch all master charge names for semantic search
        master_result = await db.execute(
            select(Charge.id, Charge.name).where(
                Charge.company_id == int(tenant_id),
                Charge.is_active == True,
            )
        )
        master_rows = master_result.fetchall()
        master_ids = [r[0] for r in master_rows]
        master_names = [r[1] for r in master_rows]

        for item in charges:
            raw_name = item.get("raw_charge_name", "")
            if not raw_name:
                continue

            # Tier 1: Dictionary / alias match
            charge_id, charge_name, tier, low_confidence, _ = await resolve_raw_charge_name(
                db, raw_name, int(tenant_id)
            )

            if charge_id:
                results.append({
                    **item,
                    "mapped_charge_id": charge_id,
                    "mapped_charge_name": charge_name,
                    "mapping_tier": tier.value,
                    "similarity_score": None,
                    "requires_hitl": False,
                })
                logger.info(f"[TOOL:charge_mapper] ✓ DICT match: '{raw_name}' → '{charge_name}'")
                continue

            # Tier 2: Semantic embedding similarity (Qwen text-embedding-v3)
            best_match_name, score = await _semantic_similarity_match(raw_name, master_names)

            if best_match_name:
                # Find the charge_id for the matched name
                idx = master_names.index(best_match_name)
                matched_id = master_ids[idx]
                results.append({
                    **item,
                    "mapped_charge_id": matched_id,
                    "mapped_charge_name": best_match_name,
                    "mapping_tier": "SEMANTIC",
                    "similarity_score": round(score, 4),
                    "requires_hitl": False,
                })
                logger.info(
                    f"[TOOL:charge_mapper] ✓ SEMANTIC match: '{raw_name}' → "
                    f"'{best_match_name}' (score={score:.3f})"
                )
            else:
                # Tier 3: Unmapped → requires HITL-1
                results.append({
                    **item,
                    "mapped_charge_id": None,
                    "mapped_charge_name": None,
                    "mapping_tier": "UNMAPPED",
                    "similarity_score": round(score, 4) if score > 0 else None,
                    "requires_hitl": True,
                })
                logger.warning(
                    f"[TOOL:charge_mapper] ✗ UNMAPPED: '{raw_name}' "
                    f"(best semantic score={score:.3f})"
                )

    unmapped_count = sum(1 for r in results if r.get("requires_hitl"))
    logger.info(
        f"[TOOL:charge_mapper] Done: {len(results)} charges, "
        f"{unmapped_count} require HITL"
    )
    return json.dumps({"mapped_items": results, "unmapped_count": unmapped_count})
