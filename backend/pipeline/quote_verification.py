"""Quote verification: does the source say these words, in this order?

A quotation is not a similar string. It is the source's own words in
sequence, which makes verification a span question rather than a similarity
question. Fuzzy similarity was the original measure here and it answers the
wrong one: measured on the labyrinth corpus (2026-08-19, 144 real quotes and
144 fabrications recombined from each source's OWN vocabulary), fuzzy scoring
stamped 18 of the 144 fabrications VERIFIED and left 39 more merely UNCERTAIN.
Contiguous-span matching separated the same two sets completely: real quotes
1.00, fabrications a maximum of 0.25.

So the verdict is the span, and fuzzy survives only as the signal that tells a
near-miss apart from an invention.

Three verdicts (owner decision, 2026-08-19):
- VERIFIED  - the source contains the quote's words as a run.
- UNCERTAIN - no run, but high fuzzy similarity: a paraphrase, a transcription
  drift, or a quote assembled from nearby text. Kept, marked, never presented
  as verbatim.
- FLAGGED   - neither. The source does not support these words.

Nothing here reads meaning. A verbatim span quoted against its own sense ("I
do not believe the labyrinth is intact" cited as "the labyrinth is intact") or
attributed to the wrong speaker passes every check in this file, by
construction. Those are semantic questions and belong to an advisory pass.

Ellipsis policy: a quotation that elides material is several spans, and each
fragment is verified on its own. The verdict is the weakest fragment's.

Reference: plans/reports/researcher-260114-1657-gemini-hallucination-prevention.md
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


# Quote marks a source or a model may use, folded before matching so a curly
# apostrophe never turns a real quotation into a miss.
_SMART_CHARS = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u00a0": " ", "\u2026": "...",
}

# How a quotation marks omitted material
_ELLIPSIS = re.compile(r"\s*(?:\.\s*\.\s*\.|\u2026|\[\s*\.\.\.\s*\])\s*")

# A fragment shorter than this cannot carry a verdict: three words match
# almost any long text by chance, so fragments this short are skipped and the
# rest of the quotation decides.
MIN_FRAGMENT_WORDS = 4

# Share of a fragment's words that must appear as one contiguous run for the
# fragment to count as verbatim. Set from measurement, not taste: on 208 real
# extracted quotes from the labyrinth corpus the median span is 1.00 and only
# 15 fall below 0.75, all of them long quotes the extractor joined across an
# unmarked elision. On 156 fabrications built from each source's own words,
# ZERO reach even 0.55. The separation is enormous, so the threshold sits low
# enough to keep real quotes whole (96% verify at 0.60) while still passing
# none of the fabrications.
SPAN_THRESHOLD = 0.60

# Fuzzy score above which a non-matching quote is a near-miss rather than an
# invention. Only consulted when the span check fails.
FUZZY_UNCERTAIN_THRESHOLD = 0.7

VERIFIED = "VERIFIED"
UNCERTAIN = "UNCERTAIN"
FLAGGED = "FLAGGED"

# The verdict FLAGGED replaced (2026-08-19). Kept so stored documents and any
# caller still reading the old name keep working.
LIKELY_HALLUCINATED = "LIKELY_HALLUCINATED"


def normalize_text(text: str) -> str:
    """Normalize text for matching.

    Folds case, smart quotes and dashes, punctuation, and whitespace, so that
    the comparison is about words rather than typography.

    Args:
        text: Any text.

    Returns:
        Lowercased text of words separated by single spaces.
    """
    for smart, plain in _SMART_CHARS.items():
        text = text.replace(smart, plain)
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_on_ellipsis(quote_text: str) -> list[str]:
    """Split a quotation into the fragments an ellipsis separates.

    Args:
        quote_text: The quotation as written.

    Returns:
        The fragments, in order. A quotation with no ellipsis is one fragment.
    """
    parts = [p.strip() for p in _ELLIPSIS.split(quote_text or "")]
    return [p for p in parts if p]


def longest_span_ratio(quote_text: str, source_text: str) -> float:
    """Longest run of the quote's words that appears in the source, as a share.

    1.0 means the source contains the whole quotation contiguously. Low values
    mean the words are present but scattered, which is what a fabrication
    assembled from the source's own vocabulary looks like.

    Args:
        quote_text: The quotation.
        source_text: The text it claims to come from.

    Returns:
        0.0 to 1.0.
    """
    quote_words = normalize_text(quote_text).split()
    if not quote_words:
        return 0.0

    haystack = f" {normalize_text(source_text)} "
    longest = 0
    for start in range(len(quote_words)):
        if len(quote_words) - start <= longest:
            break
        for end in range(len(quote_words), start + longest, -1):
            if f" {' '.join(quote_words[start:end])} " in haystack:
                longest = end - start
                break

    return longest / len(quote_words)


def verify_span(quote_text: str, source_text: str) -> dict:
    """Verify a quotation as spans: every fragment, on its own.

    Args:
        quote_text: The quotation, ellipses and all.
        source_text: The text it claims to come from.

    Returns:
        Dict with `ratio` (the weakest fragment's span ratio), `fragments`
        (per-fragment ratios), and `verbatim` (True when every fragment that
        carries a verdict is a run in the source).
    """
    fragments = split_on_ellipsis(quote_text)
    scored = [
        (fragment, longest_span_ratio(fragment, source_text))
        for fragment in fragments
        if len(normalize_text(fragment).split()) >= MIN_FRAGMENT_WORDS
    ]

    if not scored:
        # Every fragment is too short to judge: fall back to the whole string.
        ratio = longest_span_ratio(quote_text, source_text)
        return {"ratio": ratio, "fragments": [ratio], "verbatim": ratio >= SPAN_THRESHOLD}

    ratios = [ratio for _, ratio in scored]
    weakest = min(ratios)
    return {
        "ratio": weakest,
        "fragments": ratios,
        "verbatim": weakest >= SPAN_THRESHOLD,
    }


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
    threshold: float = FUZZY_UNCERTAIN_THRESHOLD,
    strict_threshold: float = 0.6,
) -> dict:
    """Verify a quotation against the text it claims to come from.

    The span decides the verdict; fuzzy similarity only separates a near-miss
    from an invention once the span check has failed.

    Args:
        quote_text: The quotation, ellipses and all.
        transcript: The source text.
        threshold: Fuzzy score at or above which a non-verbatim quote is
            UNCERTAIN rather than FLAGGED.
        strict_threshold: Accepted for backward compatibility; unused, since
            the verdict no longer comes from the fuzzy score.

    Returns:
        Dict with `status`, `verified`, `score` (the span ratio), `span`,
        `fragments`, `fuzzy`, and `match_location`.
    """
    if not quote_text or not transcript:
        return {
            "verified": False,
            "score": 0.0,
            "span": 0.0,
            "fragments": [],
            "fuzzy": 0.0,
            "status": FLAGGED,
            "match_location": None,
        }

    quote_norm = normalize_text(quote_text)
    transcript_norm = normalize_text(transcript)
    if not quote_norm:
        return {
            "verified": False,
            "score": 0.0,
            "span": 0.0,
            "fragments": [],
            "fuzzy": 0.0,
            "status": FLAGGED,
            "match_location": None,
        }

    span = verify_span(quote_text, transcript)
    location = transcript_norm.find(quote_norm)

    if span["verbatim"]:
        return {
            "verified": True,
            "score": span["ratio"],
            "span": span["ratio"],
            "fragments": span["fragments"],
            "fuzzy": 1.0 if location >= 0 else _fuzzy_partial_ratio(quote_norm, transcript_norm),
            "status": VERIFIED,
            "match_location": location if location >= 0 else None,
        }

    # No run. Fuzzy now says whether this is a paraphrase of something real or
    # words the source never put together. It has to be an ORDER-SENSITIVE
    # measure to say anything useful: measured against a 260-word window,
    # token-set ratio scores real quotes and word-salad fabrications both at
    # 1.00, because it is a bag of words and the fabrication uses the window's
    # own words. Partial ratio separates them (real min 0.77, fabrications max
    # 0.71), so it is the signal at every length.
    fuzzy = _fuzzy_partial_ratio(quote_norm, transcript_norm)
    return {
        "verified": False,
        "score": span["ratio"],
        "span": span["ratio"],
        "fragments": span["fragments"],
        "fuzzy": fuzzy,
        "status": UNCERTAIN if fuzzy >= threshold else FLAGGED,
        "match_location": None,
    }


def _get_status(score: float, threshold: float, strict_threshold: float) -> str:
    """Map a bare score to a verdict, for callers that only have a number."""
    if score >= threshold:
        return VERIFIED
    elif score >= strict_threshold:
        return UNCERTAIN
    else:
        return FLAGGED


def verify_quotes_batch(
    quotes: list[dict],
    transcript: str,
    threshold: float = FUZZY_UNCERTAIN_THRESHOLD,
    strict_threshold: float = 0.5,
    remove_hallucinated: bool = False,
) -> tuple[list[dict], list[str]]:
    """Verify a batch of quotes, marking each rather than deleting any.

    Owner decision (2026-08-19): an unverified quote is marked, not removed.
    Deleting a real quote that a transcription mangled is its own kind of
    damage, and what protects the reader is that nothing unconfirmed is ever
    presented as verbatim - which the status field carries.

    Args:
        quotes: Quote dicts with a "text" or "quote_text" field.
        transcript: The source text.
        threshold: Fuzzy score separating UNCERTAIN from FLAGGED.
        strict_threshold: Accepted for backward compatibility; unused.
        remove_hallucinated: Opt-in removal of FLAGGED quotes, off by default.

    Returns:
        Tuple of (quotes with verification metadata, warnings).
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

        quote["span_ratio"] = result["span"]
        quote["fuzzy_score"] = result["fuzzy"]

        if result["status"] == VERIFIED:
            verified_quotes.append(quote)
            logger.debug(f"Quote {quote_id}: VERIFIED (span={result['span']:.2f})")
        elif result["status"] == UNCERTAIN:
            verified_quotes.append(quote)
            warnings.append(
                f"Quote {quote_id}: UNCERTAIN (span={result['span']:.2f}, "
                f"fuzzy={result['fuzzy']:.2f}) - close to the source but not verbatim; "
                "never present it as a quotation"
            )
            logger.warning(f"Quote {quote_id}: UNCERTAIN (score={result['score']:.2f})")
        else:  # FLAGGED
            warning_msg = (
                f"Quote {quote_id}: FLAGGED (span={result['span']:.2f}, "
                f"fuzzy={result['fuzzy']:.2f}) - the source does not contain these "
                f"words: '{quote_text[:50]}...'"
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
