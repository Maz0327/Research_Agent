"""Tests for the Doc 3 retirement and its code-built remainder.

Cover for P3 work-order item 16. The Creator Brief performs rather than
informs, so it is off by default; the one part worth keeping - the source list
a video description carries - is a transcription of Doc 0 and is now built by
code, where a deviation from Doc 0 is an error rather than a style.
"""
from unittest.mock import patch

from backend.config import get_settings
from backend.pipeline.context import PipelineContext
from backend.pipeline.formatters.description_sources import (
    build_description_sources,
    render_description_sources,
)
from backend.pipeline.stages.creator_brief_stage import run_creator_brief_stage


class TestCreatorBriefFlag:
    """Off by default, still switchable for a product experiment."""

    def test_retired_by_default(self):
        """The default run does not generate Doc 3."""
        assert get_settings().creator_brief_enabled is False

    def test_stage_returns_without_generating(self, monkeypatch):
        """The stage is a no-op when the flag is off, and costs nothing."""
        ctx = PipelineContext(job_id="job-1", topic="A topic")

        with patch(
            "backend.pipeline.stages.creator_brief_stage._run_creator_brief"
        ) as generate:
            returned = run_creator_brief_stage(ctx)

        generate.assert_not_called()
        assert returned is ctx
        assert ctx.warnings == []

    def test_flag_switches_it_back_on(self, monkeypatch):
        """The code stays usable until P8."""
        settings = get_settings()
        monkeypatch.setattr(settings, "creator_brief_enabled", True)
        ctx = PipelineContext(job_id="job-1", topic="A topic")

        with patch(
            "backend.pipeline.stages.creator_brief_stage._run_creator_brief"
        ) as generate, patch(
            "backend.pipeline.stages.creator_brief_stage.update_job"
        ):
            run_creator_brief_stage(ctx)

        generate.assert_called_once()


class TestDescriptionSources:
    """The remainder: Doc 0, transcribed."""

    def _sources(self):
        return [
            {
                "source_id": "SRC_1",
                "title": "A video essay",
                "creator": "Johanna",
                "url": "https://youtu.be/abc",
                "full_text": "transcript",
            },
            {
                "source_id": "SRC_2",
                "title": "A failed fetch",
                "url": "https://example.com/x",
                "full_text": "",
            },
            {
                "source_id": "SRC_3",
                "title": "A syndicated copy",
                "url": "https://example.com/y",
                "full_text": "text",
                "duplicate_of": "SRC_1",
            },
        ]

    def test_only_sources_that_arrived_are_credited(self):
        """A description credits what the video actually drew on."""
        listed = build_description_sources(self._sources())

        assert [s["source_id"] for s in listed] == ["SRC_1", "SRC_3"]

    def test_inaccessible_sources_can_be_included(self):
        """The caller can ask for the full ledger instead."""
        listed = build_description_sources(self._sources(), include_inaccessible=True)

        assert [s["source_id"] for s in listed] == ["SRC_1", "SRC_2", "SRC_3"]

    def test_republications_are_marked(self):
        """The same article is not credited twice as if it were two."""
        rendered = render_description_sources(build_description_sources(self._sources()))

        assert "(republication)" in rendered

    def test_rendering_is_plain_text_with_urls(self):
        """What comes out is what goes in a description box."""
        rendered = render_description_sources(
            build_description_sources(self._sources()), header="Sources"
        )

        assert rendered.startswith("Sources\n")
        assert "A video essay - Johanna" in rendered
        assert "https://youtu.be/abc" in rendered
