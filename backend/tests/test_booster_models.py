"""
Unit tests for booster models.

Tests for: PrimarySourceType, PlatformSuggestion, ThemeSummary, TensionSummary,
GapSummary, ContextBundle, MissingPerspective, PrimarySourceDirection,
SearchQuery, ResearchQuestion, BoosterOutput.

Phase 9 Task 9.1.3
"""
import pytest
from datetime import datetime

from backend.models.booster_models import (
    PrimarySourceType,
    PlatformSuggestion,
    ThemeSummary,
    TensionSummary,
    GapSummary,
    ContextBundle,
    MissingPerspective,
    PrimarySourceDirection,
    SearchQuery,
    ResearchQuestion,
    BoosterOutput,
)


# =============================================================================
# TestPrimarySourceType
# =============================================================================


class TestPrimarySourceType:
    """Tests for PrimarySourceType enum."""

    def test_primary_source_type_values(self):
        """PrimarySourceType should have correct string values."""
        assert PrimarySourceType.COURT_FILING.value == "court_filing"
        assert PrimarySourceType.SEC_FILING.value == "sec_filing"
        assert PrimarySourceType.GOVERNMENT_RECORD.value == "government_record"
        assert PrimarySourceType.ACADEMIC_PAPER.value == "academic_paper"

    def test_all_source_types_exist(self):
        """All expected source types should be defined."""
        types = [
            PrimarySourceType.COURT_FILING,
            PrimarySourceType.SEC_FILING,
            PrimarySourceType.GOVERNMENT_RECORD,
            PrimarySourceType.ACADEMIC_PAPER,
            PrimarySourceType.NEWS_ARTICLE,
            PrimarySourceType.PRESS_RELEASE,
            PrimarySourceType.SOCIAL_MEDIA_ARCHIVE,
            PrimarySourceType.INTERVIEW_TRANSCRIPT,
            PrimarySourceType.INTERNAL_DOCUMENT,
            PrimarySourceType.DATASET,
            PrimarySourceType.FINANCIAL_REPORT,
            PrimarySourceType.OTHER,
        ]
        assert len(types) == 12
        assert len(PrimarySourceType) == 12


# =============================================================================
# TestPlatformSuggestion
# =============================================================================


class TestPlatformSuggestion:
    """Tests for PlatformSuggestion enum."""

    def test_platform_suggestion_values(self):
        """PlatformSuggestion should have correct values."""
        assert PlatformSuggestion.GOOGLE.value == "google"
        assert PlatformSuggestion.REDDIT.value == "reddit"
        assert PlatformSuggestion.TWITTER.value == "twitter"
        assert PlatformSuggestion.NEWS.value == "news"
        assert PlatformSuggestion.YOUTUBE.value == "youtube"
        assert PlatformSuggestion.ARCHIVE.value == "archive"

    def test_all_platforms_exist(self):
        """All expected platforms should be defined."""
        assert len(PlatformSuggestion) == 6


# =============================================================================
# TestThemeSummary
# =============================================================================


class TestThemeSummary:
    """Tests for ThemeSummary dataclass."""

    def test_theme_summary_creation(self):
        """ThemeSummary should create correctly."""
        theme = ThemeSummary(
            theme_id="THEME_1",
            label="Financial Opacity",
            description="Lack of transparency in financial reporting",
        )
        assert theme.theme_id == "THEME_1"
        assert theme.label == "Financial Opacity"
        assert theme.description == "Lack of transparency in financial reporting"

    def test_theme_summary_to_dict(self):
        """to_dict should return correct dict."""
        theme = ThemeSummary(
            theme_id="THEME_1",
            label="Test",
            description="Test description",
        )
        result = theme.to_dict()

        assert result["theme_id"] == "THEME_1"
        assert result["label"] == "Test"
        assert result["description"] == "Test description"


# =============================================================================
# TestTensionSummary
# =============================================================================


