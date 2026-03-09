"""Research pipeline runner and stages.

NOTE: RAG Grounding and LLM Judge are imported lazily to avoid circular imports.
The chain: gemini_client → pipeline.prompts → pipeline/__init__ → rag_grounding
  → stages/__init__ → (stages that import gemini_client) → CIRCULAR.
Use: `from backend.pipeline.rag_grounding import ...` directly when needed.
"""

# Mode selection (single source of truth for analysis modes) — safe, no circular deps
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

# RAG Grounding and LLM Judge: lazy imports to break circular dependency.
# Import from these modules directly when needed:
#   from backend.pipeline.rag_grounding import verify_claim_grounding, ...
#   from backend.pipeline.llm_judge import validate_extraction_with_judge, ...


def __getattr__(name):
    """Lazy imports for RAG Grounding and LLM Judge to break circular imports."""
    _rag_names = {
        "GroundingStrength", "GroundingResult",
        "verify_claim_grounding", "verify_claims_grounding",
        "apply_grounding_adjustments",
    }
    _judge_names = {
        "JudgeVerdict", "OverallQuality", "JudgeResult",
        "validate_extraction_with_judge", "apply_judge_verdicts",
    }

    if name in _rag_names:
        from backend.pipeline import rag_grounding
        return getattr(rag_grounding, name)
    if name in _judge_names:
        from backend.pipeline import llm_judge
        return getattr(llm_judge, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    # RAG Grounding (lazy)
    "GroundingStrength",
    "GroundingResult",
    "verify_claim_grounding",
    "verify_claims_grounding",
    "apply_grounding_adjustments",
    # LLM Judge (lazy)
    "JudgeVerdict",
    "OverallQuality",
    "JudgeResult",
    "validate_extraction_with_judge",
    "apply_judge_verdicts",
]

