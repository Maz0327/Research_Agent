"""Filter bot-block pages before they waste LLM extraction calls.

When sites like Reddit, Medium, or Cloudflare-protected pages return
a bot challenge instead of real content, we detect it here and skip
extraction entirely. This prevents garbage themes like
"Access Control and Authentication" appearing in research briefs.
"""

import re

from loguru import logger


# Signals that indicate a bot-block/challenge page, not real content
_BLOCK_SIGNALS = [
    "verify you are human",
    "access denied",
    "blocked by network security",
    "ray id:",  # Cloudflare fingerprint
    "enable javascript and cookies",
    "checking your browser",
    "security challenge",
    "file a ticket",
    "cf-browser-verification",
    "just a moment",  # Cloudflare waiting page
    "attention required",  # Cloudflare block page
    "you have been blocked",
    "please verify you are a human",
    "complete the security check",
]

# Minimum content length for a real article/transcript
_MIN_CONTENT_LENGTH = 500

# Need at least this many signals to classify as blocked
_MIN_SIGNAL_COUNT = 2


def is_blocked_content(text: str, min_length: int = _MIN_CONTENT_LENGTH) -> bool:
    """Detect if content is a bot-block page rather than real content.

    Args:
        text: The extracted text content to check.
        min_length: Minimum character length for real content.

    Returns:
        True if the content appears to be a bot-block page.
    """
    if not text or len(text.strip()) < min_length:
        # Very short content is suspicious but could be a legitimate short article.
        # Only flag as blocked if it also has block signals.
        if not text:
            return True
        text_lower = text.lower()
        has_signals = sum(1 for s in _BLOCK_SIGNALS if s in text_lower) >= 1
        return has_signals

    text_lower = text.lower()
    signal_count = sum(1 for s in _BLOCK_SIGNALS if s in text_lower)
    return signal_count >= _MIN_SIGNAL_COUNT


def filter_content_or_warn(
    text: str,
    source_id: str,
    url: str = "",
) -> str | None:
    """Check content and return it if valid, or None if blocked.

    Logs a warning when blocked content is detected.

    Args:
        text: The extracted text content.
        source_id: Source identifier for logging.
        url: URL for logging context.

    Returns:
        The original text if valid, None if blocked.
    """
    if is_blocked_content(text):
        url_preview = url[:60] if url else "unknown"
        content_len = len(text) if text else 0
        logger.warning(
            f"[{source_id}] Blocked content detected ({content_len} chars) "
            f"from {url_preview} — skipping extraction"
        )
        return None
    return text


# Words and phrases that belong to a page's furniture, not its argument
_CHROME_MARKERS = [
    "skip to main content",
    "skip to content",
    "toggle navigation",
    "main menu",
    "primary menu",
    "site navigation",
    "cookie policy",
    "accept cookies",
    "all rights reserved",
    "terms of service",
    "privacy policy",
    "sign in",
    "log in",
    "subscribe",
    "newsletter",
    "share this",
    "follow us",
    "back to top",
    "related articles",
    "read more",
]

# A line this long is a sentence someone wrote, not a menu item
_PROSE_LINE_WORDS = 12

# Below this, a "successful" fetch did not actually get the article
_THIN_CONTENT_WORDS = 150


def prose_density(text: str) -> float:
    """Fraction of a page's words that sit inside prose-length lines.

    Navigation, link lists, and footers are short lines. Article bodies are
    long ones. The ratio separates the two without needing to know the site.

    Args:
        text: Extracted text.

    Returns:
        0.0 to 1.0. Empty text scores 0.0.
    """
    words_total = 0
    words_in_prose = 0

    for line in text.splitlines():
        count = len(line.split())
        if not count:
            continue
        words_total += count
        if count >= _PROSE_LINE_WORDS:
            words_in_prose += count

    if not words_total:
        return 0.0
    return words_in_prose / words_total


def looks_like_navigation_chrome(text: str) -> bool:
    """Detect an extraction that captured the page's furniture, not its content.

    A Perseus 503 on 2026-08-17 was saved as a source: the fetch succeeded, the
    extractor returned the site's menus, and the pipeline treated the result as
    an article. The tell is short lines plus site-furniture phrases, with
    almost no prose.

    Args:
        text: Extracted text.

    Returns:
        True when the text reads as page chrome rather than content.
    """
    if not text or not text.strip():
        return False

    lowered = text.lower()
    markers = sum(1 for marker in _CHROME_MARKERS if marker in lowered)
    density = prose_density(text)
    line_count = sum(1 for line in text.splitlines() if line.strip())

    # Mostly menus and it says menu things, or a stack of short lines with no
    # prose in it at all. One short paragraph is thin, not chrome: that case
    # belongs to is_thin_content, which names it accurately.
    mostly_menus = density < 0.40 and markers >= 2
    a_list_not_an_article = line_count >= 5 and density < 0.25
    return mostly_menus or a_list_not_an_article


def is_thin_content(text: str, min_words: int = _THIN_CONTENT_WORDS) -> bool:
    """Detect a fetch that technically succeeded but returned almost nothing.

    Substack and other JS-heavy pages return a shell to plain HTTP clients:
    a title, a subscribe box, and no article. Thin is not empty, so nothing
    upstream notices without this check.

    Args:
        text: Extracted text.
        min_words: Word count below which content counts as thin.

    Returns:
        True when the text is too short to be the article it claims to be.
    """
    return not text or len(text.split()) < min_words


def needs_fetch_fallback(text: str) -> tuple[bool, str]:
    """Decide whether an extraction should be retried through another route.

    Args:
        text: Extracted text from the primary fetch.

    Returns:
        Tuple of (needs_fallback, reason). Reason is an empty string when the
        text is usable.
    """
    if not text or not text.strip():
        return True, "no text extracted"
    if looks_like_navigation_chrome(text):
        return True, "extraction looks like page navigation, not content"
    if is_thin_content(text):
        return True, f"thin extraction ({len(text.split())} words)"
    return False, ""
