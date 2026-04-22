"""
Shared FastAPI dependencies for LogiSight: async DB session and Supabase JWT auth.
"""

from __future__ import annotations

import os
import time
from typing import Any, TypedDict

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_db

# Re-export for routers: `from app.dependencies import get_db, get_current_user`
__all__ = [
    "get_db",
    "get_current_user",
    "security",
    "CurrentUser",
    "require_super_admin",
    "require_client",
    "require_forwarder",
    "require_company_scope",
]

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

security = HTTPBearer(auto_error=True)

# In-memory JWKS cache (RS256 keys rotate rarely)
_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at: float = 0.0
_JWKS_TTL_SECONDS = 300.0


class CurrentUser(TypedDict):
    """Claims extracted from the Supabase access token for request scoping."""

    id: str
    email: str | None
    role: str | None  # super_admin | client | forwarder
    company_id: int | None
    company_type: str | None
    is_admin: bool


def _issuer() -> str:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not set")
    return f"{SUPABASE_URL}/auth/v1"


def _coerce_company_id(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _coerce_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in ("true", "1", 1):
        return True
    return False


async def get_jwks() -> dict[str, Any]:
    """Fetch Supabase JWKS (cached)."""
    global _jwks_cache, _jwks_cache_expires_at

    now = time.monotonic()
    if _jwks_cache is not None and now < _jwks_cache_expires_at:
        return _jwks_cache

    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not set")

    url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    headers: dict[str, str] = {}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
        headers["Authorization"] = f"Bearer {SUPABASE_ANON_KEY}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    _jwks_cache = data
    _jwks_cache_expires_at = now + _JWKS_TTL_SECONDS
    return data


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Verify Supabase RS256 JWT via JWKS and return role, company_id, and related claims.
    """
    token = credentials.credentials

    try:
        jwks = await get_jwks()
        keys = jwks.get("keys") or []

        # Build public keys supporting both RS256 and ES256
        public_keys = []
        for k in keys:
            kty = k.get("kty")
            if kty == "RSA":
                public_keys.append(("RS256", jwt.algorithms.RSAAlgorithm.from_jwk(k)))
            elif kty == "EC":
                public_keys.append(("ES256", jwt.algorithms.ECAlgorithm.from_jwk(k)))

        if not public_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        payload: dict[str, Any] | None = None
        last_error: Exception | None = None
        iss = _issuer()

        for alg, key in public_keys:
            try:
                payload = jwt.decode(
                    token,
                    key=key,
                    algorithms=[alg],
                    audience="authenticated",
                    issuer=iss,
                    options={"require": ["sub", "exp"]},
                )
                break
            except jwt.InvalidTokenError as exc:
                last_error = exc
                continue

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from last_error

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from None

    app_meta = payload.get("app_metadata") or {}
    if not isinstance(app_meta, dict):
        app_meta = {}
    user_meta = payload.get("user_metadata") or {}
    if not isinstance(user_meta, dict):
        user_meta = {}

    role = app_meta.get("role") or user_meta.get("role")
    if isinstance(role, str):
        role = role.strip() or None
    else:
        role = None

    raw_company_id = app_meta.get("company_id")
    if raw_company_id is None:
        raw_company_id = user_meta.get("company_id")
    company_id = _coerce_company_id(raw_company_id)

    company_type = app_meta.get("company_type") or user_meta.get("company_type")
    if isinstance(company_type, str):
        company_type = company_type.strip() or None
    else:
        company_type = None

    is_admin = _coerce_bool(app_meta.get("is_admin", False))

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    return CurrentUser(
        id=sub,
        email=payload.get("email") if isinstance(payload.get("email"), str) else None,
        role=role,
        company_id=company_id,
        company_type=company_type,
        is_admin=is_admin,
    )


async def require_super_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


async def require_client(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.get("role") != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client role required",
        )
    return current_user


async def require_forwarder(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.get("role") != "forwarder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forwarder role required",
        )
    return current_user


async def require_company_scope(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Non-super-admin callers must have a company_id in JWT."""
    if current_user.get("role") == "super_admin":
        return current_user
    if current_user.get("company_id") is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company scope required",
        )
    return current_user
