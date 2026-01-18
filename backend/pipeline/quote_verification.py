"""Quote verification via fuzzy matching against transcripts.

Hallucination Prevention Rules:
- QV-001: Quote fuzzy match ≥0.7 → VERIFIED
- QV-002: Quote match <0.5 → LIKELY_HALLUCINATED (remove)

Reference: plans/reports/researcher-260114-1657-gemini-hallucination-prevention.md

This module verifies that extracted quotes actually exist in the source
transcript, catching hallucinated quotes before they reach the output.

Uses RapidFuzz for efficient fuzzy string matching when available,
falls back to difflib.SequenceMatcher otherwise.
"""

import re
from typing import Optional

from loguru import logger

# Try to import RapidFuzz for better performance
try:
    from rapidfuzz import fuzz as rapidfuzz_fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching.

    - Lowercase
    - Remove punctuation
    - Collapse whitespace
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fuzzy_ratio(s1: str, s2: str) -> float:
    """Calculate fuzzy similarity ratio between two strings.

    Uses RapidFuzz if available, otherwise difflib.
    Returns float 0.0-1.0.
    """
    if RAPIDFUZZ_AVAILABLE:
        return rapidfuzz_fuzz.ratio(s1, s2) / 100.0
    else:
        return SequenceMatcher(None, s1, s2).ratio()


def _fuzzy_partial_ratio(s1: str, s2: str) -> float:
    """Calculate partial fuzzy ratio (best substring match).

    Uses RapidFuzz if available, otherwise difflib with sliding window.
    Returns float 0.0-1.0.
    """
    if RAPIDFUZZ_AVAILABLE:
        return rapidfuzz_fuzz.partial_ratio(s1, s2) / 100.0
    else:
        # Fallback: sliding window with SequenceMatcher
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        best_score = 0.0
        for i in range(0, max(1, len(s2) - len(s1) + 1), 5):
            window = s2[i : i + len(s1) + 10]
            score = SequenceMatcher(None, s1, window).ratio()
            best_score = max(best_score, score)
        return best_score


def _fuzzy_token_set_ratio(s1: str, s2: str) -> float:
    """Calculate token set ratio (handles word reordering).

    Uses RapidFuzz if available, otherwise word overlap.
    Returns float 0.0-1.0.
    """
    if RAPIDFUZZ_AVAILABLE:
        return rapidfuzz_fuzz.token_set_ratio(s1, s2) / 100.0
    else:
        # Fallback: word overlap ratio
        words1 = set(s1.split())
        words2 = set(s2.split())
        if not words1:
            return 0.0
        intersection = words1 & words2
        return len(intersection) / max(len(words1), len(words2))


