"""
Context Bundle Generator - Generates constrained input for Deep Research Booster.

Based on: docs/authoritative/spec/GAPS_AND_BOOSTER_SPEC.md Part 2

The Context Bundle is AUTO-GENERATED from job output.
User provides NOTHING.

What is NOT in the Context Bundle (to prevent hallucination):
- Full transcript text
- Verbatim quotes
- Doc 0 content
- Full key point objects with claims
- Source URLs or metadata
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from backend.models.booster_models import (
    ContextBundle,
    GapSummary,
    TensionSummary,
    ThemeSummary,
)


def generate_context_bundle(
    job_id: str,
    jump_start: dict[str, Any],
    semantic_brief: dict[str, Any],
    extractions: list[dict[str, Any]],
) -> ContextBundle:
    """
    Generate Context Bundle from completed job output.

    The Context Bundle contains ONLY:
    - Scope (in/out from Doc 1)
    - Themes (labels and descriptions only)
    - Key point summaries (statements only, no claims/quotes)
    - Tensions (descriptions only)
    - Gaps (descriptions only)
    - Metadata (source count, types, confidence)

    It does NOT contain:
    - Full transcript text
    - Verbatim quotes
    - Source URLs
    - Claims with verification status

    Args:
        job_id: Job identifier
        jump_start: Doc 1 data (JumpStartDirections)
        semantic_brief: Doc 2 data (SemanticBrief)
        extractions: List of extraction results

    Returns:
        ContextBundle for booster input
    """
    # Extract scope from jump_start
    scope_lock = jump_start.get("scope_lock", {})
    scope_in = scope_lock.get("in", [])
    scope_out = scope_lock.get("out", [])

    # Handle different scope structures
    if isinstance(scope_in, dict):
        scope_in = scope_in.get("in", [])
    if isinstance(scope_out, dict):
        scope_out = scope_out.get("out", [])

    # Extract themes from semantic_brief (labels and descriptions only)
    themes = []
    for theme_data in semantic_brief.get("themes", []):
        themes.append(ThemeSummary(
            theme_id=theme_data.get("theme_id", ""),
            label=theme_data.get("label", ""),
            description=theme_data.get("description", ""),
        ))

    # Extract key point summaries (statements only, NO quotes or claims)
    key_point_summaries = []
    for kp in semantic_brief.get("key_points", []):
        statement = kp.get("statement", "")
        if statement:
            key_point_summaries.append(statement)

    # Limit to avoid context bloat
    key_point_summaries = key_point_summaries[:20]

    # Extract tensions (descriptions only, NO resolution hints)
    tensions = []
    for tension_data in semantic_brief.get("tensions", []):
        tensions.append(TensionSummary(
            tension_id=tension_data.get("tension_id", ""),
            description=tension_data.get("description", ""),
        ))

    # Extract gaps from jump_start
    gaps = []
    for gap_data in jump_start.get("gaps", []):
        gaps.append(GapSummary(
            gap_id=gap_data.get("gap_id", ""),
            description=gap_data.get("description", ""),
        ))

    # Metadata
    corpus = jump_start.get("current_corpus", {})
    source_count = corpus.get("source_count", len(extractions))
    source_types = corpus.get("perspectives_represented", [])

    # Handle different confidence structures
    confidence_data = semantic_brief.get("confidence", {})
    if isinstance(confidence_data, dict):
        confidence = confidence_data.get("overall", "medium")
    else:
        confidence = str(confidence_data) if confidence_data else "medium"

    return ContextBundle(
        scope_in=scope_in,
        scope_out=scope_out,
        themes=themes,
        key_point_summaries=key_point_summaries,
        tensions=tensions,
        gaps=gaps,
        source_count=source_count,
        source_types=source_types,
        confidence_level=confidence,
        job_id=job_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def compute_bundle_hash(bundle: ContextBundle) -> str:
    """
    Compute SHA256 hash of context bundle for verification.

    Used to verify that booster output corresponds to a specific bundle.

    Args:
        bundle: Context bundle to hash

    Returns:
        16-character hex hash
    """
    bundle_dict = {
        "job_id": bundle.job_id,
        "scope_in": bundle.scope_in,
        "themes": [t.theme_id for t in bundle.themes],
        "gaps": [g.gap_id for g in bundle.gaps],
        "source_count": bundle.source_count,
        "generated_at": bundle.generated_at,
    }
    json_str = json.dumps(bundle_dict, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def bundle_to_prompt_format(bundle: ContextBundle) -> dict[str, str]:
    """
    Format context bundle data for prompt insertion.

    Args:
        bundle: Context bundle

    Returns:
        Dictionary with formatted strings for prompt placeholders
    """
    # Format themes
    themes_str = "\n".join([
        f"- {t.theme_id}: {t.label} — {t.description}"
        for t in bundle.themes
    ]) or "(No themes identified)"

    # Format key points
    key_points_str = "\n".join([
        f"- {kp}" for kp in bundle.key_point_summaries
    ]) or "(No key points)"

    # Format tensions
    tensions_str = "\n".join([
        f"- {t.tension_id}: {t.description}"
        for t in bundle.tensions
    ]) or "(No tensions identified)"

    # Format gaps
    gaps_str = "\n".join([
        f"- {g.gap_id}: {g.description}"
        for g in bundle.gaps
    ]) or "(No gaps identified)"

    return {
        "job_id": bundle.job_id,
        "source_count": str(bundle.source_count),
        "confidence_level": bundle.confidence_level,
        "scope_in": ", ".join(bundle.scope_in) or "(Not specified)",
        "scope_out": ", ".join(bundle.scope_out) or "(Not specified)",
        "themes": themes_str,
        "key_points": key_points_str,
        "tensions": tensions_str,
        "gaps": gaps_str,
        "source_types": ", ".join(bundle.source_types) or "(Unknown)",
    }
