"""
Companies and user admin — Super Admin (LogiSight).
Uses Amazon Cognito for user creation (replacing Supabase).
"""

from __future__ import annotations

import logging
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

    # Create user in Cognito
    from app.services.cognito_client import create_user

    try:
        logger.info(f"Creating Cognito user for {body.admin_email}")
        user_sub = create_user(
            email=body.admin_email,
            password=body.admin_password,
            role=profile_role,
            company_id=int(company.id),
            company_type=body.type,
            company_name=company.name,
            is_admin=True,
            name=body.admin_name,
        )
        logger.info(f"✓ Cognito user created: {body.admin_email} (sub={user_sub})")
    except ValueError as exc:
        logger.error(f"✗ Cognito user creation failed for {body.admin_email}: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auth user creation failed: {exc!s}",
        ) from exc
    except Exception as exc:
        logger.error(f"✗ Cognito user creation failed for {body.admin_email}: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auth user creation failed: {exc!s}",
        ) from exc

    # Create Profile record in the database
    profile = Profile(
        id=UUID(user_sub),
        company_id=int(company.id),
        name=body.admin_name,
        role=profile_role,
        is_admin=True,
    )
    db.add(profile)

    try:
        logger.info(f"Committing Profile for user {user_sub} to database...")
        await db.commit()
        logger.info(
            f"✓ Profile created: id={user_sub}, company_id={company.id}, name={body.admin_name}"
        )
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

    from app.services.cognito_client import create_user

    try:
        logger.info(f"Creating Cognito user for {body.email} in company {company_id}")
        user_sub = create_user(
            email=body.email,
            password=body.password,
            role=profile_role,
            company_id=int(company.id),
            company_type=company.type,
            company_name=company.name,
            is_admin=body.is_admin,
            name=body.name,
        )
        logger.info(f"✓ Cognito user created: {body.email} (sub={user_sub})")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auth user creation failed: {exc!s}",
        ) from exc
    except Exception as exc:
        logger.error(f"✗ Cognito user creation failed for {body.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auth user creation failed: {exc!s}",
        ) from exc

    profile = Profile(
        id=UUID(user_sub),
        company_id=int(company.id),
        name=body.name,
        role=profile_role,
        is_admin=body.is_admin,
    )
    db.add(profile)

    try:
        logger.info(f"Committing Profile for user {user_sub} to database...")
        await db.commit()
        logger.info(
            f"✓ Profile created: id={user_sub}, company_id={company.id}, name={body.name}"
        )
    except Exception as exc:
        logger.error(f"✗ Failed to commit Profile to database: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {exc!s}",
        ) from exc

    return {"id": user_sub, "company_id": int(company.id)}
