"""Mode selection and configuration for semantic extraction.

This module is the SINGLE SOURCE OF TRUTH for:
- Analysis mode selection based on source type and content availability
- Confidence ceiling mappings per mode
- Quote permission rules per mode

All other modules should import from here instead of defining their own mappings.

Owner Decision (2026-01-15): TEXT_PROVIDED and OCR_EXTRACTED allow quotes but
marked as unverified. System cannot verify authenticity of user-provided content,
but extracting quotes provides better UX than omitting them entirely.
"""

from typing import Any

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel


# =============================================================================
# MASTER CONFIDENCE CEILING MAPPING
# =============================================================================

CONFIDENCE_CEILINGS: dict[AnalysisMode, ConfidenceLevel] = {
    # Video sources
    AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,    # Full transcript verified
    AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,     # Captions may have errors
    AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,              # No text, visual inference only

    # Non-video sources
    AnalysisMode.TEXT_PROVIDED: ConfidenceLevel.MEDIUM,        # User-provided, unverified
    AnalysisMode.OCR_EXTRACTED: ConfidenceLevel.MEDIUM,        # OCR may have errors
    AnalysisMode.ARTICLE_FETCHED: ConfidenceLevel.HIGH,        # Full article text available
}


# =============================================================================
# QUOTE PERMISSION RULES
# =============================================================================

QUOTES_ALLOWED: dict[AnalysisMode, bool] = {
    # Video sources
    AnalysisMode.TRANSCRIPT_GROUNDED: True,   # Verbatim quotes from transcript
    AnalysisMode.CAPTION_GROUNDED: True,      # Approximate quotes from captions
    AnalysisMode.VIDEO_ONLY: False,           # NO quotes - use observations instead

    # Non-video sources (per owner decision 2026-01-15)
    AnalysisMode.TEXT_PROVIDED: True,         # Quotes allowed with unverified warning
    AnalysisMode.OCR_EXTRACTED: True,         # Quotes allowed with OCR warning
    AnalysisMode.ARTICLE_FETCHED: True,       # Verbatim quotes from article
}

# Modes where quotes require "unverified" warning
DEGRADED_QUOTE_MODES: set[AnalysisMode] = {
    AnalysisMode.TEXT_PROVIDED,
    AnalysisMode.OCR_EXTRACTED,
    AnalysisMode.CAPTION_GROUNDED,  # Approximate due to caption timing
}

# Modes where quotes are completely prohibited
NO_QUOTE_MODES: set[AnalysisMode] = {
    AnalysisMode.VIDEO_ONLY,
}


# =============================================================================
# CONFIDENCE CEILING STRING MAPPING (for prompts)
# =============================================================================

CONFIDENCE_CEILING_STRINGS: dict[AnalysisMode, str] = {
    AnalysisMode.TRANSCRIPT_GROUNDED: "HIGH",
    AnalysisMode.CAPTION_GROUNDED: "MEDIUM",
    AnalysisMode.VIDEO_ONLY: "LOW",
    AnalysisMode.TEXT_PROVIDED: "MEDIUM",
    AnalysisMode.OCR_EXTRACTED: "MEDIUM",
    AnalysisMode.ARTICLE_FETCHED: "HIGH",
}


# =============================================================================
# MODE SELECTION FUNCTIONS
# =============================================================================

def select_analysis_mode(
    source_type: str,
    content_available: dict[str, Any],
) -> AnalysisMode:
    """Select analysis mode based on source type and available content.

    This function determines the appropriate analysis mode BEFORE any LLM call.
    Mode selection is deterministic and pre-LLM per architecture requirements.

    Args:
        source_type: Type of source ("youtube", "article", "text", "screenshot", "reddit")
        content_available: Dict indicating available content, e.g.:
            - {"supadata_transcript": True}
            - {"whisper_transcript": True}
            - {"youtube_captions": True}
            - {"article_text": True}
            - {"user_text": True}
            - {"ocr_text": True}

    Returns:
        AnalysisMode enum value

    Raises:
        ValueError: If source_type is unknown
    """
    if source_type == "youtube":
        # Video mode selection based on transcript availability
        if content_available.get("supadata_transcript"):
            return AnalysisMode.TRANSCRIPT_GROUNDED
        elif content_available.get("whisper_transcript"):
            return AnalysisMode.TRANSCRIPT_GROUNDED
        elif content_available.get("youtube_captions"):
            return AnalysisMode.CAPTION_GROUNDED
        else:
            return AnalysisMode.VIDEO_ONLY

    elif source_type == "article":
        return AnalysisMode.ARTICLE_FETCHED

    elif source_type == "text":
        return AnalysisMode.TEXT_PROVIDED

    elif source_type == "screenshot":
        return AnalysisMode.OCR_EXTRACTED

    elif source_type == "reddit":
        # Reddit posts have full text content
        return AnalysisMode.TRANSCRIPT_GROUNDED

    else:
        raise ValueError(f"Unknown source type: {source_type}")


