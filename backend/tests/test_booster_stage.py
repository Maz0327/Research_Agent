"""
Unit tests for booster stage.

Tests for: build_booster_prompt, parse_booster_response,
validate_booster_output, run_booster.

Phase 9 Task 9.2.5
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.models.booster_models import (
    BoosterOutput,
    ContextBundle,
    GapSummary,
    MissingPerspective,
    PlatformSuggestion,
    PrimarySourceDirection,
    PrimarySourceType,
    ResearchQuestion,
    SearchQuery,
    TensionSummary,
    ThemeSummary,
)
from backend.pipeline.stages.booster_stage import (
    build_booster_prompt,
    parse_booster_response,
    validate_booster_output,
    run_booster,
    booster_output_to_dict,
)


# =============================================================================
# Helper Functions
# =============================================================================


def create_minimal_bundle() -> ContextBundle:
    """Create a minimal context bundle for testing."""
    return ContextBundle(
        scope_in=["Topic A"],
        scope_out=["Topic B"],
        themes=[],
        tensions=[],
        gaps=[],
        key_point_summaries=[],
        source_count=1,
        source_types=["youtube"],
        confidence_level="medium",
        job_id="test_job",
    )


def create_full_bundle() -> ContextBundle:
    """Create a context bundle with all fields populated."""
    return ContextBundle(
        scope_in=["Financial fraud", "Corporate misconduct"],
        scope_out=["General investing tips"],
        themes=[
            ThemeSummary(
                theme_id="THEME_1",
                label="Financial Opacity",
                description="Lack of transparency in financial reporting",
            ),
            ThemeSummary(
                theme_id="THEME_2",
                label="Timeline Discrepancies",
                description="Conflicting accounts of when events occurred",
            ),
        ],
        tensions=[
            TensionSummary(
                tension_id="TEN_1",
                description="CEO claims vs whistleblower account",
            ),
        ],
        gaps=[
            GapSummary(
                gap_id="GAP_1",
                description="Missing company official response",
            ),
            GapSummary(
                gap_id="GAP_2",
                description="No financial expert analysis",
            ),
        ],
        key_point_summaries=[
            "Company reported record profits in Q4",
            "Whistleblower alleges fraud in accounting",
            "Stock price dropped 40% after allegations",
        ],
        source_count=5,
        source_types=["youtube", "article"],
        confidence_level="high",
        job_id="test_job_123",
        generated_at="2024-01-15T10:00:00Z",
    )


# =============================================================================
# TestBuildBoosterPrompt
# =============================================================================


class TestBuildBoosterPrompt:
    """Tests for build_booster_prompt function."""

    def test_build_prompt_minimal_bundle(self):
        """Minimal bundle should produce valid prompt."""
        bundle = create_minimal_bundle()
        prompt = build_booster_prompt(bundle)

        assert "test_job" in prompt
        assert "Topic A" in prompt
        assert "Topic B" in prompt
        assert "(No themes identified)" in prompt
        assert "(No gaps identified)" in prompt

    def test_build_prompt_full_bundle(self):
        """Full bundle should include all context."""
        bundle = create_full_bundle()
        prompt = build_booster_prompt(bundle)

        assert "test_job_123" in prompt
        assert "Financial fraud" in prompt
        assert "THEME_1: Financial Opacity" in prompt
        assert "THEME_2: Timeline Discrepancies" in prompt
        assert "GAP_1: Missing company official response" in prompt
        assert "TEN_1: CEO claims vs whistleblower account" in prompt
        assert "Company reported record profits" in prompt

    def test_build_prompt_limits_key_points(self):
        """Prompt should limit key points to prevent context bloat."""
        bundle = create_minimal_bundle()
        # Add 20 key points
        bundle.key_point_summaries = [f"Key point {i}" for i in range(20)]

        prompt = build_booster_prompt(bundle)

        # Should only include first 15
        assert "Key point 0" in prompt
        assert "Key point 14" in prompt
        assert "Key point 15" not in prompt  # Should be cut off

    def test_build_prompt_includes_confidence_level(self):
        """Prompt should include confidence level."""
        bundle = create_full_bundle()
        prompt = build_booster_prompt(bundle)

        assert "high" in prompt  # confidence_level

    def test_build_prompt_includes_source_count(self):
        """Prompt should include source count."""
        bundle = create_full_bundle()
        prompt = build_booster_prompt(bundle)

        assert "5" in prompt  # source_count


# =============================================================================
# TestParseBoosterResponse
# =============================================================================


class TestParseBoosterResponse:
    """Tests for parse_booster_response function."""

    def test_parse_empty_response(self):
        """Empty response should produce empty output."""
        bundle = create_minimal_bundle()
        output = parse_booster_response({}, bundle)

        assert output.missing_perspectives == []
        assert output.primary_source_directions == []
        assert output.suggested_search_queries == []
        assert output.research_questions == []
        assert output.booster_provider == "gemini"
        assert output.booster_timestamp is not None

    def test_parse_missing_perspectives(self):
        """Missing perspectives should be parsed correctly."""
        bundle = create_full_bundle()
        data = {
            "missing_perspectives": [
                {
                    "description": "Company official statement",
                    "why_it_matters": "Provides balance",
                    "related_gaps": ["GAP_1"],
                },
                {
                    "description": "Financial analyst view",
                    "why_it_matters": "Expert context",
                    "related_gaps": ["GAP_2"],
                },
            ]
        }

        output = parse_booster_response(data, bundle)

        assert len(output.missing_perspectives) == 2
        assert output.missing_perspectives[0].description == "Company official statement"
        assert output.missing_perspectives[0].related_gaps == ["GAP_1"]

    def test_parse_primary_source_directions(self):
        """Primary source directions should be parsed with correct types."""
        bundle = create_full_bundle()
        data = {
            "primary_source_directions": [
                {
                    "source_type": "court_filing",
                    "description": "Lawsuit documents",
                    "search_suggestion": "PACER search",
                    "related_gap": "GAP_1",
                },
                {
                    "source_type": "sec_filing",
                    "description": "10-K report",
                    "search_suggestion": "EDGAR search",
                },
            ]
        }

        output = parse_booster_response(data, bundle)

        assert len(output.primary_source_directions) == 2
        assert output.primary_source_directions[0].source_type == PrimarySourceType.COURT_FILING
        assert output.primary_source_directions[1].source_type == PrimarySourceType.SEC_FILING

    def test_parse_invalid_source_type_defaults_to_other(self):
        """Invalid source type should default to OTHER."""
        bundle = create_minimal_bundle()
        data = {
            "primary_source_directions": [
                {
                    "source_type": "invalid_type",
                    "description": "Test",
                    "search_suggestion": "Test",
                },
            ]
        }

        output = parse_booster_response(data, bundle)

        assert output.primary_source_directions[0].source_type == PrimarySourceType.OTHER

    def test_parse_search_queries(self):
        """Search queries should be parsed with correct platforms."""
        bundle = create_full_bundle()
        data = {
            "suggested_search_queries": [
                {
                    "query": "company fraud lawsuit 2024",
                    "purpose": "Find legal filings",
                    "platform_suggestion": "google",
                    "related_gap": "GAP_1",
                },
                {
                    "query": "CEO interview reddit",
                    "purpose": "Find discussions",
                    "platform_suggestion": "reddit",
                    "related_theme": "THEME_1",
                },
            ]
        }

        output = parse_booster_response(data, bundle)

        assert len(output.suggested_search_queries) == 2
        assert output.suggested_search_queries[0].platform_suggestion == PlatformSuggestion.GOOGLE
        assert output.suggested_search_queries[1].platform_suggestion == PlatformSuggestion.REDDIT

    def test_parse_invalid_platform_defaults_to_google(self):
        """Invalid platform should default to GOOGLE."""
        bundle = create_minimal_bundle()
        data = {
            "suggested_search_queries": [
                {
                    "query": "test query",
                    "purpose": "test",
                    "platform_suggestion": "invalid_platform",
                },
            ]
        }

        output = parse_booster_response(data, bundle)

        assert output.suggested_search_queries[0].platform_suggestion == PlatformSuggestion.GOOGLE

    def test_parse_research_questions(self):
        """Research questions should be parsed correctly."""
        bundle = create_full_bundle()
        data = {
            "research_questions": [
                {
                    "question": "What documents support the timeline?",
                    "why_it_matters": "Would verify claims",
                    "related_theme": "THEME_2",
                },
            ]
        }

        output = parse_booster_response(data, bundle)

        assert len(output.research_questions) == 1
        assert "timeline" in output.research_questions[0].question
        assert output.research_questions[0].related_theme == "THEME_2"

    def test_parse_includes_bundle_hash(self):
        """Output should include context bundle hash."""
        bundle = create_full_bundle()
        output = parse_booster_response({}, bundle)

        assert output.context_bundle_hash is not None
        assert len(output.context_bundle_hash) > 0


# =============================================================================
# TestValidateBoosterOutput
# =============================================================================


class TestValidateBoosterOutput:
    """Tests for validate_booster_output function."""

    def test_validate_empty_output_passes(self):
        """Empty output should pass validation."""
        bundle = create_full_bundle()
        output = BoosterOutput()

        warnings = validate_booster_output(output, bundle)

        assert warnings == []

    def test_validate_valid_gap_references_pass(self):
        """Valid gap references should pass."""
        bundle = create_full_bundle()  # Has GAP_1 and GAP_2
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective("Test", "Why", related_gaps=["GAP_1"]),
            ],
            primary_source_directions=[
                PrimarySourceDirection(
                    PrimarySourceType.COURT_FILING,
                    "Test",
                    "Search",
                    related_gap="GAP_2",
                ),
            ],
        )

        warnings = validate_booster_output(output, bundle)

        assert warnings == []

    def test_validate_invalid_gap_reference_warns(self):
        """Invalid gap reference should produce warning."""
        bundle = create_full_bundle()  # Has GAP_1 and GAP_2
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective("Test", "Why", related_gaps=["GAP_INVALID"]),
            ],
        )

        warnings = validate_booster_output(output, bundle)

        assert len(warnings) == 1
        assert "GAP_INVALID" in warnings[0]

    def test_validate_invalid_theme_reference_warns(self):
        """Invalid theme reference should produce warning."""
        bundle = create_full_bundle()  # Has THEME_1 and THEME_2
        output = BoosterOutput(
            suggested_search_queries=[
                SearchQuery(
                    "query",
                    "purpose",
                    PlatformSuggestion.GOOGLE,
                    related_theme="THEME_INVALID",
                ),
            ],
        )

        warnings = validate_booster_output(output, bundle)

        assert len(warnings) == 1
        assert "THEME_INVALID" in warnings[0]

    def test_validate_multiple_invalid_references(self):
        """Multiple invalid references should all warn."""
        bundle = create_full_bundle()
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective("Test", "Why", related_gaps=["INVALID_1", "INVALID_2"]),
            ],
            suggested_search_queries=[
                SearchQuery("q", "p", PlatformSuggestion.GOOGLE, related_theme="INVALID_3"),
            ],
        )

        warnings = validate_booster_output(output, bundle)

        assert len(warnings) == 3

    def test_validate_none_references_pass(self):
        """None references should be skipped, not flagged."""
        bundle = create_full_bundle()
        output = BoosterOutput(
            primary_source_directions=[
                PrimarySourceDirection(
                    PrimarySourceType.COURT_FILING,
                    "Test",
                    "Search",
                    related_gap=None,  # None should be fine
                ),
            ],
            suggested_search_queries=[
                SearchQuery("q", "p", PlatformSuggestion.GOOGLE, related_gap=None, related_theme=None),
            ],
        )

        warnings = validate_booster_output(output, bundle)

        assert warnings == []


# =============================================================================
# TestRunBooster
# =============================================================================


class TestRunBooster:
    """Tests for run_booster function."""

    @patch("backend.pipeline.stages.booster_stage.GeminiClient")
    def test_run_booster_success(self, mock_client_class):
        """Successful booster run should return output, cost, and warnings."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "data": {
                "missing_perspectives": [
                    {
                        "description": "Expert view",
                        "why_it_matters": "Adds context",
                        "related_gaps": [],
                    }
                ],
            },
            "cost": 0.05,
        }

        bundle = create_full_bundle()
        output, cost, warnings = run_booster(bundle)

        assert len(output.missing_perspectives) == 1
        assert cost == 0.05
        assert warnings == []

    @patch("backend.pipeline.stages.booster_stage.GeminiClient")
    def test_run_booster_gemini_error(self, mock_client_class):
        """Gemini error should raise RuntimeError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "error": "API rate limit exceeded",
        }

        bundle = create_full_bundle()

        with pytest.raises(RuntimeError) as exc_info:
            run_booster(bundle)

        assert "API rate limit exceeded" in str(exc_info.value)

    @patch("backend.pipeline.stages.booster_stage.GeminiClient")
    def test_run_booster_uses_higher_temperature(self, mock_client_class):
        """Booster should use higher temperature for creative directions."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "data": {},
            "cost": 0.01,
        }

        bundle = create_full_bundle()
        run_booster(bundle)

        # Check that temperature was passed
        call_kwargs = mock_client.generate_json.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.45

    @patch("backend.pipeline.stages.booster_stage.GeminiClient")
    def test_run_booster_returns_warnings_on_invalid_refs(self, mock_client_class):
        """Invalid references in response should produce warnings."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "data": {
                "missing_perspectives": [
                    {
                        "description": "Test",
                        "why_it_matters": "Test",
                        "related_gaps": ["INVALID_GAP"],  # Invalid reference
                    }
                ],
            },
            "cost": 0.01,
        }

        bundle = create_full_bundle()
        output, cost, warnings = run_booster(bundle)

        assert len(warnings) == 1
        assert "INVALID_GAP" in warnings[0]


# =============================================================================
# TestBoosterOutputToDict
# =============================================================================


class TestBoosterOutputToDict:
    """Tests for booster_output_to_dict function."""

    def test_to_dict_empty_output(self):
        """Empty output should serialize to dict."""
        output = BoosterOutput()
        result = booster_output_to_dict(output)

        assert result["missing_perspectives"] == []
        assert result["primary_source_directions"] == []
        assert result["suggested_search_queries"] == []
        assert result["research_questions"] == []
        assert result["booster_provider"] == "gemini"

    def test_to_dict_full_output(self):
        """Full output should serialize all fields."""
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective("Test perspective", "Test importance", ["GAP_1"]),
            ],
            primary_source_directions=[
                PrimarySourceDirection(PrimarySourceType.COURT_FILING, "Court docs", "PACER"),
            ],
            suggested_search_queries=[
                SearchQuery("test query", "test purpose", PlatformSuggestion.GOOGLE),
            ],
            research_questions=[
                ResearchQuestion("Test question?", "Test importance", "THEME_1"),
            ],
            booster_provider="gemini",
            context_bundle_hash="abc123",
        )

        result = booster_output_to_dict(output)

        assert len(result["missing_perspectives"]) == 1
        assert len(result["primary_source_directions"]) == 1
        assert len(result["suggested_search_queries"]) == 1
        assert len(result["research_questions"]) == 1
        assert result["context_bundle_hash"] == "abc123"

    def test_to_dict_json_serializable(self):
        """Output dict should be JSON-serializable."""
        import json

        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective("Test", "Why", []),
            ],
            primary_source_directions=[
                PrimarySourceDirection(PrimarySourceType.SEC_FILING, "Filing", "Search"),
            ],
        )

        result = booster_output_to_dict(output)
        # Should not raise
        json.dumps(result)


# =============================================================================
# TestBoosterConstraints
# =============================================================================


class TestBoosterConstraints:
    """Tests verifying booster produces DIRECTIONS, not FACTS."""

    def test_booster_output_is_directions_not_facts(self):
        """BoosterOutput should contain directions, not assertions."""
        output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective(
                    description="Find expert perspective",  # Direction
                    why_it_matters="Would provide context",  # Reason
                    related_gaps=["GAP_1"],  # Link to existing gaps
                ),
            ],
            research_questions=[
                ResearchQuestion(
                    question="What documents exist?",  # Question, not statement
                    why_it_matters="Would fill gap",
                    related_theme="THEME_1",
                ),
            ],
        )

        # All directions should point WHERE to look
        for mp in output.missing_perspectives:
            # Should have explanation of why
            assert mp.why_it_matters is not None

        for rq in output.research_questions:
            # Should be a question
            assert "?" in rq.question

    def test_search_queries_are_suggestions(self):
        """Search queries should be suggestions, not commands."""
        output = BoosterOutput(
            suggested_search_queries=[
                SearchQuery(
                    query="company name lawsuit 2024",
                    purpose="Find potential legal actions",  # Purpose explains why
                    platform_suggestion=PlatformSuggestion.GOOGLE,
                ),
            ],
        )

        # Queries have purpose explaining what to look for
        for sq in output.suggested_search_queries:
            assert sq.purpose is not None
            assert len(sq.purpose) > 0

    def test_primary_sources_have_search_suggestions(self):
        """Primary source directions should include how to find them."""
        output = BoosterOutput(
            primary_source_directions=[
                PrimarySourceDirection(
                    source_type=PrimarySourceType.COURT_FILING,
                    description="Lawsuit documents from 2020",
                    search_suggestion="PACER search for defendant name",  # How to find
                ),
            ],
        )

        # All directions should have search suggestions
        for psd in output.primary_source_directions:
            assert psd.search_suggestion is not None
            assert len(psd.search_suggestion) > 0

    def test_context_bundle_excludes_raw_content(self):
        """ContextBundle should not contain raw source content."""
        bundle = ContextBundle()

        # These fields should NOT exist on ContextBundle
        assert not hasattr(bundle, "full_text")
        assert not hasattr(bundle, "transcript")
        assert not hasattr(bundle, "quotes")
        assert not hasattr(bundle, "source_urls")
        assert not hasattr(bundle, "claims")

    def test_booster_total_directions_counts_all_types(self):
        """total_directions should count all direction types."""
        output = BoosterOutput(
            missing_perspectives=[MissingPerspective("A", "B", [])],
            primary_source_directions=[
                PrimarySourceDirection(PrimarySourceType.COURT_FILING, "X", "Y"),
                PrimarySourceDirection(PrimarySourceType.SEC_FILING, "X", "Y"),
            ],
            suggested_search_queries=[
                SearchQuery("Q", "P", PlatformSuggestion.GOOGLE),
            ],
            research_questions=[
                ResearchQuestion("Q?", "W", "T"),
                ResearchQuestion("Q2?", "W", "T"),
            ],
        )

        # 1 + 2 + 1 + 2 = 6 total directions
        assert output.total_directions == 6
