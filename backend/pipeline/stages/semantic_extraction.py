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
    Quote,
    SemanticExtractionResult,
    Tension,
    Theme,
)
from backend.models.semantic_extraction_schema import SemanticExtractionSchema
from backend.pipeline.context import PipelineContext
from backend.pipeline.prompts.semantic_extraction_prompt import (
    build_semantic_extraction_prompt,
    SEMANTIC_EXTRACTION_RETRY_PROMPT,
    SEMANTIC_EXTRACTION_ROLE,
)
from backend.pipeline.quote_verification import verify_quote
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

    # Parse quotes
    for quote_data in response.get("quotes", []):
        result.quotes.append(Quote(
            quote_id=quote_data.get("quote_id", f"QT_{len(result.quotes) + 1}"),
            text=quote_data.get("text", ""),
            source_id=source_id,
            timestamp=quote_data.get("timestamp", ""),
            approximate=quote_data.get("approximate", False),
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


def verify_quotes_in_extraction(
    result: SemanticExtractionResult,
    transcript: str,
    source_id: str,
) -> tuple[SemanticExtractionResult, list[str]]:
    """
    Verify quotes in SemanticExtractionResult against transcript.

    Per QV-003: All quotes must be verified before downstream processing.

    This verifies:
    - Quotes in result.quotes
    - Supporting quotes in result.claims

    Args:
        result: Extraction result to verify
        transcript: Source transcript to match against
        source_id: Source ID for logging

    Returns:
        Tuple of (updated_result, warnings)
    """
    warnings = []

    if not transcript:
        warnings.append(f"[{source_id}] Quote verification skipped: no transcript")
        return result, warnings

    # Verify standalone quotes
    verified_quotes = []
    quotes_removed = 0
    for quote in result.quotes:
        verification = verify_quote(quote.text, transcript)
        if verification["status"] == "LIKELY_HALLUCINATED":
            warnings.append(
                f"[{source_id}] Quote {quote.quote_id} REMOVED: "
                f"not found in transcript (score={verification['score']:.2f})"
            )
            quotes_removed += 1
        else:
            # Mark verification status
            if verification["status"] == "UNCERTAIN":
                quote.approximate = True
                warnings.append(
                    f"[{source_id}] Quote {quote.quote_id} UNCERTAIN: "
                    f"may be paraphrased (score={verification['score']:.2f})"
                )
            verified_quotes.append(quote)

    result.quotes = verified_quotes

    # Verify supporting_quotes in claims
    for claim in result.claims:
        verified_supporting = []
        for quote_text in claim.supporting_quotes:
            verification = verify_quote(quote_text, transcript)
            if verification["status"] != "LIKELY_HALLUCINATED":
                verified_supporting.append(quote_text)
            else:
                warnings.append(
                    f"[{source_id}] Claim {claim.claim_id}: "
                    f"supporting quote not found in transcript"
                )
        claim.supporting_quotes = verified_supporting

        # Downgrade confidence if all supporting quotes removed
        if not claim.supporting_quotes and claim.confidence != ConfidenceLevel.LOW:
            claim.confidence = ConfidenceLevel.LOW
            warnings.append(
                f"[{source_id}] Claim {claim.claim_id}: confidence downgraded to LOW "
                "due to no verified supporting quotes"
            )

    if quotes_removed > 0:
        logger.info(
            f"[{source_id}] Quote verification: {quotes_removed} quotes removed"
        )

    return result, warnings


def extract_semantic_structure(
    gemini_client: Any,
    source_id: str,
    source_content: str,
    analysis_mode: AnalysisMode,
    title: str = "Unknown",
    source_word_count: Optional[int] = None,
    source_duration_minutes: Optional[float] = None,
) -> tuple[SemanticExtractionResult, ValidationReport, float]:
    """
    Extract semantic structure from source content.

    Args:
        gemini_client: Initialized Gemini client (GeminiClient instance)
        source_id: Stable source identifier
        source_content: Full source text or description
        analysis_mode: How source was analyzed
        title: Source title for lock block
        source_word_count: Word count (for validation)
        source_duration_minutes: Video duration (for validation)

    Returns:
        Tuple of (extraction_result, validation_report, cost)
    """
    logger.info(f"Extracting semantic structure from {source_id} (mode: {analysis_mode.value})")

    # Build prompt with lock block and confidence ceiling
    prompt = build_semantic_extraction_prompt(
        source_id=source_id,
        source_content=source_content,
        analysis_mode=analysis_mode.value,
        title=title,
    )

    total_cost = 0.0
    retry_count = 0
    max_retries = 1

    while retry_count <= max_retries:
        try:
            # Call Gemini for extraction (sync) with JSON schema
            response = gemini_client.generate_json(
                prompt=prompt,
                system_message=SEMANTIC_EXTRACTION_ROLE,
                response_schema=SemanticExtractionSchema,
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

        # Skip sources without content (except video_only)
        if not content and analysis_mode != AnalysisMode.VIDEO_ONLY:
            logger.warning(f"No content for source {source_id}, skipping extraction")
            ctx.add_warning(f"Skipped semantic extraction for {source_id}: no content")
            sources_failed += 1
            continue

        # Handle video_only mode with no transcript - create placeholder result
        if analysis_mode == AnalysisMode.VIDEO_ONLY and not content:
            logger.warning(
                f"[{source_id}] Video-only mode with no transcript - "
                "creating placeholder result"
            )
            ctx.add_warning(
                f"[{source_id}] Video-only mode: semantic extraction skipped "
                "(requires transcript). Consider using Gemini video analysis for richer output."
            )
            # Create minimal result with limitation noted
            result = SemanticExtractionResult(
                source_id=source_id,
                analysis_mode=analysis_mode,
                analysis_limitations=[
                    "Video-only mode: No transcript available for semantic extraction",
                    "Confidence ceiling: LOW",
                ],
            )
            ctx.semantic_extractions.append(result)
            sources_skipped += 1
            continue

        logger.info(
            f"Processing {source_id} ({package.source_type}) "
            f"in {analysis_mode.value} mode"
        )

        try:
            # Initialize Gemini client (lazy init per source for error isolation)
            from backend.integrations.gemini_client import GeminiClient
            gemini_client = GeminiClient()

            # Call Gemini for semantic extraction
            result, validation_report, cost = extract_semantic_structure(
                gemini_client=gemini_client,
                source_id=source_id,
                source_content=content,
                analysis_mode=analysis_mode,
                title=package.title,
                source_word_count=package.content_word_count,
                source_duration_minutes=package.duration_minutes,
            )

            # Track cost
            if hasattr(ctx, "add_cost"):
                ctx.add_cost("gemini_semantic_extraction", cost)

            # Add validation warnings to context
            for warning in validation_report.warnings:
                ctx.add_warning(f"[{source_id}] {warning}")

            # Step 5: Quote verification post-extraction (QV-003)
            # Only verify if transcript available (not video_only mode)
            if content and analysis_mode != AnalysisMode.VIDEO_ONLY:
                result, quote_warnings = verify_quotes_in_extraction(
                    result=result,
                    transcript=content,
                    source_id=source_id,
                )
                for warning in quote_warnings:
                    ctx.add_warning(warning)

            # Store result (now stores actual SemanticExtractionResult, not just params)
            ctx.semantic_extractions.append(result)
            sources_processed += 1

            logger.info(
                f"Extracted from {source_id}: {len(result.key_points)} key points, "
                f"{len(result.themes)} themes, {len(result.quotes)} quotes, cost=${cost:.4f}"
            )

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
