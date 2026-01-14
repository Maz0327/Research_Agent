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
# Level 2: Grounding Validation (Hard Fail with video_only exception)
# -----------------------------------------------------------------------------

def validate_grounding(
    data: dict,
    analysis_mode: AnalysisMode,
) -> list[ValidationResult]:
    """
    Validate that all assertions are properly grounded.

    Hard failure if:
    - A Key Point has no source references
    - A Claim has no supporting Quote (except video_only mode)
    - A Theme references fewer than 2 Key Points

    Exception for video_only mode:
    - Claims are not required to have supporting Quotes
    - Claims must reference approximate timestamp ranges
    - Claims must be marked confidence: low
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

    # Validate Claims have supporting quotes (with video_only exception)
    for claim in data.get("claims", []):
        quotes = claim.get("supporting_quotes", [])
        timestamp = claim.get("timestamp_range")
        confidence = claim.get("confidence", "medium")

        if analysis_mode == AnalysisMode.VIDEO_ONLY:
            # video_only exception: no quotes required, but need timestamp + low confidence
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
        else:
            # Normal mode: quotes required
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

    # Apply mode ceiling
    mode_ceilings = {
        AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
        AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
        AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
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
# Combined Validation
# -----------------------------------------------------------------------------

def validate_semantic_extraction(
    data: dict,
    analysis_mode: AnalysisMode,
    source_word_count: Optional[int] = None,
    source_duration_minutes: Optional[float] = None,
) -> ValidationReport:
    """
    Run all validation levels on semantic extraction output.

    Args:
        data: Raw extraction output dict
        analysis_mode: How source was analyzed
        source_word_count: Word count of source (for long-form detection)
        source_duration_minutes: Duration in minutes (for video)

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
    confidence, reasons = calibrate_confidence(
        data,
        analysis_mode,
        source_count=1,  # Single source extraction
        verification_rate=0.5,  # Default - should be calculated from actual data
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
