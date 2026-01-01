"""
User ban verification module.

Provides functions to check if a user is banned and a FastAPI dependency
that combines authentication with ban checking.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Header, Request
from loguru import logger
from supabase import create_client, Client

from backend.auth import AuthUser, extract_token_from_header, verify_jwt, AuthError
from backend.config import get_settings


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client for ban checks."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


async def check_user_banned(user_id: str) -> bool:
    """
    Check if a user is banned via the user_settings table.

    Args:
        user_id: UUID of the user to check

    Returns:
        True if user is banned, False otherwise
    """
    client = get_supabase_client()
    if not client:
        # If Supabase is not configured, assume not banned
        logger.debug("Supabase not configured, skipping ban check")
        return False

    try:
        result = client.table("user_settings").select("is_banned").eq(
            "user_id", user_id
        ).execute()

        if result.data and len(result.data) > 0:
            is_banned = result.data[0].get("is_banned", False)
            if is_banned:
                logger.info(
                    "Banned user attempted access",
                    event="ban_check_blocked",
                    user_id=user_id[:8],
                )
            return is_banned

        # No user_settings record means user is not banned
        return False

    except Exception as e:
        logger.error(f"Error checking ban status: {e}")
        # Fail open (allow access) on error to prevent lockout
        # Log for security monitoring
        logger.warning(
            "Ban check failed, allowing access",
            event="ban_check_error",
            user_id=user_id[:8],
            error=str(e),
        )
        return False


async def get_active_user(
    authorization: Optional[str] = Header(None),
    request: Request = None,
) -> AuthUser:
    """
    FastAPI dependency to get authenticated user and verify not banned.

    This combines authentication verification with ban status checking.
    Use this instead of get_current_user for routes that should block
    banned users.

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_active_user)):
            return {"user_id": user.user_id}

    Args:
        authorization: Authorization header (injected by FastAPI)

    Returns:
        AuthUser if authenticated and not banned

    Raises:
        HTTPException: 401 if not authenticated, 403 if banned
    """
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = verify_jwt(token)
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"} if e.status_code == 401 else None,
        )

    # Expose user_id for rate limiting
    try:
        if request is not None:
            request.state.user_id = user.user_id
    except Exception:
        pass

    # Check if user is banned
    if await check_user_banned(user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Contact support for assistance.",
        )

    return user


async def get_optional_active_user(
    authorization: Optional[str] = Header(None),
    request: Request = None,
) -> Optional[AuthUser]:
    """
    FastAPI dependency to optionally get active (non-banned) user.

    Similar to get_optional_user but also checks ban status.
    Returns None for both unauthenticated users and banned users.

    Usage:
        @app.get("/public")
        async def public_route(
            user: Optional[AuthUser] = Depends(get_optional_active_user)
        ):
            if user:
                return {"message": f"Hello, {user.email}!"}
            return {"message": "Hello, guest!"}

    Args:
        authorization: Authorization header (injected by FastAPI)

    Returns:
        AuthUser if authenticated and not banned, None otherwise
    """
    token = extract_token_from_header(authorization)
    if not token:
        return None

    try:
        user = verify_jwt(token)
        try:
            if request is not None and user is not None:
                request.state.user_id = user.user_id
        except Exception:
            pass
    except AuthError:
        return None

    # Check if user is banned
    if await check_user_banned(user.user_id):
        return None

    return user