class TestTensionSummary:
    """Tests for TensionSummary dataclass."""

    def test_tension_summary_creation(self):
        """TensionSummary should create correctly."""
        tension = TensionSummary(
            tension_id="TEN_1",
            description="Conflicting accounts of the timeline",
        )
        assert tension.tension_id == "TEN_1"
        assert tension.description == "Conflicting accounts of the timeline"

    def test_tension_summary_to_dict(self):
        """to_dict should return correct dict."""
        tension = TensionSummary(
            tension_id="TEN_1",
            description="Test tension",
        )
        result = tension.to_dict()

        assert result["tension_id"] == "TEN_1"
        assert result["description"] == "Test tension"


# =============================================================================
# TestGapSummary
# =============================================================================


class TestGapSummary:
    """Tests for GapSummary dataclass."""

    def test_gap_summary_creation(self):
        """GapSummary should create correctly."""
        gap = GapSummary(
            gap_id="GAP_1",
            description="Missing response from accused party",
        )
        assert gap.gap_id == "GAP_1"
        assert gap.description == "Missing response from accused party"

    def test_gap_summary_to_dict(self):
        """to_dict should return correct dict."""
        gap = GapSummary(
            gap_id="GAP_1",
            description="Test gap",
        )
        result = gap.to_dict()

        assert result["gap_id"] == "GAP_1"
        assert result["description"] == "Test gap"


# =============================================================================
# TestContextBundle
# =============================================================================


class TestContextBundle:
    """Tests for ContextBundle dataclass."""

    def test_context_bundle_creation_minimal(self):
        """ContextBundle should create with minimal fields."""
        bundle = ContextBundle()
        assert bundle.scope_in == []
        assert bundle.scope_out == []
        assert bundle.themes == []
        assert bundle.gaps == []
        assert bundle.source_count == 0

    def test_context_bundle_creation_full(self):
        """ContextBundle should create with all fields."""
        theme = ThemeSummary("THEME_1", "Theme", "Description")
        tension = TensionSummary("TEN_1", "Tension")
        gap = GapSummary("GAP_1", "Gap")

        bundle = ContextBundle(
            scope_in=["Topic A", "Topic B"],
            scope_out=["Topic C"],
            themes=[theme],
            key_point_summaries=["Point 1", "Point 2"],
            tensions=[tension],
            gaps=[gap],
            source_count=5,
            source_types=["youtube", "article"],
            confidence_level="high",
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
        )
        assert len(bundle.scope_in) == 2
        assert len(bundle.themes) == 1
        assert bundle.source_count == 5
        assert bundle.job_id == "job_123"

    def test_context_bundle_excludes_full_text(self):
        """ContextBundle should not have full_text field."""
        bundle = ContextBundle()
        assert not hasattr(bundle, "full_text")
        assert not hasattr(bundle, "transcript")
        assert not hasattr(bundle, "quotes")

    def test_context_bundle_to_dict(self):
        """to_dict should return correctly structured dict."""
        theme = ThemeSummary("THEME_1", "Theme", "Desc")
        bundle = ContextBundle(
            scope_in=["Topic A"],
            themes=[theme],
            source_count=3,
            job_id="job_123",
        )
        result = bundle.to_dict()

        assert result["scope_in"] == ["Topic A"]
        assert len(result["themes"]) == 1
        assert result["source_count"] == 3
        assert result["job_id"] == "job_123"


# =============================================================================
# TestMissingPerspective
# =============================================================================


class TestMissingPerspective:
    """Tests for MissingPerspective dataclass."""

    def test_missing_perspective_creation(self):
        """MissingPerspective should create correctly."""
        mp = MissingPerspective(
            description="The accused party's official response",
            why_it_matters="Essential for balanced reporting",
            related_gaps=["GAP_1"],
        )
        assert mp.description == "The accused party's official response"
        assert mp.why_it_matters == "Essential for balanced reporting"
        assert mp.related_gaps == ["GAP_1"]

    def test_missing_perspective_to_dict(self):
        """to_dict should return correct dict."""
        mp = MissingPerspective(
            description="Expert analysis",
            why_it_matters="Provides context",
            related_gaps=["GAP_2"],
        )
        result = mp.to_dict()

        assert result["description"] == "Expert analysis"
        assert result["why_it_matters"] == "Provides context"
        assert result["related_gaps"] == ["GAP_2"]


