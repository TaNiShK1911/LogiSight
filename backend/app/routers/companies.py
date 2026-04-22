"""
Companies and user admin — Super Admin (LogiSight).
"""

from __future__ import annotations

import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db, require_super_admin
from app.models import Company, Profile
from app.schemas import (
    CompanyCreateWithAdmin,
    CompanyRead,
    CompanyStatusPatch,
    CompanyUserCreate,
    ProfileAdminPatch,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _supabase_new_user_id(auth_resp: object) -> str:
    user = getattr(auth_resp, "user", None)
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    if isinstance(auth_resp, dict):
        u = auth_resp.get("user")
        if isinstance(u, dict) and u.get("id"):
            return str(u["id"])
    raise HTTPException(status_code=500, detail="Supabase did not return a user id")


def _supabase_admin_client():
    try:
        from supabase import create_client
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="supabase package not installed",
        ) from exc

    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required",
        )
    return create_client(url, key)


@router.get("", response_model=list[CompanyRead])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> list[Company]:
    result = await db.execute(select(Company).order_by(Company.name))
    return list(result.scalars().all())


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreateWithAdmin,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Company:
    company = Company(
        name=body.name,
        short_name=body.short_name,
        type=body.type,
        address=body.address,
        city=body.city,
        country=body.country,
        is_active=True,
    )
    db.add(company)
    await db.flush()

    profile_role = "client" if body.type == "client" else "forwarder"
    client = _supabase_admin_client()
    try:
        logger.info(f"Creating Supabase user for {body.admin_email}")
        auth_resp = client.auth.admin.create_user(
            {
                "email": body.admin_email,
                "password": body.admin_password,
                "email_confirm": True,
                "app_metadata": {
                    "role": profile_role,
                    "company_id": int(company.id),
                    "company_type": body.type,
                    "company_name": company.name,
                    "is_admin": True,
                },
            }
        )
        logger.info(f"✓ Supabase user created successfully for {body.admin_email}")
    except Exception as exc:
        logger.error(f"✗ Supabase user creation failed for {body.admin_email}: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auth user creation failed: {exc!s}",
        ) from exc

    try:
        uid = _supabase_new_user_id(auth_resp)
        logger.info(f"✓ Extracted user ID: {uid}")
    except HTTPException:
        logger.error(f"✗ Failed to extract user ID from Supabase response")
        await db.rollback()
        raise

    # Create Profile record
    profile = Profile(
        id=UUID(uid),
        company_id=int(company.id),
        name=body.admin_name,
        role=profile_role,
        is_admin=True,
    )
    db.add(profile)

    try:
        logger.info(f"Committing Profile for user {uid} to database...")
        await db.commit()
        logger.info(f"✓ Profile created successfully: id={uid}, company_id={company.id}, name={body.admin_name}")
    except Exception as exc:
        logger.error(f"✗ Failed to commit Profile to database: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {exc!s}",
        ) from exc

    await db.refresh(company)
    return company


@router.patch("/{company_id}/status", response_model=CompanyRead)
async def patch_company_status(
    company_id: int,
    body: CompanyStatusPatch,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> Company:
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    company.is_active = body.is_active
    await db.commit()
    await db.refresh(company)
    return company


@router.post("/{company_id}/users", status_code=status.HTTP_201_CREATED)
async def add_company_user(
    company_id: int,
    body: CompanyUserCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> dict:
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    profile_role = "client" if company.type == "client" else "forwarder"
    client = _supabase_admin_client()
    try:
        logger.info(f"Creating Supabase user for {body.email} in company {company_id}")
        auth_resp = client.auth.admin.create_user(
            {
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
                "app_metadata": {
                    "role": profile_role,
                    "company_id": int(company.id),
                    "company_type": company.type,
                    "company_name": company.name,
                    "is_admin": body.is_admin,
                },
            }
        )
        logger.info(f"✓ Supabase user created successfully for {body.email}")
    except Exception as exc:
        logger.error(f"✗ Supabase user creation failed for {body.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auth user creation failed: {exc!s}",
        ) from exc

    uid = _supabase_new_user_id(auth_resp)
    logger.info(f"✓ Extracted user ID: {uid}")

    profile = Profile(
        id=UUID(uid),
        company_id=int(company.id),
        name=body.name,
        role=profile_role,
        is_admin=body.is_admin,
    )
    db.add(profile)

    try:
        logger.info(f"Committing Profile for user {uid} to database...")
        await db.commit()
        logger.info(f"✓ Profile created successfully: id={uid}, company_id={company.id}, name={body.name}")
    except Exception as exc:
        logger.error(f"✗ Failed to commit Profile to database: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {exc!s}",
        ) from exc

    return {"id": uid, "company_id": int(company.id)}
