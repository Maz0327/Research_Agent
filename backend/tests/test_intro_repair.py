"""Tests for the inline-introduction repair round (section J pass 8).

The repair works by pairs applied by code (D-024): the model writes a gloss,
code splices it in, and the model never sees the document back. These tests pin
the splice's grammar — the failures found on the real Briefing were all
grammatical, not factual — and the rule that an unfixable name stays flagged
rather than being given an invented credential.
"""
from unittest.mock import MagicMock

from backend.models.briefing import Briefing, BriefingMeta, File, Read, ReadParagraph
from backend.pipeline.briefing_lint import _is_introduced, lint_briefing
from backend.pipeline.intro_repair import (
    apply_introductions,
    first_appearance,
    repair_inline_introductions,
    splice,
)

GLOSS = "the geologist who dated the Sphinx"


def _briefing(lede="A lede sentence about the dig.", paragraphs=(), files=()):
    return Briefing(
        job_id="JOB_1",
        topic="The Hawara labyrinth",
        meta=BriefingMeta(source_count=1, independent_source_count=1, raw_words=100),
        read=Read(
            lede=lede,
            paragraphs=[ReadParagraph(text=t) for t in (paragraphs or ["A paragraph."])],
        ),
        files=[File(title=f"File {i}", body=b) for i, b in enumerate(files)],
    )


class TestSpliceGrammar:
    """Every one of these was a real defect found on the Hawara Briefing."""

    def test_the_gloss_lands_between_commas(self):
        out, changed = splice("Then Robert Schoch spoke.", "Robert Schoch", GLOSS)
        assert out == f"Then Robert Schoch, {GLOSS}, spoke."
        assert changed is True

    def test_an_existing_comma_is_reused_not_doubled(self):
        """The first version produced "Akers the researcher,," — no opening
        comma and two closing ones.

        Checked outside a name list: as of the owner ruling of 2026-08-31 a
        gloss never goes inside a run of names, so the original fixture for
        this case is now covered by TestPackerDefects instead."""
        out, _ = splice("Then Robert Schoch, who wrote it, spoke.", "Robert Schoch", GLOSS)
        assert ",," not in out

    def test_a_possessive_takes_the_gloss_in_front(self):
        """"Robert Schoch, the geologist,'s findings" is not English."""
        out, _ = splice("Robert Schoch's findings stand.", "Robert Schoch", GLOSS)
        assert "'s findings" in out
        assert ",'s" not in out
        assert out.startswith(GLOSS)

    def test_a_later_plain_mention_is_preferred_over_the_possessive(self):
        out, _ = splice(
            "Robert Schoch's view, and later Robert Schoch wrote more.",
            "Robert Schoch",
            GLOSS,
        )
        assert out.startswith("Robert Schoch's view")
        assert f"Robert Schoch, {GLOSS}, wrote more" in out

    def test_every_spliced_form_satisfies_the_lint(self):
        """The repair and the check have to agree, or the round never converges.

        Only where the repair acts: a name it declines to gloss stays flagged,
        which the module docstring calls the correct outcome.
        """
        for text in (
            "Then Robert Schoch spoke.",
            "Brown and Grassi went, and Robert Schoch followed.",
            "Robert Schoch's findings stand.",
        ):
            out, changed = splice(text, "Robert Schoch", GLOSS)
            assert changed is True, text
            assert _is_introduced(out, out.index("Robert Schoch"), "Robert Schoch"), out

    def test_an_already_introduced_name_is_left_alone(self):
        text = f"Robert Schoch, {GLOSS}, spoke."
        assert splice(text, "Robert Schoch", GLOSS) == (text, False)

    def test_an_empty_gloss_changes_nothing(self):
        """The model returning nothing is the honest path, not a repair."""
        assert splice("Robert Schoch spoke.", "Robert Schoch", "") == (
            "Robert Schoch spoke.",
            False,
        )


