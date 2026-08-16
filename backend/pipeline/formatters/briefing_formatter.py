"""Research Briefing renderer - the human-readable form of the Claim Graph.

Pure code. No LLM call. The graph already carries the prose, so rendering is
selection, ordering and layout; anything that needed writing was written at
distillation time.

Based on: plans/260814-claim-graph-briefing/spec.md Section 3

Three altitudes in one file:
  1. The map      - thesis, the claims as one-liners, the worst holes
  2. The argument - claim units on the spine, holes rendered inline
  3. The closers  - challenge prep, sources ranked, appendix pointer

Two rules bind every line emitted here. No internal IDs reach the page: the
reader sees source names and plain evidence-status language. And no em-dashes,
which the tic-lint enforces on the rendered result.
"""

import re
from typing import Optional

from backend.models.claim_graph import Claim, ClaimGraph

# The distillation prompt bans internal IDs in prose, and the model mostly
# obeys, but "mostly" is not a guarantee and a single leaked ID fails the
# document's lint. The renderer knows the ID-to-name mapping, so it substitutes
# rather than trusting. Observed on the fixture: a source note read
# "the same impact as SRC_7".
_SOURCE_ID_IN_PROSE = re.compile(r"\bSRC_(\d+)\b")

# Filled and empty blocks for the confidence scale.
_FILLED = "▮"
_EMPTY = "▯"

def _evidence_line(status: str, source_count: int) -> str:
    """Say where a claim came from, the way a person would.

    Built from the actual source count rather than one stock sentence per
    status. The first version of this repeated "More than one source lands
    here independently" under all fifteen claims, and that repetition is
    itself the essay texture the voice laws exist to prevent.
    """
    if status == "all_sources":
        return "Everything we found says this."
    if status == "conflicted":
        return "The sources don't agree on this one."
    if status == "one_source":
        return "Only one source says this, so treat it as a lead."
    if status == "multi_source":
        if source_count >= 3:
            return f"{source_count} sources say this, separately."
        return "Two sources got here on their own."
    return ""

_THESIS_CONFIDENCE_PHRASE = {
    "solid": "This holds up. The evidence is there.",
    "usable": "Good enough to build on, with the gaps below called out honestly.",
    "thin": "Treat this as a working read, not a finding. The evidence is thin.",
}

_ROLE_PHRASE = {
    "backbone": "the whole thing leans on this one",
    "confirmation": "backs up what the others said",
    "color": "good detail and quotes",
    "lead": "worth chasing, but settles nothing on its own",
}


def confidence_bar(grade: int) -> str:
    """Render a 1-5 confidence grade as a block scale."""
    grade = max(1, min(5, int(grade)))
    return _FILLED * grade + _EMPTY * (5 - grade)


def _clean_topic(topic: str) -> str:
    """Turn the raw research request into a document title.

    The stored topic is whatever the user typed, often phrased as an
    instruction ("research why films don't look like films"). Stripping the
    instruction verb and capitalizing gives a heading instead of a command,
    without inventing a title the job never had.
    """
    title = (topic or "").strip()
    for prefix in ("research ", "investigate ", "look into ", "find out "):
        if title.lower().startswith(prefix):
            title = title[len(prefix) :]
            break
    return title[:1].upper() + title[1:] if title else "Research Briefing"


def _escape_markdown(text: str) -> str:
    """Neutralize emphasis characters inside interpolated source titles.

    Source titles routinely contain asterisks (one fixture title is
    "Why don't movies look like *movies* anymore?"). Dropped verbatim into an
    italic line, those asterisks terminate the emphasis early and the rest of
    the sentence renders as plain text.
    """
    return text.replace("*", r"\*").replace("_", r"\_")


def _source_name(source_id: str, source_titles: dict[str, str]) -> str:
    """Resolve a source ID to its human name.

    Falls back to a positional label rather than leaking the raw ID, since an
    ID in the body fails the tic-lint and means nothing to a reader.
    """
    title = source_titles.get(source_id)
    if title:
        return _escape_markdown(title.strip())
    if source_id and source_id.startswith("SRC_"):
        return f"source {source_id.split('_', 1)[1]}"
    return "an unnamed source"


def _humanize(text: Optional[str], source_titles: dict[str, str]) -> str:
    """Replace any source ID the model left in prose with the source's name."""
    if not text:
        return ""
    return _SOURCE_ID_IN_PROSE.sub(
        lambda m: _source_name(f"SRC_{m.group(1)}", source_titles), text
    )


def _render_map(graph: ClaimGraph, source_titles: dict[str, str]) -> list[str]:
    """Page one: the whole argument, re-readable in about three minutes."""
    lines = [f"# {_clean_topic(graph.topic)}", ""]
    lines += [_humanize(graph.thesis.text, source_titles), ""]

    phrase = _THESIS_CONFIDENCE_PHRASE.get(graph.thesis.confidence, "")
    if phrase:
        lines += [f"**How sure:** {phrase}", ""]

    lines += ["## The map", ""]
    for claim in graph.claims_in_spine_order():
        bar = confidence_bar(claim.confidence.grade)
        title = _humanize(claim.title, source_titles)
        lines.append(f"{claim.spine_order}. **{title}** {bar}")
    lines.append("")

    worst = sorted(graph.holes, key=lambda h: h.severity, reverse=True)[:2]
    if worst:
        lines += ["### What is missing most", ""]
        for hole in worst:
            missing = _humanize(hole.missing, source_titles)
            hurts = _humanize(hole.hurts_because, source_titles)
            lines.append(f"- {missing} {hurts}")
        lines.append("")

    return lines


