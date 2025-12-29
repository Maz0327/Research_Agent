"""
Document generation helpers for pipeline output.

Contains functions to generate markdown documents from pipeline context data.
"""
from typing import Any

from backend.models.job_config import JobConfig


def generate_master_index(job_config: JobConfig, outputs: dict) -> str:
    """
    Generate master index document markdown.

    Args:
        job_config: Job configuration
        outputs: Dictionary of output markdown strings

    Returns:
        Master index markdown string
    """
    lines = [
        "# Master Index",
        "",
        f"**Topic:** {job_config.topic}",
        f"**Mode:** {job_config.mode.value}",
        "",
        "## Documents",
        "",
        "- [01 Research Map](#01-research-map)",
        "- [02 Source Shortlist](#02-source-shortlist)",
        "- [03 YouTube Index](#03-youtube-index)",
        "- [04 Transcripts](#04-transcripts)",
        "- [05 Web Extracts](#05-web-extracts)",
        "- [06 Quote Bank](#06-quote-bank)",
        "- [07 Claims Ledger](#07-claims-ledger)",
        "- [08 Evidence Table](#08-evidence-table)",
        "- [09 Missing Angles](#09-missing-angles)",
        "",
    ]
    return "\n".join(lines)


def generate_transcripts_md(transcripts: list) -> str:
    """
    Generate transcripts markdown document.

    Args:
        transcripts: List of TranscriptItem objects

    Returns:
        Transcripts markdown string
    """
    if not transcripts:
        return "# Transcripts\n\n*No transcripts available.*"

    lines = ["# Transcripts", ""]
    for transcript in transcripts:
        lines.append(f"## {transcript.video_id}")
        lines.append(f"**URL:** {transcript.video_url}")
        lines.append(f"**Status:** {transcript.status.value}")
        if transcript.text:
            lines.append(f"\n{transcript.text}\n")
        else:
            lines.append(f"*{transcript.error_message or 'Transcript not available'}*\n")
        lines.append("---\n")

    return "\n".join(lines)


def generate_web_extracts_md(web_sources: list) -> str:
    """
    Generate web extracts markdown document.

    Args:
        web_sources: List of SourceItem objects with captured content

    Returns:
        Web extracts markdown string
    """
    if not web_sources:
        return "# Web Extracts\n\n*No web sources available.*"

    lines = ["# Web Extracts", ""]
    for source in web_sources:
        lines.append(f"## {source.title}")
        lines.append(f"**URL:** {source.url}")
        lines.append(f"**Type:** {source.source_type.value}")
        if source.published_at:
            lines.append(f"**Published:** {source.published_at}")
        if source.text:
            lines.append(f"\n{source.text[:2000]}...")  # Limit extract length
        else:
            lines.append("*Content not available*")
        if source.notes:
            lines.append(f"\n*Note: {source.notes}*")
        lines.append("\n---\n")

    return "\n".join(lines)


def generate_evidence_table_md(evidence_records: list) -> str:
    """
    Generate evidence table markdown document.

    Args:
        evidence_records: List of EvidenceRecord objects

    Returns:
        Evidence table markdown string
    """
    if not evidence_records:
        return "# Evidence Table\n\n*No evidence records available.*"

    lines = [
        "# Evidence Table",
        "",
        "| Claim ID | Status | Evidence For | Evidence Against | Notes |",
        "|----------|--------|--------------|------------------|-------|",
    ]

    for record in evidence_records:
        claim_id = _get_attr(record, 'claim_id', 'N/A')
        status = _get_status_value(record)

        # Format evidence for
        evidence_for_str = _format_citations(_get_attr(record, 'evidence_for', []))

        # Format evidence against
        evidence_against_str = _format_citations(_get_attr(record, 'evidence_against', []))

        # Format notes (truncate and escape pipes)
        notes = _get_attr(record, 'notes', '')
        notes_str = (notes or "-")[:100].replace("|", "\\|").replace("\n", " ")

        lines.append(f"| {claim_id} | {status} | {evidence_for_str} | {evidence_against_str} | {notes_str} |")

    lines.append("")
    lines.append(f"**Total claims validated:** {len(evidence_records)}")

    # Summary statistics
    verified = sum(1 for r in evidence_records if _get_status_value(r) == 'Verified')
    debunked = sum(1 for r in evidence_records if _get_status_value(r) == 'Debunked')
    unproven = sum(1 for r in evidence_records if _get_status_value(r) == 'Unproven')

    lines.append(f"- Verified: {verified}")
    lines.append(f"- Debunked: {debunked}")
    lines.append(f"- Unproven: {unproven}")

    return "\n".join(lines)


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Get attribute from object or dict."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return default


def _get_status_value(record: Any) -> str:
    """Get status value from record object or dict."""
    if hasattr(record, 'status'):
        return record.status.value if hasattr(record.status, 'value') else str(record.status)
    if isinstance(record, dict):
        status = record.get('status', 'Unproven')
        return status.value if hasattr(status, 'value') else str(status)
    return 'Unproven'


def _format_citations(citations: list) -> str:
    """Format list of citations as markdown links."""
    links = []
    for citation in citations:
        url = _get_attr(citation, 'url', '')
        if url:
            links.append(f"[Link]({url})")
    return ", ".join(links) if links else "-"
