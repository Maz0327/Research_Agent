"""
FastAPI dependency injection for authentication.

Provides dependencies for protected routes that require authentication.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Header

from backend.auth import AuthError, AuthUser, extract_token_from_header, verify_jwt


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> AuthUser:
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.user_id}

    Args:
        authorization: Authorization header (injected by FastAPI)

    Returns:
        AuthUser with user_id, email, and role

    Raises:
        HTTPException: 401 if not authenticated, 500 for server errors
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
        return user
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"} if e.status_code == 401 else None,
        )


async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[AuthUser]:
    """
    FastAPI dependency to optionally get the current user.

    Use this for routes that work with or without authentication,
    but provide additional features when authenticated.

    Usage:
        @app.get("/public")
        async def public_route(user: Optional[AuthUser] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.email}!"}
            return {"message": "Hello, guest!"}

    Args:
        authorization: Authorization header (injected by FastAPI)

    Returns:
        AuthUser if authenticated, None otherwise
    """
    token = extract_token_from_header(authorization)
    if not token:
        return None

    try:
        return verify_jwt(token)
    except AuthError:
        # For optional auth, we silently return None on errors
        return None


async def require_admin(
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """
    FastAPI dependency that requires admin privileges.

    Usage:
        @app.get("/admin/endpoint")
        async def admin_route(admin: AuthUser = Depends(require_admin)):
            return {"admin_id": admin.user_id}

    Args:
        user: The authenticated user (injected via get_current_user)

    Returns:
        AuthUser if user has admin privileges

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    from backend.auth.admin import is_admin

    if not is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return user
