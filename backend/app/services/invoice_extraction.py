"""
Invoice PDF extraction using Veryfi OCR API (LogiSight).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ExtractedCharge:
    """Represents a single charge line extracted from an invoice."""

    raw_charge_name: str
    rate: Decimal
    qty: Decimal
    amount: Decimal
    basis: str | None  # Will try to infer from Veryfi data


def _normalize_basis(raw_unit: str | None) -> str:
    """
    Normalize various basis strings to canonical values.
    Returns "Per Shipment" as default if cannot determine.
    """
    if not raw_unit:
        return "Per Shipment"

    unit_upper = raw_unit.upper()

    # Check for chargeable weight variations
    if "CHG" in unit_upper and "WT" in unit_upper:
        return "Per Chg Wt"
    if "CHARGEABLE" in unit_upper and "WEIGHT" in unit_upper:
        return "Per Chg Wt"

    # Check for standard weight
    if "KG" in unit_upper or "KILO" in unit_upper or "WEIGHT" in unit_upper:
        return "Per KG"

    # Check for volume
    if "CBM" in unit_upper or "CUBIC" in unit_upper or "VOLUME" in unit_upper or "M3" in unit_upper:
        return "Per CBM"

    return "Per Shipment"


async def extract_invoice_with_veryfi(file_path: str) -> tuple[str, list[ExtractedCharge]]:
    """
    Extract invoice data using Veryfi OCR API.

    Args:
        file_path: Path to the PDF file

    Returns:
        Tuple of (invoice_number, list of extracted charges)

    Raises:
        RuntimeError: If Veryfi credentials are not configured
        Exception: If Veryfi API call fails
    """
    # Get Veryfi credentials from environment
    client_id = os.environ.get("VERYFI_CLIENT_ID", "")
    client_secret = os.environ.get("VERYFI_CLIENT_SECRET", "")
    username = os.environ.get("VERYFI_USERNAME", "")
    api_key = os.environ.get("VERYFI_API_KEY", "")

    if not all([client_id, client_secret, username, api_key]):
        raise RuntimeError(
            "Veryfi credentials not configured. Set VERYFI_CLIENT_ID, "
            "VERYFI_CLIENT_SECRET, VERYFI_USERNAME, and VERYFI_API_KEY"
        )

    try:
        from veryfi import Client as VeryfiClient
    except ImportError as exc:
        raise RuntimeError("veryfi package not installed. Run: pip install veryfi") from exc

    # Initialize Veryfi client
    print(f"[VERYFI] Initializing client for file: {file_path}")
    veryfi_client = VeryfiClient(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        api_key=api_key,
    )

    # Check if file exists
    if not os.path.exists(file_path):
        raise RuntimeError(f"File not found: {file_path}")

    print(f"[VERYFI] Processing document: {file_path}")
    print(f"[VERYFI] File size: {os.path.getsize(file_path)} bytes")

    # Process the document with categories for better extraction
    result = veryfi_client.process_document(
        file_path=file_path,
        categories=["Freight", "Logistics", "Invoice"]
    )

    print(f"[VERYFI] API call successful")
    print(f"[VERYFI] Response keys: {list(result.keys())}")

    # Extract invoice metadata
    invoice_number = result.get("invoice_number", "")
    if not invoice_number:
        invoice_number = result.get("document_number", f"INV-{os.path.basename(file_path)}")

    vendor_name = result.get("vendor", {}).get("name", "") if isinstance(result.get("vendor"), dict) else ""
    invoice_date = result.get("date", "")
    due_date = result.get("due_date", "")
    currency_code = result.get("currency_code", "USD")
    tracking_number = result.get("tracking_number", "")

    print(f"[VERYFI] Extracted invoice_number: {invoice_number}")
    print(f"[VERYFI] Vendor: {vendor_name}")
    print(f"[VERYFI] Date: {invoice_date}, Due: {due_date}")
    print(f"[VERYFI] Currency: {currency_code}, Tracking: {tracking_number}")

    # Extract line items
    charges: list[ExtractedCharge] = []
    line_items = result.get("line_items", [])

    print(f"[VERYFI] Found {len(line_items)} line items")

    for i, item in enumerate(line_items, 1):
        # Extract charge name (description)
        charge_name = item.get("description", "")
        if not charge_name or charge_name.strip() == "":
            # Skip charges with no description
            print(f"[VERYFI] Line {i}: Skipping - no description")
            continue

        # Clean up charge name: remove newlines, extra spaces, and normalize
        charge_name = " ".join(charge_name.split())

        # Remove company names and common prefixes
        import re
        # Remove company names like "CH ROBINSON INTERNATIONAL, INC."
        charge_name = re.sub(r'^[A-Z\s,\.]+(?:INC\.|LLC|LTD|CO\.|CORP\.?)\s*', '', charge_name, flags=re.IGNORECASE).strip()

        # Remove trailing type indicators that duplicate the basis field
        for suffix in ["Per Chg Wt", "Flat Rate", "Per Shipment", "Per KG", "Per CBM"]:
            if charge_name.endswith(suffix):
                charge_name = charge_name[:-len(suffix)].strip()

        # Remove trailing unit/container codes (M3, PLT, KG, LBS, etc.)
        charge_name = re.sub(r'\s+(M3|PLT|KG|LBS|CBM|CTN|PCS|CTNS)\s*$', '', charge_name, flags=re.IGNORECASE).strip()

        # Remove trailing numbers that might be weights/quantities
        charge_name = re.sub(r'\s+\d{1,3}(,\d{3})*(\.\d+)?$', '', charge_name).strip()

        # If charge name is now empty or too short, skip this charge
        if not charge_name or len(charge_name) < 3:
            print(f"[VERYFI] Line {i}: Skipping - charge name too short after cleaning")
            continue

        # Extract rate (unit price)
        rate_raw = item.get("unit_price") or item.get("price")

        # Extract quantity
        qty_raw = item.get("quantity")

        # Extract total amount
        amount_raw = item.get("total")
        if not amount_raw and rate_raw and qty_raw:
            amount_raw = rate_raw * qty_raw
        amount = Decimal(str(amount_raw)) if amount_raw else Decimal("0")

        # Skip charges with no amount
        if amount == 0:
            print(f"[VERYFI] Line {i}: Skipping - no amount")
            continue

        # If no rate per unit is explicitly mentioned, use amount as rate with qty=1
        if not rate_raw:
            rate = amount
            qty = Decimal("1")
            print(f"[VERYFI] Line {i}: No unit price found, using amount as rate with qty=1")
        else:
            rate = Decimal(str(rate_raw))
            qty = Decimal(str(qty_raw)) if qty_raw else Decimal("1")

        # Try to infer basis from unit of measure
        unit_of_measure = item.get("unit_of_measure") or item.get("unit")
        basis = _normalize_basis(unit_of_measure)

        print(f"[VERYFI] Line {i}: {charge_name} - Rate: {rate}, Qty: {qty}, Amount: {amount}, Basis: {basis}")

        charges.append(
            ExtractedCharge(
                raw_charge_name=charge_name.strip(),
                rate=rate,
                qty=qty,
                amount=amount,
                basis=basis,
            )
        )

    # If no line items found, try to extract from total
    if not charges:
        print("[VERYFI] No line items found, trying to extract from total")
        # Fallback: create a single charge with the total amount
        total = result.get("total", 0)
        if total and float(total) > 0:
            charges.append(
                ExtractedCharge(
                    raw_charge_name="Total Invoice Amount",
                    rate=Decimal(str(total)),
                    qty=Decimal("1"),
                    amount=Decimal(str(total)),
                    basis="Per Shipment",
                )
            )
            print(f"[VERYFI] Created fallback charge with total: {total}")

    print(f"[VERYFI] Extraction complete: {len(charges)} charges extracted")
    return invoice_number, charges
