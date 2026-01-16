"""Cross-Reference Stage - Compare new extractions against original content.

Based on: docs/authoritative/spec/EXTENDED_SPECIFICATIONS.md Part 2

This stage runs when new sources are added to an existing completed job.
It compares new semantic extractions against the original analysis to find:
- Supports: New content reinforcing existing themes/points
- Contradicts: New content conflicting with existing points
- New Tensions: Cross-source conflicts
- New Gaps: Previously unidentified missing information

Consumes: ctx.original_extractions, ctx.semantic_extractions (new)
Produces: ctx.cross_reference_notes
"""

from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.document_outputs import CrossReferenceNotes
from backend.models.semantic_units import (
    Gap,
    SemanticExtractionResult,
    Tension,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.prompts.cross_reference_prompt import (
    build_cross_reference_prompt,
    CROSS_REFERENCE_ROLE,
)
from backend.state import update_job


def extract_themes_from_extractions(
    extractions: list[SemanticExtractionResult],
) -> list[dict]:
    """Extract themes from extraction results as dicts."""
    themes = []
    for extraction in extractions:
        for theme in extraction.themes:
            themes.append({
                "theme_id": theme.theme_id,
                "label": theme.label,
                "description": theme.description,
                "related_key_points": theme.related_key_points,
                "source_id": extraction.source_id,
            })
    return themes


def extract_key_points_from_extractions(
    extractions: list[SemanticExtractionResult],
) -> list[dict]:
    """Extract key points from extraction results as dicts."""
    key_points = []
    for extraction in extractions:
        for kp in extraction.key_points:
            key_points.append({
                "key_point_id": kp.key_point_id,
                "statement": kp.statement,
                "source_ids": kp.source_ids,
                "confidence": kp.confidence.value,
            })
    return key_points


def extract_tensions_from_extractions(
    extractions: list[SemanticExtractionResult],
) -> list[dict]:
    """Extract tensions from extraction results as dicts."""
    tensions = []
    for extraction in extractions:
        for tension in extraction.tensions:
            tensions.append({
                "tension_id": tension.tension_id,
                "description": tension.description,
                "involved_key_points": tension.involved_key_points,
            })
    return tensions


def parse_cross_reference_response(response_data: dict[str, Any]) -> CrossReferenceNotes:
    """
    Parse Gemini response into CrossReferenceNotes.

    Args:
        response_data: Parsed JSON from Gemini

    Returns:
        CrossReferenceNotes with supports, contradicts, new_tensions, new_gaps
    """
    supports = response_data.get("supports", [])
    contradicts = response_data.get("contradicts", [])

    # Parse new tensions
    new_tensions = []
    for tension_data in response_data.get("new_tensions", []):
        tension = Tension(
            tension_id=tension_data.get("tension_id", f"TEN_{len(new_tensions) + 1}"),
            description=tension_data.get("description", ""),
            involved_key_points=tension_data.get("involved_ids", []),
            is_cross_source=tension_data.get("is_cross_source", True),
        )
        new_tensions.append(tension)

    # Parse new gaps
    new_gaps = []
    for gap_data in response_data.get("new_gaps", []):
        gap = Gap(
            gap_id=gap_data.get("gap_id", f"GAP_{len(new_gaps) + 1}"),
            description=gap_data.get("description", ""),
            why_expected=gap_data.get("why_expected", ""),
            related_key_points=gap_data.get("related_new_ids", []),
        )
        new_gaps.append(gap)

    return CrossReferenceNotes(
        supports=supports,
        contradicts=contradicts,
        new_tensions=new_tensions,
        new_gaps=new_gaps,
    )


def stage_cross_reference(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Cross-reference new extractions against original content.

    PREREQUISITE: Must have both original_extractions and new semantic_extractions.

    This stage:
    1. Extracts themes/key_points/tensions from original analysis
    2. Extracts themes/key_points from new extractions
    3. Calls Gemini to find supports/contradicts/new_tensions
    4. Stores cross-reference notes in context

    Output is used by addendum_assembly to create cross-reference section.
    """
    logger.info(f"[{ctx.job_id}] Stage: Cross-Reference Analysis")

    update_job(
        ctx.job_id,
        stage="cross_reference",
        progress_percent=75,
    )

    # Check prerequisites
    original_extractions = getattr(ctx, "original_extractions", [])
    new_extractions = getattr(ctx, "semantic_extractions", [])

    if not original_extractions:
        logger.warning("No original extractions found - skipping cross-reference")
        ctx.add_warning("Cross-reference skipped: no original extractions")
        return

    if not new_extractions:
        logger.warning("No new extractions found - skipping cross-reference")
        ctx.add_warning("Cross-reference skipped: no new extractions")
        return

    # Extract structured content from original analysis
    existing_themes = extract_themes_from_extractions(original_extractions)
    existing_key_points = extract_key_points_from_extractions(original_extractions)
    existing_tensions = extract_tensions_from_extractions(original_extractions)

    # Extract structured content from new extractions
    new_key_points = extract_key_points_from_extractions(new_extractions)
    new_themes = extract_themes_from_extractions(new_extractions)

    # Build prompt
    prompt = build_cross_reference_prompt(
        existing_themes=existing_themes,
        existing_key_points=existing_key_points,
        existing_tensions=existing_tensions,
        new_key_points=new_key_points,
        new_themes=new_themes,
        original_source_count=len(original_extractions),
        new_source_count=len(new_extractions),
    )

    try:
        # Initialize Gemini client
        gemini_client = GeminiClient()

        # Call Gemini for cross-reference analysis
        response = gemini_client.generate_json(
            prompt=prompt,
            system_message=CROSS_REFERENCE_ROLE,
        )

        if "error" in response:
            logger.error(f"Gemini error during cross-reference: {response['error']}")
            ctx.add_warning(f"Cross-reference error: {response['error']}")
            return

        # Track cost
        cost = response.get("cost", 0)
        if hasattr(ctx, "add_cost"):
            ctx.add_cost("gemini_cross_reference", cost)

        # Parse response
        data = response.get("data", {})
        cross_ref_notes = parse_cross_reference_response(data)

        # Store results in context
        ctx.cross_reference_notes = cross_ref_notes

        # Extract summary for logging
        summary = data.get("summary", {})
        supports_count = summary.get("supports_count", len(cross_ref_notes.supports))
        contradicts_count = summary.get("contradicts_count", len(cross_ref_notes.contradicts))
        new_tensions_count = summary.get("new_tensions_count", len(cross_ref_notes.new_tensions))
        new_gaps_count = summary.get("new_gaps_count", len(cross_ref_notes.new_gaps))
        overall_alignment = summary.get("overall_alignment", "neutral")

        logger.info(
            f"Cross-reference complete: "
            f"supports={supports_count}, "
            f"contradicts={contradicts_count}, "
            f"new_tensions={new_tensions_count}, "
            f"new_gaps={new_gaps_count}, "
            f"alignment={overall_alignment}, "
            f"cost=${cost:.4f}"
        )

        # Update job with cross-reference summary
        update_job(
            ctx.job_id,
            partial_outputs={
                "cross_reference_summary": {
                    "supports_count": supports_count,
                    "contradicts_count": contradicts_count,
                    "new_tensions_count": new_tensions_count,
                    "new_gaps_count": new_gaps_count,
                    "overall_alignment": overall_alignment,
                    "cost": cost,
                }
            },
        )

    except Exception as e:
        logger.error(f"Cross-reference failed: {e}")
        ctx.add_warning(f"Cross-reference error: {str(e)}")
        # Set default empty cross-reference notes
        ctx.cross_reference_notes = CrossReferenceNotes()


def run_cross_reference_analysis(
    original_extractions: list[SemanticExtractionResult],
    new_extractions: list[SemanticExtractionResult],
) -> tuple[CrossReferenceNotes, float]:
    """
    Standalone function to run cross-reference analysis.

    Useful for testing or when not using full pipeline context.

    Args:
        original_extractions: Extractions from original job
        new_extractions: Extractions from new sources

    Returns:
        Tuple of (CrossReferenceNotes, cost)
    """
    # Extract structured content
    existing_themes = extract_themes_from_extractions(original_extractions)
    existing_key_points = extract_key_points_from_extractions(original_extractions)
    existing_tensions = extract_tensions_from_extractions(original_extractions)
    new_key_points = extract_key_points_from_extractions(new_extractions)
    new_themes = extract_themes_from_extractions(new_extractions)

    # Build prompt
    prompt = build_cross_reference_prompt(
        existing_themes=existing_themes,
        existing_key_points=existing_key_points,
        existing_tensions=existing_tensions,
        new_key_points=new_key_points,
        new_themes=new_themes,
        original_source_count=len(original_extractions),
        new_source_count=len(new_extractions),
    )

    # Call Gemini
    gemini_client = GeminiClient()
    response = gemini_client.generate_json(
        prompt=prompt,
        system_message=CROSS_REFERENCE_ROLE,
    )

    if "error" in response:
        raise RuntimeError(f"Cross-reference failed: {response['error']}")

    cost = response.get("cost", 0)
    data = response.get("data", {})
    cross_ref_notes = parse_cross_reference_response(data)

    return cross_ref_notes, cost
