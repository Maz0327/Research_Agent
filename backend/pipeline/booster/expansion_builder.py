"""
Expansion Builder - Builds visually distinct markdown for Deep Research Expansion.

Based on: docs/authoritative/spec/GAPS_AND_BOOSTER_SPEC.md Part 2

The expansion section is appended to Doc 1 (Jump-Start Directions)
after a clear divider. It is visually distinct from the original content.
"""

from backend.models.booster_models import BoosterOutput
from backend.utils.markdown_helpers import (
    github_alert,
    section_header,
    directions_notice_block,
    type_icon,
)


def build_booster_expansion_markdown(output: BoosterOutput) -> str:
    """
    Build visually distinct booster expansion section for Doc 1.

    This section is appended to Jump-Start directions after a divider.
    It contains DIRECTIONS only, not facts.

    Args:
        output: Booster output with directions

    Returns:
        Markdown string for the expansion section
    """
    # Count directions for summary
    counts = {
        "perspectives": len(output.missing_perspectives),
        "sources": len(output.primary_source_directions),
        "queries": len(output.suggested_search_queries),
        "questions": len(output.research_questions),
    }
    total = output.total_directions

    lines = [
        "",
        "---",
        "",
        section_header("Deep Research Expansion", "🔬", 2),
        "",
    ]

    # Summary card
    lines.extend([
        github_alert(
            "NOTE",
            f"**Generated:** {output.booster_timestamp[:10]} | "
            f"**Total Directions:** {total}\n> \n> "
            f"👁️ {counts['perspectives']} perspectives | "
            f"📚 {counts['sources']} sources | "
            f"🔍 {counts['queries']} queries | "
            f"❓ {counts['questions']} questions"
        ),
        "",
        directions_notice_block(),
        "",
    ])

    # Check if output is empty
    if output.is_empty():
        lines.extend([
            "### No Additional Directions",
            "",
            github_alert(
                "NOTE",
                "The booster did not identify additional research directions.\n> \n> "
                "This may indicate the current sources provide comprehensive coverage, "
                "or that the identified gaps require domain-specific expertise to address."
            ),
            "",
        ])
        return "\n".join(lines)

    # Missing Perspectives
    if output.missing_perspectives:
        lines.extend([
            "### 👁️ Missing Perspectives to Seek",
            "",
        ])
        for mp in output.missing_perspectives:
            lines.extend([
                f"**{mp.description}**",
                "",
                f"- 💡 **Why it matters:** {mp.why_it_matters}",
            ])
            if mp.related_gaps:
                lines.append(f"- 🔗 **Related gaps:** `{', '.join(mp.related_gaps)}`")
            lines.append("")

    # Primary Sources
    if output.primary_source_directions:
        lines.extend([
            "### 📚 Primary Sources to Find",
            "",
            "| Type | Description | Search Approach |",
            "|:----:|-------------|-----------------|",
        ])
        for psd in output.primary_source_directions:
            source_type = psd.source_type.value.replace("_", " ").title()
            icon = type_icon(psd.source_type.value)
            # Escape pipe characters in content
            description = psd.description.replace("|", "\\|")
            search_suggestion = psd.search_suggestion.replace("|", "\\|")
            lines.append(f"| {icon} {source_type} | {description} | {search_suggestion} |")
        lines.append("")

    # Search Queries
    if output.suggested_search_queries:
        lines.extend([
            "### 🔍 Suggested Search Queries",
            "",
        ])
        for i, sq in enumerate(output.suggested_search_queries, 1):
            platform = sq.platform_suggestion.value.title()
            lines.extend([
                f"**{i}.** `{sq.query}`",
                "",
                f"| Purpose | Platform | Addresses |",
                f"|---------|----------|-----------|",
                f"| {sq.purpose} | {platform} | {sq.related_gap or '—'} |",
                "",
            ])

    # Research Questions
    if output.research_questions:
        lines.extend([
            "### ❓ Research Questions to Pursue",
            "",
        ])
        for rq in output.research_questions:
            lines.extend([
                f"> **{rq.question}**",
                "",
                f"- 💡 **Why:** {rq.why_it_matters}",
            ])
            if rq.related_theme:
                lines.append(f"- 🏷️ **Related theme:** {rq.related_theme}")
            lines.append("")

    # Footer
    lines.extend([
        "---",
        "",
        github_alert(
            "NOTE",
            "**Deep Research Expansion complete.**\n> \n> "
            "These are DIRECTIONS to explore, not established facts. "
            "Original source analysis appears above this section."
        ),
    ])

    return "\n".join(lines)


def build_booster_summary(output: BoosterOutput) -> dict:
    """
    Build a summary dict of booster output for API response.

    Args:
        output: Booster output

    Returns:
        Summary dictionary with counts
    """
    return {
        "perspectives_count": len(output.missing_perspectives),
        "source_directions_count": len(output.primary_source_directions),
        "queries_count": len(output.suggested_search_queries),
        "questions_count": len(output.research_questions),
        "total_directions": output.total_directions,
        "is_empty": output.is_empty(),
        "timestamp": output.booster_timestamp,
        "context_hash": output.context_bundle_hash,
    }
