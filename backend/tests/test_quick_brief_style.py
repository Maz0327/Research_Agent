"""Tests for style enforcement in quick_brief_stage."""

import pytest
from unittest.mock import patch

from backend.pipeline.stages.quick_brief_stage import _check_brief_style


class TestCheckBriefStyle:
    """Tests for _check_brief_style helper."""

    def test_clean_brief_no_warnings(self):
        """Brief with clean style produces no warnings."""
        result = {
            "setup": {"text": "AI is changing fast. Three things matter most."},
            "hook_options": [
                {"hook_id": "HOOK_A", "text": "Nobody saw this coming."},
            ],
            "core_facts": [
                {
                    "fact_id": "FACT_1",
                    "statement": "GPT-4 scored 90th percentile on the bar exam.",
                    "say_it_like": "It passed the bar. Most law students don't.",
                },
            ],
        }
        warnings = _check_brief_style(result)
        assert warnings == []

    def test_banned_phrase_detected(self):
        """Banned phrases in brief text should produce warnings."""
        result = {
            "setup": {
                "text": "Furthermore, the data suggests that this paradigm shift "
                "is consequently leading to significant changes in the industry "
                "that are worth noting for content creators today."
            },
            "hook_options": [],
            "core_facts": [],
        }
        warnings = _check_brief_style(result)
        assert len(warnings) > 0
        assert any("[setup]" in w for w in warnings)

    def test_long_sentence_detected(self):
        """Sentences over 35 words should be flagged."""
        long_sentence = " ".join(["word"] * 40) + "."
        result = {
            "setup": {"text": long_sentence},
            "hook_options": [],
            "core_facts": [],
        }
        warnings = _check_brief_style(result)
        assert len(warnings) > 0
        assert any("sentence" in w.lower() for w in warnings)

    def test_empty_brief_no_crash(self):
        """Empty or minimal brief should not crash."""
        assert _check_brief_style({}) == []
        assert _check_brief_style({"setup": {}}) == []
        assert _check_brief_style({"setup": {"text": ""}}) == []

    def test_violations_tagged_with_field_name(self):
        """Each violation should be tagged with the field it came from."""
        result = {
            "setup": {"text": "Short."},
            "hook_options": [],
            "core_facts": [
                {
                    "fact_id": "FACT_1",
                    "statement": "Furthermore, additionally, moreover, consequently, "
                    "it could be argued that this paradigm represents a significant "
                    "shift in the way we understand the corpus of knowledge available.",
                    "say_it_like": "Clean text here.",
                },
            ],
        }
        warnings = _check_brief_style(result)
        assert any("[FACT_1]" in w for w in warnings)
