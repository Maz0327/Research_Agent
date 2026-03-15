"""Tests for inline edit stage — section splicing logic."""
import pytest

from backend.pipeline.stages.inline_edit_stage import (
    _find_sections_key,
    _build_inline_edit_prompt,
)


class TestFindSectionsKey:
    def test_finds_sections(self):
        doc = {"sections": [{"section_id": "SECT_1"}], "title": "Test"}
        assert _find_sections_key(doc) == "sections"

    def test_finds_platforms(self):
        doc = {"platforms": [{"platform": "twitter"}], "topic": "Test"}
        assert _find_sections_key(doc) == "platforms"

    def test_returns_none_for_no_sections(self):
        doc = {"title": "Test", "body": "content"}
        assert _find_sections_key(doc) is None

    def test_ignores_non_list_keys(self):
        doc = {"sections": "not a list", "platforms": [{"id": 1}]}
        assert _find_sections_key(doc) == "platforms"


class TestBuildInlineEditPrompt:
    def test_builds_prompt_with_context(self):
        document = {
            "document_type": "blog_post",
            "topic": "AI Ethics",
            "title": "Ethics in AI",
        }
        section = {
            "section_id": "SECT_2",
            "heading": "Key Concerns",
            "body": "There are many concerns.",
            "claim_ids": ["CLM_1"],
            "source_ids": ["SRC_1"],
        }

        prompt = _build_inline_edit_prompt(
            document=document,
            section=section,
            section_id="SECT_2",
            edit_instruction="expand with more examples",
        )

        assert "SECT_2" in prompt
        assert "expand with more examples" in prompt
        assert "blog_post" in prompt
        assert "AI Ethics" in prompt

    def test_preserves_section_id_in_instruction(self):
        prompt = _build_inline_edit_prompt(
            document={"document_type": "script", "topic": "Test"},
            section={"section_id": "SCRIPT_SEC_3", "spoken_text": "Hello"},
            section_id="SCRIPT_SEC_3",
            edit_instruction="shorten",
        )
        assert 'SCRIPT_SEC_3' in prompt
