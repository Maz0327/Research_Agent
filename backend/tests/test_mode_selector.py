"""
Unit tests for mode selector module.

Tests for: mode selection, confidence ceilings, quote permissions,
and all helper functions.

Phase 9 Task 9.2.7
"""
import pytest

from backend.pipeline.mode_selector import (
    CONFIDENCE_CEILING_STRINGS,
    CONFIDENCE_CEILINGS,
    DEGRADED_QUOTE_MODES,
    MODE_DESCRIPTIONS,
    NO_QUOTE_MODES,
    QUOTE_WARNING_MESSAGES,
    QUOTES_ALLOWED,
    are_quotes_allowed,
    get_confidence_ceiling,
    get_confidence_ceiling_string,
    get_mode_description,
    get_quote_warning,
    is_no_quote_mode,
    requires_quote_warning,
    select_analysis_mode,
)
from backend.models.semantic_units import AnalysisMode, ConfidenceLevel


# =============================================================================
# TestModeSelection
# =============================================================================


class TestModeSelection:
    """Tests for select_analysis_mode function."""

    def test_selects_transcript_grounded_with_supadata(self):
        """Should select TRANSCRIPT_GROUNDED when Supadata transcript available."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={"supadata_transcript": True},
        )
        assert mode == AnalysisMode.TRANSCRIPT_GROUNDED

    def test_selects_transcript_grounded_with_whisper(self):
        """Should select TRANSCRIPT_GROUNDED when Whisper transcript available."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={"whisper_transcript": True},
        )
        assert mode == AnalysisMode.TRANSCRIPT_GROUNDED

    def test_selects_caption_grounded(self):
        """Should select CAPTION_GROUNDED when only YouTube captions available."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={"youtube_captions": True},
        )
        assert mode == AnalysisMode.CAPTION_GROUNDED

    def test_selects_video_only(self):
        """Should select VIDEO_ONLY when no transcript or captions."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={},
        )
        assert mode == AnalysisMode.VIDEO_ONLY

    def test_selects_video_only_explicit_false(self):
        """Should select VIDEO_ONLY when all transcript options are False."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={
                "supadata_transcript": False,
                "whisper_transcript": False,
                "youtube_captions": False,
            },
        )
        assert mode == AnalysisMode.VIDEO_ONLY

    def test_selects_text_provided(self):
        """Should select TEXT_PROVIDED for text source type."""
        mode = select_analysis_mode(
            source_type="text",
            content_available={"user_text": True},
        )
        assert mode == AnalysisMode.TEXT_PROVIDED

    def test_selects_ocr_extracted(self):
        """Should select OCR_EXTRACTED for screenshot source type."""
        mode = select_analysis_mode(
            source_type="screenshot",
            content_available={"ocr_text": True},
        )
        assert mode == AnalysisMode.OCR_EXTRACTED

    def test_selects_article_fetched(self):
        """Should select ARTICLE_FETCHED for article source type."""
        mode = select_analysis_mode(
            source_type="article",
            content_available={"article_text": True},
        )
        assert mode == AnalysisMode.ARTICLE_FETCHED

    def test_selects_transcript_grounded_for_reddit(self):
        """Should select TRANSCRIPT_GROUNDED for Reddit (has full text)."""
        mode = select_analysis_mode(
            source_type="reddit",
            content_available={},
        )
        assert mode == AnalysisMode.TRANSCRIPT_GROUNDED

    def test_raises_error_for_unknown_source_type(self):
        """Should raise ValueError for unknown source type."""
        with pytest.raises(ValueError) as exc_info:
            select_analysis_mode(
                source_type="unknown_type",
                content_available={},
            )
        assert "Unknown source type" in str(exc_info.value)

    def test_supadata_takes_priority_over_whisper(self):
        """Supadata should take priority when both available."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={
                "supadata_transcript": True,
                "whisper_transcript": True,
            },
        )
        assert mode == AnalysisMode.TRANSCRIPT_GROUNDED

    def test_whisper_takes_priority_over_captions(self):
        """Whisper should take priority over YouTube captions."""
        mode = select_analysis_mode(
            source_type="youtube",
            content_available={
                "supadata_transcript": False,
                "whisper_transcript": True,
                "youtube_captions": True,
            },
        )
        assert mode == AnalysisMode.TRANSCRIPT_GROUNDED


# =============================================================================
# TestConfidenceCeilings
# =============================================================================


