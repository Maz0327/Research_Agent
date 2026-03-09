"""
Tests for Kimi K2.5 visual frame analysis integration.

Tests the wiring in semantic_extraction.py:
- _run_visual_frame_analysis() — main helper
- _analyze_frames_with_fallback() — Kimi primary, Gemini fallback
- _download_video_for_frames() — yt-dlp video download
- extract_video_observations() — integration with visual analysis

All tests are fully mocked — no real API calls, no network, no ffmpeg.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.models.semantic_units import (
    AnalysisMode,
    SemanticExtractionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_settings_with_kimi():
    """Settings with KIMI_API_KEY configured."""
    settings = MagicMock()
    settings.kimi_api_key = "test-kimi-key-123"
    settings.google_api_key = "test-google-key-456"
    return settings


@pytest.fixture
def mock_settings_without_kimi():
    """Settings without KIMI_API_KEY."""
    settings = MagicMock()
    settings.kimi_api_key = None
    settings.google_api_key = "test-google-key-456"
    return settings


@pytest.fixture
def mock_frame_result():
    """Mock FrameExtractionResult with fake frame paths."""
    result = MagicMock()
    result.frames = [
        Path("/tmp/ra_frames_test/frame_0001.jpg"),
        Path("/tmp/ra_frames_test/frame_0002.jpg"),
        Path("/tmp/ra_frames_test/frame_0003.jpg"),
    ]
    result.frame_count = 3
    result.output_dir = Path("/tmp/ra_frames_test")
    return result


@pytest.fixture
def kimi_visual_dict():
    """Mock visual analysis dict (as returned by VideoVisualAnalysis.to_dict())."""
    return {
        "source_id": "SRC_1",
        "frame_analyses": [
            {
                "frame_index": 0,
                "timestamp_approx": "0:00:00",
                "content_type": "interview",
                "is_original_content": True,
                "is_third_party": False,
                "confidence": "high",
                "text_detected": "",
                "notable_elements": ["person"],
            },
            {
                "frame_index": 1,
                "timestamp_approx": "0:00:10",
                "content_type": "b-roll",
                "is_original_content": True,
                "is_third_party": False,
                "confidence": "medium",
                "text_detected": "",
                "notable_elements": ["cityscape"],
            },
            {
                "frame_index": 2,
                "timestamp_approx": "0:00:20",
                "content_type": "news_clip",
                "is_original_content": False,
                "is_third_party": True,
                "confidence": "high",
                "text_detected": "Breaking News",
                "notable_elements": ["news_anchor", "chyron"],
            },
        ],
        "overall_content_mix": "Mix of interview and third-party news clips",
        "third_party_ratio": 0.33,
        "analysis_cost": 0.005,
    }


@pytest.fixture
def base_extraction():
    """Base SemanticExtractionResult for testing."""
    return SemanticExtractionResult(
        source_id="SRC_1",
        analysis_mode=AnalysisMode.VIDEO_ONLY,
    )


# ---------------------------------------------------------------------------
# _analyze_frames_with_fallback tests
# ---------------------------------------------------------------------------

class TestAnalyzeFramesWithFallback:
    """Tests for _analyze_frames_with_fallback()."""

    def test_kimi_success(self, kimi_visual_dict):
        """When Kimi succeeds, returns Kimi result without fallback."""
        from backend.pipeline.stages.semantic_extraction import (
            _analyze_frames_with_fallback,
        )

        mock_kimi_result = MagicMock()
        mock_kimi_result.to_dict.return_value = kimi_visual_dict
        mock_kimi_result.analysis_cost = 0.005
        mock_kimi_result.frame_analyses = [MagicMock()] * 3
        mock_kimi_result.third_party_ratio = 0.33

        with patch(
            "backend.integrations.kimi_vision_client.KimiVisionClient"
        ) as MockKimi:
            MockKimi.return_value.analyze_video_frames.return_value = mock_kimi_result

            result_dict, cost, warnings, provider = _analyze_frames_with_fallback(
                frame_paths=[Path("/tmp/f1.jpg"), Path("/tmp/f2.jpg")],
                video_title="Test Video",
                research_topic="testing",
                source_id="SRC_1",
                interval_seconds=10,
                kimi_api_key="test-key",
            )

            assert provider == "kimi"
            assert cost == 0.005
            assert result_dict is not None
            assert result_dict["source_id"] == "SRC_1"
            assert len(warnings) == 0

    def test_kimi_fails_gemini_fallback(self):
        """When Kimi fails, falls back to Gemini successfully."""
        from backend.pipeline.stages.semantic_extraction import (
            _analyze_frames_with_fallback,
        )
        from backend.integrations.kimi_vision_client import KimiVisionError

        # Mock Kimi to fail
        with patch(
            "backend.integrations.kimi_vision_client.KimiVisionClient"
        ) as MockKimi:
            MockKimi.return_value.analyze_video_frames.side_effect = KimiVisionError(
                "API timeout"
            )

            # Mock Gemini to succeed
            mock_response = MagicMock()
            mock_response.text = '{"frame_analyses": [{"frame_index": 0, "content_type": "interview", "is_original_content": true, "is_third_party": false, "confidence": "high", "text_detected": "", "notable_elements": []}], "overall_content_mix": "interview", "third_party_ratio": 0.0}'

            with patch(
                "backend.integrations.gemini_client.GeminiClient"
            ) as MockGemini:
                gemini_instance = MockGemini.return_value
                gemini_instance._client.models.generate_content.return_value = mock_response
                gemini_instance._estimate_cost.return_value = 0.002

                # Mock google.genai.types for Gemini fallback
                mock_types = MagicMock()
                mock_part = MagicMock()
                mock_types.Part.from_bytes.return_value = mock_part
                mock_types.GenerateContentConfig.return_value = MagicMock()

                with patch.dict("sys.modules", {"google.genai": MagicMock(types=mock_types), "google": MagicMock()}):
                    with patch("google.genai.types", mock_types):
                        # Mock file reads
                        with patch("builtins.open", create=True) as mock_open:
                            mock_file = MagicMock()
                            mock_file.__enter__ = lambda s: s
                            mock_file.__exit__ = MagicMock(return_value=False)
                            mock_file.read.return_value = b"fake-jpeg"
                            mock_open.return_value = mock_file

                            result_dict, cost, warnings, provider = _analyze_frames_with_fallback(
                                frame_paths=[Path("/tmp/f1.jpg")],
                                video_title="Test Video",
                                research_topic="testing",
                                source_id="SRC_1",
                                interval_seconds=10,
                                kimi_api_key="test-key",
                            )

                            assert provider == "gemini"
                            assert result_dict is not None
                            assert any("Kimi failed" in w for w in warnings)

    def test_no_kimi_key_uses_gemini_directly(self):
        """When kimi_api_key is None, uses Gemini without attempting Kimi."""
        from backend.pipeline.stages.semantic_extraction import (
            _analyze_frames_with_fallback,
        )

        mock_response = MagicMock()
        mock_response.text = '{"frame_analyses": [], "overall_content_mix": "empty", "third_party_ratio": 0.0}'

        with patch(
            "backend.integrations.gemini_client.GeminiClient"
        ) as MockGemini:
            gemini_instance = MockGemini.return_value
            gemini_instance._client.models.generate_content.return_value = mock_response
            gemini_instance._estimate_cost.return_value = 0.001

            mock_types = MagicMock()
            mock_types.Part.from_bytes.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()

            with patch.dict("sys.modules", {"google.genai": MagicMock(types=mock_types), "google": MagicMock()}):
                with patch("google.genai.types", mock_types):
                    with patch("builtins.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__ = lambda s: s
                        mock_file.__exit__ = MagicMock(return_value=False)
                        mock_file.read.return_value = b"fake-jpeg"
                        mock_open.return_value = mock_file

                        result_dict, cost, warnings, provider = _analyze_frames_with_fallback(
                            frame_paths=[Path("/tmp/f1.jpg")],
                            video_title="Test Video",
                            research_topic="testing",
                            source_id="SRC_1",
                            interval_seconds=10,
                            kimi_api_key=None,
                        )

                        assert provider == "gemini"
                        assert any("not configured" in w for w in warnings)

    def test_both_fail_returns_none(self):
        """When both Kimi and Gemini fail, returns None without raising."""
        from backend.pipeline.stages.semantic_extraction import (
            _analyze_frames_with_fallback,
        )
        from backend.integrations.kimi_vision_client import KimiVisionError

        with patch(
            "backend.integrations.kimi_vision_client.KimiVisionClient"
        ) as MockKimi:
            MockKimi.return_value.analyze_video_frames.side_effect = KimiVisionError(
                "Kimi down"
            )

            with patch(
                "backend.integrations.gemini_client.GeminiClient"
            ) as MockGemini:
                MockGemini.side_effect = Exception("Gemini init failed")

                result_dict, cost, warnings, provider = _analyze_frames_with_fallback(
                    frame_paths=[Path("/tmp/f1.jpg")],
                    video_title="Test Video",
                    research_topic="testing",
                    source_id="SRC_1",
                    interval_seconds=10,
                    kimi_api_key="test-key",
                )

                assert provider == "none"
                assert result_dict is None
                assert cost == 0.0
                assert len(warnings) > 0


# ---------------------------------------------------------------------------
# _run_visual_frame_analysis tests
# ---------------------------------------------------------------------------

class TestRunVisualFrameAnalysis:
    """Tests for _run_visual_frame_analysis()."""

    def test_populates_visual_analysis(
        self, mock_settings_with_kimi, mock_frame_result, kimi_visual_dict, base_extraction
    ):
        """With all mocks, visual_analysis is populated on extraction."""
        from backend.pipeline.stages.semantic_extraction import (
            _run_visual_frame_analysis,
        )

        with patch("backend.config.get_settings", return_value=mock_settings_with_kimi):
            with patch(
                "backend.pipeline.stages.semantic_extraction._download_video_for_frames",
                return_value="/tmp/test_video.mp4",
            ):
                with patch(
                    "backend.services.frame_extraction.extract_keyframes",
                    return_value=mock_frame_result,
                ):
                    with patch(
                        "backend.pipeline.stages.semantic_extraction._analyze_frames_with_fallback",
                        return_value=(kimi_visual_dict, 0.005, [], "kimi"),
                    ):
                        with patch("os.path.exists", return_value=True):
                            with patch("os.remove"):
                                with patch("os.rmdir"):
                                    with patch("os.listdir", return_value=[]):
                                        warnings, cost = _run_visual_frame_analysis(
                                            source_id="SRC_1",
                                            video_url="https://www.youtube.com/watch?v=test123test",
                                            extraction=base_extraction,
                                            video_title="Test Video",
                                        )

                                        assert base_extraction.visual_analysis is not None
                                        assert base_extraction.visual_analysis["source_id"] == "SRC_1"
                                        assert cost == 0.005
                                        assert len(warnings) == 0

    def test_failure_is_non_fatal(self, mock_settings_with_kimi, base_extraction):
        """When everything fails, returns warnings but doesn't raise."""
        from backend.pipeline.stages.semantic_extraction import (
            _run_visual_frame_analysis,
        )

        with patch("backend.config.get_settings", return_value=mock_settings_with_kimi):
            with patch(
                "backend.pipeline.stages.semantic_extraction._download_video_for_frames",
                side_effect=RuntimeError("yt-dlp not found"),
            ):
                warnings, cost = _run_visual_frame_analysis(
                    source_id="SRC_1",
                    video_url="https://www.youtube.com/watch?v=test123test",
                    extraction=base_extraction,
                )

                assert base_extraction.visual_analysis is None
                assert cost == 0.0
                assert len(warnings) > 0
                assert any("skipped" in w.lower() or "failed" in w.lower() for w in warnings)

    def test_cleanup_on_failure(
        self, mock_settings_with_kimi, mock_frame_result, base_extraction
    ):
        """Temp files are cleaned up even when analysis fails."""
        from backend.pipeline.stages.semantic_extraction import (
            _run_visual_frame_analysis,
        )

        with patch("backend.config.get_settings", return_value=mock_settings_with_kimi):
            with patch(
                "backend.pipeline.stages.semantic_extraction._download_video_for_frames",
                return_value="/tmp/test_video.mp4",
            ):
                with patch(
                    "backend.services.frame_extraction.extract_keyframes",
                    return_value=mock_frame_result,
                ):
                    with patch(
                        "backend.pipeline.stages.semantic_extraction._analyze_frames_with_fallback",
                        side_effect=Exception("Unexpected error"),
                    ):
                        with patch("os.path.exists", return_value=True):
                            with patch("os.remove") as mock_remove:
                                with patch("os.rmdir"):
                                    with patch("os.listdir", return_value=[]):
                                        warnings, cost = _run_visual_frame_analysis(
                                            source_id="SRC_1",
                                            video_url="https://www.youtube.com/watch?v=test123test",
                                            extraction=base_extraction,
                                        )

                                        # Frame cleanup was called
                                        mock_frame_result.cleanup.assert_called_once()
                                        # Video file removal was attempted
                                        mock_remove.assert_called()

    def test_no_frames_extracted(
        self, mock_settings_with_kimi, base_extraction
    ):
        """When no frames are extracted, returns warning without calling analyzer."""
        from backend.pipeline.stages.semantic_extraction import (
            _run_visual_frame_analysis,
        )

        empty_frame_result = MagicMock()
        empty_frame_result.frames = []
        empty_frame_result.frame_count = 0

        with patch("backend.config.get_settings", return_value=mock_settings_with_kimi):
            with patch(
                "backend.pipeline.stages.semantic_extraction._download_video_for_frames",
                return_value="/tmp/test_video.mp4",
            ):
                with patch(
                    "backend.services.frame_extraction.extract_keyframes",
                    return_value=empty_frame_result,
                ):
                    with patch(
                        "backend.pipeline.stages.semantic_extraction._analyze_frames_with_fallback",
                    ) as mock_analyze:
                        with patch("os.path.exists", return_value=True):
                            with patch("os.remove"):
                                with patch("os.rmdir"):
                                    with patch("os.listdir", return_value=[]):
                                        warnings, cost = _run_visual_frame_analysis(
                                            source_id="SRC_1",
                                            video_url="https://www.youtube.com/watch?v=test123test",
                                            extraction=base_extraction,
                                        )

                                        assert any("No frames" in w for w in warnings)
                                        mock_analyze.assert_not_called()


