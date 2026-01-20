"""User settings API routes.

Updated 2026-01-19: Google Drive endpoints deprecated (validate-folder, oauth-status).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger

from backend.app.rate_limiter import limiter, RATE_LIMITS
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.models.user_settings import (
    UserSettingsUpdate,
    UserSettingsResponse,
    UsernameCheckResponse,
)
from backend.state.settings_store import (
    get_or_create_settings,
    update_user_settings,
    check_username_available,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings_endpoint(user: AuthUser = Depends(get_active_user)):
    """Get the current user's settings. Creates default settings if none exist."""
    settings = get_or_create_settings(user.user_id)
    return UserSettingsResponse.from_settings(settings)


@router.put("", response_model=UserSettingsResponse)
@limiter.limit(RATE_LIMITS["settings_update"])
async def update_settings_endpoint(
    request: Request,
    settings_update: UserSettingsUpdate,
    user: AuthUser = Depends(get_active_user),
):
    """Update the current user's settings. Only provided fields will be updated."""
    updated = update_user_settings(user.user_id, settings_update)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update settings")

    logger.info(
        "Settings updated",
        extra={
            "user_id": user.user_id,
            "updated_fields": list(settings_update.model_dump(exclude_none=True).keys()),
            "event": "settings_updated",
        }
    )

    return UserSettingsResponse.from_settings(updated)


@router.post("/validate-folder")
async def validate_folder_endpoint(request: Request):
    """DEPRECATED: Google Drive integration removed (2026-01-19)."""
    return JSONResponse(
        status_code=410,
        content={
            "error": "Google Drive integration has been removed",
            "message": "This endpoint is deprecated. Use Supabase Storage for exports.",
            "deprecated_date": "2026-01-19",
        }
    )


@router.get("/oauth-status")
async def get_oauth_status(request: Request):
    """DEPRECATED: Google Drive integration removed (2026-01-19)."""
    return JSONResponse(
        status_code=410,
        content={
            "error": "Google Drive integration has been removed",
            "message": "OAuth status check is no longer available.",
            "deprecated_date": "2026-01-19",
        }
    )


@router.get("/check-username", response_model=UsernameCheckResponse)
@limiter.limit(RATE_LIMITS["settings_check_username"])
async def check_username_availability(
    request: Request,
    username: str,
    user: AuthUser = Depends(get_active_user),
):
    """Check if a username is available."""
    # Normalize username
    username = username.strip().lower()

    # Validate format
    if len(username) < 3:
        return UsernameCheckResponse(
            available=False,
            username=username,
            error="Username must be at least 3 characters"
        )

    if len(username) > 30:
        return UsernameCheckResponse(
            available=False,
            username=username,
            error="Username must be at most 30 characters"
        )

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return UsernameCheckResponse(
            available=False,
            username=username,
            error="Username must start with a letter and contain only letters, numbers, and underscores"
        )

    is_available = check_username_available(username, user.user_id)

    return UsernameCheckResponse(
        available=is_available,
        username=username,
        error=None if is_available else "Username is already taken"
    )
