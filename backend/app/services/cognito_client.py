"""
Amazon Cognito client wrapper for LogiSight user management.
Handles user creation (AdminCreateUser), password setting, and attribute management.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _get_cognito_config() -> tuple[str, str, str]:
    """Return (user_pool_id, client_id, region)."""
    pool_id = os.environ.get("COGNITO_USER_POOL_ID", "")
    client_id = os.environ.get("COGNITO_CLIENT_ID", "")
    region = os.environ.get("COGNITO_REGION", os.environ.get("AWS_REGION", "us-east-1"))

    if not pool_id or not client_id:
        raise RuntimeError(
            "COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID must be set for auth operations"
        )
    return pool_id, client_id, region


def _get_client():
    """Return a boto3 cognito-idp client."""
    _, _, region = _get_cognito_config()
    return boto3.client("cognito-idp", region_name=region)


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    """
    Authenticate a user via Cognito USER_PASSWORD_AUTH flow.

    Returns dict with AccessToken, IdToken, RefreshToken.
    Raises ClientError on invalid credentials.
    """
    pool_id, client_id, _ = _get_cognito_config()
    client = _get_client()

    try:
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
            },
        )

        result = response.get("AuthenticationResult", {})
        return {
            "access_token": result.get("AccessToken", ""),
            "id_token": result.get("IdToken", ""),
            "refresh_token": result.get("RefreshToken", ""),
            "expires_in": result.get("ExpiresIn", 3600),
            "token_type": "Bearer",
        }
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("NotAuthorizedException", "UserNotFoundException"):
            raise ValueError("Invalid email or password") from e
        if error_code == "UserNotConfirmedException":
            raise ValueError("Account not confirmed. Please check your email.") from e
        logger.error(f"Cognito auth error: {error_code} — {e}")
        raise


def refresh_tokens(refresh_token: str) -> dict[str, Any]:
    """Refresh access/id tokens using a refresh token."""
    pool_id, client_id, _ = _get_cognito_config()
    client = _get_client()

    try:
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refresh_token,
            },
        )
        result = response.get("AuthenticationResult", {})
        return {
            "access_token": result.get("AccessToken", ""),
            "id_token": result.get("IdToken", ""),
            "expires_in": result.get("ExpiresIn", 3600),
            "token_type": "Bearer",
        }
    except ClientError as e:
        logger.error(f"Cognito refresh error: {e}")
        raise ValueError("Invalid or expired refresh token") from e


def create_user(
    email: str,
    password: str,
    role: str,
    company_id: int,
    company_type: str,
    company_name: str,
    is_admin: bool = False,
    name: str = "",
) -> str:
    """
    Create a Cognito user with custom attributes and set their password.
    Returns the Cognito user sub (UUID).
    """
    pool_id, _, _ = _get_cognito_config()
    client = _get_client()

    user_attributes = [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:role", "Value": role},
        {"Name": "custom:company_id", "Value": str(company_id)},
        {"Name": "custom:company_type", "Value": company_type},
        {"Name": "custom:company_name", "Value": company_name},
        {"Name": "custom:is_admin", "Value": "true" if is_admin else "false"},
    ]

    if name:
        user_attributes.append({"Name": "name", "Value": name})

    try:
        # Create user with temporary password
        response = client.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=user_attributes,
            MessageAction="SUPPRESS",  # Don't send welcome email
        )

        # Set permanent password immediately
        client.admin_set_user_password(
            UserPoolId=pool_id,
            Username=email,
            Password=password,
            Permanent=True,
        )

        # Extract sub (user ID)
        user_sub = ""
        for attr in response.get("User", {}).get("Attributes", []):
            if attr["Name"] == "sub":
                user_sub = attr["Value"]
                break

        if not user_sub:
            raise RuntimeError("Cognito did not return a user sub")

        logger.info(f"✓ Cognito user created: {email} (sub={user_sub})")
        return user_sub

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "UsernameExistsException":
            raise ValueError(f"User with email {email} already exists") from e
        logger.error(f"Cognito create user error: {error_code} — {e}")
        raise


def admin_get_user(email: str) -> dict[str, Any]:
    """Fetch user details from Cognito by email (username)."""
    pool_id, _, _ = _get_cognito_config()
    client = _get_client()

    try:
        response = client.admin_get_user(
            UserPoolId=pool_id,
            Username=email,
        )
        attrs = {}
        for attr in response.get("UserAttributes", []):
            attrs[attr["Name"]] = attr["Value"]
        return attrs
    except ClientError as e:
        logger.error(f"Cognito get user error: {e}")
        raise
