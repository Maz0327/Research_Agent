"""
Semantic Validation - 4-level validation for Research Agent outputs.

Based on: docs/authoritative/spec/Validation_and_Retry_Rules.md

Validation occurs at four levels:
1. Schema Validation (machine) - hard fail
2. Grounding Validation (machine) - hard fail
3. Structural Sufficiency (heuristic) - soft fail
4. Confidence Calibration (derived)

Principles (Non-Negotiable):
- Prefer honest thin output over padded output
- Never fabricate to satisfy quotas
- Retries are bounded
- Degradation is visible
- Failure is actionable
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loguru import logger

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    SemanticExtractionResult,
)
from backend.pipeline.mode_selector import (
    CONFIDENCE_CEILINGS,
    DEGRADED_QUOTE_MODES,
    NO_QUOTE_MODES,
    get_confidence_ceiling,
    get_quote_warning,
)


class ValidationLevel(str, Enum):
    """Severity of validation failure."""
    HARD_FAIL = "hard_fail"  # Job/stage cannot continue
    SOFT_FAIL = "soft_fail"  # Job continues with warnings
    WARNING = "warning"  # Minor issue, no action needed
    PASS = "pass"


class StageStatus(str, Enum):
    """Status of a pipeline stage after validation."""
    SUCCESS = "success"
    FAILED_WITH_WARNINGS = "failed_with_warnings"
    FAILED = "failed"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    level: ValidationLevel
    message: str
    field: Optional[str] = None
    details: Optional[dict] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "message": self.message,
            "field": self.field,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Complete validation report for an extraction or document."""
    results: list[ValidationResult] = field(default_factory=list)
    overall_status: StageStatus = StageStatus.SUCCESS
    confidence_ceiling: Optional[ConfidenceLevel] = None
    warnings: list[str] = field(default_factory=list)

    def add_result(self, result: ValidationResult) -> None:
        self.results.append(result)

        if result.level == ValidationLevel.HARD_FAIL:
            self.overall_status = StageStatus.FAILED
        elif result.level == ValidationLevel.SOFT_FAIL:
            if self.overall_status != StageStatus.FAILED:
                self.overall_status = StageStatus.FAILED_WITH_WARNINGS
            self.warnings.append(result.message)
        elif result.level == ValidationLevel.WARNING:
            self.warnings.append(result.message)

    @property
    def has_hard_failures(self) -> bool:
        return any(r.level == ValidationLevel.HARD_FAIL for r in self.results)

    @property
    def has_soft_failures(self) -> bool:
        return any(r.level == ValidationLevel.SOFT_FAIL for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "results": [r.to_dict() for r in self.results],
            "confidence_ceiling": (
                self.confidence_ceiling.value if self.confidence_ceiling else None
            ),
            "warnings": self.warnings,
        }


# -----------------------------------------------------------------------------
# Confidence Penalty Weights (Hallucination Prevention)
# -----------------------------------------------------------------------------

# HIGH confidence errors are penalized more severely than LOW confidence errors
# Rationale: An LLM claiming HIGH confidence when wrong is more problematic
CONFIDENCE_PENALTY_WEIGHTS = {
    ConfidenceLevel.HIGH: 3.0,    # 3x penalty for confident errors
    ConfidenceLevel.MEDIUM: 1.5,  # 1.5x penalty for medium confidence
    ConfidenceLevel.LOW: 1.0,     # Baseline penalty
}


