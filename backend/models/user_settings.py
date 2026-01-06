"""User settings models for per-user configuration."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
import re

from pydantic import BaseModel, Field, field_validator


class PipelineType(str, Enum):
    """Available research pipeline types."""
    QUICK = "quick"
    FULL = "full"
    BREAKING_NEWS = "breaking_news"
    INVESTIGATION = "investigation"
    PROFILE = "profile"
    CONTROVERSY = "controversy"


class SortOrder(str, Enum):
    """Available sort orders for job listing."""
    NEWEST = "newest"
    OLDEST = "oldest"
    STATUS = "status"


class DriveFolder(BaseModel):
    """A user's Google Drive folder configuration."""
    folder_id: str
    folder_name: Optional[str] = None
    is_default: bool = False
    added_at: Optional[datetime] = None


class UserSettings(BaseModel):
    """User settings stored in database."""

    id: Optional[str] = None
    user_id: str

    # Profile Settings
    username: Optional[str] = Field(default=None, min_length=3, max_length=30)

    # Google Drive Settings - Multi-folder support (up to 3)
    drive_folders: List[DriveFolder] = Field(default_factory=list)
    default_folder_id: Optional[str] = None

    # Legacy fields (kept for backwards compatibility)
    drive_folder_id: Optional[str] = None
    use_custom_folder: bool = False

    # Pipeline Settings
    default_pipeline: PipelineType = PipelineType.INVESTIGATION
    auto_extract_claims: bool = True
    max_sources: int = Field(default=25, ge=5, le=50)
    
    # Notification Settings
    email_on_complete: bool = True
    email_on_failure: bool = True
    email_summary: bool = False
    
    # Display Settings
    jobs_per_page: int = Field(default=10, ge=5, le=25)
    default_sort: SortOrder = SortOrder.NEWEST
    show_progress_details: bool = True

    # Webhook Settings
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_events: List[str] = Field(default_factory=list)  # Empty = all events

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserSettingsUpdate(BaseModel):
    """Request model for updating user settings."""

    # Profile Settings
    username: Optional[str] = Field(default=None, min_length=3, max_length=30)

    # Google Drive Settings - Multi-folder support
    drive_folders: Optional[List[DriveFolder]] = None
    default_folder_id: Optional[str] = None

    # Legacy fields (kept for backwards compatibility)
    drive_folder_id: Optional[str] = None
    use_custom_folder: Optional[bool] = None

    # Pipeline Settings
    default_pipeline: Optional[PipelineType] = None
    auto_extract_claims: Optional[bool] = None
    max_sources: Optional[int] = Field(default=None, ge=5, le=50)

    # Notification Settings
    email_on_complete: Optional[bool] = None
    email_on_failure: Optional[bool] = None
    email_summary: Optional[bool] = None

    # Display Settings
    jobs_per_page: Optional[int] = Field(default=None, ge=5, le=25)
    default_sort: Optional[SortOrder] = None
    show_progress_details: Optional[bool] = None

    # Webhook Settings
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_events: Optional[List[str]] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Only allow alphanumeric and underscores
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("Username must start with a letter and contain only letters, numbers, and underscores")

        return v.lower()

    @field_validator('drive_folders')
    @classmethod
    def validate_drive_folders(cls, v: Optional[List[DriveFolder]]) -> Optional[List[DriveFolder]]:
        """Validate drive folders list."""
        if v is None:
            return v

        if len(v) > 3:
            raise ValueError("Maximum 3 folders allowed")

        # Ensure at most one default
        defaults = [f for f in v if f.is_default]
        if len(defaults) > 1:
            raise ValueError("Only one folder can be set as default")

        return v

    @field_validator('drive_folder_id')
    @classmethod
    def validate_drive_folder_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate Google Drive folder ID format."""
        if v is None:
            return v

        # Remove whitespace
        v = v.strip()

        if not v:
            return None

        # If it's a URL, extract the folder ID
        url_pattern = r'https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)'
        match = re.match(url_pattern, v)
        if match:
            return match.group(1)

        # Otherwise, validate as a folder ID directly
        id_pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(id_pattern, v):
            raise ValueError("Invalid folder ID format. Use a Google Drive folder URL or ID.")

        return v


class DriveFolderResponse(BaseModel):
    """Response model for a drive folder."""
    folder_id: str
    folder_name: Optional[str] = None
    folder_url: str
    is_default: bool = False
    added_at: Optional[datetime] = None


class UserSettingsResponse(BaseModel):
    """Response model for user settings API."""

    # Profile Settings
    username: Optional[str] = None

    # Google Drive Settings - Multi-folder support
    drive_folders: List[DriveFolderResponse] = Field(default_factory=list)
    default_folder_id: Optional[str] = None

    # Legacy fields (kept for backwards compatibility)
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None  # Derived from drive_folder_id
    use_custom_folder: bool = False

    # Pipeline Settings
    default_pipeline: str = "investigation"
    auto_extract_claims: bool = True
    max_sources: int = 25

    # Notification Settings
    email_on_complete: bool = True
    email_on_failure: bool = True
    email_summary: bool = False

    # Display Settings
    jobs_per_page: int = 10
    default_sort: str = "newest"
    show_progress_details: bool = True

    # Webhook Settings
    webhook_url: Optional[str] = None
    webhook_events: List[str] = Field(default_factory=list)
    webhook_configured: bool = False  # True if webhook_url is set

    @classmethod
    def from_settings(cls, settings: UserSettings) -> "UserSettingsResponse":
        """Create response from UserSettings model."""
        # Build drive folder responses
        drive_folders_response = []
        for folder in settings.drive_folders:
            drive_folders_response.append(DriveFolderResponse(
                folder_id=folder.folder_id,
                folder_name=folder.folder_name,
                folder_url=f"https://drive.google.com/drive/folders/{folder.folder_id}",
                is_default=folder.is_default,
                added_at=folder.added_at,
            ))

        # Legacy drive_folder_url
        drive_folder_url = None
        if settings.drive_folder_id:
            drive_folder_url = f"https://drive.google.com/drive/folders/{settings.drive_folder_id}"

        return cls(
            username=settings.username,
            drive_folders=drive_folders_response,
            default_folder_id=settings.default_folder_id,
            drive_folder_id=settings.drive_folder_id,
            drive_folder_url=drive_folder_url,
            use_custom_folder=settings.use_custom_folder,
            default_pipeline=settings.default_pipeline.value,
            auto_extract_claims=settings.auto_extract_claims,
            max_sources=settings.max_sources,
            email_on_complete=settings.email_on_complete,
            email_on_failure=settings.email_on_failure,
            email_summary=settings.email_summary,
            jobs_per_page=settings.jobs_per_page,
            default_sort=settings.default_sort.value,
            show_progress_details=settings.show_progress_details,
            webhook_url=settings.webhook_url,
            webhook_events=settings.webhook_events,
            webhook_configured=bool(settings.webhook_url),
        )


class FolderValidationRequest(BaseModel):
    """Request to validate a Google Drive folder."""
    folder_url: str
    
    @field_validator('folder_url')
    @classmethod
    def validate_folder_url(cls, v: str) -> str:
        """Validate folder URL format."""
        v = v.strip()
        
        url_pattern = r'^https?://drive\.google\.com/drive/(?:u/\d+/)?folders/[a-zA-Z0-9_-]+'
        if not re.match(url_pattern, v):
            raise ValueError("Invalid Google Drive folder URL")
        
        return v


class FolderValidationResponse(BaseModel):
    """Response from folder validation."""
    valid: bool
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    accessible: bool = False
    error: Optional[str] = None


class UsernameCheckRequest(BaseModel):
    """Request to check username availability."""
    username: str = Field(min_length=3, max_length=30)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be empty")

        # Only allow alphanumeric and underscores
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("Username must start with a letter and contain only letters, numbers, and underscores")

        return v.lower()


class UsernameCheckResponse(BaseModel):
    """Response from username availability check."""
    available: bool
    username: str
    error: Optional[str] = None
