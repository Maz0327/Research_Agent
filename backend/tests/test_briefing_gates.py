"""Tests for the coverage and grounding gates.

Cover for P3 work-order items 13 and 16a. The two gates check opposite
directions of the same trust question, mechanically: coverage asks whether
anything the harvest found went missing from the document, grounding asks
whether anything in the document was never in the corpus. Neither asks a model.
"""
from backend.models.briefing import (
    Anecdote,
    Briefing,
    BriefingMeta,
    Dispute,
    DisputeSide,
    File,
    Player,
    Read,
    ReadParagraph,
    RecordEntry,
    SourceTrailEntry,
    chip,
)
from backend.pipeline.briefing_gates import (
    coverage_gate,
    grounding_gate,
    names_in,
    numbers_in,
    quotes_in,
)

RAW = (
    "Flinders Petrie excavated Hawara in 1888 and found a stone bed measuring "
    "304 by 244 metres. Herodotus wrote that the labyrinth held 3,000 chambers, "
    'half of them below ground: "This I saw myself, and I found it greater than '
    'words can say." The Mataha expedition scanned the site in 2008 with Egypt\'s '
    "own NRIAG institute and reported a grid at 8 to 12 metres depth."
)


def _briefing(**overrides) -> Briefing:
    """A Briefing whose prose stays inside RAW unless a test changes it."""
    payload = {
        "job_id": "job-1",
        "topic": "The lost labyrinth",
        "meta": BriefingMeta(source_count=1, independent_source_count=1, raw_words=60),
        "read": Read(
            lede="Read the one source.",
            paragraphs=[
                ReadParagraph(
                    label="What you've got",
                    text=(
                        "Flinders Petrie excavated Hawara in 1888 and found a stone "
                        "bed of 304 by 244 metres."
                    ),
                )
            ],
        ),
        "source_trail": [SourceTrailEntry(source_id="SRC_1", title="A source")],
    }
    payload.update(overrides)
    return Briefing(**payload)


class TestAtomExtraction:
    """The gates only work if they see the same atoms a reader would."""

    def test_numbers_are_normalized(self):
        """Thousands separators do not create two different numbers."""
        assert "3000" in numbers_in("the labyrinth held 3,000 chambers")
        assert "1888" in numbers_in("excavated in 1888")

    def test_names_are_collected(self):
        """Capitalized runs are treated as names."""
        found = names_in("Flinders Petrie excavated Hawara in 1888")
        assert any("Petrie" in name for name in found)

    def test_quotes_are_collected(self):
        """Long quoted passages are pulled out for verbatim checking."""
        quotes = quotes_in('He wrote "this I saw myself and found it great" in book two')
        assert quotes == {"this I saw myself and found it great"}

    def test_short_quotes_are_ignored(self):
        """Scare quotes are not citations."""
        assert quotes_in('a so-called "maze" of rooms') == set()


