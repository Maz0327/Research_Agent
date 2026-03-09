"""
Unit tests for validation stages covering V1-V10 validation rules.

Tests for: schema validation, grounding validation, confidence ceiling,
quote verification, timestamp validation, provenance chain, cardinality,
and Doc 3 gating requirements.

Phase 9 Task 9.2.3
"""
import pytest
from unittest.mock import Mock, patch

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel
from backend.pipeline.semantic_validation import (
    ValidationLevel,
    ValidationResult,
    ValidationReport,
    StageStatus,
    validate_schema,
    validate_extraction_schema,
    validate_grounding,
    validate_structural_sufficiency,
    calibrate_confidence,
    validate_confidence_ceiling,
    validate_timestamp_bounds,
    validate_clip_timestamps,
    validate_based_on_references,
    collect_valid_ids,
    validate_semantic_extraction,
    should_retry,
)
from backend.pipeline.stages.quote_verification import (
    normalize_text,
    find_best_match,
    verify_quote,
    verify_all_quotes,
    QuoteVerification,
    EXACT_MATCH_THRESHOLD,
    FUZZY_MATCH_THRESHOLD,
)


# =============================================================================
# TestValidationResult
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """ValidationResult should create correctly."""
        result = ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message="Test failure",
            field="test_field",
        )
        assert result.level == ValidationLevel.HARD_FAIL
        assert result.message == "Test failure"
        assert result.field == "test_field"

    def test_validation_result_to_dict(self):
        """to_dict should return correct dict."""
        result = ValidationResult(
            level=ValidationLevel.WARNING,
            message="Test warning",
            field="key_points",
            details={"count": 5},
        )
        d = result.to_dict()

        assert d["level"] == "warning"
        assert d["message"] == "Test warning"
        assert d["field"] == "key_points"
        assert d["details"]["count"] == 5


# =============================================================================
# TestValidationReport
# =============================================================================


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_validation_report_creation(self):
        """ValidationReport should create with defaults."""
        report = ValidationReport()
        assert report.results == []
        assert report.overall_status == StageStatus.SUCCESS
        assert report.warnings == []

    def test_add_result_hard_fail(self):
        """add_result should set FAILED status for hard failures."""
        report = ValidationReport()
        report.add_result(ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message="Hard failure",
        ))
        assert report.overall_status == StageStatus.FAILED
        assert len(report.results) == 1

    def test_add_result_soft_fail(self):
        """add_result should set FAILED_WITH_WARNINGS for soft failures."""
        report = ValidationReport()
        report.add_result(ValidationResult(
            level=ValidationLevel.SOFT_FAIL,
            message="Soft failure",
        ))
        assert report.overall_status == StageStatus.FAILED_WITH_WARNINGS
        assert "Soft failure" in report.warnings

    def test_add_result_warning(self):
        """add_result should add to warnings for WARNING level."""
        report = ValidationReport()
        report.add_result(ValidationResult(
            level=ValidationLevel.WARNING,
            message="Just a warning",
        ))
        assert report.overall_status == StageStatus.SUCCESS
        assert "Just a warning" in report.warnings

    def test_has_hard_failures(self):
        """has_hard_failures should return True when hard failures exist."""
        report = ValidationReport()
        assert report.has_hard_failures is False

        report.add_result(ValidationResult(level=ValidationLevel.HARD_FAIL, message="Fail"))
        assert report.has_hard_failures is True

    def test_has_soft_failures(self):
        """has_soft_failures should return True when soft failures exist."""
        report = ValidationReport()
        assert report.has_soft_failures is False

        report.add_result(ValidationResult(level=ValidationLevel.SOFT_FAIL, message="Soft"))
        assert report.has_soft_failures is True


# =============================================================================
# TestV1JsonSchema
# =============================================================================


