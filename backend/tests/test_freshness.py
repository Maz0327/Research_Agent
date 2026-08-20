"""Tests for the staleness pass and the update mechanism (work order I.26/I.29).

The failure this guards against is a "new" finding that is not new: a result
with no date treated as recent, or a re-check that reports movement where the
document is unchanged. Both would cost the owner a re-read they did not owe.
"""
from datetime import date
from unittest.mock import MagicMock

from backend.models.briefing import Briefing, BriefingMeta, File, Read, ReadParagraph
from backend.pipeline.briefing_diff import changed_sections, diff_briefings
from backend.pipeline.freshness import (
    build_addendum,
    candidate_date,
    find_updates,
    gap_search_prompt,
    parse_date,
    split_by_date,
)

CUTOFF = date(2026, 6, 1)


def _briefing(lede="A lede that carries the document.", files=None, sources=None):
    """Build a minimal valid Briefing for comparison."""
    return Briefing(
        job_id="JOB_1",
        topic="A topic",
        meta=BriefingMeta(source_count=1, independent_source_count=1, raw_words=100),
        read=Read(lede=lede, paragraphs=[ReadParagraph(text="A paragraph.")]),
        files=files or [],
        source_trail=sources or [],
    )


class TestDateParsing:
    """A date that cannot be read is unknown, never today."""

    def test_common_provider_formats_parse(self):
        assert parse_date("2026-07-14") == date(2026, 7, 14)
        assert parse_date("2026-07-14T09:30:00Z") == date(2026, 7, 14)
        assert parse_date("July 14, 2026") == date(2026, 7, 14)

    def test_unreadable_dates_are_none_not_now(self):
        """The whole point: an undated page must not arrive as this week's news."""
        assert parse_date("") is None
        assert parse_date("last Tuesday") is None
        assert parse_date(None) is None

    def test_the_date_is_found_under_whichever_key_carries_it(self):
        assert candidate_date({"publishedDate": "2026-07-14"}) == date(2026, 7, 14)
        assert candidate_date({"published_at": "2026-07-14"}) == date(2026, 7, 14)
        assert candidate_date({"url": "x"}) is None


class TestDateSplit:
    """Undated results are their own bucket, not silently sorted."""

    def test_newer_older_and_undated_separate(self):
        newer, older, undated = split_by_date(
            [
                {"url": "a", "published_date": "2026-07-01"},
                {"url": "b", "published_date": "2025-01-01"},
                {"url": "c"},
            ],
            CUTOFF,
        )
        assert [c["url"] for c in newer] == ["a"]
        assert [c["url"] for c in older] == ["b"]
        assert [c["url"] for c in undated] == ["c"]

    def test_a_result_on_the_cutoff_is_not_newer(self):
        """The original run already saw that day."""
        newer, older, _ = split_by_date(
            [{"url": "a", "published_date": CUTOFF.isoformat()}], CUTOFF
        )
        assert newer == [] and len(older) == 1


class TestGapPrompt:
    """The search asks for what the document said it lacked."""

    def test_the_prompt_is_built_from_go_get_instructions(self):
        prompt = gap_search_prompt([
            {"question": "Were the scans peer reviewed?", "go_get": "The scan report itself"},
        ])
        assert "The scan report itself" in prompt
        assert "Were the scans peer reviewed?" in prompt

    def test_no_gaps_means_no_search(self):
        """Searching the topic at large is drift, which is what this avoids."""
        assert gap_search_prompt([]) == ""


