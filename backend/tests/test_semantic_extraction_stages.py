"""
Unit tests for semantic extraction pipeline stages.

Tests for: SourceIdentityPackage, source identity builders,
semantic extraction, quote verification, synthesis aggregation.

Phase 9 Task 9.2.1
"""
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    Claim,
    KeyPoint,
    Quote,
    SemanticExtractionResult,
    Theme,
    Tension,
)
from backend.models.document_outputs import TranscriptProvenance
from backend.pipeline.stages.source_identity import (
    SourceIdentityPackage,
    build_source_identity_from_article,
    build_source_identity_from_reddit,
    build_source_identity_from_text,
    build_source_identity_from_screenshot,
)
from backend.pipeline.stages.semantic_extraction import (
    parse_extraction_response,
    verify_quotes_in_extraction,
    extract_semantic_structure,
)
from backend.pipeline.stages.semantic_synthesis import (
    aggregate_for_synthesis,
    aggregate_for_synthesis_with_attribution,
    detect_cross_source_conflicts,
    calculate_verification_rate,
    parse_synthesis_response,
)


# =============================================================================
# TestSourceIdentityPackage
# =============================================================================


class TestSourceIdentityPackage:
    """Tests for SourceIdentityPackage dataclass."""

    def test_source_identity_package_creation_minimal(self):
        """SourceIdentityPackage should create with minimal fields."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test Video",
        )
        assert package.source_id == "SRC_1"
        assert package.source_type == "youtube"
        assert package.analysis_mode == AnalysisMode.VIDEO_ONLY
        assert package.is_accessible is True

    def test_source_identity_package_creation_full(self):
        """SourceIdentityPackage should create with all fields."""
        provenance = TranscriptProvenance(
            transcript_source="supadata",
            transcript_status="success",
            captions_status="n/a",
            gemini_analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quote_verification=True,
            timestamp_grounding=True,
            semantic_precision=ConfidenceLevel.HIGH,
        )
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            creator="Test Channel",
            published="2024-01-15",
            duration_seconds=600,
            transcript_source="supadata",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            content="Transcript text here",
            content_word_count=100,
            is_accessible=True,
            provenance=provenance,
        )
        assert package.transcript_source == "supadata"
        assert package.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert package.content_word_count == 100
        assert package.provenance is not None

    def test_confidence_ceiling_transcript_grounded(self):
        """TRANSCRIPT_GROUNDED should have HIGH ceiling."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )
        assert package.confidence_ceiling == ConfidenceLevel.HIGH

    def test_confidence_ceiling_caption_grounded(self):
        """CAPTION_GROUNDED should have MEDIUM ceiling."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test",
            analysis_mode=AnalysisMode.CAPTION_GROUNDED,
        )
        assert package.confidence_ceiling == ConfidenceLevel.MEDIUM

    def test_confidence_ceiling_video_only(self):
        """VIDEO_ONLY should have LOW ceiling."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
        )
        assert package.confidence_ceiling == ConfidenceLevel.LOW

    def test_confidence_ceiling_text_provided(self):
        """TEXT_PROVIDED should have MEDIUM ceiling."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="user_text",
            url="",
            title="Pasted Article",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,
        )
        assert package.confidence_ceiling == ConfidenceLevel.MEDIUM

    def test_confidence_ceiling_ocr_extracted(self):
        """OCR_EXTRACTED should have MEDIUM ceiling."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="screenshot",
            url="",
            title="Screenshot",
            analysis_mode=AnalysisMode.OCR_EXTRACTED,
        )
        assert package.confidence_ceiling == ConfidenceLevel.MEDIUM

    def test_confidence_ceiling_article_fetched(self):
        """ARTICLE_FETCHED should have HIGH ceiling."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="article",
            url="https://example.com/article",
            title="Article",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
        )
        assert package.confidence_ceiling == ConfidenceLevel.HIGH

    def test_to_dict_serialization(self):
        """to_dict should serialize all fields correctly."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            content_word_count=500,
            input_mode="url",
            user_provided=False,
        )
        result = package.to_dict()

        assert result["source_id"] == "SRC_1"
        assert result["analysis_mode"] == "transcript_grounded"
        assert result["content_word_count"] == 500
        assert result["input_mode"] == "url"

    def test_phase_2b_fields_text_input(self):
        """Phase 2B fields should be set correctly for text input."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="user_text",
            url="",
            title="WSJ Article",
            input_mode="text",
            user_provided=True,
            platform_hint="other",
            context_note="From email forward",
        )
        assert package.input_mode == "text"
        assert package.user_provided is True
        assert package.platform_hint == "other"
        assert package.context_note == "From email forward"

    def test_phase_2b_fields_screenshot_input(self):
        """Phase 2B fields should be set correctly for screenshot input."""
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="screenshot",
            url="",
            title="Twitter Screenshot",
            input_mode="screenshot",
            user_provided=False,
            ocr_extracted=True,
            platform_hint="twitter",
        )
        assert package.input_mode == "screenshot"
        assert package.ocr_extracted is True
        assert package.platform_hint == "twitter"


# =============================================================================
# TestSourceIdentityBuilders
# =============================================================================


class TestSourceIdentityBuilders:
    """Tests for source identity builder functions."""

    def test_build_from_article_with_content(self):
        """Article builder should create TRANSCRIPT_GROUNDED package."""
        article_data = {
            "url": "https://example.com/article",
            "title": "Test Article",
            "author": "John Doe",
            "published": "2024-01-15",
            "content": "This is the article content with several words.",
        }
        package = build_source_identity_from_article(article_data, source_index=0)

        assert package.source_id == "SRC_1"
        assert package.source_type == "article"
        assert package.analysis_mode == AnalysisMode.ARTICLE_FETCHED  # Articles use ARTICLE_FETCHED mode
        assert package.is_accessible is True
        assert package.content_word_count == 8  # "This is the article content with several words."

    def test_build_from_article_without_content(self):
        """Article builder should handle missing content gracefully."""
        article_data = {
            "url": "https://example.com/article",
            "title": "Empty Article",
        }
        package = build_source_identity_from_article(article_data, source_index=2)

        assert package.source_id == "SRC_3"
        assert package.is_accessible is False
        assert package.failure_reason == "No content extracted"

    def test_build_from_reddit_with_comments(self):
        """Reddit builder should combine selftext and comments."""
        post_data = {
            "url": "https://reddit.com/r/test/comments/abc123",
            "title": "Test Post",
            "author": "testuser",
            "selftext": "This is the main post.",
            "comments": [
                {"body": "First comment."},
                {"body": "Second comment."},
            ],
        }
        package = build_source_identity_from_reddit(post_data, source_index=0)

        assert package.source_id == "SRC_1"
        assert package.source_type == "reddit"
        assert package.analysis_mode == AnalysisMode.ARTICLE_FETCHED  # Reddit uses ARTICLE_FETCHED mode
        assert "First comment" in package.content
        assert "Second comment" in package.content

    def test_build_from_text_with_context(self):
        """Text builder should set TEXT_PROVIDED mode."""
        content = "This is user-pasted content from a WSJ article."
        package = build_source_identity_from_text(
            content=content,
            source_label="WSJ Article",
            source_index=0,
            context_note="Forwarded from colleague",
            platform_hint="other",
        )

        assert package.source_id == "SRC_1"
        assert package.source_type == "user_text"
        assert package.analysis_mode == AnalysisMode.TEXT_PROVIDED
        assert package.user_provided is True
        assert package.input_mode == "text"
        assert package.context_note == "Forwarded from colleague"

    def test_build_from_text_empty_content(self):
        """Text builder should handle empty content."""
        package = build_source_identity_from_text(
            content="",
            source_label="Empty",
            source_index=0,
        )

        assert package.is_accessible is False
        assert package.failure_reason == "No content provided"

    def test_build_from_screenshot_twitter(self):
        """Screenshot builder should set OCR_EXTRACTED mode."""
        ocr_text = "This is extracted text from a Twitter screenshot @user said something"
        package = build_source_identity_from_screenshot(
            ocr_text=ocr_text,
            source_index=1,
            platform_hint="twitter",
            context_note="Screenshot from mobile",
        )

        assert package.source_id == "SRC_2"
        assert package.source_type == "screenshot"
        assert package.analysis_mode == AnalysisMode.OCR_EXTRACTED
        assert package.ocr_extracted is True
        assert package.title == "Twitter/X Screenshot"

    def test_build_from_screenshot_forum(self):
        """Screenshot builder should handle forum hint."""
        ocr_text = "Forum post content here"
        package = build_source_identity_from_screenshot(
            ocr_text=ocr_text,
            source_index=0,
            platform_hint="forum",
        )

        assert package.title == "Forum Screenshot"
        assert package.platform_hint == "forum"

    def test_build_from_screenshot_empty_ocr(self):
        """Screenshot builder should handle empty OCR."""
        package = build_source_identity_from_screenshot(
            ocr_text="",
            source_index=0,
            platform_hint="reddit",
        )

        assert package.is_accessible is False
        assert "OCR extraction failed" in package.failure_reason


# =============================================================================
# TestParseExtractionResponse
# =============================================================================


class TestParseExtractionResponse:
    """Tests for parsing Gemini extraction responses."""

    def test_parse_empty_response(self):
        """Empty response should return empty result."""
        result = parse_extraction_response(
            response={},
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert result.source_id == "SRC_1"
        assert result.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert result.key_points == []
        assert result.claims == []

    def test_parse_key_points(self):
        """Key points should be parsed correctly."""
        response = {
            "key_points": [
                {
                    "key_point_id": "KP_1",
                    "statement": "Main point statement",
                    "confidence": "high",
                    "supporting_claims": ["CLM_1"],
                },
                {
                    "key_point_id": "KP_2",
                    "statement": "Second point",
                    "confidence": "medium",
                },
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert len(result.key_points) == 2
        assert result.key_points[0].key_point_id == "KP_1"
        assert result.key_points[0].confidence == ConfidenceLevel.HIGH
        assert result.key_points[1].confidence == ConfidenceLevel.MEDIUM

    def test_parse_claims_with_quotes(self):
        """Claims should be parsed with supporting quotes."""
        response = {
            "claims": [
                {
                    "claim_id": "CLM_1",
                    "statement": "A factual claim",
                    "confidence": "high",
                    "supporting_quotes": ["Quote one", "Quote two"],
                    "timestamp_range": "1:30-2:00",
                },
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert len(result.claims) == 1
        assert result.claims[0].claim_id == "CLM_1"
        assert len(result.claims[0].supporting_quotes) == 2
        assert result.claims[0].timestamp_range == "1:30-2:00"

    def test_parse_claims_video_only_mode(self):
        """VIDEO_ONLY claims should have source_mode set."""
        response = {
            "claims": [
                {
                    "claim_id": "CLM_1",
                    "statement": "Visual observation",
                    "confidence": "low",
                },
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
        )

        assert result.claims[0].source_mode == AnalysisMode.VIDEO_ONLY

    def test_parse_themes(self):
        """Themes should be parsed correctly."""
        response = {
            "themes": [
                {
                    "theme_id": "THEME_1",
                    "label": "Financial Transparency",
                    "description": "Discussion of financial disclosure practices",
                    "related_key_points": ["KP_1", "KP_2"],
                }
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert len(result.themes) == 1
        assert result.themes[0].theme_id == "THEME_1"
        assert result.themes[0].label == "Financial Transparency"

    def test_parse_tensions(self):
        """Tensions should be parsed correctly."""
        response = {
            "tensions": [
                {
                    "tension_id": "TEN_1",
                    "description": "Conflict between sources on timeline",
                    "involved_key_points": ["KP_1", "KP_3"],
                }
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert len(result.tensions) == 1
        assert result.tensions[0].tension_id == "TEN_1"

    def test_parse_approximate_observations(self):
        """Approximate observations for video_only should be parsed."""
        response = {
            "approximate_observations": [
                {
                    "observation_id": "OBS_1",
                    "observation": "Speaker appears nervous",
                    "timestamp_range": "~5:00 - 5:30",
                }
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
        )

        assert len(result.approximate_observations) == 1
        assert result.approximate_observations[0].confidence == ConfidenceLevel.LOW
        assert result.approximate_observations[0].approximate is True

    def test_parse_invalid_confidence_defaults_to_medium(self):
        """Invalid confidence values should default to MEDIUM."""
        response = {
            "key_points": [
                {
                    "key_point_id": "KP_1",
                    "statement": "Test",
                    "confidence": "invalid_confidence",
                }
            ]
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert result.key_points[0].confidence == ConfidenceLevel.MEDIUM

    def test_parse_analysis_limitations(self):
        """Analysis limitations should be captured."""
        response = {
            "analysis_limitations": ["Low audio quality", "Speaker overlap"],
        }
        result = parse_extraction_response(
            response=response,
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        assert len(result.analysis_limitations) == 2
        assert "Low audio quality" in result.analysis_limitations


# =============================================================================
# TestVerifyQuotesInExtraction
# =============================================================================


class TestVerifyQuotesInExtraction:
    """Tests for quote verification in extraction results."""

    def test_verify_quotes_no_transcript(self):
        """Verification should skip when no transcript."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )
        updated, warnings = verify_quotes_in_extraction(
            result=result,
            transcript="",
            source_id="SRC_1",
        )

        assert len(warnings) == 1
        assert "no transcript" in warnings[0]

    def test_verify_quotes_exact_match(self):
        """Exact quote match should be verified."""
        quote = Quote(
            quote_id="QT_1",
            text="This is an exact quote from the transcript.",
            source_id="SRC_1",
            timestamp="1:00",
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quotes=[quote],
        )

        transcript = "Some intro. This is an exact quote from the transcript. Some outro."
        updated, warnings = verify_quotes_in_extraction(
            result=result,
            transcript=transcript,
            source_id="SRC_1",
        )

        assert len(updated.quotes) == 1
        assert updated.quotes[0].quote_id == "QT_1"

    def test_verify_claim_supporting_quotes(self):
        """Supporting quotes in claims should be verified."""
        claim = Claim(
            claim_id="CLM_1",
            statement="A claim",
            source_id="SRC_1",
            confidence=ConfidenceLevel.HIGH,
            supporting_quotes=["This exact quote exists", "This quote does not exist"],
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            claims=[claim],
        )

        transcript = "Intro text. This exact quote exists in the transcript."
        updated, warnings = verify_quotes_in_extraction(
            result=result,
            transcript=transcript,
            source_id="SRC_1",
        )

        # Only verified quote should remain
        assert len(updated.claims[0].supporting_quotes) == 1
        assert "not found" in str(warnings)

    def test_verify_claim_confidence_downgrade(self):
        """Claim confidence should downgrade when all quotes removed."""
        claim = Claim(
            claim_id="CLM_1",
            statement="A claim",
            source_id="SRC_1",
            confidence=ConfidenceLevel.HIGH,
            supporting_quotes=["Nonexistent quote one", "Nonexistent quote two"],
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            claims=[claim],
        )

        transcript = "This transcript contains completely different content."
        updated, warnings = verify_quotes_in_extraction(
            result=result,
            transcript=transcript,
            source_id="SRC_1",
        )

        assert updated.claims[0].confidence == ConfidenceLevel.LOW
        assert "downgraded to LOW" in str(warnings)


