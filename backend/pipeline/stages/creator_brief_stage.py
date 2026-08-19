"""Creator Brief Assembly Stage — Doc 3.

Based on: docs/authoritative/spec/RASS.md Stage F
Temperature: 0.3 (creative but grounded)

This stage runs after document_assembly. It reads:
- Doc 0 data: ctx.source_ledger (sources, titles, URLs)
- Doc 2 data: ctx.semantic_brief (themes, tensions, key_points)
- Claim data: ctx.semantic_extractions (claim_ids, statements, source_ids)

It outputs:
- ctx.outputs["creator_brief"] — CreatorBriefDocument as dict
- ctx.outputs["creator_brief_md"] — markdown-formatted Creator Brief

Failure is NON-FATAL: a Creator Brief failure does not fail the job.
The error is logged and stored in ctx warnings.
"""

import json
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.creator_brief import CreatorBriefDocument
from backend.pipeline.context import PipelineContext
from backend.pipeline.prompts.creator_brief_prompt import (
    CREATOR_BRIEF_ROLE,
    build_creator_brief_prompt,
)
from backend.state import update_job

# Temperature for Creator Brief (per architecture Rule 16)
CREATOR_BRIEF_TEMPERATURE = 0.3


def _collect_claims(ctx: PipelineContext) -> list[dict[str, Any]]:
    """Collect all claims from semantic extractions into a flat list.

    Args:
        ctx: Pipeline context with semantic_extractions populated.

    Returns:
        List of claim dicts with claim_id, statement, source_id, confidence.
    """
    claims: list[dict[str, Any]] = []
    for extraction in ctx.semantic_extractions:
        for claim in getattr(extraction, "claims", []):
            claims.append(claim.to_dict())
    return claims


def _collect_valid_claim_ids(ctx: PipelineContext) -> set[str]:
    """Return all valid claim_ids from semantic extractions.

    Used for provenance validation.

    Args:
        ctx: Pipeline context with semantic_extractions populated.

    Returns:
        Set of all claim_id strings present in the extractions.
    """
    ids: set[str] = set()
    for extraction in ctx.semantic_extractions:
        for claim in getattr(extraction, "claims", []):
            ids.add(claim.claim_id)
    return ids


def _collect_valid_source_ids(ctx: PipelineContext) -> set[str]:
    """Return all valid source_ids from the source ledger.

    Used for provenance validation.

    Args:
        ctx: Pipeline context with source_ledger populated.

    Returns:
        Set of all source_id strings in Doc 0.
    """
    sources = ctx.source_ledger.get("sources", [])
    return {s.get("source_id", "") for s in sources if s.get("source_id")}


def _validate_provenance(
    brief: CreatorBriefDocument,
    valid_claim_ids: set[str],
    valid_source_ids: set[str],
) -> list[str]:
    """Validate provenance chain: all IDs in the brief must exist in Doc 0/2.

    Per architecture Rule 14a: every reference must trace to a real source.

    Args:
        brief: Parsed CreatorBriefDocument.
        valid_claim_ids: Claim IDs that exist in Doc 2 (extractions).
        valid_source_ids: Source IDs that exist in Doc 0.

    Returns:
        List of provenance violation messages. Empty = valid.
    """
    violations: list[str] = []

    brief_claim_ids = brief.all_claim_ids()
    brief_source_ids = brief.all_source_ids()

    # Check every referenced claim_id exists in extractions
    if valid_claim_ids:  # only validate if we have claims to validate against
        bad_claims = brief_claim_ids - valid_claim_ids
        if bad_claims:
            violations.append(
                f"Creator Brief references unknown claim_ids: {sorted(bad_claims)}"
            )

    # Check every referenced source_id exists in Doc 0
    bad_sources = brief_source_ids - valid_source_ids
    if bad_sources:
        violations.append(
            f"Creator Brief references unknown source_ids: {sorted(bad_sources)}"
        )

    return violations


