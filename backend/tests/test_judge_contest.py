"""Tests for the judge-contest harness and its constructed ground truth.

Cover for P3 work-order item 17. A judge slot cannot be filled by reading
model cards, and hand-labelling is slow and disputable, so ground truth is
constructed: a harvested fact is supported by its source, and a fact altered
in a named way is not. These tests pin the construction and the scoring, which
is what makes the contest's numbers mean anything.
"""
from unittest.mock import MagicMock

from backend.pipeline.faithfulness_set import (
    CORRUPTIONS,
    build_faithfulness_set,
    cohens_kappa,
    names_in_corpus,
)
from backend.pipeline.judge_contest import (
    judge_item,
    judge_pair,
    score_judge,
    score_position_bias,
    source_window,
)

FACTS = [
    {"fact_id": f"SRC_1:F_{i}", "source_id": "SRC_1", "text": text}
    for i, text in enumerate(
        [
            "Flinders Petrie excavated Hawara in 1888 and found a stone bed of 304 metres.",
            "Herodotus wrote that the labyrinth held 3,000 chambers below and above ground.",
            "The Mataha expedition scanned the site in 2008 with the NRIAG institute.",
            "Karl Lepsius mistook a Roman village for the labyrinth in 1843.",
            "The canal was cut across the site around 1820 and flooded the entrance.",
            "Eric Uphill rebuilt the complex as a standard twelfth dynasty funerary site.",
            "Louis De Cordier funded the survey and published the scans himself in 2010.",
            "Timothy Akers reported a metallic object forty metres across at the centre.",
            "Carmen Boulter produced a two level model showing one flooded level.",
            "Trevor Grassi runs the foundation page and organised the rescue plan.",
            "Zahi Hawass was accused of halting the release of the 2008 findings.",
            "Abbas Mohamed ran the geophysics for the expedition and published in 2009.",
            "Filippo Biondi agreed to scan the site after finishing work at Giza.",
            "Alan Lloyd showed that only two of the six ancient authors visited.",
            "Mark Carlotto published a satellite paper on the site in 2023.",
            "William Brown drilled boreholes and found the pyramid corner underground.",
        ]
    )
]


class TestConstructedGroundTruth:
    """The labels are true by construction, which is the point."""

    def test_the_set_is_balanced_and_covers_every_corruption(self):
        """Half supported, half altered, with each failure mode represented."""
        items = build_faithfulness_set(FACTS, size=12)

        supported = [i for i in items if i["label"] == "supported"]
        corrupted = [i for i in items if i["label"] == "unsupported"]

        assert len(supported) == len(corrupted) == 6
        assert set(i["corruption"] for i in corrupted) <= set(CORRUPTIONS)

    def test_corrupted_items_differ_from_their_original(self):
        """An 'alteration' that changed nothing would be labelled wrong."""
        items = build_faithfulness_set(FACTS, size=8)

        for item in items:
            if item["label"] == "unsupported":
                assert item["statement"] != item["original"]

    def test_the_set_is_identical_for_every_judge(self):
        """A contest where the models see different items proves nothing."""
        first = build_faithfulness_set(FACTS, size=8)
        second = build_faithfulness_set(FACTS, size=8)

        assert [i["statement"] for i in first] == [i["statement"] for i in second]

    def test_names_are_pooled_for_attribution_swaps(self):
        """Swapping in a name from the same corpus keeps the item plausible."""
        names = names_in_corpus([f["text"] for f in FACTS], minimum=1)

        assert "Flinders Petrie" in names
        assert "Karl Lepsius" in names


class TestKappa:
    """Raw agreement flatters; kappa is what gets reported."""

    def test_perfect_agreement(self):
        assert cohens_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0

    def test_chance_agreement_scores_zero(self):
        """Half right on a balanced set is worth nothing, and says so."""
        assert cohens_kappa(["a", "b", "a", "b"], ["a", "a", "b", "b"]) == 0.0

    def test_always_answering_the_same_thing_scores_zero(self):
        """The failure mode raw agreement hides: 50% accuracy, zero skill."""
        truth = ["supported", "unsupported"] * 10
        lazy = ["supported"] * 20

        accuracy = sum(1 for t, p in zip(truth, lazy, strict=False) if t == p) / len(truth)

        assert accuracy == 0.5
        assert cohens_kappa(truth, lazy) == 0.0


class TestScoring:
    """The harness measures what it claims to measure."""

    def _client(self, verdicts):
        client = MagicMock()
        client.generate_structured.side_effect = [
            ({"verdict": v, "reason": "because"}, {"cost": 0.0}) for v in verdicts
        ]
        return client

    def test_a_perfect_judge_scores_one(self):
        items = build_faithfulness_set(FACTS, size=4)
        windows = {i["item_id"]: "material" for i in items}
        truth = [i["label"] for i in items]
        client = self._client(truth * 3)

        score = score_judge(client, "perfect", items, windows, repeats=3)

        assert score.kappa == 1.0
        assert score.test_retest == 1.0

    def test_a_lazy_judge_scores_zero_despite_half_right(self):
        items = build_faithfulness_set(FACTS, size=8)
        windows = {i["item_id"]: "material" for i in items}
        client = self._client(["supported"] * 24)

        score = score_judge(client, "lazy", items, windows, repeats=3)

        assert score.accuracy == 0.5
        assert score.kappa == 0.0

    def test_a_failed_call_is_counted_not_hidden(self):
        items = build_faithfulness_set(FACTS, size=4)
        windows = {i["item_id"]: "material" for i in items}
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("provider down")

        score = score_judge(client, "broken", items, windows, repeats=1)

        assert score.errors == len(items)

    def test_position_bias_needs_the_same_winner_both_ways(self):
        """A judge that always says 'A' is measuring position, not truth."""
        items = build_faithfulness_set(FACTS, size=8)
        windows = {i["item_id"]: "material" for i in items}

        always_a = MagicMock()
        always_a.generate_structured.return_value = (
            {"supported_option": "A", "reason": "because"},
            {"cost": 0.0},
        )
        consistency, tested = score_position_bias(always_a, items, windows, pairs=2)

        assert tested == 2
        assert consistency == 0.0

    def test_a_consistent_judge_scores_one(self):
        """Same statement wins whichever slot it sits in."""
        items = build_faithfulness_set(FACTS, size=8)
        windows = {i["item_id"]: "material" for i in items}

        client = MagicMock()
        client.generate_structured.side_effect = [
            ({"supported_option": "A", "reason": ""}, {"cost": 0.0}),
            ({"supported_option": "B", "reason": ""}, {"cost": 0.0}),
        ] * 8
        consistency, tested = score_position_bias(client, items, windows, pairs=2)

        assert consistency == 1.0


class TestSourceWindow:
    """A judge should be answering a faithfulness question, not a search one."""

    def test_the_window_lands_on_the_relevant_passage(self):
        source = (
            "Opening material about something else entirely. " * 40
            + "The Mataha expedition scanned the site in 2008 with the NRIAG institute. "
            + "Closing material about the weather. " * 40
        )

        window = source_window("The Mataha expedition scanned the site in 2008", source, words=60)

        assert "Mataha" in window
        assert len(window.split()) <= 60

    def test_short_sources_are_passed_through_whole(self):
        assert source_window("anything", "a short source", words=60) == "a short source"
