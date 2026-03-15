"""Tests for Voice Profile models."""
import pytest

from backend.models.voice_profile import (
    VoiceProfile,
    SentenceRhythm,
    TransitionPattern,
    EmphasisPatterns,
    CreateVoiceProfileRequest,
)


class TestVoiceProfile:
    def test_valid_profile(self):
        profile = VoiceProfile(
            id="test-id",
            user_id="user-id",
            creator_name="Test Creator",
        )
        assert profile.creator_name == "Test Creator"
        assert profile.source_video_count == 0

    def test_to_voice_instructions(self):
        profile = VoiceProfile(
            id="test-id",
            user_id="user-id",
            creator_name="John Smith",
            sentence_rhythm=SentenceRhythm(
                avg_sentence_length=15,
                length_variation="highly_varied",
                fragment_frequency="frequent",
            ),
            transition_patterns=[
                TransitionPattern(
                    from_context="evidence to opinion",
                    phrase="But here's the thing...",
                    frequency="common",
                ),
            ],
            opening_patterns=["Starts with a provocative question"],
            closing_patterns=["Ends with a call to action"],
            emphasis_patterns=EmphasisPatterns(
                repetition_style="Triple repetition",
                rhetorical_questions=True,
                pause_markers=["...", "right?"],
            ),
        )
        instructions = profile.to_voice_instructions()
        assert "John Smith" in instructions
        assert "15 words" in instructions
        assert "But here's the thing..." in instructions
        assert "Rhetorical questions: Yes" in instructions
        assert "right?" in instructions

    def test_empty_profile_instructions(self):
        profile = VoiceProfile(
            id="test-id",
            user_id="user-id",
            creator_name="Minimal Creator",
        )
        instructions = profile.to_voice_instructions()
        assert "Minimal Creator" in instructions
        assert "SENTENCE RHYTHM" in instructions


class TestSentenceRhythm:
    def test_defaults(self):
        rhythm = SentenceRhythm(avg_sentence_length=12)
        assert rhythm.length_variation == "varied"
        assert rhythm.fragment_frequency == "occasional"

    def test_validation(self):
        with pytest.raises(ValueError):
            SentenceRhythm(avg_sentence_length=0)


class TestCreateVoiceProfileRequest:
    def test_valid_request(self):
        req = CreateVoiceProfileRequest(
            creator_name="Creator",
            video_urls=["https://youtube.com/watch?v=test"],
        )
        assert len(req.video_urls) == 1

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            CreateVoiceProfileRequest(creator_name="", video_urls=["https://example.com"])

    def test_empty_urls_rejected(self):
        with pytest.raises(ValueError):
            CreateVoiceProfileRequest(creator_name="Creator", video_urls=[])
