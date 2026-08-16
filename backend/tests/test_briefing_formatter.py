"""Tests for the Shape B Briefing renderer and the lint that gates it.

Decision 024: named stories with details woven in, self-contained sections,
no cross-references, nothing chosen for the reader. The lint is part of the
render test: a Briefing that trips a voice law fails here, not in front of
the owner.
"""

import pytest

from backend.models.claim_graph import ClaimGraph
from backend.pipeline.formatters.briefing_formatter import (
    _clean_topic,
    confidence_bar,
    render_briefing,
)
from backend.pipeline.style_enforcer import lint_rendered_document

SOURCE_TITLES = {
    "SRC_1": "Why don't movies look like *movies* anymore?",
    "SRC_2": "The Colorist's Complaint",
}


def _graph_dict(**overrides) -> dict:
    claims = []
    for i in range(1, 9):
        claims.append(
            {
                "id": f"CLM_{i}",
                "title": f"The look changed for reason number {i}.",
                "what_sources_say": "The camera and the money ended up telling the same story here.",
                "pushback": None,
                "my_read": None,
                "say_it_like": f"Here is the {i} of it, out loud.",
                "confidence": {
                    "grade": 4 if i <= 2 else 2,
                    "reason": "Two separate sources, quotes unverified.",
                },
                "evidence_status": "multi_source" if i <= 2 else "one_source",
                "evidence": [{"source_id": "SRC_1"}]
                if i > 2
                else [{"source_id": "SRC_1"}, {"source_id": "SRC_2"}],
                "story_goods": [],
                "spine_order": i,
                "tags": [],
            }
        )

    graph = {
        "graph_version": "1",
        "job_id": "job-1",
        "topic": "research why films look flat now",
        "thesis": {
            "text": "The look changed because the money changed.",
            "confidence": "usable",
            "based_on": ["CLM_1"],
        },
        "claims": claims,
        "story_goods": [],
        "holes": [
            {
                "id": "HOLE_1",
                "attached_to": "CLM_1",
                "missing": "Nobody asked a working colorist about any of this.",
                "hurts_because": "The whole case is outsiders describing insiders.",
                "severity": 4,
                "how_to_fill": "Trade interviews with colorists around big releases.",
            },
        ],
        "sections": [
            {
                "id": "STY_1",
                "title": "The money might explain the cameras",
                "body": (
                    "Budgets are tight, schedules are brutal, and finance "
                    "calls the shots while the people who own the look get "
                    "squeezed out of the room.\n\n"
                    "Hold that next to the camera complaints and the story "
                    "flips: it stops being about taste and becomes about "
                    "economics. Nobody in the sources says this in one place. "
                    "You'd be the one assembling it."
                ),
                "claim_ids": ["CLM_1", "CLM_2"],
                "is_connection": True,
            },
            {
                "id": "STY_2",
                "title": "Even the old classics might be getting flattened",
                "body": (
                    "Buried in one essay is the wildest claim in the pile: "
                    "remasters run old films through the modern pipeline and "
                    "the flatness infects them too. Only one person says this, "
                    "so you'd be carrying it alone."
                ),
                "claim_ids": ["CLM_3"],
                "is_connection": False,
            },
        ],
        "noticings": [
            {
                "text": "The big scenes all happen in rain and darkness, on purpose.",
                "claim_ids": ["CLM_4"],
            }
        ],
        "landscape": {
            "everyone_does": (
                "The worn path is the practical-effects fairy tale, told a "
                "thousand times."
            ),
            "nobody_has": (
                "The economics-drove-the-image version is sitting in this "
                "material, unassembled."
            ),
        },
        "sources_ranked": [
            {"source_id": "SRC_1", "role": "backbone", "note": None},
            {"source_id": "SRC_2", "role": "color", "note": None},
        ],
    }
    graph.update(overrides)
    return graph


@pytest.fixture
def briefing() -> str:
    return render_briefing(ClaimGraph.model_validate(_graph_dict()), SOURCE_TITLES)