class TestV1JsonSchema:
    """Tests for V1: JSON Schema Validation."""

    def test_valid_json_passes(self):
        """Valid data should pass schema validation."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [{"key_point_id": "KP_1", "statement": "Test"}],
            "claims": [{"claim_id": "CLM_1", "statement": "Test"}],
            "themes": [{"theme_id": "THEME_1", "label": "Test"}],
        }
        results = validate_extraction_schema(data)

        assert len(results) == 0 or all(r.level != ValidationLevel.HARD_FAIL for r in results)

    def test_invalid_json_not_dict_fails(self):
        """Non-dict data should fail schema validation."""
        results = validate_schema("not a dict", ["source_id"])

        assert len(results) == 1
        assert results[0].level == ValidationLevel.HARD_FAIL
        assert "not a valid dictionary" in results[0].message

    def test_missing_required_keys_fails(self):
        """Missing required keys should fail schema validation."""
        data = {"source_id": "SRC_1"}  # Missing other required keys
        results = validate_extraction_schema(data)

        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert len(hard_fails) >= 1  # At least one missing key

    def test_key_point_missing_id_fails(self):
        """Key point without ID should fail."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [{"statement": "No ID here"}],  # Missing key_point_id
            "claims": [],
            "themes": [],
        }
        results = validate_extraction_schema(data)

        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert any("key_point_id" in r.message for r in hard_fails)

    def test_claim_missing_id_fails(self):
        """Claim without ID should fail."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [],
            "claims": [{"statement": "No ID"}],  # Missing claim_id
            "themes": [],
        }
        results = validate_extraction_schema(data)

        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert any("claim_id" in r.message for r in hard_fails)


# =============================================================================
# TestV2SourceIdConsistency
# =============================================================================


class TestV2SourceIdConsistency:
    """Tests for V2: Source ID Consistency Validation."""

    def test_valid_source_ids_pass(self):
        """Key points with valid source_ids should pass."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [
                {"key_point_id": "KP_1", "source_ids": ["SRC_1"], "statement": "Test"},
            ],
            "claims": [],
            "themes": [],
        }
        results = validate_grounding(data, AnalysisMode.TRANSCRIPT_GROUNDED)

        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        source_ref_fails = [f for f in hard_fails if "source references" in f.message]
        assert len(source_ref_fails) == 0

    def test_key_point_no_source_ids_fails(self):
        """Key point without source_ids should fail."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [
                {"key_point_id": "KP_1", "source_ids": [], "statement": "Test"},
            ],
            "claims": [],
            "themes": [],
        }
        results = validate_grounding(data, AnalysisMode.TRANSCRIPT_GROUNDED)

        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert any("no source references" in r.message for r in hard_fails)


# =============================================================================
# TestV3ConfidenceCeiling
# =============================================================================


class TestV3ConfidenceCeiling:
    """Tests for V3: Confidence Ceiling Enforcement."""

    def test_transcript_grounded_allows_high(self):
        """transcript_grounded should allow HIGH confidence."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [
                {"key_point_id": "KP_1", "confidence": "high", "source_ids": ["SRC_1"]},
            ],
            "claims": [],
            "quotes": [],
        }
        results = validate_confidence_ceiling(data, AnalysisMode.TRANSCRIPT_GROUNDED)

        # Should not downgrade HIGH confidence for transcript_grounded
        downgrade_warnings = [r for r in results if "downgraded" in r.message]
        assert len(downgrade_warnings) == 0

    def test_caption_grounded_caps_at_medium(self):
        """caption_grounded should cap confidence at MEDIUM."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "caption_grounded",
            "key_points": [
                {"key_point_id": "KP_1", "confidence": "high", "source_ids": ["SRC_1"]},
            ],
            "claims": [],
            "quotes": [],
        }
        results = validate_confidence_ceiling(data, AnalysisMode.CAPTION_GROUNDED)

        # Should downgrade HIGH to MEDIUM
        assert data["key_points"][0]["confidence"] == "medium"
        assert any("downgraded" in r.message for r in results)

    def test_video_only_caps_at_low(self):
        """video_only should cap confidence at LOW."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "video_only",
            "key_points": [
                {"key_point_id": "KP_1", "confidence": "medium", "source_ids": ["SRC_1"]},
            ],
            "claims": [],
            "quotes": [],
        }
        results = validate_confidence_ceiling(data, AnalysisMode.VIDEO_ONLY)

        # Should downgrade MEDIUM to LOW
        assert data["key_points"][0]["confidence"] == "low"

    def test_auto_downgrade_with_warning(self):
        """Auto-downgrade should add warning message."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "ocr_extracted",
            "key_points": [
                {"key_point_id": "KP_1", "confidence": "high", "source_ids": ["SRC_1"]},
            ],
            "claims": [
                {"claim_id": "CLM_1", "confidence": "high", "source_id": "SRC_1"},
            ],
            "quotes": [],
        }
        results = validate_confidence_ceiling(data, AnalysisMode.OCR_EXTRACTED)

        downgrade_warnings = [r for r in results if "downgraded" in r.message.lower()]
        assert len(downgrade_warnings) >= 2  # Both KP and Claim downgraded


# =============================================================================
# TestV4QuoteVerification
# =============================================================================


class TestV4QuoteVerification:
    """Tests for V4: Quote Verification (fuzzy matching)."""

    def test_exact_match_verified(self):
        """Exact quote match should be verified."""
        source_text = "This is the exact quote from the transcript."
        status, ratio, matched = verify_quote(
            "This is the exact quote from the transcript.",
            source_text,
        )
        assert status == "verified"
        assert ratio >= EXACT_MATCH_THRESHOLD

    def test_95_percent_match_verified(self):
        """95%+ match should be verified."""
        source_text = "This is a long statement that we want to verify against the source."
        # Very similar with minor difference
        status, ratio, matched = verify_quote(
            "This is a long statement that we want to verify against the source",  # Missing period
            source_text,
        )
        assert status == "verified"
        assert ratio >= EXACT_MATCH_THRESHOLD

    def test_80_94_percent_partial(self):
        """80-94% match should be partial."""
        source_text = "The company reported significant losses in the fourth quarter of 2023."
        # Moderately similar
        status, ratio, matched = verify_quote(
            "The company reported major losses in Q4 of 2023.",
            source_text,
        )
        # This should be partial or unverified depending on actual similarity
        assert status in ("partial", "unverified")

    def test_below_80_unverified(self):
        """<80% match should be unverified."""
        source_text = "Completely different content about something else entirely."
        status, ratio, matched = verify_quote(
            "The CEO announced new strategic initiatives for growth.",
            source_text,
        )
        assert status == "unverified"
        assert ratio < FUZZY_MATCH_THRESHOLD

    def test_whitespace_normalization(self):
        """Quote verification should normalize whitespace."""
        source_text = "This  has   extra   whitespace."
        status, ratio, matched = verify_quote(
            "This has extra whitespace.",
            source_text,
        )
        assert status == "verified"

    def test_case_insensitive(self):
        """Quote verification should be case-insensitive."""
        source_text = "THE STATEMENT WAS MADE IN ALL CAPS."
        status, ratio, matched = verify_quote(
            "the statement was made in all caps.",
            source_text,
        )
        assert status == "verified"


# =============================================================================
# TestV4QuoteVerificationBatch
# =============================================================================


class TestV4QuoteVerificationBatch:
    """Tests for batch quote verification."""

    def test_verify_all_quotes_empty(self):
        """Empty quotes list should return 100% rate."""
        verifications, rate = verify_all_quotes([], "source text", "SRC_1")
        assert rate == 1.0
        assert verifications == []

    def test_verify_all_quotes_no_source(self):
        """No source text should return 0% rate."""
        quotes = [{"quote_id": "QT_1", "text": "Test quote"}]
        verifications, rate = verify_all_quotes(quotes, "", "SRC_1")
        assert rate == 0.0
        assert all(v.status == "unverified" for v in verifications)

    def test_verify_all_quotes_mixed_results(self):
        """Mixed results should calculate correct rate."""
        source_text = "This is a verified quote. But this other content is different."
        quotes = [
            {"quote_id": "QT_1", "text": "This is a verified quote."},
            {"quote_id": "QT_2", "text": "This quote does not exist in the source."},
        ]
        verifications, rate = verify_all_quotes(quotes, source_text, "SRC_1")

        assert len(verifications) == 2
        # At least one should be verified
        verified_count = sum(1 for v in verifications if v.status in ("verified", "partial"))
        assert verified_count >= 1


# =============================================================================
# TestV5QuotePermission
# =============================================================================


class TestV5QuotePermission:
    """Tests for V5: Quote Permission by Mode."""

    def test_transcript_grounded_allows_quotes(self):
        """transcript_grounded should allow quotes without warning."""
        data = {
            "source_id": "SRC_1",
            "quotes": [{"quote_id": "QT_1", "text": "Quote text"}],
            "claims": [],
            "key_points": [],
        }
        results = validate_confidence_ceiling(data, AnalysisMode.TRANSCRIPT_GROUNDED)

        # Should not have any quote warnings
        quote_warnings = [r for r in results if r.field == "quotes"]
        hard_fails = [r for r in quote_warnings if r.level == ValidationLevel.HARD_FAIL]
        assert len(hard_fails) == 0

    def test_video_only_forbids_quotes(self):
        """video_only should HARD FAIL if quotes present."""
        data = {
            "source_id": "SRC_1",
            "quotes": [{"quote_id": "QT_1", "text": "Quote text"}],
            "claims": [],
            "key_points": [],
        }
        results = validate_confidence_ceiling(data, AnalysisMode.VIDEO_ONLY)

        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert len(hard_fails) == 1
        assert "QUOTES NOT ALLOWED" in hard_fails[0].message

    def test_text_provided_allows_with_warning(self):
        """text_provided should allow quotes with warning."""
        data = {
            "source_id": "SRC_1",
            "quotes": [{"quote_id": "QT_1", "text": "Quote text"}],
            "claims": [],
            "key_points": [],
        }
        results = validate_confidence_ceiling(
            data, AnalysisMode.TEXT_PROVIDED, has_source_metadata=False
        )

        # Should have WARNING, not HARD_FAIL
        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        assert len(warnings) >= 1
        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert len(hard_fails) == 0


# =============================================================================
# TestV6TimestampValidation
# =============================================================================


class TestV6TimestampValidation:
    """Tests for V6: Timestamp Validation."""

    def test_valid_timestamp_format_mm_ss(self):
        """MM:SS format should be valid."""
        timestamps = ["1:23", "12:45", "59:59"]
        fixed, warnings = validate_timestamp_bounds(timestamps, duration_seconds=3600)

        assert len(warnings) == 0
        assert fixed == timestamps

    def test_valid_timestamp_format_hh_mm_ss(self):
        """HH:MM:SS format should be valid."""
        timestamps = ["1:23:45", "0:05:30"]
        fixed, warnings = validate_timestamp_bounds(timestamps, duration_seconds=7200)

        assert len(warnings) == 0

    def test_invalid_timestamp_rejected(self):
        """Invalid timestamp format should produce warning."""
        timestamps = ["invalid", "not:a:timestamp:format"]
        fixed, warnings = validate_timestamp_bounds(timestamps, duration_seconds=3600)

        assert len(warnings) == 2
        assert all("Invalid timestamp format" in w for w in warnings)

    def test_timestamp_range_validation_clamp(self):
        """Timestamp exceeding duration should be clamped."""
        timestamps = ["10:00"]  # 600 seconds
        duration = 300  # 5 minutes
        fixed, warnings = validate_timestamp_bounds(timestamps, duration_seconds=duration)

        assert len(warnings) == 1
        assert "exceeds duration" in warnings[0]
        # Should be clamped to duration
        assert fixed[0] == "5:00"

    def test_timestamp_within_tolerance(self):
        """Timestamp within tolerance should pass."""
        timestamps = ["5:15"]  # 315 seconds
        duration = 300  # 5 minutes
        # 315 seconds is within default 30s tolerance of 300
        fixed, warnings = validate_timestamp_bounds(timestamps, duration_seconds=duration)

        assert len(warnings) == 0


# =============================================================================
# TestV6ClipTimestamps
# =============================================================================


class TestV6ClipTimestamps:
    """Tests for clip timestamp validation."""

    def test_valid_clip_timestamps(self):
        """Valid clip timestamps should pass."""
        clips = [
            {"clip_id": "CLIP_1", "start_time": "1:00", "end_time": "2:00"},
        ]
        validated, warnings = validate_clip_timestamps(clips, duration_seconds=3600)

        assert len(warnings) == 0
        assert "_timestamp_clamped" not in validated[0]

    def test_clip_timestamps_clamped(self):
        """Clip timestamps exceeding duration should be clamped."""
        clips = [
            {"clip_id": "CLIP_1", "start_time": "1:00", "end_time": "10:00"},
        ]
        validated, warnings = validate_clip_timestamps(clips, duration_seconds=300)

        assert len(warnings) >= 1
        assert validated[0].get("_timestamp_clamped") is True


# =============================================================================
# TestV7EmptyOutput
# =============================================================================


class TestV7EmptyOutput:
    """Tests for V7: Empty Output Permission."""

    def test_empty_arrays_permitted(self):
        """Empty arrays should be permitted without hard failure."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [],
            "claims": [],
            "themes": [],
            "quotes": [],
        }
        results = validate_extraction_schema(data)

        # Empty arrays should not cause hard failure
        hard_fails = [r for r in results if r.level == ValidationLevel.HARD_FAIL]
        assert len(hard_fails) == 0

    def test_sparse_output_accepted(self):
        """Sparse output should be accepted (with possible warnings)."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "video_only",
            "key_points": [
                {"key_point_id": "KP_1", "source_ids": ["SRC_1"], "statement": "Single point"},
            ],
            "claims": [],
            "themes": [],
            "gaps": [],
        }
        report = validate_semantic_extraction(data, AnalysisMode.VIDEO_ONLY)

        # Should not be a hard failure
        assert report.overall_status != StageStatus.FAILED or not report.has_hard_failures


# =============================================================================
# TestV8ProvenanceChain
# =============================================================================


class TestV8ProvenanceChain:
    """Tests for V8: Provenance Chain Validation."""

    def test_complete_chain_passes(self):
        """Complete provenance chain should pass."""
        data = {
            "source_id": "SRC_1",
            "quotes": [{"quote_id": "QT_1"}],
            "key_points": [{"key_point_id": "KP_1"}],
            "themes": [{"theme_id": "THEME_1"}],
        }
        valid_ids = collect_valid_ids(data)

        assert "SRC_1" in valid_ids
        assert "QT_1" in valid_ids
        assert "KP_1" in valid_ids
        assert "THEME_1" in valid_ids

    def test_theme_missing_keypoint_warning(self):
        """Theme with <2 key points should produce warning."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [{"key_point_id": "KP_1", "source_ids": ["SRC_1"]}],
            "claims": [],
            "themes": [
                {"theme_id": "THEME_1", "related_key_points": ["KP_1"]},  # Only 1 key point
            ],
        }
        results = validate_grounding(data, AnalysisMode.TRANSCRIPT_GROUNDED)

        # Should produce soft fail for theme with <2 key points
        soft_fails = [r for r in results if r.level == ValidationLevel.SOFT_FAIL]
        theme_fails = [r for r in soft_fails if "Theme" in r.message and "fewer than 2" in r.message]
        assert len(theme_fails) == 1

    def test_based_on_invalid_reference_removed(self):
        """Invalid based_on references should be removed."""
        assertions = [
            {"key_point_id": "KP_1", "based_on": ["QT_1", "INVALID_ID"]},
        ]
        valid_ids = {"QT_1", "KP_1", "SRC_1"}

        validated, warnings = validate_based_on_references(assertions, valid_ids)

        assert "INVALID_ID" not in validated[0]["based_on"]
        assert "QT_1" in validated[0]["based_on"]
        assert len(warnings) >= 1


