"""
Supabase JWT authentication module.

This module provides JWT verification for Supabase Auth tokens.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from loguru import logger

from backend.config import get_settings


@dataclass
class AuthUser:
    """Authenticated user extracted from JWT token."""

    user_id: str  # UUID from Supabase auth.users
    email: Optional[str] = None
    role: str = "authenticated"


class AuthError(Exception):
    """Authentication error."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def verify_jwt(token: str) -> AuthUser:
    """
    Verify a Supabase JWT token and extract user info.

    Args:
        token: JWT token from Authorization header (without "Bearer " prefix)

    Returns:
        AuthUser with user_id and email

    Raises:
        AuthError: If token is invalid, expired, or missing required claims
    """
    settings = get_settings()

    if not settings.supabase_jwt_secret:
        raise AuthError("JWT verification not configured", status_code=500)

    try:
        # Decode and verify the JWT
        # Supabase uses HS256 algorithm by default
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,  # Configurable audience
        )

        # Extract user ID from 'sub' claim
        user_id = payload.get("sub")
        if not user_id:
            raise AuthError("Token missing user ID (sub claim)")

        # Extract email from claims (may be in different locations)
        email = payload.get("email")
        if not email:
            # Try user_metadata
            user_metadata = payload.get("user_metadata", {})
            email = user_metadata.get("email")

        # Extract role (default to "authenticated")
        role = payload.get("role", "authenticated")

        logger.debug(f"Authenticated user: {user_id[:8]}... (role: {role})")

        return AuthUser(
            user_id=user_id,
            email=email,
            role=role,
        )

    except ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise AuthError("Token expired")

    except InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise AuthError("Invalid token")


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer eyJ...")

    Returns:
        JWT token string, or None if not present or invalid format
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
