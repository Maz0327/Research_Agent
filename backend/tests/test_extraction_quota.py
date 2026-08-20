"""Tests for the length-scaled extraction quota.

Cover for the fix to D-027's finding. Every Gemini 3.x model returns a roughly
fixed NUMBER of items whatever it is handed, so a long source is summarized
harder: measured, one source gave 6 quotes from 6,392 words (0.94 per thousand)
and 4 from 379 words (10.55 per thousand). The prompt now states the quota in
proportion to the source, and the regression these tests protect is density
staying flat as the input grows.
"""
import os

import pytest

from backend.pipeline.prompts.semantic_extraction_prompt import (
    CLAIMS_PER_1000_WORDS,
    KEY_POINTS_PER_1000_WORDS,
    QUOTES_PER_1000_WORDS,
    build_extraction_quota,
    build_semantic_extraction_prompt,
)


def _numbers_after(block: str, label: str) -> tuple[int, int]:
    """Read the low and high figures the quota states for one unit type."""
    line = next(line for line in block.splitlines() if line.strip().startswith(label))
    low, high = [int(part) for part in line.replace(",", "").split() if part.isdigit()]
    return low, high


class TestQuotaScaling:
    """The quota is a rate, not a number."""

    @pytest.mark.parametrize("words", [1000, 3000, 6392, 12000])
    def test_targets_scale_with_the_source(self, words):
        """Twice the source, twice the quota."""
        block = build_extraction_quota("word " * words)

        low, high = _numbers_after(block, "- quotes:")

        assert low == int(words / 1000 * QUOTES_PER_1000_WORDS[0])
        assert high == int(words / 1000 * QUOTES_PER_1000_WORDS[1])

    def test_density_stays_flat_as_the_input_grows(self):
        """The regression this exists to prevent, asserted at four sizes.

        These are the four input sizes the original measurement used, where
        the model's own density fell from 10.55 to 0.94 quotes per thousand
        words. The quota it is given must not do the same thing.
        """
        densities = []
        for words in (379, 912, 1790, 6392):
            block = build_extraction_quota("word " * words)
            low, _high = _numbers_after(block, "- quotes:")
            densities.append(low / (words / 1000))

        assert max(densities) - min(densities) < 1.0
        assert all(d >= QUOTES_PER_1000_WORDS[0] - 1 for d in densities)

    def test_every_unit_type_gets_its_own_rate(self):
        """Quotes and claims carry the evidence; key points sit a level up."""
        block = build_extraction_quota("word " * 4000)

        quotes = _numbers_after(block, "- quotes:")
        claims = _numbers_after(block, "- claims:")
        points = _numbers_after(block, "- key points:")

        assert quotes[0] > claims[0] > points[0]
        assert points[1] == int(4000 / 1000 * KEY_POINTS_PER_1000_WORDS[1])
        assert claims[1] == int(4000 / 1000 * CLAIMS_PER_1000_WORDS[1])

    def test_short_sources_get_no_quota(self):
        """Below a couple of hundred words a rate says nothing useful."""
        assert build_extraction_quota("word " * 50) == ""
        assert build_extraction_quota("") == ""


class TestTruncationFallback:
    """A quota that overflows the output ceiling must not lose the source."""

    def test_a_truncated_response_retries_on_half_the_source(self, monkeypatch):
        """Measured: two of six sources overflowed once the quota was added."""
        from unittest.mock import MagicMock

        from backend.models.semantic_units import AnalysisMode
        from backend.pipeline.stages import semantic_extraction as se

        client = MagicMock()
        client.generate_json.side_effect = [
            {"data": {}, "cost": 0.01, "truncated": True, "error": "too big"},
            {"data": {"quotes": [], "claims": [], "key_points": []}, "cost": 0.01},
        ]
        monkeypatch.setattr(se, "validate_semantic_extraction", lambda **k: MagicMock(results=[], warnings=[]))
        monkeypatch.setattr(se, "should_retry", lambda report: False)

        result, _report, cost = se.extract_semantic_structure(
            gemini_client=client,
            source_id="SRC_1",
            source_content="word " * 8000,
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            title="A source",
        )

        assert client.generate_json.call_count == 2
        first, second = [c.kwargs["prompt"] for c in client.generate_json.call_args_list]
        assert len(second) < len(first)
        assert result.parse_error is False
        assert cost == 0.02


