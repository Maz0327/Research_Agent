"""
Shared markdown formatting helpers for document outputs.

These helpers provide consistent styling across all document types:
- Doc 0: Source Ledger
- Doc 1: Jump-Start Directions
- Doc 2: Semantic Brief
- Doc 3: Producer Packet
- Booster Expansion
- Research Brief Export

Usage:
    from backend.utils.markdown_helpers import (
        status_emoji,
        confidence_badge,
        type_icon,
        github_alert,
        section_header,
    )
"""

import re
from typing import Optional


# -----------------------------------------------------------------------------
# ID FORMATTING (Convert internal IDs to user-friendly labels)
# -----------------------------------------------------------------------------

# Mapping of ID prefixes to human-readable labels
ID_LABEL_MAP: dict[str, str] = {
    "SRC": "Source",
    "KP": "Key Point",
    "CLM": "Claim",
    "QT": "Quote",
    "OBS": "Observation",
    "THEME": "Theme",
    "TEN": "Tension",
    "GAP": "Open Question",
    "REF": "Reference",
    "EV": "Evidence",
    "ANG": "Angle",
}


def format_internal_id(id_str: str) -> str:
    """
    Convert internal ID to user-friendly label.

    Args:
        id_str: Internal ID (e.g., 'SRC_1', 'KP_12', 'TEN_3')

    Returns:
        User-friendly label (e.g., 'Source 1', 'Key Point 12', 'Tension 3')

    Examples:
        format_internal_id('SRC_1')    -> 'Source 1'
        format_internal_id('KP_12')    -> 'Key Point 12'
        format_internal_id('THEME_2')  -> 'Theme 2'
        format_internal_id('TEN_1')    -> 'Tension 1'
        format_internal_id('GAP_5')    -> 'Open Question 5'
        format_internal_id('unknown')  -> 'unknown' (passthrough)
    """
    if not id_str:
        return id_str

    match = re.match(r"^([A-Z]+)_(\d+)$", id_str)
    if not match:
        return id_str

    prefix, number = match.groups()
    label = ID_LABEL_MAP.get(prefix)

    if not label:
        return id_str
    return f"{label} {number}"


def format_id_list(ids: list[str], separator: str = ", ") -> str:
    """
    Format a list of internal IDs to user-friendly labels.

    Args:
        ids: List of internal IDs
        separator: String to join formatted IDs

    Returns:
        Formatted string with all IDs converted

    Example:
        format_id_list(['KP_1', 'KP_3', 'KP_7'])
        -> 'Key Point 1, Key Point 3, Key Point 7'
    """
    if not ids:
        return ""
    return separator.join(format_internal_id(id_str) for id_str in ids)


# -----------------------------------------------------------------------------
# STATUS AND BADGE HELPERS
# -----------------------------------------------------------------------------


def status_emoji(status: str) -> str:
    """
    Return emoji for source/item status.

    Args:
        status: Status string ('ingested', 'partial', 'failed', etc.)

    Returns:
        Emoji string
    """
    status_lower = status.lower() if status else ""
    return {
        "ingested": "✅",
        "partial": "⚠️",
        "failed": "❌",
        "success": "✅",
        "pending": "⏳",
        "error": "❌",
        "warning": "⚠️",
    }.get(status_lower, "❓")


def confidence_badge(level: str) -> str:
    """
    Return colored badge string for confidence level.

    Args:
        level: Confidence level ('high', 'medium', 'low')

    Returns:
        Badge string with emoji and label
    """
    level_lower = level.lower() if level else ""
    return {
        "high": "🟢 HIGH",
        "medium": "🟡 MEDIUM",
        "low": "🔴 LOW",
    }.get(level_lower, "⚪ UNKNOWN")


def type_icon(source_type: str) -> str:
    """
    Return icon for source/content type.

    Args:
        source_type: Type string ('youtube', 'article', etc.)

    Returns:
        Emoji icon
    """
    type_lower = source_type.lower() if source_type else ""
    return {
        "youtube": "📺",
        "article": "📄",
        "reddit": "💬",
        "text": "📝",
        "screenshot": "🖼️",
        "academic": "🎓",
        "news": "📰",
        "blog": "✍️",
        "podcast": "🎙️",
        "video": "🎬",
        "social": "📱",
        "interview": "🎤",
    }.get(type_lower, "📎")


