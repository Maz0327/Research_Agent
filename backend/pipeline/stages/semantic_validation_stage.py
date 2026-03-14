"""
Semantic Validation Stage - Validates extraction results before synthesis.

Pipeline Position:
  EXTRACTION → [VALIDATION] → GAP_ANALYSIS → SYNTHESIS → ASSEMBLY

Purpose:
  Quote verification checks if LLM-extracted quotes actually exist in the
  RAW SOURCE CONTENT (Doc 0). This catches LLM hallucination.

Verification runs for ALL modes that allow quotes:
  - transcript_grounded: verify against transcript
  - caption_grounded: verify against captions
  - article_fetched: verify against fetched article
  - text_provided: verify against user-pasted text
  - ocr_extracted: verify against OCR-extracted text

Only video_only is exempt (no quotes allowed).

Validation Checks (per Validation_and_Retry_Rules.md):
  - V4: Quote Verification - fuzzy match against source text
  - V3: Confidence Ceiling - already handled in semantic_validation.py
  - V2: Source ID Consistency - already handled in semantic_validation.py
  - V6: Timestamp Validation - already handled in semantic_validation.py
"""

from typing import Optional

from loguru import logger

from backend.models.semantic_units import AnalysisMode, SemanticExtractionResult
from backend.pipeline.context import PipelineContext
from backend.pipeline.mode_selector import are_quotes_allowed
from backend.pipeline.semantic_validation import (
    validate_semantic_extraction,
    ValidationReport,
)
from backend.pipeline.stages.quote_verification import (
    verify_all_quotes,
    QuoteVerification,
)


def stage_semantic_validation(ctx: PipelineContext) -> PipelineContext:
    """Validate all semantic extractions before synthesis.

    Runs quote verification and other validation checks on each extraction.
    Updates extractions with verification status and calculates overall
    verification rate.

    Args:
        ctx: Pipeline context with semantic_extractions populated

    Returns:
        Updated context with validation results
    """
    logger.info(f"[{ctx.job_id}] Starting semantic validation stage")

    if not ctx.semantic_extractions:
        logger.warning(f"[{ctx.job_id}] No extractions to validate")
        return ctx

    total_quotes = 0
    verified_quotes = 0
    validation_warnings = []

    for extraction in ctx.semantic_extractions:
        source_id = extraction.source_id
        analysis_mode = extraction.analysis_mode

        # Skip quote verification for modes that don't allow quotes
        if not are_quotes_allowed(analysis_mode):
            logger.debug(
                f"[{source_id}] Skipping quote verification "
                f"({analysis_mode.value} mode - quotes not allowed)"
            )
            continue

        # Get raw source content from source_identity_packages (Doc 0)
        source_text = _get_source_text(ctx, source_id)

        if not source_text:
            validation_warnings.append(
                f"No source text available for {source_id} - cannot verify quotes"
            )
            logger.warning(
                f"[{source_id}] No source text for quote verification"
            )
            continue

        # V4: Quote Verification - check quotes exist in provided source content
        if extraction.quotes:
            quote_dicts = [q.to_dict() for q in extraction.quotes]
            verifications, rate = verify_all_quotes(
                quote_dicts, source_text, source_id
            )

            # Update quote objects with verification status
            _update_quotes_with_verification(extraction, verifications)

            # Count for overall rate
            total_quotes += len(extraction.quotes)
            verified_quotes += sum(
                1 for v in verifications if v.status in ("verified", "partial")
            )

            # Add warnings for unverified quotes
            for v in verifications:
                if v.status == "unverified":
                    validation_warnings.append(
                        f"Quote {v.quote_id} not found in source {source_id} "
                        f"(mode: {analysis_mode.value}, ratio: {v.match_ratio:.1%})"
                    )

            # Per-extraction verification rate for this source
            extraction_rate = rate
        else:
            extraction_rate = 1.0  # No quotes = 100% rate

        # Run full validation suite (schema, grounding, ceiling, etc.)
        source_duration = ctx.source_durations.get(source_id) if hasattr(ctx, 'source_durations') else None
        source_metadata = ctx.source_metadata.get(source_id) if hasattr(ctx, 'source_metadata') else None

        report = validate_semantic_extraction(
            extraction.to_dict(),
            analysis_mode,
            source_word_count=_estimate_word_count(source_text),
            source_duration_minutes=source_duration / 60 if source_duration else None,
            has_source_metadata=bool(source_metadata),
            verification_rate=extraction_rate,
            expected_source_id=source_id,
        )

        # Collect warnings from validation report
        validation_warnings.extend(report.warnings)

        # Store report on extraction (if it has the attribute)
        if hasattr(extraction, 'validation_report'):
            extraction.validation_report = report.to_dict()

    # Calculate overall verification rate
    verification_rate = verified_quotes / total_quotes if total_quotes > 0 else 1.0

    # Store results in context
    ctx.verification_rate = verification_rate
    ctx.validation_warnings = validation_warnings

    # Add warnings to job warnings
    for warning in validation_warnings:
        ctx.add_warning(warning)

    logger.info(
        f"[{ctx.job_id}] Validation complete: "
        f"quotes={verified_quotes}/{total_quotes} verified ({verification_rate:.1%}), "
        f"warnings={len(validation_warnings)}"
    )

    return ctx


def _get_source_text(ctx: PipelineContext, source_id: str) -> Optional[str]:
    """Get source text for quote verification from source_identity_packages.

    Args:
        ctx: Pipeline context
        source_id: Source identifier to look up

    Returns:
        Source content text or None if not found
    """
    # Check source_identity_packages (primary source of Doc 0 content)
    for pkg in ctx.source_identity_packages:
        if pkg.source_id == source_id:
            return pkg.content

    # Fallback: check transcripts dict (older format)
    if hasattr(ctx, 'transcripts') and isinstance(ctx.transcripts, dict):
        if source_id in ctx.transcripts:
            return ctx.transcripts[source_id]

    return None


def _estimate_word_count(text: Optional[str]) -> int:
    """Estimate word count from text."""
    if not text:
        return 0
    return len(text.split())


def _update_quotes_with_verification(
    extraction: SemanticExtractionResult,
    verifications: list[QuoteVerification],
) -> None:
    """Update quote objects with verification results.

    Args:
        extraction: The extraction result to update
        verifications: List of verification results
    """
    # Create lookup by quote_id
    verification_lookup = {v.quote_id: v for v in verifications}

    for quote in extraction.quotes:
        verification = verification_lookup.get(quote.quote_id)
        if verification:
            # Update quote with verification status
            # These fields are added in Task 4.3
            if hasattr(quote, 'verification_status'):
                quote.verification_status = verification.status
            if hasattr(quote, 'match_ratio'):
                quote.match_ratio = verification.match_ratio
            if hasattr(quote, '_verification_warning') and verification.status == "unverified":
                quote._verification_warning = (
                    f"Quote not found in source text (match ratio: {verification.match_ratio:.1%})"
                )
