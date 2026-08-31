"""Human-facing version diff (work order I.29c).

The existing version manager already produces a machine diff — source counts,
claim counts, a trigger label. That answers "did something change". It does not
answer the question the owner actually has, which is "what changed since I read
this, and do I need to read it again?"

So this compares two Briefings the way a reader would: which facts are new,
which sections were touched, and which were not. A section nobody touched is
the most valuable thing this can report, because it is the part the owner can
safely skip.
"""
from typing import Any

from backend.models.briefing import Briefing

# The nine sections, in the order the document presents them.
SECTIONS = (
    "read",
    "players",
    "places",
    "record",
    "files",
    "disputes",
    "anecdotes",
    "info_gaps",
    "source_trail",
)


def _fact_ids(briefing: Briefing) -> set[str]:
    """Every fact ID the Briefing cites, across all sections."""
    ids: set[str] = set()
    for file in briefing.files:
        ids.update(file.fact_ids)
    return ids


def _source_ids(briefing: Briefing) -> set[str]:
    """Every source ID in the Source Trail."""
    return {entry.source_id for entry in briefing.source_trail}


def _section_text(briefing: Briefing, section: str) -> str:
    """Flatten one section to comparable text.

    Deliberately text rather than structure: a reordered list that says the
    same thing should not read as a change the owner must re-read.
    """
    value = getattr(briefing, section, None)
    if value is None:
        return ""

    if section == "read":
        return " ".join([value.lede] + [p.text for p in value.paragraphs])

    parts: list[str] = []
    for item in value:
        for field in (
            "name", "role", "line", "body", "when", "what", "context", "title",
            "text", "claim", "holders", "question", "why", "go_get",
            "contribution", "heading",
        ):
            got = getattr(item, field, None)
            if isinstance(got, str) and got.strip():
                parts.append(got.strip())
    return " ".join(parts)


def changed_sections(old: Briefing, new: Briefing) -> dict[str, bool]:
    """Report which sections changed and which did not.

    Args:
        old: The version the owner already read.
        new: The version just produced.

    Returns:
        Section name to whether its text differs.
    """
    return {
        section: _section_text(old, section) != _section_text(new, section)
        for section in SECTIONS
    }


def diff_briefings(
    old: Briefing | None,
    new: Briefing,
    addendum: dict | None = None,
) -> dict[str, Any]:
    """Describe what changed between two Briefings, for a person.

    Args:
        old: The previously read version, or None for a first run.
        new: The current version.
        addendum: An update-check addendum to carry into the summary.

    Returns:
        A diff: new and dropped facts and sources, per-section changed flags,
        the sections safe to skip, and a one-line summary.
    """
    if old is None:
        return {
            "first_version": True,
            "summary": "First version — nothing to compare against.",
            "new_facts": [],
            "dropped_facts": [],
            "new_sources": [],
            "dropped_sources": [],
            "changed_sections": dict.fromkeys(SECTIONS, True),
            "unchanged_sections": [],
            "addendum": addendum,
        }

    new_facts = sorted(_fact_ids(new) - _fact_ids(old))
    dropped_facts = sorted(_fact_ids(old) - _fact_ids(new))
    new_sources = sorted(_source_ids(new) - _source_ids(old))
    dropped_sources = sorted(_source_ids(old) - _source_ids(new))
    changed = changed_sections(old, new)
    unchanged = [section for section, did in changed.items() if not did]

    bits = []
    if new_sources:
        bits.append(f"{len(new_sources)} new source{'s' if len(new_sources) != 1 else ''}")
    if new_facts:
        bits.append(f"{len(new_facts)} new fact{'s' if len(new_facts) != 1 else ''}")
    if dropped_facts:
        bits.append(f"{len(dropped_facts)} dropped")
    touched = [section for section, did in changed.items() if did]
    if touched:
        bits.append("changed: " + ", ".join(touched))

    summary = "; ".join(bits) if bits else "No change — the document you read still stands."
    if unchanged and touched:
        summary += f" | unchanged, safe to skip: {', '.join(unchanged)}"

    return {
        "first_version": False,
        "summary": summary,
        "new_facts": new_facts,
        "dropped_facts": dropped_facts,
        "new_sources": new_sources,
        "dropped_sources": dropped_sources,
        "changed_sections": changed,
        "unchanged_sections": unchanged,
        "addendum": addendum,
    }


def render_diff_markdown(diff: dict[str, Any]) -> str:
    """Render the diff as the note that sits above a re-read."""
    lines = ["## What changed since your read", "", diff.get("summary", ""), ""]

    addendum = diff.get("addendum")
    if addendum:
        lines.extend([f"*Update check {addendum.get('checked_on', '')}: "
                      f"{addendum.get('headline', '')}*", ""])

    if diff.get("new_sources"):
        lines.append("**New sources:** " + ", ".join(diff["new_sources"]))
    if diff.get("dropped_sources"):
        lines.append("**Dropped sources:** " + ", ".join(diff["dropped_sources"]))
    if diff.get("unchanged_sections"):
        lines.append(
            "**Unchanged — skip these:** " + ", ".join(diff["unchanged_sections"])
        )
    return "\n".join(lines).rstrip() + "\n"
