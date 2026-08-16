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




# -----------------------------------------------------------------------------
# Shape B rendering (Decision 024)
#
# The document is built from the telling layer: named story sections whose
# titles are full sentences, self-contained bodies with the details woven in,
# noticings, and the landscape. Claims render only inside the closing
# "out loud" section, as plain talk about what is safe to say.
# -----------------------------------------------------------------------------

_THESIS_CONFIDENCE_PHRASE = {
    "solid": "This picture holds up. The backing is there.",
    "usable": "Good enough to build on, with the soft spots called out below.",
    "thin": "Treat this as a working read, not a finding. The backing is thin.",
}


def _sentence_case_header(title: str) -> str:
    """Make sure a section title reads as a sentence, not a label."""
    title = title.strip().rstrip(".")
    return title[:1].upper() + title[1:] if title else title


def _render_out_loud(graph: ClaimGraph, titles: dict[str, str]) -> list[str]:
    """The closing section: what to say with your chest, and where to tread.

    Derived from the claims and holes rather than written by the model, so it
    cannot drift from the provenance layer.
    """
    lines = ["## If you end up talking about this out loud", ""]

    solid = [
        c
        for c in graph.claims_in_spine_order()
        if c.confidence.grade >= 4 or c.evidence_status == "all_sources"
    ]
    careful = [
        c
        for c in graph.claims_in_spine_order()
        if c.evidence_status in ("one_source", "conflicted") and c not in solid
    ]

    if solid:
        lines.append("**Say these with your chest:**")
        for claim in solid:
            lines.append(f"- {_humanize(claim.title, titles)}")
        lines.append("")

    if careful:
        lines.append(
            "**Use these, but say who's claiming them, because if someone "
            "pushes back this is all you've got:**"
        )
        for claim in careful:
            note = (
                "the sources don't agree on this one"
                if claim.evidence_status == "conflicted"
                else "one source only"
            )
            lines.append(f"- {_humanize(claim.title, titles)} ({note})")
        lines.append("")

    honest = sorted(graph.holes, key=lambda h: h.severity, reverse=True)
    if honest:
        lines.append(
            "**The honest-on-camera moments, if you want them.** Saying these "
            "out loud is what makes the rest believable:"
        )
        for hole in honest[:4]:
            missing = _humanize(hole.missing, titles)
            hurts = _humanize(hole.hurts_because, titles)
            lines.append(f"- {missing} {hurts}")
        lines.append("")

        chase = [h for h in honest if h.how_to_fill]
        if chase:
            lines.append("**And if you want to chase any of it down:**")
            for hole in chase[:4]:
                lines.append(f"- {_humanize(hole.how_to_fill, titles)}")
            lines.append("")

    return lines


def render_briefing(
    graph: ClaimGraph, source_titles: Optional[dict[str, str]] = None
) -> str:
    """Render the Claim Graph as the Research Briefing (Shape B).

    Named stories with the details told in place, the noticings, the
    landscape, and a derived "out loud" closer. Falls back to a minimal
    claims-only rendering when the telling layer is absent (a legacy graph),
    so old stored graphs still produce something readable.

    Args:
        graph: The validated claim graph, telling layer included.
        source_titles: Maps source_id to human-readable title.

    Returns:
        The Briefing as markdown.
    """
    titles = source_titles or {}
    lines: list[str] = [f"# {_clean_topic(graph.topic)}", ""]

    source_count = len({s.source_id for s in graph.sources_ranked}) or len(titles)
    if source_count:
        lines += [
            f"**Read this like I'm telling you what I found, because that's "
            f"what it is.** Everything here comes from the {source_count} "
            f"sources on this job. Where something's shaky, I say so in the "
            f"sentence.",
            "",
        ]

    lines += ["## The whole thing in one breath", ""]
    lines += [_humanize(graph.thesis.text, titles), ""]
    phrase = _THESIS_CONFIDENCE_PHRASE.get(graph.thesis.confidence, "")
    if phrase:
        lines += [f"*{phrase}*", ""]

    if graph.sections:
        for section in graph.sections:
            lines += [f"## {_sentence_case_header(_humanize(section.title, titles))}", ""]
            for paragraph in section.body.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    lines += [_humanize(paragraph, titles), ""]
    else:
        # Legacy graph without a telling layer: fall back to claim prose so
        # the document is still readable, without the old field anatomy.
        for claim in graph.claims_in_spine_order():
            lines += [f"## {_sentence_case_header(_humanize(claim.title, titles))}", ""]
            lines += [_humanize(claim.what_sources_say, titles), ""]
            if claim.my_read:
                lines += [_humanize(claim.my_read, titles), ""]

    if graph.noticings:
        lines += [
            "## The stuff that made me stop",
            "",
            "Little things that could be something, or nothing.",
            "",
        ]
        for noticing in graph.noticings:
            lines.append(f"- {_humanize(noticing.text, titles)}")
        lines.append("")

    if graph.landscape:
        lines += ["## What everyone already does with this topic", ""]
        lines += [_humanize(graph.landscape.everyone_does, titles), ""]
        if graph.landscape.nobody_has:
            lines += [_humanize(graph.landscape.nobody_has, titles), ""]

    lines += _render_out_loud(graph, titles)

    lines += [
        "---",
        "",
        "*Receipts: full quotes, timestamps and source text are in the source "
        "ledger that ships with this job. Nothing here is outside knowledge; "
        "if it's not in the sources, it's not in this document.*",
        "",
    ]

    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"