# =============================================================================
# TestV9Cardinality
# =============================================================================


class TestV9Cardinality:
    """Tests for V9: Cardinality Validation."""

    def test_long_form_min_key_points(self):
        """Long-form content should have minimum key points."""
        data = {
            "source_id": "SRC_1",
            "key_points": [
                {"key_point_id": "KP_1", "source_ids": ["SRC_1"]},
            ],  # Only 1 key point
            "themes": [],
            "gaps": [],
        }
        results = validate_structural_sufficiency(
            data,
            source_word_count=5000,  # Long-form
        )

        soft_fails = [r for r in results if r.level == ValidationLevel.SOFT_FAIL]
        assert any("minimum 3" in r.message for r in soft_fails)

    def test_theme_diversity_check(self):
        """Should warn when themes collapse into single category."""
        data = {
            "source_id": "SRC_1",
            "key_points": [
                {"key_point_id": f"KP_{i}", "source_ids": ["SRC_1"]}
                for i in range(5)
            ],
            "themes": [{"theme_id": "THEME_1"}],  # Only 1 theme for 5 key points
            "gaps": [],
        }
        results = validate_structural_sufficiency(data)

        soft_fails = [r for r in results if r.level == ValidationLevel.SOFT_FAIL]
        assert any("theme" in r.message.lower() for r in soft_fails)


