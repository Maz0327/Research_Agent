"""Tests for the grounding repair round (D-036).

The pass fixes facts the corpus does not contain. What these tests guard hardest
is the failure discovered while building it: the grounding gate raises false
alarms on name variants ("King Tut" in the source, "Tutankhamun" in the prose)
and character differences ("Rosæ" vs "Rosae"), and the first version of this
repair obediently DELETED those true statements. A wrongly deleted fact is worse
than a flagged one, so the model is given the source and allowed to overrule the
checker.
"""
from unittest.mock import MagicMock

from backend.models.briefing import Briefing, BriefingMeta, Read, ReadParagraph
from backend.pipeline.briefing_gates import GateFinding, GateReport
from backend.pipeline.grounding_repair import apply_repair, repair_grounding

CORPUS = [
    "Flinders Petrie excavated at Hawara in 1888. Herodotus wrote that the "
    "labyrinth held three thousand chambers. The team reached the water table "
    "at eight metres."
]


def _briefing(lede, paragraph="A paragraph about the dig at Hawara."):
    return Briefing(
        job_id="J",
        topic="The Hawara labyrinth",
        meta=BriefingMeta(source_count=1, independent_source_count=1, raw_words=50),
        read=Read(lede=lede, paragraphs=[ReadParagraph(text=paragraph)]),
    )


def _report(where, *atoms):
    return GateReport(
        name="grounding",
        checked=10,
        findings=[GateFinding(kind="number", value=a, where=where) for a in atoms],
    )


def _client(*repairs):
    client = MagicMock()
    client.generate_structured.return_value = ({"repairs": list(repairs)}, {})
    return client


class TestApplyRepair:
    """The three actions, applied by code."""

    def test_a_wrong_figure_is_corrected_in_place(self):
        out, changed = apply_repair(
            "The site held 9,000 chambers.", "9,000", "correct", "3,000"
        )
        assert out == "The site held 3,000 chambers." and changed

    def test_an_unsupported_clause_is_cut_and_the_sentence_still_reads(self):
        out, changed = apply_repair(
            "Petrie dug at Hawara, funded by a secret trust, in 1888.",
            "secret trust",
            "cut",
            ", funded by a secret trust,",
        )
        assert out == "Petrie dug at Hawara in 1888." and changed

    def test_a_paraphrased_cut_falls_back_to_the_whole_sentence(self):
        """The model does not always copy the fragment verbatim. The fallback is
        coarser but never leaves the invention standing."""
        out, changed = apply_repair(
            "Petrie dug at Hawara. A secret trust paid for it. He published in 1889.",
            "secret trust",
            "cut",
            "the trust that was secret",
        )
        assert "secret trust" not in out
        assert "He published in 1889." in out and changed

    def test_keep_changes_nothing(self):
        text = "Tutankhamun's tomb was found in 1923."
        assert apply_repair(text, "Tutankhamun", "keep", "") == (text, False)


class TestFalseAlarms:
    """The defect that nearly shipped."""

    def test_a_name_variant_is_kept_not_deleted(self):
        """The source says "King Tut", the prose says "Tutankhamun". The text
        matcher cannot see they are the same person; the model can."""
        briefing = _briefing("Tutankhamun's tomb was found in 1923.")
        result = repair_grounding(
            briefing,
            _report("read.lede", "Tutankhamun"),
            ["The tomb of King Tut was discovered in 1923."],
            _client({"atom": "Tutankhamun", "action": "keep", "replacement": ""}),
        )
        assert result["overruled"] == ["Tutankhamun"]
        assert result["applied"] == []
        assert "Tutankhamun" in briefing.read.lede

    def test_a_genuine_invention_is_still_repaired(self):
        briefing = _briefing("Herodotus counted 9,000 chambers there.")
        result = repair_grounding(
            briefing,
            _report("read.lede", "9,000"),
            CORPUS,
            _client({"atom": "9,000", "action": "correct", "replacement": "three thousand"}),
        )
        assert len(result["applied"]) == 1
        assert "9,000" not in briefing.read.lede


class TestRoundBehaviour:
    """One round, and what it does when it cannot finish."""

    def test_nothing_ungrounded_means_no_call(self):
        client = MagicMock()
        result = repair_grounding(_briefing("A clean lede."), GateReport(name="g"), CORPUS, client)
        assert result["ran"] is False
        client.generate_structured.assert_not_called()

    def test_an_atom_the_model_ignores_stays_flagged(self):
        """Silence is not a repair — the finding survives for a human."""
        briefing = _briefing("Herodotus counted 9,000 chambers there.")
        result = repair_grounding(
            briefing, _report("read.lede", "9,000"), CORPUS, _client()
        )
        assert result["unresolved"] == ["9,000"]
        assert "9,000" in briefing.read.lede

    def test_a_failed_call_leaves_the_document_untouched(self):
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("provider down")
        briefing = _briefing("Herodotus counted 9,000 chambers there.")
        result = repair_grounding(briefing, _report("read.lede", "9,000"), CORPUS, client)
        assert result["ran"] is False
        assert "9,000" in briefing.read.lede

    def test_repairs_reach_read_paragraphs_too(self):
        briefing = _briefing("A lede.", "The shaft ran to 40 metres below the sand.")
        repair_grounding(
            briefing,
            _report("read.paragraphs[0]", "40"),
            CORPUS,
            _client({"atom": "40", "action": "correct", "replacement": "eight"}),
        )
        assert "eight metres" in briefing.read.paragraphs[0].text
