"""
Script to fix orphaned companies (companies without profiles).
This creates Profile records for users that exist in auth.users but not in profiles table.

Run: python fix_orphaned_profiles.py
"""

import asyncio
import os
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import select, text

load_dotenv()

from app.database import async_session_factory
from app.models import Company, Profile


async def fix_orphaned_profiles():
    """Find companies without profiles and create them if users exist in auth.users."""

    print("\n" + "=" * 60)
    print("FIXING ORPHANED PROFILES")
    print("=" * 60)

    async with async_session_factory() as db:
        # Find companies without profiles
        result = await db.execute(
            text("""
                SELECT c.id, c.name, c.type
                FROM companies c
                LEFT JOIN profiles p ON p.company_id = c.id
                WHERE p.id IS NULL
                ORDER BY c.id
            """)
        )
        orphaned_companies = result.fetchall()

        if not orphaned_companies:
            print("\n✓ No orphaned companies found. All companies have profiles.")
            return

        print(f"\n⚠ Found {len(orphaned_companies)} companies without profiles:")
        for company in orphaned_companies:
            print(f"   - Company ID: {company[0]}, Name: '{company[1]}', Type: {company[2]}")

        # For each orphaned company, try to find users in auth.users
        print("\n" + "=" * 60)
        print("SEARCHING FOR USERS IN AUTH.USERS")
        print("=" * 60)

        for company_id, company_name, company_type in orphaned_companies:
            print(f"\nCompany ID {company_id} ({company_name}):")

            # Try to find users with this company_id in app_metadata
            result = await db.execute(
                text("""
                    SELECT id, email, raw_app_meta_data
                    FROM auth.users
                    WHERE raw_app_meta_data->>'company_id' = :company_id
                """),
                {"company_id": str(company_id)},
            )
            users = result.fetchall()

            if not users:
                print(f"   ✗ No users found in auth.users for company_id={company_id}")
                print(f"   → You need to create users via POST /companies/{company_id}/users")
                continue

            print(f"   ✓ Found {len(users)} user(s) in auth.users:")

            for user_id, email, metadata in users:
                print(f"      - {email} (UUID: {user_id})")

                # Check if profile already exists (shouldn't, but let's be safe)
                existing = await db.get(Profile, UUID(user_id))
                if existing:
                    print(f"        → Profile already exists (skipping)")
                    continue

                # Extract role from metadata
                role = metadata.get("role", "client" if company_type == "client" else "forwarder")
                is_admin = metadata.get("is_admin", False)

                # Create profile
                profile = Profile(
                    id=UUID(user_id),
                    company_id=company_id,
                    name=email.split("@")[0],  # Use email prefix as name
                    role=role,
                    is_admin=is_admin,
                )
                db.add(profile)
                print(f"        → Creating profile...")

            try:
                await db.commit()
                print(f"   ✓ Profiles created successfully for company {company_id}")
            except Exception as e:
                await db.rollback()
                print(f"   ✗ Failed to create profiles: {e}")

        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Verify all companies now have profiles
        result = await db.execute(
            text("""
                SELECT c.id, c.name, COUNT(p.id) as profile_count
                FROM companies c
                LEFT JOIN profiles p ON p.company_id = c.id
                GROUP BY c.id, c.name
                ORDER BY c.id
            """)
        )
        companies = result.fetchall()

        print("\nCompanies and their profile counts:")
        for company_id, company_name, profile_count in companies:
            status = "✓" if profile_count > 0 else "✗"
            print(f"   {status} Company ID {company_id} ({company_name}): {profile_count} profile(s)")


if __name__ == "__main__":
    asyncio.run(fix_orphaned_profiles())