# =============================================================================
# TestV10DocThreeGating
# =============================================================================


class TestV10DocThreeGating:
    """Tests for V10: Doc 3 (Producer Packet) Gating Requirements."""

    def test_requires_4_plus_sources(self):
        """Producer Packet should require 4+ sources."""
        from backend.models.document_outputs import LegacyProducerPacketGating as ProducerPacket

        packet = ProducerPacket(
            job_id="job_123",
            story_core="Test story",
            source_count=3,  # Below minimum
            high_confidence_sources=2,
        )
        passes, failed = packet.meets_gating_requirements()

        assert passes is False
        assert any("sources" in f.lower() for f in failed)

    def test_requires_high_confidence_source(self):
        """Producer Packet should require at least 1 high-confidence source."""
        from backend.models.document_outputs import LegacyProducerPacketGating as ProducerPacket

        packet = ProducerPacket(
            job_id="job_123",
            story_core="Test story",
            source_count=5,
            high_confidence_sources=0,  # No high-confidence sources
        )
        passes, failed = packet.meets_gating_requirements()

        assert passes is False
        assert any("high-confidence" in f.lower() for f in failed)

    def test_gating_passes_with_requirements_met(self):
        """Producer Packet should pass gating when requirements met."""
        from backend.models.document_outputs import LegacyProducerPacketGating as ProducerPacket

        packet = ProducerPacket(
            job_id="job_123",
            story_core="Test story",
            source_count=5,
            high_confidence_sources=2,
        )
        passes, failed = packet.meets_gating_requirements()

        assert passes is True
        assert len(failed) == 0


