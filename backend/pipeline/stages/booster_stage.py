"""
Booster Stage - Deep Research Booster Pipeline Stage.

Based on: docs/authoritative/spec/GAPS_AND_BOOSTER_SPEC.md Part 2

CRITICAL: The booster produces DIRECTIONS, not FACTS.
It tells you WHERE to look, not WHAT you'll find.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.booster_models import (
    BoosterOutput,
    ContextBundle,
    ImpactLevel,
    MissingPerspective,
    PlatformSuggestion,
    PrimarySourceDirection,
    PrimarySourceType,
    ResearchQuestion,
    SearchQuery,
)
from backend.pipeline.booster.context_bundle_generator import compute_bundle_hash
from backend.pipeline.prompts.booster_prompt import (
    BOOSTER_CONTEXT_LOCK,
    BOOSTER_PROMPT,
    BOOSTER_ROLE,
)

# Module-level constants for impact validation and sorting
VALID_IMPACTS: frozenset[str] = frozenset(il.value for il in ImpactLevel)
IMPACT_ORDER: dict[str, int] = {"critical": 0, "important": 1, "nice_to_have": 2}


def build_booster_prompt(bundle: ContextBundle) -> str:
    """
    Build complete booster prompt from context bundle.

    Args:
        bundle: Context bundle from job output

    Returns:
        Complete prompt string ready for LLM
    """
    # Format themes
    themes_str = "\n".join([
        f"- {t.theme_id}: {t.label} — {t.description}"
        for t in bundle.themes
    ]) or "(No themes identified)"

    # Format key points (limited to prevent context bloat)
    key_points_str = "\n".join([
        f"- {kp}" for kp in bundle.key_point_summaries[:15]
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

    context_lock = BOOSTER_CONTEXT_LOCK.format(
        job_id=bundle.job_id,
        source_count=bundle.source_count,
        confidence_level=bundle.confidence_level,
    )

    prompt = context_lock + "\n\n" + BOOSTER_PROMPT.format(
        scope_in=", ".join(bundle.scope_in) or "(Not specified)",
        scope_out=", ".join(bundle.scope_out) or "(Not specified)",
        themes=themes_str,
        key_points=key_points_str,
        tensions=tensions_str,
        gaps=gaps_str,
        source_count=bundle.source_count,
        source_types=", ".join(bundle.source_types) or "(Unknown)",
        confidence_level=bundle.confidence_level,
    )

    return prompt


def parse_booster_response(data: dict[str, Any], bundle: ContextBundle) -> BoosterOutput:
    """
    Parse Gemini response into BoosterOutput.

    Args:
        data: Raw JSON response from Gemini
        bundle: Context bundle for hash computation

    Returns:
        Parsed BoosterOutput
    """
    def _parse_impact(raw: str) -> str:
        """Validate and normalize impact level."""
        val = raw.lower().strip() if raw else "important"
        return val if val in VALID_IMPACTS else "important"

    # Parse missing perspectives
    missing_perspectives = []
    for mp in data.get("missing_perspectives", []):
        missing_perspectives.append(MissingPerspective(
            description=mp.get("description", ""),
            why_it_matters=mp.get("why_it_matters", ""),
            related_gaps=mp.get("related_gaps", []),
            impact_level=_parse_impact(mp.get("impact_level", "important")),
        ))

    # Parse primary source directions
    primary_source_directions = []
    for psd in data.get("primary_source_directions", []):
        source_type_str = psd.get("source_type", "other")
        try:
            source_type = PrimarySourceType(source_type_str)
        except ValueError:
            source_type = PrimarySourceType.OTHER

        primary_source_directions.append(PrimarySourceDirection(
            source_type=source_type,
            description=psd.get("description", ""),
            search_suggestion=psd.get("search_suggestion", ""),
            related_gap=psd.get("related_gap"),
            why_it_matters=psd.get("why_it_matters", ""),
            impact_level=_parse_impact(psd.get("impact_level", "important")),
        ))

    # Parse search queries
    search_queries = []
    for sq in data.get("suggested_search_queries", []):
        platform_str = sq.get("platform_suggestion", "google")
        try:
            platform = PlatformSuggestion(platform_str)
        except ValueError:
            platform = PlatformSuggestion.GOOGLE

        search_queries.append(SearchQuery(
            query=sq.get("query", ""),
            purpose=sq.get("purpose", ""),
            platform_suggestion=platform,
            related_gap=sq.get("related_gap"),
            related_theme=sq.get("related_theme"),
            why_it_matters=sq.get("why_it_matters", ""),
            impact_level=_parse_impact(sq.get("impact_level", "important")),
        ))

    # Parse research questions
    research_questions = []
    for rq in data.get("research_questions", []):
        research_questions.append(ResearchQuestion(
            question=rq.get("question", ""),
            why_it_matters=rq.get("why_it_matters", ""),
            related_theme=rq.get("related_theme", ""),
            impact_level=_parse_impact(rq.get("impact_level", "important")),
        ))

    # R14: Sort all categories by impact (critical first)
    missing_perspectives.sort(key=lambda x: IMPACT_ORDER.get(x.impact_level, 1))
    primary_source_directions.sort(key=lambda x: IMPACT_ORDER.get(x.impact_level, 1))
    search_queries.sort(key=lambda x: IMPACT_ORDER.get(x.impact_level, 1))
    research_questions.sort(key=lambda x: IMPACT_ORDER.get(x.impact_level, 1))

    return BoosterOutput(
        missing_perspectives=missing_perspectives,
        primary_source_directions=primary_source_directions,
        suggested_search_queries=search_queries,
        research_questions=research_questions,
        booster_provider="gemini",
        booster_timestamp=datetime.now(timezone.utc).isoformat(),
        context_bundle_hash=compute_bundle_hash(bundle),
    )


def validate_booster_output(output: BoosterOutput, bundle: ContextBundle) -> list[str]:
    """
    Validate booster output for grounding and hallucination.

    Checks:
    - All gap_id references exist in bundle
    - All theme_id references exist in bundle
    - No empty required fields

    Args:
        output: Booster output to validate
        bundle: Original context bundle

    Returns:
        List of warnings. Empty = valid.
    """
    warnings = []
    valid_gap_ids = {g.gap_id for g in bundle.gaps}
    valid_theme_ids = {t.theme_id for t in bundle.themes}

    # Check that related_gaps reference valid gap IDs
    for mp in output.missing_perspectives:
        for gap_id in mp.related_gaps:
            if gap_id and gap_id not in valid_gap_ids:
                warnings.append(f"Invalid gap reference in missing_perspectives: {gap_id}")

    # Check primary source directions
    for psd in output.primary_source_directions:
        if psd.related_gap and psd.related_gap not in valid_gap_ids:
            warnings.append(f"Invalid gap reference in primary_source_directions: {psd.related_gap}")

    # Check search queries
    for sq in output.suggested_search_queries:
        if sq.related_gap and sq.related_gap not in valid_gap_ids:
            warnings.append(f"Invalid gap reference in search_queries: {sq.related_gap}")
        if sq.related_theme and sq.related_theme not in valid_theme_ids:
            warnings.append(f"Invalid theme reference in search_queries: {sq.related_theme}")

    # Check research questions
    for rq in output.research_questions:
        if rq.related_theme and rq.related_theme not in valid_theme_ids:
            warnings.append(f"Invalid theme reference in research_questions: {rq.related_theme}")

    # Anti-hallucination: Detect generic search queries
    generic_query_patterns = [
        re.compile(r'search for (?:more |additional |further )?information about', re.IGNORECASE),
        re.compile(r'find (?:more |additional )?details about', re.IGNORECASE),
        re.compile(r'look for (?:more |facts|details) about', re.IGNORECASE),
        re.compile(r'research (?:more )?about', re.IGNORECASE),
    ]
    for sq in output.suggested_search_queries:
        for pattern in generic_query_patterns:
            if pattern.search(sq.query):
                warnings.append(
                    f"Generic search query detected (not actionable): '{sq.query[:60]}'"
                )
                break

    # Anti-hallucination: Detect speculative language in source directions
    speculation_patterns = [
        re.compile(r'\b(?:might|could|would)\s+(?:reveal|show|contain|demonstrate|prove)', re.IGNORECASE),
        re.compile(r'\blikely\s+(?:shows?|demonstrates?|contains?)', re.IGNORECASE),
    ]
    for psd in output.primary_source_directions:
        text_to_check = f"{psd.description} {psd.why_it_matters}"
        for pattern in speculation_patterns:
            if pattern.search(text_to_check):
                warnings.append(
                    f"Speculative language in source direction: "
                    f"'{psd.description[:50]}' — booster should suggest WHERE, not WHAT"
                )
                break

    return warnings


def run_booster(bundle: ContextBundle) -> tuple[BoosterOutput, float, list[str]]:
    """
    Run the Deep Research Booster.

    This is the main entry point for the booster stage.
    It generates research directions based on the context bundle.

    Args:
        bundle: Context bundle from job output

    Returns:
        Tuple of (BoosterOutput, cost, warnings)

    Raises:
        RuntimeError: If booster generation fails
    """
    logger.info(f"Running booster for job {bundle.job_id}")
    logger.info(
        f"Bundle stats: {len(bundle.themes)} themes, "
        f"{len(bundle.gaps)} gaps, {len(bundle.tensions)} tensions, "
        f"{len(bundle.key_point_summaries)} key points"
    )

    # Build prompt
    prompt = build_booster_prompt(bundle)

    # Call Gemini with higher temperature for variety
    client = GeminiClient()
    response = client.generate_json(
        prompt=prompt,
        system_message=BOOSTER_ROLE,
        temperature=0.45,  # Higher for creative directions
    )

    if "error" in response:
        raise RuntimeError(f"Booster generation failed: {response['error']}")

    cost = response.get("cost", 0.0)
    data = response.get("data", {})

    # Handle case where data is a string (shouldn't happen with JSON mode)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise RuntimeError(f"Booster returned non-JSON data: {data[:100]}")

    # Parse response
    output = parse_booster_response(data, bundle)

    # Validate
    warnings = validate_booster_output(output, bundle)

    logger.info(
        f"Booster complete for job {bundle.job_id}: "
        f"{len(output.missing_perspectives)} perspectives, "
        f"{len(output.primary_source_directions)} source directions, "
        f"{len(output.suggested_search_queries)} queries, "
        f"{len(output.research_questions)} questions, "
        f"{len(warnings)} warnings, cost=${cost:.4f}"
    )

    return output, cost, warnings


def booster_output_to_dict(output: BoosterOutput) -> dict[str, Any]:
    """
    Convert BoosterOutput to dictionary for storage.

    Args:
        output: Booster output

    Returns:
        Dictionary representation
    """
    return output.to_dict()