def calculate_weighted_error_score(
    validation_results: list["ValidationResult"],
    extraction_data: dict,
) -> float:
    """Calculate error score weighted by confidence of affected items.

    Higher scores indicate more problematic extractions (high confidence + errors).

    Args:
        validation_results: List of validation results with errors
        extraction_data: The extraction data being validated

    Returns:
        Weighted error score (0.0 = no errors)
    """
    if not validation_results:
        return 0.0

    total_score = 0.0

    # Build confidence lookup for items
    item_confidences = {}
    for kp in extraction_data.get("key_points", []):
        kp_id = kp.get("key_point_id", "")
        conf_str = kp.get("confidence", "medium")
        try:
            item_confidences[kp_id] = ConfidenceLevel(conf_str.lower())
        except ValueError:
            item_confidences[kp_id] = ConfidenceLevel.MEDIUM

    for claim in extraction_data.get("claims", []):
        claim_id = claim.get("claim_id", "")
        conf_str = claim.get("confidence", "medium")
        try:
            item_confidences[claim_id] = ConfidenceLevel(conf_str.lower())
        except ValueError:
            item_confidences[claim_id] = ConfidenceLevel.MEDIUM

    # Calculate weighted score
    for result in validation_results:
        if result.level in (ValidationLevel.HARD_FAIL, ValidationLevel.SOFT_FAIL):
            base_score = 2.0 if result.level == ValidationLevel.HARD_FAIL else 1.0

            # Find affected item's confidence
            affected_conf = ConfidenceLevel.MEDIUM  # Default
            if result.details:
                item_id = (
                    result.details.get("key_point_id") or
                    result.details.get("claim_id") or
                    result.details.get("item_id", "")
                )
                if item_id in item_confidences:
                    affected_conf = item_confidences[item_id]

            # Apply weight
            weight = CONFIDENCE_PENALTY_WEIGHTS.get(affected_conf, 1.0)
            total_score += base_score * weight

        elif result.level == ValidationLevel.WARNING:
            total_score += 0.5

    return total_score


def should_downgrade_source_confidence(
    weighted_score: float,
    threshold: float = 5.0,
) -> bool:
    """Determine if source-level confidence should be downgraded.

    High weighted error scores suggest systematic extraction issues.

    Args:
        weighted_score: Result from calculate_weighted_error_score
        threshold: Score above which to recommend downgrade (default 5.0)

    Returns:
        True if source confidence should be downgraded
    """
    return weighted_score >= threshold


def get_confidence_penalty_summary(
    validation_results: list["ValidationResult"],
    extraction_data: dict,
) -> dict:
    """Get summary of confidence penalties applied.

    Args:
        validation_results: Validation results with errors
        extraction_data: The extraction data

    Returns:
        Summary dict with scores and recommendations
    """
    weighted_score = calculate_weighted_error_score(validation_results, extraction_data)
    should_downgrade = should_downgrade_source_confidence(weighted_score)

    # Count errors by confidence level
    high_conf_errors = 0
    medium_conf_errors = 0
    low_conf_errors = 0

    for result in validation_results:
        if result.level in (ValidationLevel.HARD_FAIL, ValidationLevel.SOFT_FAIL):
            if result.details:
                conf = result.details.get("confidence", "medium")
                if conf == "high":
                    high_conf_errors += 1
                elif conf == "medium":
                    medium_conf_errors += 1
                else:
                    low_conf_errors += 1

    return {
        "weighted_error_score": round(weighted_score, 2),
        "should_downgrade_source": should_downgrade,
        "high_confidence_errors": high_conf_errors,
        "medium_confidence_errors": medium_conf_errors,
        "low_confidence_errors": low_conf_errors,
        "threshold": 5.0,
    }


# -----------------------------------------------------------------------------
# Level 1: Schema Validation (Hard Fail)
# -----------------------------------------------------------------------------

def validate_schema(data: dict, required_keys: list[str]) -> list[ValidationResult]:
    """
    Validate that required keys exist and have correct types.

    Hard failure if:
    - Output is not valid dict
    - Required top-level keys are missing
    - IDs are malformed or missing
    """
    results = []

    if not isinstance(data, dict):
        results.append(ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message="Output is not a valid dictionary",
            field="root",
        ))
        return results

    for key in required_keys:
        if key not in data:
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message=f"Required key '{key}' is missing",
                field=key,
            ))

    return results


