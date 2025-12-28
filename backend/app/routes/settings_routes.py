"""User settings API routes."""
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user
from backend.config import require_google_oauth, MissingRequiredSettingError
from backend.models.user_settings import (
    UserSettingsUpdate,
    UserSettingsResponse,
    FolderValidationRequest,
    FolderValidationResponse,
    UsernameCheckResponse,
)
from backend.state.settings_store import (
    get_or_create_settings,
    update_user_settings,
    check_username_available,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings_endpoint(user: AuthUser = Depends(get_current_user)):
    """Get the current user's settings. Creates default settings if none exist."""
    settings = get_or_create_settings(user.user_id)
    return UserSettingsResponse.from_settings(settings)


@router.put("", response_model=UserSettingsResponse)
async def update_settings_endpoint(
    request: Request,
    settings_update: UserSettingsUpdate,
    user: AuthUser = Depends(get_current_user),
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


@router.post("/validate-folder", response_model=FolderValidationResponse)
async def validate_folder_endpoint(
    request: Request,
    folder_request: FolderValidationRequest,
    user: AuthUser = Depends(get_current_user),
):
    """Validate that a Google Drive folder is accessible."""
    # Extract folder ID from URL
    url_pattern = r'https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)'
    match = re.match(url_pattern, folder_request.folder_url)

    if not match:
        return FolderValidationResponse(
            valid=False,
            error="Invalid Google Drive folder URL format"
        )

    folder_id = match.group(1)

    try:
        from googleapiclient.errors import HttpError
        from backend.integrations.google_drive_docs import build_oauth_credentials, _get_drive_service

        # Check OAuth is configured
        try:
            settings = require_google_oauth()
        except MissingRequiredSettingError as e:
            logger.error(f"OAuth not configured: {e}")
            return FolderValidationResponse(
                valid=False,
                folder_id=folder_id,
                accessible=False,
                error="Google Drive not configured. Contact admin to set up OAuth credentials."
            )

        # Build credentials
        try:
            creds = build_oauth_credentials(settings)
            logger.info(f"OAuth credentials built successfully, valid={creds.valid}")
        except Exception as cred_error:
            logger.exception(f"Failed to build OAuth credentials: {type(cred_error).__name__}: {cred_error}")
            return FolderValidationResponse(
                valid=False,
                folder_id=folder_id,
                accessible=False,
                error=f"OAuth credentials error: {type(cred_error).__name__}. Check server logs."
            )

        drive_service = _get_drive_service(creds)

        # Get folder metadata
        folder = drive_service.files().get(
            fileId=folder_id,
            fields="id, name, mimeType"
        ).execute()

        # Verify it's actually a folder
        if folder.get("mimeType") != "application/vnd.google-apps.folder":
            return FolderValidationResponse(
                valid=False,
                folder_id=folder_id,
                error="URL does not point to a folder"
            )

        logger.info(f"Folder validated successfully: {folder.get('name')} ({folder_id})")
        return FolderValidationResponse(
            valid=True,
            folder_id=folder_id,
            folder_name=folder.get("name"),
            accessible=True
        )

    except HttpError as e:
        status_code = e.resp.status if hasattr(e, 'resp') else 'unknown'
        logger.error(f"Drive API HttpError for folder {folder_id}: status={status_code}")

        if status_code == 404:
            error_msg = "Folder not found. Please check the URL and ensure the folder exists."
        elif status_code == 403:
            error_msg = "Cannot access folder. Please share it with your account or make it accessible."
        else:
            error_msg = f"Google Drive API error ({status_code}). Please try again."

        return FolderValidationResponse(
            valid=False,
            folder_id=folder_id,
            accessible=False,
            error=error_msg
        )

    except Exception as e:
        logger.exception(f"Unexpected error validating folder {folder_id}: {type(e).__name__}: {e}")
        return FolderValidationResponse(
            valid=False,
            folder_id=folder_id,
            accessible=False,
            error=f"Validation error: {type(e).__name__}. Check server logs for details."
        )


@router.get("/oauth-status")
async def get_oauth_status(
    request: Request,
    user: AuthUser = Depends(get_current_user),
):
    """Check if Google OAuth is properly configured."""
    from backend.integrations.google_drive_docs import validate_oauth_config

    is_valid, message = validate_oauth_config()
    return {"connected": is_valid, "message": message}


@router.get("/check-username", response_model=UsernameCheckResponse)
async def check_username_availability(
    request: Request,
    username: str,
    user: AuthUser = Depends(get_current_user),
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
