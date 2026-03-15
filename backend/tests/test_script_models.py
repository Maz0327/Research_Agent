"""Tests for Script (Doc 5) models."""
import pytest

from backend.models.script_models import (
    ScriptDocument,
    ScriptSection,
    ScriptHook,
    ScriptOutro,
    GenerateScriptRequest,
)


def _make_section(section_id: str, beat_label: str = "Setup") -> dict:
    return {
        "section_id": section_id,
        "beat_label": beat_label,
        "spoken_text": "This is the spoken text for this section of the video script.",
        "stage_direction": "B-roll of city skyline",
        "duration_estimate": "~90 seconds",
        "claim_ids": ["CLM_1"],
        "source_ids": ["SRC_1"],
    }


def _make_script(**overrides) -> dict:
    base = {
        "document_type": "script",
        "job_id": "test-job-123",
        "generated_at": "2026-03-15T00:00:00Z",
        "topic": "Test Topic",
        "source_count": 3,
        "tone": "conversational",
        "target_length": "medium",
        "story_arc": "discovery",
        "title": "The Story of Test Topic",
        "hook": {
            "text": "Did you know that this surprising fact exists?",
            "hook_type": "question",
            "claim_id": "CLM_1",
            "source_id": "SRC_1",
        },
        "sections": [
            _make_section("SCRIPT_SEC_1", "Setup"),
            _make_section("SCRIPT_SEC_2", "Development"),
            _make_section("SCRIPT_SEC_3", "Payoff"),
        ],
        "outro": {
            "text": "And that's the story. Thanks for watching.",
            "call_to_action": "Subscribe for more.",
        },
        "total_word_count": 1500,
        "estimated_duration": "8 minutes",
        "description_sources": [
            {"source_id": "SRC_1", "title": "Source One", "url": "https://example.com"},
        ],
        "guardrails": {
            "no_new_facts_ack": True,
            "all_facts_reference_doc2": True,
            "all_facts_reference_doc0": True,
        },
    }
    base.update(overrides)
    return base


class TestScriptDocument:
    def test_valid_script(self):
        doc = ScriptDocument(**_make_script())
        assert doc.document_type == "script"
        assert doc.tone == "conversational"
        assert len(doc.sections) == 3

    def test_sequential_section_ids(self):
        data = _make_script(sections=[
            _make_section("SCRIPT_SEC_1"),
            _make_section("SCRIPT_SEC_3"),
            _make_section("SCRIPT_SEC_4"),
        ])
        with pytest.raises(ValueError, match="sequential IDs"):
            ScriptDocument(**data)

    def test_minimum_sections(self):
        data = _make_script(sections=[
            _make_section("SCRIPT_SEC_1"),
            _make_section("SCRIPT_SEC_2"),
        ])
        with pytest.raises(ValueError):
            ScriptDocument(**data)

    def test_tone_validation(self):
        data = _make_script(tone="invalid_tone")
        with pytest.raises(ValueError):
            ScriptDocument(**data)

    def test_all_claim_ids(self):
        doc = ScriptDocument(**_make_script())
        # Hook claim_id + 3 sections each with CLM_1
        assert "CLM_1" in doc.all_claim_ids()

    def test_all_source_ids(self):
        doc = ScriptDocument(**_make_script())
        assert "SRC_1" in doc.all_source_ids()


class TestGenerateScriptRequest:
    def test_defaults(self):
        req = GenerateScriptRequest()
        assert req.tone == "conversational"
        assert req.target_length == "medium"
        assert req.voice_profile_id is None

    def test_custom_params(self):
        req = GenerateScriptRequest(tone="energetic", target_length="short")
        assert req.tone == "energetic"
        assert req.target_length == "short"
