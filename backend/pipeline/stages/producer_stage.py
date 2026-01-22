"""Producer Packet stage - 4-stage creative pipeline.

Based on: docs/authoritative/spec/RASS.md Stage G
Phase: 8

CRITICAL: All output is CREATIVE INTERPRETATION.
This does not modify Doc 0/1/2.
"""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.producer_models import (
    ProducerPacket,
    StoryCore,
    NarrativeAngle,
    OpeningHook,
    StructureOption,
    KeyMoment,
    TitleOption,
    ThumbnailConcept,
    RiskAssessment,
    InterviewSuggestions,
    InterviewCandidate,
    BRollSuggestion,
    HookType,
    StructureType,
    TitleTone,
    SensitivityLevel,
)
from backend.pipeline.prompts.producer_prompt import (
    PRODUCER_ROLE,
    build_producer_prompt,
)


def run_producer_pipeline(
    job_id: str,
    job_data: dict[str, Any],
) -> tuple[ProducerPacket, float, list[str]]:
    """Run 4-stage producer pipeline.

    Stages:
    1. Story Core
    2. Structure Options
    3. Creative Elements
    4. Risk & Context

    Args:
        job_id: Job identifier
        job_data: Job data with sources, themes, key_points, etc.

    Returns:
        Tuple of (ProducerPacket, total_cost, warnings)
    """
    logger.info(f"Running producer pipeline for job {job_id}")
    warnings = []
    total_cost = 0.0

    client = GeminiClient()

    # Extract context from job data
    doc2 = job_data.get("artifacts", {}).get("semantic_brief", {})
    sources = job_data.get("sources", [])

    themes = doc2.get("themes", [])
    key_points = doc2.get("key_points", [])
    tensions = doc2.get("tensions", [])

    # Build context summaries
    themes_str = "\n".join([
        f"- {t.get('theme_id', '')}: {t.get('label', '')} — {t.get('description', '')}"
        for t in themes[:8]
    ]) or "(No themes)"

    key_points_summary = "\n".join([
        f"- {kp.get('key_point_id', '')}: {kp.get('statement', '')}"
        for kp in key_points[:12]
    ]) or "(No key points)"

    tensions_str = "\n".join([
        f"- {t.get('tension_id', '')}: {t.get('description', '')}"
        for t in tensions[:5]
    ]) or "(No tensions)"

    sources_str = "\n".join([
        f"- {s.get('source_id', '')}: {s.get('title', '')} ({s.get('source_type', '')})"
        for s in sources[:10]
    ]) or "(No sources)"

    # Stage 1: Story Core
    logger.info(f"Producer Stage 1: Story Core for job {job_id}")
    context = {
        "job_id": job_id,
        "source_count": len(sources),
        "themes": themes_str,
        "key_points_summary": key_points_summary,
        "tensions": tensions_str,
    }
    prompt = build_producer_prompt("story_core", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=PRODUCER_ROLE,
        temperature=0.4,
    )
    total_cost += response.get("cost", 0.0)

    if "error" in response:
        raise RuntimeError(f"Story core generation failed: {response['error']}")

    story_data = response.get("data", {})
    story_core = StoryCore(
        central_question=story_data.get("central_question", ""),
        one_sentence_pitch=story_data.get("one_sentence_pitch", ""),
        why_this_matters=story_data.get("why_this_matters", ""),
        target_audience=story_data.get("target_audience", ""),
        emotional_arc=story_data.get("emotional_arc", ""),
    )

    # Stage 2: Structure
    logger.info(f"Producer Stage 2: Structure for job {job_id}")
    context = {
        "job_id": job_id,
        "story_core": story_core.to_dict(),
        "themes": themes_str,
        "key_moments": key_points_summary[:500],
        "source_count": len(sources),
    }
    prompt = build_producer_prompt("structure", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=PRODUCER_ROLE,
        temperature=0.4,
    )
    total_cost += response.get("cost", 0.0)

    if "error" in response:
        warnings.append(f"Structure generation warning: {response['error']}")

    structure_data = response.get("data", {})

    # Parse narrative angles
    narrative_angles = []
    for a in structure_data.get("narrative_angles", []):
        narrative_angles.append(NarrativeAngle(
            angle_id=a.get("angle_id", f"ANG_{len(narrative_angles)+1}"),
            title=a.get("title", ""),
            description=a.get("description", ""),
            strengths=a.get("strengths", []),
            weaknesses=a.get("weaknesses", []),
            best_for=a.get("best_for", ""),
            key_sources=a.get("key_sources", []),
        ))

    # Parse structure options
    structure_options = []
    for s in structure_data.get("structure_options", []):
        try:
            struct_type = StructureType(s.get("structure_type", "thematic"))
        except ValueError:
            struct_type = StructureType.THEMATIC
        structure_options.append(StructureOption(
            structure_type=struct_type,
            description=s.get("description", ""),
            section_breakdown=s.get("section_breakdown", []),
            pros=s.get("pros", []),
            cons=s.get("cons", []),
        ))

    # Stage 3: Creative Elements
    logger.info(f"Producer Stage 3: Creative Elements for job {job_id}")
    context = {
        "job_id": job_id,
        "story_core": story_core.to_dict(),
        "narrative_angles": [a.to_dict() for a in narrative_angles],
        "key_points": key_points_summary,
        "sources": sources_str,
    }
    prompt = build_producer_prompt("creative", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=PRODUCER_ROLE,
        temperature=0.5,  # Higher for creative elements
    )
    total_cost += response.get("cost", 0.0)

    if "error" in response:
        warnings.append(f"Creative elements warning: {response['error']}")

    creative_data = response.get("data", {})

    # Parse opening hooks
    opening_hooks = []
    for h in creative_data.get("opening_hooks", []):
        try:
            hook_type = HookType(h.get("hook_type", "cold_open"))
        except ValueError:
            hook_type = HookType.COLD_OPEN
        opening_hooks.append(OpeningHook(
            hook_type=hook_type,
            content=h.get("content", ""),
            tone=h.get("tone", ""),
            source_basis=h.get("source_basis", []),
        ))

    # Parse title options
    title_options = []
    for t in creative_data.get("title_options", []):
        try:
            tone = TitleTone(t.get("tone", "serious"))
        except ValueError:
            tone = TitleTone.SERIOUS
        title_options.append(TitleOption(
            title=t.get("title", ""),
            subtitle=t.get("subtitle"),
            tone=tone,
            seo_considerations=t.get("seo_considerations"),
        ))

    # Parse thumbnail concepts
    thumbnail_concepts = []
    for c in creative_data.get("thumbnail_concepts", []):
        thumbnail_concepts.append(ThumbnailConcept(
            concept=c.get("concept", ""),
            visual_elements=c.get("visual_elements", []),
            text_overlay=c.get("text_overlay"),
            emotional_appeal=c.get("emotional_appeal", ""),
        ))

    # Parse key moments
    key_moments = []
    for m in creative_data.get("key_moments", []):
        key_moments.append(KeyMoment(
            moment=m.get("moment", ""),
            source_id=m.get("source_id", ""),
            timestamp=m.get("timestamp"),
            why_compelling=m.get("why_compelling", ""),
            potential_use=m.get("potential_use", ""),
        ))

    # Stage 4: Risk & Context
    logger.info(f"Producer Stage 4: Risk & Context for job {job_id}")
    context = {
        "job_id": job_id,
        "story_core": story_core.to_dict(),
        "themes": themes_str,
        "tensions": tensions_str,
        "sources": sources_str,
    }
    prompt = build_producer_prompt("risk", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=PRODUCER_ROLE,
        temperature=0.3,  # Lower for risk assessment
    )
    total_cost += response.get("cost", 0.0)

    if "error" in response:
        warnings.append(f"Risk assessment warning: {response['error']}")

    risk_data = response.get("data", {})

    # Parse risk assessment
    risk_dict = risk_data.get("risk_assessment", {})
    try:
        sensitivity = SensitivityLevel(risk_dict.get("sensitivity_level", "medium"))
    except ValueError:
        sensitivity = SensitivityLevel.MEDIUM
    risk_assessment = RiskAssessment(
        sensitivity_level=sensitivity,
        potential_issues=risk_dict.get("potential_issues", []),
        mitigation_suggestions=risk_dict.get("mitigation_suggestions", []),
        legal_considerations=risk_dict.get("legal_considerations", []),
        ethical_considerations=risk_dict.get("ethical_considerations", []),
    )

    # Parse interview suggestions
    interview_dict = risk_data.get("interview_suggestions", {})
    people = []
    for p in interview_dict.get("people_to_contact", []):
        people.append(InterviewCandidate(
            name=p.get("name", ""),
            role=p.get("role", ""),
            why_relevant=p.get("why_relevant", ""),
            potential_questions=p.get("potential_questions", []),
        ))
    interview_suggestions = InterviewSuggestions(
        people_to_contact=people,
        expert_perspectives_needed=interview_dict.get("expert_perspectives_needed", []),
    )

    # Parse b-roll suggestions (defensive: Gemini may return strings instead of dicts)
    b_roll_suggestions = []
    for b in risk_data.get("b_roll_suggestions", []):
        if isinstance(b, str):
            # Gemini returned a string instead of a dict - wrap it
            b_roll_suggestions.append(BRollSuggestion(
                description=b,
                purpose="(auto-generated from string response)",
                source_options=[],
            ))
        elif isinstance(b, dict):
            b_roll_suggestions.append(BRollSuggestion(
                description=b.get("description", ""),
                purpose=b.get("purpose", ""),
                source_options=b.get("source_options", []),
            ))
        # Skip any other types silently

    # Assemble Producer Packet
    packet = ProducerPacket(
        job_id=job_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        story_core=story_core,
        narrative_angles=narrative_angles,
        opening_hooks=opening_hooks,
        structure_options=structure_options,
        key_moments=key_moments,
        title_options=title_options,
        thumbnail_concepts=thumbnail_concepts,
        risk_assessment=risk_assessment,
        interview_suggestions=interview_suggestions,
        b_roll_suggestions=b_roll_suggestions,
    )

    # Validate cardinality
    cardinality_warnings = validate_producer_cardinality(packet)
    warnings.extend(cardinality_warnings)

    logger.info(
        f"Producer pipeline complete for job {job_id}: "
        f"{len(narrative_angles)} angles, {len(opening_hooks)} hooks, "
        f"{len(title_options)} titles, cost=${total_cost:.4f}"
    )

    return packet, total_cost, warnings