# ---------------------------------------------------------------------------
# extract_video_observations integration tests
# ---------------------------------------------------------------------------

class TestExtractVideoObservationsWithVisual:
    """Integration tests for visual analysis within extract_video_observations()."""

    def test_visual_failure_still_returns_observations(self):
        """When visual analysis fails, Gemini observations still returned."""
        from backend.pipeline.stages.semantic_extraction import (
            extract_video_observations,
        )

        mock_video_result = {
            "clips": [
                {
                    "quote": "This is what happened",
                    "speaker": "Reporter",
                    "timestamp_start": "01:00",
                    "timestamp_end": "01:30",
                }
            ],
            "video_info": {"title": "Test Video"},
            "cost": 0.01,
        }

        with patch(
            "backend.integrations.gemini_client.GeminiClient"
        ) as MockGemini:
            instance = MockGemini.return_value
            instance.analyze_youtube_video.return_value = mock_video_result

            with patch(
                "backend.pipeline.stages.semantic_extraction._run_visual_frame_analysis",
                return_value=(["Visual analysis skipped: test"], 0.0),
            ):
                extraction, cost, warnings = extract_video_observations(
                    video_url="https://www.youtube.com/watch?v=test123test",
                    source_id="SRC_1",
                )

                # Gemini observations are still present
                assert len(extraction.approximate_observations) > 0
                assert extraction.analysis_mode == AnalysisMode.VIDEO_ONLY
                # Visual analysis warnings included
                assert any("Visual analysis" in w for w in warnings)

    def test_visual_analysis_cost_summed(self):
        """Visual analysis cost is added to Gemini video cost."""
        from backend.pipeline.stages.semantic_extraction import (
            extract_video_observations,
        )

        mock_video_result = {
            "clips": [
                {
                    "quote": "Statement",
                    "speaker": "Speaker",
                    "timestamp_start": "00:00",
                    "timestamp_end": "00:10",
                }
            ],
            "video_info": {"title": "Test"},
            "cost": 0.01,
        }

        with patch(
            "backend.integrations.gemini_client.GeminiClient"
        ) as MockGemini:
            instance = MockGemini.return_value
            instance.analyze_youtube_video.return_value = mock_video_result

            with patch(
                "backend.pipeline.stages.semantic_extraction._run_visual_frame_analysis",
                return_value=([], 0.005),
            ):
                extraction, cost, warnings = extract_video_observations(
                    video_url="https://www.youtube.com/watch?v=test123test",
                    source_id="SRC_1",
                )

                # Cost should be Gemini (0.01) + visual (0.005)
                assert cost == pytest.approx(0.015, abs=0.001)


