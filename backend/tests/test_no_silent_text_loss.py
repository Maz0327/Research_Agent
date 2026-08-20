"""The pre-rerun sweep: nothing may lose source text silently (2026-08-20).

Four defects of one family were found before regenerating the Hawara Briefing,
and this file is the guard that keeps them fixed. The family is: source text
that never reaches a model, or an ask that does not scale with the input, in a
way nothing reports.

Each test names the measured defect it descends from, because the number that
was wrong in every case still looked plausible.
"""
import pytest

from backend.pipeline.briefing_passes import (
    READ_MIN_CHARS_PER_SOURCE,
    READ_TOTAL_CHARS,
    read_budget,
)
from backend.pipeline.prompts.llm_judge_prompt import relevant_source
from backend.pipeline.prompts.semantic_extraction_prompt import build_extraction_quota
from backend.pipeline.stages.harvest_stage import HARVEST_SYSTEM, harvest_quota


class TestHarvestScalesWithLength:
    """Measured: 40 facts per 1,000 words on short sources, 12 on long."""

    def test_the_ask_is_a_rate_not_a_fixed_range(self):
        """"Extract 10 to 40 facts" returns roughly the same count for 1,000
        words as for 10,000 — the D-029 behaviour, one pass over."""
        quota = harvest_quota()
        assert "per 1,000 words" in quota or "for every 1,000 words" in quota
        assert "10 to 40 facts" not in HARVEST_SYSTEM

    def test_the_rate_is_a_floor_on_effort_not_on_output(self):
        """The empty-output law outranks the quota: a thin source under-delivers
        honestly rather than being padded to hit a number."""
        quota = harvest_quota()
        assert "return fewer" in quota
        assert "invent" in quota

    def test_the_template_still_carries_its_placeholder(self):
        """The quota is substituted per call; a system prompt shipped with the
        raw placeholder would ask the model for "{quota}"."""
        assert "{quota}" in HARVEST_SYSTEM


class TestReadBudget:
    """Measured: a flat 40,000-char cap took 28% off the Hawara corpus's
    longest source while the call sat nowhere near its context limit."""

    def test_a_corpus_inside_the_budget_is_sent_whole(self):
        texts = {"SRC_1": "x" * 55_779, "SRC_2": "y" * 20_000}
        assert read_budget(texts) == {"SRC_1": 55_779, "SRC_2": 20_000}

    def test_an_overflowing_corpus_spends_exactly_its_budget(self):
        texts = {f"SRC_{i}": "x" * 100_000 for i in range(10)}
        assert sum(read_budget(texts).values()) == READ_TOTAL_CHARS

    def test_the_cut_lands_on_the_long_sources_not_the_short_ones(self):
        """One enormous source must not starve the short ones around it."""
        texts = {"BIG": "x" * 2_000_000, "SMALL": "y" * 5_000}
        budget = read_budget(texts)
        assert budget["SMALL"] == 5_000
        assert budget["BIG"] < 2_000_000

    def test_every_source_keeps_the_floor(self):
        texts = {f"SRC_{i}": "x" * 500_000 for i in range(20)}
        assert min(read_budget(texts).values()) >= READ_MIN_CHARS_PER_SOURCE

    def test_an_empty_corpus_is_not_an_error(self):
        assert read_budget({}) == {}


class TestExtractionRetryKeepsTheSource:
    """Measured: the truncation retry halved the SOURCE and continued, so the
    back half of every truncating source was never extracted — while a comment
    claimed the remainder was covered."""

    def test_a_lower_scale_asks_for_less_from_the_same_text(self):
        text = "word " * 4_000
        full = build_extraction_quota(text, scale=1.0)
        half = build_extraction_quota(text, scale=0.5)
        assert full != half
        # Same source length reported either way; only the ask shrinks.
        assert "4000" in full.replace(",", "") and "4000" in half.replace(",", "")

    def test_the_floor_keeps_a_quota_from_reaching_zero(self):
        text = "word " * 1_000
        assert build_extraction_quota(text, scale=0.01)

    def test_a_source_too_short_to_scale_gets_no_quota(self):
        assert build_extraction_quota("word " * 50) == ""


class TestJudgeSeesTheEvidence:
    """Measured: the production judge took the FIRST 15,000 characters, so a
    claim whose evidence sat later was marked unsupported on the strength of
    text the judge never saw — in the component that checks everything else."""

    EVIDENCE = (
        "The survey team recorded a cavity at eighteen metres beneath the "
        "Hawara pyramid in 2008."
    )
    EXTRACTION = '{"claim": "a cavity was recorded at eighteen metres beneath Hawara"}'

    def test_evidence_at_the_end_of_a_long_source_survives(self):
        source = ("unrelated chatter about other matters. " * 900) + self.EVIDENCE
        kept = relevant_source(source, self.EXTRACTION, 15_000)
        assert "eighteen metres beneath the Hawara pyramid" in kept

    def test_a_short_source_is_passed_through_untouched(self):
        assert relevant_source(self.EVIDENCE, self.EXTRACTION, 15_000) == self.EVIDENCE

    def test_the_budget_is_respected(self):
        source = "unrelated chatter about other matters. " * 3_000
        assert len(relevant_source(source, self.EXTRACTION, 15_000)) <= 16_000

    def test_omissions_are_marked_rather_than_silently_joined(self):
        """A judge reading two windows spliced together would see a sentence
        that the source never contained."""
        source = (
            self.EVIDENCE
            + (" unrelated chatter about other matters." * 900)
            + " The same team returned to the Hawara pyramid cavity in 2011."
        )
        kept = relevant_source(source, self.EXTRACTION, 8_000)
        if kept.count("Hawara") > 1:
            assert "omitted" in kept


@pytest.mark.parametrize(
    "module,symbol",
    [
        ("backend.pipeline.stages.harvest_stage", "chunk_text"),
        ("backend.pipeline.briefing_passes", "read_budget"),
        ("backend.pipeline.prompts.llm_judge_prompt", "relevant_source"),
    ],
)
def test_each_fix_is_reachable(module, symbol):
    """A fix that is not imported anywhere is not a fix."""
    import importlib

    assert hasattr(importlib.import_module(module), symbol)
