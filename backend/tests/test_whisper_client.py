"""Tests for the Whisper transcription client's segment handling.

Regression cover for P3 work-order item A1: the OpenAI SDK returns
`TranscriptionSegment` objects for `verbose_json`, and the client used to call
`.get()` on them, which raised `AttributeError` on every transcription.
"""

from types import SimpleNamespace

from backend.integrations.whisper_client import WhisperTranscriptionClient


class TestNormalizeSegments:
    """`_normalize_segments` accepts SDK objects and dicts alike."""

    def test_sdk_objects_use_attribute_access(self):
        """SDK `TranscriptionSegment`-shaped objects normalize without .get()."""
        raw = [
            SimpleNamespace(start=0.0, end=2.5, text="Hello there", id=0),
            SimpleNamespace(start=2.5, end=4.0, text="second segment", id=1),
        ]

        segments = WhisperTranscriptionClient._normalize_segments(raw)

        assert segments == [
            {"start": 0.0, "end": 2.5, "text": "Hello there"},
            {"start": 2.5, "end": 4.0, "text": "second segment"},
        ]

    def test_dicts_still_work(self):
        """Cached or replayed dict payloads normalize the same way."""
        raw = [{"start": 1.0, "end": 3.0, "text": "from a dict"}]

        segments = WhisperTranscriptionClient._normalize_segments(raw)

        assert segments == [{"start": 1.0, "end": 3.0, "text": "from a dict"}]

    def test_missing_fields_fall_back_to_defaults(self):
        """A segment without timings still yields a usable dict."""
        raw = [SimpleNamespace(text="no timings"), {"text": "dict, no timings"}]

        segments = WhisperTranscriptionClient._normalize_segments(raw)

        assert segments == [
            {"start": 0, "end": 0, "text": "no timings"},
            {"start": 0, "end": 0, "text": "dict, no timings"},
        ]

    def test_none_fields_fall_back_to_defaults(self):
        """Explicit None values are replaced by the defaults, not passed through."""
        raw = [SimpleNamespace(start=None, end=None, text=None)]

        segments = WhisperTranscriptionClient._normalize_segments(raw)

        assert segments == [{"start": 0, "end": 0, "text": ""}]

    def test_empty_or_missing_segments(self):
        """No segments on the response is an empty list, never a crash."""
        assert WhisperTranscriptionClient._normalize_segments(None) == []
        assert WhisperTranscriptionClient._normalize_segments([]) == []


class TestTranscribeSegmentExtraction:
    """`transcribe()` survives a real-shaped SDK response."""

    def test_transcribe_with_sdk_segment_objects(self, tmp_path, monkeypatch):
        """The whole call path returns normalized segments for object responses."""
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake audio bytes")

        response = SimpleNamespace(
            text="Hello there second segment",
            segments=[
                SimpleNamespace(start=0.0, end=2.5, text="Hello there"),
                SimpleNamespace(start=2.5, end=4.0, text="second segment"),
            ],
        )

        class FakeTranscriptions:
            def create(self, **kwargs):
                return response

        client = WhisperTranscriptionClient.__new__(WhisperTranscriptionClient)
        client.api_key = "test-key"
        client.cost_per_minute = 0.006
        client.client = SimpleNamespace(audio=SimpleNamespace(transcriptions=FakeTranscriptions()))
        monkeypatch.setattr(WhisperTranscriptionClient, "_get_audio_duration", lambda self, path: 2.0)

        result = WhisperTranscriptionClient.transcribe(client, str(audio_file))

        assert result["text"] == "Hello there second segment"
        assert result["segments"] == [
            {"start": 0.0, "end": 2.5, "text": "Hello there"},
            {"start": 2.5, "end": 4.0, "text": "second segment"},
        ]
        assert result["method"] == "whisper"
        assert result["cost"] == 2.0 * 0.006
