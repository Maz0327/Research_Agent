"""
Unit tests for semantic unit models.

Tests for: Quote, Claim, KeyPoint, Theme, Tension, Gap,
ApproximateObservation, SpeculativeObservation, SemanticExtractionResult.

Phase 9 Task 9.1.1
"""
import pytest
from backend.models.semantic_units import (
    AnalysisMode,
    ApproximateObservation,
    Claim,
    ConfidenceLevel,
    Gap,
    KeyPoint,
    Quote,
    SemanticExtractionResult,
    SpeculativeObservation,
    Tension,
    Theme,
)


# =============================================================================
# TestConfidenceLevel
# =============================================================================


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_confidence_level_values(self):
        """ConfidenceLevel should have correct string values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_confidence_level_is_string_enum(self):
        """ConfidenceLevel values should be usable as strings."""
        assert str(ConfidenceLevel.HIGH) == "ConfidenceLevel.HIGH"
        assert ConfidenceLevel.HIGH.value == "high"


# =============================================================================
# TestAnalysisMode
# =============================================================================


class TestAnalysisMode:
    """Tests for AnalysisMode enum."""

    def test_all_six_analysis_modes_exist(self):
        """All 6 analysis modes should be defined per RASS spec."""
        modes = [
            AnalysisMode.TRANSCRIPT_GROUNDED,
            AnalysisMode.CAPTION_GROUNDED,
            AnalysisMode.VIDEO_ONLY,
            AnalysisMode.TEXT_PROVIDED,
            AnalysisMode.OCR_EXTRACTED,
            AnalysisMode.ARTICLE_FETCHED,
        ]
        assert len(modes) == 6
        assert len(AnalysisMode) == 6

    def test_analysis_mode_string_values(self):
        """AnalysisMode values should be snake_case strings."""
        assert AnalysisMode.TRANSCRIPT_GROUNDED.value == "transcript_grounded"
        assert AnalysisMode.CAPTION_GROUNDED.value == "caption_grounded"
        assert AnalysisMode.VIDEO_ONLY.value == "video_only"
        assert AnalysisMode.TEXT_PROVIDED.value == "text_provided"
        assert AnalysisMode.OCR_EXTRACTED.value == "ocr_extracted"
        assert AnalysisMode.ARTICLE_FETCHED.value == "article_fetched"


# =============================================================================
# TestQuote
# =============================================================================


class TestQuote:
    """Tests for Quote dataclass."""

    def test_quote_creation_minimal(self):
        """Quote should create with minimal required fields."""
        quote = Quote(
            quote_id="QT_1",
            text="This is a test quote.",
            source_id="SRC_1",
        )
        assert quote.quote_id == "QT_1"
        assert quote.text == "This is a test quote."
        assert quote.source_id == "SRC_1"
        assert quote.timestamp is None
        assert quote.paragraph_index is None
        assert quote.approximate is False

    def test_quote_creation_full(self):
        """Quote should create with all fields."""
        quote = Quote(
            quote_id="QT_2",
            text="Full quote with all fields.",
            source_id="SRC_2",
            timestamp="05:30",
            paragraph_index=3,
            approximate=True,
        )
        assert quote.timestamp == "05:30"
        assert quote.paragraph_index == 3
        assert quote.approximate is True

    def test_quote_with_verification_status(self):
        """Quote should support verification fields."""
        quote = Quote(
            quote_id="QT_3",
            text="Verified quote.",
            source_id="SRC_1",
            verification_status="verified",
            match_ratio=0.98,
        )
        assert quote.verification_status == "verified"
        assert quote.match_ratio == 0.98
        assert quote._verification_warning is None

    def test_quote_with_verification_warning(self):
        """Quote should support verification warning."""
        quote = Quote(
            quote_id="QT_4",
            text="Unverified quote.",
            source_id="SRC_1",
            verification_status="unverified",
            match_ratio=0.45,
            _verification_warning="Quote not found in source text",
        )
        assert quote.verification_status == "unverified"
        assert quote._verification_warning == "Quote not found in source text"

    def test_quote_to_dict_minimal(self):
        """to_dict should return correct dict for minimal quote."""
        quote = Quote(
            quote_id="QT_1",
            text="Test quote.",
            source_id="SRC_1",
        )
        result = quote.to_dict()

        assert result["quote_id"] == "QT_1"
        assert result["text"] == "Test quote."
        assert result["source_id"] == "SRC_1"
        assert result["timestamp"] is None
        assert result["approximate"] is False
        # Verification fields should NOT be in dict when not set
        assert "verification_status" not in result

    def test_quote_to_dict_with_verification(self):
        """to_dict should include verification fields when set."""
        quote = Quote(
            quote_id="QT_1",
            text="Test quote.",
            source_id="SRC_1",
            verification_status="partial",
            match_ratio=0.87,
            _verification_warning="Minor differences found",
        )
        result = quote.to_dict()

        assert result["verification_status"] == "partial"
        assert result["match_ratio"] == 0.87
        assert result["_verification_warning"] == "Minor differences found"


# =============================================================================
# TestClaim
# =============================================================================


class TestClaim:
    """Tests for Claim dataclass."""

    def test_claim_creation_minimal(self):
        """Claim should create with minimal required fields."""
        claim = Claim(
            claim_id="CLM_1",
            statement="The event occurred in 2020.",
            source_id="SRC_1",
        )
        assert claim.claim_id == "CLM_1"
        assert claim.statement == "The event occurred in 2020."
        assert claim.source_id == "SRC_1"
        assert claim.supporting_quotes == []
        assert claim.confidence == ConfidenceLevel.MEDIUM

    def test_claim_with_supporting_quotes(self):
        """Claim should support quote references."""
        claim = Claim(
            claim_id="CLM_2",
            statement="Revenue increased by 50%.",
            source_id="SRC_1",
            supporting_quotes=["QT_1", "QT_2"],
            confidence=ConfidenceLevel.HIGH,
        )
        assert claim.supporting_quotes == ["QT_1", "QT_2"]
        assert claim.confidence == ConfidenceLevel.HIGH

    def test_claim_video_only_mode(self):
        """Claim should support video_only mode fields."""
        claim = Claim(
            claim_id="CLM_3",
            statement="Speaker appeared emotional.",
            source_id="SRC_1",
            timestamp_range="~02:30 - 03:15",
            source_mode=AnalysisMode.VIDEO_ONLY,
            confidence=ConfidenceLevel.LOW,
        )
        assert claim.timestamp_range == "~02:30 - 03:15"
        assert claim.source_mode == AnalysisMode.VIDEO_ONLY
        assert claim.confidence == ConfidenceLevel.LOW

    def test_claim_confidence_levels(self):
        """Claim should accept all confidence levels."""
        for level in ConfidenceLevel:
            claim = Claim(
                claim_id="CLM_test",
                statement="Test",
                source_id="SRC_1",
                confidence=level,
            )
            assert claim.confidence == level

    def test_claim_to_dict(self):
        """to_dict should return correct dict."""
        claim = Claim(
            claim_id="CLM_1",
            statement="Test claim.",
            source_id="SRC_1",
            supporting_quotes=["QT_1"],
            confidence=ConfidenceLevel.HIGH,
            timestamp_range="~01:00 - 02:00",
            source_mode=AnalysisMode.VIDEO_ONLY,
        )
        result = claim.to_dict()

        assert result["claim_id"] == "CLM_1"
        assert result["statement"] == "Test claim."
        assert result["source_id"] == "SRC_1"
        assert result["supporting_quotes"] == ["QT_1"]
        assert result["confidence"] == "high"
        assert result["timestamp_range"] == "~01:00 - 02:00"
        assert result["source_mode"] == "video_only"


# =============================================================================
# TestKeyPoint
# =============================================================================


class TestKeyPoint:
    """Tests for KeyPoint dataclass."""

    def test_key_point_creation(self):
        """KeyPoint should create correctly."""
        kp = KeyPoint(
            key_point_id="KP_1",
            statement="Central argument about transparency.",
            source_ids=["SRC_1"],
        )
        assert kp.key_point_id == "KP_1"
        assert kp.statement == "Central argument about transparency."
        assert kp.source_ids == ["SRC_1"]
        assert kp.supporting_claims == []
        assert kp.confidence == ConfidenceLevel.MEDIUM

    def test_key_point_requires_source_ids_list(self):
        """KeyPoint source_ids should be a list."""
        kp = KeyPoint(
            key_point_id="KP_1",
            statement="Test",
            source_ids=["SRC_1", "SRC_2"],
        )
        assert isinstance(kp.source_ids, list)
        assert len(kp.source_ids) == 2

    def test_key_point_with_multiple_sources(self):
        """KeyPoint should support multiple source attribution."""
        kp = KeyPoint(
            key_point_id="KP_2",
            statement="Multiple sources agree on this point.",
            source_ids=["SRC_1", "SRC_2", "SRC_3"],
            supporting_claims=["CLM_1", "CLM_5", "CLM_9"],
            confidence=ConfidenceLevel.HIGH,
        )
        assert len(kp.source_ids) == 3
        assert len(kp.supporting_claims) == 3

    def test_key_point_to_dict(self):
        """to_dict should return correct dict."""
        kp = KeyPoint(
            key_point_id="KP_1",
            statement="Test key point.",
            source_ids=["SRC_1"],
            supporting_claims=["CLM_1"],
            confidence=ConfidenceLevel.HIGH,
        )
        result = kp.to_dict()

        assert result["key_point_id"] == "KP_1"
        assert result["statement"] == "Test key point."
        assert result["source_ids"] == ["SRC_1"]
        assert result["supporting_claims"] == ["CLM_1"]
        assert result["confidence"] == "high"


# =============================================================================
# TestTheme
# =============================================================================


class TestTheme:
    """Tests for Theme dataclass."""

    def test_theme_creation(self):
        """Theme should create correctly."""
        theme = Theme(
            theme_id="THEME_1",
            label="Financial Opacity",
            description="Multiple sources describe lack of transparency in finances.",
            related_key_points=["KP_1", "KP_2"],
        )
        assert theme.theme_id == "THEME_1"
        assert theme.label == "Financial Opacity"
        assert theme.description == "Multiple sources describe lack of transparency in finances."
        assert theme.related_key_points == ["KP_1", "KP_2"]

    def test_theme_with_cross_source_consensus(self):
        """Theme should support cross-source attribution."""
        theme = Theme(
            theme_id="THEME_2",
            label="Timeline Inconsistencies",
            description="Different accounts give conflicting dates.",
            related_key_points=["KP_3", "KP_4"],
            sources_supporting=["SRC_1", "SRC_2"],
            is_consensus=True,
        )
        assert theme.sources_supporting == ["SRC_1", "SRC_2"]
        assert theme.is_consensus is True

    def test_theme_supporting_key_points(self):
        """Theme must reference related key points."""
        theme = Theme(
            theme_id="THEME_3",
            label="Test Theme",
            description="Test description.",
            related_key_points=["KP_1", "KP_2", "KP_3"],
        )
        assert len(theme.related_key_points) == 3

    def test_theme_to_dict_without_cross_source(self):
        """to_dict should exclude Phase 5 fields when empty."""
        theme = Theme(
            theme_id="THEME_1",
            label="Test",
            description="Desc",
            related_key_points=["KP_1"],
        )
        result = theme.to_dict()

        assert result["theme_id"] == "THEME_1"
        assert result["label"] == "Test"
        assert "sources_supporting" not in result
        assert "is_consensus" not in result

    def test_theme_to_dict_with_cross_source(self):
        """to_dict should include Phase 5 fields when populated."""
        theme = Theme(
            theme_id="THEME_1",
            label="Test",
            description="Desc",
            related_key_points=["KP_1"],
            sources_supporting=["SRC_1", "SRC_2"],
            is_consensus=True,
        )
        result = theme.to_dict()

        assert result["sources_supporting"] == ["SRC_1", "SRC_2"]
        assert result["is_consensus"] is True


# =============================================================================
# TestTension
# =============================================================================


class TestTension:
    """Tests for Tension dataclass."""

    def test_tension_creation(self):
        """Tension should create correctly."""
        tension = Tension(
            tension_id="TEN_1",
            description="Sources disagree on the timeline of events.",
            involved_key_points=["KP_1", "KP_2"],
        )
        assert tension.tension_id == "TEN_1"
        assert tension.description == "Sources disagree on the timeline of events."
        assert tension.involved_key_points == ["KP_1", "KP_2"]
        assert tension.label == ""  # Default to empty string

    def test_tension_with_label(self):
        """Tension should support label field for UX."""
        tension = Tension(
            tension_id="TEN_1",
            description="Two sources give conflicting dates for the merger announcement.",
            label="Timeline Conflict",
            involved_key_points=["KP_1", "KP_2"],
        )
        assert tension.label == "Timeline Conflict"
        assert tension.tension_id == "TEN_1"

    def test_tension_label_in_to_dict(self):
        """to_dict should include label field."""
        tension = Tension(
            tension_id="TEN_1",
            description="Test tension.",
            label="Test Label",
            involved_key_points=["KP_1"],
        )
        result = tension.to_dict()
        assert result["label"] == "Test Label"
        assert "label" in result

    def test_tension_with_cross_source_flag(self):
        """Tension should support cross-source attribution."""
        tension = Tension(
            tension_id="TEN_2",
            description="Two sources give conflicting accounts.",
            involved_key_points=["KP_5", "KP_6"],
            sources_position_a=["SRC_1"],
            sources_position_b=["SRC_2"],
            is_cross_source=True,
        )
        assert tension.sources_position_a == ["SRC_1"]
        assert tension.sources_position_b == ["SRC_2"]
        assert tension.is_cross_source is True

    def test_tension_to_dict_without_cross_source(self):
        """to_dict should exclude Phase 5 fields when not cross-source."""
        tension = Tension(
            tension_id="TEN_1",
            description="Internal tension",
            involved_key_points=["KP_1", "KP_2"],
            is_cross_source=False,
        )
        result = tension.to_dict()

        assert result["tension_id"] == "TEN_1"
        assert "sources_position_a" not in result
        assert "is_cross_source" not in result

    def test_tension_to_dict_with_cross_source(self):
        """to_dict should include Phase 5 fields when cross-source."""
        tension = Tension(
            tension_id="TEN_1",
            description="Cross-source tension",
            involved_key_points=["KP_1", "KP_2"],
            sources_position_a=["SRC_1"],
            sources_position_b=["SRC_2"],
            is_cross_source=True,
        )
        result = tension.to_dict()

        assert result["sources_position_a"] == ["SRC_1"]
        assert result["sources_position_b"] == ["SRC_2"]
        assert result["is_cross_source"] is True


# =============================================================================
# TestGap
# =============================================================================


class TestGap:
    """Tests for Gap dataclass."""

    def test_gap_creation(self):
        """Gap should create correctly."""
        gap = Gap(
            gap_id="GAP_1",
            description="No response from the accused party.",
            why_expected="A competent investigation would include their perspective.",
        )
        assert gap.gap_id == "GAP_1"
        assert gap.description == "No response from the accused party."
        assert gap.why_expected == "A competent investigation would include their perspective."
        assert gap.label == ""  # Default to empty string

    def test_gap_with_label(self):
        """Gap should support label field for UX."""
        gap = Gap(
            gap_id="GAP_1",
            description="No primary documentation for the $50M claim.",
            why_expected="Financial claims need supporting documents.",
            label="Missing Primary Docs",
        )
        assert gap.label == "Missing Primary Docs"
        assert gap.gap_id == "GAP_1"

    def test_gap_label_in_to_dict(self):
        """to_dict should include label field."""
        gap = Gap(
            gap_id="GAP_1",
            description="Test gap.",
            why_expected="Expected because...",
            label="Test Label",
        )
        result = gap.to_dict()
        assert result["label"] == "Test Label"
        assert "label" in result

    def test_gap_with_related_themes(self):
        """Gap should support related theme references."""
        gap = Gap(
            gap_id="GAP_2",
            description="Missing financial documents.",
            why_expected="Claims about finances need documentation.",
            related_themes=["THEME_1", "THEME_2"],
            related_key_points=["KP_3", "KP_4"],
            suggested_research_direction="FOIA request for financial records",
        )
        assert gap.related_themes == ["THEME_1", "THEME_2"]
        assert gap.related_key_points == ["KP_3", "KP_4"]
        assert gap.suggested_research_direction == "FOIA request for financial records"

    def test_gap_to_dict(self):
        """to_dict should return correct dict."""
        gap = Gap(
            gap_id="GAP_1",
            description="Test gap.",
            why_expected="Expected because...",
            related_themes=["THEME_1"],
            related_key_points=["KP_1"],
            suggested_research_direction="Research direction",
        )
        result = gap.to_dict()

        assert result["gap_id"] == "GAP_1"
        assert result["description"] == "Test gap."
        assert result["why_expected"] == "Expected because..."
        assert result["related_themes"] == ["THEME_1"]
        assert result["suggested_research_direction"] == "Research direction"


# =============================================================================
# TestApproximateObservation
# =============================================================================


class TestApproximateObservation:
    """Tests for ApproximateObservation dataclass."""

    def test_approximate_observation_creation(self):
        """ApproximateObservation should create correctly."""
        obs = ApproximateObservation(
            observation_id="OBS_1",
            observation="Speaker gestures at a chart showing growth.",
            source_id="SRC_1",
            timestamp_range="~02:30 - 03:00",
        )
        assert obs.observation_id == "OBS_1"
        assert obs.observation == "Speaker gestures at a chart showing growth."
        assert obs.source_id == "SRC_1"
        assert obs.timestamp_range == "~02:30 - 03:00"

    def test_approximate_observation_always_approximate(self):
        """ApproximateObservation should always be approximate=True."""
        obs = ApproximateObservation(
            observation_id="OBS_1",
            observation="Test",
            source_id="SRC_1",
            timestamp_range="~00:00 - 01:00",
        )
        assert obs.approximate is True

    def test_approximate_observation_always_low_confidence(self):
        """ApproximateObservation should always be LOW confidence."""
        obs = ApproximateObservation(
            observation_id="OBS_1",
            observation="Test",
            source_id="SRC_1",
            timestamp_range="~00:00 - 01:00",
        )
        assert obs.confidence == ConfidenceLevel.LOW

    def test_approximate_observation_to_dict(self):
        """to_dict should return correct dict."""
        obs = ApproximateObservation(
            observation_id="OBS_1",
            observation="Test observation.",
            source_id="SRC_1",
            timestamp_range="~01:00 - 02:00",
        )
        result = obs.to_dict()

        assert result["observation_id"] == "OBS_1"
        assert result["observation"] == "Test observation."
        assert result["source_id"] == "SRC_1"
        assert result["timestamp_range"] == "~01:00 - 02:00"
        assert result["approximate"] is True
        assert result["type"] == "observation"
        assert result["confidence"] == "low"


# =============================================================================
# TestSpeculativeObservation
# =============================================================================


class TestSpeculativeObservation:
    """Tests for SpeculativeObservation dataclass."""

    def test_speculative_observation_creation(self):
        """SpeculativeObservation should create correctly."""
        spec = SpeculativeObservation(
            text="This may indicate an attempt to obscure responsibility.",
            based_on=["KP_1", "KP_2"],
        )
        assert spec.text == "This may indicate an attempt to obscure responsibility."
        assert spec.based_on == ["KP_1", "KP_2"]
        assert spec.label == "speculative"

    def test_speculative_observation_always_labeled(self):
        """SpeculativeObservation should always have label='speculative'."""
        spec = SpeculativeObservation(text="Test", based_on=[])
        assert spec.label == "speculative"

    def test_speculative_observation_to_dict(self):
        """to_dict should return correct dict."""
        spec = SpeculativeObservation(
            text="One possible motive is financial pressure.",
            based_on=["KP_3"],
        )
        result = spec.to_dict()

        assert result["text"] == "One possible motive is financial pressure."
        assert result["based_on"] == ["KP_3"]
        assert result["label"] == "speculative"


# =============================================================================
# TestSemanticExtractionResult
# =============================================================================


class TestSemanticExtractionResult:
    """Tests for SemanticExtractionResult dataclass."""

    def test_extraction_result_creation_minimal(self):
        """SemanticExtractionResult should create with minimal fields."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )
        assert result.source_id == "SRC_1"
        assert result.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert result.quotes == []
        assert result.claims == []
        assert result.key_points == []
        assert result.themes == []
        assert result.tensions == []
        assert result.approximate_observations == []

    def test_extraction_result_with_content(self):
        """SemanticExtractionResult should hold all semantic units."""
        quote = Quote(quote_id="QT_1", text="Test", source_id="SRC_1")
        claim = Claim(claim_id="CLM_1", statement="Test", source_id="SRC_1")
        kp = KeyPoint(key_point_id="KP_1", statement="Test", source_ids=["SRC_1"])

        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quotes=[quote],
            claims=[claim],
            key_points=[kp],
        )
        assert len(result.quotes) == 1
        assert len(result.claims) == 1
        assert len(result.key_points) == 1

    def test_confidence_ceiling_transcript_grounded(self):
        """transcript_grounded should have HIGH ceiling."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )
        assert result.confidence_ceiling == ConfidenceLevel.HIGH

    def test_confidence_ceiling_caption_grounded(self):
        """caption_grounded should have MEDIUM ceiling."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.CAPTION_GROUNDED,
        )
        assert result.confidence_ceiling == ConfidenceLevel.MEDIUM

    def test_confidence_ceiling_video_only(self):
        """video_only should have LOW ceiling."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
        )
        assert result.confidence_ceiling == ConfidenceLevel.LOW

    def test_confidence_ceiling_text_provided(self):
        """text_provided should have MEDIUM ceiling."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,
        )
        assert result.confidence_ceiling == ConfidenceLevel.MEDIUM

    def test_confidence_ceiling_ocr_extracted(self):
        """ocr_extracted should have MEDIUM ceiling."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.OCR_EXTRACTED,
        )
        assert result.confidence_ceiling == ConfidenceLevel.MEDIUM

    def test_confidence_ceiling_article_fetched(self):
        """article_fetched should have HIGH ceiling."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
        )
        assert result.confidence_ceiling == ConfidenceLevel.HIGH

    def test_enforce_confidence_ceiling_high_mode(self):
        """enforce_confidence_ceiling should not change HIGH mode claims."""
        claim = Claim(
            claim_id="CLM_1",
            statement="Test",
            source_id="SRC_1",
            confidence=ConfidenceLevel.HIGH,
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            claims=[claim],
        )
        warnings = result.enforce_confidence_ceiling()

        assert len(warnings) == 0
        assert result.claims[0].confidence == ConfidenceLevel.HIGH

    def test_enforce_confidence_ceiling_medium_mode(self):
        """enforce_confidence_ceiling should downgrade HIGH to MEDIUM."""
        claim = Claim(
            claim_id="CLM_1",
            statement="Test",
            source_id="SRC_1",
            confidence=ConfidenceLevel.HIGH,
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.CAPTION_GROUNDED,  # MEDIUM ceiling
            claims=[claim],
        )
        warnings = result.enforce_confidence_ceiling()

        assert len(warnings) == 1
        assert "auto-downgraded" in warnings[0]
        assert result.claims[0].confidence == ConfidenceLevel.MEDIUM

    def test_enforce_confidence_ceiling_low_mode(self):
        """enforce_confidence_ceiling should downgrade to LOW."""
        claim = Claim(
            claim_id="CLM_1",
            statement="Test",
            source_id="SRC_1",
            confidence=ConfidenceLevel.HIGH,
        )
        kp = KeyPoint(
            key_point_id="KP_1",
            statement="Test",
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.MEDIUM,
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,  # LOW ceiling
            claims=[claim],
            key_points=[kp],
        )
        warnings = result.enforce_confidence_ceiling()

        assert len(warnings) == 2
        assert result.claims[0].confidence == ConfidenceLevel.LOW
        assert result.key_points[0].confidence == ConfidenceLevel.LOW

    def test_enforce_confidence_ceiling_no_change_when_below(self):
        """enforce_confidence_ceiling should not change when below ceiling."""
        claim = Claim(
            claim_id="CLM_1",
            statement="Test",
            source_id="SRC_1",
            confidence=ConfidenceLevel.LOW,
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,  # HIGH ceiling
            claims=[claim],
        )
        warnings = result.enforce_confidence_ceiling()

        assert len(warnings) == 0
        assert result.claims[0].confidence == ConfidenceLevel.LOW

    def test_mode_specific_metadata(self):
        """SemanticExtractionResult should track transcript source."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            transcript_source="supadata",
        )
        assert result.transcript_source == "supadata"

    def test_mode_specific_parse_error(self):
        """SemanticExtractionResult should track parse errors."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,
            parse_error=True,
        )
        assert result.parse_error is True

    def test_extraction_result_to_dict(self):
        """to_dict should serialize all content."""
        quote = Quote(quote_id="QT_1", text="Quote text", source_id="SRC_1")
        claim = Claim(claim_id="CLM_1", statement="Claim", source_id="SRC_1")
        kp = KeyPoint(key_point_id="KP_1", statement="KP", source_ids=["SRC_1"])
        theme = Theme(
            theme_id="THEME_1",
            label="Theme",
            description="Desc",
            related_key_points=["KP_1"],
        )
        tension = Tension(
            tension_id="TEN_1",
            description="Tension",
            involved_key_points=["KP_1"],
        )

        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quotes=[quote],
            claims=[claim],
            key_points=[kp],
            themes=[theme],
            tensions=[tension],
            transcript_source="whisper",
        )
        d = result.to_dict()

        assert d["source_id"] == "SRC_1"
        assert d["analysis_mode"] == "transcript_grounded"
        assert len(d["quotes"]) == 1
        assert len(d["claims"]) == 1
        assert len(d["key_points"]) == 1
        assert len(d["themes"]) == 1
        assert len(d["tensions"]) == 1
        assert d["transcript_source"] == "whisper"

    def test_video_only_with_observations(self):
        """video_only mode should use approximate_observations."""
        obs = ApproximateObservation(
            observation_id="OBS_1",
            observation="Visual cue",
            source_id="SRC_1",
            timestamp_range="~00:00 - 01:00",
        )
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            approximate_observations=[obs],
        )
        assert len(result.approximate_observations) == 1
        assert result.quotes == []  # No quotes in video_only