def _render_claim(
    claim: Claim, graph: ClaimGraph, source_titles: dict[str, str]
) -> list[str]:
    """One claim unit, with its holes and story goods attached."""
    lines = [f"### {_humanize(claim.title, source_titles)}", ""]

    says = _humanize(claim.what_sources_say, source_titles)
    lines += [f"**What the sources say:** {says}", ""]

    names = [
        _source_name(ref.source_id, source_titles)
        for ref in claim.evidence
        if ref.source_id
    ]
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)

    status = _evidence_line(claim.evidence_status, len(seen))
    if seen:
        who = seen[0] if len(seen) == 1 else ", ".join(seen[:-1]) + f" and {seen[-1]}"
        lines += [f"*{status} From {who}.*", ""]
    elif status:
        lines += [f"*{status}*", ""]

    if claim.pushback:
        lines += [f"**The pushback:** {_humanize(claim.pushback, source_titles)}", ""]

    if claim.my_read:
        lines += [f"**My read:** {_humanize(claim.my_read, source_titles)}", ""]

    bar = confidence_bar(claim.confidence.grade)
    reason = _humanize(claim.confidence.reason, source_titles)
    lines += [f"**How sure:** {reason} {bar}", ""]

    if claim.say_it_like:
        said = _humanize(claim.say_it_like, source_titles)
        lines += [f'*Say it like:* "{said}"', ""]

    goods = [s for s in graph.story_goods if claim.id in s.claim_ids]
    if goods:
        lines.append("**Worth using:**")
        for good in goods:
            text = _humanize(good.text, source_titles)
            lines.append(f"- {text} ({_source_name(good.source_id, source_titles)})")
        lines.append("")

    for hole in graph.holes_for(claim.id):
        missing = _humanize(hole.missing, source_titles)
        hurts = _humanize(hole.hurts_because, source_titles)
        detail = f" {_humanize(hole.how_to_fill, source_titles)}" if hole.how_to_fill else ""
        lines += [f"**What's missing here:** {missing} {hurts}{detail}", ""]

    return lines


def _render_closers(graph: ClaimGraph, source_titles: dict[str, str]) -> list[str]:
    """Challenge prep, source ranking, and the pointer to the receipts."""
    lines: list[str] = []
    claims_by_id = {c.id: c for c in graph.claims}

    if graph.weakest_ground or graph.strongest_ground:
        lines += ["## If someone challenges you", ""]

        if graph.strongest_ground:
            claim = claims_by_id.get(graph.strongest_ground.claim_id)
            if claim:
                title = _humanize(claim.title, source_titles)
                why = _humanize(graph.strongest_ground.why, source_titles)
                lines += [f"**Stand here.** {title} {why}", ""]

        if graph.weakest_ground:
            claim = claims_by_id.get(graph.weakest_ground.claim_id)
            if claim:
                title = _humanize(claim.title, source_titles)
                why = _humanize(graph.weakest_ground.why, source_titles)
                lines += [f"**Expect the hit here.** {title} {why}", ""]

    if graph.sources_ranked:
        lines += ["## Sources, ranked by how useful they were", ""]
        for ranked in graph.sources_ranked:
            name = _source_name(ranked.source_id, source_titles)
            role = _ROLE_PHRASE.get(ranked.role, ranked.role)
            note = f" {_humanize(ranked.note, source_titles)}" if ranked.note else ""
            lines.append(f"- **{name}** ({role}).{note}")
        lines.append("")

    lines += [
        "## Where the receipts are",
        "",
        "Full source text, verbatim quotes and timestamps are in the source "
        "ledger that ships with this job.",
        "",
    ]
    return lines


def render_briefing(
    graph: ClaimGraph, source_titles: Optional[dict[str, str]] = None
) -> str:
    """Render the Claim Graph as the Research Briefing.

    Args:
        graph: The validated claim graph.
        source_titles: Maps source_id to human-readable title. Without it the
            renderer falls back to positional names, since raw IDs must never
            reach the page.

    Returns:
        The Briefing as markdown.
    """
    titles = source_titles or {}

    lines = _render_map(graph, titles)
    lines += ["## The argument", ""]

    for claim in graph.claims_in_spine_order():
        lines += _render_claim(claim, graph, titles)

    thesis_holes = graph.holes_for("thesis")
    if thesis_holes:
        lines += ["## What would change the whole picture", ""]
        for hole in thesis_holes:
            missing = _humanize(hole.missing, titles)
            hurts = _humanize(hole.hurts_because, titles)
            detail = f" {_humanize(hole.how_to_fill, titles)}" if hole.how_to_fill else ""
            lines.append(f"- {missing} {hurts}{detail}")
        lines.append("")

    lines += _render_closers(graph, titles)

    # Collapse any accidental triple blank line from an omitted optional block.
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"
