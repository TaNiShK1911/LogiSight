"""
Add a test endpoint to debug authentication
"""
from fastapi import APIRouter, Depends, Request
from app.dependencies import get_current_user, CurrentUser, security
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()

@router.get("/debug/auth-test")
async def test_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Test endpoint to see what auth headers we're receiving"""
    headers = dict(request.headers)

    return {
        "has_authorization": "authorization" in headers,
        "authorization_preview": headers.get("authorization", "")[:50] if "authorization" in headers else None,
        "credentials_scheme": credentials.scheme if credentials else None,
        "credentials_preview": credentials.credentials[:50] if credentials else None,
        "all_headers": {k: v[:100] for k, v in headers.items()},
    }

@router.get("/debug/auth-verify")
async def verify_auth(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Test endpoint that requires authentication"""
    return {
        "authenticated": True,
        "user": current_user,
    }
