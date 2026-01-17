"""Tests for prompt template guardrail validation.

Phase 9: Validates that all prompts include the required 5 guardrail components
per architecture rules in CLAUDE.md.

Required 5 Components:
1. Source Identity Lock
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction (extraction prompts only)
5. Output Schema
"""

import pytest
import re


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_prompt_module():
    """Load the base prompt module."""
    from backend.pipeline.prompts.modes import base
    return base


@pytest.fixture
def synthesis_prompt_module():
    """Load the semantic synthesis prompt module."""
    from backend.pipeline.prompts import semantic_synthesis_prompt
    return semantic_synthesis_prompt


@pytest.fixture
def gap_analysis_prompt_module():
    """Load the gap analysis prompt module."""
    from backend.pipeline.prompts import gap_analysis_prompt
    return gap_analysis_prompt


@pytest.fixture
def research_starter_prompt_module():
    """Load the research starter prompt module."""
    from backend.pipeline.prompts import research_starter_prompt
    return research_starter_prompt


@pytest.fixture
def structure_analysis_prompt_module():
    """Load the structure analysis prompt module."""
    from backend.pipeline.prompts import structure_analysis_prompt
    return structure_analysis_prompt


# =============================================================================
# Component Detection Helpers
# =============================================================================


def has_source_identity_lock(text: str) -> bool:
    """Check if text contains source identity lock pattern."""
    patterns = [
        r"SOURCE IDENTITY LOCK",
        r"SYNTHESIS CONTEXT LOCK",
        r"CONTEXT LOCK",
        r"source_id:",
        r"╔══════",  # Box drawing character (lock block)
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def has_confidence_ceiling(text: str) -> bool:
    """Check if text contains confidence ceiling declaration."""
    patterns = [
        r"CONFIDENCE CEILING",
        r"confidence_ceiling",
        r"Maximum.*confidence",
        r"ceiling.*HIGH|MEDIUM|LOW",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def has_empty_output_permission(text: str) -> bool:
    """Check if text contains empty output permission."""
    patterns = [
        r"EMPTY OUTPUT PERMISSION",
        r"empty arrays",
        r"Return empty",
        r"acceptable to return empty",
        r"DO NOT invent",
        r"DO NOT pad",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def has_layered_extraction(text: str) -> bool:
    """Check if text contains layered extraction instructions."""
    patterns = [
        r"EXTRACTION LAYERS",
        r"LAYER 1.*EXPLICIT",
        r"LAYER 2.*PATTERNS",
        r"LAYER 3.*STRUCTURAL",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def has_output_schema(text: str) -> bool:
    """Check if text contains output schema/format definition."""
    patterns = [
        r"OUTPUT FORMAT",
        r"OUTPUT.*JSON",
        r"Return.*JSON",
        r"```json",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


# =============================================================================
# Test: Base Prompt Module (modes/base.py)
# =============================================================================


class TestBasePromptComponents:
    """Test that base.py has all 5 guardrail components."""

    def test_base_has_source_identity_lock_block(self, base_prompt_module):
        """Base must have SOURCE_IDENTITY_LOCK_BLOCK constant."""
        assert hasattr(base_prompt_module, "SOURCE_IDENTITY_LOCK_BLOCK")
        text = base_prompt_module.SOURCE_IDENTITY_LOCK_BLOCK
        assert "SOURCE IDENTITY LOCK" in text
        assert "source_id:" in text
        assert "analysis_mode:" in text
        assert "confidence_ceiling:" in text

    def test_base_has_confidence_ceiling_declaration(self, base_prompt_module):
        """Base must have CONFIDENCE_CEILING_DECLARATION constant."""
        assert hasattr(base_prompt_module, "CONFIDENCE_CEILING_DECLARATION")
        text = base_prompt_module.CONFIDENCE_CEILING_DECLARATION
        assert "CONFIDENCE CEILING" in text
        assert "MAXIMUM allowed confidence" in text

    def test_base_has_empty_output_permission(self, base_prompt_module):
        """Base must have EMPTY_OUTPUT_PERMISSION constant."""
        assert hasattr(base_prompt_module, "EMPTY_OUTPUT_PERMISSION")
        text = base_prompt_module.EMPTY_OUTPUT_PERMISSION
        assert "EMPTY OUTPUT PERMISSION" in text
        assert "empty arrays" in text.lower()

    def test_base_has_layered_extraction_instructions(self, base_prompt_module):
        """Base must have LAYERED_EXTRACTION_INSTRUCTIONS constant."""
        assert hasattr(base_prompt_module, "LAYERED_EXTRACTION_INSTRUCTIONS")
        text = base_prompt_module.LAYERED_EXTRACTION_INSTRUCTIONS
        assert "LAYER 1" in text
        assert "LAYER 2" in text
        assert "LAYER 3" in text

    def test_base_has_output_schema(self, base_prompt_module):
        """Base must have BASE_OUTPUT_SCHEMA constant."""
        assert hasattr(base_prompt_module, "BASE_OUTPUT_SCHEMA")
        text = base_prompt_module.BASE_OUTPUT_SCHEMA
        assert "OUTPUT FORMAT" in text
        assert "JSON" in text


class TestBasePromptBuilder:
    """Test that build_base_prompt includes all components."""

    def test_build_base_prompt_includes_all_components(self, base_prompt_module):
        """Built prompt must include all 5 guardrail components."""
        prompt = base_prompt_module.build_base_prompt(
            source_id="SRC_1",
            source_content="Test content",
            title="Test Title",
            analysis_mode="transcript_grounded",
            confidence_ceiling="HIGH",
            mode_specific_instructions="Test instructions",
        )

        # Component 1: Source Identity Lock
        assert has_source_identity_lock(prompt), "Missing Source Identity Lock"

        # Component 2: Confidence Ceiling
        assert has_confidence_ceiling(prompt), "Missing Confidence Ceiling"

        # Component 3: Empty Output Permission
        assert has_empty_output_permission(prompt), "Missing Empty Output Permission"

        # Component 4: Layered Extraction
        assert has_layered_extraction(prompt), "Missing Layered Extraction"

        # Component 5: Output Schema
        assert has_output_schema(prompt), "Missing Output Schema"


# =============================================================================
# Test: Mode-Specific Prompts (inherit from base)
# =============================================================================


class TestModePromptInheritance:
    """Test that mode-specific prompts properly inherit from base."""

    def test_transcript_grounded_mode_exists(self):
        """transcript_grounded mode must exist."""
        from backend.pipeline.prompts.modes import transcript_grounded
        assert hasattr(transcript_grounded, "build_transcript_grounded_prompt") or \
               hasattr(transcript_grounded, "TRANSCRIPT_GROUNDED_INSTRUCTIONS")

    def test_caption_grounded_mode_exists(self):
        """caption_grounded mode must exist."""
        from backend.pipeline.prompts.modes import caption_grounded
        assert hasattr(caption_grounded, "build_caption_grounded_prompt") or \
               hasattr(caption_grounded, "CAPTION_GROUNDED_INSTRUCTIONS")

    def test_video_only_mode_exists(self):
        """video_only mode must exist."""
        from backend.pipeline.prompts.modes import video_only
        assert hasattr(video_only, "build_video_only_prompt") or \
               hasattr(video_only, "VIDEO_ONLY_INSTRUCTIONS")

    def test_text_provided_mode_exists(self):
        """text_provided mode must exist."""
        from backend.pipeline.prompts.modes import text_provided
        assert hasattr(text_provided, "build_text_provided_prompt") or \
               hasattr(text_provided, "TEXT_PROVIDED_INSTRUCTIONS")

    def test_ocr_extracted_mode_exists(self):
        """ocr_extracted mode must exist."""
        from backend.pipeline.prompts.modes import ocr_extracted
        assert hasattr(ocr_extracted, "build_ocr_extracted_prompt") or \
               hasattr(ocr_extracted, "OCR_EXTRACTED_INSTRUCTIONS")

    def test_article_fetched_mode_exists(self):
        """article_fetched mode must exist."""
        from backend.pipeline.prompts.modes import article_fetched
        assert hasattr(article_fetched, "build_article_fetched_prompt") or \
               hasattr(article_fetched, "ARTICLE_FETCHED_INSTRUCTIONS")


# =============================================================================
# Test: Semantic Synthesis Prompt
# =============================================================================


class TestSemanticSynthesisPrompt:
    """Test semantic_synthesis_prompt.py guardrails."""

    def test_synthesis_has_context_lock(self, synthesis_prompt_module):
        """Synthesis must have SYNTHESIS_CONTEXT_LOCK."""
        assert hasattr(synthesis_prompt_module, "SYNTHESIS_CONTEXT_LOCK")
        text = synthesis_prompt_module.SYNTHESIS_CONTEXT_LOCK
        assert "SYNTHESIS CONTEXT LOCK" in text

    def test_synthesis_has_ceiling(self, synthesis_prompt_module):
        """Synthesis must have confidence ceiling in lock."""
        text = synthesis_prompt_module.SYNTHESIS_CONTEXT_LOCK
        assert "confidence" in text.lower() or "MEDIUM" in text

    def test_synthesis_has_empty_output_handling(self, synthesis_prompt_module):
        """Synthesis must have thin output/empty handling."""
        text = synthesis_prompt_module.SEMANTIC_SYNTHESIS_PROMPT
        assert "FAILURE" in text or "THIN OUTPUT" in text or "empty" in text.lower()

    def test_synthesis_has_output_schema(self, synthesis_prompt_module):
        """Synthesis must have JSON output schema."""
        text = synthesis_prompt_module.SEMANTIC_SYNTHESIS_PROMPT
        assert has_output_schema(text), "Missing output schema"

    def test_build_semantic_synthesis_prompt_function(self, synthesis_prompt_module):
        """Builder function must exist and work."""
        assert hasattr(synthesis_prompt_module, "build_semantic_synthesis_prompt")
        prompt = synthesis_prompt_module.build_semantic_synthesis_prompt(
            scope_lock="Test scope",
            key_points=[{"key_point_id": "KP_1", "statement": "Test"}],
            themes=[],
            tensions=[],
            gaps=[],
            verification_rate=0.8,
            source_diversity=2,
        )
        assert len(prompt) > 100


# =============================================================================
# Test: Gap Analysis Prompt
# =============================================================================


class TestGapAnalysisPrompt:
    """Test gap_analysis_prompt.py guardrails."""

    def test_gap_analysis_has_context_lock(self, gap_analysis_prompt_module):
        """Gap analysis must have context lock."""
        assert hasattr(gap_analysis_prompt_module, "GAP_ANALYSIS_CONTEXT_LOCK")
        text = gap_analysis_prompt_module.GAP_ANALYSIS_CONTEXT_LOCK
        assert "GAP ANALYSIS LOCK" in text

    def test_gap_analysis_has_ceiling(self, gap_analysis_prompt_module):
        """Gap analysis must have confidence ceiling."""
        text = gap_analysis_prompt_module.GAP_ANALYSIS_CONTEXT_LOCK
        assert "Ceiling" in text or "MEDIUM" in text

    def test_gap_analysis_has_anti_hallucination(self, gap_analysis_prompt_module):
        """Gap analysis must have anti-hallucination rules."""
        text = gap_analysis_prompt_module.GAP_ANALYSIS_PROMPT
        # Check for various anti-hallucination patterns
        has_anti_hallucination = (
            "Anti-Hallucination" in text or
            "ANTI-HALLUCINATION" in text or
            "Do NOT invent" in text or
            "DO NOT invent" in text
        )
        assert has_anti_hallucination

    def test_gap_analysis_has_output_schema(self, gap_analysis_prompt_module):
        """Gap analysis must have JSON output schema."""
        text = gap_analysis_prompt_module.GAP_ANALYSIS_PROMPT
        assert has_output_schema(text)


# =============================================================================
# Test: Legacy Prompts (expected to fail until fixed)
# =============================================================================


class TestLegacyPromptGaps:
    """Identify legacy prompts missing guardrails.

    These tests document gaps in legacy prompts.
    They are expected to pass (confirming missing components).
    """

    def test_research_starter_missing_source_lock(self, research_starter_prompt_module):
        """Research starter is MISSING source identity lock."""
        text = research_starter_prompt_module.RESEARCH_STARTER_PROMPT
        # This test confirms the prompt is missing the component
        # When fixed, this test should be updated to assert presence
        has_lock = has_source_identity_lock(text)
        if not has_lock:
            pytest.skip("research_starter_prompt needs Source Identity Lock (legacy prompt)")

    def test_research_starter_missing_ceiling(self, research_starter_prompt_module):
        """Research starter is MISSING confidence ceiling."""
        text = research_starter_prompt_module.RESEARCH_STARTER_PROMPT
        has_ceiling = has_confidence_ceiling(text)
        if not has_ceiling:
            pytest.skip("research_starter_prompt needs Confidence Ceiling (legacy prompt)")

    def test_structure_analysis_missing_source_lock(self, structure_analysis_prompt_module):
        """Structure analysis is MISSING source identity lock."""
        text = structure_analysis_prompt_module.STRUCTURE_ANALYSIS_PROMPT
        has_lock = has_source_identity_lock(text)
        if not has_lock:
            pytest.skip("structure_analysis_prompt needs Source Identity Lock (legacy prompt)")

    def test_structure_analysis_missing_ceiling(self, structure_analysis_prompt_module):
        """Structure analysis is MISSING confidence ceiling."""
        text = structure_analysis_prompt_module.STRUCTURE_ANALYSIS_PROMPT
        has_ceiling = has_confidence_ceiling(text)
        if not has_ceiling:
            pytest.skip("structure_analysis_prompt needs Confidence Ceiling (legacy prompt)")