def verify_quote(
    quote_text: str,
    transcript: str,
    threshold: float = 0.7,
    strict_threshold: float = 0.6,
) -> dict:
    """Verify a quote against a transcript using fuzzy matching.

    Args:
        quote_text: The extracted quote to verify
        transcript: The full transcript to match against
        threshold: Minimum score for VERIFIED status (default 0.7)
        strict_threshold: Below this score = LIKELY_HALLUCINATED (default 0.6)

    Returns:
        dict with keys:
            - verified: bool (score >= threshold)
            - score: float (0.0 - 1.0)
            - status: "VERIFIED" | "UNCERTAIN" | "LIKELY_HALLUCINATED"
            - match_location: approximate character position if found
    """
    if not quote_text or not transcript:
        return {
            "verified": False,
            "score": 0.0,
            "status": "LIKELY_HALLUCINATED",
            "match_location": None,
        }

    quote_norm = normalize_text(quote_text)
    transcript_norm = normalize_text(transcript)

    # Empty after normalization
    if not quote_norm:
        return {
            "verified": False,
            "score": 0.0,
            "status": "LIKELY_HALLUCINATED",
            "match_location": None,
        }

    # Exact substring match (fastest check)
    if quote_norm in transcript_norm:
        match_pos = transcript_norm.find(quote_norm)
        return {
            "verified": True,
            "score": 1.0,
            "status": "VERIFIED",
            "match_location": match_pos,
        }

    # Short quotes: use partial ratio
    if len(quote_norm) < 30:
        score = _fuzzy_partial_ratio(quote_norm, transcript_norm)
        return {
            "verified": score >= threshold,
            "score": score,
            "status": _get_status(score, threshold, strict_threshold),
            "match_location": None,
        }

    # Long quotes: sliding window with token_set_ratio for word order flexibility
    best_score = 0.0
    best_position = None
    window_size = min(len(quote_norm) * 2, len(transcript_norm))
    step_size = max(10, len(quote_norm) // 4)

    for i in range(0, max(1, len(transcript_norm) - len(quote_norm)), step_size):
        window = transcript_norm[i : i + window_size]
        score = _fuzzy_token_set_ratio(quote_norm, window)
        if score > best_score:
            best_score = score
            best_position = i
        # Early exit if we find a great match
        if best_score >= 0.95:
            break

    return {
        "verified": best_score >= threshold,
        "score": best_score,
        "status": _get_status(best_score, threshold, strict_threshold),
        "match_location": best_position,
    }


def _get_status(score: float, threshold: float, strict_threshold: float) -> str:
    """Determine verification status from score."""
    if score >= threshold:
        return "VERIFIED"
    elif score >= strict_threshold:
        return "UNCERTAIN"
    else:
        return "LIKELY_HALLUCINATED"


def verify_quotes_batch(
    quotes: list[dict],
    transcript: str,
    threshold: float = 0.7,
    strict_threshold: float = 0.5,
    remove_hallucinated: bool = True,
) -> tuple[list[dict], list[str]]:
    """Verify a batch of quotes against a transcript.

    Args:
        quotes: List of quote dicts with "text" or "quote_text" field
        transcript: Full transcript to match against
        threshold: Minimum score for VERIFIED
        strict_threshold: Below this = LIKELY_HALLUCINATED
        remove_hallucinated: If True, remove quotes with status LIKELY_HALLUCINATED

    Returns:
        Tuple of:
            - Updated quotes list with verification metadata added
            - List of warning messages for unverified quotes
    """
    warnings = []
    verified_quotes = []

    for quote in quotes:
        # Support both "text" and "quote_text" field names
        quote_text = quote.get("text") or quote.get("quote_text", "")
        quote_id = quote.get("quote_id", "UNKNOWN")

        result = verify_quote(quote_text, transcript, threshold, strict_threshold)

        # Add verification metadata
        quote["quote_verified"] = result["verified"]
        quote["match_score"] = result["score"]
        quote["verification_status"] = result["status"]

        if result["status"] == "VERIFIED":
            verified_quotes.append(quote)
            logger.debug(f"Quote {quote_id}: VERIFIED (score={result['score']:.2f})")
        elif result["status"] == "UNCERTAIN":
            verified_quotes.append(quote)
            warnings.append(
                f"Quote {quote_id}: UNCERTAIN (score={result['score']:.2f}) - "
                "may be paraphrased or partially accurate"
            )
            logger.warning(f"Quote {quote_id}: UNCERTAIN (score={result['score']:.2f})")
        else:  # LIKELY_HALLUCINATED
            warning_msg = (
                f"Quote {quote_id}: LIKELY_HALLUCINATED (score={result['score']:.2f}) - "
                f"text: '{quote_text[:50]}...'"
            )
            warnings.append(warning_msg)
            logger.warning(warning_msg)

            if not remove_hallucinated:
                verified_quotes.append(quote)

    removed_count = len(quotes) - len(verified_quotes)
    if removed_count > 0:
        logger.info(
            f"Quote verification: {len(verified_quotes)} kept, {removed_count} removed"
        )

    return verified_quotes, warnings


def verify_quotes_for_video(
    quotes: list[dict],
    video_id: str,
    transcript: Optional[str],
) -> tuple[list[dict], list[str]]:
    """Verify quotes for a specific video.

    If no transcript available, marks all quotes as unverifiable.

    Args:
        quotes: List of quote dicts
        video_id: YouTube video ID for logging
        transcript: Transcript text, or None if unavailable

    Returns:
        Tuple of (verified_quotes, warnings)
    """
    if not transcript:
        logger.warning(
            f"No transcript for {video_id} - marking quotes as unverifiable"
        )
        warnings = [f"No transcript available for {video_id} - quotes cannot be verified"]
        for quote in quotes:
            quote["quote_verified"] = False
            quote["match_score"] = 0.0
            quote["verification_status"] = "NO_TRANSCRIPT"
        return quotes, warnings

    return verify_quotes_batch(quotes, transcript)


def verify_extraction_results(
    extraction_result: dict,
    transcript: Optional[str] = None,
    video_id: Optional[str] = None,
) -> tuple[dict, list[str]]:
    """
    Verify all quotes in an extraction result against transcript.

    This is the main integration point for quote verification in the
    ProducerPacket pipeline. Call after Gemini extraction.

    Hallucination Prevention Rule QV-003: All quotes must be verified
    before downstream processing (Gap Analysis, Research Starter).

    Args:
        extraction_result: Dict with "clips" and "quotes" from Gemini extraction
        transcript: Transcript text to verify against (None = skip verification)
        video_id: Video ID for logging

    Returns:
        Tuple of (updated_result, warnings)
        - Clips with match_score < 0.5 are REMOVED
        - Clips with match_score 0.5-0.7 are FLAGGED as uncertain
        - Quotes follow same rules
    """
    warnings = []
    video_id = video_id or extraction_result.get("video_url", "unknown")

    if not transcript:
        logger.info(f"No transcript for {video_id} - skipping quote verification")
        warnings.append(f"Quote verification skipped for {video_id}: no transcript available")
        return extraction_result, warnings

    logger.info(f"Verifying quotes for {video_id} against transcript ({len(transcript)} chars)")

    # Verify clips (which contain quotes)
    clips = extraction_result.get("clips", [])
    if clips:
        verified_clips = []
        for clip in clips:
            quote_text = clip.get("quote", "")
            if not quote_text:
                verified_clips.append(clip)
                continue

            result = verify_quote(quote_text, transcript)
            clip["quote_verified"] = result["verified"]
            clip["match_score"] = result["score"]
            clip["verification_status"] = result["status"]

            if result["status"] == "LIKELY_HALLUCINATED":
                clip_id = clip.get("clip_id", "UNKNOWN")
                warnings.append(
                    f"Clip {clip_id} REMOVED: quote not found in transcript "
                    f"(score={result['score']:.2f})"
                )
                logger.warning(f"Removing hallucinated clip {clip_id}")
            else:
                verified_clips.append(clip)
                if result["status"] == "UNCERTAIN":
                    clip_id = clip.get("clip_id", "UNKNOWN")
                    warnings.append(
                        f"Clip {clip_id} UNCERTAIN: quote may be paraphrased "
                        f"(score={result['score']:.2f})"
                    )

        removed_clips = len(clips) - len(verified_clips)
        if removed_clips > 0:
            logger.info(f"Quote verification: {removed_clips} clips removed as hallucinated")
        extraction_result["clips"] = verified_clips

    # Verify standalone quotes
    quotes = extraction_result.get("quotes", [])
    if quotes:
        verified_quotes, quote_warnings = verify_quotes_batch(
            quotes, transcript, remove_hallucinated=True
        )
        extraction_result["quotes"] = verified_quotes
        warnings.extend(quote_warnings)

    # Add verification summary
    extraction_result["quote_verification"] = {
        "transcript_available": True,
        "clips_verified": len(extraction_result.get("clips", [])),
        "clips_removed": len(clips) - len(extraction_result.get("clips", [])),
        "quotes_verified": len(extraction_result.get("quotes", [])),
        "quotes_removed": len(quotes) - len(extraction_result.get("quotes", [])),
    }

    return extraction_result, warnings


async def verify_batch_results_with_transcripts(
    batch_results: list[dict],
    transcript_fetcher: Optional[callable] = None,
) -> tuple[list[dict], list[str]]:
    """
    Verify quotes across multiple video extraction results.

    This function handles batch verification for multi-video jobs.

    Args:
        batch_results: List of extraction results from analyze_youtube_videos_batch
        transcript_fetcher: Async function(video_url) -> transcript_text or None

    Returns:
        Tuple of (verified_results, all_warnings)
    """
    all_warnings = []
    verified_results = []

    for result in batch_results:
        video_url = result.get("video_url", "")

        # Fetch transcript if fetcher provided
        transcript = None
        if transcript_fetcher:
            try:
                transcript = await transcript_fetcher(video_url)
            except Exception as e:
                logger.warning(f"Failed to fetch transcript for {video_url}: {e}")
                all_warnings.append(f"Transcript fetch failed for {video_url}: {str(e)}")

        # Verify this result
        verified_result, warnings = verify_extraction_results(
            result, transcript, video_url
        )
        verified_results.append(verified_result)
        all_warnings.extend(warnings)

    return verified_results, all_warnings
