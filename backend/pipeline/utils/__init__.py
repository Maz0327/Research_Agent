"""Pipeline utility modules."""
from .url_dedup import canonicalize_url, deduplicate_urls

__all__ = [
    "canonicalize_url",
    "deduplicate_urls",
]
