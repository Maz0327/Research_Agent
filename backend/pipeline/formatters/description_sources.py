"""The source list a video description carries, built by code.

This is the one part of the retired Creator Brief worth keeping (work order
item 16). It was being written by a model, which is the wrong tool: a
description's source list is a transcription of Doc 0, and any deviation from
Doc 0 is an error rather than a style.
"""

from collections.abc import Iterable
from typing import Optional


def build_description_sources(
    sources: Iterable[dict], include_inaccessible: bool = False
) -> list[dict]:
    """Build the source list for a video description, straight from Doc 0.

    Args:
        sources: Doc 0 source entries.
        include_inaccessible: When True, sources whose text never arrived are
            listed too. They are excluded by default: a description credits
            what the video actually drew on.

    Returns:
        List of dicts with `source_id`, `title`, `creator`, and `url`, in
        ledger order, with republications marked so a description does not
        credit the same article twice as if it were two.
    """
    listed: list[dict] = []
    for source in sources:
        source_id = source.get("source_id")
        if not source_id:
            continue
        if not include_inaccessible and not (source.get("full_text") or "").strip():
            continue
        listed.append(
            {
                "source_id": source_id,
                "title": (source.get("title") or "Untitled").strip(),
                "creator": (source.get("creator") or None),
                "url": (source.get("url") or None),
                "duplicate_of": source.get("duplicate_of"),
            }
        )
    return listed


def render_description_sources(
    sources: Iterable[dict], header: Optional[str] = "Sources"
) -> str:
    """Render the source list as the plain text a description box takes.

    Args:
        sources: Output of `build_description_sources`.
        header: Optional heading line.

    Returns:
        Plain text, one source per line, republications noted.
    """
    lines = [header] if header else []
    for source in sources:
        line = source["title"]
        if source.get("creator"):
            line += f" - {source['creator']}"
        if source.get("url"):
            line += f"\n{source['url']}"
        if source.get("duplicate_of"):
            line += " (republication)"
        lines.append(line)
    return "\n".join(lines)
