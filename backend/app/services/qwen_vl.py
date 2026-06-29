"""
Qwen-VL Invoice Extraction Service (LogiSight).
Uses qwen-vl-max via DashScope to parse freight invoice PDFs into structured line items.
This is the PRIMARY extraction method; Veryfi is the fallback.

Models used:
  - qwen-vl-max: Multimodal visual understanding of PDF images
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_VL_MODEL = "qwen-vl-max"

EXTRACTION_PROMPT = (
    "You are a freight invoice parser. Extract all charge line items from this invoice image. "
    "Return ONLY a JSON array — no markdown, no explanation. "
    "Each element must have exactly these fields:\n"
    "  charge_name (string): descriptive name of the charge\n"
    "  amount (number): total amount for this line\n"
    "  currency (string): 3-letter currency code, e.g. USD\n"
    "  quantity (number or null): quantity / weight if shown\n"
    "  unit (string or null): unit of measure, e.g. KG, CBM, Per Shipment\n"
    "  rate (number or null): unit rate if shown\n\n"
    "If the invoice has a single total only, return one element with charge_name='Total Invoice Amount'.\n"
    "Example: [{\"charge_name\": \"Ocean Freight\", \"amount\": 1200.00, \"currency\": \"USD\", "
    "\"quantity\": 1, \"unit\": \"Per Shipment\", \"rate\": 1200.00}]"
)

INVOICE_META_PROMPT = (
    "Extract the following metadata from this freight invoice image. "
    "Return ONLY a JSON object with these keys:\n"
    "  invoice_number (string): the invoice or document number\n"
    "  invoice_date (string or null): date in YYYY-MM-DD format if found\n"
    "  currency (string): primary 3-letter currency code\n\n"
    "If a field cannot be found, use null. Return ONLY valid JSON, no markdown."
)


@dataclass
class QwenExtractedCharge:
    """Represents a single charge line extracted by Qwen-VL."""

    raw_charge_name: str
    rate: Decimal
    qty: Decimal
    amount: Decimal
    basis: str | None
    currency: str = "USD"


def _normalize_basis_from_unit(unit: str | None) -> str:
    """Map Qwen-VL unit strings to canonical LogiSight basis values."""
    if not unit:
        return "Per Shipment"
    u = unit.upper()
    if "KG" in u or "KILO" in u or "WEIGHT" in u:
        return "Per KG"
    if "CBM" in u or "CUBIC" in u or "M3" in u or "VOLUME" in u:
        return "Per CBM"
    if "CHG" in u or "CHARGEABLE" in u:
        return "Per Chg Wt"
    if "FLAT" in u:
        return "Flat Rate"
    return "Per Shipment"


def _get_dashscope_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is not set. "
            "Set it in .env to enable Qwen-VL invoice parsing."
        )
    return key


async def _render_pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    """
    Convert PDF pages to JPEG images using pdf2image.
    Returns list of JPEG bytes, one per page (max 3 pages for cost efficiency).
    """
    try:
        from pdf2image import convert_from_bytes
        import io
        from PIL import Image as PILImage

        images = convert_from_bytes(pdf_bytes, dpi=150, fmt="JPEG", first_page=1, last_page=3)
        result = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            result.append(buf.getvalue())
        return result
    except ImportError:
        raise RuntimeError(
            "pdf2image and/or Pillow not installed. "
            "Run: pip install pdf2image Pillow"
        )


async def _call_qwen_vl(
    api_key: str,
    image_bytes: bytes,
    prompt: str,
    model: str = QWEN_VL_MODEL,
) -> str:
    """Send a single image to Qwen-VL and return the text response."""
    image_b64 = base64.b64encode(image_bytes).decode()

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()

    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _parse_charge_list(raw_json: str) -> list[dict]:
    """Parse JSON string from Qwen-VL, stripping markdown fences if present."""
    text = raw_json.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def _parse_invoice_meta(raw_json: str) -> dict:
    """Parse invoice metadata JSON from Qwen-VL."""
    text = raw_json.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def _coerce_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Safely convert a value to Decimal."""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


