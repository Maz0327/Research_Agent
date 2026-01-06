"""Gemini prompts for multi-pass video analysis pipeline.

Phase 3: Full Research Assistant Pipeline
- Pass 2: Structure Analysis (ContentBlueprint)
- Pass 3: Gap Analysis (GapAnalysis)
- Pass 4: Research Starter (ResearchStarter)
"""

from .structure_analysis_prompt import STRUCTURE_ANALYSIS_PROMPT
from .gap_analysis_prompt import GAP_ANALYSIS_PROMPT
from .research_starter_prompt import RESEARCH_STARTER_PROMPT

__all__ = [
    "STRUCTURE_ANALYSIS_PROMPT",
    "GAP_ANALYSIS_PROMPT",
    "RESEARCH_STARTER_PROMPT",
]
