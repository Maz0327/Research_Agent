"""Tests for the harvest recall audit (work order I.25).

The audit exists because the harvest inventory is otherwise one model's
unchecked word about what a source contained. What these tests pin is the
honesty of the measurement rather than any particular number: a failed
re-extraction must not read as perfect recall, text the harvest never saw must
be reported as unread rather than as a miss, and one dense source must not be
able to carry the whole corpus's score.
"""
from unittest.mock import MagicMock

from backend.pipeline.harvest_audit import (
    RECALL_THRESHOLD,
    audit_harvest_recall,
    blocks_of,
    recall_of,
    score_sample,
    stratified_sample,
    truncated_sources,
)

# An unpunctuated transcript, which is what Supadata actually returns.
TRANSCRIPT = " ".join(f"word{i} of the labyrinth chamber survey" for i in range(400))

PARAGRAPHS = "\n\n".join(
    f"Paragraph {i} describes the Hawara excavation in enough words to be worth "
    f"sampling, because a block shorter than the floor cannot be scored against "
    f"anything and would only add noise to the recall rate this module reports."
    for i in range(9)
)


class TestBlockSplitting:
    """A source has to be divisible before it can be sampled."""

    def test_real_paragraphs_are_used_when_present(self):
        blocks = blocks_of(PARAGRAPHS)
        assert len(blocks) == 9

    def test_an_unpunctuated_transcript_still_splits(self):
        """Measured on the Hawara fixture: transcripts carry no full stops at
        all, so both the paragraph and sentence splitters collapse to one block
        and the word-window fallback is the only thing left."""
        blocks = blocks_of(TRANSCRIPT)
        assert len(blocks) > 10
        assert all(len(b.split()) >= 25 for b in blocks)

    def test_empty_text_yields_no_blocks(self):
        assert blocks_of("") == []
        assert blocks_of("   ") == []


class TestSampling:
    """The sample is spread by position, and it reproduces."""

    def test_positions_cycle_front_middle_back(self):
        picked = stratified_sample(PARAGRAPHS, per_source=3, seed=0)
        assert [p for p, _ in picked] == ["front", "middle", "back"]

    def test_the_same_seed_picks_the_same_blocks(self):
        """A recall number that moves on re-run measures nothing."""
        assert stratified_sample(PARAGRAPHS, 3, seed=7) == stratified_sample(
            PARAGRAPHS, 3, seed=7
        )

    def test_a_source_too_short_to_split_is_skipped_not_faked(self):
        assert stratified_sample("", 3) == []


class TestRecallScoring:
    """What counts as captured, and what a miss carries with it."""

    def test_a_fact_the_inventory_holds_verbatim_is_captured(self):
        fact = "The Hawara labyrinth was described by Herodotus as exceeding the pyramids."
        rate, misses = recall_of([fact], [fact])
        assert rate == 1.0
        assert misses == []

    def test_a_fact_the_inventory_lacks_is_a_miss_carrying_its_score(self):
        rate, misses = recall_of(
            ["The survey team drilled to a depth of eight metres at the north wall."],
            ["Herodotus visited Egypt and wrote about a great structure there."],
        )
        assert rate == 0.0
        assert misses[0]["best_score"] < RECALL_THRESHOLD

    def test_scores_are_kept_for_hits_as_well_as_misses(self):
        """A recall number is only arguable if the distribution under it is visible."""
        scored = score_sample(
            ["The labyrinth sits beside the pyramid at Hawara in Egypt."],
            ["The labyrinth sits beside the pyramid at Hawara in Egypt."],
        )
        assert len(scored) == 1
        assert scored[0]["best_score"] == 1.0

    def test_facts_too_short_to_score_are_excluded_not_counted_wrong(self):
        """"It is old" matches anything or nothing; either answer is noise."""
        assert score_sample(["It is old."], ["Something else entirely here."]) == []


class TestTruncation:
    """Text the harvest never saw is not text the harvest missed."""

    def test_a_source_over_the_cap_is_reported_with_its_unread_share(self):
        cut = truncated_sources(
            [{"source_id": "SRC_3", "full_text": "x" * 36_823}], max_chars=24_000
        )
        assert cut[0]["unread_chars"] == 12_823
        assert cut[0]["unread_share"] == 0.348

    def test_a_source_inside_the_cap_is_not_reported(self):
        assert truncated_sources(
            [{"source_id": "SRC_1", "full_text": "x" * 100}], max_chars=24_000
        ) == []


class TestAuditReport:
    """End to end, including the failure paths."""

    def _client(self, facts):
        client = MagicMock()
        client.generate_structured.return_value = ({"facts": facts}, {})
        return client

    def test_a_failed_re_extraction_does_not_read_as_perfect_recall(self):
        """The worst possible bug here: a dead provider reporting 100% coverage."""
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("provider down")
        report = audit_harvest_recall(
            [{"source_id": "SRC_1", "full_text": PARAGRAPHS}],
            [{"source_id": "SRC_1", "text": "A harvested fact about the excavation."}],
            client,
        )
        assert report["overall_recall"] is None
        assert report["sampled_facts"] == 0

    def test_macro_recall_gives_every_source_one_vote(self):
        """Measured on the fixture: pooling let two dense articles move back-of-
        source recall from 0.55 to 0.82 while the thin sources were unchanged."""
        fact = "The Hawara excavation reached the water table at eight metres depth."
        report = audit_harvest_recall(
            [
                {"source_id": "SRC_1", "full_text": PARAGRAPHS},
                {"source_id": "SRC_2", "full_text": PARAGRAPHS},
            ],
            [{"source_id": "SRC_1", "text": fact}],
            self._client([fact]),
        )
        # SRC_1 holds the fact, SRC_2 holds nothing: one source each way.
        assert report["macro_recall"] == 0.5
        assert report["weakest_sources"][0]["source_id"] == "SRC_2"

    def test_the_report_names_its_own_threshold(self):
        """A rate without the cut that produced it cannot be argued with."""
        report = audit_harvest_recall(
            [{"source_id": "SRC_1", "full_text": PARAGRAPHS}],
            [{"source_id": "SRC_1", "text": "A fact."}],
            self._client(["A fact about the Hawara excavation and its depth."]),
        )
        assert report["threshold"] == RECALL_THRESHOLD
        assert "score_distribution" in report
