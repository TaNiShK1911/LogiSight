"""
Invoice vs accepted-quote anomaly detection (LogiSight) — mirrors frontend client.ts logic.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Anomaly, Invoice, InvoiceCharge, Quote, QuoteCharge
from app.schemas import AnomalyFlagType


async def run_invoice_analysis(session: AsyncSession, invoice_id: int) -> list[Anomaly]:
    r0 = await session.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.invoice_charges),
            selectinload(Invoice.quote).selectinload(Quote.quote_charges),
        )
    )
    inv = r0.scalar_one_or_none()
    if inv is None:
        raise ValueError("invoice not found")

    quote = inv.quote
    if quote is None:
        raise ValueError("quote missing")

    if quote.status != "ACCEPTED":
        raise ValueError("quote must be ACCEPTED before analysis")

    invoice_charges = list(inv.invoice_charges or [])
    quote_charges = list(quote.quote_charges or [])

    # Build lookup maps by mapped_charge_id
    quote_by_mapped: dict[int, QuoteCharge] = {}
    for qc in quote_charges:
        if qc.mapped_charge_id is not None:
            quote_by_mapped[int(qc.mapped_charge_id)] = qc

    invoice_by_mapped: dict[int, InvoiceCharge] = {}
    for ic in invoice_charges:
        if ic.mapped_charge_id is not None:
            invoice_by_mapped[int(ic.mapped_charge_id)] = ic

    # Build fallback lookup by raw charge name (normalized)
    quote_by_raw: dict[str, QuoteCharge] = {}
    for qc in quote_charges:
        key = qc.raw_charge_name.strip().lower()
        quote_by_raw[key] = qc

    invoice_by_raw: dict[str, InvoiceCharge] = {}
    for ic in invoice_charges:
        key = ic.raw_charge_name.strip().lower()
        invoice_by_raw[key] = ic

    rows: list[dict] = []

    print(f"\n=== Anomaly Detection for Invoice {invoice_id} ===")
    print(f"Invoice charges: {len(invoice_charges)}, Quote charges: {len(quote_charges)}")

    # Only check for amount mismatches on charges that exist in both quote and invoice
    # Don't flag unexpected or missing charges - forwarders may legitimately add/remove charges
    for ic in invoice_charges:
        qc: QuoteCharge | None = None

        # Try to match by mapped_charge_id first (if both are mapped to the SAME charge master entry)
        if ic.mapped_charge_id is not None:
            mid = int(ic.mapped_charge_id)
            qc = quote_by_mapped.get(mid)
            if qc:
                print(f"✓ Matched '{ic.raw_charge_name}' by mapped_id={mid}")

        # Fallback: match by raw charge name (handles unmapped or mismatched mappings)
        if qc is None:
            raw_key = ic.raw_charge_name.strip().lower()
            qc = quote_by_raw.get(raw_key)
            if qc:
                print(f"✓ Matched '{ic.raw_charge_name}' by raw name")

        # If no matching quote charge found, skip (don't flag as unexpected)
        if qc is None:
            print(f"- Skipped '{ic.raw_charge_name}' (no match in quote)")
            continue

        # Only flag amount mismatch - ignore rate/basis differences when amounts match
        amount_diff = abs(_to_float(ic.amount) - _to_float(qc.amount))
        if amount_diff > 0.01:
            label = ic.raw_charge_name  # Always use raw charge name for clarity
            print(f"⚠ AMOUNT_MISMATCH: '{label}' - invoice: {ic.amount}, quote: {qc.amount}, diff: {amount_diff}")
            rows.append(
                {
                    "invoice_id": invoice_id,
                    "invoice_charge_id": int(ic.id),
                    "flag_type": AnomalyFlagType.AMOUNT_MISMATCH.value,
                    "description": f'"{label}": invoiced {ic.amount}, quoted {qc.amount}.',
                    "variance": _to_float(ic.amount) - _to_float(qc.amount),
                }
            )
        else:
            print(f"✓ '{ic.raw_charge_name}' amounts match (diff: {amount_diff})")

    other = await session.execute(
        select(Invoice.id).where(
            Invoice.quote_id == inv.quote_id,
            Invoice.id != invoice_id,
        )
    )
    if other.first() is not None:
        rows.append(
            {
                "invoice_id": invoice_id,
                "invoice_charge_id": None,
                "flag_type": AnomalyFlagType.DUPLICATE_INVOICE.value,
                "description": "Another invoice already exists for this quote. Possible duplicate submission.",
                "variance": None,
            }
        )

    await session.execute(delete(Anomaly).where(Anomaly.invoice_id == invoice_id))

    for row in rows:
        session.add(
            Anomaly(
                invoice_id=row["invoice_id"],
                invoice_charge_id=row["invoice_charge_id"],
                flag_type=row["flag_type"],
                description=row["description"],
                variance=row["variance"],
            )
        )

    await session.commit()

    result = await session.execute(
        select(Anomaly).where(Anomaly.invoice_id == invoice_id).order_by(Anomaly.id)
    )
    return list(result.scalars().all())


def _to_float(v: Decimal | float | int | None) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)