def validate_extraction_schema(data: dict) -> list[ValidationResult]:
    """Validate semantic extraction output schema."""
    required_keys = ["source_id", "analysis_mode", "key_points", "claims", "themes"]
    results = validate_schema(data, required_keys)

    # Validate ID formats
    for kp in data.get("key_points", []):
        if not isinstance(kp, dict) or "key_point_id" not in kp:
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message="Key point missing key_point_id",
                field="key_points",
                details=kp,
            ))

    for claim in data.get("claims", []):
        if not isinstance(claim, dict) or "claim_id" not in claim:
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message="Claim missing claim_id",
                field="claims",
                details=claim,
            ))
        elif not claim.get("source_id"):
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message=f"Claim {claim.get('claim_id')} has empty source_id",
                field="claims",
                details=claim,
            ))

    for theme in data.get("themes", []):
        if not isinstance(theme, dict) or "theme_id" not in theme:
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message="Theme missing theme_id",
                field="themes",
                details=theme,
            ))

    return results


# -----------------------------------------------------------------------------
# Level 2: Grounding Validation (Hard Fail with NO_QUOTE_MODES exceptions)
# -----------------------------------------------------------------------------

# Use mode_selector for quote rules (single source of truth)
# NO_QUOTE_MODES and DEGRADED_QUOTE_MODES imported from backend.pipeline.mode_selector
_NO_QUOTE_MODES_FOR_GROUNDING = NO_QUOTE_MODES
_DEGRADED_QUOTE_MODES = DEGRADED_QUOTE_MODES


def validate_grounding(
    data: dict,
    analysis_mode: AnalysisMode,
) -> list[ValidationResult]:
    """
    Validate that all assertions are properly grounded.

    Hard failure if:
    - A Key Point has no source references
    - A Claim has no supporting Quote (except NO_QUOTE_MODES)
    - A Theme references fewer than 2 Key Points

    NO_QUOTE_MODES exceptions (video_only, text_provided, ocr_extracted):
    - Claims are NOT required to have supporting Quotes
    - For video_only: Claims should have timestamp ranges + low confidence
    - For text_provided/ocr_extracted: No timestamp requirement (text content)
    """
    results = []

    # Validate Key Points have source references
    for kp in data.get("key_points", []):
        source_ids = kp.get("source_ids", [])
        if not source_ids:
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message=f"Key point {kp.get('key_point_id')} has no source references",
                field="key_points",
            ))

    # Validate Claims have supporting quotes (with mode-specific rules)
    for claim in data.get("claims", []):
        quotes = claim.get("supporting_quotes", [])
        timestamp = claim.get("timestamp_range")
        confidence = claim.get("confidence", "medium")

        if analysis_mode in _NO_QUOTE_MODES_FOR_GROUNDING:
            # video_only: NO quotes allowed, use observations with timestamps
            if not timestamp:
                results.append(ValidationResult(
                    level=ValidationLevel.SOFT_FAIL,
                    message=f"Claim {claim.get('claim_id')} in video_only mode missing timestamp_range",
                    field="claims",
                ))
            if confidence != "low":
                results.append(ValidationResult(
                    level=ValidationLevel.SOFT_FAIL,
                    message=f"Claim {claim.get('claim_id')} in video_only mode must have confidence: low",
                    field="claims",
                ))

        elif analysis_mode in _DEGRADED_QUOTE_MODES:
            # text_provided/ocr_extracted: quotes ALLOWED but with warnings
            # No requirement for quotes - they're optional
            # If quotes present, they'll be flagged with warnings in ceiling validation
            pass

        else:
            # Quote-required modes: quotes required for claims
            if not quotes:
                results.append(ValidationResult(
                    level=ValidationLevel.HARD_FAIL,
                    message=f"Claim {claim.get('claim_id')} has no supporting quotes",
                    field="claims",
                ))

    # Validate Themes reference at least 2 Key Points
    for theme in data.get("themes", []):
        related_kps = theme.get("related_key_points", [])
        if len(related_kps) < 2:
            results.append(ValidationResult(
                level=ValidationLevel.SOFT_FAIL,
                message=f"Theme {theme.get('theme_id')} has fewer than 2 key points ({len(related_kps)})",
                field="themes",
            ))

    # Validate Tensions have source_ids (provenance chain)
    for tension in data.get("tensions", []):
        tension_source_ids = tension.get("source_ids", [])
        if not tension_source_ids:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"Tension {tension.get('tension_id')} has no source_ids — provenance chain incomplete",
                field="tensions",
            ))

    return results


