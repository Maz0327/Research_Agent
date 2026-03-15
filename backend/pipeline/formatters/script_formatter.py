"""Script Markdown Formatter — Doc 5.

Produces polished, copy-paste-ready markdown from a ScriptDocument.
"""

from datetime import datetime, timezone

from backend.models.script_models import ScriptDocument


def format_script(
    script: ScriptDocument,
    *,
    include_provenance_footer: bool = True,
) -> str:
    """Convert a ScriptDocument to polished markdown.

    Args:
        script: Validated ScriptDocument.
        include_provenance_footer: Whether to add provenance chain footer.

    Returns:
        Polished markdown string.
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    lines: list[str] = []

    # Header
    lines += [
        f"# {script.title}",
        "",
        f"*{now} · {script.source_count} source{'s' if script.source_count != 1 else ''} · "
        f"{script.estimated_duration} · {script.tone} · Doc 5*",
        "",
        f"**Story Arc:** {script.story_arc} | "
        f"**Word Count:** {script.total_word_count:,} | "
        f"**Target:** {script.target_length}",
        "",
        "---",
        "",
    ]

    # Hook
    lines += [
        "## Opening Hook",
        "",
        f"> {script.hook.text}",
        "",
        f"*Type: {script.hook.hook_type} · Source: {script.hook.source_id}*",
        "",
        "---",
        "",
    ]

    # Sections
    for section in script.sections:
        lines += [
            f"## [{section.beat_label}] {section.section_id}",
            "",
        ]
        if section.stage_direction:
            lines += [f"*{section.stage_direction}*", ""]
        lines += [
            section.spoken_text,
            "",
            f"*Duration: {section.duration_estimate}*",
        ]
        if section.source_ids:
            refs = ", ".join(section.source_ids)
            lines.append(f"*Sources: {refs}*")
        lines += ["", "---", ""]

    # Outro
    lines += [
        "## Outro",
        "",
        f"> {script.outro.text}",
        "",
    ]
    if script.outro.call_to_action:
        lines += [f"**{script.outro.call_to_action}**", ""]

    # Sources
    if script.description_sources:
        lines += [
            "---",
            "",
            "## Sources",
            "",
        ]
        for ds in script.description_sources:
            title = ds.get("title", "Unknown")
            url = ds.get("url", "")
            creator = ds.get("creator", "")
            source_id = ds.get("source_id", "")

            line = f"- **{title}**"
            if creator:
                line += f" by {creator}"
            if url:
                line += f" — [{url}]({url})"
            if source_id:
                line += f" ({source_id})"
            lines.append(line)
        lines.append("")

    # Provenance footer
    if include_provenance_footer:
        lines += [
            "---",
            "",
            "*Every factual claim traces to a Doc 2 key point and a Doc 0 source.*",
            "",
        ]

    return "\n".join(lines)


def format_script_from_dict(script_dict: dict, **kwargs: object) -> str:
    """Convenience wrapper — parse dict then format.

    Args:
        script_dict: ScriptDocument as dict.
        **kwargs: Passed to format_script().

    Returns:
        Polished markdown string.
    """
    script = ScriptDocument(**script_dict)
    return format_script(script, **kwargs)