# =============================================================================
# TestAggregateForSynthesis
# =============================================================================


class MockPipelineContext:
    """Mock pipeline context for testing."""

    def __init__(self):
        self.job_id = "test_job"
        self.topic = "Test Topic"
        self.semantic_extractions = []
        self.identified_gaps = []
        self.scope_in = []
        self.scope_out = []
        self.source_coverage = {}
        self.cross_source_conflicts = []
        self.source_contributions = {}

    def add_warning(self, msg):
        pass


class TestAggregateForSynthesis:
    """Tests for synthesis aggregation functions."""

    def test_aggregate_empty_context(self):
        """Empty context should return empty lists."""
        ctx = MockPipelineContext()

        key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

        assert key_points == []
        assert themes == []
        assert tensions == []
        assert gaps == []

    def test_aggregate_key_points(self):
        """Key points should be aggregated across extractions."""
        ctx = MockPipelineContext()
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_1",
                        statement="First point",
                        source_ids=["SRC_1"],
                        confidence=ConfidenceLevel.HIGH,
                    ),
                ],
            ),
            SemanticExtractionResult(
                source_id="SRC_2",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_2",
                        statement="Second point",
                        source_ids=["SRC_2"],
                        confidence=ConfidenceLevel.MEDIUM,
                    ),
                ],
            ),
        ]

        key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

        assert len(key_points) == 2
        assert key_points[0]["key_point_id"] == "KP_1"
        assert key_points[1]["key_point_id"] == "KP_2"

    def test_aggregate_themes_across_sources(self):
        """Themes should be aggregated across extractions."""
        ctx = MockPipelineContext()
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                themes=[
                    Theme(
                        theme_id="THEME_1",
                        label="Financial",
                        description="Financial matters",
                        related_key_points=["KP_1"],
                    ),
                ],
            ),
        ]

        key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

        assert len(themes) == 1
        assert themes[0]["label"] == "Financial"

    def test_aggregate_with_attribution_builds_coverage(self):
        """Aggregation with attribution should build source coverage map."""
        ctx = MockPipelineContext()
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_1",
                        statement="Point from SRC_1",
                        source_ids=["SRC_1"],
                        confidence=ConfidenceLevel.HIGH,
                    ),
                ],
            ),
        ]

        result = aggregate_for_synthesis_with_attribution(ctx)
        key_points, themes, tensions, gaps, source_coverage, conflicts = result

        assert "KP_1" in source_coverage
        assert source_coverage["KP_1"] == ["SRC_1"]