# =============================================================================
# TestIDNamingConventions
# =============================================================================


class TestIDNamingConventions:
    """Tests for ID naming conventions per CLAUDE.md Rule 11."""

    def test_source_id_convention(self):
        """Source IDs should follow SRC_N pattern."""
        result = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )
        assert result.source_id.startswith("SRC_")

    def test_quote_id_convention(self):
        """Quote IDs should follow QT_N pattern."""
        quote = Quote(quote_id="QT_1", text="Test", source_id="SRC_1")
        assert quote.quote_id.startswith("QT_")

    def test_claim_id_convention(self):
        """Claim IDs should follow CLM_N pattern."""
        claim = Claim(claim_id="CLM_1", statement="Test", source_id="SRC_1")
        assert claim.claim_id.startswith("CLM_")

    def test_key_point_id_convention(self):
        """KeyPoint IDs should follow KP_N pattern."""
        kp = KeyPoint(key_point_id="KP_1", statement="Test", source_ids=["SRC_1"])
        assert kp.key_point_id.startswith("KP_")

    def test_theme_id_convention(self):
        """Theme IDs should follow THEME_N pattern."""
        theme = Theme(
            theme_id="THEME_1",
            label="Test",
            description="Desc",
            related_key_points=["KP_1"],
        )
        assert theme.theme_id.startswith("THEME_")

    def test_tension_id_convention(self):
        """Tension IDs should follow TEN_N pattern."""
        tension = Tension(
            tension_id="TEN_1",
            description="Test",
            involved_key_points=["KP_1"],
        )
        assert tension.tension_id.startswith("TEN_")

    def test_gap_id_convention(self):
        """Gap IDs should follow GAP_N pattern."""
        gap = Gap(gap_id="GAP_1", description="Test", why_expected="Expected")
        assert gap.gap_id.startswith("GAP_")

    def test_observation_id_convention(self):
        """Observation IDs should follow OBS_N pattern."""
        obs = ApproximateObservation(
            observation_id="OBS_1",
            observation="Test",
            source_id="SRC_1",
            timestamp_range="~00:00 - 01:00",
        )
        assert obs.observation_id.startswith("OBS_")


