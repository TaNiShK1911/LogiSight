"""
Create sample Charge Master entries for testing
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def create_sample_charges():
    # Common freight charges
    charges = [
        ("Air Freight", "AIR-FRT"),
        ("Fuel Surcharge", "FSC"),
        ("Security Surcharge", "SEC"),
        ("Freight", "FRT"),
        ("Airline Handling", "AH"),
        ("Import Customs Clearance", "ICC"),
        ("Environmental Fee", "ENV"),
        ("Origin Charges", "ORIG"),
        ("Handling", "HNDL"),
        ("Delivery", "DEL"),
        ("EDI Charges", "EDI"),
        ("House B/L Fees", "HBL"),
        ("AMS Fee", "AMS"),
        ("Terminal Handling", "THC"),
        ("Transfer Fee", "XFER"),
        ("Inland Transportation", "INLD"),
        ("Weekend Transfer", "WKND"),
        ("Filing Fee", "FILE"),
    ]

    company_id = 9  # aditya global

    async with engine.begin() as conn:
        for name, short_name in charges:
            # Insert charge
            result = await conn.execute(text("""
                INSERT INTO charges (company_id, name, short_name, is_active)
                VALUES (:company_id, :name, :short_name, true)
                ON CONFLICT (company_id, name) DO NOTHING
                RETURNING id
            """), {"company_id": company_id, "name": name, "short_name": short_name})

            charge_id = result.scalar_one_or_none()
            if charge_id:
                print(f"[OK] Created charge: {name}")

                # Add common aliases
                aliases = []
                if "Freight" in name:
                    aliases = ["Freight Charges", "Air Freight", "Ocean Freight"]
                elif "Fuel" in name:
                    aliases = ["FSC", "Fuel Charge", "Bunker Surcharge"]
                elif "Security" in name:
                    aliases = ["ISS", "Security Fee"]
                elif "Handling" in name:
                    aliases = ["Handling Charges", "Handling Import", "Handling Fee"]
                elif "Delivery" in name:
                    aliases = ["Delivery Fee", "Delivery - unstackable"]
                elif "Origin" in name:
                    aliases = ["Origin Charges + pick up", "Origin Fee"]
                elif "Customs" in name:
                    aliases = ["Import Customs clearance Charges", "Customs Fee"]
                elif "Terminal" in name:
                    aliases = ["Destination Terminal Handling", "THC"]
                elif "Transfer" in name:
                    aliases = ["Transfer Fee Flat Rate", "Weekend Transfer"]
                elif "Transportation" in name:
                    aliases = ["Inland Transportation Flat Rate"]
                elif "Filing" in name:
                    aliases = ["Inbond Filing Fee", "Filing Fee Flat Rate"]

                for alias in aliases:
                    await conn.execute(text("""
                        INSERT INTO charge_aliases (charge_id, alias)
                        VALUES (:charge_id, :alias)
                        ON CONFLICT DO NOTHING
                    """), {"charge_id": charge_id, "alias": alias})
                    print(f"  + Added alias: {alias}")
            else:
                print(f"[SKIP] Charge already exists: {name}")

asyncio.run(create_sample_charges())
print("\n[DONE] Sample Charge Master created for company_id=9")