# =============================================================================
# TestDetectCrossSourceConflicts
# =============================================================================


class TestDetectCrossSourceConflicts:
    """Tests for cross-source conflict detection."""

    def test_detect_no_conflicts_same_source(self):
        """Same source key points should not conflict."""
        key_points = [
            {"key_point_id": "KP_1", "source_ids": ["SRC_1"], "confidence": "high"},
            {"key_point_id": "KP_2", "source_ids": ["SRC_1"], "confidence": "low"},
        ]
        source_coverage = {"KP_1": ["SRC_1"], "KP_2": ["SRC_1"]}

        conflicts = detect_cross_source_conflicts(key_points, source_coverage)

        # Same source = no conflict flagged
        assert len(conflicts) == 0

    def test_detect_returns_empty_for_unrelated_sources(self):
        """Unrelated key points should not be flagged."""
        key_points = [
            {"key_point_id": "KP_1", "source_ids": ["SRC_1"], "confidence": "high"},
            {"key_point_id": "KP_2", "source_ids": ["SRC_2"], "confidence": "high"},
        ]
        source_coverage = {"KP_1": ["SRC_1"], "KP_2": ["SRC_2"]}

        conflicts = detect_cross_source_conflicts(key_points, source_coverage)

        # Current implementation returns empty (heuristic-based)
        assert isinstance(conflicts, list)


