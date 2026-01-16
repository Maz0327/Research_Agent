"""Producer Packet prompts - 4-stage creative pipeline.

Based on: docs/authoritative/spec/RASS.md Stage G
Phase: 8

CRITICAL: All output is CREATIVE INTERPRETATION, not facts.
This is explicitly labeled and does not modify Doc 0/1/2.
"""

PRODUCER_ROLE = """You are a creative documentary consultant.
Your job is to help producers find compelling narrative angles.

CRITICAL RULES:
1. All output is CREATIVE INTERPRETATION
2. You are suggesting directions, not stating facts
3. All factual claims must reference source material
4. Be explicit about uncertainty and speculation
5. Higher creativity is encouraged - this is the creative layer

EMPTY OUTPUT PERMISSION:
It is acceptable — and preferred — to return fewer items if:
- No clear angles emerge from the material
- No compelling hooks found
- Risk level is uncertain

DO NOT invent content to fill arrays.
Sparse, accurate output > dense, forced output.
"""

# Stage 1: Story Core
STORY_CORE_PROMPT = """## CONTEXT
Job ID: {job_id}
Source Count: {source_count}
Themes: {themes}
Key Points Summary: {key_points_summary}
Tensions: {tensions}

## TASK: STORY CORE
Generate the central narrative elements for this documentary.

## REQUIREMENTS
- central_question: The big question this documentary will explore
- one_sentence_pitch: Elevator pitch (max 25 words)
- why_this_matters: Why audience should care (connect to universal themes)
- target_audience: Who would watch this
- emotional_arc: The emotional journey (beginning → middle → end)

## OUTPUT (JSON)
{{
    "central_question": "...",
    "one_sentence_pitch": "...",
    "why_this_matters": "...",
    "target_audience": "...",
    "emotional_arc": "..."
}}

REMEMBER: This is creative interpretation. Be bold with narrative vision."""

# Stage 2: Structure Options
STRUCTURE_PROMPT = """## CONTEXT
Job ID: {job_id}
Story Core: {story_core}
Themes: {themes}
Key Moments: {key_moments}
Source Count: {source_count}

## TASK: NARRATIVE STRUCTURE
Generate narrative angles and structure options.

## REQUIREMENTS
Generate:
- 2-4 narrative_angles (different ways to tell this story)
- 2-3 structure_options (how to organize the documentary)

Each narrative_angle needs:
- angle_id: ANG_1, ANG_2, etc.
- title, description, strengths, weaknesses, best_for
- key_sources: which sources support this angle

Each structure_option needs:
- structure_type: chronological/thematic/mystery_reveal/compare_contrast/problem_solution
- description, section_breakdown, pros, cons

## OUTPUT (JSON)
{{
    "narrative_angles": [...],
    "structure_options": [...]
}}"""

# Stage 3: Creative Elements
CREATIVE_ELEMENTS_PROMPT = """## CONTEXT
Job ID: {job_id}
Story Core: {story_core}
Narrative Angles: {narrative_angles}
Key Points: {key_points}
Sources: {sources}

## TASK: CREATIVE ELEMENTS
Generate opening hooks, titles, and thumbnail concepts.

## REQUIREMENTS
Generate:
- 2-4 opening_hooks (different ways to start)
- 3-5 title_options with subtitles
- 2-3 thumbnail_concepts
- 3-8 key_moments (compelling moments from sources)

Each opening_hook needs:
- hook_type: cold_open/provocative_question/surprising_fact/personal_story/scene_setting
- content, tone, source_basis

Each title_option needs:
- title, subtitle (optional), tone: serious/provocative/curious/urgent
- seo_considerations (optional)

Each key_moment needs:
- moment, source_id, timestamp (if available), why_compelling, potential_use

## OUTPUT (JSON)
{{
    "opening_hooks": [...],
    "title_options": [...],
    "thumbnail_concepts": [...],
    "key_moments": [...]
}}"""

# Stage 4: Risk & Context
RISK_CONTEXT_PROMPT = """## CONTEXT
Job ID: {job_id}
Story Core: {story_core}
Themes: {themes}
Tensions: {tensions}
Sources: {sources}

## TASK: RISK ASSESSMENT & PRODUCTION CONTEXT
Assess risks and suggest interviews/b-roll.

## REQUIREMENTS
Generate:
- risk_assessment (required)
- interview_suggestions
- b_roll_suggestions

risk_assessment needs:
- sensitivity_level: low/medium/high
- potential_issues, mitigation_suggestions
- legal_considerations, ethical_considerations

interview_suggestions needs:
- people_to_contact: [{{name, role, why_relevant, potential_questions}}]
- expert_perspectives_needed

## OUTPUT (JSON)
{{
    "risk_assessment": {{
        "sensitivity_level": "...",
        "potential_issues": [...],
        "mitigation_suggestions": [...],
        "legal_considerations": [...],
        "ethical_considerations": [...]
    }},
    "interview_suggestions": {{
        "people_to_contact": [...],
        "expert_perspectives_needed": [...]
    }},
    "b_roll_suggestions": [...]
}}"""


def build_producer_prompt(stage: str, context: dict) -> str:
    """Build prompt for specific producer stage.

    Args:
        stage: One of 'story_core', 'structure', 'creative', 'risk'
        context: Context dict with required fields

    Returns:
        Formatted prompt string
    """
    prompts = {
        "story_core": STORY_CORE_PROMPT,
        "structure": STRUCTURE_PROMPT,
        "creative": CREATIVE_ELEMENTS_PROMPT,
        "risk": RISK_CONTEXT_PROMPT,
    }

    if stage not in prompts:
        raise ValueError(f"Unknown producer stage: {stage}")

    return prompts[stage].format(**context)
