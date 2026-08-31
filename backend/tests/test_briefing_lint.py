"""Tests for the document-level Briefing lint and the style instruments.

Cover for P3 work-order item 15's lint additions and items H19-H23. Three
D-025 rules are about the whole document rather than one passage: names that
recur get a card, sources are named in prose rather than cited by ID inside a
sentence, and staging is disclosed. The statistical instruments and the repair
invariants sit alongside them.
"""
from backend.models.briefing import (
    Anecdote,
    Briefing,
    BriefingMeta,
    File,
    Player,
    Read,
    ReadParagraph,
    RecordEntry,
    SourceTrailEntry,
)
from backend.pipeline.briefing_lint import (
    check_garbled_prose,
    check_inline_introductions,
    check_named_citations,
    check_player_cards,
    check_staging_disclosure,
    lint_briefing,
)
from backend.pipeline.repair_invariants import check_repair_invariants
from backend.pipeline.style_enforcer import check_publish_fingerprints, check_vocabulary
from backend.pipeline.style_stats import measure_style, slop_score


def _approved_sample() -> str:
    """The owner-approved Section 1, which is what "not slop" measures against."""
    with open(
        "plans/260814-claim-graph-briefing/artifacts/APPROVED-SECTION-1-SAMPLE.md"
    ) as handle:
        return handle.read().split("## THE SAMPLE (verbatim from chat)")[1]


def _briefing(**overrides) -> Briefing:
    payload = {
        "job_id": "job-1",
        "topic": "The labyrinth",
        "meta": BriefingMeta(source_count=2, independent_source_count=2, raw_words=100),
        "read": Read(
            lede="Read both.",
            paragraphs=[ReadParagraph(text="Flinders Petrie described the stone bed in 1888.")],
        ),
        "source_trail": [
            SourceTrailEntry(source_id="SRC_1", title="A source"),
            SourceTrailEntry(source_id="SRC_2", title="Another"),
        ],
    }
    payload.update(overrides)
    return Briefing(**payload)


class TestPlayerCards:
    """A name a reader keeps meeting must be somewhere they can look it up."""

    def test_recurring_name_without_a_card_is_an_error(self):
        """Two sections is the threshold, and it is checked, not trusted."""
        briefing = _briefing(
            files=[
                File(
                    title="The excavation",
                    body="Flinders Petrie concluded the chip stratum was demolition debris.",
                    source_ids=["SRC_1"],
                )
            ]
        )

        errors = check_player_cards(briefing)

        assert any("Flinders Petrie" in e for e in errors)

    def test_a_carded_name_passes(self):
        """With a card, the same name is fine."""
        briefing = _briefing(
            files=[
                File(
                    title="The excavation",
                    body="Flinders Petrie concluded the chip stratum was demolition debris.",
                    source_ids=["SRC_1"],
                )
            ],
            players=[
                Player(
                    name="Flinders Petrie",
                    role="excavated Hawara",
                    body="Found the stone bed.",
                    source_ids=["SRC_1"],
                )
            ],
        )

        assert check_player_cards(briefing) == []

    def test_a_one_off_name_needs_no_card(self):
        """One appearance is introduced inline, per the format."""
        briefing = _briefing(
            files=[File(title="A file", body="Eric Uphill argued otherwise.", source_ids=["SRC_1"])]
        )

        assert check_player_cards(briefing) == []


class TestInlineIntroductions:
    """Everyone below the card cap is introduced where the reader meets them."""

    NAMES = [
        "Flinders Petrie", "Eric Uphill", "Alan Lloyd", "Karl Lepsius",
        "Louis De Cordier", "Zahi Hawass", "Carmen Boulter", "Timothy Akers",
        "Trevor Grassi", "William Brown", "Filippo Biondi", "Mark Carlotto",
        "Edgar Cayce", "Graham Hancock", "Lawrence Conyers", "Abbas Mohamed",
        "Johanna Mueller", "Robert Schoch", "John West", "Manly Hall",
    ]

    def _briefing_with_names(self, count, introduced):
        """A Briefing whose sections mention `count` recurring names."""
        def mention(name, section_word):
            return (
                f"{name}, the {section_word} specialist, {section_word} it."
                if introduced
                else f"Later {name} {section_word} it."
            )

        names = self.NAMES[:count]
        return _briefing(
            read=Read(
                lede="Read them.",
                paragraphs=[ReadParagraph(text=" ".join(mention(n, "described") for n in names))],
            ),
            files=[
                File(
                    title="A file",
                    body=" ".join(mention(n, "confirmed") for n in names),
                    source_ids=["SRC_1"],
                )
            ],
        )

    def test_uncarded_recurring_name_needs_an_introduction(self):
        """Below the line, a bare mention is an error."""
        briefing = self._briefing_with_names(20, introduced=False)

        errors = check_inline_introductions(briefing)

        assert errors
        assert "no inline introduction" in errors[0]

    def test_an_introduced_name_passes(self):
        """An appositive where the reader meets the name satisfies the rule."""
        briefing = self._briefing_with_names(20, introduced=True)

        assert check_inline_introductions(briefing) == []

    def test_names_above_the_line_are_not_checked_here(self):
        """Those need cards instead, which is the other rule."""
        briefing = self._briefing_with_names(3, introduced=False)

        assert check_inline_introductions(briefing) == []


