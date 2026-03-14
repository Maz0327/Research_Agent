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