class TestAddendum:
    """Nothing new is a real answer."""

    def test_new_items_are_listed_with_their_dates(self):
        addendum = build_addendum(
            "A topic",
            {"newer": [{"url": "a", "title": "A report", "published_date": "2026-07-01"}]},
            CUTOFF,
            today=date(2026, 8, 20),
        )
        assert addendum["has_updates"] is True
        assert addendum["new_items"][0]["published"] == "2026-07-01"
        assert addendum["checked_on"] == "2026-08-20"

    def test_nothing_new_says_nothing_new(self):
        addendum = build_addendum("A topic", {"newer": []}, CUTOFF, today=date(2026, 8, 20))
        assert addendum["has_updates"] is False
        assert "Nothing new" in addendum["headline"]

    def test_undated_results_are_surfaced_for_a_human_not_claimed_as_new(self):
        addendum = build_addendum(
            "A topic",
            {"newer": [], "undated": [{"url": "a", "title": "Undated page"}]},
            CUTOFF,
            today=date(2026, 8, 20),
        )
        assert addendum["has_updates"] is False
        assert "undated" in addendum["headline"]
        assert addendum["undated_items"][0]["url"] == "a"

    def test_a_failed_search_reports_nothing_rather_than_raising(self):
        def boom(**_kwargs):
            raise RuntimeError("provider down")

        findings = find_updates(
            {}, [{"go_get": "Something"}], CUTOFF, search=boom
        )
        assert findings["newer"] == []


class TestVersionDiff:
    """The reader's question: what changed, and what can I skip?"""

    def test_an_unchanged_section_is_named_as_safe_to_skip(self):
        old = _briefing()
        new = _briefing(lede="A completely different lede sentence entirely.")
        diff = diff_briefings(old, new)
        assert diff["changed_sections"]["read"] is True
        assert "players" in diff["unchanged_sections"]
        assert "safe to skip" in diff["summary"]

    def test_no_change_says_the_document_still_stands(self):
        """The most useful answer a re-run can give."""
        diff = diff_briefings(_briefing(), _briefing())
        assert diff["summary"].startswith("No change")
        assert diff["new_facts"] == []

    def test_new_facts_and_sources_are_counted(self):
        old = _briefing(files=[File(title="A file", body="Body text.", fact_ids=["F_1"])])
        new = _briefing(
            files=[File(title="A file", body="Body text.", fact_ids=["F_1", "F_2"])]
        )
        diff = diff_briefings(old, new)
        assert diff["new_facts"] == ["F_2"]
        assert diff["dropped_facts"] == []

    def test_a_first_version_is_not_a_diff(self):
        diff = diff_briefings(None, _briefing())
        assert diff["first_version"] is True
        assert all(diff["changed_sections"].values())

    def test_section_comparison_reads_text_not_object_identity(self):
        """Two builds of the same content must not read as a change."""
        assert changed_sections(_briefing(), _briefing()) == {
            k: False for k in changed_sections(_briefing(), _briefing())
        }


class TestCheckUpdatesMode:
    """The iterate mode, wired end to end."""

    def test_the_mode_returns_an_addendum_model_ready_to_attach(self):
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.iteration.modes.check_updates import run_check_updates

        ctx = PipelineContext(job_id="JOB_1", topic="A topic", job_config=None)
        artifacts = {
            "doc_0": {"data": {"created_at": "2026-06-01T00:00:00Z", "sources": []}},
            "briefing": {"data": {"info_gaps": [{"go_get": "The scan report"}]}},
        }
        result = run_check_updates(
            ctx,
            artifacts,
            MagicMock(),
            search=lambda **_k: [{"url": "a", "title": "New", "published_date": "2026-07-01"}],
            today=date(2026, 8, 20),
        )
        assert result["model"].has_updates is True
        assert result["model"].covers_since == "2026-06-01"

    def test_a_briefing_with_no_gaps_searches_nothing(self):
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.iteration.modes.check_updates import run_check_updates

        called = []
        ctx = PipelineContext(job_id="JOB_1", topic="A topic", job_config=None)
        result = run_check_updates(
            ctx,
            {"doc_0": {"data": {"created_at": "2026-06-01T00:00:00Z"}}, "briefing": {"data": {}}},
            MagicMock(),
            search=lambda **_k: called.append(1) or [],
            today=date(2026, 8, 20),
        )
        assert called == []
        assert result["model"].has_updates is False