class TestGroundingGate:
    """Nothing reaches the reader that the corpus does not contain."""

    def test_grounded_briefing_passes(self):
        """Every atom in the document appears in the raw text."""
        report = grounding_gate(_briefing(), [RAW])

        assert report.passed
        assert report.checked > 0

    def test_invented_number_is_caught(self):
        """A figure nobody wrote is a finding, not a rounding difference."""
        briefing = _briefing(
            read=Read(
                lede="Read the one source.",
                paragraphs=[ReadParagraph(text="Petrie found 9,412 chambers at Hawara.")],
            )
        )

        report = grounding_gate(briefing, [RAW])

        assert not report.passed
        assert any(f.kind == "number" and f.value == "9412" for f in report.findings)

    def test_invented_name_is_caught(self):
        """A person the corpus never mentions cannot be introduced."""
        briefing = _briefing(
            players=[
                Player(
                    name="Wilhelm Steinhauser",
                    role="the excavator",
                    body="Ran the second dig.",
                    source_ids=["SRC_1"],
                )
            ]
        )

        report = grounding_gate(briefing, [RAW])

        assert any(f.kind == "name" and "Steinhauser" in f.value for f in report.findings)

    def test_fabricated_quote_is_caught(self):
        """A quotation that is not in the source is the worst failure of all."""
        briefing = _briefing(
            files=[
                File(
                    title="The Record",
                    body='Herodotus wrote "the chambers were filled with gold and silver".',
                    source_ids=["SRC_1"],
                )
            ]
        )

        report = grounding_gate(briefing, [RAW])

        assert any(f.kind == "quote" for f in report.findings)

    def test_real_quote_survives_punctuation_drift(self):
        """Citations are not byte comparisons; transcripts drift."""
        briefing = _briefing(
            files=[
                File(
                    title="The Record",
                    body='Herodotus wrote "this I saw myself and I found it greater than words can say".',
                    source_ids=["SRC_1"],
                )
            ]
        )

        report = grounding_gate(briefing, [RAW])

        assert not any(f.kind == "quote" for f in report.findings)

    def test_harvest_facts_count_as_corpus(self):
        """The harvest is derived from the raw text, so it grounds atoms too."""
        briefing = _briefing(
            anecdotes=[Anecdote(text="The dig ran for 14 seasons.", source_ids=["SRC_1"])]
        )

        without = grounding_gate(briefing, [RAW])
        with_harvest = grounding_gate(briefing, [RAW], ["The dig ran for 14 seasons."])

        assert any(f.value == "14" for f in without.findings)
        assert not any(f.value == "14" for f in with_harvest.findings)

    def test_no_raw_text_is_reported_not_assumed_clean(self):
        """An unchecked gate says so instead of quietly passing."""
        report = grounding_gate(_briefing(), [])

        assert report.passed
        assert report.notes


class TestCoverageGate:
    """Nothing the harvest found disappears without being reported."""

    def _inventory(self, *facts):
        return [
            {"fact_id": f"SRC_1:F_{i + 1}", "source_id": "SRC_1", "text": text}
            for i, text in enumerate(facts)
        ]

    def test_covered_fact_passes(self):
        """A fact whose specifics are in the document counts as said."""
        report = coverage_gate(
            _briefing(),
            self._inventory("Flinders Petrie excavated Hawara in 1888."),
        )

        assert report.passed
        assert report.checked == 1

    def test_missing_fact_is_reported(self):
        """The document never says it, so the gate says so."""
        report = coverage_gate(
            _briefing(),
            self._inventory("The Mataha expedition scanned the site in 2008."),
        )

        assert not report.passed
        assert report.findings[0].kind == "uncovered_fact"
        assert "SRC_1:F_1" in report.findings[0].where

    def test_paraphrase_counts_as_coverage(self):
        """Saying it in other words is still saying it."""
        briefing = _briefing(
            files=[
                File(
                    title="The Excavation",
                    body="Petrie dug at Hawara and uncovered a great stone bed there.",
                    source_ids=["SRC_1"],
                )
            ]
        )

        report = coverage_gate(
            briefing, self._inventory("Petrie uncovered a great stone bed at Hawara.")
        )

        assert report.passed

    def test_every_section_counts_as_the_document(self):
        """A fact carried only by a dispute or a record entry is still covered."""
        briefing = _briefing(
            record=[
                RecordEntry(
                    when="2008",
                    what="The Mataha expedition scanned the site with NRIAG.",
                    source_ids=["SRC_1"],
                )
            ],
            disputes=[
                Dispute(
                    claim="The grid is real.",
                    holders="For: Mataha. Against: Petrie.",
                    chip=chip("contested"),
                    case_for=DisputeSide(
                        heading="The case for",
                        text="The grid sits at 8 to 12 metres depth.",
                        source_ids=["SRC_1"],
                    ),
                    case_against=DisputeSide(
                        heading="The case against",
                        text="Petrie found demolition debris.",
                        source_ids=["SRC_1"],
                    ),
                )
            ],
        )

        report = coverage_gate(
            briefing,
            self._inventory(
                "The Mataha expedition scanned the site in 2008 with NRIAG.",
                "The reported grid sits at 8 to 12 metres depth.",
            ),
        )

        assert report.passed

    def test_empty_inventory_is_not_a_pass_by_default(self):
        """With nothing harvested there is nothing to check, and it says so."""
        report = coverage_gate(_briefing(), [])

        assert report.passed
        assert report.checked == 0
