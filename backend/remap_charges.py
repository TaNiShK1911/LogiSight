"""
Remap all unmapped charges for a company against current Charge Master.
This fixes quotes/invoices that were submitted before aliases were added.
"""
import asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine
from app.models import QuoteCharge, InvoiceCharge, Quote, Invoice
from app.services.charge_mapping import resolve_raw_charge_name


async def remap_quote_charges(company_id: int):
    """Remap all unmapped quote charges for a company."""
    async with AsyncSession(engine) as session:
        # Find all unmapped quote charges for this company
        result = await session.execute(
            select(QuoteCharge)
            .join(Quote, Quote.id == QuoteCharge.quote_id)
            .where(
                Quote.buyer_id == company_id,
                QuoteCharge.mapped_charge_id.is_(None)
            )
        )
        unmapped_charges = list(result.scalars().all())

        print(f"Found {len(unmapped_charges)} unmapped quote charges for company {company_id}")

        remapped_count = 0
        for qc in unmapped_charges:
            # Try to map against current Charge Master
            mid, mname, tier, low, sim = await resolve_raw_charge_name(
                session, qc.raw_charge_name, company_id
            )

            if mid is not None:
                # Update the charge with new mapping
                qc.mapped_charge_id = mid
                qc.mapped_charge_name = mname
                qc.mapping_tier = tier.value
                qc.low_confidence = low
                qc.similarity_score = sim
                remapped_count += 1
                print(f"  [OK] Remapped: \"{qc.raw_charge_name}\" -> \"{mname}\" (tier: {tier.value})")

        await session.commit()
        print(f"\nRemapped {remapped_count} out of {len(unmapped_charges)} quote charges")
        return remapped_count


async def remap_invoice_charges(company_id: int):
    """Remap all unmapped invoice charges for a company."""
    async with AsyncSession(engine) as session:
        # Find all unmapped invoice charges for this company
        result = await session.execute(
            select(InvoiceCharge)
            .join(Invoice, Invoice.id == InvoiceCharge.invoice_id)
            .join(Quote, Quote.id == Invoice.quote_id)
            .where(
                Quote.buyer_id == company_id,
                InvoiceCharge.mapped_charge_id.is_(None)
            )
        )
        unmapped_charges = list(result.scalars().all())

        print(f"Found {len(unmapped_charges)} unmapped invoice charges for company {company_id}")

        remapped_count = 0
        for ic in unmapped_charges:
            # Try to map against current Charge Master
            mid, mname, tier, low, sim = await resolve_raw_charge_name(
                session, ic.raw_charge_name, company_id
            )

            if mid is not None:
                # Update the charge with new mapping
                ic.mapped_charge_id = mid
                ic.mapped_charge_name = mname
                ic.mapping_tier = tier.value
                ic.low_confidence = low
                ic.similarity_score = sim
                remapped_count += 1
                print(f"  [OK] Remapped: \"{ic.raw_charge_name}\" -> \"{mname}\" (tier: {tier.value})")

        await session.commit()
        print(f"\nRemapped {remapped_count} out of {len(unmapped_charges)} invoice charges")
        return remapped_count


async def main():
    company_id = 9  # aditya global

    print(f"=== Remapping charges for company_id={company_id} ===\n")

    print("1. Remapping quote charges...")
    quote_count = await remap_quote_charges(company_id)

    print("\n2. Remapping invoice charges...")
    invoice_count = await remap_invoice_charges(company_id)

    print(f"\n=== DONE ===")
    print(f"Total remapped: {quote_count + invoice_count} charges")
    print("\nNote: You should re-analyze invoices to regenerate anomalies with the new mappings.")


if __name__ == "__main__":
    asyncio.run(main())