def validate_producer_cardinality(packet: ProducerPacket) -> list[str]:
    """Validate cardinality targets from spec.

    Based on: docs/authoritative/spec/Document_Output_Format.md (Doc 3)

    Returns:
        List of warnings for cardinality violations.
    """
    warnings = []

    # Minimums (from Document_Output_Format.md)
    if len(packet.narrative_angles) < 2:
        warnings.append(f"narrative_angles below minimum: {len(packet.narrative_angles)}/2")
    if len(packet.opening_hooks) < 2:
        warnings.append(f"opening_hooks below minimum: {len(packet.opening_hooks)}/2")
    if len(packet.structure_options) < 2:
        warnings.append(f"structure_options below minimum: {len(packet.structure_options)}/2")
    if len(packet.title_options) < 2:
        warnings.append(f"title_options below minimum: {len(packet.title_options)}/2")
    if len(packet.key_moments) < 3:
        warnings.append(f"key_moments below minimum: {len(packet.key_moments)}/3")

    # Maximums
    if len(packet.narrative_angles) > 6:
        warnings.append(f"narrative_angles above maximum: {len(packet.narrative_angles)}/6")
    if len(packet.opening_hooks) > 6:
        warnings.append(f"opening_hooks above maximum: {len(packet.opening_hooks)}/6")
    if len(packet.structure_options) > 5:
        warnings.append(f"structure_options above maximum: {len(packet.structure_options)}/5")
    if len(packet.title_options) > 8:
        warnings.append(f"title_options above maximum: {len(packet.title_options)}/8")
    if len(packet.key_moments) > 15:
        warnings.append(f"key_moments above maximum: {len(packet.key_moments)}/15")

    return warnings
