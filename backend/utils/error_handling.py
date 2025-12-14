"""Utility functions for error handling and security."""
import re
from typing import Any


def sanitize_error_message(error: Exception, include_type: bool = True) -> str:
    """
    Sanitize error messages to prevent leaking sensitive data like API keys.
    
    Args:
        error: The exception to sanitize
        include_type: Whether to include exception type in message
        
    Returns:
        Sanitized error message string
    """
    error_msg = str(error)
    
    # Remove potential API keys (various formats)
    patterns = [
        r'sk-[A-Za-z0-9]{32,}',  # OpenAI keys
        r'pplx-[A-Za-z0-9]{32,}',  # Perplexity keys
        r'AIza[0-9A-Za-z-_]{35}',  # Google API keys
        r'xoxb-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{24}',  # Slack bot tokens
        r'Bearer\s+[A-Za-z0-9_-]+',  # Generic bearer tokens
    ]
    
    for pattern in patterns:
        error_msg = re.sub(pattern, '[REDACTED]', error_msg, flags=re.IGNORECASE)
    
    # Remove URLs that might contain tokens
    error_msg = re.sub(r'https?://[^\s]+', '[URL_REDACTED]', error_msg)
    
    if include_type:
        return f"{type(error).__name__}: {error_msg}"
    return error_msg


def sanitize_dict_for_logging(data: dict[str, Any], sensitive_keys: list[str] = None) -> dict[str, Any]:
    """
    Sanitize a dictionary for safe logging by redacting sensitive keys.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: List of keys to redact (default: common sensitive keys)
        
    Returns:
        Sanitized dictionary copy
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'api_key', 'apikey', 'token', 'secret', 'password', 'auth',
            'authorization', 'bearer', 'x-api-key', 'api-key',
        ]
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict_for_logging(value, sensitive_keys)
        else:
            sanitized[key] = value
    
    return sanitized

