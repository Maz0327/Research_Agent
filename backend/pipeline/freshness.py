"""Staleness pass and dated addendum (work order I.26, and I.29's check_updates).

A Briefing on a live subject starts going stale the moment it is written. The
Hawara dig is the case this was built for: the corpus's own Info Gaps already
say what is missing and where to look for it, which makes them the natural
queries for "has any of this been answered since?".

Two rules shape the whole module. New material lands as a *dated addendum*
rather than being folded into the body, so the owner reads the delta instead of
re-reading the document. And a result whose date cannot be established is
reported as undated rather than assumed recent — the failure that would matter
here is a "new" finding that predates the original run.
"""
import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from loguru import logger

# Dates arrive from search providers in whatever format the source used.
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%d %b %Y",
    "%b %d, %Y",
    "%B %d, %Y",
)

_DATE_KEYS = ("published_date", "published", "date", "publishedDate", "published_at")


def parse_date(value: Any) -> Optional[date]:
    """Parse a provider's date string, returning None when it cannot be read.

    Args:
        value: Whatever the provider put in its date field.

    Returns:
        The date, or None. None means unknown — never "today".
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text[: len(fmt) + 6], fmt).date()
        except ValueError:
            continue

    # Last resort: an ISO-ish prefix, which covers most provider output.
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(*(int(g) for g in match.groups()))
        except ValueError:
            return None
    return None


def candidate_date(candidate: dict) -> Optional[date]:
    """Find a candidate's publication date under whichever key carries it."""
    for key in _DATE_KEYS:
        parsed = parse_date(candidate.get(key))
        if parsed:
            return parsed
    return None


def split_by_date(
    candidates: list[dict],
    since: date,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Sort candidates into newer, older, and undated.

    Undated results are kept separately rather than dropped or assumed recent.
    Most of the web does not publish a machine-readable date, so discarding
    them would throw away most of the answer, and trusting them would let a
    2019 page arrive as this week's news.

    Args:
        candidates: Search results.
        since: The cutoff, normally the original job's date.

    Returns:
        Tuple of (newer, older, undated).
    """
    newer, older, undated = [], [], []
    for candidate in candidates:
        published = candidate_date(candidate)
        if published is None:
            undated.append(candidate)
        elif published > since:
            newer.append(candidate)
        else:
            older.append(candidate)
    return newer, older, undated


def gap_search_prompt(info_gaps: list[dict], limit: int = 6) -> str:
    """Turn the Briefing's own Info Gaps into search guidance.

    The gaps already carry `go_get` — the instruction the Briefing wrote for a
    researcher. Reusing it means the freshness pass looks for exactly what the
    document said was missing, rather than re-searching the topic at large.

    Args:
        info_gaps: Info Gap entries carrying `question` and `go_get`.
        limit: How many gaps to fold in.

    Returns:
        A guidance string for `grounded_search`, or "" when there are no gaps.
    """
    lines = []
    for gap in info_gaps[:limit]:
        question = str(gap.get("question") or "").strip()
        go_get = str(gap.get("go_get") or "").strip()
        if go_get:
            lines.append(f"- {go_get}" + (f" (answers: {question})" if question else ""))
        elif question:
            lines.append(f"- {question}")

    if not lines:
        return ""
    return (
        "Find material published since the original research that answers any of "
        "these open questions. Prefer primary sources, official statements, and "
        "dated reporting.\n" + "\n".join(lines)
    )


def find_updates(
    doc_0: dict,
    info_gaps: list[dict],
    since: date,
    existing_urls: Optional[set[str]] = None,
    max_results: int = 8,
    search: Any = None,
) -> dict:
    """Search for material that post-dates the original run.

    Args:
        doc_0: The source ledger, for grounding the queries.
        info_gaps: The Briefing's Info Gaps, which become the search guidance.
        since: The original job's date.
        existing_urls: URLs already in the research, excluded from results.
        max_results: Candidates to request.
        search: Injection point for `grounded_search`; defaults to the real one.

    Returns:
        A findings dict: newer, undated, and older candidates plus the guidance
        actually used. Empty rather than raising when there is nothing to ask.
    """
    prompt = gap_search_prompt(info_gaps)
    if not prompt:
        logger.info("Freshness pass: no info gaps to search from")
        return {"newer": [], "undated": [], "older": [], "prompt": ""}

    if search is None:
        from backend.pipeline.runs.search import grounded_search as search

    try:
        candidates = search(
            doc_0=doc_0,
            user_prompt=prompt,
            existing_urls=existing_urls or set(),
            max_results=max_results,
        )
    except Exception as exc:
        logger.warning(f"Freshness pass: search failed ({exc})")
        return {"newer": [], "undated": [], "older": [], "prompt": prompt}

    newer, older, undated = split_by_date(candidates, since)
    return {"newer": newer, "undated": undated, "older": older, "prompt": prompt}


def build_addendum(topic: str, findings: dict, since: date, today: Optional[date] = None) -> dict:
    """Assemble the dated addendum the owner actually reads.

    Args:
        topic: The job topic.
        findings: Output of `find_updates`.
        since: The original job's date.
        today: The addendum's date; defaults to today in UTC.

    Returns:
        An addendum dict. `has_updates` is False when nothing dated is newer,
        which is a real answer and must not be dressed up as one.
    """
    stamped = today or datetime.now(timezone.utc).date()
    newer = findings.get("newer") or []
    undated = findings.get("undated") or []

    if newer:
        headline = f"{len(newer)} item{'s' if len(newer) != 1 else ''} published since {since.isoformat()}"
    elif undated:
        headline = f"Nothing dated after {since.isoformat()}; {len(undated)} undated result{'s' if len(undated) != 1 else ''} to check by hand"
    else:
        headline = f"Nothing new found since {since.isoformat()}"

    return {
        "topic": topic,
        "checked_on": stamped.isoformat(),
        "covers_since": since.isoformat(),
        "has_updates": bool(newer),
        "headline": headline,
        "new_items": [
            {
                "url": c.get("url", ""),
                "title": c.get("title", ""),
                "snippet": c.get("snippet", ""),
                "published": candidate_date(c).isoformat() if candidate_date(c) else None,
            }
            for c in newer
        ],
        "undated_items": [
            {"url": c.get("url", ""), "title": c.get("title", "")} for c in undated
        ],
    }


def render_addendum_markdown(addendum: dict) -> str:
    """Render the addendum as the delta note that sits above the Briefing."""
    lines = [
        f"## Update check — {addendum.get('checked_on', '')}",
        "",
        addendum.get("headline", ""),
        "",
    ]
    for item in addendum.get("new_items") or []:
        stamp = f" ({item['published']})" if item.get("published") else ""
        lines.append(f"- **{item.get('title') or item.get('url')}**{stamp} — {item.get('url')}")
    if addendum.get("undated_items"):
        lines.extend(["", "Undated, needs a human eye:"])
        for item in addendum["undated_items"]:
            lines.append(f"- {item.get('title') or item.get('url')} — {item.get('url')}")
    return "\n".join(lines).rstrip() + "\n"