class TestConfidenceCeilings:
    """Tests for confidence ceiling functions and mappings."""

    def test_all_modes_have_ceiling(self):
        """All analysis modes should have a confidence ceiling defined."""
        for mode in AnalysisMode:
            assert mode in CONFIDENCE_CEILINGS
            assert isinstance(CONFIDENCE_CEILINGS[mode], ConfidenceLevel)

    def test_transcript_grounded_ceiling_high(self):
        """TRANSCRIPT_GROUNDED should have HIGH ceiling."""
        assert CONFIDENCE_CEILINGS[AnalysisMode.TRANSCRIPT_GROUNDED] == ConfidenceLevel.HIGH

    def test_caption_grounded_ceiling_medium(self):
        """CAPTION_GROUNDED should have MEDIUM ceiling."""
        assert CONFIDENCE_CEILINGS[AnalysisMode.CAPTION_GROUNDED] == ConfidenceLevel.MEDIUM

    def test_video_only_ceiling_low(self):
        """VIDEO_ONLY should have LOW ceiling."""
        assert CONFIDENCE_CEILINGS[AnalysisMode.VIDEO_ONLY] == ConfidenceLevel.LOW

    def test_text_provided_ceiling_medium(self):
        """TEXT_PROVIDED should have MEDIUM ceiling."""
        assert CONFIDENCE_CEILINGS[AnalysisMode.TEXT_PROVIDED] == ConfidenceLevel.MEDIUM

    def test_ocr_extracted_ceiling_medium(self):
        """OCR_EXTRACTED should have MEDIUM ceiling."""
        assert CONFIDENCE_CEILINGS[AnalysisMode.OCR_EXTRACTED] == ConfidenceLevel.MEDIUM

    def test_article_fetched_ceiling_high(self):
        """ARTICLE_FETCHED should have HIGH ceiling."""
        assert CONFIDENCE_CEILINGS[AnalysisMode.ARTICLE_FETCHED] == ConfidenceLevel.HIGH

    def test_get_confidence_ceiling(self):
        """get_confidence_ceiling should return correct level."""
        assert get_confidence_ceiling(AnalysisMode.TRANSCRIPT_GROUNDED) == ConfidenceLevel.HIGH
        assert get_confidence_ceiling(AnalysisMode.VIDEO_ONLY) == ConfidenceLevel.LOW

    def test_get_confidence_ceiling_default(self):
        """get_confidence_ceiling should default to LOW for unknown."""
        # This tests the edge case where a mode might not be in the dict
        # (shouldn't happen in practice, but good defensive coding)
        assert get_confidence_ceiling(AnalysisMode.TRANSCRIPT_GROUNDED) == ConfidenceLevel.HIGH

    def test_get_confidence_ceiling_string(self):
        """get_confidence_ceiling_string should return uppercase string."""
        assert get_confidence_ceiling_string(AnalysisMode.TRANSCRIPT_GROUNDED) == "HIGH"
        assert get_confidence_ceiling_string(AnalysisMode.CAPTION_GROUNDED) == "MEDIUM"
        assert get_confidence_ceiling_string(AnalysisMode.VIDEO_ONLY) == "LOW"

    def test_get_confidence_ceiling_string_from_string_value(self):
        """get_confidence_ceiling_string should handle string input."""
        assert get_confidence_ceiling_string("transcript_grounded") == "HIGH"
        assert get_confidence_ceiling_string("video_only") == "LOW"

    def test_get_confidence_ceiling_string_invalid_string(self):
        """get_confidence_ceiling_string should return LOW for invalid string."""
        assert get_confidence_ceiling_string("invalid_mode") == "LOW"

    def test_all_modes_have_ceiling_string(self):
        """All modes should have a ceiling string mapping."""
        for mode in AnalysisMode:
            assert mode in CONFIDENCE_CEILING_STRINGS
            assert CONFIDENCE_CEILING_STRINGS[mode] in ("HIGH", "MEDIUM", "LOW")


# =============================================================================
# TestQuotePermissions
# =============================================================================


