"""Creator Brief Markdown Formatter — Doc 3.

Produces polished, consistent markdown output from a CreatorBriefDocument.

Matches the format from docs/competitive/sandcastles-ux-deep-dive.md Section 8.1:
- Header with topic, date, source count
- HOOK OPTIONS (A/B) with "why it works"
- THE SETUP
- THE TWIST / CONTRAST MOMENT
- CORE FACTS with "say it like" phrasing + source links
- THE ANALOGY
- WHAT THIS MEANS FOR YOU
- CLIFFHANGER / OPEN LOOP ENDING
- SOURCES (for description box)
- CLAIMS FLAGGED AS DISPUTED OR SPECULATIVE

Visual language:
- Consistent with Doc 0, 1, 2 markdown rendering
- Disputed claims use ⚠️ warning style
- Sources use citation style consistent with Semantic Brief
- Significance levels visually indicated
"""

from datetime import datetime, timezone
from typing import Optional

from backend.models.creator_brief import CreatorBriefDocument


# ---------------------------------------------------------------------------
# Significance icons (consistent with claim rendering elsewhere)
# ---------------------------------------------------------------------------
_SIGNIFICANCE_ICONS = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}

_FRAMING_LABELS = {
    "contradicts": "CONTRADICTS",
    "disputed": "DISPUTED",
    "speculative": "SPECULATIVE",
    "hedged": "HEDGED",
    "open_question": "OPEN QUESTION",
}


