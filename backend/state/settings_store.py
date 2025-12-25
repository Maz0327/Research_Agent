"""Settings store for user preferences."""
from typing import Any, Optional

import httpx
from loguru import logger

from backend.config import get_settings
from backend.models.user_settings import UserSettings, UserSettingsUpdate, PipelineType, SortOrder, DriveFolder
from backend.utils.error_handling import sanitize_error_message


# Constants
SUPABASE_API_TIMEOUT = 5.0


def _rest_base_url() -> str:
    """Base URL for Supabase PostgREST."""
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    base_url = str(settings.supabase_url)
    return base_url.rstrip("/") + "/rest/v1"


def _headers() -> dict[str, str]:
    """Headers required by Supabase REST."""
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _row_to_settings(row: dict[str, Any]) -> UserSettings:
    """Convert database row to UserSettings model."""
    # Parse drive_folders from JSONB
    drive_folders = []
    raw_folders = row.get("drive_folders") or []
    if isinstance(raw_folders, list):
        for folder in raw_folders:
            if isinstance(folder, dict):
                drive_folders.append(DriveFolder(
                    folder_id=folder.get("folder_id", ""),
                    folder_name=folder.get("folder_name"),
                    is_default=folder.get("is_default", False),
                    added_at=folder.get("added_at"),
                ))

    return UserSettings(
        id=row.get("id"),
        user_id=row.get("user_id"),
        username=row.get("username"),
        drive_folders=drive_folders,
        default_folder_id=row.get("default_folder_id"),
        drive_folder_id=row.get("drive_folder_id"),
        use_custom_folder=row.get("use_custom_folder", False),
        default_pipeline=PipelineType(row.get("default_pipeline", "investigation")),
        auto_extract_claims=row.get("auto_extract_claims", True),
        max_sources=row.get("max_sources", 25),
        email_on_complete=row.get("email_on_complete", True),
        email_on_failure=row.get("email_on_failure", True),
        email_summary=row.get("email_summary", False),
        jobs_per_page=row.get("jobs_per_page", 10),
        default_sort=SortOrder(row.get("default_sort", "newest")),
        show_progress_details=row.get("show_progress_details", True),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def get_user_settings(user_id: str) -> Optional[UserSettings]:
    """
    Get user settings from database.
    
    Args:
        user_id: User's UUID
        
    Returns:
        UserSettings if found, None otherwise
    """
    url = _rest_base_url() + "/user_settings"
    headers = _headers()
    params = {
        "user_id": f"eq.{user_id}",
        "limit": 1,
    }
    
    with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
        resp = client.get(url, headers=headers, params=params)
    
    if resp.status_code == 404:
        return None
    
    try:
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(
            "Failed to fetch settings for user %s: %s",
            user_id,
            sanitize_error_message(e),
        )
        raise
    
    data = resp.json()
    if not data:
        return None
    
    return _row_to_settings(data[0])


def create_default_settings(user_id: str) -> UserSettings:
    """
    Create default settings for a new user.
    
    Args:
        user_id: User's UUID
        
    Returns:
        Created UserSettings
    """
    url = _rest_base_url() + "/user_settings"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    
    payload = {
        "user_id": user_id,
        # All other fields use database defaults
    }
    
    logger.info("Creating default settings for user %s", user_id)
    
    with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
        resp = client.post(url, headers=headers, json=payload)
    
    try:
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(
            "Failed to create settings for user %s: %s",
            user_id,
            sanitize_error_message(e),
        )
        raise
    
    data = resp.json()
    if isinstance(data, list):
        if not data:
            raise RuntimeError("Supabase returned empty list when creating settings")
        data = data[0]
    
    return _row_to_settings(data)


def get_or_create_settings(user_id: str) -> UserSettings:
    """
    Get user settings, creating defaults if not found.
    
    Args:
        user_id: User's UUID
        
    Returns:
        UserSettings (existing or newly created)
    """
    settings = get_user_settings(user_id)
    if settings:
        return settings
    
    return create_default_settings(user_id)


def update_user_settings(user_id: str, updates: UserSettingsUpdate) -> Optional[UserSettings]:
    """
    Update user settings.
    
    Args:
        user_id: User's UUID
        updates: Fields to update
        
    Returns:
        Updated UserSettings or None if not found
    """
    # Ensure settings exist
    existing = get_or_create_settings(user_id)
    
    # Build update payload (only non-None fields)
    payload = {}
    for field, value in updates.model_dump(exclude_none=True).items():
        if isinstance(value, PipelineType):
            payload[field] = value.value
        elif isinstance(value, SortOrder):
            payload[field] = value.value
        elif field == "drive_folders" and isinstance(value, list):
            # Convert DriveFolder objects to dicts for JSONB storage
            payload[field] = [
                {
                    "folder_id": f.get("folder_id") if isinstance(f, dict) else f.folder_id,
                    "folder_name": f.get("folder_name") if isinstance(f, dict) else f.folder_name,
                    "is_default": f.get("is_default", False) if isinstance(f, dict) else f.is_default,
                    "added_at": str(f.get("added_at")) if isinstance(f, dict) and f.get("added_at") else (str(f.added_at) if hasattr(f, 'added_at') and f.added_at else None),
                }
                for f in value
            ]
        else:
            payload[field] = value
    
    if not payload:
        # No updates, return existing
        return existing
    
    url = _rest_base_url() + "/user_settings"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    params = {"user_id": f"eq.{user_id}"}
    
    logger.info("Updating settings for user %s: %s", user_id, list(payload.keys()))
    
    with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
        resp = client.patch(url, headers=headers, params=params, json=payload)
    
    if resp.status_code == 404:
        logger.warning("Settings not found for user %s", user_id)
        return None
    
    try:
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(
            "Failed to update settings for user %s: %s",
            user_id,
            sanitize_error_message(e),
        )
        raise
    
    data = resp.json()
    if isinstance(data, list):
        if not data:
            return None
        data = data[0]

    return _row_to_settings(data)


def check_username_available(username: str, current_user_id: str) -> bool:
    """
    Check if a username is available.

    A username is available if:
    - No user has this username, OR
    - The only user with this username is the current user

    Args:
        username: Username to check (should be lowercase)
        current_user_id: The user making the request

    Returns:
        True if username is available for the current user
    """
    url = _rest_base_url() + "/user_settings"
    headers = _headers()
    params = {
        "username": f"eq.{username.lower()}",
        "select": "user_id",
        "limit": 1,
    }

    try:
        with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
            resp = client.get(url, headers=headers, params=params)

        resp.raise_for_status()
        data = resp.json()

        if not data:
            # No one has this username
            return True

        # Check if the existing username belongs to current user
        existing_user_id = data[0].get("user_id")
        return existing_user_id == current_user_id

    except httpx.HTTPError as e:
        logger.error(
            "Failed to check username availability: %s",
            sanitize_error_message(e),
        )
        # On error, return False to prevent duplicate usernames
        return False
