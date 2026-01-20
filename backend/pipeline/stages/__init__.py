"""Pipeline stages module - NEW SEMANTIC PIPELINE ONLY.

Updated 2026-01-19: Legacy discovery pipeline completely removed.
- No topic-based discovery (stages 1-6.5 removed)
- No Drive upload (stage 9 removed)
- No Slack integration
- User-supplied sources only (videos, articles, text, screenshots)

Each stage function takes a PipelineContext and modifies it in place.
"""
from .initialization import stage_0_initialize, stage_10_completion

# Semantic Pipeline Stages (Phase 2A) - ACTIVE
from .source_identity import stage_source_identity
from .semantic_extraction import stage_semantic_extraction
from .gap_analysis import stage_gap_analysis
from .semantic_synthesis import stage_semantic_synthesis
from .document_assembly import stage_document_assembly

# Extended Input Stages (Phase 2B)
from .ocr_extraction import stage_ocr_extraction

# Validation Stage (Phase 4)
from .semantic_validation_stage import stage_semantic_validation
from .quote_verification import (
    verify_quote,
    verify_all_quotes,
    QuoteVerification,
)

# Cross-Reference Stage (Phase 6 - Evolving Jobs)
from .cross_reference import stage_cross_reference

# Booster Stage (Phase 7 - Deep Research Booster)
from .booster_stage import run_booster, booster_output_to_dict

# Producer Stage (Phase 8 - Doc 3)
from .producer_stage import run_producer_pipeline, validate_producer_cardinality

__all__ = [
    # Stage 0: Initialization
    "stage_0_initialize",
    # Stage 10: Completion
    "stage_10_completion",
    # Semantic Pipeline Stages (Phase 2A)
    "stage_source_identity",
    "stage_semantic_extraction",
    "stage_gap_analysis",
    "stage_semantic_synthesis",
    "stage_document_assembly",
    # Extended Input Stages (Phase 2B)
    "stage_ocr_extraction",
    # Validation Stage (Phase 4)
    "stage_semantic_validation",
    "verify_quote",
    "verify_all_quotes",
    "QuoteVerification",
    # Cross-Reference Stage (Phase 6)
    "stage_cross_reference",
    # Booster Stage (Phase 7)
    "run_booster",
    "booster_output_to_dict",
    # Producer Stage (Phase 8)
    "run_producer_pipeline",
    "validate_producer_cardinality",
]