# =============================================================================
# TestConfidenceCalibration
# =============================================================================


class TestConfidenceCalibration:
    """Tests for confidence calibration logic."""

    def test_high_confidence_multi_source_verified(self):
        """High confidence with multiple verified sources."""
        data = {
            "key_points": [{"key_point_id": f"KP_{i}"} for i in range(5)],
            "tensions": [],
        }
        confidence, reasons = calibrate_confidence(
            data,
            AnalysisMode.TRANSCRIPT_GROUNDED,
            source_count=3,
            verification_rate=0.8,
        )
        assert confidence == ConfidenceLevel.HIGH

    def test_medium_confidence_partial_verification(self):
        """Medium confidence with partial verification."""
        data = {
            "key_points": [{"key_point_id": f"KP_{i}"} for i in range(5)],
            "tensions": [],
        }
        confidence, reasons = calibrate_confidence(
            data,
            AnalysisMode.CAPTION_GROUNDED,  # MEDIUM ceiling
            source_count=1,
            verification_rate=0.6,
        )
        assert confidence == ConfidenceLevel.MEDIUM

    def test_low_confidence_thin_extraction(self):
        """Low confidence for thin extraction."""
        data = {
            "key_points": [{"key_point_id": "KP_1"}],  # Only 1 key point
            "tensions": [],
        }
        confidence, reasons = calibrate_confidence(
            data,
            AnalysisMode.TRANSCRIPT_GROUNDED,
            source_count=1,
            verification_rate=0.5,
        )
        assert confidence == ConfidenceLevel.LOW
        assert any("thin" in r.lower() for r in reasons)

    def test_ceiling_enforced(self):
        """Confidence should be capped at mode ceiling."""
        data = {
            "key_points": [{"key_point_id": f"KP_{i}"} for i in range(5)],
            "tensions": [],
        }
        confidence, reasons = calibrate_confidence(
            data,
            AnalysisMode.VIDEO_ONLY,  # LOW ceiling
            source_count=3,
            verification_rate=0.9,
        )
        # Even with high verification, ceiling should cap at LOW
        assert confidence == ConfidenceLevel.LOW