def run_creator_brief_stage(ctx: PipelineContext) -> PipelineContext:
    """Assemble the Creator Brief (Doc 3).

    Reads Doc 0 and Doc 2 data from ctx, calls the LLM, validates
    provenance, and stores the result in ctx.outputs.

    Failure is NON-FATAL: adds warning and returns ctx unchanged if
    Creator Brief generation fails.

    Args:
        ctx: Pipeline context with source_ledger, semantic_brief,
             and semantic_extractions populated.

    Returns:
        Updated PipelineContext with creator_brief in outputs.
    """
    from backend.config import get_settings

    if not get_settings().creator_brief_enabled:
        # Retired from the default run (work order item 16). The document
        # performs rather than informs; the description source list it used to
        # carry is built by code now. Kept behind a flag until P8.
        logger.info(f"[{ctx.job_id}] Creator Brief skipped: retired by config")
        return ctx

    logger.info(f"[{ctx.job_id}] Creator Brief stage starting")
    update_job(ctx.job_id, stage="creator_brief_assembly", progress_percent=88)

    try:
        _run_creator_brief(ctx)
    except Exception as e:
        logger.error(f"[{ctx.job_id}] Creator Brief generation failed: {e}")
        ctx.add_warning(f"Creator Brief generation failed (non-fatal): {e}")

    return ctx


def _run_creator_brief(ctx: PipelineContext) -> None:
    """Inner implementation — raises on failure.

    Args:
        ctx: Pipeline context.

    Raises:
        Exception: If LLM call fails, parsing fails, or provenance is invalid.
    """
    client = GeminiClient()

    # Collect data from context
    sources: list[dict] = ctx.source_ledger.get("sources", [])
    source_count = len(sources)
    doc2: dict = ctx.semantic_brief

    claims = _collect_claims(ctx)
    valid_claim_ids = _collect_valid_claim_ids(ctx)
    valid_source_ids = _collect_valid_source_ids(ctx)

    # Format data for prompt
    doc0_sources_str = _format_doc0_sources(sources)
    doc2_claims_str = _format_doc2_claims(claims)
    doc2_themes_str = _format_doc2_themes(doc2.get("themes", []))
    doc2_tensions_str = _format_doc2_tensions(doc2.get("tensions", []))

    # Build prompt
    prompt = build_creator_brief_prompt(
        job_id=ctx.job_id,
        topic=ctx.topic,
        source_count=source_count,
        doc0_sources=doc0_sources_str,
        doc2_claims=doc2_claims_str,
        doc2_themes=doc2_themes_str,
        doc2_tensions=doc2_tensions_str,
    )

    logger.info(f"[{ctx.job_id}] Calling LLM for Creator Brief (temp={CREATOR_BRIEF_TEMPERATURE})")

    # LLM call
    response = client.generate_json(
        prompt=prompt,
        system_message=CREATOR_BRIEF_ROLE,
        temperature=CREATOR_BRIEF_TEMPERATURE,
    )

    if response.get("error"):
        raise ValueError(f"LLM error: {response['error']}")

    raw_data: dict = response.get("data", {})
    if not raw_data:
        raise ValueError("LLM returned empty data")

    # Inject job_id and topic if LLM omitted them (common with structured outputs)
    raw_data.setdefault("job_id", ctx.job_id)
    raw_data.setdefault("topic", ctx.topic)
    raw_data.setdefault("source_count", source_count)

    # Parse and validate with Pydantic (guardrails, hook IDs, fact count)
    brief = CreatorBriefDocument(**raw_data)

    # Provenance validation
    violations = _validate_provenance(brief, valid_claim_ids, valid_source_ids)
    if violations:
        for v in violations:
            logger.warning(f"[{ctx.job_id}] Provenance violation: {v}")
            ctx.add_warning(f"Creator Brief provenance: {v}")

        # Provenance violations are warnings, not hard failures.
        # The brief is still usable — the frontend will display warnings.

    # Estimate cost from response
    cost = response.get("cost", 0.0)
    ctx.add_cost("creator_brief", cost)

    # Generate story arc suggestion based on topic/mode
    story_arc = _generate_story_arc_suggestion(ctx, doc2)

    # Store outputs — use polished formatter for markdown
    from backend.pipeline.formatters.creator_brief_formatter import format_creator_brief
    brief_dict = brief.model_dump(mode="json")
    if story_arc:
        brief_dict["suggested_structure"] = story_arc
    ctx.outputs["creator_brief"] = brief_dict
    ctx.outputs["creator_brief_md"] = format_creator_brief(brief)

    logger.info(
        f"[{ctx.job_id}] Creator Brief assembled: "
        f"{len(brief.hook_options)} hooks, "
        f"{len(brief.core_facts)} facts, "
        f"{len(brief.disputed_claims)} disputed"
    )


# ---------------------------------------------------------------------------
# Data formatters — convert context data to prompt-readable text
# ---------------------------------------------------------------------------