class TestNamedCitations:
    """IDs belong in the tag, not the sentence."""

    def test_bare_id_in_prose_is_an_error(self):
        """A leaked ID is the research register showing through."""
        briefing = _briefing(
            files=[
                File(
                    title="The scans",
                    body="SRC_2 reports a grid at eight metres.",
                    source_ids=["SRC_2"],
                )
            ]
        )

        errors = check_named_citations(briefing)

        assert any("SRC_2" in e for e in errors)

    def test_named_citation_passes(self):
        """Naming the source the way a person would is the point."""
        briefing = _briefing(
            files=[
                File(
                    title="The scans",
                    body="Johanna's video reports a grid at eight metres.",
                    source_ids=["SRC_2"],
                )
            ]
        )

        assert check_named_citations(briefing) == []


class TestStagingDisclosure:
    """When a source performs a fact, say where the fact lives."""

    def test_undisclosed_staging_is_an_advisory(self):
        """Reported, not blocking: the detector is a word list."""
        briefing = _briefing(
            anecdotes=[
                Anecdote(
                    text="The Why Files dramatizes Petrie's tunnel collapse as a scene.",
                    source_ids=["SRC_1"],
                )
            ]
        )

        assert check_staging_disclosure(briefing)

    def test_disclosed_staging_passes(self):
        """Saying where the underlying fact lives satisfies the rule."""
        briefing = _briefing(
            anecdotes=[
                Anecdote(
                    text=(
                        "The Why Files dramatizes the tunnel collapse as a scene; the "
                        "underlying account comes from Petrie's own journals."
                    ),
                    source_ids=["SRC_1"],
                )
            ]
        )

        assert check_staging_disclosure(briefing) == []


