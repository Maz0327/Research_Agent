"""Web content capture and text extraction from URLs."""
import ipaddress
import re
import socket
from typing import Optional
from urllib.parse import urlparse

import httpx
from loguru import logger
import trafilatura

from backend.models.source import SourceItem, SourceType
from backend.utils.rate_limiter import sync_wait_for_rate_limit


# Standard user agent string
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Private/reserved IP ranges to block (SSRF prevention)
_BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),        # Private class A
    ipaddress.ip_network("172.16.0.0/12"),      # Private class B
    ipaddress.ip_network("192.168.0.0/16"),     # Private class C
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / AWS metadata
    ipaddress.ip_network("0.0.0.0/8"),          # Reserved
    ipaddress.ip_network("100.64.0.0/10"),      # Shared address space (RFC 6598)
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
]


def is_safe_url(url: str) -> bool:
    """
    Validate that a URL does not point to a private/internal IP address (SSRF prevention).

    Resolves the hostname and checks whether the resulting IP address falls within
    any reserved or private range. Only http/https schemes are permitted.

    Args:
        url: URL string to validate

    Returns:
        True if the URL is safe to fetch, False if it should be blocked
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"SSRF block: non-http(s) scheme in URL: {url}")
            return False
        hostname = parsed.hostname
        if not hostname:
            logger.warning(f"SSRF block: no hostname in URL: {url}")
            return False
        # Resolve hostname → IP (uses system DNS)
        resolved_ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(resolved_ip)
        for blocked_range in _BLOCKED_IP_RANGES:
            if ip_obj in blocked_range:
                logger.warning(
                    f"SSRF block: URL {url!r} resolved to private IP {resolved_ip} "
                    f"(blocked range {blocked_range})"
                )
                return False
        return True
    except Exception as exc:
        # Resolution failure — treat as unsafe to avoid DNS-rebinding tricks
        logger.warning(f"SSRF block: could not validate URL {url!r}: {exc}")
        return False

# Request timeout in seconds
FETCH_TIMEOUT = 30.0

# Maximum content size to download (10MB)
MAX_CONTENT_SIZE = 10 * 1024 * 1024


def _is_pdf_url(url: str) -> bool:
    """
    Check if URL points to a PDF file.
    
    Args:
        url: URL string
        
    Returns:
        True if URL is a PDF, False otherwise
    """
    url_lower = url.lower()
    return url_lower.endswith('.pdf') or 'application/pdf' in url_lower or '.pdf?' in url_lower


def _detect_blocked_content(html_content: str, status_code: int) -> bool:
    """
    Detect if content is blocked, paywalled, or requires login.
    
    Uses heuristics to detect common blocking patterns.
    
    Args:
        html_content: HTML content of the page
        status_code: HTTP status code
        
    Returns:
        True if content appears blocked, False otherwise
    """
    if status_code == 403:
        return True
    
    if status_code == 401:
        return True
    
    if status_code == 429:  # Rate limited
        return True
    
    if not html_content or len(html_content) < 500:
        # Very short content might indicate blocking
        return False  # Don't mark as blocked, just might be a small page
    
    content_lower = html_content.lower()
    
    # Common blocking indicators
    blocked_patterns = [
        r'subscribe\s+to\s+(?:read|continue|unlock)',
        r'please\s+(?:sign\s+in|log\s+in|register)',
        r'paywall',
        r'subscription\s+required',
        r'access\s+denied',
        r'content\s+unavailable',
        r'blocked\s+by',
        r'your\s+request\s+couldn\'t\s+be\s+processed',
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, content_lower):
            return True
    
    return False


def _extract_text_with_trafilatura(html_content: str, url: str) -> Optional[str]:
    """
    Extract readable text from HTML using trafilatura.
    
    Args:
        html_content: Raw HTML content
        url: Source URL (for context)
        
    Returns:
        Extracted text or None if extraction failed
    """
    try:
        extracted = trafilatura.extract(
            html_content,
            url=url,
            include_links=False,
            include_images=False,
            include_tables=True,
            favor_recall=True,  # Prefer getting more content over precision
        )
        
        if extracted and len(extracted.strip()) > 50:  # Minimum meaningful content
            return extracted.strip()
        
        logger.warning(f"trafilatura extracted minimal or no text from {url}")
        return None
    
    except Exception as e:
        logger.exception(f"Error extracting text with trafilatura from {url}: {e}")
        return None


def extract_title_from_html(html_content: str, url: str) -> Optional[str]:
    """Extract page title from HTML using trafilatura metadata.

    Tries og:title, then <title> tag. Returns None if nothing useful found.
    """
    try:
        metadata = trafilatura.extract_metadata(html_content, default_url=url)
        if metadata and metadata.title and len(metadata.title.strip()) > 3:
            return metadata.title.strip()
    except Exception:
        pass
    return None


# Strings that show up in author metadata but name nobody
_JUNK_BYLINE_MARKERS = (
    "staff",
    "admin",
    "editor",
    "newsroom",
    "correspondent",
    "contributor",
    "guest",
    "unknown",
    "anonymous",
)


def _clean_byline(raw: Optional[str]) -> Optional[str]:
    """Normalize an author string, or reject it as unusable.

    Publishers put all sorts of things in author metadata: "By Jane Doe",
    profile URLs, email addresses, "Staff Writer", the site's own name. A
    wrong byline is worse than none, so anything that does not look like a
    person or a named outlet is dropped.

    Args:
        raw: Author string from page metadata, possibly None.

    Returns:
        A cleaned byline, or None when nothing usable is left.
    """
    if not raw:
        return None

    byline = raw.strip()
    if byline.lower().startswith("by "):
        byline = byline[3:].strip()
    byline = byline.strip(" -|,;")

    if not byline or len(byline) > 120:
        return None
    if "@" in byline or "http://" in byline or "https://" in byline:
        return None
    if byline.lower() in _JUNK_BYLINE_MARKERS:
        return None

    return byline


def extract_byline_from_html(html_content: str, url: str) -> dict:
    """Extract author and publication date from a page, without an LLM.

    trafilatura reads meta tags (`author`, `article:author`), schema.org
    JSON-LD, and common byline markup, which covers the overwhelming majority
    of publishers. Sources whose byline stays unknown are honest holes, not
    guesses.

    Args:
        html_content: Raw HTML of the page.
        url: Source URL (used as trafilatura's default URL for relative refs).

    Returns:
        Dict with `creator`, `published`, and `sitename` keys. Any value may be
        None when the page does not carry it.
    """
    result: dict = {"creator": None, "published": None, "sitename": None}

    try:
        metadata = trafilatura.extract_metadata(html_content, default_url=url)
    except Exception as e:
        logger.debug(f"Byline extraction failed for {url}: {e}")
        return result

    if not metadata:
        return result

    result["creator"] = _clean_byline(getattr(metadata, "author", None))
    published = getattr(metadata, "date", None)
    result["published"] = published.strip() if isinstance(published, str) and published.strip() else None
    sitename = getattr(metadata, "sitename", None)
    result["sitename"] = sitename.strip() if isinstance(sitename, str) and sitename.strip() else None

    return result


def _fetch_url_content(url: str) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Fetch content from a URL using httpx.
    
    Args:
        url: URL to fetch
        
    Returns:
        Tuple of (html_content, status_code, error_message)
        If successful: (html_content, status_code, None)
        If failed: (None, status_code, error_message)
    """
    # Block requests to private/internal IPs before making any network call
    if not is_safe_url(url):
        return None, None, "URL blocked: resolves to private or reserved IP address"

    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        with httpx.Client(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            
            # Check content size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                return None, response.status_code, f"Content too large: {content_length} bytes"
            
            # Check if response is HTML
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                # Not HTML, might be PDF or other format
                return None, response.status_code, f"Non-HTML content type: {content_type}"
            
            response.raise_for_status()
            return response.text, response.status_code, None
    
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return None, None, "Request timeout"
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error {e.response.status_code} fetching {url}: {e}")
        return None, e.response.status_code, f"HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        logger.warning(f"Request error fetching {url}: {e}")
        return None, None, f"Request error: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error fetching {url}: {e}")
        return None, None, f"Unexpected error: {str(e)}"


WAYBACK_CDX_API = "http://web.archive.org/cdx/search/cdx"
WAYBACK_SNAPSHOT_TEMPLATE = "https://web.archive.org/web/{timestamp}id_/{url}"


def _latest_wayback_snapshot(url: str, timeout: float) -> Optional[str]:
    """Find the most recent successful Internet Archive capture of a URL.

    Uses the CDX index rather than the `wayback/available` endpoint, which
    rate-limits aggressively (429 on the second lookup, measured 08-19). The
    `id_` snapshot form returns the page as archived, without the archive's
    own toolbar markup.

    Args:
        url: Original source URL.
        timeout: Request timeout in seconds.

    Returns:
        Snapshot URL, or None when the archive has no successful capture.
    """
    sync_wait_for_rate_limit("archive_org")
    response = httpx.get(
        WAYBACK_CDX_API,
        params={
            "url": url,
            "output": "json",
            "limit": "-1",  # most recent match
            "filter": "statuscode:200",
            "fl": "timestamp,original",
        },
        timeout=timeout,
        follow_redirects=True,
    )
    if response.status_code != 200:
        logger.debug(f"Wayback index returned {response.status_code} for {url[:60]}")
        return None

    rows = response.json()
    # Row 0 is the header when any match exists.
    if not isinstance(rows, list) or len(rows) < 2:
        return None

    timestamp, original = rows[-1][0], rows[-1][1]
    return WAYBACK_SNAPSHOT_TEMPLATE.format(timestamp=timestamp, url=original)


def fetch_via_wayback(url: str, timeout: float = 30.0) -> tuple[Optional[str], Optional[str]]:
    """Fetch a page's most recent Internet Archive snapshot.

    Live fetches fail in ways the archive does not: a 503 (Perseus, 08-17), a
    paywall added after publication, a page rewritten since it was cited. The
    snapshot is the text a reader saw, so it keeps the source in the corpus
    instead of dropping it.

    Args:
        url: Original source URL.
        timeout: Per-request timeout in seconds.

    Returns:
        Tuple of (html, snapshot_url). Both None when no snapshot exists or the
        archive cannot be reached: an unreachable archive never fails a job.
    """
    try:
        snapshot_url = _latest_wayback_snapshot(url, timeout)
        if not snapshot_url:
            logger.debug(f"No Wayback snapshot for {url[:60]}")
            return None, None

        sync_wait_for_rate_limit("archive_org")
        snapshot = httpx.get(snapshot_url, timeout=timeout, follow_redirects=True)
        if snapshot.status_code != 200:
            logger.debug(
                f"Wayback snapshot returned {snapshot.status_code} for {url[:60]}"
            )
            return None, None

        logger.info(f"Recovered {url[:60]} from the Internet Archive")
        return snapshot.text, snapshot_url

    except Exception as e:
        logger.debug(f"Wayback fallback failed for {url[:60]}: {e}")
        return None, None


def capture_web_content(sources: list[SourceItem]) -> list[SourceItem]:
    """
    Capture web content for a list of SourceItems.
    
    For each URL:
    - Fetches HTML with httpx (timeout, user-agent)
    - Extracts readable text using trafilatura
    - Handles PDFs (keeps as PDF source, doesn't parse)
    - Handles blocked/paywalled sites (marks in notes, keeps URL/title)
    
    Args:
        sources: List of SourceItem objects from Perplexity shortlist
        
    Returns:
        Updated list of SourceItem objects with text where available
        
    Example:
        >>> sources = [
        ...     SourceItem(url="https://example.com/article", title="Article", source_type=SourceType.WEB)
        ... ]
        >>> updated = capture_web_content(sources)
        >>> for source in updated:
        ...     if source.text:
        ...         print(f"Captured {len(source.text)} characters from {source.url}")
    """
    updated_sources = []
    
    for source in sources:
        # Skip if already has text (avoid re-processing)
        if source.text:
            logger.debug(f"Skipping {source.url} - already has text")
            updated_sources.append(source)
            continue
        
        # Handle PDFs - don't parse, just mark
        if _is_pdf_url(source.url) or source.source_type == SourceType.PDF:
            logger.info(f"PDF detected for {source.url}, keeping as PDF source")
            updated_source = source.model_copy()
            updated_source.source_type = SourceType.PDF
            if not updated_source.notes:
                updated_source.notes = "PDF file (not parsed in MVP)"
            updated_sources.append(updated_source)
            continue
        
        # Skip YouTube sources (should be handled separately)
        if source.source_type == SourceType.YOUTUBE:
            logger.debug(f"Skipping YouTube source {source.url}")
            updated_sources.append(source)
            continue
        
        # Fetch content
        html_content, status_code, error_message = _fetch_url_content(source.url)
        
        if html_content is None:
            # Fetch failed or non-HTML content
            updated_source = source.model_copy()
            
            if error_message:
                if status_code in (403, 401):
                    # Blocked/unauthorized
                    updated_source.notes = f"Blocked/unavailable: {error_message}"
                elif status_code == 429:
                    updated_source.notes = f"Rate limited: {error_message}"
                else:
                    updated_source.notes = f"Fetch failed: {error_message}"
            
            updated_sources.append(updated_source)
            logger.warning(f"Could not fetch content from {source.url}: {error_message}")
            continue
        
        # Check if content is blocked/paywalled
        if _detect_blocked_content(html_content, status_code or 200):
            logger.warning(f"Content appears blocked/paywalled for {source.url}")
            updated_source = source.model_copy()
            updated_source.notes = "Content blocked, paywalled, or requires subscription"
            updated_sources.append(updated_source)
            continue
        
        # Extract text using trafilatura
        extracted_text = _extract_text_with_trafilatura(html_content, source.url)
        
        if extracted_text:
            logger.info(f"Successfully extracted {len(extracted_text)} characters from {source.url}")
            updated_source = source.model_copy()
            updated_source.text = extracted_text
            updated_sources.append(updated_source)
        else:
            # Extraction failed but we have HTML - keep source with note
            logger.warning(f"Text extraction failed for {source.url}")
            updated_source = source.model_copy()
            updated_source.notes = (updated_source.notes or "") + " Text extraction failed"
            if updated_source.notes.startswith(" "):
                updated_source.notes = updated_source.notes.strip()
            updated_sources.append(updated_source)
    
    return updated_sources
