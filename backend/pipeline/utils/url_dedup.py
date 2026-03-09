"""URL canonicalization and deduplication utilities.

Provides functions to normalize URLs and detect duplicates, particularly
for YouTube videos which have multiple URL formats.
"""
import re
from functools import lru_cache
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Tracking parameters to remove during canonicalization
TRACKING_PARAMS = {
    # UTM parameters
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    # Social tracking
    "fbclid", "gclid", "dclid", "msclkid",
    # Other tracking
    "ref", "source", "via", "from",
}

# YouTube-specific parameters to preserve
YOUTUBE_PRESERVE_PARAMS = {"v", "list"}  # video ID and playlist

# YouTube URL patterns
YOUTUBE_PATTERNS = [
    # Standard watch URLs
    re.compile(r"^(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    # Short URLs
    re.compile(r"^(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    # Embed URLs
    re.compile(r"^(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    # Mobile URLs
    re.compile(r"^(?:https?://)?m\.youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
]


def extract_youtube_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats.

    Args:
        url: YouTube URL in any format

    Returns:
        11-character video ID or None if not a YouTube URL
    """
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group(1)

    # Fallback: parse query string for 'v' parameter
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
        params = parse_qs(parsed.query)
        if "v" in params and params["v"]:
            video_id = params["v"][0]
            if len(video_id) == 11:
                return video_id

    return None


@lru_cache(maxsize=1024)
def canonicalize_url(url: str) -> str:
    """Normalize URL for deduplication.

    Applies the following normalizations:
    - Lowercase domain
    - Remove tracking parameters (utm_*, fbclid, etc.)
    - Normalize YouTube URLs to standard format
    - Remove fragments
    - Ensure https scheme

    Args:
        url: URL to canonicalize

    Returns:
        Canonicalized URL string
    """
    url = url.strip()

    # Handle YouTube URLs specially
    video_id = extract_youtube_video_id(url)
    if video_id:
        # Normalize to standard YouTube watch URL
        return f"https://www.youtube.com/watch?v={video_id}"

    # Parse URL
    parsed = urlparse(url)

    # Ensure scheme (default to https)
    scheme = parsed.scheme.lower() or "https"
    if scheme == "http":
        scheme = "https"

    # Lowercase netloc (domain)
    netloc = parsed.netloc.lower()

    # Remove www. prefix for consistency (optional, can be kept)
    # if netloc.startswith("www."):
    #     netloc = netloc[4:]

    # Parse and filter query parameters
    params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {}
    for key, values in params.items():
        if key.lower() not in TRACKING_PARAMS:
            filtered_params[key] = values

    # Sort parameters for consistent ordering
    query = urlencode(filtered_params, doseq=True) if filtered_params else ""

    # Reconstruct URL without fragment
    canonical = urlunparse((
        scheme,
        netloc,
        parsed.path.rstrip("/") if parsed.path != "/" else "/",
        "",  # params (rarely used)
        query,
        "",  # fragment (removed)
    ))

    return canonical


def deduplicate_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    """Remove duplicate URLs from a list.

    Uses canonicalization to detect duplicates even with different
    URL formats (e.g., youtu.be vs youtube.com).

    Args:
        urls: List of URLs to deduplicate

    Returns:
        Tuple of (unique_urls, duplicate_urls)
        - unique_urls: List of unique URLs (first occurrence kept)
        - duplicate_urls: List of URLs that were removed as duplicates
    """
    if not urls:
        return [], []

    seen_canonical = set()
    unique_urls = []
    duplicate_urls = []

    for url in urls:
        canonical = canonicalize_url(url)

        if canonical in seen_canonical:
            duplicate_urls.append(url)
        else:
            seen_canonical.add(canonical)
            unique_urls.append(url)

    return unique_urls, duplicate_urls


def is_youtube_url(url: str) -> bool:
    """Check if a URL is a YouTube video URL.

    Args:
        url: URL to check

    Returns:
        True if URL is a YouTube video URL
    """
    return extract_youtube_video_id(url) is not None
