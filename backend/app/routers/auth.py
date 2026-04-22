"""
Auth helpers — Supabase JWT is verified in app.dependencies.get_current_user.
"""

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.get("/me")
async def read_current_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Return claims from the validated Supabase access token (for debugging and clients)."""
    return current_user
