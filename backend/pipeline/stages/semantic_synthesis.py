"""
Semantic Synthesis Stage - Create unified semantic understanding.

This stage synthesizes a coherent semantic understanding from all
extracted semantic units across sources. It produces:
- Semantic Core (2-4 sentence description of topic's essence)
- Synthesized Themes (cross-source patterns)
- Confidence Assessment (calibrated for source quality)
- Speculative Observations (explicitly labeled)

Based on: docs/authoritative/spec/RASS.md Section 4.5
Consumes: ctx.semantic_extractions + ctx.identified_gaps
Produces: ctx.semantic_core, ctx.synthesized_themes, ctx.speculative_observations
"""

from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.semantic_units import (
    ConfidenceLevel,
    Theme,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.prompts.semantic_synthesis_prompt import (
    build_semantic_synthesis_prompt,
    SEMANTIC_SYNTHESIS_ROLE,
)
from backend.pipeline.style_enforcer import enforce_style
from backend.pipeline.text_similarity import group_matching
from backend.pipeline.theme_dedup import merge_similar_themes
from backend.state import update_job


def aggregate_for_synthesis(ctx: PipelineContext) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """
    Aggregate semantic units for synthesis prompt.

    Returns:
        Tuple of (key_points, themes, tensions, gaps) as lists of dicts
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

    # Gaps from gap analysis stage
    gaps = []
    for gap in getattr(ctx, "identified_gaps", []):
        gaps.append({
            "gap_id": gap.gap_id,
            "description": gap.description,
            "why_expected": gap.why_expected,
            "related_themes": gap.related_themes,
            "related_key_points": gap.related_key_points,
        })

    return key_points, themes, tensions, gaps


def build_source_coverage(
    key_points: list[dict],
    duplicate_of: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Map each key point to every source that independently says it.

    Extraction is source-isolated, so a key point's own `source_ids` always
    names exactly one source. Corroboration therefore cannot be read off the
    extraction: it has to be measured by matching what the sources say, which
    is what this does. Before the fix, coverage was simply copied from
    `source_ids` and every key point read as single-source.

    Syndicated copies are folded into their canonical source first, so a wire
    story republished four times counts once (the SRC_7/SRC_8 case).

    Args:
        key_points: Aggregated key-point dicts with `key_point_id`,
            `statement`, and `source_ids`.
        duplicate_of: Optional map of duplicate source ID to canonical source
            ID, from the syndication detector.

    Returns:
        Dict mapping key_point_id to the sorted list of supporting source IDs.
    """
    duplicate_of = duplicate_of or {}

    def canonical(source_id: str) -> str:
        return duplicate_of.get(source_id, source_id)

    groups = group_matching(
        (kp["key_point_id"], kp.get("statement", "")) for kp in key_points
    )

    sources_by_group: dict[str, set[str]] = {}
    for kp in key_points:
        group_id = groups.get(kp["key_point_id"], kp["key_point_id"])
        supporting = {canonical(s) for s in kp.get("source_ids", []) if s}
        sources_by_group.setdefault(group_id, set()).update(supporting)

    return {
        kp["key_point_id"]: sorted(
            sources_by_group.get(groups.get(kp["key_point_id"], kp["key_point_id"]), set())
        )
        for kp in key_points
    }


def aggregate_for_synthesis_with_attribution(
    ctx: PipelineContext
) -> tuple[list[dict], list[dict], list[dict], list[dict], dict, list]:
    """
    Aggregate semantic units with source attribution tracking (Phase 5).

    In addition to aggregating units, this function:
    1. Tracks which sources support each key point (source_coverage)
    2. Detects potential cross-source conflicts

    Returns:
        Tuple of (key_points, themes, tensions, gaps, source_coverage, potential_conflicts)
    """
    key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

    # Phase 5: Build source coverage map (key_point_id → [source_ids])
    source_coverage = build_source_coverage(
        key_points,
        duplicate_of=getattr(ctx, "duplicate_sources", None),
    )

    # Phase 5: Detect potential cross-source conflicts
    # A conflict exists when key points from different sources make contradictory claims
    potential_conflicts = detect_cross_source_conflicts(key_points, source_coverage)

    # Store in context for downstream use
    ctx.source_coverage = source_coverage
    ctx.cross_source_conflicts = potential_conflicts

    # Calculate source contributions
    source_contributions = {}
    for extraction in getattr(ctx, "semantic_extractions", []):
        src_id = extraction.source_id
        source_contributions[src_id] = {
            "key_points": len(extraction.key_points),
            "claims": len(extraction.claims),
            "quotes": len(extraction.quotes),
            "themes": len(extraction.themes),
            "tensions": len(extraction.tensions),
        }
    ctx.source_contributions = source_contributions

    return key_points, themes, tensions, gaps, source_coverage, potential_conflicts


def detect_cross_source_conflicts(
    key_points: list[dict],
    source_coverage: dict
) -> list[dict]:
    """
    Detect potential conflicts between key points from different sources.

    This is a heuristic-based detection that flags:
    - Key points with LOW confidence that contradict HIGH confidence points
    - Key points from different sources about similar topics with different conclusions

    Returns:
        List of conflict dicts with structure:
        {
            "key_point_a": str,
            "key_point_b": str,
            "sources_a": list[str],
            "sources_b": list[str],
            "conflict_type": "potential_contradiction" | "confidence_mismatch"
        }
    """
    conflicts = []

    # Build lookup for quick access
    kp_by_id = {kp["key_point_id"]: kp for kp in key_points}

    # Check for confidence mismatches between sources
    for i, kp_a in enumerate(key_points):
        sources_a = set(kp_a.get("source_ids", []))
        conf_a = kp_a.get("confidence", "medium")

        for kp_b in key_points[i + 1:]:
            sources_b = set(kp_b.get("source_ids", []))
            conf_b = kp_b.get("confidence", "medium")

            # Only flag if different sources
            if sources_a & sources_b:
                continue

            # Flag significant confidence mismatches on related topics
            # (Full semantic similarity would require LLM, so we use heuristics)
            if conf_a == "high" and conf_b == "low" or conf_a == "low" and conf_b == "high":
                # Weak signal — could be conflict or different aspects.
                # Track for downstream review but don't resolve automatically.
                conflicts.append({
                    "key_point_a": kp_a.get("statement", kp_a.get("key_point_id", "")),
                    "key_point_b": kp_b.get("statement", kp_b.get("key_point_id", "")),
                    "sources_a": list(sources_a),
                    "sources_b": list(sources_b),
                    "conflict_type": "confidence_mismatch",
                })

    return conflicts


def calculate_verification_rate(ctx: PipelineContext) -> float:
    """Calculate percentage of claims with verified quotes."""
    total_claims = 0
    verified_claims = 0

    for extraction in getattr(ctx, "semantic_extractions", []):
        for claim in extraction.claims:
            total_claims += 1
            if claim.supporting_quotes:
                verified_claims += 1

    if total_claims == 0:
        return 0.0

    return verified_claims / total_claims


def parse_synthesis_response(response_data: dict[str, Any]) -> dict:
    """
    Parse Gemini response into synthesis outputs.

    Returns:
        Dict with semantic_core, themes, tensions, gaps, speculative_observations, confidence
    """
    result = {
        "semantic_core": "",
        "semantic_core_based_on": [],
        "themes": [],
        "theme_merges": [],
        "speculative_observations": [],
        "confidence_level": ConfidenceLevel.MEDIUM,
        "confidence_reasoning": [],
    }

    # Parse semantic core
    semantic_core_data = response_data.get("semantic_core", {})
    if isinstance(semantic_core_data, dict):
        result["semantic_core"] = semantic_core_data.get("text", "")
        result["semantic_core_based_on"] = semantic_core_data.get("based_on", [])
    elif isinstance(semantic_core_data, str):
        result["semantic_core"] = semantic_core_data

    # Parse synthesized themes
    for theme_data in response_data.get("themes", []):
        theme = Theme(
            theme_id=theme_data.get("theme_id", f"THEME_{len(result['themes']) + 1}"),
            label=theme_data.get("label", theme_data.get("description", "")[:50]),
            description=theme_data.get("description", ""),
            related_key_points=theme_data.get("supporting_key_points", []),
        )
        result["themes"].append(theme)

    # Restated themes make a document look like it found more than it did.
    # The merge is code-decided and narrow; see theme_dedup for the measurement.
    result["themes"], result["theme_merges"] = merge_similar_themes(result["themes"])

    # Parse speculative observations
    for obs_data in response_data.get("speculative_observations", []):
        result["speculative_observations"].append({
            "text": obs_data.get("text", ""),
            "based_on": obs_data.get("based_on", []),
            "label": obs_data.get("label", "speculative"),
        })

    # Parse confidence assessment
    confidence_data = response_data.get("confidence_assessment", {})
    level_str = confidence_data.get("level", "medium")
    try:
        result["confidence_level"] = ConfidenceLevel(level_str.lower())
    except ValueError:
        result["confidence_level"] = ConfidenceLevel.MEDIUM

    result["confidence_reasoning"] = confidence_data.get("reasoning", [])

    return result


def stage_semantic_synthesis(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Synthesize unified semantic understanding.

    PREREQUISITE: semantic_extraction and gap_analysis stages must run first.

    This stage:
    1. Aggregates all semantic units from extractions
    2. Includes identified gaps from gap analysis
    3. Calls Gemini to synthesize semantic core
    4. Stores synthesis results in context

    Output is consumed by document_assembly for Doc 2 (Semantic Brief).
    """
    logger.info(f"[{ctx.job_id}] Stage: Semantic Synthesis")

    update_job(
        ctx.job_id,
        stage="semantic_synthesis",
        progress_percent=60,
    )

    # Check prerequisites
    extractions = getattr(ctx, "semantic_extractions", [])
    if not extractions:
        logger.warning("No semantic extractions found - skipping synthesis")
        ctx.add_warning("Semantic synthesis skipped: no extractions available")
        return

    # Aggregate inputs with Phase 5 source attribution tracking
    key_points, themes, tensions, gaps, _source_coverage, _conflicts = (
        aggregate_for_synthesis_with_attribution(ctx)
    )

    # Build scope lock
    scope_lock = f"Research topic: {ctx.topic}"
    if hasattr(ctx, "scope_in") and ctx.scope_in:
        scope_lock += f"\nIn scope: {', '.join(ctx.scope_in)}"
    if hasattr(ctx, "scope_out") and ctx.scope_out:
        scope_lock += f"\nOut of scope: {', '.join(ctx.scope_out)}"

    # Calculate verification rate
    verification_rate = calculate_verification_rate(ctx)

    # Count unique sources
    source_diversity = len(set(
        kp.get("source_ids", ["unknown"])[0]
        for kp in key_points
        if kp.get("source_ids")
    ))

    # Build prompt
    prompt = build_semantic_synthesis_prompt(
        scope_lock=scope_lock,
        key_points=key_points,
        themes=themes,
        tensions=tensions,
        gaps=gaps,
        verification_rate=verification_rate,
        source_diversity=source_diversity,
    )

    try:
        # Initialize Gemini client
        gemini_client = GeminiClient()

        # Call Gemini for synthesis (with style enforcement retry)
        synthesis_result = None
        total_cost = 0.0
        # Bound before the loop so the retry branch reads a defined value even
        # if the first attempt ever stops short of the style check.
        style_violations: list[str] = []

        for attempt in range(2):  # Max 2 attempts (original + 1 retry)
            current_prompt = prompt
            if attempt > 0:
                # Append style violations to prompt for retry
                violation_msg = "\n".join(style_violations)
                current_prompt = (
                    prompt
                    + f"\n\n## STYLE VIOLATIONS IN PREVIOUS ATTEMPT\n"
                    f"Your previous output was rejected for these style issues:\n"
                    f"{violation_msg}\n\n"
                    f"Fix ALL of these. Write shorter sentences. No academic jargon. "
                    f"Be direct. Address the creator as 'you'."
                )

            response = gemini_client.generate_json(
                prompt=current_prompt,
                system_message=SEMANTIC_SYNTHESIS_ROLE,
            )

            if "error" in response:
                logger.error(f"Gemini error during synthesis: {response['error']}")
                ctx.add_warning(f"Semantic synthesis error: {response['error']}")
                return

            # Track cost
            cost = response.get("cost", 0)
            total_cost += cost
            if hasattr(ctx, "add_cost"):
                ctx.add_cost("gemini_semantic_synthesis", cost)

            # Parse response
            data = response.get("data", {})
            synthesis_result = parse_synthesis_response(data)

            # Style enforcement check
            all_text_parts = [synthesis_result["semantic_core"]]
            all_text_parts += [t.description for t in synthesis_result["themes"]]
            all_text = " ".join(all_text_parts)

            passes, style_violations = enforce_style(all_text)

            if passes:
                if attempt > 0:
                    logger.info(f"[{ctx.job_id}] Style check passed on retry (attempt {attempt + 1})")
                break
            elif attempt == 0:
                logger.warning(
                    f"[{ctx.job_id}] Style check failed ({len(style_violations)} violations), "
                    f"retrying synthesis: {style_violations[:3]}"
                )
            else:
                logger.warning(
                    f"[{ctx.job_id}] Style check still failing after retry, "
                    f"accepting with warnings: {style_violations[:3]}"
                )
                ctx.add_warning(
                    f"Style enforcement: {len(style_violations)} violations remain after retry"
                )

        cost = total_cost

        # Store results in context
        # These are used by document_assembly for Doc 2
        ctx.semantic_core = synthesis_result["semantic_core"]
        ctx.synthesized_themes = synthesis_result["themes"]
        ctx.speculative_observations = synthesis_result["speculative_observations"]
        ctx.confidence_reasoning = synthesis_result["confidence_reasoning"]
        ctx.theme_merges = synthesis_result.get("theme_merges", [])
        for merge in ctx.theme_merges:
            ctx.add_warning(
                f"Merged theme \"{merge['merged_label']}\" into "
                f"\"{merge['kept_label']}\" (restatement)"
            )

        # Store semantic_core_based_on for Doc 2
        if not hasattr(ctx, "semantic_core_based_on"):
            ctx.semantic_core_based_on = []
        ctx.semantic_core_based_on = synthesis_result["semantic_core_based_on"]

        # Store overall confidence for downstream use
        if not hasattr(ctx, "overall_confidence"):
            ctx.overall_confidence = ConfidenceLevel.MEDIUM
        ctx.overall_confidence = synthesis_result["confidence_level"]

        logger.info(
            f"Semantic synthesis complete: "
            f"core={len(synthesis_result['semantic_core'])} chars, "
            f"themes={len(synthesis_result['themes'])}, "
            f"confidence={synthesis_result['confidence_level'].value}, "
            f"cost=${cost:.4f}"
        )

        # Update job with synthesis summary
        update_job(
            ctx.job_id,
            partial_outputs={
                "semantic_synthesis_summary": {
                    "semantic_core_length": len(synthesis_result["semantic_core"]),
                    "themes_synthesized": len(synthesis_result["themes"]),
                    "speculative_observations": len(synthesis_result["speculative_observations"]),
                    "confidence_level": synthesis_result["confidence_level"].value,
                    "verification_rate": f"{verification_rate:.0%}",
                    "source_diversity": source_diversity,
                    "cost": cost,
                }
            },
        )

    except Exception as e:
        logger.error(f"Semantic synthesis failed: {e}")
        ctx.add_warning(f"Semantic synthesis error: {str(e)}")
        # Set defaults to allow pipeline to continue
        ctx.semantic_core = ""
        ctx.synthesized_themes = []
        ctx.speculative_observations = []
        ctx.confidence_reasoning = ["Synthesis failed"]
