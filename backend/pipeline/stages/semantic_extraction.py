"""
Semantic Extraction Stage - Extract semantic structure from sources.

This stage processes source content through Gemini to extract:
- Key Points
- Claims
- Themes
- Tensions
- Approximate Observations (for video_only mode)

IMPORTANT: This stage consumes SourceIdentityPackage from the
source_identity stage. It does NOT resolve identity itself.

Based on: docs/authoritative/spec/RASS.md Section 4.3
"""

from typing import Any, Optional, TYPE_CHECKING

from loguru import logger

from backend.models.semantic_units import (
    AnalysisMode,
    ApproximateObservation,
    Claim,
    ConfidenceLevel,
    KeyPoint,
    SemanticExtractionResult,
    Tension,
    Theme,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.prompts.semantic_extraction_prompt import (
    build_semantic_extraction_prompt,
    SEMANTIC_EXTRACTION_RETRY_PROMPT,
    SEMANTIC_EXTRACTION_ROLE,
)
from backend.pipeline.semantic_validation import (
    should_retry,
    validate_semantic_extraction,
    ValidationReport,
)
from backend.state import update_job

if TYPE_CHECKING:
    from backend.pipeline.stages.source_identity import SourceIdentityPackage


def parse_extraction_response(
    response: dict[str, Any],
    source_id: str,
    analysis_mode: AnalysisMode,
) -> SemanticExtractionResult:
    """
    Parse Gemini response into SemanticExtractionResult.

    Handles both normal extraction and video_only mode with
    approximate_observations.
    """
    result = SemanticExtractionResult(
        source_id=source_id,
        analysis_mode=analysis_mode,
    )

    # Parse key points
    for kp_data in response.get("key_points", []):
        confidence_str = kp_data.get("confidence", "medium")
        try:
            confidence = ConfidenceLevel(confidence_str.lower())
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM

        result.key_points.append(KeyPoint(
            key_point_id=kp_data.get("key_point_id", f"KP_{len(result.key_points) + 1}"),
            statement=kp_data.get("statement", ""),
            source_ids=[source_id],
            supporting_claims=kp_data.get("supporting_claims", []),
            confidence=confidence,
        ))

    # Parse claims
    for claim_data in response.get("claims", []):
        confidence_str = claim_data.get("confidence", "medium")
        try:
            confidence = ConfidenceLevel(confidence_str.lower())
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM

        result.claims.append(Claim(
            claim_id=claim_data.get("claim_id", f"CLM_{len(result.claims) + 1}"),
            statement=claim_data.get("statement", ""),
            source_id=source_id,
            supporting_quotes=claim_data.get("supporting_quotes", []),
            confidence=confidence,
            timestamp_range=claim_data.get("timestamp_range"),
            source_mode=analysis_mode if analysis_mode == AnalysisMode.VIDEO_ONLY else None,
        ))

    # Parse themes
    for theme_data in response.get("themes", []):
        result.themes.append(Theme(
            theme_id=theme_data.get("theme_id", f"THEME_{len(result.themes) + 1}"),
            label=theme_data.get("label", ""),
            description=theme_data.get("description", ""),
            related_key_points=theme_data.get("related_key_points", []),
        ))

    # Parse tensions
    for tension_data in response.get("tensions", []):
        result.tensions.append(Tension(
            tension_id=tension_data.get("tension_id", f"TEN_{len(result.tensions) + 1}"),
            description=tension_data.get("description", ""),
            involved_key_points=tension_data.get("involved_key_points", []),
        ))

    # Parse approximate observations (video_only mode)
    for obs_data in response.get("approximate_observations", []):
        result.approximate_observations.append(ApproximateObservation(
            observation_id=obs_data.get("observation_id", f"OBS_{len(result.approximate_observations) + 1}"),
            observation=obs_data.get("observation", ""),
            source_id=source_id,
            timestamp_range=obs_data.get("timestamp_range", "~0:00 - 0:00"),
            approximate=True,
            observation_type="observation",
            confidence=ConfidenceLevel.LOW,
        ))

    # Parse analysis limitations
    result.analysis_limitations = response.get("analysis_limitations", [])
    result.transcript_source = response.get("transcript_source")
    result.parse_error = response.get("parse_error", False)

    return result


async def extract_semantic_structure(
    gemini_client: Any,
    source_id: str,
    source_content: str,
    analysis_mode: AnalysisMode,
    source_word_count: Optional[int] = None,
    source_duration_minutes: Optional[float] = None,
) -> tuple[SemanticExtractionResult, ValidationReport, float]:
    """
    Extract semantic structure from source content.

    Args:
        gemini_client: Initialized Gemini client
        source_id: Stable source identifier
        source_content: Full source text or description
        analysis_mode: How source was analyzed
        source_word_count: Word count (for validation)
        source_duration_minutes: Video duration (for validation)

    Returns:
        Tuple of (extraction_result, validation_report, cost)
    """
    logger.info(f"Extracting semantic structure from {source_id} (mode: {analysis_mode.value})")

    # Build prompt
    prompt = build_semantic_extraction_prompt(
        source_id=source_id,
        source_content=source_content,
        analysis_mode=analysis_mode.value,
    )

    total_cost = 0.0
    retry_count = 0
    max_retries = 1

    while retry_count <= max_retries:
        try:
            # Call Gemini for extraction
            response = await gemini_client.generate_json(
                prompt=prompt,
                system_message=SEMANTIC_EXTRACTION_ROLE,
            )

            if "error" in response:
                logger.error(f"Gemini error: {response['error']}")
                return SemanticExtractionResult(
                    source_id=source_id,
                    analysis_mode=analysis_mode,
                    parse_error=True,
                    analysis_limitations=[f"Gemini error: {response['error']}"],
                ), ValidationReport(), response.get("cost", 0)

            total_cost += response.get("cost", 0)
            data = response.get("data", {})

            # Validate extraction
            validation_report = validate_semantic_extraction(
                data=data,
                analysis_mode=analysis_mode,
                source_word_count=source_word_count,
                source_duration_minutes=source_duration_minutes,
            )

            # Check if retry needed
            if should_retry(validation_report) and retry_count < max_retries:
                logger.warning(f"Retrying extraction for {source_id} due to validation issues")
                prompt = SEMANTIC_EXTRACTION_RETRY_PROMPT + "\n\nOriginal content:\n" + source_content
                retry_count += 1
                continue

            # Parse and return result
            result = parse_extraction_response(data, source_id, analysis_mode)

            # Enforce confidence ceiling
            ceiling_warnings = result.enforce_confidence_ceiling()
            for warning in ceiling_warnings:
                validation_report.warnings.append(warning)

            return result, validation_report, total_cost

        except Exception as e:
            logger.error(f"Semantic extraction failed for {source_id}: {e}")
            return SemanticExtractionResult(
                source_id=source_id,
                analysis_mode=analysis_mode,
                parse_error=True,
                analysis_limitations=[f"Extraction error: {str(e)}"],
            ), ValidationReport(), total_cost

    # Should not reach here, but return empty result if we do
    return SemanticExtractionResult(
        source_id=source_id,
        analysis_mode=analysis_mode,
        parse_error=True,
    ), ValidationReport(), total_cost


def stage_semantic_extraction(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Extract semantic structure from all sources.

    PREREQUISITE: source_identity stage must run first to populate
    ctx.source_identity_packages with resolved identity data.

    This stage:
    1. Iterates over all SourceIdentityPackages (from source_identity stage)
    2. Uses pre-resolved analysis_mode (no guessing)
    3. Extracts semantic units using Gemini
    4. Validates extraction results
    5. Stores results in context

    Stage failures are handled gracefully - individual source failures
    do not fail the entire job.
    """
    logger.info(f"[{ctx.job_id}] Stage: Semantic Extraction")

    update_job(
        ctx.job_id,
        stage="semantic_extraction",
        progress_percent=40,
    )

    # Initialize storage for extraction results
    if not hasattr(ctx, "semantic_extractions"):
        ctx.semantic_extractions = []

    # Process each source from identity packages (resolved in source_identity stage)
    sources_processed = 0
    sources_failed = 0
    sources_skipped = 0

    # Get identity packages from context (populated by source_identity stage)
    packages = getattr(ctx, "source_identity_packages", [])

    if not packages:
        logger.warning("No source identity packages found - was source_identity stage run?")
        ctx.add_warning("No source identity packages available for semantic extraction")
        return

    for package in packages:
        source_id = package.source_id
        analysis_mode = package.analysis_mode
        content = package.content

        # Skip inaccessible sources
        if not package.is_accessible:
            logger.warning(f"Source {source_id} not accessible, skipping extraction")
            ctx.add_warning(
                f"Skipped semantic extraction for {source_id}: {package.failure_reason}"
            )
            sources_skipped += 1
            continue

        # Skip sources without content (video_only with no transcript)
        if not content and analysis_mode != AnalysisMode.VIDEO_ONLY:
            logger.warning(f"No content for source {source_id}, skipping extraction")
            ctx.add_warning(f"Skipped semantic extraction for {source_id}: no content")
            sources_failed += 1
            continue

        logger.info(
            f"Processing {source_id} ({package.source_type}) "
            f"in {analysis_mode.value} mode"
        )

        try:
            # Build extraction parameters from identity package
            # In actual implementation, this would call Gemini via extract_semantic_structure()
            extraction_params = {
                "source_id": source_id,
                "source_type": package.source_type,
                "analysis_mode": analysis_mode.value,
                "content_length": package.content_word_count or 0,
                "transcript_source": package.transcript_source,
                "confidence_ceiling": package.confidence_ceiling.value,
                "title": package.title,
                "url": package.url,
            }
            ctx.semantic_extractions.append(extraction_params)
            sources_processed += 1

        except Exception as e:
            logger.error(f"Failed to process {source_id}: {e}")
            ctx.add_warning(f"Semantic extraction failed for {source_id}: {str(e)}")
            sources_failed += 1

    logger.info(
        f"Semantic extraction complete: {sources_processed} processed, "
        f"{sources_failed} failed, {sources_skipped} skipped"
    )

    # Update job with extraction summary
    update_job(
        ctx.job_id,
        partial_outputs={
            "semantic_extraction_summary": {
                "sources_processed": sources_processed,
                "sources_failed": sources_failed,
                "sources_skipped": sources_skipped,
                "total_packages": len(packages),
            }
        },
    )
