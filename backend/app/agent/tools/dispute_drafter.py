"""
Autopilot Agent Tool: Dispute Letter Drafter (Qwen-Max)

Generates a formal, professional freight dispute letter using Qwen-Max.
The letter is stored in the database with status=DRAFT and awaits HITL-3 approval
before being dispatched to the forwarder.
"""

from __future__ import annotations

import json
import logging
import os

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

DISPUTE_LETTER_TEMPLATE = """
You are a professional freight audit specialist writing on behalf of a client.
Write a formal dispute letter with the following details:

Client (sender): {client_name}
Freight Forwarder (recipient): {forwarder_name}
Invoice Number: {invoice_number}
Original Quote Reference: {quote_ref}

The following billing discrepancies were identified:

{anomaly_details}

Requirements for the letter:
1. Use professional, factual business language — no emotional or aggressive tone
2. Reference the original quote number {quote_ref} specifically
3. Request written explanation or correction for each discrepancy listed
4. Set a clear response deadline of 5 business days from the date of this letter
5. Address it to the Accounts Receivable / Finance department
6. State that unresolved disputes may delay payment processing
7. Offer to schedule a call to discuss if needed
8. Keep the letter under 400 words

Write ONLY the letter body text (no metadata, no JSON). Start with "Dear Accounts Receivable,"
"""


def _get_qwen_max_llm():
    """Return Qwen-Max LLM for high-quality long-form writing."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
        base_url=DASHSCOPE_BASE_URL,
        model="qwen-max",
        temperature=0.3,  # Slightly higher for more natural prose
        max_tokens=1000,
    )


@tool
async def tool_draft_dispute_letter(
    invoice_id: str,
    anomalies_json: str,
) -> str:
    """
    Generate a formal dispute letter for the detected invoice anomalies using Qwen-Max.
    The letter is stored in the database with status=DRAFT and returned as plain text.

    Args:
        invoice_id: Integer invoice ID.
        anomalies_json: JSON string output from tool_detect_anomalies
                        (the "anomalies" list, or the full dict).

    Returns:
        JSON string:
        {
            "dispute_letter_id": int,
            "letter_text": str,
            "status": "DRAFT"
        }
        or {"error": "..."} on failure.
    """
    from app.database import async_session_factory
    from app.models import Invoice, Company, DisputeLetter
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    import asyncio

    logger.info(f"[TOOL:dispute_drafter] Drafting letter for invoice_id={invoice_id}")

    # Parse anomalies
    try:
        payload = json.loads(anomalies_json)
        anomalies = payload.get("anomalies", payload) if isinstance(payload, dict) else payload
    except (json.JSONDecodeError, KeyError) as exc:
        return json.dumps({"error": f"Invalid anomalies_json: {exc}"})

    if not anomalies:
        return json.dumps({"error": "No anomalies provided — nothing to dispute"})

    # Fetch invoice + quote + company details
    async with async_session_factory() as db:
        inv_result = await db.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.quote).selectinload("forwarder"),
                selectinload(Invoice.quote).selectinload("buyer"),
            )
            .where(Invoice.id == int(invoice_id))
        )
        invoice = inv_result.scalar_one_or_none()

        if not invoice:
            return json.dumps({"error": f"Invoice {invoice_id} not found"})

    quote = invoice.quote
    client_name = quote.buyer.name if quote and quote.buyer else "Client"
    forwarder_name = quote.forwarder.name if quote and quote.forwarder else "Forwarder"
    invoice_number = invoice.invoice_number
    quote_ref = quote.quote_ref if quote else "N/A"

    # Build anomaly details string
    anomaly_lines = []
    for i, a in enumerate(anomalies, 1):
        if a.get("severity") in ("HIGH", "MEDIUM"):
            if a["anomaly_type"] == "AMOUNT_MISMATCH":
                anomaly_lines.append(
                    f"{i}. {a['charge_name']}: Invoiced ${a['invoice_amount']:.2f} "
                    f"vs Quoted ${a.get('quoted_amount', 0):.2f} "
                    f"({'+' if (a.get('variance_pct') or 0) > 0 else ''}"
                    f"{a.get('variance_pct', 0):.1f}% variance)"
                )
            elif a["anomaly_type"] == "UNEXPECTED_CHARGE":
                anomaly_lines.append(
                    f"{i}. {a['charge_name']}: Charged ${a['invoice_amount']:.2f} "
                    f"— this charge does not appear in the approved quote"
                )
            elif a["anomaly_type"] == "DUPLICATE_CHARGE":
                anomaly_lines.append(
                    f"{i}. {a['charge_name']}: Appears to be duplicated on the invoice"
                )

    if not anomaly_lines:
        anomaly_lines = [
            f"{i+1}. {a['charge_name']}: {a.get('reasoning_explanation', a['anomaly_type'])}"
            for i, a in enumerate(anomalies[:5])
        ]

    anomaly_details = "\n".join(anomaly_lines)

    # Build prompt and invoke Qwen-Max
    try:
        if not os.environ.get("DASHSCOPE_API_KEY"):
            # Fallback: generate a template letter without LLM
            letter_text = (
                f"Dear Accounts Receivable,\n\n"
                f"We are writing to formally dispute invoice {invoice_number} from {forwarder_name}, "
                f"dated against quote {quote_ref}.\n\n"
                f"The following discrepancies have been identified:\n\n"
                f"{anomaly_details}\n\n"
                f"Please provide written clarification or correction within 5 business days. "
                f"Payment will be withheld for the disputed amounts pending resolution.\n\n"
                f"Sincerely,\n{client_name} Finance Department"
            )
        else:
            llm = _get_qwen_max_llm()
            prompt = DISPUTE_LETTER_TEMPLATE.format(
                client_name=client_name,
                forwarder_name=forwarder_name,
                invoice_number=invoice_number,
                quote_ref=quote_ref,
                anomaly_details=anomaly_details,
            )
            response = await asyncio.to_thread(llm.invoke, prompt)
            letter_text = response.content.strip()

        logger.info(
            f"[TOOL:dispute_drafter] Letter drafted: "
            f"{len(letter_text)} chars for invoice_id={invoice_id}"
        )

    except Exception as exc:
        logger.exception(f"[TOOL:dispute_drafter] LLM call failed: {exc}")
        return json.dumps({"error": f"Letter generation failed: {exc}"})

    # Store letter draft in DB
    async with async_session_factory() as db:
        letter = DisputeLetter(
            invoice_id=int(invoice_id),
            letter_text=letter_text,
            status="DRAFT",
        )
        db.add(letter)
        await db.commit()
        await db.refresh(letter)
        letter_id = letter.id

    logger.info(
        f"[TOOL:dispute_drafter] Stored dispute letter id={letter_id} (DRAFT)"
    )
    return json.dumps({
        "dispute_letter_id": letter_id,
        "letter_text": letter_text,
        "status": "DRAFT",
    })