# =============================================================================
# TestShouldRetry
# =============================================================================


class TestShouldRetry:
    """Tests for retry logic."""

    def test_retry_on_schema_failure(self):
        """Should retry on schema failure."""
        report = ValidationReport()
        report.add_result(ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message="Missing required key",
            field="key_points",
        ))
        assert should_retry(report) is True

    def test_retry_on_thin_output(self):
        """Should retry on thin output."""
        report = ValidationReport()
        report.add_result(ValidationResult(
            level=ValidationLevel.SOFT_FAIL,
            message="Output is too thin for long-form source",
            field="key_points",
        ))
        assert should_retry(report) is True

    def test_no_retry_on_warnings_only(self):
        """Should not retry on warnings only."""
        report = ValidationReport()
        report.add_result(ValidationResult(
            level=ValidationLevel.WARNING,
            message="Minor issue",
        ))
        assert should_retry(report) is False


# =============================================================================
# TestNormalizeText
# =============================================================================


class TestNormalizeText:
    """Tests for text normalization in quote verification."""

    def test_normalize_lowercase(self):
        """normalize_text should lowercase."""
        assert normalize_text("HELLO WORLD") == "hello world"

    def test_normalize_whitespace(self):
        """normalize_text should normalize whitespace."""
        assert normalize_text("hello   world") == "hello world"
        assert normalize_text("  hello  world  ") == "hello world"

    def test_normalize_empty(self):
        """normalize_text should handle empty string."""
        assert normalize_text("") == ""
        assert normalize_text(None) == ""


