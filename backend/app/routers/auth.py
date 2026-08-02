"""
Auth endpoints — Cognito login, token refresh, and user profile (LogiSight).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_db
from app.models import Profile

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Request / Response Models ───────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: str | None = None
    expires_in: int = 3600
    token_type: str = "Bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: str
    email: str | None = None
    name: str
    role: str | None = None
    company_id: int | None = None
    company_type: str | None = None
    is_admin: bool = False


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """
    Authenticate against Cognito and return JWT tokens.
    """
    from app.services.cognito_client import authenticate_user

    try:
        tokens = authenticate_user(body.email, body.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from e

    return TokenResponse(
        access_token=tokens["access_token"],
        id_token=tokens["id_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in", 3600),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    """
    Refresh access/id tokens using a Cognito refresh token.
    """
    from app.services.cognito_client import refresh_tokens

    try:
        tokens = refresh_tokens(body.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        ) from e

    return TokenResponse(
        access_token=tokens["access_token"],
        id_token=tokens["id_token"],
        refresh_token=None,  # Cognito doesn't return new refresh token on refresh
        expires_in=tokens.get("expires_in", 3600),
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Return the current user's profile (from DB, enriched with JWT claims).
    """
    user_id = current_user["id"]

    # Try to fetch profile from DB for the name
    from uuid import UUID

    try:
        result = await db.execute(
            select(Profile).where(Profile.id == UUID(user_id))
        )
        profile = result.scalar_one_or_none()
    except Exception:
        profile = None

    name = ""
    if profile:
        name = profile.name or ""

    if not name:
        name = current_user.get("email") or "User"

    return UserProfileResponse(
        id=user_id,
        email=current_user.get("email"),
        name=name,
        role=current_user.get("role"),
        company_id=current_user.get("company_id"),
        company_type=current_user.get("company_type"),
        is_admin=current_user.get("is_admin", False),
    )
