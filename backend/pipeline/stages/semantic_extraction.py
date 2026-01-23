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

Performance: Uses ThreadPoolExecutor for parallel source processing.
Configure via SEMANTIC_EXTRACTION_MAX_WORKERS env var (default: 3).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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
    get_retry_prompt,
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

# NOTE: llm_judge and rag_grounding are imported lazily inside functions
# to avoid circular import issues with quote_verification

if TYPE_CHECKING:
    from backend.pipeline.stages.source_identity import SourceIdentityPackage


@dataclass
class SourceExtractionResult:
    """
    Result of extracting a single source (for parallel processing).

    Captures all outputs from process_single_source() for thread-safe
    accumulation and deterministic merge.
    """
    source_id: str
    index: int  # Original index for deterministic ordering
    extraction_result: Optional[SemanticExtractionResult] = None
    warnings: list[str] = None  # type: ignore
    costs: dict[str, float] = None  # type: ignore
    status: str = "pending"  # pending, processed, skipped, failed

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.costs is None:
            self.costs = {}


def extract_video_observations(
    video_url: str,
    source_id: str,
    duration_seconds: Optional[int] = None,
) -> tuple[SemanticExtractionResult, float, list[str]]:
    """
    Extract observations from a video using Gemini video analysis.

    Used for video_only mode when no transcript is available.
    Returns ApproximateObservations (NO quotes - per spec).

    Args:
        video_url: YouTube video URL
        source_id: Source ID for attribution
        duration_seconds: Video duration in seconds (for chunked analysis)

    Returns:
        Tuple of (SemanticExtractionResult, cost, warnings)
    """
    from backend.integrations.gemini_client import GeminiClient

    warnings = []
    cost = 0.0

    # Threshold for chunked analysis (2 hours = 7200 seconds)
    # Videos exceeding Gemini's 1M token limit (~2-3 hours) need chunking
    CHUNK_THRESHOLD_SECONDS = 7200

    try:
        gemini_client = GeminiClient()

        # Analyze video directly via Gemini
        # Use chunked analysis for long videos to avoid token limit errors
        logger.info(f"[{source_id}] Extracting observations from video: {video_url}")

        if duration_seconds and duration_seconds > CHUNK_THRESHOLD_SECONDS:
            logger.info(
                f"[{source_id}] Long video detected ({duration_seconds}s), "
                "using chunked analysis"
            )
            video_result = gemini_client.analyze_youtube_video_chunked(
                video_url=video_url,
                duration_seconds=duration_seconds,
                model="gemini-2.5-flash",
                chunk_duration_seconds=3600,  # 1 hour chunks
            )
        else:
            video_result = gemini_client.analyze_youtube_video(
                video_url=video_url,
                model="gemini-2.5-flash",
                max_clips=12,
            )

        cost = video_result.get("cost", 0.0)

        # Check for errors
        if video_result.get("error"):
            warnings.append(f"Video analysis error: {video_result['error']}")
            return SemanticExtractionResult(
                source_id=source_id,
                analysis_mode=AnalysisMode.VIDEO_ONLY,
                analysis_limitations=[
                    f"Video analysis failed: {video_result['error']}",
                    "Confidence ceiling: LOW",
                ],
            ), cost, warnings

        # Convert clips to ApproximateObservations (NO quotes allowed in video_only)
        observations = []
        clips = video_result.get("clips", [])

        for i, clip in enumerate(clips):
            # Transform quote to observation description (not verbatim)
            # Per spec: video_only mode cannot have quotes, only observations
            quote_text = clip.get("quote", "")
            speaker = clip.get("speaker", "Speaker")
            timestamp_start = clip.get("timestamp_start", "00:00")
            timestamp_end = clip.get("timestamp_end", timestamp_start)

            # Create observation description from clip data
            if quote_text:
                # Transform to non-verbatim observation
                observation_text = (
                    f"{speaker} discusses: {_summarize_as_observation(quote_text)}"
                )
            else:
                observation_text = f"{speaker} appears at this point in the video"

            observations.append(ApproximateObservation(
                observation_id=f"OBS_{i + 1}",
                observation=observation_text,
                source_id=source_id,
                timestamp_range=f"~{timestamp_start} - {timestamp_end}",
                approximate=True,
                observation_type="observation",
                confidence=ConfidenceLevel.LOW,
            ))

        # Build key points from observations
        key_points = []
        video_info = video_result.get("video_info", {})
        video_title = video_info.get("title", "Video")

        # Create summary key point if we have observations
        if observations:
            summary_points = [obs.observation for obs in observations[:3]]
            key_points.append(KeyPoint(
                key_point_id="KP_1",
                statement=f"Video '{video_title}' contains {len(observations)} observed segments",
                source_ids=[source_id],
                supporting_claims=[],
                confidence=ConfidenceLevel.LOW,
            ))

        logger.info(
            f"[{source_id}] Video extraction: {len(observations)} observations, "
            f"{len(key_points)} key points, cost=${cost:.4f}"
        )

        return SemanticExtractionResult(
            source_id=source_id,
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            key_points=key_points,
            approximate_observations=observations,
            analysis_limitations=[
                "Video-only mode: Observations based on visual/audio analysis",
                "Confidence ceiling: LOW - no transcript verification possible",
                "Quotes not included (spec requirement for video_only mode)",
            ],
        ), cost, warnings

    except Exception as e:
        logger.error(f"[{source_id}] Video extraction failed: {e}")
        warnings.append(f"Video extraction failed: {str(e)}")
        return SemanticExtractionResult(
            source_id=source_id,
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            analysis_limitations=[
                f"Video extraction failed: {str(e)}",
                "Confidence ceiling: LOW",
            ],
        ), cost, warnings