class TestPackerDefects:
    """Three splice failures found live on the 2026-08-31 Packer briefing."""

    def test_a_long_existing_appositive_is_not_doubled(self):
        """The guard only looked 40 characters ahead, so a long appositive lost
        its closing comma to the truncation and the name was glossed twice:
        "Walter Birkby, the forensic anthropologist who disputed Starrs, the
        forensic anthropologist assisting him, disagreed."."""
        text = "Walter Birkby, the forensic anthropologist assisting him, disagreed."
        assert _is_introduced(text, text.index("Walter Birkby"), "Walter Birkby")
        _, changed = splice(text, "Walter Birkby", GLOSS)
        assert changed is False

    def test_no_gloss_inside_a_run_of_names(self):
        """A gloss between list commas reads as another item: five men became
        six on the Packer roster."""
        text = (
            "On February 9, Packer, Israel Swan, George Noon, Frank Miller, "
            "James Humphrey, and Shannon Wilson Bell left camp."
        )
        _, changed = splice(text, "James Humphrey", "a prospector who left camp")
        assert changed is False

    def test_a_list_is_protected_wherever_it_starts(self):
        """The guard used to need a comma before the first sibling, so the
        second name of a list was glossed and the fifth was not."""
        for text in (
            "Brown, Robert Schoch, and Grassi",
            "The men were Brown, Robert Schoch, and Grassi",
        ):
            _, changed = splice(text, "Robert Schoch", GLOSS)
            assert changed is False, text

    def test_two_adjacent_names_are_not_a_list(self):
        """The guard needs siblings on both sides; one neighbour is prose."""
        out, changed = splice(
            "Packer, Israel Swan had argued about rations.", "Israel Swan", GLOSS
        )
        assert changed is True
        assert f"Israel Swan, {GLOSS}," in out

    def test_a_gloss_that_restates_the_sentence_is_skipped(self):
        """"Robert McGrue, leader of the larger prospecting party, led the
        larger party" is a stutter the lint cannot see, because the appositive
        is well formed."""
        _, changed = splice(
            "Robert McGrue led the larger party.",
            "Robert McGrue",
            "leader of the larger prospecting party",
        )
        assert changed is False

    def test_an_unrelated_gloss_still_lands(self):
        out, changed = splice(
            "The panel met three times. Jack Ruina chaired it.",
            "Jack Ruina",
            "the MIT engineer",
        )
        assert changed is True
        assert "Jack Ruina, the MIT engineer, chaired it." in out


class TestContextWindow:
    """The gloss writer must see the name it is being asked about."""

    def test_the_passage_is_a_window_around_the_name(self):
        """Handing over the section's opening instead meant the model was asked
        about someone the passage never mentioned, and six of ten names came
        back empty."""
        filler = "Filler sentence about the excavation. " * 60
        briefing = _briefing(paragraphs=[filler + "Then Robert Schoch spoke."])
        passage = first_appearance(briefing, "Robert Schoch")
        assert "Robert Schoch" in passage
        assert len(passage) < len(filler)

    def test_a_name_that_never_appears_has_no_passage(self):
        assert first_appearance(_briefing(), "Nobody Here") is None


class TestSectionCoverage:
    """The rule is per section: a reader jumping to The Files saw no earlier gloss."""

    def test_the_gloss_is_applied_in_every_section_the_name_appears_in(self):
        briefing = _briefing(
            paragraphs=["Then Robert Schoch spoke."],
            files=["Robert Schoch published on the site."],
        )
        applied = apply_introductions(briefing, {"Robert Schoch": GLOSS})
        assert len(applied) == 2
        assert GLOSS in briefing.read.paragraphs[0].text
        assert GLOSS in briefing.files[0].body


class TestRepairRound:
    """One round, and what happens when it cannot finish."""

    def _client(self, people=True, gloss=GLOSS):
        client = MagicMock()

        def answer(**kwargs):
            if "sorting names" in kwargs["system"]:
                names = [
                    line[2:]
                    for line in kwargs["prompt"].splitlines()
                    if line.startswith("- ")
                ]
                kind = "person" if people else "organisation"
                return ({"names": [{"name": n, "kind": kind} for n in names]}, {})
            names = [
                line.split("name: ", 1)[1]
                for line in kwargs["prompt"].splitlines()
                if line.startswith("name: ")
            ]
            return (
                {"introductions": [{"name": n, "introduction": gloss} for n in names]},
                {},
            )

        client.generate_structured.side_effect = answer
        return client

    def test_a_name_classified_as_not_a_person_is_exempt(self):
        """"Synthetic Aperture Radar, who is..." is the failure this prevents."""
        briefing = _briefing(
            paragraphs=["Synthetic Aperture Radar reported a void beneath the site."],
            files=["Synthetic Aperture Radar reported a second void there."],
        )
        result = repair_inline_introductions(briefing, self._client(people=False), maximum=0)
        assert result["applied"] == []
        assert GLOSS not in briefing.files[0].body

    def test_a_name_the_round_cannot_introduce_stays_flagged(self):
        """Inventing a credential to clear a lint error is the worse failure."""
        briefing = _briefing(
            paragraphs=["Then Robert Schoch spoke about the dig at Hawara."],
            files=["Robert Schoch published a paper on the site at Hawara."],
        )
        result = repair_inline_introductions(briefing, self._client(gloss=""), maximum=0)
        assert result["applied"] == []
        assert result["unresolved"] == ["Robert Schoch"]
        assert lint_briefing(briefing, people={"Robert Schoch"}).errors

    def test_a_repaired_briefing_passes_the_lint_it_was_repairing(self):
        briefing = _briefing(
            paragraphs=["Then Robert Schoch spoke about the dig at Hawara."],
            files=["Robert Schoch published a paper on the site at Hawara."],
        )
        result = repair_inline_introductions(briefing, self._client(), maximum=0)
        remaining = [
            e for e in lint_briefing(briefing, people=set(result["people"])).errors
            if "inline introduction" in e
        ]
        assert remaining == []
