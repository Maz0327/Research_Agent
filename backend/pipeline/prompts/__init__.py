"""Gemini prompts for semantic extraction pipeline.

Prompts are organized by purpose:
- semantic_extraction_prompt: Main semantic extraction (backward compat)
- semantic_synthesis_prompt: Cross-source synthesis
- gap_analysis_prompt: Gap identification
- research_starter_prompt: Research starting points
- structure_analysis_prompt: Video structure analysis

Mode-specific prompts are in prompts/modes/ directory.
Use modes.get_prompt_for_mode() for mode-specific extraction.
"""

from .structure_analysis_prompt import STRUCTURE_ANALYSIS_PROMPT
from .gap_analysis_prompt import GAP_ANALYSIS_PROMPT
from .research_starter_prompt import RESEARCH_STARTER_PROMPT
from .semantic_extraction_prompt import (
    build_semantic_extraction_prompt,
    SEMANTIC_EXTRACTION_ROLE,
)

# Mode-specific prompts (Phase 3)
from .modes import get_prompt_for_mode

__all__ = [
    # Legacy prompts
    "STRUCTURE_ANALYSIS_PROMPT",
    "GAP_ANALYSIS_PROMPT",
    "RESEARCH_STARTER_PROMPT",
    # Semantic extraction
    "build_semantic_extraction_prompt",
    "SEMANTIC_EXTRACTION_ROLE",
    # Mode-specific prompts (Phase 3)
    "get_prompt_for_mode",
]