def _summarize_as_observation(quote_text: str) -> str:
    """
    Convert a verbatim quote to an observation description.

    video_only mode cannot have quotes, so we summarize instead.
    """
    # Truncate long quotes and add ellipsis
    if len(quote_text) > 100:
        return f"'{quote_text[:97]}...'"
    return f"'{quote_text}'"


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
    max_retries = 2  # Increased from 1 for better error recovery

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
                # Classify error type for targeted retry prompt
                error_type = "thin"  # Default
                issues = []

                for result in validation_report.results:
                    msg = result.message.lower()
                    if "schema" in msg or "missing" in msg or "required" in msg:
                        error_type = "schema"
                        issues.append(result.message)
                    elif "hallucin" in msg or "not found" in msg or "unverified" in msg:
                        error_type = "hallucination"
                        issues.append(result.message)
                    elif "grounding" in msg or "reference" in msg or "source" in msg:
                        error_type = "grounding"
                        issues.append(result.message)
                    elif "thin" in msg or "few" in msg:
                        issues.append(result.message)

                # Get appropriate retry prompt
                retry_prompt = get_retry_prompt(error_type, issues or validation_report.warnings[:5])

                logger.warning(
                    f"Retrying extraction for {source_id} "
                    f"(error_type={error_type}, retry={retry_count + 1}/{max_retries})"
                )
                prompt = retry_prompt + "\n\n## ORIGINAL SOURCE CONTENT:\n\n" + source_content
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