class TestShape:
    def test_sections_render_as_full_sentence_headers(self, briefing):
        assert "## The money might explain the cameras" in briefing
        assert "## Even the old classics might be getting flattened" in briefing

    def test_no_claim_unit_anatomy(self, briefing):
        """The repeated field labels were the wall-of-text disease."""
        for label in (
            "**What the sources say:**",
            "**My read:**",
            "**How sure:**",
            "*Say it like:*",
            "**The pushback:**",
        ):
            assert label not in briefing

    def test_no_confidence_bars_in_body(self, briefing):
        assert "▮" not in briefing

    def test_section_bodies_keep_their_paragraph_breaks(self, briefing):
        assert "You'd be the one assembling it." in briefing
        idx = briefing.find("squeezed out of the room.")
        nxt = briefing.find("Hold that next")
        assert -1 < idx < nxt

    def test_one_breath_opening(self, briefing):
        assert "## The short version" in briefing
        assert "The look changed because the money changed." in briefing

    def test_noticings_render(self, briefing):
        assert "## Things that stood out" in briefing
        assert "rain and darkness, on purpose." in briefing

    def test_landscape_renders_without_choosing(self, briefing):
        assert "## How this topic is usually covered, and what is not" in briefing
        assert "practical-effects fairy tale" in briefing
        assert "unassembled" in briefing
        assert "you should" not in briefing.lower()

    def test_out_loud_closer_derived_from_claims(self, briefing):
        assert "**Solid, safe to state plainly:**" in briefing
        assert "The look changed for reason number 1." in briefing
        assert "one source only" in briefing

    def test_holes_become_open_questions(self, briefing):
        assert "Open questions nobody in the sources answers" in briefing
        assert "Nobody asked a working colorist" in briefing

    def test_receipts_pointer_present(self, briefing):
        assert "source ledger" in briefing


class TestVoiceLaws:
    def test_passes_the_lint(self, briefing):
        result = lint_rendered_document(briefing)
        assert result.passes, result.errors

    def test_no_internal_ids_reach_the_page(self, briefing):
        for token in ("CLM_", "SRC_", "STG_", "STY_", "HOLE_", "KP_"):
            assert token not in briefing

    def test_leaked_source_id_is_humanized(self):
        data = _graph_dict()
        data["sections"][0]["body"] = "This matches what SRC_2 found."
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)
        assert "SRC_2" not in briefing
        assert "The Colorist's Complaint" in briefing


class TestCrossReferenceBan:
    """Decision 024's hard rule: the reader never decodes a label."""

    @pytest.mark.parametrize(
        "sentence",
        [
            "Thread 4 sits underneath threads 2 and 3.",
            "As mentioned above, the cameras changed.",
            "See below for the money story.",
            "The previous section covers the cameras.",
            "As we said, the look is flat now.",
        ],
    )
    def test_cross_references_fail_the_render(self, sentence):
        data = _graph_dict()
        data["sections"][0]["body"] = sentence
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)
        result = lint_rendered_document(briefing)
        assert not result.passes

    def test_plain_resaying_passes(self):
        data = _graph_dict()
        data["sections"][0]["body"] = (
            "The camera complaints are real, and the money story sits "
            "underneath them: budgets drive the choices the essayists blame "
            "on taste."
        )
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)
        assert lint_rendered_document(briefing).passes


class TestSectionValidators:
    def test_section_without_provenance_rejected(self):
        data = _graph_dict()
        data["sections"][0]["claim_ids"] = []
        with pytest.raises(Exception, match="no provenance"):
            ClaimGraph.model_validate(data)

    def test_section_citing_unknown_claim_rejected(self):
        data = _graph_dict()
        data["sections"][0]["claim_ids"] = ["CLM_99"]
        with pytest.raises(Exception, match="unknown claim"):
            ClaimGraph.model_validate(data)

    def test_single_source_connection_rejected(self):
        """A connection that draws on one source is just a claim."""
        data = _graph_dict()
        data["sections"][0]["claim_ids"] = ["CLM_3"]  # one-source claim
        with pytest.raises(Exception, match="only one source"):
            ClaimGraph.model_validate(data)

    def test_legacy_graph_without_telling_layer_still_renders(self):
        data = _graph_dict()
        data["sections"] = []
        data["noticings"] = []
        data["landscape"] = None
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)
        assert "## The look changed for reason number 1" in briefing
        assert lint_rendered_document(briefing).passes


class TestTopicCleanup:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("research why films look flat", "Why films look flat"),
            ("", "Research Briefing"),
        ],
    )
    def test_turns_a_request_into_a_heading(self, raw, expected):
        assert _clean_topic(raw) == expected


class TestConfidenceBar:
    def test_still_available_for_other_projections(self):
        assert confidence_bar(3) == "▮▮▮▯▯"