class TestGarbledProse:
    """Sentences that read as machine-edited. Every fixture is a real one from
    the 2026-08-31 Packer briefing (owner: "that's not a human form of
    reading/writing")."""

    def test_two_descriptions_stacked_on_one_name(self):
        briefing = _briefing(
            read=Read(
                lede=(
                "Walter Birkby, the forensic anthropologist who disputed Starrs, "
                "the forensic anthropologist assisting him, disagreed."
            ),
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        assert any("stacked" in f for f in check_garbled_prose(briefing))

    def test_a_description_inside_a_run_of_names(self):
        briefing = _briefing(
            read=Read(
                lede=(
                "Packer, Israel Swan, Frank Miller, James Humphrey, a prospector "
                "who left camp, and Shannon Bell set out."
            ),
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        assert any("run of names" in f for f in check_garbled_prose(briefing))

    def test_a_phrase_the_sentence_says_twice(self):
        briefing = _briefing(
            read=Read(
                lede=(
                "They were drawn by reports of enormous fortunes, and the paper "
                "promised tales of enormous fortunes for the asking."
            ),
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        assert any("repeats itself" in f for f in check_garbled_prose(briefing))

    def test_grammar_words_repeating_are_not_reported(self):
        """"that he was" twice is grammar, not a stutter."""
        briefing = _briefing(
            read=Read(
                lede="He said that he was cold and that he was hungry that night.",
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        assert not any("repeats itself" in f for f in check_garbled_prose(briefing))

    def test_a_sentence_opener_is_not_read_as_a_name(self):
        """"Afterward, the six men were no longer seen together, and Packer ..."
        is ordinary prose."""
        briefing = _briefing(
            read=Read(
                lede=(
                "Afterward, the six men were no longer seen together, and Packer "
                "reached the agency alone."
            ),
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        assert check_garbled_prose(briefing) == []

    def test_clean_prose_passes(self):
        briefing = _briefing(
            read=Read(
                lede="Packer reached the agency on 16 April 1874.",
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        assert check_garbled_prose(briefing) == []

    def test_findings_are_advisories_not_errors(self):
        """A reader decides whether a sentence reads badly, so this never
        blocks a build."""
        briefing = _briefing(
            read=Read(
                lede=(
                "Walter Birkby, the forensic anthropologist who disputed Starrs, "
                "the forensic anthropologist assisting him, disagreed."
            ),
                paragraphs=[ReadParagraph(text="A paragraph.")],
            )
        )
        result = lint_briefing(briefing)
        assert any("stacked" in a for a in result.advisories)
        assert not any("stacked" in e for e in result.errors)


class TestLintBriefing:
    """Errors block, advisories report."""

    def test_clean_briefing_passes(self):
        """Nothing to say about a document that follows the rules."""
        result = lint_briefing(_briefing())

        assert result.passes
        assert result.errors == []

    def test_errors_block_and_advisories_do_not(self):
        """The two tiers behave differently, which is the whole point."""
        briefing = _briefing(
            record=[
                RecordEntry(
                    when="1888",
                    what="SRC_1 says Petrie dug here.",
                    source_ids=["SRC_1"],
                )
            ],
            anecdotes=[
                Anecdote(text="The video re-enacts the collapse.", source_ids=["SRC_1"])
            ],
        )

        result = lint_briefing(briefing)

        assert not result.passes
        assert result.advisories


class TestStyleInstruments:
    """Measurements that phrase lists cannot make."""

    def test_marching_sentences_are_detected(self):
        """The enumerate-and-march tell has no vocabulary; it has a variance."""
        march = "The first point is here. The second point is here. The third point is here. " * 4

        stats = measure_style(march)

        assert stats.sentence_length_stdev < 4
        assert any("barely varies" in f for f in stats.findings)

    def test_human_prose_scores_low(self):
        """The owner-approved sample is the calibration."""
        assert slop_score(_approved_sample()) < 15

    def test_slop_score_moves_with_the_signals(self):
        """The number is only useful if it separates the two cases."""
        march = "The first point is here. The second point is here. The third point is here. " * 4

        assert slop_score(march) >= slop_score(_approved_sample()) + 20

    def test_vocabulary_advisories(self):
        """Curated patterns, advisory because each is sometimes right."""
        findings = check_vocabulary(
            "The scan serves as a testament to a pivotal moment. It is worth noting this."
        )

        assert any("copula avoidance" in f for f in findings)
        assert any("significance inflation" in f for f in findings)
        assert any("false hedging" in f for f in findings)

    def test_publish_fingerprints_are_errors(self):
        """A placeholder or a tracking parameter in published text is a defect."""
        findings = check_publish_fingerprints(
            "Read more at https://example.com/?utm_source=newsletter [TODO]"
        )

        assert len(findings) == 2


class TestRepairInvariants:
    """A repair may fix voice; it may never touch a fact."""

    def test_reordering_a_sentence_is_allowed(self):
        """Voice is what repair is for."""
        report = check_repair_invariants(
            "Petrie found 3,000 chambers in 1888.", "In 1888, Petrie found 3,000 chambers."
        )

        assert report.holds

    def test_changing_a_number_is_caught(self):
        """The failure that reads better and says something else."""
        report = check_repair_invariants(
            "Petrie found 3,000 chambers.", "Petrie found 300 chambers."
        )

        assert not report.holds
        assert report.lost_numbers == ["3000"]

    def test_trimming_a_quote_is_caught(self):
        """A shortened quotation is no longer a quotation."""
        report = check_repair_invariants(
            'He wrote "greater than words can say" there.',
            'He wrote "greater than words" there.',
        )

        assert not report.holds
        assert report.lost_quotes

    def test_dropping_a_citation_id_is_caught(self):
        """Provenance cannot be tidied away."""
        report = check_repair_invariants("The scans (SRC_2) found a grid.", "The scans found a grid.")

        assert not report.holds
        assert report.lost_ids == ["SRC_2"]

    def test_summary_reads_as_a_sentence(self):
        """Whoever sees this in a log should understand it immediately."""
        assert "no fact changed" in check_repair_invariants("a 1 b", "b 1 a").summary()