def process_single_source(
    package: "SourceIdentityPackage",
    index: int,
    job_config: Optional[Any] = None,
) -> SourceExtractionResult:
    """
    Process a single source package (thread-safe, isolated).

    Performs all extraction steps for one source:
    1. Handle video_only mode special case
    2. Gemini semantic extraction
    3. Quote verification
    4. LLM Judge validation (if enabled)
    5. RAG grounding (if enabled)

    Args:
        package: Source identity package with resolved metadata
        index: Original index for deterministic ordering
        job_config: Job configuration (for hallucination settings)

    Returns:
        SourceExtractionResult with extraction_result, warnings, costs, status
    """
    source_id = package.source_id
    analysis_mode = package.analysis_mode
    content = package.content

    result = SourceExtractionResult(source_id=source_id, index=index)

    # Skip inaccessible sources
    if not package.is_accessible:
        logger.warning(f"Source {source_id} not accessible, skipping extraction")
        result.warnings.append(
            f"Skipped semantic extraction for {source_id}: {package.failure_reason}"
        )
        result.status = "skipped"
        return result

    # Skip sources without content (except video_only)
    if not content and analysis_mode != AnalysisMode.VIDEO_ONLY:
        logger.warning(f"No content for source {source_id}, skipping extraction")
        result.warnings.append(f"Skipped semantic extraction for {source_id}: no content")
        result.status = "failed"
        return result

    # Handle video_only mode with no transcript - use Gemini video analysis
    if analysis_mode == AnalysisMode.VIDEO_ONLY and not content:
        video_url = package.url
        if video_url and "youtube" in video_url.lower():
            logger.info(
                f"[{source_id}] Video-only mode with no transcript - "
                "using Gemini video analysis"
            )
            extraction, video_cost, video_warnings = extract_video_observations(
                video_url=video_url,
                source_id=source_id,
                duration_seconds=getattr(package, 'duration_seconds', None),
            )
            result.costs["gemini_video"] = video_cost
            result.warnings.extend(video_warnings)
            result.extraction_result = extraction

            if extraction.approximate_observations:
                result.status = "processed"
                logger.info(
                    f"[{source_id}] Video extraction complete: "
                    f"{len(extraction.approximate_observations)} observations"
                )
            else:
                result.status = "skipped"
                result.warnings.append(
                    f"[{source_id}] Video analysis produced no observations"
                )
            return result
        else:
            # Non-YouTube video or no URL - create placeholder
            logger.warning(
                f"[{source_id}] Video-only mode with no URL/non-YouTube - "
                "creating placeholder result"
            )
            result.warnings.append(
                f"[{source_id}] Video-only mode: requires YouTube URL for analysis"
            )
            result.extraction_result = SemanticExtractionResult(
                source_id=source_id,
                analysis_mode=analysis_mode,
                analysis_limitations=[
                    "Video-only mode: No YouTube URL available for video analysis",
                    "Confidence ceiling: LOW",
                ],
            )
            result.status = "skipped"
            return result

    logger.info(
        f"Processing {source_id} ({package.source_type}) "
        f"in {analysis_mode.value} mode"
    )

    try:
        # Initialize Gemini client (lazy init per source for error isolation)
        from backend.integrations.gemini_client import GeminiClient
        gemini_client = GeminiClient()

        # Call Gemini for semantic extraction
        extraction, validation_report, cost = extract_semantic_structure(
            gemini_client=gemini_client,
            source_id=source_id,
            source_content=content,
            analysis_mode=analysis_mode,
            title=package.title,
            source_word_count=package.content_word_count,
            source_duration_minutes=package.duration_minutes,
        )

        # Track cost
        result.costs["gemini_semantic_extraction"] = cost

        # Add validation warnings
        for warning in validation_report.warnings:
            result.warnings.append(f"[{source_id}] {warning}")

        # Step 5: Quote verification post-extraction (QV-003)
        if content and analysis_mode != AnalysisMode.VIDEO_ONLY:
            extraction, quote_warnings = verify_quotes_in_extraction(
                result=extraction,
                transcript=content,
                source_id=source_id,
            )
            result.warnings.extend(quote_warnings)

        # Step 6: LLM Judge cross-model validation (if enabled)
        if _should_run_llm_judge_for_source(
            job_config=job_config,
            extraction=extraction,
            validation_report=validation_report,
        ):
            logger.info(f"[{source_id}] Running LLM Judge (GPT-4o) validation")
            try:
                from backend.pipeline.llm_judge import (
                    validate_extraction_with_judge,
                    apply_judge_verdicts,
                )

                judge_result = validate_extraction_with_judge(
                    source_text=content,
                    extraction_result=extraction.to_dict(),
                    source_id=source_id,
                )

                extraction, judge_warnings = apply_judge_verdicts(extraction, judge_result)

                for warning in judge_warnings:
                    result.warnings.append(f"[{source_id}] LLM Judge: {warning}")

                if judge_result.cost:
                    result.costs["openai_llm_judge"] = judge_result.cost

                logger.info(
                    f"[{source_id}] LLM Judge: {judge_result.items_reviewed} items, "
                    f"{len(judge_result.hallucination_flags)} hallucinations flagged, "
                    f"quality={judge_result.overall_quality.value}"
                )
            except Exception as e:
                logger.warning(f"[{source_id}] LLM Judge failed (non-fatal): {e}")
                result.warnings.append(f"[{source_id}] LLM Judge skipped: {str(e)}")

        # Step 7: RAG Grounding verification (if enabled)
        if _should_run_rag_grounding_for_source(job_config) and content:
            logger.info(f"[{source_id}] Running RAG grounding verification")
            try:
                from backend.pipeline.rag_grounding import (
                    verify_claims_grounding,
                    apply_grounding_adjustments,
                )

                rag_threshold = "high"
                max_claims = 10
                if job_config:
                    hall_config = getattr(job_config, "hallucination", None)
                    if hall_config:
                        rag_threshold = getattr(hall_config, "rag_confidence_threshold", "high")
                        max_claims = getattr(hall_config, "max_claims_to_rag_verify", 10)

                grounding_results, grounding_warnings = verify_claims_grounding(
                    claims=extraction.claims,
                    source_text=content,
                    source_id=source_id,
                    confidence_threshold=rag_threshold,
                    max_claims=max_claims,
                )

                extraction.claims, adjustment_warnings = apply_grounding_adjustments(
                    claims=extraction.claims,
                    grounding_results=grounding_results,
                )

                for warning in grounding_warnings + adjustment_warnings:
                    result.warnings.append(f"[{source_id}] RAG Grounding: {warning}")

                logger.info(
                    f"[{source_id}] RAG Grounding: verified {len(grounding_results)} claims"
                )
            except Exception as e:
                logger.warning(f"[{source_id}] RAG Grounding failed (non-fatal): {e}")
                result.warnings.append(f"[{source_id}] RAG Grounding skipped: {str(e)}")

        result.extraction_result = extraction
        result.status = "processed"

        logger.info(
            f"Extracted from {source_id}: {len(extraction.key_points)} key points, "
            f"{len(extraction.themes)} themes, {len(extraction.quotes)} quotes, cost=${cost:.4f}"
        )

    except Exception as e:
        logger.error(f"Failed to process {source_id}: {e}")
        result.warnings.append(f"Semantic extraction failed for {source_id}: {str(e)}")
        result.status = "failed"

    return result


