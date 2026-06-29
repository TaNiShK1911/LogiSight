"""
Autopilot Agent Tool: Anomaly Detector

Compares mapped invoice charges against the approved quote using:
  1. Rule-based checks (deterministic, fast): amount tolerance ±5%, unexpected charges, duplicates
  2. Qwen-Max chain-of-thought reasoning for borderline / ambiguous cases

Uses qwen-max for high-quality multi-step reasoning explanations.
"""

from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
AMOUNT_TOLERANCE_PCT = 5.0      # ±5% variance is acceptable
HIGH_VALUE_THRESHOLD_PCT = 15.0  # Above this → HIGH severity → HITL-2
HIGH_VALUE_THRESHOLD_ABS = 500.0  # Above $500 total disputed → HITL-2


def _get_qwen_max_llm():
    """Return Qwen-Max LLM via DashScope for anomaly reasoning."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
        base_url=DASHSCOPE_BASE_URL,
        model="qwen-max",
        temperature=0.1,
    )


def _compute_variance_pct(invoiced: float, quoted: float) -> float | None:
    """Compute percentage variance from quoted to invoiced amount."""
    if quoted == 0:
        return None  # Cannot compute percentage from zero
    return round(((invoiced - quoted) / abs(quoted)) * 100, 2)


async def _run_rule_based_checks(
    mapped_items: list[dict],
    quote_charges: list[dict],
) -> list[dict]:
    """
    Apply deterministic rule-based anomaly checks.

    Returns list of anomaly dicts with fields:
    {anomaly_type, charge_name, invoice_amount, quoted_amount,
     variance_pct, severity, reasoning_explanation}
    """
    anomalies = []
    quote_by_name: dict[str, dict] = {}
    for qc in quote_charges:
        name = (qc.get("mapped_charge_name") or qc.get("raw_charge_name") or "").lower()
        if name:
            quote_by_name[name] = qc

    seen_charges: set[str] = set()

    for item in mapped_items:
        charge_name = (
            item.get("mapped_charge_name")
            or item.get("raw_charge_name")
            or "Unknown"
        )
        charge_key = charge_name.lower()
        inv_amount = float(item.get("amount", 0))

        # Check 1: Duplicate charge detection
        if charge_key in seen_charges:
            anomalies.append({
                "anomaly_type": "DUPLICATE_CHARGE",
                "charge_name": charge_name,
                "invoice_amount": inv_amount,
                "quoted_amount": None,
                "variance_pct": None,
                "severity": "HIGH",
                "reasoning_explanation": (
                    f"Charge '{charge_name}' appears more than once on the invoice, "
                    "which may indicate a billing error or duplicate entry."
                ),
            })
            continue
        seen_charges.add(charge_key)

        # Check 2: Unexpected charge (no matching quote line)
        quote_item = quote_by_name.get(charge_key)
        if not quote_item:
            anomalies.append({
                "anomaly_type": "UNEXPECTED_CHARGE",
                "charge_name": charge_name,
                "invoice_amount": inv_amount,
                "quoted_amount": 0.0,
                "variance_pct": None,
                "severity": "BORDERLINE" if inv_amount < 100 else "HIGH",
                "reasoning_explanation": (
                    f"Charge '{charge_name}' (${inv_amount:.2f}) does not appear "
                    "in the approved quote. This may be an unauthorised surcharge."
                ),
            })
            continue

        # Check 3: Amount mismatch beyond tolerance
        quoted_amount = float(quote_item.get("amount", 0))
        variance_pct = _compute_variance_pct(inv_amount, quoted_amount)

        if variance_pct is not None and abs(variance_pct) > AMOUNT_TOLERANCE_PCT:
            variance_abs = abs(inv_amount - quoted_amount)
            severity: str
            if abs(variance_pct) > HIGH_VALUE_THRESHOLD_PCT or variance_abs > HIGH_VALUE_THRESHOLD_ABS:
                severity = "HIGH"
            elif abs(variance_pct) > 10.0:
                severity = "MEDIUM"
            else:
                severity = "BORDERLINE"

            anomalies.append({
                "anomaly_type": "AMOUNT_MISMATCH",
                "charge_name": charge_name,
                "invoice_amount": inv_amount,
                "quoted_amount": quoted_amount,
                "variance_pct": variance_pct,
                "severity": severity,
                "reasoning_explanation": (
                    f"'{charge_name}' billed at ${inv_amount:.2f} vs quoted ${quoted_amount:.2f} "
                    f"({'+' if variance_pct > 0 else ''}{variance_pct:.1f}%). "
                    f"Exceeds the {AMOUNT_TOLERANCE_PCT}% tolerance."
                ),
            })

    # Check 4: Missing charges (in quote but not in invoice)
    invoiced_keys = {
        (item.get("mapped_charge_name") or item.get("raw_charge_name") or "").lower()
        for item in mapped_items
    }
    for name_key, qc in quote_by_name.items():
        if name_key not in invoiced_keys:
            q_amount = float(qc.get("amount", 0))
            if q_amount > 0:
                anomalies.append({
                    "anomaly_type": "MISSING_CHARGE",
                    "charge_name": qc.get("mapped_charge_name") or name_key,
                    "invoice_amount": 0.0,
                    "quoted_amount": q_amount,
                    "variance_pct": -100.0,
                    "severity": "LOW",
                    "reasoning_explanation": (
                        f"Charge '{qc.get('mapped_charge_name') or name_key}' "
                        f"(${q_amount:.2f}) was in the quote but not billed — this may be acceptable."
                    ),
                })

    return anomalies


async def _enrich_borderline_with_qwen(
    borderline_anomalies: list[dict],
    context: str,
) -> list[dict]:
    """
    Use Qwen-Max to reason about borderline anomalies and upgrade/downgrade severity.
    Returns the enriched anomaly dicts with updated severity and reasoning.
    """
    if not os.environ.get("DASHSCOPE_API_KEY") or not borderline_anomalies:
        return borderline_anomalies

    try:
        llm = _get_qwen_max_llm()
        anomaly_descriptions = "\n".join(
            f"- {a['charge_name']}: invoice=${a['invoice_amount']}, "
            f"quoted={a.get('quoted_amount', 'N/A')}, "
            f"type={a['anomaly_type']}, variance={a.get('variance_pct', 'N/A')}%"
            for a in borderline_anomalies
        )
        prompt = (
            f"You are a freight audit expert. Analyse these borderline billing anomalies "
            f"for context: {context}\n\n"
            f"Anomalies:\n{anomaly_descriptions}\n\n"
            "For each anomaly, determine if it should be upgraded to HIGH or downgraded to LOW severity. "
            "Return a JSON array with the same order as input, each item having: "
            "{charge_name, final_severity, reasoning_explanation}. "
            "Return ONLY valid JSON, no markdown."
        )

        response = llm.invoke(prompt)
        enriched_raw = response.content.strip()

        # Strip markdown if present
        if enriched_raw.startswith("```"):
            lines = enriched_raw.split("\n")
            enriched_raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        enriched_list = json.loads(enriched_raw)
        for i, enriched in enumerate(enriched_list):
            if i < len(borderline_anomalies):
                borderline_anomalies[i]["severity"] = enriched.get(
                    "final_severity", borderline_anomalies[i]["severity"]
                )
                borderline_anomalies[i]["reasoning_explanation"] = enriched.get(
                    "reasoning_explanation",
                    borderline_anomalies[i]["reasoning_explanation"],
                )
        logger.info(f"[TOOL:anomaly_detector] Qwen-Max enriched {len(enriched_list)} borderline anomalies")
    except Exception as exc:
        logger.warning(f"[TOOL:anomaly_detector] Qwen-Max enrichment failed: {exc}")

    return borderline_anomalies


@tool
async def tool_detect_anomalies(
    invoice_id: str,
    mapped_items_json: str,
    quote_id: str,
) -> str:
    """
    Compare mapped invoice charges against the approved quote. Apply rule-based
    checks (amount tolerance ±5%, unexpected charges, duplicates) then use
    Qwen-Max to reason about ambiguous borderline cases.

    Args:
        invoice_id: Integer invoice ID.
        mapped_items_json: JSON output from tool_map_charges_to_master.
        quote_id: Integer quote ID to compare against.

    Returns:
        JSON string:
        {
            "anomalies": [
                {
                    "anomaly_type": "AMOUNT_MISMATCH"|"UNEXPECTED_CHARGE"|"DUPLICATE_CHARGE"|"MISSING_CHARGE",
                    "charge_name": str,
                    "invoice_amount": float,
                    "quoted_amount": float | null,
                    "variance_pct": float | null,
                    "severity": "LOW"|"MEDIUM"|"HIGH"|"BORDERLINE",
                    "reasoning_explanation": str
                }, ...
            ],
            "requires_hitl": bool,
            "total_disputed_amount": float,
            "summary": str
        }
    """
    from app.database import async_session_factory
    from app.models import Quote, QuoteCharge
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    logger.info(
        f"[TOOL:anomaly_detector] Detecting anomalies for "
        f"invoice_id={invoice_id}, quote_id={quote_id}"
    )

    try:
        payload = json.loads(mapped_items_json)
        mapped_items = payload.get("mapped_items", payload) if isinstance(payload, dict) else payload
    except (json.JSONDecodeError, KeyError) as exc:
        return json.dumps({"error": f"Invalid mapped_items_json: {exc}", "anomalies": []})

    # Fetch quote charges from DB
    async with async_session_factory() as db:
        qc_result = await db.execute(
            select(QuoteCharge).where(QuoteCharge.quote_id == int(quote_id))
        )
        quote_charges = qc_result.scalars().all()

    quote_charge_dicts = [
        {
            "mapped_charge_name": qc.mapped_charge_name,
            "raw_charge_name": qc.raw_charge_name,
            "amount": float(qc.amount),
            "basis": qc.basis,
        }
        for qc in quote_charges
    ]

    # Step 1: Rule-based checks
    anomalies = await _run_rule_based_checks(mapped_items, quote_charge_dicts)

    # Step 2: Qwen-Max reasoning for BORDERLINE cases
    borderline = [a for a in anomalies if a["severity"] == "BORDERLINE"]
    if borderline:
        context = f"invoice_id={invoice_id}, quote_id={quote_id}"
        enriched = await _enrich_borderline_with_qwen(borderline, context)
        # Update the anomalies list with enriched versions
        borderline_names = {b["charge_name"] for b in borderline}
        anomalies = [
            a for a in anomalies if a["charge_name"] not in borderline_names
        ] + enriched

    # Determine if HITL-2 is required
    high_anomalies = [a for a in anomalies if a["severity"] == "HIGH"]
    total_disputed = sum(
        abs(a["invoice_amount"] - (a["quoted_amount"] or 0))
        for a in high_anomalies
        if a.get("invoice_amount") is not None
    )
    requires_hitl = bool(high_anomalies) or total_disputed > HIGH_VALUE_THRESHOLD_ABS

    summary = (
        f"Found {len(anomalies)} anomaly(ies): "
        f"{sum(1 for a in anomalies if a['severity'] == 'HIGH')} HIGH, "
        f"{sum(1 for a in anomalies if a['severity'] == 'MEDIUM')} MEDIUM, "
        f"{sum(1 for a in anomalies if a['severity'] == 'LOW')} LOW. "
        f"Total disputed amount: ${total_disputed:.2f}. "
        f"HITL-2 {'required' if requires_hitl else 'not required'}."
    )

    logger.info(f"[TOOL:anomaly_detector] {summary}")
    return json.dumps({
        "anomalies": anomalies,
        "requires_hitl": requires_hitl,
        "total_disputed_amount": round(total_disputed, 2),
        "summary": summary,
    })
