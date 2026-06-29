"""
Autopilot Agent Tool: PDF Parser (Qwen-VL)

Downloads the invoice PDF from OSS and uses Qwen-VL to extract structured
charge line items. Returns a JSON string for consumption by subsequent agent steps.
"""

from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def tool_parse_invoice_pdf(invoice_id: str) -> str:
    """
    Download the invoice PDF from storage and use Qwen-VL to extract all
    charge line items as structured JSON.

    Args:
        invoice_id: The integer invoice ID stored in the database.

    Returns:
        A JSON string containing:
        {
            "invoice_number": str,
            "charges": [
                {
                    "raw_charge_name": str,
                    "amount": float,
                    "rate": float,
                    "qty": float,
                    "basis": str,
                    "currency": str
                }, ...
            ]
        }
        or {"error": "...", "charges": []} on failure.
    """
    from app.database import async_session_factory
    from app.models import Invoice
    from app.services.oss_storage import download_invoice_from_oss
    from app.services.qwen_vl import extract_invoice_with_qwen_vl_or_veryfi
    from sqlalchemy import select

    logger.info(f"[TOOL:pdf_parser] Processing invoice_id={invoice_id}")

    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(Invoice).where(Invoice.id == int(invoice_id))
            )
            invoice = result.scalar_one_or_none()

        if not invoice:
            return json.dumps({"error": f"Invoice {invoice_id} not found", "charges": []})

        # Download PDF bytes from OSS (or local fallback)
        pdf_bytes = await download_invoice_from_oss(invoice.file_path)

        # Extract charges using Qwen-VL (with Veryfi fallback)
        inv_number, charges = await extract_invoice_with_qwen_vl_or_veryfi(
            file_path=invoice.file_path,
            pdf_bytes=pdf_bytes,
        )

        charges_list = [
            {
                "raw_charge_name": c.raw_charge_name,
                "amount": float(c.amount),
                "rate": float(c.rate),
                "qty": float(c.qty),
                "basis": c.basis or "Per Shipment",
                "currency": getattr(c, "currency", "USD"),
            }
            for c in charges
        ]

        logger.info(
            f"[TOOL:pdf_parser] Extracted {len(charges_list)} charges "
            f"from invoice_id={invoice_id}"
        )
        return json.dumps({"invoice_number": inv_number, "charges": charges_list})

    except Exception as exc:
        logger.exception(f"[TOOL:pdf_parser] Error for invoice_id={invoice_id}: {exc}")
        return json.dumps({"error": str(exc), "charges": []})