class TestQuotaSafety:
    """A quota must never become a reason to invent."""

    def test_the_empty_output_permission_is_restated(self):
        """Returning less than the quota beats fabricating to reach it."""
        block = build_extraction_quota("word " * 3000)

        assert "EMPTY OUTPUT PERMISSION" in block
        assert "worse failure" in block

    def test_the_quota_reaches_the_built_prompt(self):
        """Every mode gets it, since it is appended after mode dispatch."""
        for mode in ("transcript_grounded", "article_fetched", "text_provided"):
            prompt = build_semantic_extraction_prompt(
                source_id="SRC_1",
                source_content="word " * 3000,
                analysis_mode=mode,
                title="A source",
            )

            assert "EXTRACTION QUOTA" in prompt
            assert "SOURCE IDENTITY LOCK" in prompt or "source_id" in prompt


class TestThinSourceHonesty:
    """A quota must never become a reason to invent.

    The empty-output law says a sparse source produces a sparse extraction. A
    quota is a standing instruction to produce MORE, so this is the failure
    mode the quota could introduce, and the one that would matter most: a
    fabricated quote is the worst thing this pipeline can emit.

    Measured live on 2026-08-20 with gemini-3.6-flash: a 2,015-word page of
    boilerplate carrying two real facts, quota asking for 16 to 24 quotes.
    The model returned 8 quotes, 2 key points and 4 claims, all 8 quotes
    verbatim, zero flagged. It under-delivered against the quota instead of
    filling it, which is the required behaviour.
    """

    THIN_SOURCE = (
        "Welcome to the Hawara information page. This page is part of our site. "
        "The site is maintained by volunteers who care about the region. "
        "We hope you find the page useful. Thank you for visiting the page today. "
        "Please check back later for updates about the region and the site. "
    ) * 40 + "The pyramid at Hawara was built for Amenemhat III. A canal runs past the site."

    def test_the_quota_still_permits_under_delivery(self):
        """The instruction that keeps a thin source thin is stated, not implied."""
        block = " ".join(build_extraction_quota(self.THIN_SOURCE).split())

        assert "EMPTY OUTPUT PERMISSION" in block
        assert "Inventing material to hit a number is a worse failure" in block

    @pytest.mark.live_api
    @pytest.mark.skipif(
        os.environ.get("RUN_LIVE_API_TESTS") != "1",
        reason="live provider call; set RUN_LIVE_API_TESTS=1 to run",
    )
    def test_a_thin_source_under_delivers_and_flags_nothing(self):
        """The real check: quota on, sparse source, no fabrication."""
        from backend.integrations.gemini_client import GeminiClient
        from backend.models.semantic_units import AnalysisMode
        from backend.pipeline.quote_verification import FLAGGED, verify_quote
        from backend.pipeline.stages.semantic_extraction import extract_semantic_structure

        words = len(self.THIN_SOURCE.split())
        quota_low, _high = _numbers_after(
            build_extraction_quota(self.THIN_SOURCE), "- quotes:"
        )

        result, _report, _cost = extract_semantic_structure(
            gemini_client=GeminiClient(),
            source_id="SRC_THIN",
            source_content=self.THIN_SOURCE,
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            title="Hawara information page",
        )

        verdicts = [verify_quote(q.text, self.THIN_SOURCE)["status"] for q in result.quotes]

        assert verdicts.count(FLAGGED) == 0, "the quota produced unsupported quotes"
        assert len(result.quotes) < quota_low, (
            f"a {words}-word boilerplate page yielded {len(result.quotes)} quotes "
            f"against a floor of {quota_low}: the model filled the quota"
        )