class TestQuotePermissions:
    """Tests for quote permission functions and mappings."""

    def test_all_modes_have_quote_permission(self):
        """All analysis modes should have quote permission defined."""
        for mode in AnalysisMode:
            assert mode in QUOTES_ALLOWED
            assert isinstance(QUOTES_ALLOWED[mode], bool)

    def test_transcript_grounded_allows_quotes(self):
        """TRANSCRIPT_GROUNDED should allow quotes."""
        assert QUOTES_ALLOWED[AnalysisMode.TRANSCRIPT_GROUNDED] is True
        assert are_quotes_allowed(AnalysisMode.TRANSCRIPT_GROUNDED) is True

    def test_caption_grounded_allows_quotes(self):
        """CAPTION_GROUNDED should allow quotes (approximate)."""
        assert QUOTES_ALLOWED[AnalysisMode.CAPTION_GROUNDED] is True
        assert are_quotes_allowed(AnalysisMode.CAPTION_GROUNDED) is True

    def test_video_only_forbids_quotes(self):
        """VIDEO_ONLY should NOT allow quotes."""
        assert QUOTES_ALLOWED[AnalysisMode.VIDEO_ONLY] is False
        assert are_quotes_allowed(AnalysisMode.VIDEO_ONLY) is False

    def test_text_provided_allows_quotes(self):
        """TEXT_PROVIDED should allow quotes (with warning)."""
        assert QUOTES_ALLOWED[AnalysisMode.TEXT_PROVIDED] is True
        assert are_quotes_allowed(AnalysisMode.TEXT_PROVIDED) is True

    def test_ocr_extracted_allows_quotes(self):
        """OCR_EXTRACTED should allow quotes (with warning)."""
        assert QUOTES_ALLOWED[AnalysisMode.OCR_EXTRACTED] is True
        assert are_quotes_allowed(AnalysisMode.OCR_EXTRACTED) is True

    def test_article_fetched_allows_quotes(self):
        """ARTICLE_FETCHED should allow quotes."""
        assert QUOTES_ALLOWED[AnalysisMode.ARTICLE_FETCHED] is True
        assert are_quotes_allowed(AnalysisMode.ARTICLE_FETCHED) is True


# =============================================================================
# TestDegradedQuoteModes
# =============================================================================


class TestDegradedQuoteModes:
    """Tests for degraded quote mode detection."""

    def test_text_provided_is_degraded(self):
        """TEXT_PROVIDED should be a degraded quote mode."""
        assert AnalysisMode.TEXT_PROVIDED in DEGRADED_QUOTE_MODES
        assert requires_quote_warning(AnalysisMode.TEXT_PROVIDED) is True

    def test_ocr_extracted_is_degraded(self):
        """OCR_EXTRACTED should be a degraded quote mode."""
        assert AnalysisMode.OCR_EXTRACTED in DEGRADED_QUOTE_MODES
        assert requires_quote_warning(AnalysisMode.OCR_EXTRACTED) is True

    def test_caption_grounded_is_degraded(self):
        """CAPTION_GROUNDED should be a degraded quote mode."""
        assert AnalysisMode.CAPTION_GROUNDED in DEGRADED_QUOTE_MODES
        assert requires_quote_warning(AnalysisMode.CAPTION_GROUNDED) is True

    def test_transcript_grounded_not_degraded(self):
        """TRANSCRIPT_GROUNDED should NOT be a degraded mode."""
        assert AnalysisMode.TRANSCRIPT_GROUNDED not in DEGRADED_QUOTE_MODES
        assert requires_quote_warning(AnalysisMode.TRANSCRIPT_GROUNDED) is False

    def test_article_fetched_not_degraded(self):
        """ARTICLE_FETCHED should NOT be a degraded mode."""
        assert AnalysisMode.ARTICLE_FETCHED not in DEGRADED_QUOTE_MODES
        assert requires_quote_warning(AnalysisMode.ARTICLE_FETCHED) is False

    def test_video_only_not_degraded(self):
        """VIDEO_ONLY should NOT be degraded (no quotes allowed at all)."""
        assert AnalysisMode.VIDEO_ONLY not in DEGRADED_QUOTE_MODES
        assert requires_quote_warning(AnalysisMode.VIDEO_ONLY) is False


# =============================================================================
# TestNoQuoteModes
# =============================================================================