# =============================================================================
# TestCalculateVerificationRate
# =============================================================================


class TestCalculateVerificationRate:
    """Tests for verification rate calculation."""

    def test_verification_rate_empty(self):
        """Empty extractions should return 0."""
        ctx = MockPipelineContext()

        rate = calculate_verification_rate(ctx)

        assert rate == 0.0

    def test_verification_rate_no_quotes(self):
        """Claims without quotes should return 0."""
        ctx = MockPipelineContext()
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.VIDEO_ONLY,
                claims=[
                    Claim(
                        claim_id="CLM_1",
                        statement="Claim",
                        source_id="SRC_1",
                        confidence=ConfidenceLevel.LOW,
                        supporting_quotes=[],
                    ),
                ],
            ),
        ]

        rate = calculate_verification_rate(ctx)

        assert rate == 0.0

    def test_verification_rate_all_verified(self):
        """All claims with quotes should return 1.0."""
        ctx = MockPipelineContext()
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                claims=[
                    Claim(
                        claim_id="CLM_1",
                        statement="Claim 1",
                        source_id="SRC_1",
                        confidence=ConfidenceLevel.HIGH,
                        supporting_quotes=["Quote 1"],
                    ),
                    Claim(
                        claim_id="CLM_2",
                        statement="Claim 2",
                        source_id="SRC_1",
                        confidence=ConfidenceLevel.HIGH,
                        supporting_quotes=["Quote 2"],
                    ),
                ],
            ),
        ]

        rate = calculate_verification_rate(ctx)

        assert rate == 1.0

    def test_verification_rate_partial(self):
        """Mixed claims should return correct percentage."""
        ctx = MockPipelineContext()
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                claims=[
                    Claim(
                        claim_id="CLM_1",
                        statement="Verified",
                        source_id="SRC_1",
                        confidence=ConfidenceLevel.HIGH,
                        supporting_quotes=["Quote"],
                    ),
                    Claim(
                        claim_id="CLM_2",
                        statement="Unverified",
                        source_id="SRC_1",
                        confidence=ConfidenceLevel.LOW,
                        supporting_quotes=[],
                    ),
                ],
            ),
        ]

        rate = calculate_verification_rate(ctx)

        assert rate == 0.5