# =============================================================================
# TestPrimarySourceDirection
# =============================================================================


class TestPrimarySourceDirection:
    """Tests for PrimarySourceDirection dataclass."""

    def test_primary_source_direction_creation(self):
        """PrimarySourceDirection should create correctly."""
        psd = PrimarySourceDirection(
            source_type=PrimarySourceType.COURT_FILING,
            description="Lawsuit documents from 2020 case",
            search_suggestion="PACER search for defendant name",
            related_gap="GAP_1",
        )
        assert psd.source_type == PrimarySourceType.COURT_FILING
        assert "Lawsuit documents" in psd.description
        assert "PACER" in psd.search_suggestion

    def test_primary_source_direction_source_types(self):
        """PrimarySourceDirection should support all source types."""
        for source_type in PrimarySourceType:
            psd = PrimarySourceDirection(
                source_type=source_type,
                description="Test",
                search_suggestion="Test search",
            )
            assert psd.source_type == source_type

    def test_primary_source_direction_to_dict(self):
        """to_dict should return correct dict with string value."""
        psd = PrimarySourceDirection(
            source_type=PrimarySourceType.SEC_FILING,
            description="10-K annual report",
            search_suggestion="SEC EDGAR search",
        )
        result = psd.to_dict()

        assert result["source_type"] == "sec_filing"  # String value, not enum
        assert result["description"] == "10-K annual report"


# =============================================================================
# TestSearchQuery
# =============================================================================


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_search_query_creation(self):
        """SearchQuery should create correctly."""
        sq = SearchQuery(
            query="company name fraud investigation 2020",
            purpose="Find news coverage of initial investigation",
            platform_suggestion=PlatformSuggestion.NEWS,
            related_gap="GAP_2",
            related_theme="THEME_1",
        )
        assert "fraud investigation" in sq.query
        assert sq.platform_suggestion == PlatformSuggestion.NEWS
        assert sq.related_gap == "GAP_2"

    def test_search_query_platform_suggestions(self):
        """SearchQuery should support all platforms."""
        for platform in PlatformSuggestion:
            sq = SearchQuery(
                query="test query",
                purpose="test purpose",
                platform_suggestion=platform,
            )
            assert sq.platform_suggestion == platform

    def test_search_query_to_dict(self):
        """to_dict should return correct dict with string value."""
        sq = SearchQuery(
            query="test query",
            purpose="test purpose",
            platform_suggestion=PlatformSuggestion.GOOGLE,
        )
        result = sq.to_dict()

        assert result["query"] == "test query"
        assert result["platform_suggestion"] == "google"  # String value


# =============================================================================
# TestResearchQuestion
# =============================================================================


class TestResearchQuestion:
    """Tests for ResearchQuestion dataclass."""

    def test_research_question_creation(self):
        """ResearchQuestion should create correctly."""
        rq = ResearchQuestion(
            question="What was the company's revenue in Q4 2020?",
            why_it_matters="Would verify or contradict claims in testimony",
            related_theme="THEME_1",
        )
        assert "revenue" in rq.question
        assert "verify" in rq.why_it_matters
        assert rq.related_theme == "THEME_1"

    def test_research_question_to_dict(self):
        """to_dict should return correct dict."""
        rq = ResearchQuestion(
            question="Test question?",
            why_it_matters="Test importance",
            related_theme="THEME_2",
        )
        result = rq.to_dict()

        assert result["question"] == "Test question?"
        assert result["why_it_matters"] == "Test importance"
        assert result["related_theme"] == "THEME_2"


# =============================================================================
# TestBoosterOutput
# =============================================================================


