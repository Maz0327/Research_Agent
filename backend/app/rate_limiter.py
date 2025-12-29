"""Shared rate limiter configuration for API routes.

This module provides a centralized rate limiter instance that can be
imported by route modules to apply rate limiting decorators.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter with IP-based key function
limiter = Limiter(key_func=get_remote_address)

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
