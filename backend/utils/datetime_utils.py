"""
Datetime utilities for consistent timezone-aware datetime handling.

Python 3.12+ deprecated datetime.utcnow() in favor of timezone-aware datetimes.
This module provides helpers for consistent UTC datetime handling.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Get the current UTC datetime with timezone info.

    Returns:
        Timezone-aware datetime in UTC.
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Get the current UTC datetime as an ISO 8601 string.

    Returns:
        ISO 8601 formatted string (e.g., '2025-12-28T12:34:56.789012+00:00')
    """
    return utc_now().isoformat()


def utc_today_iso() -> str:
    """
    Get today's date in UTC as an ISO 8601 date string.

    Returns:
        ISO 8601 date string (e.g., '2025-12-28')
    """
    return utc_now().date().isoformat()