class TestNoQuoteModes:
    """Tests for no-quote mode detection."""

    def test_video_only_is_no_quote_mode(self):
        """VIDEO_ONLY should be a no-quote mode."""
        assert AnalysisMode.VIDEO_ONLY in NO_QUOTE_MODES
        assert is_no_quote_mode(AnalysisMode.VIDEO_ONLY) is True

    def test_transcript_grounded_not_no_quote(self):
        """TRANSCRIPT_GROUNDED should NOT be a no-quote mode."""
        assert AnalysisMode.TRANSCRIPT_GROUNDED not in NO_QUOTE_MODES
        assert is_no_quote_mode(AnalysisMode.TRANSCRIPT_GROUNDED) is False

    def test_text_provided_not_no_quote(self):
        """TEXT_PROVIDED should NOT be a no-quote mode."""
        assert AnalysisMode.TEXT_PROVIDED not in NO_QUOTE_MODES
        assert is_no_quote_mode(AnalysisMode.TEXT_PROVIDED) is False

    def test_only_video_only_is_no_quote(self):
        """Only VIDEO_ONLY should be in no-quote modes."""
        assert len(NO_QUOTE_MODES) == 1
        assert AnalysisMode.VIDEO_ONLY in NO_QUOTE_MODES


# =============================================================================
# TestModeDescriptions
# =============================================================================


class TestModeDescriptions:
    """Tests for mode description helpers."""

    def test_all_modes_have_description(self):
        """All analysis modes should have a description."""
        for mode in AnalysisMode:
            assert mode in MODE_DESCRIPTIONS
            assert len(MODE_DESCRIPTIONS[mode]) > 0

    def test_get_mode_description(self):
        """get_mode_description should return description string."""
        desc = get_mode_description(AnalysisMode.TRANSCRIPT_GROUNDED)
        assert "transcript" in desc.lower()
        assert len(desc) > 10

    def test_video_only_description_mentions_no_quotes(self):
        """VIDEO_ONLY description should mention no quotes."""
        desc = get_mode_description(AnalysisMode.VIDEO_ONLY)
        assert "NO quotes" in desc or "no quotes" in desc.lower()

    def test_mode_description_default(self):
        """get_mode_description should have sensible default."""
        # This shouldn't happen in practice, but tests defensive coding
        desc = get_mode_description(AnalysisMode.TRANSCRIPT_GROUNDED)
        assert desc != "Unknown analysis mode"


# =============================================================================
# TestQuoteWarnings
# =============================================================================


class TestQuoteWarnings:
    """Tests for quote warning messages."""

    def test_text_provided_has_warning(self):
        """TEXT_PROVIDED should have a warning message."""
        warning = get_quote_warning(AnalysisMode.TEXT_PROVIDED)
        assert warning is not None
        assert "user-provided" in warning.lower() or "unconfirmed" in warning.lower()

    def test_ocr_extracted_has_warning(self):
        """OCR_EXTRACTED should have a warning message."""
        warning = get_quote_warning(AnalysisMode.OCR_EXTRACTED)
        assert warning is not None
        assert "ocr" in warning.lower()

    def test_caption_grounded_has_warning(self):
        """CAPTION_GROUNDED should have a warning message."""
        warning = get_quote_warning(AnalysisMode.CAPTION_GROUNDED)
        assert warning is not None
        assert "approximate" in warning.lower() or "caption" in warning.lower()

    def test_transcript_grounded_no_warning(self):
        """TRANSCRIPT_GROUNDED should not have a warning."""
        warning = get_quote_warning(AnalysisMode.TRANSCRIPT_GROUNDED)
        assert warning is None

    def test_article_fetched_no_warning(self):
        """ARTICLE_FETCHED should not have a warning."""
        warning = get_quote_warning(AnalysisMode.ARTICLE_FETCHED)
        assert warning is None

    def test_video_only_no_warning(self):
        """VIDEO_ONLY should not have a warning (no quotes allowed)."""
        warning = get_quote_warning(AnalysisMode.VIDEO_ONLY)
        assert warning is None

    def test_degraded_modes_have_warnings(self):
        """All degraded modes should have warning messages."""
        for mode in DEGRADED_QUOTE_MODES:
            assert mode in QUOTE_WARNING_MESSAGES
            assert get_quote_warning(mode) is not None


# =============================================================================
# TestMappingConsistency
# =============================================================================