# ---------------------------------------------------------------------------
# _download_video_for_frames tests
# ---------------------------------------------------------------------------

class TestDownloadVideoForFrames:
    """Tests for _download_video_for_frames()."""

    def test_invalid_url_raises(self):
        """Non-YouTube URL raises RuntimeError."""
        from backend.pipeline.stages.semantic_extraction import (
            _download_video_for_frames,
        )

        with pytest.raises(RuntimeError, match="Cannot extract video ID"):
            _download_video_for_frames(
                video_url="https://example.com/not-youtube",
                source_id="SRC_1",
            )

    def test_successful_download(self):
        """Successful yt-dlp download returns path."""
        from backend.pipeline.stages.semantic_extraction import (
            _download_video_for_frames,
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("tempfile.mkdtemp", return_value="/tmp/ra_video_test"):
                path = _download_video_for_frames(
                    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    source_id="SRC_1",
                )

                assert "dQw4w9WgXcQ" in path
                assert path.endswith(".mp4")

    def test_ytdlp_failure_raises(self):
        """yt-dlp failure raises RuntimeError."""
        from backend.pipeline.stages.semantic_extraction import (
            _download_video_for_frames,
        )

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: Video unavailable"

        with patch("subprocess.run", return_value=mock_result):
            with patch("tempfile.mkdtemp", return_value="/tmp/ra_video_test"):
                with pytest.raises(RuntimeError, match="yt-dlp failed"):
                    _download_video_for_frames(
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        source_id="SRC_1",
                    )