def _format_doc0_sources(sources: list[dict]) -> str:
    """Format source ledger sources for the prompt.

    Args:
        sources: List of source dicts from Doc 0.

    Returns:
        Human-readable source list string.
    """
    if not sources:
        return "(No sources in Doc 0)"

    lines = []
    for s in sources:
        source_id = s.get("source_id", "?")
        title = s.get("title", "Untitled")
        url = s.get("url", "")
        source_type = s.get("source_type", "unknown")
        creator = s.get("creator", "")

        line = f"- {source_id}: [{source_type}] {title}"
        if creator:
            line += f" by {creator}"
        if url:
            line += f" | {url}"
        lines.append(line)

    return "\n".join(lines)


def _format_doc2_claims(claims: list[dict]) -> str:
    """Format extracted claims for the prompt.

    Args:
        claims: List of claim dicts from semantic extractions.

    Returns:
        Human-readable claims string with IDs, statements, source refs.
    """
    if not claims:
        return "(No claims extracted — use key_points from themes instead)"

    lines = []
    for c in claims[:60]:  # cap at 60 to stay within token limits
        claim_id = c.get("claim_id", "?")
        statement = c.get("statement", c.get("text", ""))
        source_id = c.get("source_id", "?")
        confidence = c.get("confidence", "medium")
        # Optional enrichment fields (present if V3 extractor was used)
        framing = c.get("framing", "")
        significance = c.get("significance", "")
        speaker = c.get("speaker", "")

        line = f"- {claim_id} [{source_id}] ({confidence}): {statement}"
        if speaker:
            line += f" — said by: {speaker}"
        if framing:
            line += f" [framing: {framing}]"
        if significance:
            line += f" [significance: {significance}]"
        lines.append(line)

    return "\n".join(lines)


def _format_doc2_themes(themes: list[dict]) -> str:
    """Format themes from Doc 2 for the prompt.

    Args:
        themes: List of theme dicts from SemanticBrief.

    Returns:
        Human-readable themes string.
    """
    if not themes:
        return "(No themes identified)"

    lines = []
    for t in themes[:8]:
        theme_id = t.get("theme_id", "?")
        label = t.get("label", "")
        description = t.get("description", "")
        source_ids = t.get("source_ids", [])

        line = f"- {theme_id}: {label}"
        if description:
            line += f" — {description}"
        if source_ids:
            line += f" [sources: {', '.join(source_ids[:5])}]"
        lines.append(line)

    return "\n".join(lines)