def _should_run_llm_judge_for_source(
    job_config: Optional[Any],
    extraction: SemanticExtractionResult,
    validation_report: "ValidationReport",
) -> bool:
    """
    Determine if LLM Judge should run for this specific source.

    Supports two modes:
    1. Always-on (default): Run for all sources when enable_llm_judge=True
    2. Conditional: Only run when confidence < HIGH or warnings > threshold

    Conditional mode is enabled via LLM_JUDGE_CONDITIONAL env var.
    """
    from backend.config import get_settings

    # First check if LLM Judge is enabled at all
    enable_judge = True  # Default ON
    if job_config:
        if hasattr(job_config, "should_enable_llm_judge"):
            enable_judge = job_config.should_enable_llm_judge()
        else:
            hall_config = getattr(job_config, "hallucination", None)
            if hall_config:
                enable_judge = getattr(hall_config, "enable_llm_judge", True)

    if not enable_judge:
        return False

    # Check if conditional mode is enabled
    settings = get_settings()
    if not settings.llm_judge_conditional:
        return True  # Always run when not conditional

    # Conditional mode: only run if confidence < HIGH or warnings exceed threshold
    warning_threshold = settings.llm_judge_warning_threshold

    # Check if any key point has confidence below HIGH
    has_low_confidence = any(
        kp.confidence != ConfidenceLevel.HIGH
        for kp in extraction.key_points
    )

    # Check warning count from validation
    warning_count = len(validation_report.warnings)

    should_run = has_low_confidence or warning_count >= warning_threshold

    if not should_run:
        logger.debug(
            f"[{extraction.source_id}] LLM Judge skipped (conditional mode): "
            f"all HIGH confidence, {warning_count} warnings < {warning_threshold}"
        )

    return should_run


def _should_run_rag_grounding_for_source(job_config: Optional[Any]) -> bool:
    """Check if RAG Grounding should run (same logic as original)."""
    if job_config is None:
        return False

    if hasattr(job_config, "should_enable_rag_grounding"):
        return job_config.should_enable_rag_grounding()

    hall_config = getattr(job_config, "hallucination", None)
    if hall_config:
        return getattr(hall_config, "enable_rag_grounding", False)

    return False


def stage_semantic_extraction(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Extract semantic structure from all sources.

    PREREQUISITE: source_identity stage must run first to populate
    ctx.source_identity_packages with resolved identity data.

    This stage:
    1. Iterates over all SourceIdentityPackages (from source_identity stage)
    2. Uses pre-resolved analysis_mode (no guessing)
    3. Extracts semantic units using Gemini (PARALLEL)
    4. Validates extraction results
    5. Stores results in context (deterministic order)

    Performance: Uses ThreadPoolExecutor for parallel processing.
    Configure via SEMANTIC_EXTRACTION_MAX_WORKERS env var (default: 3).

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

    # Get max workers from config
    from backend.config import get_settings
    settings = get_settings()
    max_workers = min(settings.semantic_extraction_max_workers, len(packages))

    logger.info(
        f"[{ctx.job_id}] Processing {len(packages)} sources with "
        f"{max_workers} parallel workers"
    )

    # Get job_config for passing to threads
    job_config = getattr(ctx, "job_config", None)

    # Process sources in parallel with ThreadPoolExecutor
    source_results: list[SourceExtractionResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks with original index for deterministic ordering
        future_to_index = {
            executor.submit(
                process_single_source,
                package=pkg,
                index=i,
                job_config=job_config,
            ): i
            for i, pkg in enumerate(packages)
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            try:
                result = future.result()
                source_results.append(result)
            except Exception as e:
                # Should not happen as process_single_source handles exceptions
                idx = future_to_index[future]
                logger.error(f"Unexpected error processing package {idx}: {e}")
                source_results.append(SourceExtractionResult(
                    source_id=packages[idx].source_id,
                    index=idx,
                    status="failed",
                    warnings=[f"Unexpected executor error: {str(e)}"],
                ))

    # Sort results by original index for deterministic ordering
    source_results.sort(key=lambda r: r.index)

    # Merge results into context (deterministic order preserved)
    for result in source_results:
        # Add warnings to context
        for warning in result.warnings:
            ctx.add_warning(warning)

        # Add costs to context
        for cost_key, cost_value in result.costs.items():
            if hasattr(ctx, "add_cost"):
                ctx.add_cost(cost_key, cost_value)

        # Add extraction result if present
        if result.extraction_result:
            ctx.semantic_extractions.append(result.extraction_result)

        # Update counters
        if result.status == "processed":
            sources_processed += 1
        elif result.status == "skipped":
            sources_skipped += 1
        elif result.status == "failed":
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
