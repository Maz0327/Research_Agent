"""Producer Packet stage - 6-stage creative pipeline.

Based on: docs/authoritative/spec/RASS.md Stage G
Phase: 8

CRITICAL: All output is CREATIVE INTERPRETATION.
This does not modify Doc 0/1/2.

Stages:
1. Story Core
2. Structure + Story Landscape + Recommendation
3. Creative Elements
4. Risk & Context
5. Production Blueprint (conditional)
6. Self-Critique / Quality Check
"""

import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.utils.output_quality import validate_output_quality

from backend.integrations.gemini_client import GeminiClient
from backend.models.producer_models import (
    ProducerPacket,
    StoryCore,
    StoryLandscape,
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
    ProductionBlueprint,
    ActStructure,
    Act,
    Beat,
    ClipSheetEntry,
    ClipType,
    EnhancedBRollSuggestion,
    ProductionNotes,
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
    doc2_raw = job_data.get("artifacts", {}).get("semantic_brief", {})
    sources = job_data.get("sources", [])

    # Handle nested storage format: {"data": {...}, "markdown": "..."}
    # vs direct format: {"themes": [...], ...}
    if "data" in doc2_raw and isinstance(doc2_raw.get("data"), dict):
        doc2 = doc2_raw["data"]
    else:
        doc2 = doc2_raw

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

    # R16: Extract creator profile from job_data, with defaults
    creator_profile = job_data.get("creator_profile", {})
    content_style = creator_profile.get("content_style", "investigative")
    typical_length = creator_profile.get("typical_length", "15-30 min")
    creator_audience = creator_profile.get("audience", "General audience interested in this topic")
    creator_tone = creator_profile.get("tone", "serious")

    # Build creator context string for prompts (only if non-default profile provided)
    creator_context = ""
    if creator_profile:
        creator_context = (
            f"\n\n## CREATOR CONTEXT (Tailor output to this creator)\n"
            f"Content Style: {content_style}\n"
            f"Typical Video Length: {typical_length}\n"
            f"Target Audience: {creator_audience}\n"
            f"Tone: {creator_tone}\n\n"
            f"Adapt all recommendations to this creator's style. "
            f"A 5-minute explainer needs different pacing than a 45-minute investigative piece."
        )

    # R16: Combine system role with creator context
    system_role = PRODUCER_ROLE + creator_context

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
        system_message=system_role,
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

    # Collect source IDs for quality validation
    source_ids = [s.get("source_id", "") for s in sources if s.get("source_id")]

    # R17: Quality check on Story Core
    for field_name in ("one_sentence_pitch", "why_this_matters", "emotional_arc"):
        text = getattr(story_core, field_name, "")
        if text:
            quality = validate_output_quality(text, source_ids)
            if quality.hedge_count > 0:
                warnings.append(
                    f"Story core '{field_name}' contains {quality.hedge_count} hedge phrase(s)"
                )

    # Stage 2: Structure
    logger.info(f"Producer Stage 2: Structure for job {job_id}")
    context = {
        "job_id": job_id,
        "story_core": json.dumps(story_core.to_dict(), indent=2),
        "themes": themes_str,
        "key_moments": key_points_summary[:500],
        "source_count": len(sources),
    }
    prompt = build_producer_prompt("structure", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=system_role,
        temperature=0.4,
    )
    total_cost += response.get("cost", 0.0)

    if "error" in response:
        warnings.append(f"Structure generation warning: {response['error']}")

    structure_data = response.get("data", {})

    # Parse story landscape (R8: structured categories)
    story_landscape = None
    landscape_data = structure_data.get("story_landscape")
    if landscape_data and isinstance(landscape_data, dict):
        story_landscape = StoryLandscape(
            saturated_angles=landscape_data.get("saturated_angles", []),
            emerging_angles=landscape_data.get("emerging_angles", []),
            untold_angles=landscape_data.get("untold_angles", []),
            landscape_summary=landscape_data.get("landscape_summary", ""),
            # Backward compat
            common_angles=landscape_data.get("common_angles", []),
            fresh_angles=landscape_data.get("fresh_angles", []),
        )
        # R8 validation: Check landscape has specifics
        for sa in story_landscape.saturated_angles:
            if isinstance(sa, dict):
                who = sa.get("who_covered_it", "")
                if not who:
                    warnings.append("Saturated angle missing 'who_covered_it' — may be generic")
                elif "widely covered" not in who.lower() and "mainstream" not in who.lower():
                    # Anti-hallucination: specific creator names may be fabricated
                    # Flag for human verification (we can't auto-verify)
                    warnings.append(
                        f"Saturated angle names specific creators: '{who[:60]}' — verify independently"
                    )

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
            confidence=a.get("confidence", ""),
        ))

    # R17: Quality check on narrative angles
    for angle in narrative_angles:
        quality = validate_output_quality(angle.description, source_ids)
        if quality.hedge_count > 2:
            warnings.append(
                f"Angle '{angle.title}' has {quality.hedge_count} hedge phrases — may be generic"
            )
        if quality.circular_count > 0:
            warnings.append(
                f"Angle '{angle.title}' has circular reasoning detected"
            )

    # Parse recommendation + decision brief (R11)
    recommended_angle_id = structure_data.get("recommended_angle_id")
    recommendation_reasoning = structure_data.get("recommendation_reasoning", "")
    risk_if_wrong = structure_data.get("risk_if_wrong", "")
    pivot_angle_id = structure_data.get("pivot_angle_id")
    pivot_reasoning = structure_data.get("pivot_reasoning", "")
    decision_criteria = structure_data.get("decision_criteria", [])

    # R11 validation: decision brief completeness
    if recommended_angle_id and not risk_if_wrong:
        warnings.append("Decision brief missing 'risk_if_wrong' — recommendation incomplete")
    if recommended_angle_id and not pivot_angle_id:
        warnings.append("Decision brief missing pivot angle — no fallback plan")

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
        "story_core": json.dumps(story_core.to_dict(), indent=2),
        "narrative_angles": json.dumps([a.to_dict() for a in narrative_angles], indent=2),
        "key_points": key_points_summary,
        "sources": sources_str,
    }
    prompt = build_producer_prompt("creative", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=system_role,
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
        "story_core": json.dumps(story_core.to_dict(), indent=2),
        "themes": themes_str,
        "tensions": tensions_str,
        "sources": sources_str,
    }
    prompt = build_producer_prompt("risk", context)

    response = client.generate_json(
        prompt=prompt,
        system_message=system_role,
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

    # Stage 5: Production Blueprint (only if we have a recommended angle)
    production_blueprint = None
    if recommended_angle_id:
        logger.info(f"Producer Stage 5: Production Blueprint for job {job_id}")
        # Find selected angle details
        selected_angle_info = f"Angle {recommended_angle_id}"
        for angle in narrative_angles:
            if angle.angle_id == recommended_angle_id:
                selected_angle_info = (
                    f"{angle.angle_id}: {angle.title}\n"
                    f"Description: {angle.description}\n"
                    f"Strengths: {', '.join(angle.strengths)}\n"
                    f"Key Sources: {', '.join(angle.key_sources)}"
                )
                break

        context = {
            "job_id": job_id,
            "selected_angle": selected_angle_info,
            "story_core": json.dumps(story_core.to_dict(), indent=2),
            "themes": themes_str,
            "key_points": key_points_summary,
            "sources": sources_str,
        }
        prompt = build_producer_prompt("blueprint", context)

        response = client.generate_json(
            prompt=prompt,
            system_message=system_role,
            temperature=0.3,  # Structured output, low creativity
        )
        total_cost += response.get("cost", 0.0)

        if "error" in response:
            warnings.append(f"Production blueprint warning: {response['error']}")
        else:
            blueprint_data = response.get("data", {})
            try:
                production_blueprint = parse_production_blueprint(
                    blueprint_data, recommended_angle_id, narrative_angles
                )
            except Exception as e:
                warnings.append(f"Production blueprint parse error: {e}")
                logger.warning(f"Failed to parse production blueprint: {e}")
    else:
        logger.info(
            f"Skipping Stage 5 (Production Blueprint) — no recommended angle for job {job_id}"
        )

    # R17: Quality check on production blueprint beats
    source_ids_set = set(source_ids)
    if production_blueprint and production_blueprint.act_structure:
        for act in production_blueprint.act_structure.acts:
            for beat in act.beats:
                if not beat.source_references:
                    warnings.append(
                        f"Beat {beat.beat_number} in Act {act.act_number} has no source references"
                    )
                else:
                    # Anti-hallucination: validate source refs exist
                    for ref in beat.source_references:
                        if ref not in source_ids_set:
                            warnings.append(
                                f"Beat {beat.beat_number} in Act {act.act_number} "
                                f"references non-existent source: {ref}"
                            )
                # R9: Validate beat has asset requirements
                if not beat.required_assets:
                    warnings.append(
                        f"Beat {beat.beat_number} in Act {act.act_number} missing required_assets"
                    )

        # R10: Validate clip suggested_beat references existing beats
        valid_beats = {
            f"Act {a.act_number}, Beat {b.beat_number}"
            for a in production_blueprint.act_structure.acts
            for b in a.beats
        }
        for clip in production_blueprint.clip_sheet:
            if clip.suggested_beat and clip.suggested_beat not in valid_beats:
                warnings.append(
                    f"Clip '{clip.description[:30]}' references non-existent beat: {clip.suggested_beat}"
                )

    # Assemble Producer Packet
    packet = ProducerPacket(
        job_id=job_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        story_core=story_core,
        story_landscape=story_landscape,
        recommended_angle_id=recommended_angle_id,
        recommendation_reasoning=recommendation_reasoning,
        narrative_angles=narrative_angles,
        opening_hooks=opening_hooks,
        structure_options=structure_options,
        key_moments=key_moments,
        title_options=title_options,
        thumbnail_concepts=thumbnail_concepts,
        risk_assessment=risk_assessment,
        interview_suggestions=interview_suggestions,
        b_roll_suggestions=b_roll_suggestions,
        production_blueprint=production_blueprint,
        # R11: Decision brief extensions
        risk_if_wrong=risk_if_wrong,
        pivot_angle_id=pivot_angle_id,
        pivot_reasoning=pivot_reasoning,
        decision_criteria=decision_criteria,
    )

    # ─── Stage 6: Self-Critique (Quality Check) ───
    logger.info(f"Producer Stage 6: Self-Critique for job {job_id}")
    try:
        # Truncate packet JSON for token limits
        packet_json_str = json.dumps(packet.to_dict(), indent=2, default=str)
        if len(packet_json_str) > 8000:
            packet_json_str = packet_json_str[:8000] + "\n... (truncated)"

        critique_context = {
            "packet_json": packet_json_str,
            "source_ids": json.dumps(source_ids),
        }
        critique_prompt = build_producer_prompt("critique", critique_context)

        critique_response = client.generate_json(
            prompt=critique_prompt,
            system_message="You are a quality reviewer. Be harsh. Flag generic output.",
            temperature=0.1,  # Factual checking, not creative
        )
        total_cost += critique_response.get("cost", 0.0)

        if "error" not in critique_response:
            critique_data = critique_response.get("data", {})
            quality_score = critique_data.get("quality_score", 100)
            generic_count = critique_data.get("generic_phrase_count", 0)

            if quality_score < 60:
                warnings.append(
                    f"Self-critique quality score: {quality_score}/100 — output may be generic (threshold: 60)"
                )
            if generic_count > 1:
                warnings.append(
                    f"Self-critique found {generic_count} generic phrase(s)"
                )

            # Apply revised sections if the critique improved them
            revised = critique_data.get("revised_sections", {})
            if revised and isinstance(revised, dict):
                if revised.get("one_sentence_pitch") and story_core:
                    # Only apply if revision is meaningfully different
                    original = story_core.one_sentence_pitch
                    revised_pitch = revised["one_sentence_pitch"]
                    if revised_pitch != original and len(revised_pitch) > 10:
                        story_core.one_sentence_pitch = revised_pitch
                        packet.story_core = story_core
                        logger.info("Self-critique revised one_sentence_pitch")

                if revised.get("recommendation_reasoning") and recommendation_reasoning:
                    revised_reasoning = revised["recommendation_reasoning"]
                    if revised_reasoning != recommendation_reasoning and len(revised_reasoning) > 10:
                        packet.recommendation_reasoning = revised_reasoning
                        logger.info("Self-critique revised recommendation_reasoning")

            # Store critique results on packet
            packet.quality_score = quality_score
            packet.quality_issues = critique_data.get("issues", [])

            logger.info(
                f"Self-critique complete: score={quality_score}/100, "
                f"issues={len(packet.quality_issues)}, generic_phrases={generic_count}"
            )
        else:
            warnings.append(f"Self-critique generation warning: {critique_response['error']}")
            logger.warning(f"Self-critique failed: {critique_response['error']}")

    except Exception as e:
        warnings.append(f"Self-critique error (non-fatal): {e}")
        logger.warning(f"Self-critique failed (non-fatal): {e}")

    # Validate cardinality
    cardinality_warnings = validate_producer_cardinality(packet)
    warnings.extend(cardinality_warnings)

    logger.info(
        f"Producer pipeline complete for job {job_id}: "
        f"{len(narrative_angles)} angles, {len(opening_hooks)} hooks, "
        f"{len(title_options)} titles, "
        f"blueprint={'yes' if production_blueprint else 'no'}, "
        f"quality={getattr(packet, 'quality_score', 'N/A')}/100, "
        f"cost=${total_cost:.4f}"
    )

    return packet, total_cost, warnings


def validate_producer_cardinality(packet: ProducerPacket) -> list[str]:
    """Validate cardinality targets from spec.

    Based on: docs/authoritative/spec/Document_Output_Format.md (Doc 4 — formerly Doc 3)

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


def parse_production_blueprint(
    data: dict,
    recommended_angle_id: str,
    narrative_angles: list[NarrativeAngle],
) -> ProductionBlueprint:
    """Parse production blueprint from LLM response.

    Args:
        data: Raw JSON data from LLM
        recommended_angle_id: The selected angle ID
        narrative_angles: List of narrative angles for title lookup

    Returns:
        ProductionBlueprint instance
    """
    # Find selected angle title
    selected_title = ""
    for angle in narrative_angles:
        if angle.angle_id == recommended_angle_id:
            selected_title = angle.title
            break

    # Parse act structure
    act_structure = None
    act_data = data.get("act_structure")
    if act_data and isinstance(act_data, dict):
        acts = []
        for a in act_data.get("acts", []):
            beats = []
            for b in a.get("beats", []):
                beats.append(Beat(
                    beat_number=b.get("beat_number", len(beats) + 1),
                    description=b.get("description", ""),
                    duration_note=b.get("duration_note", ""),
                    source_references=b.get("source_references", []),
                    notes=b.get("notes", ""),
                    # R9: Asset requirements per beat
                    required_assets=b.get("required_assets", []),
                    asset_difficulty=b.get("asset_difficulty", ""),
                ))
            acts.append(Act(
                act_number=a.get("act_number", len(acts) + 1),
                title=a.get("title", ""),
                purpose=a.get("purpose", ""),
                beats=beats,
                approximate_duration=a.get("approximate_duration", ""),
            ))
        act_structure = ActStructure(
            acts=acts,
            total_estimated_duration=act_data.get("total_estimated_duration", ""),
            structure_rationale=act_data.get("structure_rationale", ""),
        )

    # Parse clip sheet
    clip_sheet = []
    for c in data.get("clip_sheet", []):
        if isinstance(c, str):
            clip_sheet.append(ClipSheetEntry(description=c))
            continue
        if not isinstance(c, dict):
            continue
        try:
            clip_type = ClipType(c.get("clip_type", "needs_review"))
        except ValueError:
            clip_type = ClipType.NEEDS_REVIEW
        # R10: Clip scoring fields
        relevance_score = c.get("relevance_score", 0)
        if not isinstance(relevance_score, int) or relevance_score < 1 or relevance_score > 5:
            relevance_score = 3  # Default to middle if invalid

        clip_sheet.append(ClipSheetEntry(
            description=c.get("description", ""),
            source_id=c.get("source_id", ""),
            timestamp=c.get("timestamp", ""),
            clip_type=clip_type,
            clip_type_reasoning=c.get("clip_type_reasoning", ""),
            suggested_use=c.get("suggested_use", ""),
            legal_notes=c.get("legal_notes", ""),
            relevance_score=relevance_score,
            suggested_beat=c.get("suggested_beat", ""),
            alternative_if_unavailable=c.get("alternative_if_unavailable", ""),
        ))

    # Parse enhanced B-roll
    enhanced_b_roll = []
    for b in data.get("enhanced_b_roll", []):
        if isinstance(b, str):
            enhanced_b_roll.append(EnhancedBRollSuggestion(description=b))
            continue
        if not isinstance(b, dict):
            continue
        enhanced_b_roll.append(EnhancedBRollSuggestion(
            description=b.get("description", ""),
            purpose=b.get("purpose", ""),
            search_queries=b.get("search_queries", []),
            visual_style=b.get("visual_style", ""),
            duration_needed=b.get("duration_needed", ""),
        ))

    # Parse production notes
    production_notes = None
    notes_data = data.get("production_notes")
    if notes_data and isinstance(notes_data, dict):
        production_notes = ProductionNotes(
            audio_mood=notes_data.get("audio_mood", ""),
            visual_style=notes_data.get("visual_style", ""),
            legal_flags=notes_data.get("legal_flags", []),
            accessibility_notes=notes_data.get("accessibility_notes", []),
        )

    return ProductionBlueprint(
        selected_angle_id=recommended_angle_id,
        selected_angle_title=selected_title,
        act_structure=act_structure,
        clip_sheet=clip_sheet,
        enhanced_b_roll=enhanced_b_roll,
        production_notes=production_notes,
    )
