"""Tests for the cold-reader read regression (work order I.30).

The instrument's value is that it separates two things a single score hides:
whether the reader retained what the Briefing establishes, and whether what
they came away saying is true. A reader who is confident and wrong scores well
on the first and badly on the second, and that is the result worth catching.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock

from backend.models.briefing import (
    Briefing,
    BriefingMeta,
    Chip,
    Dispute,
    DisputeSide,
    Player,
    Read,
    ReadParagraph,
)
from backend.pipeline.read_regression import (
    COLD_READER_QUESTIONS,
    expected_content,
    read_only_text,
    read_regression,
    score_coverage,
    score_grounding,
)

CORPUS = (
    "Flinders Petrie excavated at Hawara in 1888 and reported a great structure. "
    "Herodotus described a labyrinth of 3000 chambers beside the pyramid. "
    "The survey team reported readings at 8 metres depth."
)


def _briefing(players=("Flinders Petrie", "Herodotus"), disputes=("Does the labyrinth exist?",)):
    """Build a Briefing with a Read a cold reader could actually be given."""
    return Briefing(
        job_id="JOB_1",
        topic="The Hawara labyrinth",
        meta=BriefingMeta(source_count=2, independent_source_count=2, raw_words=500),
        read=Read(
            lede="Flinders Petrie dug at Hawara in 1888.",
            paragraphs=[
                ReadParagraph(text="Herodotus described 3000 chambers beside the pyramid.")
            ],
        ),
        players=[Player(name=n, role="A role", body="A card body.") for n in players],
        disputes=[
            Dispute(
                claim=c,
                holders="Two camps",
                chip=Chip(label="contested"),
                case_for=DisputeSide(heading="For", text="The case for."),
                case_against=DisputeSide(heading="Against", text="The case against."),
            )
            for c in disputes
        ],
    )


class TestWhatTheReaderSees:
    """The reader gets Section 1 and nothing else — that is the whole test."""

    def test_only_section_one_is_handed_over(self):
        text = read_only_text(_briefing())
        assert "Flinders Petrie dug at Hawara" in text
        assert "A card body" not in text
        assert "The case for" not in text

    def test_the_question_set_is_fixed(self):
        """A moving question set makes the trend line meaningless."""
        assert len(COLD_READER_QUESTIONS) == 5
        assert COLD_READER_QUESTIONS[0].startswith("What is this about")


class TestCoverage:
    """How much of what the Briefing establishes the reader retained."""

    def test_a_reader_who_retained_everything_scores_one(self):
        expected = expected_content(_briefing())
        score = score_coverage(
            "It is about Flinders Petrie and Herodotus, and whether the "
            "labyrinth exists at all.",
            expected,
        )
        assert score["players"]["rate"] == 1.0
        assert score["disputes"]["rate"] == 1.0

    def test_a_surname_counts_as_retaining_the_person(self):
        """A reader who says "Petrie" has retained "Flinders Petrie"."""
        score = score_coverage("Petrie dug there.", {"players": ["Flinders Petrie"]})
        assert score["players"]["rate"] == 1.0

    def test_the_people_the_reader_lost_are_named(self):
        """A rate alone cannot be acted on; the missing names can."""
        score = score_coverage(
            "It is about Herodotus.", {"players": ["Flinders Petrie", "Herodotus"]}
        )
        assert score["players"]["missed"] == ["Flinders Petrie"]
        assert score["players"]["rate"] == 0.5

    def test_an_empty_category_scores_none_not_zero(self):
        """No disputes to retain is not a failure to retain them."""
        score = score_coverage("Anything.", {"players": [], "disputes": []})
        assert score["players"]["rate"] is None
        assert score["overall"] is None


class TestGrounding:
    """Whether what the reader came away saying is actually true."""

    def test_a_reader_repeating_the_corpus_is_fully_grounded(self):
        score = score_grounding("Petrie dug at Hawara in 1888.", CORPUS)
        assert score["ungrounded"] == 0

    def test_a_figure_the_corpus_never_gives_is_caught(self):
        """The dangerous result: confident and wrong."""
        score = score_grounding("There were 9000 chambers under the site.", CORPUS)
        assert "9000" in score["items"]
        assert score["ungrounded_rate"] > 0

    def test_a_fabricated_quote_is_caught(self):
        score = score_grounding(
            'Petrie wrote that "the chambers ran for miles beneath the sand".', CORPUS
        )
        assert score["ungrounded"] >= 1


class TestHarness:
    """Running it, and the trend line."""

    def _client(self, answer):
        client = MagicMock()
        client.generate_structured.return_value = (
            {"answers": [{"question": q, "answer": answer} for q in COLD_READER_QUESTIONS]},
            {},
        )
        return client

    def test_a_failed_reader_call_reports_not_run_rather_than_zero(self):
        """A dead provider must not read as a Briefing nobody could understand."""
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("provider down")
        result = read_regression(_briefing(), CORPUS, client)
        assert result["ran"] is False

    def test_the_trend_records_and_then_reports_a_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            good = "Petrie and Herodotus, and whether the labyrinth exists."
            first = read_regression(_briefing(), CORPUS, self._client(good), path)
            assert first["trend"]["runs"] == 1
            assert first["trend"]["coverage_delta"] is None

            worse = read_regression(
                _briefing(), CORPUS, self._client("It is about Herodotus."), path
            )
            assert worse["trend"]["runs"] == 2
            assert worse["trend"]["coverage_delta"] < 0

            with open(path) as handle:
                assert len(json.load(handle)) == 2

    def test_an_unreadable_history_starts_fresh_rather_than_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            with open(path, "w") as handle:
                handle.write("{ not json")
            result = read_regression(
                _briefing(), CORPUS, self._client("Petrie and Herodotus."), path
            )
            assert result["trend"]["runs"] == 1
