"""Centralized input validation utilities.

This module provides validation functions for common input types
to prevent injection attacks and ensure data integrity.
"""
import re
import uuid
from typing import Optional


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate UUID format before using in database queries.

    Args:
        value: String to validate as UUID
        field_name: Name of the field for error messages

    Returns:
        Validated UUID string

    Raises:
        ValidationError: If value is not a valid UUID
    """
    if not value:
        raise ValidationError(f"{field_name} cannot be empty")

    try:
        # Parse and normalize UUID
        parsed = uuid.UUID(value)
        return str(parsed)
    except (ValueError, AttributeError) as e:
        raise ValidationError(f"Invalid {field_name} format: {value}") from e


def validate_youtube_video_id(video_id: str) -> str:
    """
    Validate YouTube video ID format to prevent command injection.

    YouTube video IDs are exactly 11 characters and contain only:
    - Alphanumeric characters (A-Z, a-z, 0-9)
    - Underscores (_)
    - Hyphens (-)

    Args:
        video_id: YouTube video ID to validate

    Returns:
        Validated video ID

    Raises:
        ValidationError: If video ID format is invalid

    Example:
        >>> validate_youtube_video_id("dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> validate_youtube_video_id("'; DROP TABLE--")
        ValidationError: Invalid YouTube video ID format
    """
    if not video_id:
        raise ValidationError("Video ID cannot be empty")

    # Strip whitespace
    video_id = video_id.strip()

    # Check length (YouTube video IDs are exactly 11 characters)
    if len(video_id) != 11:
        raise ValidationError(
            f"Invalid YouTube video ID format: {video_id}. "
            "Video IDs must be exactly 11 characters."
        )

    # Check character set (only alphanumeric, underscore, hyphen)
    if not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        raise ValidationError(
            f"Invalid YouTube video ID format: {video_id}. "
            "Video IDs can only contain letters, numbers, underscores, and hyphens."
        )

    return video_id


def validate_youtube_url(url: str) -> tuple[str, str]:
    """
    Validate and extract video ID from YouTube URL.

    Supports various YouTube URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID

    Args:
        url: YouTube URL to validate

    Returns:
        Tuple of (validated_url, video_id)

    Raises:
        ValidationError: If URL is not a valid YouTube URL
    """
    if not url:
        raise ValidationError("URL cannot be empty")

    url = url.strip()

    # Pattern for various YouTube URL formats
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([A-Za-z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([A-Za-z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Normalize to standard format
            normalized_url = f"https://www.youtube.com/watch?v={video_id}"
            return normalized_url, video_id

    raise ValidationError(
        f"Invalid YouTube URL format: {url}. "
        "Supported formats: youtube.com/watch?v=..., youtu.be/..."
    )


def validate_email(email: str) -> str:
    """
    Basic email format validation.

    Args:
        email: Email address to validate

    Returns:
        Normalized email (lowercase, trimmed)

    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError("Email cannot be empty")

    email = email.strip().lower()

    # Basic email pattern
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValidationError(f"Invalid email format: {email}")

    return email


def sanitize_string(value: str, max_length: int = 1000, field_name: str = "value") -> str:
    """
    Sanitize a string input by trimming and limiting length.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Returns:
        Sanitized string

    Raises:
        ValidationError: If string exceeds max length after trimming
    """
    if not value:
        raise ValidationError(f"{field_name} cannot be empty")

    sanitized = value.strip()

    if len(sanitized) > max_length:
        raise ValidationError(
            f"{field_name} exceeds maximum length of {max_length} characters"
        )

    return sanitized


def validate_subreddit_name(name: str) -> str:
    """
    Validate subreddit name format.

    Reddit subreddit names must:
    - Be 3-21 characters long
    - Contain only alphanumeric characters and underscores
    - Not start with underscore

    Args:
        name: Subreddit name to validate

    Returns:
        Validated subreddit name (without r/ prefix)

    Raises:
        ValidationError: If name format is invalid
    """
    if not name:
        raise ValidationError("Subreddit name cannot be empty")

    # Remove r/ prefix if present
    name = name.strip()
    if name.startswith('r/'):
        name = name[2:]

    # Check length
    if len(name) < 3 or len(name) > 21:
        raise ValidationError(
            f"Invalid subreddit name: {name}. "
            "Names must be 3-21 characters long."
        )

    # Check format
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
        raise ValidationError(
            f"Invalid subreddit name: {name}. "
            "Names must start with a letter and contain only letters, numbers, and underscores."
        )

    return name


# =============================================================================
# Phase 1.5: Video Job Duration/Cost Validation
# =============================================================================

# Cost per minute of video at Gemini 2.5 Flash rates (~$0.015/min estimated)
GEMINI_COST_PER_MINUTE = 0.015
# Pro costs more (~$0.075/min)
GEMINI_PRO_COST_PER_MINUTE = 0.075


class VideoJobValidationResult:
    """Result of video job validation."""

    def __init__(
        self,
        valid: bool,
        error: Optional[str] = None,
        warnings: Optional[list[str]] = None,
        total_duration_minutes: float = 0,
        estimated_cost: float = 0,
    ):
        self.valid = valid
        self.error = error
        self.warnings = warnings or []
        self.total_duration_minutes = total_duration_minutes
        self.estimated_cost = estimated_cost


def validate_video_job_inputs(
    video_urls: list[str],
    video_durations: Optional[list[int]] = None,
    model: str = "gemini-2.5-flash",
    max_videos: int = 10,
    max_total_duration_minutes: int = 300,  # 5 hours
    cost_warning_threshold: float = 5.00,
    cost_hard_cap: float = 10.00,
) -> VideoJobValidationResult:
    """
    Validate video job inputs before submission.

    Phase 1.5: Prevents runaway costs from large video batches.

    Args:
        video_urls: List of YouTube video URLs
        video_durations: Optional list of durations in seconds (if known)
        model: Gemini model to use
        max_videos: Maximum videos per job
        max_total_duration_minutes: Maximum total duration
        cost_warning_threshold: Warn if estimated cost exceeds this
        cost_hard_cap: Block if estimated cost exceeds this

    Returns:
        VideoJobValidationResult with validation status and details
    """
    warnings = []

    # Check video count
    if not video_urls:
        return VideoJobValidationResult(
            valid=False,
            error="No video URLs provided",
        )

    if len(video_urls) > max_videos:
        return VideoJobValidationResult(
            valid=False,
            error=f"Too many videos: {len(video_urls)} exceeds limit of {max_videos}",
        )

    # Validate each URL
    valid_urls = []
    for url in video_urls:
        try:
            validated_url, _ = validate_youtube_url(url)
            valid_urls.append(validated_url)
        except ValidationError as e:
            return VideoJobValidationResult(
                valid=False,
                error=str(e),
            )

    # Calculate duration if provided
    total_duration_minutes = 0.0
    if video_durations:
        total_duration_seconds = sum(video_durations)
        total_duration_minutes = total_duration_seconds / 60

        if total_duration_minutes > max_total_duration_minutes:
            return VideoJobValidationResult(
                valid=False,
                error=f"Total duration {total_duration_minutes:.0f} min exceeds limit of {max_total_duration_minutes} min",
            )

    # Estimate cost
    cost_per_minute = (
        GEMINI_PRO_COST_PER_MINUTE if "pro" in model.lower()
        else GEMINI_COST_PER_MINUTE
    )

    # If no duration provided, estimate ~10 min per video
    if not video_durations:
        total_duration_minutes = len(video_urls) * 10

    estimated_cost = total_duration_minutes * cost_per_minute

    if estimated_cost > cost_hard_cap:
        return VideoJobValidationResult(
            valid=False,
            error=f"Estimated cost ${estimated_cost:.2f} exceeds limit of ${cost_hard_cap:.2f}",
            estimated_cost=estimated_cost,
            total_duration_minutes=total_duration_minutes,
        )

    if estimated_cost > cost_warning_threshold:
        warnings.append(f"Estimated cost: ${estimated_cost:.2f}")

    return VideoJobValidationResult(
        valid=True,
        warnings=warnings,
        total_duration_minutes=total_duration_minutes,
        estimated_cost=estimated_cost,
    )
