"""Tests for Phase 3 Full Research Assistant Pipeline fixes.

These tests verify the critical fixes implemented for:
- C-001: JSON parsing with error tracking
- C-002: API timeout configuration
- C-003: Bounded video processing
- C-004: Input validation
- H-001: Robust JSON parsing utility
- H-011: YouTube URL validation
- H-013: parse_error flag in dataclasses
"""

import json
import pytest
from dataclasses import asdict

from backend.models.video_analysis_models import (
    ContentBlueprint,
    GapAnalysis,
    ResearchStarter,
    ActSection,
    OpenLoop,
    MissingPerspective,
    CoverageBlindSpot,
    Contradiction,
    SearchQuery,
    SourceSuggestion,
    RabbitHole,
    ContentAngle,
)


class TestContentBlueprintDataclass:
    """Tests for ContentBlueprint dataclass structure."""

    def test_parse_error_field_exists(self):
        """C-001/H-013: ContentBlueprint should have parse_error field."""
        blueprint = ContentBlueprint(
            video_url="https://www.youtube.com/watch?v=test123",
            title="Test Video",
            hook_technique="Pattern interrupt",
            hook_timestamp="0:30",
            hook_description="Description of hook",
            structure_type="3-act",
            act_breakdown=[],
            open_loops=[],
        )
        assert hasattr(blueprint, "parse_error")
        assert blueprint.parse_error is False

    def test_parse_error_can_be_set_true(self):
        """H-013: parse_error should be settable to True."""
        blueprint = ContentBlueprint(
            video_url="https://www.youtube.com/watch?v=test123",
            title="Test Video",
            hook_technique="Pattern interrupt",
            hook_timestamp="0:30",
            hook_description="Description of hook",
            structure_type="3-act",
            act_breakdown=[],
            open_loops=[],
            parse_error=True,
        )
        assert blueprint.parse_error is True

    def test_to_dict_includes_parse_error(self):
        """H-013: to_dict should include parse_error field."""
        blueprint = ContentBlueprint(
            video_url="https://www.youtube.com/watch?v=test123",
            title="Test Video",
            hook_technique="Pattern interrupt",
            hook_timestamp="0:30",
            hook_description="Description of hook",
            structure_type="3-act",
            act_breakdown=[],
            open_loops=[],
            parse_error=True,
        )
        result = blueprint.to_dict()
        assert "parse_error" in result
        assert result["parse_error"] is True


class TestGapAnalysisDataclass:
    """Tests for GapAnalysis dataclass structure."""

    def test_parse_error_field_exists(self):
        """C-001/H-013: GapAnalysis should have parse_error field."""
        gap = GapAnalysis(
            missing_perspectives=[],
            unanswered_questions=[],
            mentioned_but_unexplored=[],
            contradictions=[],
        )
        assert hasattr(gap, "parse_error")
        assert gap.parse_error is False

    def test_parse_error_can_be_set_true(self):
        """H-013: parse_error should be settable to True."""
        gap = GapAnalysis(
            missing_perspectives=[],
            unanswered_questions=[],
            mentioned_but_unexplored=[],
            contradictions=[],
            parse_error=True,
        )
        assert gap.parse_error is True


class TestResearchStarterDataclass:
    """Tests for ResearchStarter dataclass structure."""

    def test_parse_error_field_exists(self):
        """C-001/H-013: ResearchStarter should have parse_error field."""
        starter = ResearchStarter(
            search_queries=[],
            source_suggestions=[],
            rabbit_holes=[],
            content_angles=[],
        )
        assert hasattr(starter, "parse_error")
        assert starter.parse_error is False

    def test_parse_error_can_be_set_true(self):
        """H-013: parse_error should be settable to True."""
        starter = ResearchStarter(
            search_queries=[],
            source_suggestions=[],
            rabbit_holes=[],
            content_angles=[],
            parse_error=True,
        )
        assert starter.parse_error is True


