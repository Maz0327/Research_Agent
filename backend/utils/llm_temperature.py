"""Task-specific temperature configuration for LLM calls.

Hallucination Prevention Rule TO-001: Temperature optimization per task type.
Research shows 10-15% hallucination reduction with proper temperature settings.

Reference: plans/reports/researcher-260114-1657-gemini-hallucination-prevention.md

Temperature Guide:
- 0.0: Fully deterministic, highest confidence tokens only (factual extraction)
- 0.1-0.2: Near-deterministic with minimal randomness (structured extraction)
- 0.3-0.5: Moderate variation (exploratory tasks)
- 0.7+: Creative output, HIGH hallucination risk (NOT recommended for research)
"""

from enum import Enum


class TaskType(str, Enum):
    """Task types for temperature selection."""

    # Factual extraction - MUST be deterministic
    QUOTE_EXTRACTION = "quote_extraction"
    CLIP_EXTRACTION = "clip_extraction"
    OCR_EXTRACTION = "ocr_extraction"
    CITATION_GENERATION = "citation_generation"

    # Structured analysis - low temperature
    SEMANTIC_EXTRACTION = "semantic_extraction"
    SYNTHESIS = "synthesis"
    STRUCTURE_ANALYSIS = "structure_analysis"

    # Exploratory - moderate temperature
    GAP_ANALYSIS = "gap_analysis"
    RESEARCH_STARTER = "research_starter"

    # General purpose
    GENERAL = "general"


# Task-specific temperature settings
# Based on research: lower temperature = lower hallucination rate for factual tasks
TEMPERATURE_CONFIG: dict[str, float] = {
    # Factual extraction: 0.0 (deterministic)
    TaskType.QUOTE_EXTRACTION: 0.0,
    TaskType.CLIP_EXTRACTION: 0.0,
    TaskType.OCR_EXTRACTION: 0.0,
    TaskType.CITATION_GENERATION: 0.0,

    # Structured analysis: 0.1-0.2
    TaskType.SEMANTIC_EXTRACTION: 0.2,
    TaskType.SYNTHESIS: 0.2,
    TaskType.STRUCTURE_ANALYSIS: 0.3,

    # Exploratory: 0.3-0.5
    TaskType.GAP_ANALYSIS: 0.4,
    TaskType.RESEARCH_STARTER: 0.5,

    # General purpose
    TaskType.GENERAL: 0.7,
}


def get_temperature(task_type: str | TaskType) -> float:
    """Get optimal temperature for a task type.

    Args:
        task_type: Task type string or TaskType enum

    Returns:
        Temperature value (0.0-1.0)
    """
    if isinstance(task_type, TaskType):
        task_type = task_type.value

    return TEMPERATURE_CONFIG.get(task_type, TEMPERATURE_CONFIG[TaskType.GENERAL])


# Convenience aliases for common operations
TEMP_FACTUAL = 0.0      # For quote/clip/OCR extraction
TEMP_STRUCTURED = 0.2   # For semantic extraction, synthesis
TEMP_EXPLORATORY = 0.4  # For gap analysis
TEMP_CREATIVE = 0.7     # For brainstorming (NOT recommended for research)