# -----------------------------------------------------------------------------
# Level 3: Structural Sufficiency (Soft Fail)
# -----------------------------------------------------------------------------

def validate_structural_sufficiency(
    data: dict,
    source_word_count: Optional[int] = None,
    source_duration_minutes: Optional[float] = None,
) -> list[ValidationResult]:
    """
    Evaluate output relative to corpus size and diversity.

    Soft fail if:
    - Long source (≥30 min or ≥3k words) with <3 Key Points
    - All Key Points come from single source
    - Themes collapse into single category
    - No Gaps identified in non-trivial topic
    - Verification rate <50%
    """
    results = []

    key_points = data.get("key_points", [])
    themes = data.get("themes", [])
    gaps = data.get("gaps", [])

    is_long_form = (
        (source_word_count and source_word_count >= 3000) or
        (source_duration_minutes and source_duration_minutes >= 30)
    )

    # Check key point count for long-form content
    if is_long_form and len(key_points) < 3:
        results.append(ValidationResult(
            level=ValidationLevel.SOFT_FAIL,
            message=f"Long-form source with only {len(key_points)} key points (minimum 3)",
            field="key_points",
        ))

    # Check if all key points from single source
    source_ids = set()
    for kp in key_points:
        source_ids.update(kp.get("source_ids", []))

    if len(source_ids) == 1 and len(key_points) > 1:
        results.append(ValidationResult(
            level=ValidationLevel.WARNING,
            message="All key points from single source - limited perspective",
            field="key_points",
        ))

    # Check theme diversity
    if len(themes) < 2 and len(key_points) >= 4:
        results.append(ValidationResult(
            level=ValidationLevel.SOFT_FAIL,
            message=f"Only {len(themes)} themes despite {len(key_points)} key points",
            field="themes",
        ))

    # Check for gaps in multi-source corpus
    if len(source_ids) > 1 and len(gaps) < 3:
        results.append(ValidationResult(
            level=ValidationLevel.WARNING,
            message=f"Only {len(gaps)} gaps identified for multi-source corpus (expect 3-7)",
            field="gaps",
        ))

    return results


# -----------------------------------------------------------------------------
# Level 4: Confidence Calibration
# -----------------------------------------------------------------------------

def calibrate_confidence(
    data: dict,
    analysis_mode: AnalysisMode,
    source_count: int = 1,
    verification_rate: float = 0.0,
) -> tuple[ConfidenceLevel, list[str]]:
    """
    Derive confidence level based on validation signals.

    Confidence Ceiling Enforcement (Machine-Checked):
    | Analysis Mode | Max Confidence |
    |---------------|----------------|
    | transcript_grounded | high |
    | caption_grounded | medium |
    | video_only | low |

    High Confidence:
    - ≥2 sources
    - Verification rate ≥70%
    - No unresolved critical tensions

    Medium Confidence:
    - Limited sources
    - Partial verification
    - Some unresolved tensions

    Low Confidence:
    - Single perspective
    - Thin extraction
    - High uncertainty
    """
    reasons = []

    # Apply mode ceiling - all 6 analysis modes (Phase 2B)
    mode_ceilings = {
        AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
        AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
        AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
        AnalysisMode.TEXT_PROVIDED: ConfidenceLevel.MEDIUM,
        AnalysisMode.OCR_EXTRACTED: ConfidenceLevel.MEDIUM,
        AnalysisMode.ARTICLE_FETCHED: ConfidenceLevel.HIGH,
    }
    ceiling = mode_ceilings.get(analysis_mode, ConfidenceLevel.LOW)

    # Calculate base confidence
    tensions = data.get("tensions", [])
    key_points = data.get("key_points", [])

    if source_count >= 2 and verification_rate >= 0.7 and len(tensions) == 0:
        base_confidence = ConfidenceLevel.HIGH
        reasons.append("Multiple sources with high verification rate")
    elif source_count >= 1 and verification_rate >= 0.5:
        base_confidence = ConfidenceLevel.MEDIUM
        reasons.append("Partial verification with some limitations")
    else:
        base_confidence = ConfidenceLevel.LOW
        reasons.append("Limited sources or verification")

    # Check for thin extraction
    if len(key_points) < 3:
        base_confidence = ConfidenceLevel.LOW
        reasons.append("Thin extraction (fewer than 3 key points)")

    # Check for unresolved tensions
    if len(tensions) > 2:
        if base_confidence == ConfidenceLevel.HIGH:
            base_confidence = ConfidenceLevel.MEDIUM
        reasons.append(f"{len(tensions)} unresolved tensions")

    # Apply ceiling
    confidence_order = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
    ceiling_idx = confidence_order.index(ceiling)
    base_idx = confidence_order.index(base_confidence)

    if base_idx > ceiling_idx:
        reasons.append(
            f"Confidence capped at {ceiling.value} due to {analysis_mode.value} mode"
        )
        return ceiling, reasons

    return base_confidence, reasons


