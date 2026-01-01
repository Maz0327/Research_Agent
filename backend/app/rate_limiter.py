"""Shared rate limiter configuration for API routes.

This module provides a centralized rate limiter instance that can be
imported by route modules to apply rate limiting decorators.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional


def rate_limit_key(request) -> str:
    """Derive a fair rate-limit key.

    Preference order:
    - Authenticated user_id (prevents users behind same IP from throttling each other)
    - X-Forwarded-For first IP (when behind proxies)
    - Client IP
    - Fallback string
    """
    # Prefer authenticated user when available
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Respect proxy headers if present
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
        if ip:
            return f"ip:{ip}"

    # Fall back to SlowAPI's remote address helper
    client_ip = get_remote_address(request)
    return f"ip:{client_ip}" if client_ip else "anonymous"

# Initialize rate limiter with custom key function
limiter = Limiter(key_func=rate_limit_key)

# Rate limit constants for different operations
RATE_LIMITS = {
    # Settings routes
    "settings_update": "30/minute",
    "settings_validate_folder": "10/minute",
    "settings_oauth_status": "10/minute",
    "settings_check_username": "30/minute",

    # Jobs routes
    "jobs_create": "10/hour",
    "jobs_list": "30/minute",
    "jobs_get": "60/minute",
    "jobs_cancel": "10/minute",

    # Transcripts routes
    "transcripts_create": "5/hour",
    "transcripts_get": "60/minute",
}