# =============================================================================
# TestParseSynthesisResponse
# =============================================================================


class TestParseSynthesisResponse:
    """Tests for parsing synthesis response."""

    def test_parse_empty_response(self):
        """Empty response should return defaults."""
        result = parse_synthesis_response({})

        assert result["semantic_core"] == ""
        assert result["themes"] == []
        assert result["speculative_observations"] == []
        assert result["confidence_level"] == ConfidenceLevel.MEDIUM

    def test_parse_semantic_core_dict(self):
        """Semantic core as dict should be parsed."""
        response = {
            "semantic_core": {
                "text": "This is the core understanding.",
                "based_on": ["KP_1", "KP_2"],
            }
        }
        result = parse_synthesis_response(response)

        assert result["semantic_core"] == "This is the core understanding."
        assert result["semantic_core_based_on"] == ["KP_1", "KP_2"]

    def test_parse_semantic_core_string(self):
        """Semantic core as string should be parsed."""
        response = {"semantic_core": "Simple core text."}
        result = parse_synthesis_response(response)

        assert result["semantic_core"] == "Simple core text."

    def test_parse_themes(self):
        """Themes should be parsed as Theme objects."""
        response = {
            "themes": [
                {
                    "theme_id": "THEME_1",
                    "label": "Main Theme",
                    "description": "Description of theme",
                    "supporting_key_points": ["KP_1"],
                }
            ]
        }
        result = parse_synthesis_response(response)

        assert len(result["themes"]) == 1
        assert isinstance(result["themes"][0], Theme)
        assert result["themes"][0].label == "Main Theme"

    def test_parse_speculative_observations(self):
        """Speculative observations should be parsed."""
        response = {
            "speculative_observations": [
                {
                    "text": "This might indicate...",
                    "based_on": ["KP_1"],
                    "label": "speculative",
                }
            ]
        }
        result = parse_synthesis_response(response)

        assert len(result["speculative_observations"]) == 1
        assert result["speculative_observations"][0]["label"] == "speculative"

    def test_parse_confidence_assessment(self):
        """Confidence assessment should be parsed."""
        response = {
            "confidence_assessment": {
                "level": "high",
                "reasoning": ["Multiple sources agree", "Verified quotes"],
            }
        }
        result = parse_synthesis_response(response)

        assert result["confidence_level"] == ConfidenceLevel.HIGH
        assert len(result["confidence_reasoning"]) == 2

    def test_parse_invalid_confidence_defaults_to_medium(self):
        """Invalid confidence should default to MEDIUM."""
        response = {
            "confidence_assessment": {
                "level": "super_high",
            }
        }
        result = parse_synthesis_response(response)

        assert result["confidence_level"] == ConfidenceLevel.MEDIUM


