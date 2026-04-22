"""
Seed script to create SYSTEM company and populate standard charge master.
Run this once after database setup: python scripts/seed_standard_charges.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Company, Charge, ChargeAlias

# Standard freight charges with their common aliases
STANDARD_CHARGES = [
    {
        "name": "Air Freight",
        "short_name": "AIRFRT",
        "aliases": ["freight", "air freight charge", "airfreight", "air cargo", "air transport"],
    },
    {
        "name": "Fuel Surcharge",
        "short_name": "FSC",
        "aliases": ["fsc", "fuel levy", "bunker surcharge", "baf", "fuel adjustment", "bunker adjustment factor"],
    },
    {
        "name": "Security Surcharge",
        "short_name": "ISS",
        "aliases": ["iss", "security fee", "security charge", "isps"],
    },
    {
        "name": "Destination Terminal Handling",
        "short_name": "DESTTHC",
        "aliases": ["destination charges", "destination handling", "dest handling", "terminal handling", "thc dest", "destination terminal handling fee"],
    },
    {
        "name": "Inland Transportation",
        "short_name": "INLAND",
        "aliases": ["delivery", "inland haulage", "trucking", "cartage", "delivery cartage"],
    },
    {
        "name": "House B/L Fee",
        "short_name": "HBL",
        "aliases": ["hbl fee", "house bill fee", "hawb fee", "house airway bill", "house b/l fees"],
    },
    {
        "name": "AMS Fee",
        "short_name": "AMS",
        "aliases": ["ams filing", "ams charge", "manifest fee", "ams fee"],
    },
    {
        "name": "Destination Handling",
        "short_name": "DESTHND",
        "aliases": ["dest handling", "destination charges", "handling fee destination"],
    },
    {
        "name": "Origin Charges",
        "short_name": "ORIGCHG",
        "aliases": ["origin handling", "origin fees", "handling fee origin"],
    },
    {
        "name": "VAT on Services",
        "short_name": "VAT",
        "aliases": ["vat", "tax", "service tax", "gst", "vat on services"],
    },
    {
        "name": "Terminal Fee",
        "short_name": "TERM",
        "aliases": ["terminal", "terminal fee", "terminal charge", "terminal handling"],
    },
    {
        "name": "CFS Handling",
        "short_name": "CFS",
        "aliases": ["cfs", "container freight station", "cfs charge", "cfs handling"],
    },
    {
        "name": "Import Service Charge",
        "short_name": "ISC",
        "aliases": ["isc", "import charge", "import fee", "import service charge - airline"],
    },
    {
        "name": "Document Turnover Fee",
        "short_name": "DOCTURN",
        "aliases": ["doc fee", "documentation fee", "document fee", "doc turnover", "document turnover fee"],
    },
]


async def seed_standard_charges():
    """Create SYSTEM company and populate with standard charges."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Create async engine
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if SYSTEM company already exists
        result = await session.execute(
            select(Company).where(Company.short_name == "SYSTEM")
        )
        system_company = result.scalar_one_or_none()

        if system_company:
            print(f"✓ SYSTEM company already exists (id={system_company.id})")
        else:
            # Create SYSTEM company
            system_company = Company(
                name="Standard Charge Master",
                short_name="SYSTEM",
                type="client",  # Use client type so charges work
                is_active=True,
                city="Global",
                country="Global",
            )
            session.add(system_company)
            await session.flush()
            print(f"✓ Created SYSTEM company (id={system_company.id})")

        # Add standard charges
        for charge_data in STANDARD_CHARGES:
            # Check if charge already exists
            result = await session.execute(
                select(Charge).where(
                    Charge.company_id == system_company.id,
                    Charge.name == charge_data["name"]
                )
            )
            existing_charge = result.scalar_one_or_none()

            if existing_charge:
                print(f"  - {charge_data['name']} already exists")
                charge = existing_charge
            else:
                # Create charge
                charge = Charge(
                    company_id=system_company.id,
                    name=charge_data["name"],
                    short_name=charge_data["short_name"],
                    is_active=True,
                )
                session.add(charge)
                await session.flush()
                print(f"  + Created charge: {charge_data['name']}")

            # Add aliases
            for alias in charge_data["aliases"]:
                # Check if alias already exists
                result = await session.execute(
                    select(ChargeAlias).where(
                        ChargeAlias.charge_id == charge.id,
                        ChargeAlias.alias == alias
                    )
                )
                existing_alias = result.scalar_one_or_none()

                if not existing_alias:
                    alias_obj = ChargeAlias(
                        charge_id=charge.id,
                        alias=alias
                    )
                    session.add(alias_obj)
                    print(f"    + Added alias: {alias}")

        await session.commit()
        print("\n✓ Standard charge master seeded successfully!")
        print(f"  SYSTEM company ID: {system_company.id}")
        print(f"  Total charges: {len(STANDARD_CHARGES)}")


if __name__ == "__main__":
    asyncio.run(seed_standard_charges())