def get_confidence_ceiling(mode: AnalysisMode) -> ConfidenceLevel:
    """Get confidence ceiling for analysis mode.

    Args:
        mode: Analysis mode

    Returns:
        Maximum allowed confidence level for this mode
    """
    return CONFIDENCE_CEILINGS.get(mode, ConfidenceLevel.LOW)


def get_confidence_ceiling_string(mode: AnalysisMode) -> str:
    """Get confidence ceiling as string for prompt injection.

    Args:
        mode: Analysis mode (can be enum or string)

    Returns:
        "HIGH", "MEDIUM", or "LOW"
    """
    # Handle string mode values
    if isinstance(mode, str):
        try:
            mode = AnalysisMode(mode)
        except ValueError:
            return "LOW"

    return CONFIDENCE_CEILING_STRINGS.get(mode, "LOW")


def are_quotes_allowed(mode: AnalysisMode) -> bool:
    """Check if quotes are allowed for analysis mode.

    Args:
        mode: Analysis mode

    Returns:
        True if quotes can be extracted, False if prohibited
    """
    return QUOTES_ALLOWED.get(mode, False)


def requires_quote_warning(mode: AnalysisMode) -> bool:
    """Check if quotes require unverified/degraded warning.

    Args:
        mode: Analysis mode

    Returns:
        True if quotes should be marked as unverified
    """
    return mode in DEGRADED_QUOTE_MODES


def is_no_quote_mode(mode: AnalysisMode) -> bool:
    """Check if mode prohibits quotes entirely.

    Args:
        mode: Analysis mode

    Returns:
        True if quotes are prohibited (use observations instead)
    """
    return mode in NO_QUOTE_MODES


# =============================================================================
# MODE DESCRIPTION HELPERS (for prompts and logging)
# =============================================================================

MODE_DESCRIPTIONS: dict[AnalysisMode, str] = {
    AnalysisMode.TRANSCRIPT_GROUNDED: "Full transcript available - verbatim quotes allowed",
    AnalysisMode.CAPTION_GROUNDED: "YouTube captions only - approximate quotes with timing variance",
    AnalysisMode.VIDEO_ONLY: "No transcript - visual observations only, NO quotes",
    AnalysisMode.TEXT_PROVIDED: "User-provided text - quotes allowed but unverified by system",
    AnalysisMode.OCR_EXTRACTED: "OCR from screenshot - quotes may have transcription errors",
    AnalysisMode.ARTICLE_FETCHED: "Article fetched - full text available, verbatim quotes allowed",
}


def get_mode_description(mode: AnalysisMode) -> str:
    """Get human-readable description of analysis mode.

    Args:
        mode: Analysis mode

    Returns:
        Description string for prompts or logging
    """
    return MODE_DESCRIPTIONS.get(mode, "Unknown analysis mode")


# =============================================================================
# QUOTE WARNING MESSAGES
# =============================================================================

QUOTE_WARNING_MESSAGES: dict[AnalysisMode, str] = {
    AnalysisMode.TEXT_PROVIDED: "Quote accuracy unconfirmed by system - user-provided content",
    AnalysisMode.OCR_EXTRACTED: "Quote may contain OCR transcription errors",
    AnalysisMode.CAPTION_GROUNDED: "Quote timing approximate (±5 seconds) - from auto-captions",
}


def get_quote_warning(mode: AnalysisMode) -> str | None:
    """Get warning message to attach to quotes for degraded modes.

    Args:
        mode: Analysis mode

    Returns:
        Warning message string, or None if no warning needed
    """
    return QUOTE_WARNING_MESSAGES.get(mode)