def sensitivity_icon(level: str) -> str:
    """
    Return icon for sensitivity/risk level.

    Args:
        level: Sensitivity level ('low', 'medium', 'high', 'critical')

    Returns:
        Emoji icon
    """
    level_lower = level.lower() if level else ""
    return {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }.get(level_lower, "⚪")


def github_alert(alert_type: str, content: str) -> str:
    """
    Generate GitHub-style alert/admonition block.

    Types and colors:
    - NOTE: Blue - Background information
    - TIP: Green - Helpful suggestions
    - IMPORTANT: Purple - Key information
    - WARNING: Yellow - Potential issues
    - CAUTION: Red - Critical warnings

    Args:
        alert_type: One of 'NOTE', 'TIP', 'IMPORTANT', 'WARNING', 'CAUTION'
        content: Alert content (can be multiline)

    Returns:
        Formatted alert block
    """
    # Ensure each line starts with >
    lines = content.split("\n")
    formatted_lines = [f"> {line}" if not line.startswith(">") else line for line in lines]
    content_formatted = "\n".join(formatted_lines)

    return f"> [!{alert_type.upper()}]\n{content_formatted}"


def section_header(title: str, icon: str = "", level: int = 2) -> str:
    """
    Generate section header with optional icon.

    Args:
        title: Section title
        icon: Optional emoji icon
        level: Header level (1-6)

    Returns:
        Markdown header string
    """
    prefix = "#" * level
    icon_part = f"{icon} " if icon else ""
    return f"{prefix} {icon_part}{title}"


def triage_badge(level: str) -> str:
    """
    Return badge for triage/quality level.

    Args:
        level: Triage level ('ready', 'usable', 'thin', 'degraded', 'failed')

    Returns:
        Badge string with emoji and label
    """
    level_lower = level.lower() if level else ""
    return {
        "ready": "🟢 READY",
        "usable": "🟡 USABLE",
        "thin": "🟠 THIN",
        "degraded": "🔴 DEGRADED",
        "failed": "⛔ FAILED",
    }.get(level_lower, "❓ UNKNOWN")


def format_duration(seconds: Optional[int]) -> str:
    """
    Format duration in human-readable form.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., '12m 30s' or '1h 5m')
    """
    if not seconds:
        return ""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m {secs}s"


def escape_pipe(text: str) -> str:
    """
    Escape pipe characters in text for use inside markdown table cells.

    Unescaped pipe characters break markdown table rendering by creating
    extra columns. This replaces literal | with the escaped form \\|.

    Args:
        text: Text that may contain pipe characters

    Returns:
        Text with pipe characters escaped
    """
    if not text:
        return text
    return text.replace("|", "\\|")


def truncate_text(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """
    Truncate text to max length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def summary_stats_line(*stats: tuple[str, int | str]) -> str:
    """
    Generate inline stats summary.

    Args:
        stats: Tuples of (label, value)

    Returns:
        Formatted stats line (e.g., 'Sources: 5 | Points: 12 | Gaps: 3')

    Example:
        summary_stats_line(("Sources", 5), ("Points", 12), ("Gaps", 3))
        # Returns: "**Sources:** 5 | **Points:** 12 | **Gaps:** 3"
    """
    parts = [f"**{label}:** {value}" for label, value in stats]
    return " | ".join(parts)


def creative_notice_block() -> str:
    """
    Generate standard creative interpretation notice for producer outputs.

    Returns:
        Formatted notice block
    """
    return github_alert(
        "IMPORTANT",
        "**Creative Interpretation Notice**\n> \n> "
        "This content represents creative interpretation and storytelling suggestions, "
        "NOT factual research findings. Always verify claims independently."
    )


def directions_notice_block() -> str:
    """
    Generate standard directions notice for booster/research outputs.

    Returns:
        Formatted notice block
    """
    return github_alert(
        "NOTE",
        "**Research Directions Notice**\n> \n> "
        "These are research DIRECTIONS, not facts. "
        "They suggest WHERE to look, not WHAT you'll find."
    )
