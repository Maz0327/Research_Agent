"""
Error logging service for tracking and categorizing errors.

Logs errors to the database with user-friendly messages and technical details.
"""
from enum import Enum
from typing import Optional
import traceback

from loguru import logger

from backend.utils.datetime_utils import utc_now_iso


class ErrorCategory(str, Enum):
    """Categories for classifying errors."""
    API_ERROR = "api_error"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    AUTH = "auth"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    UNKNOWN = "unknown"


# Map technical error patterns to user-friendly messages and categories
ERROR_MAPPINGS = [
    ("OpenAI API", "The AI service is temporarily unavailable. Please try again in a few minutes.", ErrorCategory.EXTERNAL_SERVICE),
    ("rate limit", "The system is busy. Your request will be processed shortly.", ErrorCategory.EXTERNAL_SERVICE),
    ("SIGKILL", "Processing was interrupted due to resource limits. Try with fewer sources.", ErrorCategory.MEMORY),
    ("signal 9", "Processing was interrupted due to resource limits. Try with fewer sources.", ErrorCategory.MEMORY),
    ("MemoryError", "Processing was interrupted. Try with a smaller research scope.", ErrorCategory.MEMORY),
    ("memory", "Processing was interrupted. Try with a smaller research scope.", ErrorCategory.MEMORY),
    ("OOM", "Processing was interrupted due to memory limits.", ErrorCategory.MEMORY),
    ("timeout", "The request took too long. Please try again.", ErrorCategory.TIMEOUT),
    ("timed out", "The request took too long. Please try again.", ErrorCategory.TIMEOUT),
    ("TimeoutError", "The request took too long. Please try again.", ErrorCategory.TIMEOUT),
    ("authentication", "Your session has expired. Please log in again.", ErrorCategory.AUTH),
    ("401", "Your session has expired. Please log in again.", ErrorCategory.AUTH),
    ("403", "You don't have permission to perform this action.", ErrorCategory.AUTH),
    ("Perplexity", "The research service is temporarily unavailable. Please try again.", ErrorCategory.EXTERNAL_SERVICE),
    ("YouTube", "Unable to fetch video content. Some videos may be unavailable.", ErrorCategory.EXTERNAL_SERVICE),
    ("Google Drive", "Unable to save to Google Drive. Check your folder permissions.", ErrorCategory.EXTERNAL_SERVICE),
    ("validation", "Some information could not be verified. Results may be incomplete.", ErrorCategory.VALIDATION),
    ("ConnectionError", "Unable to connect to the server. Check your internet connection.", ErrorCategory.EXTERNAL_SERVICE),
    ("ConnectionRefused", "Unable to connect to the service. Please try again.", ErrorCategory.EXTERNAL_SERVICE),
    ("database", "A database error occurred. Please try again.", ErrorCategory.DATABASE),
    ("PostgreSQL", "A database error occurred. Please try again.", ErrorCategory.DATABASE),
    ("Supabase", "A database error occurred. Please try again.", ErrorCategory.DATABASE),
]


def classify_error(technical_message: str) -> tuple[str, ErrorCategory]:
    """
    Classify an error and return user-friendly message and category.

    Args:
        technical_message: The raw error message

    Returns:
        Tuple of (user_message, category)
    """
    message_lower = technical_message.lower()

    for pattern, user_message, category in ERROR_MAPPINGS:
        if pattern.lower() in message_lower:
            return user_message, category

    # Default for unknown errors
    return (
        "An unexpected error occurred. Please try again or contact support if the problem persists.",
        ErrorCategory.UNKNOWN
    )


def log_error(
    technical_message: str,
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    stage: Optional[str] = None,
    stack_trace: Optional[str] = None,
    endpoint: Optional[str] = None,
    request_data: Optional[dict] = None,
) -> Optional[str]:
    """
    Log an error to the database and return the error ID.

    Args:
        technical_message: The technical error message
        job_id: Optional job ID if error is job-related
        user_id: Optional user ID
        user_email: Optional user email
        stage: Pipeline stage where error occurred
        stack_trace: Full stack trace if available
        endpoint: API endpoint if applicable
        request_data: Request context (will be sanitized)

    Returns:
        Error log ID if successfully stored, None otherwise
    """
    # Classify the error
    user_message, category = classify_error(technical_message)

    # Sanitize request data - remove sensitive fields
    sanitized_request = None
    if request_data:
        sanitized_request = {
            k: v for k, v in request_data.items()
            if k.lower() not in ('password', 'token', 'secret', 'key', 'authorization', 'cookie')
        }

    # Log to console immediately
    logger.error(
        f"[{category.value}] {technical_message}",
        extra={
            "job_id": job_id,
            "user_id": user_id,
            "stage": stage,
            "category": category.value,
        }
    )

    # Try to store in database
    try:
        from backend.state.impl.supabase_store import get_supabase_client

        supabase = get_supabase_client()
        result = supabase.table("error_logs").insert({
            "job_id": job_id,
            "user_id": user_id,
            "user_email": user_email,
            "user_message": user_message,
            "error_category": category.value,
            "technical_message": technical_message[:5000],  # Limit size
            "stack_trace": stack_trace[:10000] if stack_trace else None,  # Limit size
            "stage": stage,
            "endpoint": endpoint,
            "request_data": sanitized_request,
            "created_at": utc_now_iso(),
            "resolved": False,
        }).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get("id")

    except Exception as e:
        # Don't let error logging cause more errors
        logger.warning(f"Failed to store error log in database: {e}")

    return None


def log_exception(
    exception: Exception,
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    stage: Optional[str] = None,
    endpoint: Optional[str] = None,
    request_data: Optional[dict] = None,
) -> Optional[str]:
    """
    Log an exception with full stack trace.

    Convenience wrapper around log_error that extracts the stack trace.

    Args:
        exception: The exception to log
        Other args: Same as log_error

    Returns:
        Error log ID if successfully stored, None otherwise
    """
    stack_trace = traceback.format_exc()

    return log_error(
        technical_message=str(exception),
        job_id=job_id,
        user_id=user_id,
        user_email=user_email,
        stage=stage,
        stack_trace=stack_trace,
        endpoint=endpoint,
        request_data=request_data,
    )


def get_user_friendly_message(technical_message: str) -> str:
    """
    Get just the user-friendly message for an error.

    Useful for returning to frontend without logging.

    Args:
        technical_message: The technical error message

    Returns:
        User-friendly error message
    """
    user_message, _ = classify_error(technical_message)
    return user_message
