"""Mode-specific extraction prompts.

This module contains the 6 mode-specific prompts for semantic extraction.
Each mode file includes all 5 required components:
1. Source Identity Lock Block
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction Instructions
5. Output Schema

Use get_prompt_for_mode() to dispatch to the appropriate prompt builder.
"""

from backend.models.semantic_units import AnalysisMode

from .transcript_grounded import build_transcript_grounded_prompt
from .caption_grounded import build_caption_grounded_prompt
from .video_only import build_video_only_prompt
from .text_provided import build_text_provided_prompt
from .ocr_extracted import build_ocr_extracted_prompt
from .article_fetched import build_article_fetched_prompt


# Dispatch table for mode-specific prompt builders
_PROMPT_BUILDERS = {
    AnalysisMode.TRANSCRIPT_GROUNDED: build_transcript_grounded_prompt,
    AnalysisMode.CAPTION_GROUNDED: build_caption_grounded_prompt,
    AnalysisMode.VIDEO_ONLY: build_video_only_prompt,
    AnalysisMode.TEXT_PROVIDED: build_text_provided_prompt,
    AnalysisMode.OCR_EXTRACTED: build_ocr_extracted_prompt,
    AnalysisMode.ARTICLE_FETCHED: build_article_fetched_prompt,
}


def get_prompt_for_mode(
    mode: AnalysisMode | str,
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Get the mode-specific extraction prompt.

    Args:
        mode: Analysis mode (enum or string value)
        source_id: Stable source identifier (e.g., "SRC_1")
        source_content: Full source text or description
        title: Source title for lock block

    Returns:
        Complete prompt string with all 5 required components

    Raises:
        ValueError: If mode is not recognized
    """
    # Handle string mode values
    if isinstance(mode, str):
        try:
            mode = AnalysisMode(mode)
        except ValueError:
            raise ValueError(f"Unknown analysis mode: {mode}")

    builder = _PROMPT_BUILDERS.get(mode)
    if builder is None:
        raise ValueError(f"No prompt builder for mode: {mode}")

    return builder(
        source_id=source_id,
        source_content=source_content,
        title=title,
    )


__all__ = [
    "get_prompt_for_mode",
    "build_transcript_grounded_prompt",
    "build_caption_grounded_prompt",
    "build_video_only_prompt",
    "build_text_provided_prompt",
    "build_ocr_extracted_prompt",
    "build_article_fetched_prompt",
]