def format_creator_brief(
    brief: CreatorBriefDocument,
    *,
    include_provenance_footer: bool = True,
) -> str:
    """Convert a CreatorBriefDocument to polished markdown.

    The output is designed to be copy-paste ready for the creator's workflow:
    - Hooks are formatted for immediate use
    - Facts include "say it like" phrasing for natural delivery
    - Disputed claims are prominently warned
    - Sources are formatted for description box copy-paste

    Args:
        brief: Validated CreatorBriefDocument.
        include_provenance_footer: Whether to add the provenance chain footer.

    Returns:
        Polished markdown string.
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    lines: list[str] = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines += [
        f"# Creator Brief",
        f"**{brief.topic}**",
        "",
        f"*{now} · {brief.source_count} source{'s' if brief.source_count != 1 else ''} · Doc 3*",
        "",
        "---",
        "",
    ]

    # -----------------------------------------------------------------------
    # Hook Options
    # -----------------------------------------------------------------------
    lines += [
        "## Hook Options",
        "",
        "> Pick one hook to open your video. Both are grounded in the research.",
        "",
    ]

    for hook in sorted(brief.hook_options, key=lambda h: h.hook_id):
        label = hook.hook_id.replace("_", " ")  # HOOK_A → HOOK A
        lines += [
            f"### {label}",
            "",
            f'> **"{hook.text}"**',
            "",
            f"**Why it works:** {hook.why_it_works}",
            "",
            f"*Grounded in: {hook.claim_id} · {hook.source_id}*",
            "",
        ]

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # The Setup
    # -----------------------------------------------------------------------
    lines += [
        "## The Setup",
        "",
        brief.setup.text,
        "",
    ]
    if brief.setup.supporting_source_ids:
        src_refs = " · ".join(brief.setup.supporting_source_ids)
        lines += [f"*Sources: {src_refs}*", ""]

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # The Twist (optional)
    # -----------------------------------------------------------------------
    if brief.twist:
        lines += [
            "## The Twist",
            "",
            "> This is where the obvious answer turns out to be wrong.",
            "",
            brief.twist.text,
            "",
            f"*Framing: **{_FRAMING_LABELS.get(brief.twist.framing, brief.twist.framing)}** · "
            f"{brief.twist.claim_id} · {brief.twist.source_id}*",
            "",
            "---",
            "",
        ]

    # -----------------------------------------------------------------------
    # Core Facts
    # -----------------------------------------------------------------------
    lines += [
        "## Core Facts",
        "",
        "> These are the facts to build your video around. "
        "\"Say it like\" gives you natural-language phrasing for on-camera delivery.",
        "",
    ]

    for fact in brief.core_facts:
        icon = _SIGNIFICANCE_ICONS.get(fact.significance, "·")
        lines += [
            f"### {fact.fact_id} {icon}",
            "",
            f"**As extracted:** {fact.statement}",
            "",
            f"**Say it like:** *\"{fact.say_it_like}\"*",
            "",
        ]

        meta_parts = [f"Significance: **{fact.significance}**"]
        if fact.speaker:
            meta_parts.append(f"Speaker: {fact.speaker}")
        meta_parts.append(f"{fact.claim_id} · {fact.source_id}")
        lines += [f"*{' · '.join(meta_parts)}*", ""]

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Analogy (optional)
    # -----------------------------------------------------------------------
    if brief.analogy:
        lines += [
            "## The Analogy",
            "",
            "> Use this to explain the concept to a general audience.",
            "",
            brief.analogy.text,
            "",
            "---",
            "",
        ]

    # -----------------------------------------------------------------------
    # Personal Stakes (optional)
    # -----------------------------------------------------------------------
    if brief.personal_stakes:
        lines += [
            "## What This Means for You",
            "",
            brief.personal_stakes.text,
            "",
            "---",
            "",
        ]

    # -----------------------------------------------------------------------
    # Cliffhanger (optional)
    # -----------------------------------------------------------------------
    if brief.cliffhanger:
        lines += [
            "## Cliffhanger / Open Question",
            "",
            "> End here to keep viewers thinking after the video ends.",
            "",
            brief.cliffhanger.text,
            "",
            f"*Framing: **{_FRAMING_LABELS.get(brief.cliffhanger.framing, brief.cliffhanger.framing)}***",
            "",
            "---",
            "",
        ]

    # -----------------------------------------------------------------------
    # Sources for Description Box
    # -----------------------------------------------------------------------
    if brief.description_sources:
        lines += [
            "## Sources",
            "",
            "> Copy-paste these into your video description box.",
            "",
        ]

        for src in brief.description_sources:
            # Format: Title by Creator — URL
            parts = [f"**{src.title}**"]
            if src.creator:
                parts.append(f"by {src.creator}")
            line = " ".join(parts)
            if src.url:
                line += f"  \n{src.url}"
            lines += [f"- {line}", ""]

        lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Disputed / Speculative Claims (flagged section)
    # -----------------------------------------------------------------------
    if brief.disputed_claims:
        lines += [
            "## ⚠️ Claims Flagged as Disputed or Speculative",
            "",
            "> **Do not present these as established facts.** "
            "Frame carefully — acknowledge uncertainty.",
            "",
        ]

        for d in brief.disputed_claims:
            framing_label = _FRAMING_LABELS.get(d.framing, d.framing.upper())
            lines += [
                f"- **[{framing_label}]** {d.statement}",
            ]
            meta_parts = []
            if d.speaker:
                meta_parts.append(f"Said by: {d.speaker}")
            meta_parts += [d.claim_id, d.source_id]
            lines += [f"  *{' · '.join(meta_parts)}*", ""]

        lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Provenance footer
    # -----------------------------------------------------------------------
    if include_provenance_footer:
        lines += [
            "*Doc 3 — Creator Brief*  ",
            f"*Job: {brief.job_id} · Generated: {brief.generated_at.strftime('%Y-%m-%d %H:%M UTC')}*  ",
            "*Every fact in this brief traces to a claim in Doc 2 and a source in Doc 0.*",
        ]

    return "\n".join(lines)


def format_creator_brief_from_dict(brief_dict: dict, **kwargs) -> str:
    """Convenience wrapper — parse dict then format.

    Args:
        brief_dict: Raw CreatorBriefDocument dict (e.g. from ctx.outputs).
        **kwargs: Forwarded to format_creator_brief.

    Returns:
        Polished markdown string.
    """
    brief = CreatorBriefDocument(**brief_dict)
    return format_creator_brief(brief, **kwargs)