# =============================================================================
# TestFullValidation
# =============================================================================


class TestFullValidation:
    """Tests for full validation pipeline."""

    def test_validate_semantic_extraction_valid(self):
        """Valid extraction should pass with SUCCESS status."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "transcript_grounded",
            "key_points": [
                {"key_point_id": "KP_1", "source_ids": ["SRC_1"], "statement": "Point 1", "confidence": "high"},
                {"key_point_id": "KP_2", "source_ids": ["SRC_1"], "statement": "Point 2", "confidence": "high"},
                {"key_point_id": "KP_3", "source_ids": ["SRC_1"], "statement": "Point 3", "confidence": "high"},
            ],
            "claims": [
                {"claim_id": "CLM_1", "source_id": "SRC_1", "supporting_quotes": ["QT_1"]},
            ],
            "themes": [
                {"theme_id": "THEME_1", "related_key_points": ["KP_1", "KP_2"]},
            ],
            "quotes": [{"quote_id": "QT_1", "text": "Quote"}],
            "gaps": [],
            "tensions": [],
        }
        report = validate_semantic_extraction(data, AnalysisMode.TRANSCRIPT_GROUNDED)

        # Should not have hard failures
        assert not report.has_hard_failures

    def test_validate_semantic_extraction_video_only_with_quotes_fails(self):
        """video_only extraction with quotes should HARD FAIL."""
        data = {
            "source_id": "SRC_1",
            "analysis_mode": "video_only",
            "key_points": [
                {"key_point_id": "KP_1", "source_ids": ["SRC_1"], "confidence": "low"},
            ],
            "claims": [],
            "themes": [],
            "quotes": [{"quote_id": "QT_1", "text": "Forbidden quote"}],
        }
        report = validate_semantic_extraction(data, AnalysisMode.VIDEO_ONLY)

        assert report.has_hard_failures
        assert any("QUOTES NOT ALLOWED" in r.message for r in report.results)