class TestJsonParsingUtility:
    """Tests for the JSON parsing utility function."""

    def test_parse_json_from_llm_response_import(self):
        """H-001: parse_json_from_llm_response should be importable."""
        from backend.integrations.gemini_client import parse_json_from_llm_response

        assert callable(parse_json_from_llm_response)

    def test_parse_plain_json(self):
        """H-001: Should parse plain JSON."""
        from backend.integrations.gemini_client import parse_json_from_llm_response

        result = parse_json_from_llm_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_code_block(self):
        """H-001: Should parse JSON in ```json code block."""
        from backend.integrations.gemini_client import parse_json_from_llm_response

        response = '```json\n{"key": "value"}\n```'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}

    def test_parse_json_with_plain_code_block(self):
        """H-001: Should parse JSON in ``` code block."""
        from backend.integrations.gemini_client import parse_json_from_llm_response

        response = '```\n{"key": "value"}\n```'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}

    def test_parse_json_with_trailing_text(self):
        """H-001: Should parse JSON with trailing text."""
        from backend.integrations.gemini_client import parse_json_from_llm_response

        response = 'Here is the result: {"key": "value"} Hope this helps!'
        result = parse_json_from_llm_response(response)
        assert result == {"key": "value"}

    def test_parse_invalid_json_raises_error(self):
        """H-001: Should raise GeminiParseError for invalid JSON."""
        from backend.integrations.gemini_client import parse_json_from_llm_response, GeminiParseError

        with pytest.raises(GeminiParseError):
            parse_json_from_llm_response("not json at all")


class TestYouTubeUrlValidation:
    """Tests for YouTube URL validation."""

    def test_validate_youtube_url_import(self):
        """H-011: validate_youtube_url should be importable."""
        from backend.integrations.gemini_client import validate_youtube_url

        assert callable(validate_youtube_url)

    def test_valid_youtube_url(self):
        """H-011: Should accept valid YouTube URLs."""
        from backend.integrations.gemini_client import validate_youtube_url

        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert validate_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert validate_youtube_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_invalid_youtube_url(self):
        """H-011: Should reject invalid YouTube URLs."""
        from backend.integrations.gemini_client import validate_youtube_url

        assert not validate_youtube_url("https://vimeo.com/123456")
        assert not validate_youtube_url("not a url")
        assert not validate_youtube_url("")
        assert not validate_youtube_url("https://youtube.com/")  # No video ID

    def test_youtube_url_with_extra_params(self):
        """H-011: Should accept YouTube URLs with extra parameters."""
        from backend.integrations.gemini_client import validate_youtube_url

        assert validate_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=60s"
        )
        assert validate_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest"
        )


class TestGeminiClientConstants:
    """Tests for GeminiClient constants."""

    def test_max_videos_constant_exists(self):
        """C-003: MAX_VIDEOS_PER_JOB constant should exist."""
        from backend.integrations.gemini_client import MAX_VIDEOS_PER_JOB

        assert isinstance(MAX_VIDEOS_PER_JOB, int)
        assert MAX_VIDEOS_PER_JOB == 20

    def test_api_timeout_constant_exists(self):
        """C-002: API_TIMEOUT_SECONDS constant should exist."""
        from backend.integrations.gemini_client import API_TIMEOUT_SECONDS

        assert isinstance(API_TIMEOUT_SECONDS, int)
        assert API_TIMEOUT_SECONDS > 0

    def test_progress_constants_exist(self):
        """L-002/L-007: Progress constants should exist."""
        from backend.integrations.gemini_client import PROGRESS_START, PROGRESS_RANGE

        assert isinstance(PROGRESS_START, int)
        assert isinstance(PROGRESS_RANGE, int)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_gemini_parse_error_import(self):
        """C-001: GeminiParseError should be importable."""
        from backend.integrations.gemini_client import GeminiParseError

        assert issubclass(GeminiParseError, Exception)

    def test_gemini_timeout_error_import(self):
        """C-002: GeminiTimeoutError should be importable."""
        from backend.integrations.gemini_client import GeminiTimeoutError

        assert issubclass(GeminiTimeoutError, Exception)

    def test_gemini_parse_error_message(self):
        """C-001: GeminiParseError should accept message."""
        from backend.integrations.gemini_client import GeminiParseError

        error = GeminiParseError("Failed to parse JSON response")
        assert str(error) == "Failed to parse JSON response"

    def test_gemini_timeout_error_message(self):
        """C-002: GeminiTimeoutError should accept message."""
        from backend.integrations.gemini_client import GeminiTimeoutError

        error = GeminiTimeoutError("API call timed out after 300s")
        assert str(error) == "API call timed out after 300s"


class TestActSection:
    """Tests for ActSection dataclass."""

    def test_act_section_creation(self):
        """Verify ActSection can be created with required fields."""
        act = ActSection(
            name="Introduction",
            timestamp_start="0:00",
            timestamp_end="2:30",
            description="The setup and context",
        )
        assert act.name == "Introduction"
        assert act.timestamp_start == "0:00"
        assert act.timestamp_end == "2:30"

    def test_act_section_to_dict(self):
        """Verify ActSection to_dict works."""
        act = ActSection(
            name="Introduction",
            timestamp_start="0:00",
            timestamp_end="2:30",
            description="The setup and context",
        )
        result = act.to_dict()
        assert result["name"] == "Introduction"
        assert result["timestamp_start"] == "0:00"


