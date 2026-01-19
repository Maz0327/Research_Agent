"""Research pipeline runner and stages."""

# Mode selection (single source of truth for analysis modes)
from backend.pipeline.mode_selector import (
    CONFIDENCE_CEILINGS,
    DEGRADED_QUOTE_MODES,
    NO_QUOTE_MODES,
    QUOTES_ALLOWED,
    get_confidence_ceiling,
    get_confidence_ceiling_string,
    select_analysis_mode,
    are_quotes_allowed,
    requires_quote_warning,
    is_no_quote_mode,
)

# RAG Grounding (hallucination prevention)
from backend.pipeline.rag_grounding import (
    GroundingStrength,
    GroundingResult,
    verify_claim_grounding,
    verify_claims_grounding,
    apply_grounding_adjustments,
)

# LLM Judge (cross-model validation)
from backend.pipeline.llm_judge import (
    JudgeVerdict,
    OverallQuality,
    JudgeResult,
    validate_extraction_with_judge,
    apply_judge_verdicts,
)

__all__ = [
    # Mode selection
    "CONFIDENCE_CEILINGS",
    "DEGRADED_QUOTE_MODES",
    "NO_QUOTE_MODES",
    "QUOTES_ALLOWED",
    "get_confidence_ceiling",
    "get_confidence_ceiling_string",
    "select_analysis_mode",
    "are_quotes_allowed",
    "requires_quote_warning",
    "is_no_quote_mode",
    # RAG Grounding
    "GroundingStrength",
    "GroundingResult",
    "verify_claim_grounding",
    "verify_claims_grounding",
    "apply_grounding_adjustments",
    # LLM Judge
    "JudgeVerdict",
    "OverallQuality",
    "JudgeResult",
    "validate_extraction_with_judge",
    "apply_judge_verdicts",
]

