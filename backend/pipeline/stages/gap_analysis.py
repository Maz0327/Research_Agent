"""
Gap Analysis Stage - Identify research gaps from semantic extractions.

This stage analyzes what's MISSING from the research corpus by comparing
what is present vs what would normally be expected for the topic.

Based on: docs/authoritative/spec/RASS.md Section 4.4
Consumes: ctx.semantic_extractions (from semantic_extraction stage)
Produces: ctx.identified_gaps (list of Gap objects)
"""

from typing import Any

from loguru import logger

# NOTE: GeminiClient imported lazily inside stage_gap_analysis() to break
# circular import: gemini_client → pipeline → stages/__init__ → gap_analysis → gemini_client
from backend.models.semantic_units import Gap
from backend.pipeline.context import PipelineContext
from backend.pipeline.prompts.semantic_synthesis_prompt import build_gap_identification_prompt
from backend.state import update_job


def parse_gap_response(response_data: dict[str, Any]) -> list[Gap]:
    """
    Parse Gemini response into Gap objects.

    Args:
        response_data: JSON response from Gemini

    Returns:
        List of Gap objects
    """
    gaps = []

    for gap_data in response_data.get("gaps", []):
        gap = Gap(
            gap_id=gap_data.get("gap_id", f"GAP_{len(gaps) + 1}"),
            description=gap_data.get("description", ""),
            why_expected=gap_data.get("why_expected", ""),
            related_themes=gap_data.get("related_themes", []),
            related_key_points=gap_data.get("related_key_points", []),
            suggested_research_direction=gap_data.get("suggested_research_direction"),
        )
        gaps.append(gap)

    return gaps


def build_source_manifest(ctx: PipelineContext) -> list[dict]:
    """
    Build source manifest from identity packages for gap identification.

    Returns list of {source_id, type, title, status} dicts.
    """
    manifest = []

    packages = getattr(ctx, "source_identity_packages", [])
    for pkg in packages:
        manifest.append({
            "source_id": pkg.source_id,
            "type": pkg.source_type,
            "title": pkg.title,
            "status": "ingested" if pkg.is_accessible else "failed",
        })

    return manifest


def aggregate_semantic_units(ctx: PipelineContext) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Aggregate key points, themes, and tensions from all extractions.

    Returns:
        Tuple of (key_points, themes, tensions) as lists of dicts
    """
    key_points = []
    themes = []
    tensions = []

    extractions = getattr(ctx, "semantic_extractions", [])
    for extraction in extractions:
        # Key points
        for kp in extraction.key_points:
            key_points.append({
                "key_point_id": kp.key_point_id,
                "statement": kp.statement,
                "source_ids": kp.source_ids,
                "confidence": kp.confidence.value,
            })

        # Themes
        for theme in extraction.themes:
            themes.append({
                "theme_id": theme.theme_id,
                "label": theme.label,
                "description": theme.description,
                "related_key_points": theme.related_key_points,
            })

        # Tensions
        for tension in extraction.tensions:
            tensions.append({
                "tension_id": tension.tension_id,
                "description": tension.description,
                "involved_key_points": tension.involved_key_points,
            })

    return key_points, themes, tensions


def stage_gap_analysis(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Identify gaps in research coverage.

    PREREQUISITE: semantic_extraction stage must run first to populate
    ctx.semantic_extractions with SemanticExtractionResult objects.

    This stage:
    1. Builds source manifest from identity packages
    2. Aggregates semantic units from all extractions
    3. Calls Gemini to identify gaps
    4. Stores Gap objects in ctx.identified_gaps

    Stage failures are handled gracefully - an empty gaps list is valid
    and indicates comprehensive coverage.
    """
    logger.info(f"[{ctx.job_id}] Stage: Gap Analysis")

    update_job(
        ctx.job_id,
        stage="gap_analysis",
        progress_percent=55,
    )

    # Initialize storage for gaps
    if not hasattr(ctx, "identified_gaps"):
        ctx.identified_gaps = []

    # Check prerequisites
    extractions = getattr(ctx, "semantic_extractions", [])
    if not extractions:
        logger.warning("No semantic extractions found - skipping gap analysis")
        ctx.add_warning("Gap analysis skipped: no semantic extractions available")
        return

    # Build inputs for gap identification
    source_manifest = build_source_manifest(ctx)
    key_points, themes, tensions = aggregate_semantic_units(ctx)

    # Build scope lock from topic
    scope_lock = f"Research topic: {ctx.topic}"
    if hasattr(ctx, "scope_in") and ctx.scope_in:
        scope_lock += f"\nIn scope: {', '.join(ctx.scope_in)}"
    if hasattr(ctx, "scope_out") and ctx.scope_out:
        scope_lock += f"\nOut of scope: {', '.join(ctx.scope_out)}"

    # Build prompt
    prompt = build_gap_identification_prompt(
        scope_lock=scope_lock,
        source_manifest=source_manifest,
        key_points=key_points,
        themes=themes,
        tensions=tensions,
    )

    try:
        # Lazy import to break circular import chain
        from backend.integrations.gemini_client import GeminiClient

        # Initialize Gemini client
        gemini_client = GeminiClient()

        # Call Gemini for gap identification
        response = gemini_client.generate_json(
            prompt=prompt,
            system_message="You are a research completeness checker. Identify what's MISSING, not what's present.",
        )

        if "error" in response:
            logger.error(f"Gemini error during gap analysis: {response['error']}")
            ctx.add_warning(f"Gap analysis error: {response['error']}")
            return

        # Track cost
        cost = response.get("cost", 0)
        if hasattr(ctx, "add_cost"):
            ctx.add_cost("gemini_gap_analysis", cost)

        # Parse response
        data = response.get("data", {})
        gaps = parse_gap_response(data)

        # Store gaps in context
        ctx.identified_gaps = gaps

        logger.info(
            f"Gap analysis complete: {len(gaps)} gaps identified, cost=${cost:.4f}"
        )

        # Log gap summary
        if gaps:
            for gap in gaps[:3]:  # Log first 3 gaps
                logger.debug(f"  GAP: {gap.description[:60]}...")

        # Update job with gap analysis summary
        update_job(
            ctx.job_id,
            partial_outputs={
                "gap_analysis_summary": {
                    "gaps_identified": len(gaps),
                    "gap_ids": [g.gap_id for g in gaps],
                    "cost": cost,
                }
            },
        )

    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")
        ctx.add_warning(f"Gap analysis error: {str(e)}")
        # Don't fail the pipeline - empty gaps is valid
        ctx.identified_gaps = []