# -----------------------------------------------------------------------------
# Mode-Based Ceiling Enforcement (Phase 2B)
# -----------------------------------------------------------------------------

# NOTE: Mode configurations (NO_QUOTE_MODES, DEGRADED_QUOTE_MODES, CONFIDENCE_CEILINGS)
# are now imported from backend.pipeline.mode_selector (single source of truth).
# See imports at top of file.


def validate_confidence_ceiling(
    data: dict,
    analysis_mode: AnalysisMode,
    has_source_metadata: bool = False,
) -> list[ValidationResult]:
    """
    Enforce mode-based confidence ceilings and quote warnings.

    Quote Rules:
    - video_only: HARD FAIL if quotes exist (must use observations)
    - text_provided/ocr_extracted: Quotes ALLOWED with warnings
    - Other modes: Quotes required (no warning)

    Args:
        data: Semantic extraction output dict
        analysis_mode: One of the 6 analysis modes
        has_source_metadata: True if user provided source info (URL, author, title)

    Returns:
        List of validation results (may include auto-fix notes)
    """
    results = []
    ceiling = CONFIDENCE_CEILINGS.get(analysis_mode, ConfidenceLevel.LOW)

    # Count all quotes
    quotes = data.get("quotes", [])
    supporting_quotes = []
    for claim in data.get("claims", []):
        sq = claim.get("supporting_quotes", [])
        if sq:
            supporting_quotes.extend(sq)
    quote_count = len(quotes) + len(supporting_quotes)

    # Check for quotes in FORBIDDEN mode (video_only only)
    if analysis_mode in NO_QUOTE_MODES:
        if quote_count > 0:
            results.append(ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message=(
                    f"QUOTES NOT ALLOWED in {analysis_mode.value} mode. "
                    f"Found {quote_count} quote(s). Use approximate_observations instead."
                ),
                field="quotes",
                details={
                    "analysis_mode": analysis_mode.value,
                    "quotes_found": len(quotes),
                    "supporting_quotes_found": len(supporting_quotes),
                },
            ))

    # Check for quotes in DEGRADED mode (text_provided, ocr_extracted)
    elif analysis_mode in DEGRADED_QUOTE_MODES and quote_count > 0:
        # Quotes allowed but add warning
        if analysis_mode == AnalysisMode.TEXT_PROVIDED:
            if has_source_metadata:
                warning_msg = (
                    f"User-provided source with {quote_count} quote(s). "
                    "Accuracy unconfirmed by system. User should verify quotes match original."
                )
            else:
                warning_msg = (
                    f"Source not identified. {quote_count} quote(s) extracted from user-pasted text. "
                    "Cannot verify authenticity. User should confirm source and quote accuracy."
                )
        else:  # OCR_EXTRACTED
            warning_msg = (
                f"OCR-extracted content with {quote_count} quote(s). "
                "May contain transcription errors. User should verify accuracy."
            )

        results.append(ValidationResult(
            level=ValidationLevel.WARNING,
            message=warning_msg,
            field="quotes",
            details={
                "analysis_mode": analysis_mode.value,
                "quote_count": quote_count,
                "has_source_metadata": has_source_metadata,
                "_quote_accuracy_unverified": True,
            },
        ))

        # Mark all quotes as unverified
        for quote in quotes:
            quote["_accuracy_unverified"] = True
            quote["_verification_warning"] = warning_msg

    # Auto-downgrade confidence if above ceiling
    confidence_order = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
    ceiling_idx = confidence_order.index(ceiling)

    for kp in data.get("key_points", []):
        kp_confidence = kp.get("confidence", "medium")
        try:
            kp_level = ConfidenceLevel(kp_confidence)
            kp_idx = confidence_order.index(kp_level)

            if kp_idx > ceiling_idx:
                # Auto-downgrade
                kp["confidence"] = ceiling.value
                kp["_confidence_downgraded"] = True
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=(
                        f"Key point {kp.get('key_point_id')} confidence downgraded "
                        f"from {kp_confidence} to {ceiling.value} (mode ceiling)"
                    ),
                    field="key_points",
                ))
        except ValueError:
            # Invalid confidence value - will be caught by schema validation
            pass

    for claim in data.get("claims", []):
        claim_confidence = claim.get("confidence", "medium")
        try:
            claim_level = ConfidenceLevel(claim_confidence)
            claim_idx = confidence_order.index(claim_level)

            if claim_idx > ceiling_idx:
                # Auto-downgrade
                claim["confidence"] = ceiling.value
                claim["_confidence_downgraded"] = True
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=(
                        f"Claim {claim.get('claim_id')} confidence downgraded "
                        f"from {claim_confidence} to {ceiling.value} (mode ceiling)"
                    ),
                    field="claims",
                ))
        except ValueError:
            pass

    return results


