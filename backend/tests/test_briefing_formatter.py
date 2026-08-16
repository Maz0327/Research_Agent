"""Tests for the Briefing renderer and the tic-lint that gates it.

EXECUTION-PLAN P2 makes the lint part of the render test: a Briefing that
trips a voice law fails here rather than reaching a reader.
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
                "what_sources_say": "Two sources got to the same place on their own.",
                "pushback": "One source reads the timeline differently." if i == 1 else None,
                "my_read": "This one holds up." if i == 1 else None,
                "say_it_like": f"Here is the {i} of it, out loud.",
                "confidence": {
                    "grade": 4,
                    "reason": "Two independent sources, quotes unverified.",
                },
                "evidence_status": "multi_source",
                "evidence": [{"source_id": "SRC_1"}, {"source_id": "SRC_2"}],
                "story_goods": ["STG_1"] if i == 1 else [],
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
        "story_goods": [
            {
                "id": "STG_1",
                "type": "number",
                "text": "The budget tripled between the two films.",
                "source_id": "SRC_2",
                "claim_ids": ["CLM_1"],
            }
        ],
        "holes": [
            {
                "id": "HOLE_1",
                "attached_to": "CLM_1",
                "missing": "The studio's own numbers.",
                "hurts_because": "The claim rests on one outside estimate.",
                "severity": 4,
                "how_to_fill": "Look for the annual report.",
            },
            {
                "id": "HOLE_2",
                "attached_to": "thesis",
                "missing": "Anyone defending the current look.",
                "hurts_because": "The argument only has one side.",
                "severity": 5,
                "how_to_fill": None,
            },
        ],
        "weakest_ground": {"claim_id": "CLM_3", "why": "It rests on one source."},
        "strongest_ground": {"claim_id": "CLM_1", "why": "Two sources agree."},
        "sources_ranked": [
            {"source_id": "SRC_1", "role": "backbone", "note": "Sets up the whole case."},
            {"source_id": "SRC_2", "role": "color", "note": None},
        ],
    }
    graph.update(overrides)
    return graph


@pytest.fixture
def briefing() -> str:
    graph = ClaimGraph.model_validate(_graph_dict())
    return render_briefing(graph, SOURCE_TITLES)


class TestStructure:
    def test_has_all_three_altitudes(self, briefing):
        assert "## The map" in briefing
        assert "## The argument" in briefing
        assert "## Where the receipts are" in briefing

    def test_map_lists_every_claim(self, briefing):
        head = briefing.split("## The argument")[0]
        for i in range(1, 9):
            assert f"The look changed for reason number {i}." in head

    def test_claim_unit_anatomy(self, briefing):
        assert "**What the sources say:**" in briefing
        assert "**The pushback:**" in briefing
        assert "**My read:**" in briefing
        assert "**How sure:**" in briefing
        assert "*Say it like:*" in briefing

    def test_omits_pushback_when_absent(self, briefing):
        """Claims 2-8 have no pushback, so the label appears exactly once."""
        assert briefing.count("**The pushback:**") == 1

    def test_holes_render_inline_on_their_claim(self, briefing):
        body = briefing.split("## The argument")[1]
        assert "**What's missing here:** The studio's own numbers." in body

    def test_thesis_hole_gets_its_own_section(self, briefing):
        assert "## What would change the whole picture" in briefing
        assert "Anyone defending the current look." in briefing

    def test_story_goods_attach_to_their_claim(self, briefing):
        assert "**Worth using:**" in briefing
        assert "The budget tripled between the two films." in briefing

    def test_challenge_section_names_both_grounds(self, briefing):
        assert "**Stand here.**" in briefing
        assert "**Expect the hit here.**" in briefing

    def test_sources_ranked_in_plain_language(self, briefing):
        assert "the whole thing leans on this one" in briefing
        assert "good detail and quotes" in briefing


class TestVoiceLaws:
    def test_passes_the_tic_lint(self, briefing):
        result = lint_rendered_document(briefing)
        assert result.passes, result.errors

    def test_no_internal_ids_reach_the_page(self, briefing):
        for token in ("CLM_", "SRC_", "STG_", "HOLE_", "KP_", "TEN_", "GAP_"):
            assert token not in briefing

    def test_no_em_dashes(self, briefing):
        assert "—" not in briefing

    def test_uses_source_names_not_ids(self, briefing):
        assert "The Colorist's Complaint" in briefing

    def test_leaked_id_in_model_prose_is_humanized(self):
        """The model occasionally writes an ID into a prose field anyway."""
        data = _graph_dict()
        data["claims"][0]["what_sources_say"] = "This matches SRC_2 exactly."
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        assert "SRC_2" not in briefing
        assert "This matches The Colorist's Complaint exactly." in briefing
        assert lint_rendered_document(briefing).passes

    def test_asterisks_in_source_titles_are_escaped(self, briefing):
        """An unescaped asterisk terminates the surrounding italics early."""
        assert r"like \*movies\* anymore" in briefing


class TestLintGate:
    def test_em_dash_fails_the_render(self):
        data = _graph_dict()
        data["claims"][0]["my_read"] = "This holds up — mostly."
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        result = lint_rendered_document(briefing)
        assert not result.passes
        assert any("em-dash" in e for e in result.errors)

    def test_banned_vocabulary_fails_the_render(self):
        data = _graph_dict()
        data["claims"][0]["my_read"] = "A testament to the craft."
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        assert not lint_rendered_document(briefing).passes

    def test_not_just_construction_fails_the_render(self):
        data = _graph_dict()
        data["claims"][0]["my_read"] = "It's not just the cameras, it's the money."
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        assert not lint_rendered_document(briefing).passes

    def test_honest_enumeration_is_advisory_not_an_error(self):
        """A three-item noun list must not fail a document."""
        result = lint_rendered_document(
            "Artists talked about workload, deadlines, and creative limits daily."
        )
        assert result.passes
        assert result.advisories

    @pytest.mark.parametrize(
        "sentence",
        [
            "Every source in this corpus critiques the modern look.",
            "Primary testimony is absent from the record.",
            "The article posits that budgets are the cause.",
            "Two sources independently corroborate the claim.",
            "This warrants further investigation by someone.",
        ],
    )
    def test_research_register_fails_the_render(self, sentence):
        """The reader does not care how the information was obtained.

        Owner feedback at the P2 gate: the document must read as a person
        telling a person, not as a research essay.
        """
        data = _graph_dict()
        data["claims"][0]["what_sources_say"] = sentence
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        result = lint_rendered_document(briefing)
        assert not result.passes
        assert any("Research-essay word" in e for e in result.errors)


class TestEvidenceLine:
    def test_counts_sources_rather_than_repeating_one_phrase(self):
        """The stock phrase under all 15 claims was itself essay texture."""
        data = _graph_dict()
        data["claims"][0]["evidence"] = [
            {"source_id": "SRC_1"},
            {"source_id": "SRC_2"},
            {"source_id": "SRC_3"},
        ]
        titles = dict(SOURCE_TITLES, SRC_3="A Third Source")
        briefing = render_briefing(ClaimGraph.model_validate(data), titles)

        assert "3 sources say this, separately." in briefing

    def test_two_sources_reads_naturally(self, briefing):
        assert "Two sources got here on their own." in briefing

    def test_never_says_independently(self, briefing):
        """Research register, and it appeared 14 times in the first draft."""
        assert "independently" not in briefing.lower()

    def test_one_source_is_flagged_as_a_lead(self):
        data = _graph_dict()
        data["claims"][0]["evidence_status"] = "one_source"
        data["claims"][0]["evidence"] = [{"source_id": "SRC_1"}]
        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        assert "Only one source says this, so treat it as a lead." in briefing


class TestConfidenceBar:
    @pytest.mark.parametrize(
        "grade,expected",
        [
            (1, "▮▯▯▯▯"),
            (3, "▮▮▮▯▯"),
            (5, "▮▮▮▮▮"),
        ],
    )
    def test_renders_grade(self, grade, expected):
        assert confidence_bar(grade) == expected

    def test_clamps_out_of_range(self):
        assert confidence_bar(9) == "▮▮▮▮▮"
        assert confidence_bar(0) == "▮▯▯▯▯"


class TestTopicCleanup:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("research why films look flat", "Why films look flat"),
            ("Investigate the budget claims", "The budget claims"),
            ("why films look flat", "Why films look flat"),
            ("", "Research Briefing"),
        ],
    )
    def test_turns_a_request_into_a_heading(self, raw, expected):
        assert _clean_topic(raw) == expected


class TestGracefulDegradation:
    def test_renders_without_source_titles(self):
        """Missing titles must not leak raw IDs onto the page."""
        briefing = render_briefing(ClaimGraph.model_validate(_graph_dict()), None)

        assert "SRC_" not in briefing
        assert "source 1" in briefing
        assert lint_rendered_document(briefing).passes

    def test_renders_without_optional_sections(self):
        data = _graph_dict()
        data["story_goods"] = []
        data["holes"] = []
        data["weakest_ground"] = None
        data["strongest_ground"] = None
        data["sources_ranked"] = []
        for claim in data["claims"]:
            claim["story_goods"] = []

        briefing = render_briefing(ClaimGraph.model_validate(data), SOURCE_TITLES)

        assert "## The map" in briefing
        assert "If someone challenges you" not in briefing
        assert "\n\n\n" not in briefing
        assert lint_rendered_document(briefing).passes