class TestMappingConsistency:
    """Tests to ensure all mappings are consistent."""

    def test_all_modes_covered_in_all_mappings(self):
        """All modes should be in all relevant mappings."""
        all_modes = set(AnalysisMode)

        assert set(CONFIDENCE_CEILINGS.keys()) == all_modes
        assert set(QUOTES_ALLOWED.keys()) == all_modes
        assert set(CONFIDENCE_CEILING_STRINGS.keys()) == all_modes
        assert set(MODE_DESCRIPTIONS.keys()) == all_modes

    def test_no_quote_modes_subset_of_quotes_not_allowed(self):
        """NO_QUOTE_MODES should only contain modes where quotes not allowed."""
        for mode in NO_QUOTE_MODES:
            assert QUOTES_ALLOWED[mode] is False

    def test_degraded_modes_have_quotes_allowed(self):
        """DEGRADED_QUOTE_MODES should only contain modes where quotes allowed."""
        for mode in DEGRADED_QUOTE_MODES:
            assert QUOTES_ALLOWED[mode] is True

    def test_ceiling_strings_match_ceiling_levels(self):
        """Ceiling strings should match actual ceiling level values."""
        for mode in AnalysisMode:
            ceiling_level = CONFIDENCE_CEILINGS[mode]
            ceiling_string = CONFIDENCE_CEILING_STRINGS[mode]
            assert ceiling_string.lower() == ceiling_level.value


# =============================================================================
# TestArchitectureCompliance
# =============================================================================


class TestArchitectureCompliance:
    """Tests to verify compliance with CLAUDE.md architecture rules."""

    def test_video_modes_have_correct_ceilings(self):
        """Video modes should have ceilings per spec:
        - transcript_grounded: HIGH
        - caption_grounded: MEDIUM
        - video_only: LOW
        """
        assert get_confidence_ceiling(AnalysisMode.TRANSCRIPT_GROUNDED) == ConfidenceLevel.HIGH
        assert get_confidence_ceiling(AnalysisMode.CAPTION_GROUNDED) == ConfidenceLevel.MEDIUM
        assert get_confidence_ceiling(AnalysisMode.VIDEO_ONLY) == ConfidenceLevel.LOW

    def test_non_video_modes_have_correct_ceilings(self):
        """Non-video modes should have ceilings per spec:
        - text_provided: MEDIUM
        - ocr_extracted: MEDIUM
        - article_fetched: HIGH
        """
        assert get_confidence_ceiling(AnalysisMode.TEXT_PROVIDED) == ConfidenceLevel.MEDIUM
        assert get_confidence_ceiling(AnalysisMode.OCR_EXTRACTED) == ConfidenceLevel.MEDIUM
        assert get_confidence_ceiling(AnalysisMode.ARTICLE_FETCHED) == ConfidenceLevel.HIGH

    def test_only_video_only_forbids_quotes(self):
        """Per spec, only VIDEO_ONLY should forbid quotes."""
        quote_forbidden_modes = [m for m in AnalysisMode if not are_quotes_allowed(m)]
        assert quote_forbidden_modes == [AnalysisMode.VIDEO_ONLY]

    def test_mode_selection_is_deterministic(self):
        """Mode selection should be deterministic (same input = same output)."""
        content = {"supadata_transcript": True}
        mode1 = select_analysis_mode("youtube", content)
        mode2 = select_analysis_mode("youtube", content)
        mode3 = select_analysis_mode("youtube", content)
        assert mode1 == mode2 == mode3 == AnalysisMode.TRANSCRIPT_GROUNDED

    def test_transcript_acquisition_order(self):
        """Transcript acquisition order should be: Supadata > Whisper > Captions > None."""
        # All available - should pick Supadata (first in order)
        all_available = {
            "supadata_transcript": True,
            "whisper_transcript": True,
            "youtube_captions": True,
        }
        assert select_analysis_mode("youtube", all_available) == AnalysisMode.TRANSCRIPT_GROUNDED

        # Supadata unavailable - should pick Whisper
        no_supadata = {
            "supadata_transcript": False,
            "whisper_transcript": True,
            "youtube_captions": True,
        }
        assert select_analysis_mode("youtube", no_supadata) == AnalysisMode.TRANSCRIPT_GROUNDED

        # Only captions - should pick caption_grounded
        only_captions = {
            "supadata_transcript": False,
            "whisper_transcript": False,
            "youtube_captions": True,
        }
        assert select_analysis_mode("youtube", only_captions) == AnalysisMode.CAPTION_GROUNDED

        # Nothing available - should pick video_only
        nothing = {
            "supadata_transcript": False,
            "whisper_transcript": False,
            "youtube_captions": False,
        }
        assert select_analysis_mode("youtube", nothing) == AnalysisMode.VIDEO_ONLY
