"""
Quote Verification - Verify LLM-extracted quotes exist in source text.

Purpose: Catch LLM hallucination by verifying quotes against raw source content.

Verification applies to ALL modes that allow quotes:
- transcript_grounded: verify against transcript
- caption_grounded: verify against captions
- article_fetched: verify against fetched article
- text_provided: verify against user-pasted text
- ocr_extracted: verify against OCR-extracted text

Verification Statuses:
- verified: Exact or near-exact match found (95%+)
- partial: Similar text found (80-94% match)
- unverified: No match found (<80%)

Rule: Unverified quotes are NOT removed - they are flagged for user review.
Per Validation_and_Retry_Rules.md V4.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from loguru import logger


# Thresholds per Validation_and_Retry_Rules.md
EXACT_MATCH_THRESHOLD = 0.95  # 95%+ = verified
FUZZY_MATCH_THRESHOLD = 0.80  # 80%+ = partial, <80% = unverified


@dataclass
class QuoteVerification:
    """Result of verifying a single quote against source text."""
    quote_id: str
    quote_text: str
    status: str  # verified | partial | unverified
    match_ratio: float
    matched_text: Optional[str] = None
    source_location: Optional[str] = None  # timestamp or paragraph index


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Handles common variations:
    - Case differences
    - Extra whitespace
    - Punctuation variations
    """
    if not text:
        return ""
    # Lowercase and normalize whitespace
    normalized = " ".join(text.lower().split())
    return normalized


def find_best_match(quote: str, source_text: str) -> tuple[float, str]:
    """Find the best matching substring in source text.

    Uses sliding window approach with SequenceMatcher for fuzzy matching.

    Args:
        quote: The quote text to find
        source_text: The source content to search in

    Returns:
        Tuple of (match_ratio, matched_text)
    """
    if not quote or not source_text:
        return 0.0, ""

    quote_norm = normalize_text(quote)
    source_norm = normalize_text(source_text)

    # Quick exact match check
    if quote_norm in source_norm:
        return 1.0, quote

    # Sliding window fuzzy match
    quote_len = len(quote_norm)
    if quote_len == 0:
        return 0.0, ""

    best_ratio = 0.0
    best_match = ""

    # Window sizes to try (quote length +/- 20%)
    min_window = max(int(quote_len * 0.8), 10)
    max_window = int(quote_len * 1.2)

    # Step size for sliding window (balance speed vs accuracy)
    step = max(1, quote_len // 10)

    for window_size in range(min_window, max_window + 1, 5):
        for i in range(0, len(source_norm) - window_size + 1, step):
            window = source_norm[i:i + window_size]

            # Use SequenceMatcher for similarity ratio
            ratio = SequenceMatcher(None, quote_norm, window).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                # Get original text (not normalized) for matched_text
                # Approximate position in original text
                orig_start = max(0, int(i * len(source_text) / len(source_norm)))
                orig_end = min(len(source_text), orig_start + len(quote))
                best_match = source_text[orig_start:orig_end].strip()

    return best_ratio, best_match


def verify_quote(quote_text: str, source_text: str) -> tuple[str, float, str]:
    """Verify a single quote exists in source text.

    Args:
        quote_text: The extracted quote to verify
        source_text: The raw source content (Doc 0)

    Returns:
        Tuple of (status, match_ratio, matched_text)
        - status: "verified" | "partial" | "unverified"
        - match_ratio: 0.0 to 1.0 similarity score
        - matched_text: The best matching text found (if any)
    """
    if not quote_text:
        return "unverified", 0.0, ""

    if not source_text:
        return "unverified", 0.0, ""

    ratio, matched = find_best_match(quote_text, source_text)

    if ratio >= EXACT_MATCH_THRESHOLD:
        return "verified", ratio, matched
    elif ratio >= FUZZY_MATCH_THRESHOLD:
        return "partial", ratio, matched
    else:
        return "unverified", ratio, ""


def verify_all_quotes(
    quotes: list[dict],
    source_text: str,
    source_id: str,
) -> tuple[list[QuoteVerification], float]:
    """Verify all quotes against source text.

    Args:
        quotes: List of quote dicts with "quote_id" and "text" fields
        source_text: The raw source content (Doc 0)
        source_id: Source identifier for logging

    Returns:
        Tuple of (verifications, verification_rate)
        - verifications: List of QuoteVerification results
        - verification_rate: Fraction of quotes that are verified or partial
    """
    if not quotes:
        # No quotes = 100% verification rate (nothing to verify)
        return [], 1.0

    if not source_text:
        # No source text = all quotes unverified
        logger.warning(f"[{source_id}] No source text for quote verification")
        return [
            QuoteVerification(
                quote_id=q.get("quote_id", f"UNKNOWN_{i}"),
                quote_text=q.get("text", ""),
                status="unverified",
                match_ratio=0.0,
                source_location=q.get("timestamp"),
            )
            for i, q in enumerate(quotes)
        ], 0.0

    results = []
    verified_count = 0

    for quote in quotes:
        quote_id = quote.get("quote_id", "UNKNOWN")
        quote_text = quote.get("text", "")
        timestamp = quote.get("timestamp")

        status, ratio, matched = verify_quote(quote_text, source_text)

        results.append(QuoteVerification(
            quote_id=quote_id,
            quote_text=quote_text,
            status=status,
            match_ratio=ratio,
            matched_text=matched if status != "unverified" else None,
            source_location=timestamp,
        ))

        if status in ("verified", "partial"):
            verified_count += 1
            logger.debug(f"[{source_id}] Quote {quote_id}: {status} ({ratio:.1%})")
        else:
            logger.warning(
                f"[{source_id}] Quote {quote_id}: UNVERIFIED ({ratio:.1%}) - "
                f"text not found in source"
            )

    verification_rate = verified_count / len(quotes)

    logger.info(
        f"[{source_id}] Quote verification: "
        f"{verified_count}/{len(quotes)} verified ({verification_rate:.1%})"
    )

    return results, verification_rate