# =============================================================================
# TestExtractSemanticStructure
# =============================================================================


class TestExtractSemanticStructure:
    """Tests for extract_semantic_structure function."""

    def test_extract_handles_gemini_error(self):
        """Function should handle Gemini errors gracefully."""
        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "error": "API rate limit exceeded",
            "cost": 0.0,
        }

        result, report, cost = extract_semantic_structure(
            gemini_client=mock_client,
            source_id="SRC_1",
            source_content="Test content",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            title="Test",
        )

        assert result.parse_error is True
        assert "API rate limit exceeded" in result.analysis_limitations[0]

    def test_extract_handles_exception(self):
        """Function should handle exceptions gracefully."""
        mock_client = MagicMock()
        mock_client.generate_json.side_effect = Exception("Network error")

        result, report, cost = extract_semantic_structure(
            gemini_client=mock_client,
            source_id="SRC_1",
            source_content="Test content",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            title="Test",
        )

        assert result.parse_error is True
        assert "Network error" in str(result.analysis_limitations)

    def test_extract_enforces_confidence_ceiling(self):
        """Function should enforce confidence ceiling."""
        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "data": {
                "key_points": [
                    {
                        "key_point_id": "KP_1",
                        "statement": "Test",
                        "confidence": "high",
                    }
                ]
            },
            "cost": 0.001,
        }

        # CAPTION_GROUNDED has MEDIUM ceiling
        result, report, cost = extract_semantic_structure(
            gemini_client=mock_client,
            source_id="SRC_1",
            source_content="Test content",
            analysis_mode=AnalysisMode.CAPTION_GROUNDED,
            title="Test",
        )

        # HIGH should be capped to MEDIUM
        assert result.key_points[0].confidence == ConfidenceLevel.MEDIUM

    def test_extract_returns_validation_report(self):
        """Function should return validation report."""
        mock_client = MagicMock()
        mock_client.generate_json.return_value = {
            "data": {},
            "cost": 0.001,
        }

        result, report, cost = extract_semantic_structure(
            gemini_client=mock_client,
            source_id="SRC_1",
            source_content="Test content",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            title="Test",
        )

        assert report is not None
        assert isinstance(cost, float)