# -----------------------------------------------------------------------------
# Hallucination Prevention: Timestamp Validation (TV-001)
# -----------------------------------------------------------------------------

def validate_timestamp_bounds(
    timestamps: list[str],
    duration_seconds: int,
    tolerance_seconds: int = 30,
) -> tuple[list[str], list[str]]:
    """
    Validate and fix timestamps that exceed video duration.

    Rule TV-001: Timestamps must not exceed video duration.
    - Soft fail: timestamps exceeding duration are clamped
    - Warning: Invalid format timestamps are preserved with warning

    Args:
        timestamps: List of timestamp strings (e.g., "1:23", "1:23:45")
        duration_seconds: Video duration in seconds
        tolerance_seconds: Allow timestamps up to this much past duration (default 30s)

    Returns:
        Tuple of (fixed_timestamps, warnings)
    """
    warnings = []
    fixed = []

    for ts in timestamps:
        try:
            parts = ts.split(":")
            if len(parts) == 2:
                # MM:SS format
                seconds = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                # HH:MM:SS format
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                warnings.append(f"Invalid timestamp format: {ts}")
                fixed.append(ts)
                continue

            if seconds > duration_seconds + tolerance_seconds:
                warnings.append(
                    f"Timestamp {ts} ({seconds}s) exceeds duration {duration_seconds}s, "
                    f"clamping to duration"
                )
                # Clamp to duration
                hours, remainder = divmod(duration_seconds, 3600)
                mins, secs = divmod(remainder, 60)
                if hours > 0:
                    ts = f"{hours}:{mins:02d}:{secs:02d}"
                else:
                    ts = f"{mins}:{secs:02d}"

            fixed.append(ts)

        except (ValueError, IndexError) as e:
            warnings.append(f"Invalid timestamp format '{ts}': {e}")
            fixed.append(ts)

    if warnings:
        logger.warning(f"Timestamp validation: {len(warnings)} issues found")

    return fixed, warnings