def _format_doc2_tensions(tensions: list[dict]) -> str:
    """Format tensions from Doc 2 for the prompt.

    Args:
        tensions: List of tension dicts from SemanticBrief.

    Returns:
        Human-readable tensions string.
    """
    if not tensions:
        return "(No tensions identified)"

    lines = []
    for t in tensions[:5]:
        tension_id = t.get("tension_id", "?")
        description = t.get("description", "")
        source_ids = t.get("source_ids", [])

        line = f"- {tension_id}: {description}"
        if source_ids:
            line += f" [sources: {', '.join(source_ids[:4])}]"
        lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_creator_brief_markdown(brief: CreatorBriefDocument, topic: str) -> str:
    """Render a CreatorBriefDocument as markdown.

    This is a simple render pass. The full polished renderer is in
    backend/pipeline/formatters/creator_brief_formatter.py (Phase 2.3.1).

    Args:
        brief: Validated CreatorBriefDocument.
        topic: Research topic string.

    Returns:
        Markdown string.
    """
    from datetime import datetime

    lines = [
        f"# Creator Brief — {topic}",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Sources: {brief.source_count} | Doc 3*",
        "",
        "---",
        "",
    ]

    # Hook Options
    lines.append("## Hook Options")
    lines.append("")
    for hook in sorted(brief.hook_options, key=lambda h: h.hook_id):
        lines.append(f"### {hook.hook_id}")
        lines.append(f"> {hook.text}")
        lines.append(f"")
        lines.append(f"**Why it works:** {hook.why_it_works}")
        lines.append(f"*Source: {hook.claim_id} / {hook.source_id}*")
        lines.append("")

    # Setup
    lines.append("## The Setup")
    lines.append("")
    lines.append(brief.setup.text)
    if brief.setup.supporting_source_ids:
        lines.append(f"*Sources: {', '.join(brief.setup.supporting_source_ids)}*")
    lines.append("")

    # Twist
    if brief.twist:
        lines.append("## The Twist")
        lines.append("")
        lines.append(brief.twist.text)
        lines.append(f"*Framing: {brief.twist.framing} | {brief.twist.claim_id} / {brief.twist.source_id}*")
        lines.append("")

    # Core Facts
    lines.append("## Core Facts")
    lines.append("")
    for fact in brief.core_facts:
        lines.append(f"### {fact.fact_id}")
        lines.append(f"**As extracted:** {fact.statement}")
        lines.append(f"**Say it like:** *\"{fact.say_it_like}\"*")
        if fact.speaker:
            lines.append(f"**Speaker:** {fact.speaker}")
        lines.append(f"**Significance:** {fact.significance} | *{fact.claim_id} / {fact.source_id}*")
        lines.append("")

    # Analogy
    if brief.analogy:
        lines.append("## The Analogy")
        lines.append("")
        lines.append(brief.analogy.text)
        lines.append("")

    # Personal Stakes
    if brief.personal_stakes:
        lines.append("## What This Means for You")
        lines.append("")
        lines.append(brief.personal_stakes.text)
        lines.append("")

    # Cliffhanger
    if brief.cliffhanger:
        lines.append("## Cliffhanger / Open Question")
        lines.append("")
        lines.append(brief.cliffhanger.text)
        lines.append(f"*Framing: {brief.cliffhanger.framing}*")
        lines.append("")

    # Sources for description
    if brief.description_sources:
        lines.append("## Sources (for video description)")
        lines.append("")
        for src in brief.description_sources:
            line = f"- **{src.title}**"
            if src.creator:
                line += f" by {src.creator}"
            if src.url:
                line += f" — {src.url}"
            line += f" *(Doc 0: {src.source_id})*"
            lines.append(line)
        lines.append("")

    # Disputed Claims
    if brief.disputed_claims:
        lines.append("## Claims Flagged as Disputed or Speculative")
        lines.append("")
        lines.append("> ⚠️ These claims require extra care. Do not present them as established facts.")
        lines.append("")
        for d in brief.disputed_claims:
            lines.append(f"- **[{d.framing.upper()}]** {d.statement}")
            if d.speaker:
                lines.append(f"  *(Said by: {d.speaker} | {d.claim_id} / {d.source_id})*")
            else:
                lines.append(f"  *({d.claim_id} / {d.source_id})*")
        lines.append("")

    lines.append("---")
    lines.append(f"*Doc 3 — Creator Brief | Job: {brief.job_id}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Story Arc Suggestion — Phase 3B
# ---------------------------------------------------------------------------

# Arc templates keyed by mode/topic type
_STORY_ARC_TEMPLATES: dict[str, dict[str, Any]] = {
    "cold_open": {
        "arc_name": "Cold Open Investigation",
        "arc_type": "cold_open",
        "topic_fit_reason": "Investigation topics work best with a single damning detail that pulls viewers in.",
        "beats": [
            {"beat_number": 1, "label": "The Detail", "description": "Open with the single most damning or surprising detail. No context yet — just the hook."},
            {"beat_number": 2, "label": "Surface Story", "description": "Give the official version. What does the public think happened?"},
            {"beat_number": 3, "label": "Evidence Trail", "description": "Walk through the evidence chronologically. Let each piece build on the last."},
            {"beat_number": 4, "label": "The Pattern", "description": "Zoom out. Show this isn't isolated — it's part of a pattern."},
            {"beat_number": 5, "label": "What Happens Next", "description": "The stakes going forward. What should the audience watch for?"},
        ],
    },
    "multiple_perspectives": {
        "arc_name": "Multiple Perspectives",
        "arc_type": "multiple_perspectives",
        "topic_fit_reason": "Controversy topics need balanced presentation of competing viewpoints.",
        "beats": [
            {"beat_number": 1, "label": "The Claim", "description": "State the central claim or controversy clearly. What's being debated?"},
            {"beat_number": 2, "label": "Side A", "description": "Present the strongest evidence for one perspective. Steel-man it."},
            {"beat_number": 3, "label": "Side B", "description": "Present the strongest evidence for the other perspective. Equal treatment."},
            {"beat_number": 4, "label": "What's Actually True", "description": "Where does the evidence actually land? What can we verify?"},
            {"beat_number": 5, "label": "Why It Matters", "description": "The broader implications. What does this mean for the audience?"},
        ],
    },
    "heros_journey": {
        "arc_name": "Hero's Journey",
        "arc_type": "heros_journey",
        "topic_fit_reason": "Profile topics follow a natural arc: origin, conflict, transformation.",
        "beats": [
            {"beat_number": 1, "label": "The Payoff", "description": "Show where the subject is now — the impressive result that makes people care."},
            {"beat_number": 2, "label": "Origin / Conflict", "description": "Go back to the beginning. What obstacles did they face?"},
            {"beat_number": 3, "label": "The Build", "description": "The process, the grind, the key decisions that led to breakthrough."},
            {"beat_number": 4, "label": "Transformation", "description": "The turning point. What changed and why?"},
            {"beat_number": 5, "label": "Call to Action", "description": "What can the audience learn or apply from this story?"},
        ],
    },
    "discovery": {
        "arc_name": "Discovery Arc",
        "arc_type": "discovery",
        "topic_fit_reason": "Explainer topics are best structured as a guided journey of understanding.",
        "beats": [
            {"beat_number": 1, "label": "The Question", "description": "Frame the central question. Why should anyone care about this?"},
            {"beat_number": 2, "label": "Why It's Hard", "description": "Show why this question doesn't have a simple answer. Acknowledge complexity."},
            {"beat_number": 3, "label": "The Mechanism", "description": "Explain how it actually works. The core insight."},
            {"beat_number": 4, "label": "Implications", "description": "So what? What does this mean for the real world?"},
            {"beat_number": 5, "label": "Open Thread", "description": "The unanswered question. What we still don't know."},
        ],
    },
}

# Mode → arc type mapping
_MODE_TO_ARC: dict[str, str] = {
    "investigation": "cold_open",
    "controversy": "multiple_perspectives",
    "profile": "heros_journey",
    "breaking_news": "cold_open",
    "full": "discovery",
    "quick": "discovery",
}


def _generate_story_arc_suggestion(
    ctx: PipelineContext,
    doc2: dict[str, Any],
) -> dict[str, Any] | None:
    """Generate a story arc suggestion based on the topic mode and Doc 2 themes.

    This is deterministic — no LLM call needed. The arc template is selected
    based on the job mode and then customized with theme/claim IDs from Doc 2.

    Args:
        ctx: Pipeline context with mode and topic.
        doc2: Doc 2 data (semantic brief) with themes and tensions.

    Returns:
        Story arc dict or None if no appropriate arc found.
    """
    mode = getattr(ctx, "mode", "full") or "full"

    # Check if tensions exist — if so, controversy arc might fit better
    tensions = doc2.get("tensions", [])
    if len(tensions) >= 2 and mode not in ("investigation", "profile"):
        arc_key = "multiple_perspectives"
    else:
        arc_key = _MODE_TO_ARC.get(mode, "discovery")

    template = _STORY_ARC_TEMPLATES.get(arc_key)
    if not template:
        return None

    # Deep copy the template
    import copy
    arc = copy.deepcopy(template)

    # Map Doc 2 themes to beats where possible
    themes = doc2.get("themes", [])
    theme_ids = [t.get("theme_id", "") for t in themes[:5]]

    for i, beat in enumerate(arc["beats"]):
        if i < len(theme_ids) and theme_ids[i]:
            beat["mapped_ids"] = [theme_ids[i]]

    # Generate scripting preview
    topic = ctx.topic or "this topic"
    arc["scripting_preview"] = _generate_scripting_preview(arc_key, topic, themes)

    return arc


def _generate_scripting_preview(
    arc_key: str,
    topic: str,
    themes: list[dict[str, Any]],
) -> str:
    """Generate a one-paragraph scripting preview for the arc.

    Args:
        arc_key: The arc template key.
        topic: The research topic.
        themes: Doc 2 themes for context.

    Returns:
        A one-paragraph preview string.
    """
    theme_labels = [t.get("label", "") for t in themes[:3] if t.get("label")]
    themes_str = ", ".join(theme_labels) if theme_labels else "the key findings"

    previews = {
        "cold_open": (
            f"Open with the most surprising detail about {topic} — something that makes viewers "
            f"stop scrolling. Then pull back and give the official story. Walk through {themes_str} "
            f"one by one, building the evidence trail. Zoom out to show the pattern, then end with "
            f"what's still unfolding."
        ),
        "multiple_perspectives": (
            f"Start by stating the core debate around {topic} clearly. Present the strongest case "
            f"for each side — don't strawman either position. Use {themes_str} as the framework for "
            f"what the evidence actually shows. Close with why this matters to your audience."
        ),
        "heros_journey": (
            f"Start with the payoff — show where the subject of {topic} is now. Then rewind to "
            f"the beginning: the obstacles, the early struggles. Build through {themes_str}, "
            f"hitting the turning point, and close with what the audience can take away."
        ),
        "discovery": (
            f"Frame {topic} as a question your audience didn't know they had. Show why the answer "
            f"isn't obvious — then walk them through {themes_str} as the mechanism. End with the "
            f"implications and the question that's still unanswered."
        ),
    }

    return previews.get(arc_key, f"Structure your video about {topic} around {themes_str}.")