class TestOpenLoop:
    """Tests for OpenLoop dataclass."""

    def test_open_loop_creation(self):
        """Verify OpenLoop can be created with required fields."""
        loop = OpenLoop(
            timestamp="1:30",
            technique="question",
            description="Raises a question about the outcome",
        )
        assert loop.timestamp == "1:30"
        assert loop.technique == "question"

    def test_open_loop_to_dict(self):
        """Verify OpenLoop to_dict works."""
        loop = OpenLoop(
            timestamp="1:30",
            technique="question",
            description="Raises a question about the outcome",
        )
        result = loop.to_dict()
        assert result["timestamp"] == "1:30"


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_search_query_creation(self):
        """Verify SearchQuery can be created."""
        query = SearchQuery(
            query="site:reddit.com AI research",
            platform="google",
            why="Find community discussions",
        )
        assert query.platform == "google"
        assert query.query == "site:reddit.com AI research"


class TestSourceSuggestion:
    """Tests for SourceSuggestion dataclass."""

    def test_source_suggestion_creation(self):
        """Verify SourceSuggestion can be created."""
        source = SourceSuggestion(
            source_type="academic",
            description="ArXiv papers on topic",
            why_helpful="Primary research",
        )
        assert source.source_type == "academic"


class TestRabbitHole:
    """Tests for RabbitHole dataclass."""

    def test_rabbit_hole_creation(self):
        """Verify RabbitHole can be created."""
        hole = RabbitHole(
            topic="Related subtopic",
            mentioned_in="Video title at timestamp",
            potential_angle="Unique angle to explore",
        )
        assert hole.topic == "Related subtopic"


class TestContentAngle:
    """Tests for ContentAngle dataclass."""

    def test_content_angle_creation(self):
        """Verify ContentAngle can be created."""
        angle = ContentAngle(
            angle="Contrarian take",
            differentiator="First to cover this aspect",
            why_unique="Different methodology",
        )
        assert angle.angle == "Contrarian take"


class TestMissingPerspective:
    """Tests for MissingPerspective dataclass."""

    def test_missing_perspective_creation(self):
        """Verify MissingPerspective can be created."""
        perspective = MissingPerspective(
            perspective="Expert economist view",
            why_important="Adds credibility",
            suggested_search="economist interview topic",
        )
        assert perspective.perspective == "Expert economist view"


class TestCoverageBlindSpot:
    """Tests for CoverageBlindSpot dataclass."""

    def test_coverage_blind_spot_creation(self):
        """Verify CoverageBlindSpot can be created."""
        blind_spot = CoverageBlindSpot(
            topic="Historical context",
            where_mentioned="Video A at 5:30",
            why_explore="Provides background",
        )
        assert blind_spot.topic == "Historical context"


class TestContradiction:
    """Tests for Contradiction dataclass."""

    def test_contradiction_creation(self):
        """Verify Contradiction can be created."""
        contradiction = Contradiction(
            claim_a="Statement 1",
            source_a="Video A",
            claim_b="Statement 2",
            source_b="Video B",
            opportunity="Clarify methodology",
        )
        assert contradiction.source_a == "Video A"
        assert contradiction.opportunity == "Clarify methodology"


class TestGapAnalysisToDict:
    """Tests for GapAnalysis to_dict method."""

    def test_to_dict_includes_all_fields(self):
        """Verify GapAnalysis to_dict includes all fields."""
        gap = GapAnalysis(
            missing_perspectives=[
                MissingPerspective(
                    perspective="test",
                    why_important="test",
                    suggested_search="test",
                )
            ],
            unanswered_questions=["What happened?"],
            mentioned_but_unexplored=[],
            contradictions=[],
            parse_error=True,
        )
        result = gap.to_dict()
        assert "missing_perspectives" in result
        assert "unanswered_questions" in result
        assert "parse_error" in result
        assert result["parse_error"] is True


class TestResearchStarterToDict:
    """Tests for ResearchStarter to_dict method."""

    def test_to_dict_includes_all_fields(self):
        """Verify ResearchStarter to_dict includes all fields."""
        starter = ResearchStarter(
            search_queries=[
                SearchQuery(query="test", platform="google", why="test")
            ],
            source_suggestions=[],
            rabbit_holes=[],
            content_angles=[],
            parse_error=True,
        )
        result = starter.to_dict()
        assert "search_queries" in result
        assert "source_suggestions" in result
        assert "parse_error" in result
        assert result["parse_error"] is True
