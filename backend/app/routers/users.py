"""User profile admin — Super Admin (LogiSight)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db, require_super_admin
from app.models import Profile
from app.schemas import ProfileAdminPatch

router = APIRouter()


@router.patch("/{user_id}/admin")
async def patch_user_admin(
    user_id: UUID,
    body: ProfileAdminPatch,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> dict:
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")
    profile.is_admin = body.is_admin
    await db.commit()
    return {"id": str(user_id), "is_admin": profile.is_admin}
