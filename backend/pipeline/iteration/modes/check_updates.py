"""check_updates iteration mode (work order I.29a; the pass is item I.26).

The sixth iterate mode, and the only one that asks a question about time: has
anything been published since the original run that answers what the Briefing
itself said was missing?

It reuses the Briefing's own Info Gaps as the search guidance, which keeps the
search honest — it looks for what the document admitted it lacked, not for the
topic at large. New material lands as a dated addendum rather than being folded
into the body, so a re-read is a delta, not a re-read.
"""
from datetime import date, datetime, timezone
from typing import Any, Optional

from loguru import logger

from backend.models.briefing import Addendum
from backend.pipeline.context import PipelineContext
from backend.pipeline.freshness import build_addendum, find_updates

from ..metrics_tracker import MetricsTracker


def _job_date(artifacts: dict[str, Any]) -> date:
    """Find the date the original research was done.

    Falls back to today, which makes the check find nothing rather than
    reporting stale material as new. Of the two ways to be wrong, silence is
    the recoverable one.
    """
    for key in ("created_at", "generated_on"):
        raw = artifacts.get("doc_0", {}).get("data", {}).get(key)
        if raw:
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
            except ValueError:
                continue
    logger.warning("check_updates: no job date found; using today")
    return datetime.now(timezone.utc).date()


def _existing_urls(artifacts: dict[str, Any]) -> set[str]:
    """Every URL already in the research, so the check reports only new ones."""
    sources = artifacts.get("doc_0", {}).get("data", {}).get("sources", []) or []
    return {str(s.get("url") or "") for s in sources if s.get("url")}


def run_check_updates(
    ctx: PipelineContext,
    artifacts_dict: dict[str, Any],
    metrics: MetricsTracker,
    search: Any = None,
    today: Optional[date] = None,
) -> dict[str, Any]:
    """Check whether anything has been published since the original run.

    Args:
        ctx: Pipeline context, for job_id and topic.
        artifacts_dict: The completed job's documents.
        metrics: Metrics tracker.
        search: Injection point for `grounded_search`, for tests.
        today: The addendum's date; defaults to today in UTC.

    Returns:
        The addendum as a dict, alongside the model form ready to attach to a
        Briefing. `has_updates` False is a real answer, not a failure.
    """
    doc_0 = artifacts_dict.get("doc_0", {}).get("data", {}) or {}
    briefing = artifacts_dict.get("briefing", {}).get("data", {}) or {}
    info_gaps = briefing.get("info_gaps", []) or []

    since = _job_date(artifacts_dict)
    logger.info(f"[{ctx.job_id}] check_updates: searching for material after {since}")

    findings = find_updates(
        doc_0=doc_0,
        info_gaps=info_gaps,
        since=since,
        existing_urls=_existing_urls(artifacts_dict),
        search=search,
    )
    addendum = build_addendum(ctx.topic, findings, since, today)

    logger.info(
        f"[{ctx.job_id}] check_updates: {len(addendum['new_items'])} new, "
        f"{len(addendum['undated_items'])} undated"
    )
    return {
        "addendum": addendum,
        "model": Addendum(
            checked_on=addendum["checked_on"],
            covers_since=addendum["covers_since"],
            headline=addendum["headline"],
            has_updates=addendum["has_updates"],
            new_items=addendum["new_items"],
        ),
    }