async def parse_invoice_with_qwen_vl(
    pdf_bytes: bytes,
) -> tuple[str, list[QwenExtractedCharge]]:
    """
    Primary invoice extraction method using Qwen-VL multimodal model.

    Converts the PDF to images, sends the first page to qwen-vl-max for
    structured charge extraction. Returns (invoice_number, list[QwenExtractedCharge]).

    Args:
        pdf_bytes: Raw PDF file bytes

    Returns:
        Tuple of (invoice_number, list of extracted charges)

    Raises:
        RuntimeError: If DASHSCOPE_API_KEY is not set or parsing fails
    """
    api_key = _get_dashscope_api_key()

    logger.info("[QWEN-VL] Starting PDF to image conversion")
    images = await _render_pdf_to_images(pdf_bytes)

    if not images:
        raise RuntimeError("PDF could not be rendered to images (empty document?)")

    logger.info(f"[QWEN-VL] Rendered {len(images)} page(s). Sending page 1 for extraction.")

    # Step 1: Extract metadata from first page
    meta_raw = await _call_qwen_vl(api_key, images[0], INVOICE_META_PROMPT)
    logger.info(f"[QWEN-VL] Metadata raw response: {meta_raw[:300]}")

    try:
        meta = _parse_invoice_meta(meta_raw)
        invoice_number = meta.get("invoice_number") or f"INV-QWEN-{id(pdf_bytes)}"
        default_currency = meta.get("currency") or "USD"
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[QWEN-VL] Could not parse metadata JSON: {e}. Using defaults.")
        invoice_number = f"INV-QWEN-{id(pdf_bytes)}"
        default_currency = "USD"

    # Step 2: Extract charge line items (process all pages, combine)
    all_raw_items: list[dict] = []
    for page_idx, img_bytes in enumerate(images):
        logger.info(f"[QWEN-VL] Extracting charges from page {page_idx + 1}")
        try:
            charges_raw = await _call_qwen_vl(api_key, img_bytes, EXTRACTION_PROMPT)
            logger.info(f"[QWEN-VL] Page {page_idx + 1} raw charges: {charges_raw[:400]}")
            items = _parse_charge_list(charges_raw)
            all_raw_items.extend(items)
        except (json.JSONDecodeError, httpx.HTTPStatusError) as e:
            logger.warning(f"[QWEN-VL] Page {page_idx + 1} extraction failed: {e}")
            continue

    logger.info(f"[QWEN-VL] Total raw items extracted: {len(all_raw_items)}")

    # Step 3: Normalise into QwenExtractedCharge objects
    charges: list[QwenExtractedCharge] = []
    for idx, item in enumerate(all_raw_items):
        name = str(item.get("charge_name") or "").strip()
        if not name or len(name) < 2:
            logger.debug(f"[QWEN-VL] Item {idx}: skipping — no charge name")
            continue

        amount = _coerce_decimal(item.get("amount"))
        if amount == Decimal("0"):
            logger.debug(f"[QWEN-VL] Item {idx}: skipping '{name}' — zero amount")
            continue

        rate_val = item.get("rate")
        qty_val = item.get("quantity")

        if rate_val is not None and qty_val is not None:
            rate = _coerce_decimal(rate_val, amount)
            qty = _coerce_decimal(qty_val, Decimal("1"))
        else:
            rate = amount
            qty = Decimal("1")

        basis = _normalize_basis_from_unit(item.get("unit"))
        currency = str(item.get("currency") or default_currency).upper()[:3]

        charges.append(
            QwenExtractedCharge(
                raw_charge_name=name,
                rate=rate,
                qty=qty,
                amount=amount,
                basis=basis,
                currency=currency,
            )
        )
        logger.info(
            f"[QWEN-VL] ✓ Charge: '{name}' | {currency} {amount} | {basis}"
        )

    logger.info(
        f"[QWEN-VL] Extraction complete: invoice='{invoice_number}', "
        f"{len(charges)} charges"
    )
    return invoice_number, charges


async def extract_invoice_with_qwen_vl_or_veryfi(
    file_path: str,
    pdf_bytes: bytes | None = None,
) -> tuple[str, list]:
    """
    Attempt Qwen-VL extraction first; fall back to Veryfi on failure.
    Returns (invoice_number, list of charge objects compatible with both extractors).

    This is the recommended entry point for invoice extraction in the autopilot pipeline.
    """
    if pdf_bytes is None:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

    # Try Qwen-VL first
    try:
        invoice_number, charges = await parse_invoice_with_qwen_vl(pdf_bytes)
        if charges:
            logger.info(
                f"[EXTRACTION] Qwen-VL succeeded: {len(charges)} charges extracted"
            )
            return invoice_number, charges
        else:
            logger.warning("[EXTRACTION] Qwen-VL returned 0 charges, falling back to Veryfi")
    except RuntimeError as e:
        if "DASHSCOPE_API_KEY" in str(e):
            logger.info("[EXTRACTION] Qwen-VL not configured, using Veryfi")
        else:
            logger.warning(f"[EXTRACTION] Qwen-VL failed ({e}), falling back to Veryfi")
    except Exception as e:
        logger.warning(f"[EXTRACTION] Qwen-VL unexpected error ({e}), falling back to Veryfi")

    # Fallback to Veryfi
    logger.info("[EXTRACTION] Using Veryfi OCR fallback")
    from app.services.invoice_extraction import extract_invoice_with_veryfi
    return await extract_invoice_with_veryfi(file_path)
