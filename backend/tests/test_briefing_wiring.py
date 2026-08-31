"""Tests that the Briefing is produced by a job, not only by hand.

Cover for the pipeline wiring under P3 work-order items 14-15. Every pass, the
gates, the renderer, and the vault existed and worked before this; what was
missing was a job ever calling them. These tests run the stage with a scripted
client and check that its outputs land where the completion stage looks.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.models.semantic_units import AnalysisMode
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.briefing_stage import stage_briefing
from backend.pipeline.stages.initialization import _brief_document


def _package(source_id, title, content):
    return SimpleNamespace(
        source_id=source_id,
        title=title,
        source_type="article",
        creator="Jane Doe",
        published="2026-01-02",
        content=content,
        analysis_mode=AnalysisMode.ARTICLE_FETCHED,
    )


def _scripted_client():
    """A client that answers each pass with something schema-shaped."""
    client = MagicMock()

    def answer(prompt, schema, system, max_tokens=8000, model=None):
        keys = set(schema.get("properties", {}))
        if keys == {"lede", "paragraphs"}:
            data = {
                "lede": "Read both sources.",
                "paragraphs": [
                    {
                        "label": "What you've got",
                        "text": "Petrie excavated Hawara in 1888 and found a stone bed.",
                    }
                ],
            }
        elif keys == {"subjects", "anecdote_fact_ids"}:
            data = {
                "subjects": [{"title": "The excavation", "fact_ids": ["SRC_1:F_2"]}],
                "anecdote_fact_ids": ["SRC_2:F_1"],
            }
        elif keys == {"title", "body"}:
            data = {
                "title": "The excavation",
                "body": "The stone bed measures 304 by 244 metres of plaster.",
            }
        elif keys == {"blurbs"}:
            data = {"blurbs": [{"index": 0, "context": "He read it as a foundation."}]}
        elif keys == {"players"}:
            data = {"players": []}
        elif keys == {"places"}:
            data = {"places": []}
        elif keys == {"names"}:
            data = {"names": []}
        elif keys == {"contributions"}:
            data = {"contributions": [{"source_id": "SRC_1", "contribution": "the dig record."}]}
        else:
            data = {
                "for_heading": "The case for",
                "for_text": "The bed is a foundation.",
                "against_heading": "The case against",
                "against_text": "The bed is a roof.",
            }
        return data, {"cost": 0.0}

    client.generate_structured.side_effect = answer
    return client


@pytest.fixture
def ctx():
    context = PipelineContext(job_id="job-1", topic="The lost labyrinth")
    context.source_identity_packages = [
        _package("SRC_1", "A dig report", "Petrie excavated Hawara in 1888 and found a stone bed."),
        _package("SRC_2", "A retelling", "Petrie got stuck in a collapsing tunnel and used a match."),
    ]
    context.harvest = {
        "SRC_1": [
            "Petrie excavated Hawara in 1888 and found a stone bed.",
            "The stone bed measures 304 by 244 metres of plaster.",
        ],
        "SRC_2": ["Petrie got stuck in a collapsing tunnel and used a match."],
    }
    context.harvest_inventory = [
        {
            "fact_id": "SRC_1:F_1",
            "source_id": "SRC_1",
            "text": "Petrie excavated Hawara in 1888 and found a stone bed.",
            "has_number": True,
        },
        {
            "fact_id": "SRC_1:F_2",
            "source_id": "SRC_1",
            "text": "The stone bed measures 304 by 244 metres of plaster.",
            "has_number": True,
        },
        {
            "fact_id": "SRC_2:F_1",
            "source_id": "SRC_2",
            "text": "Petrie got stuck in a collapsing tunnel and used a match.",
            "has_number": False,
        },
    ]
    return context


class TestStageBriefing:
    """The stage a job now runs."""

    def _run(self, ctx, client=None):
        with patch(
            "backend.integrations.structured_client.get_structured_client",
            return_value=client or _scripted_client(),
        ), patch("backend.pipeline.stages.briefing_stage.update_job"):
            stage_briefing(ctx)

    def test_the_job_ends_up_with_a_briefing(self, ctx):
        """The whole chain runs from a context, with no hand-holding."""
        self._run(ctx)

        assert ctx.briefing is not None
        assert ctx.briefing.read.lede == "Read both sources."
        assert ctx.briefing.files

    def test_outputs_are_where_completion_looks(self, ctx):
        """JSON, Markdown, HTML, gates, and the vault all travel with the job."""
        self._run(ctx)

        for key in (
            "briefing",
            "briefing_md",
            "briefing_html",
            "briefing_report",
            "source_vault_html",
        ):
            assert ctx.outputs.get(key), f"missing output: {key}"

        assert ctx.outputs["briefing_html"].startswith('<meta charset="utf-8">')
        assert "<title>" in ctx.outputs["briefing_html"]
        assert "SRC_1" in ctx.outputs["source_vault_html"]

    def test_the_brief_slot_serves_the_briefing(self, ctx):
        """Doc 2 carries the canonical JSON plus its renders."""
        self._run(ctx)

        document = _brief_document(ctx)

        assert document["data"]["briefing_version"] == "1"
        assert document["markdown"].startswith("# ")
        assert document["html"]
        assert document["gates"]["coverage"]["checked"] == 3

    def test_gates_run_and_are_reported(self, ctx):
        """A job that produces a Briefing also produces its evidence."""
        self._run(ctx)

        report = ctx.briefing_report

        assert report["coverage"]["passed"] is True
        assert "grounding" in report and "lint" in report

    def test_a_failure_degrades_rather_than_killing_the_job(self, ctx):
        """Research already paid for is not lost to a Briefing failure."""
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("provider down")

        self._run(ctx, client)

        assert ctx.briefing is None
        assert any("Briefing generation failed" in w for w in ctx.warnings)

    def test_no_sources_no_briefing(self, ctx):
        """Nothing to write about is not an error."""
        ctx.source_identity_packages = []

        self._run(ctx)

        assert ctx.briefing is None
        assert ctx.warnings == []