# =============================================================================
# TestIDFormatHelpers
# =============================================================================


class TestIDFormatHelpers:
    """Tests for ID formatting helper functions."""

    def test_format_internal_id_source(self):
        """format_internal_id should convert SRC_N to 'Source N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("SRC_1") == "Source 1"
        assert format_internal_id("SRC_12") == "Source 12"
        assert format_internal_id("SRC_100") == "Source 100"

    def test_format_internal_id_key_point(self):
        """format_internal_id should convert KP_N to 'Key Point N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("KP_1") == "Key Point 1"
        assert format_internal_id("KP_25") == "Key Point 25"

    def test_format_internal_id_theme(self):
        """format_internal_id should convert THEME_N to 'Theme N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("THEME_1") == "Theme 1"
        assert format_internal_id("THEME_5") == "Theme 5"

    def test_format_internal_id_tension(self):
        """format_internal_id should convert TEN_N to 'Tension N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("TEN_1") == "Tension 1"
        assert format_internal_id("TEN_3") == "Tension 3"

    def test_format_internal_id_gap(self):
        """format_internal_id should convert GAP_N to 'Open Question N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("GAP_1") == "Open Question 1"
        assert format_internal_id("GAP_7") == "Open Question 7"

    def test_format_internal_id_claim(self):
        """format_internal_id should convert CLM_N to 'Claim N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("CLM_1") == "Claim 1"

    def test_format_internal_id_quote(self):
        """format_internal_id should convert QT_N to 'Quote N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("QT_1") == "Quote 1"

    def test_format_internal_id_observation(self):
        """format_internal_id should convert OBS_N to 'Observation N'."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("OBS_1") == "Observation 1"

    def test_format_internal_id_passthrough(self):
        """format_internal_id should pass through unknown IDs."""
        from backend.utils.markdown_helpers import format_internal_id
        assert format_internal_id("UNKNOWN_1") == "UNKNOWN_1"
        assert format_internal_id("plain text") == "plain text"
        assert format_internal_id("") == ""

    def test_format_id_list_basic(self):
        """format_id_list should convert list of IDs."""
        from backend.utils.markdown_helpers import format_id_list
        result = format_id_list(["KP_1", "KP_3", "KP_7"])
        assert result == "Key Point 1, Key Point 3, Key Point 7"

    def test_format_id_list_mixed_types(self):
        """format_id_list should handle mixed ID types."""
        from backend.utils.markdown_helpers import format_id_list
        result = format_id_list(["SRC_1", "THEME_2", "GAP_3"])
        assert result == "Source 1, Theme 2, Open Question 3"

    def test_format_id_list_empty(self):
        """format_id_list should handle empty list."""
        from backend.utils.markdown_helpers import format_id_list
        assert format_id_list([]) == ""

    def test_format_id_list_custom_separator(self):
        """format_id_list should support custom separator."""
        from backend.utils.markdown_helpers import format_id_list
        result = format_id_list(["KP_1", "KP_2"], separator=" | ")
        assert result == "Key Point 1 | Key Point 2"