class TestBoosterOutput:
    """Tests for BoosterOutput dataclass."""

    def test_booster_output_creation_empty(self):
        """BoosterOutput should create with empty defaults."""
        output = BoosterOutput()
        assert output.missing_perspectives == []
        assert output.primary_source_directions == []
        assert output.suggested_search_queries == []
        assert output.research_questions == []
        assert output.booster_provider == "gemini"
        assert output.booster_timestamp is not None

    def test_booster_output_creation_full(self):
        """BoosterOutput should create with all fields."""
        mp = MissingPerspective("Perspective", "Why", [])
        psd = PrimarySourceDirection(
            PrimarySourceType.COURT_FILING,
            "Court docs",
            "Search PACER",
        )
        sq = SearchQuery(
            "query",
            "purpose",
            PlatformSuggestion.GOOGLE,
        )
        rq = ResearchQuestion("Question?", "Why", "THEME_1")

        output = BoosterOutput(
            missing_perspectives=[mp],
            primary_source_directions=[psd],
            suggested_search_queries=[sq],
            research_questions=[rq],
            booster_provider="gemini",
            context_bundle_hash="abc123",
        )
        assert len(output.missing_perspectives) == 1
        assert len(output.primary_source_directions) == 1
        assert len(output.suggested_search_queries) == 1
        assert len(output.research_questions) == 1

    def test_booster_output_total_directions(self):
        """total_directions should count all direction types."""
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective("A", "B", []),
                MissingPerspective("C", "D", []),
            ],
            primary_source_directions=[
                PrimarySourceDirection(PrimarySourceType.COURT_FILING, "X", "Y"),
            ],
            suggested_search_queries=[
                SearchQuery("Q", "P", PlatformSuggestion.GOOGLE),
            ],
            research_questions=[],
        )
        assert output.total_directions == 4

    def test_booster_output_is_empty_true(self):
        """is_empty should return True when no directions."""
        output = BoosterOutput()
        assert output.is_empty() is True

    def test_booster_output_is_empty_false(self):
        """is_empty should return False when has directions."""
        output = BoosterOutput(
            missing_perspectives=[MissingPerspective("A", "B", [])],
        )
        assert output.is_empty() is False

    def test_booster_output_to_dict(self):
        """to_dict should return correctly structured dict."""
        mp = MissingPerspective("Perspective", "Why", [])
        output = BoosterOutput(
            missing_perspectives=[mp],
            booster_provider="gemini",
            context_bundle_hash="hash123",
        )
        result = output.to_dict()

        assert len(result["missing_perspectives"]) == 1
        assert result["booster_provider"] == "gemini"
        assert result["context_bundle_hash"] == "hash123"
        assert "booster_timestamp" in result


# =============================================================================
# TestBoosterConstraints
# =============================================================================


class TestBoosterConstraints:
    """Tests to verify booster produces DIRECTIONS, not FACTS."""

    def test_context_bundle_no_raw_content(self):
        """ContextBundle should not contain raw content fields."""
        bundle = ContextBundle()

        # Should NOT have these fields
        assert not hasattr(bundle, "full_text")
        assert not hasattr(bundle, "transcript")
        assert not hasattr(bundle, "quotes")
        assert not hasattr(bundle, "source_urls")
        assert not hasattr(bundle, "claims")

    def test_context_bundle_only_summaries(self):
        """ContextBundle should only contain summaries."""
        bundle = ContextBundle(
            key_point_summaries=["Point 1 summary", "Point 2 summary"],
            themes=[ThemeSummary("T1", "Label", "Desc")],
        )

        # Should have summary fields
        assert isinstance(bundle.key_point_summaries, list)
        assert isinstance(bundle.themes, list)
        assert all(isinstance(s, str) for s in bundle.key_point_summaries)

    def test_booster_output_is_directions(self):
        """BoosterOutput should contain directions, not assertions."""
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective(
                    description="Find expert perspective",
                    why_it_matters="Adds context",
                    related_gaps=[],
                )
            ],
            research_questions=[
                ResearchQuestion(
                    question="What documents exist?",  # Question, not assertion
                    why_it_matters="Would fill gap",
                    related_theme="THEME_1",
                )
            ],
        )

        # Directions point WHERE to look, not WHAT you'll find
        for mp in output.missing_perspectives:
            assert "why_it_matters" in mp.to_dict()  # Explains purpose

        for rq in output.research_questions:
            assert "?" in rq.question  # Is a question, not a statement