def validate_clip_timestamps(
    clips: list[dict],
    duration_seconds: int,
) -> tuple[list[dict], list[str]]:
    """
    Validate timestamps in clip objects.

    Args:
        clips: List of clip dicts with start_time/end_time fields
        duration_seconds: Video duration in seconds

    Returns:
        Tuple of (validated_clips, warnings)
    """
    warnings = []

    for clip in clips:
        clip_id = clip.get("clip_id", "UNKNOWN")

        # Validate start_time
        start = clip.get("start_time", "")
        if start:
            fixed_starts, start_warnings = validate_timestamp_bounds(
                [start], duration_seconds
            )
            if start_warnings:
                warnings.extend([f"Clip {clip_id} start: {w}" for w in start_warnings])
                clip["start_time"] = fixed_starts[0]
                clip["_timestamp_clamped"] = True

        # Validate end_time
        end = clip.get("end_time", "")
        if end:
            fixed_ends, end_warnings = validate_timestamp_bounds(
                [end], duration_seconds
            )
            if end_warnings:
                warnings.extend([f"Clip {clip_id} end: {w}" for w in end_warnings])
                clip["end_time"] = fixed_ends[0]
                clip["_timestamp_clamped"] = True

    return clips, warnings


# -----------------------------------------------------------------------------
# Hallucination Prevention: Citation Validation (CV-001)
# -----------------------------------------------------------------------------

def validate_based_on_references(
    assertions: list[dict],
    valid_ids: set[str],
) -> tuple[list[dict], list[str]]:
    """
    Validate that based_on references point to existing IDs.

    Rule CV-001: Citation IDs must exist - hard fail removes invalid refs.

    Args:
        assertions: List of assertion dicts with "based_on" field
        valid_ids: Set of valid IDs that can be referenced

    Returns:
        Tuple of (validated_assertions, warnings)
    """
    warnings = []
    valid_assertions = []

    for assertion in assertions:
        based_on = assertion.get("based_on", [])

        # Skip if no references
        if not based_on:
            valid_assertions.append(assertion)
            continue

        # Separate valid and invalid references
        valid_refs = [ref for ref in based_on if ref in valid_ids]
        invalid_refs = [ref for ref in based_on if ref not in valid_ids]

        if invalid_refs:
            assertion_id = assertion.get("key_point_id") or assertion.get("claim_id") or "UNKNOWN"
            warning = f"Assertion {assertion_id}: removed invalid refs {invalid_refs}"
            warnings.append(warning)
            logger.warning(warning)
            assertion["_validation_warning"] = f"Removed invalid refs: {invalid_refs}"
            assertion["_removed_refs"] = invalid_refs

        assertion["based_on"] = valid_refs

        # Only keep if at least one valid reference remains
        if valid_refs:
            valid_assertions.append(assertion)
        else:
            # All references were invalid - keep assertion but mark it
            assertion["_all_refs_invalid"] = True
            assertion["confidence"] = "low"  # Downgrade confidence
            valid_assertions.append(assertion)
            warnings.append(
                f"Assertion {assertion.get('key_point_id', 'UNKNOWN')}: "
                "all based_on refs invalid, confidence downgraded to low"
            )

    return valid_assertions, warnings


def collect_valid_ids(data: dict) -> set[str]:
    """
    Collect all valid IDs from extraction data for citation validation.

    Args:
        data: Semantic extraction output dict

    Returns:
        Set of valid IDs (SRC_*, QUOTE_*, CLIP_*, etc.)
    """
    valid_ids = set()

    # Source IDs
    source_id = data.get("source_id")
    if source_id:
        valid_ids.add(source_id)

    # Quote IDs
    for quote in data.get("quotes", []):
        quote_id = quote.get("quote_id")
        if quote_id:
            valid_ids.add(quote_id)

    # Clip IDs
    for clip in data.get("clips", []):
        clip_id = clip.get("clip_id")
        if clip_id:
            valid_ids.add(clip_id)

    # Key Point IDs
    for kp in data.get("key_points", []):
        kp_id = kp.get("key_point_id")
        if kp_id:
            valid_ids.add(kp_id)

    # Claim IDs
    for claim in data.get("claims", []):
        claim_id = claim.get("claim_id")
        if claim_id:
            valid_ids.add(claim_id)

    # Theme IDs
    for theme in data.get("themes", []):
        theme_id = theme.get("theme_id")
        if theme_id:
            valid_ids.add(theme_id)

    return valid_ids


