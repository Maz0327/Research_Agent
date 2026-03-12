"""Admin role utilities for the Research Agent."""
from typing import Optional, Set

from loguru import logger

from backend.auth import AuthUser


# Cache admin emails on module load
_admin_emails: Optional[Set[str]] = None


def _load_admin_emails() -> Set[str]:
    """Load admin emails from Settings (ADMIN_EMAILS env var)."""
    global _admin_emails
    if _admin_emails is not None:
        return _admin_emails

    from backend.config import get_settings
    settings = get_settings()
    admin_str = settings.admin_emails or ""
    _admin_emails = {
        email.strip().lower()
        for email in admin_str.split(",")
        if email.strip()
    }

    if _admin_emails:
        logger.info(f"Loaded {len(_admin_emails)} admin email(s) from ADMIN_EMAILS env var")

    return _admin_emails


def is_admin(user: AuthUser) -> bool:
    """
    Check if a user has admin privileges.

    Admin status is determined by:
    1. User's role claim in JWT being "admin" or "service_role"
    2. User's email being in the ADMIN_EMAILS environment variable

    Args:
        user: The authenticated user to check

    Returns:
        True if user has admin privileges, False otherwise
    """
    # Check role claim from JWT
    if user.role in ("admin", "service_role"):
        return True

    # Check email whitelist
    if user.email:
        admin_emails = _load_admin_emails()
        if user.email.lower() in admin_emails:
            return True

    return False


def reload_admin_emails() -> Set[str]:
    """
    Force reload of admin emails from environment.

    Useful if ADMIN_EMAILS env var has been updated.

    Returns:
        Set of admin email addresses
    """
    global _admin_emails
    _admin_emails = None
    return _load_admin_emails()