# -----------------------------------------------------------------------------
# Combined Validation
# -----------------------------------------------------------------------------

def validate_semantic_extraction(
    data: dict,
    analysis_mode: AnalysisMode,
    source_word_count: Optional[int] = None,
    source_duration_minutes: Optional[float] = None,
    has_source_metadata: bool = False,
    verification_rate: Optional[float] = None,
) -> ValidationReport:
    """
    Run all validation levels on semantic extraction output.

    Args:
        data: Raw extraction output dict
        analysis_mode: How source was analyzed
        source_word_count: Word count of source (for long-form detection)
        source_duration_minutes: Duration in minutes (for video)
        has_source_metadata: True if user provided source info (URL, author, title)
                             Used for quote warning messages in text_provided mode
        verification_rate: Quote verification rate (0.0 to 1.0). If None, defaults to 0.5.
                          Calculated by stage_semantic_validation from actual quote checks.

    Returns:
        ValidationReport with all results and overall status
    """
    report = ValidationReport()

    # Level 1: Schema
    logger.debug("Running schema validation...")
    schema_results = validate_extraction_schema(data)
    for result in schema_results:
        report.add_result(result)

    if report.has_hard_failures:
        logger.warning("Schema validation failed, skipping remaining validations")
        return report

    # Level 2: Grounding
    logger.debug("Running grounding validation...")
    grounding_results = validate_grounding(data, analysis_mode)
    for result in grounding_results:
        report.add_result(result)

    # Level 2.5: Mode-Based Ceiling Enforcement (Phase 2B)
    logger.debug("Running ceiling enforcement validation...")
    ceiling_results = validate_confidence_ceiling(data, analysis_mode, has_source_metadata)
    for result in ceiling_results:
        report.add_result(result)

    # If ceiling validation has hard failures (quotes in no-quote mode), stop
    if any(r.level == ValidationLevel.HARD_FAIL for r in ceiling_results):
        logger.warning("Ceiling validation failed - quotes found in non-quote mode")
        return report

    # Level 3: Structural Sufficiency
    logger.debug("Running structural sufficiency validation...")
    sufficiency_results = validate_structural_sufficiency(
        data,
        source_word_count=source_word_count,
        source_duration_minutes=source_duration_minutes,
    )
    for result in sufficiency_results:
        report.add_result(result)

    # Level 4: Confidence Calibration
    logger.debug("Calibrating confidence...")
    # Use actual verification rate if provided, otherwise default to 0.5
    actual_rate = verification_rate if verification_rate is not None else 0.5
    confidence, reasons = calibrate_confidence(
        data,
        analysis_mode,
        source_count=1,  # Single source extraction
        verification_rate=actual_rate,
    )
    report.confidence_ceiling = confidence
    for reason in reasons:
        report.add_result(ValidationResult(
            level=ValidationLevel.WARNING,
            message=f"Confidence: {reason}",
            field="confidence",
        ))

    logger.info(
        f"Validation complete: status={report.overall_status.value}, "
        f"confidence={confidence.value}, warnings={len(report.warnings)}"
    )

    return report


def should_retry(report: ValidationReport) -> bool:
    """
    Determine if extraction should be retried based on validation.

    Retry triggers:
    - Invalid JSON (schema fail)
    - Missing required fields
    - Structural thinness
    - Over-abstract output

    Max 1 retry per stage.
    """
    # Never retry hard failures except schema issues
    schema_fails = [
        r for r in report.results
        if r.level == ValidationLevel.HARD_FAIL and r.field in ("root", "key_points", "claims")
    ]

    if schema_fails:
        return True

    # Retry for structural thinness
    thin_output = [
        r for r in report.results
        if r.level == ValidationLevel.SOFT_FAIL and "thin" in r.message.lower()
    ]

    return len(thin_output) > 0
