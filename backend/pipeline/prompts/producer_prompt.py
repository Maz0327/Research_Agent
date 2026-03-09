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

ANTI-GENERIC RULES (VIOLATIONS WILL BE DETECTED AND FLAGGED BY CODE):
1. Never start two consecutive sentences with the same word
2. BANNED PHRASES — never use: "it's important to note", "it's worth noting", "interestingly", "notably", "it depends", "various factors", "needless to say", "at the end of the day", "in today's world", "delve into", "rich tapestry", "multifaceted", "navigate the complexities", "a nuanced understanding", "paradigm shift", "holistic approach", "shed light on", "raises important questions"
3. Every recommendation MUST reference a specific source by ID (e.g. SRC_1)
4. If you catch yourself hedging, commit to a position and state your confidence level
5. Quantify when possible — use percentages, counts, timeframes from the sources
6. Never repeat the same idea in different words — state it once, clearly
7. Be SPECIFIC: "Source 1's interview at 12:30" not "one of the sources mentioned"

GROUNDING RULE FOR CREATIVE INTERPRETATION:
- Creative opinions (angle recommendations, risk assessments) are allowed without source refs
- Factual claims about the world (who covered this topic, when events happened) must be marked as uncertain if not from sources
- Use "likely covered by..." instead of "covered by [specific name]" when uncertain about external facts
- Stage 6 self-critique will flag ungrounded factual claims

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

# Stage 2: Structure Options + Story Landscape + Recommendation
STRUCTURE_PROMPT = """## CONTEXT
Job ID: {job_id}
Story Core: {story_core}
Themes: {themes}
Key Moments: {key_moments}
Source Count: {source_count}

## TASK: NARRATIVE STRUCTURE + STORY LANDSCAPE + DECISION BRIEF
Generate a story landscape, narrative angles with confidence, structure options,
and a DECISIVE recommendation with risk/pivot analysis.

## REQUIREMENTS

### Story Landscape (R8: Competitive Framing)
Analyze the content landscape using these categories:

- saturated_angles: List 2-4 angles that are SATURATED. For each:
  - angle: The angle description
  - who_covered_it: Name specific creators, outlets, or publications that have done this. If unsure of specific names, say "widely covered by mainstream media" — do NOT fabricate specific names.
  - why_avoid: Why this is played out
  - trend: "declining" (audience fatigue) or "stable" (still works but crowded)

- emerging_angles: List 1-3 angles that are EMERGING. For each:
  - angle: The angle description
  - evidence: Why you believe this is gaining traction
  - window: "narrow" (act fast) or "open" (time to develop)
  - trend: "rising"

- untold_angles: List 1-2 angles that are UNTOLD. For each:
  - angle: The angle description
  - why_untold: Why nobody has covered this yet
  - risk: What makes this harder to produce
  - trend: "unknown"

- landscape_summary: 2-3 sentences with a DECISIVE take on the landscape.

### Narrative Angles
Generate 2-4 narrative_angles (different ways to tell this story).

Each narrative_angle needs:
- angle_id: ANG_1, ANG_2, etc.
- title, description, strengths, weaknesses, best_for
- key_sources: which sources support this angle
- confidence: "strong" (well-supported by research), "moderate" (some support, needs more), or "speculative" (creative leap, limited evidence)

### Structure Options
Generate 2-3 structure_options (how to organize the documentary).

Each structure_option needs:
- structure_type: chronological/thematic/mystery_reveal/compare_contrast/problem_solution
- description, section_breakdown, pros, cons

### Recommendation (DECISION BRIEF — R11)
After analyzing all angles, provide a DECISION BRIEF:
- recommended_angle_id: The angle_id you recommend (e.g. "ANG_2")
- recommendation_reasoning: 2-3 sentences on WHY this angle wins
- risk_if_wrong: What happens if this angle doesn't resonate? (1-2 sentences)
- pivot_angle_id: Which angle is the backup? (e.g. "ANG_1")
- pivot_reasoning: Why this is the best fallback (1 sentence)
- decision_criteria: What evidence would CHANGE this recommendation? (1-2 bullet points as list)

Be DECISIVE. This is a RECOMMENDATION, not a menu. Do not hedge.

## OUTPUT (JSON)
{{
    "story_landscape": {{
        "saturated_angles": [...],
        "emerging_angles": [...],
        "untold_angles": [...],
        "landscape_summary": "..."
    }},
    "narrative_angles": [...],
    "structure_options": [...],
    "recommended_angle_id": "ANG_X",
    "recommendation_reasoning": "...",
    "risk_if_wrong": "...",
    "pivot_angle_id": "ANG_Y",
    "pivot_reasoning": "...",
    "decision_criteria": ["...", "..."]
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


# Stage 5: Production Blueprint
PRODUCTION_BLUEPRINT_PROMPT = """## CONTEXT
Job ID: {job_id}
Selected Angle: {selected_angle}
Story Core: {story_core}
Themes: {themes}
Key Points: {key_points}
Sources: {sources}

## TASK: PRODUCTION BLUEPRINT
Create a shooting script and production guide for the selected angle.

## REQUIREMENTS

### Act Structure
Create a 3-act structure:
- ACT I: SETUP — Hook + context + inciting incident (3-5 beats)
- ACT II: EXPLORATION — Main body with evidence, arguments, turns (3-5 beats)
- ACT III: RESOLUTION — Climax + fallout + outro (3-5 beats)

Each act needs:
- act_number (1-3), title, purpose, approximate_duration (e.g. "0:00 - 5:00")
- beats: array of beats, each with:
  - beat_number, description (what happens)
  - duration_note (e.g. "0:00 - 0:30")
  - source_references (which sources support this beat)
  - notes (production notes, optional)
  - required_assets: list of specific assets needed (footage, graphics, interviews, text overlays)
  - asset_difficulty: "easy" (stock footage available), "medium" (requires licensing/contact), "hard" (requires original production)

Total structure_rationale: 2-3 sentences on why this structure works.
total_estimated_duration: e.g. "45-55 min"

### Clip Sheet
For each source video, list key clips:
- description, source_id, timestamp (if known)
- clip_type: "third_party" (✅ usable footage from other creators/studios), "original_skip" (❌ creator's own camera — skip), "needs_review" (⚠️ unclear rights)
- clip_type_reasoning: brief explanation of classification
- suggested_use: which act/beat this fits
- legal_notes: any rights concerns
- relevance_score: 1-5 (5=essential for the angle, 1=tangentially related)
- suggested_beat: which specific act/beat this fits (e.g. "Act 1, Beat 3")
- alternative_if_unavailable: what to search for if this clip can't be licensed

### Enhanced B-Roll
For each B-roll need:
- description, purpose
- search_queries: 2-3 exact search terms to find this footage
- visual_style: what it should look/feel like
- duration_needed: how long you need

### Production Notes
- audio_mood: overall audio/music direction
- visual_style: color grade, editing style
- legal_flags: any claims that need legal review before airing
- accessibility_notes: subtitle needs, content warnings, etc.

## OUTPUT (JSON)
{{
    "act_structure": {{
        "acts": [
            {{
                "act_number": 1,
                "title": "...",
                "purpose": "...",
                "approximate_duration": "...",
                "beats": [
                    {{
                        "beat_number": 1,
                        "description": "...",
                        "duration_note": "...",
                        "source_references": ["..."],
                        "notes": "..."
                    }}
                ]
            }}
        ],
        "total_estimated_duration": "...",
        "structure_rationale": "..."
    }},
    "clip_sheet": [
        {{
            "description": "...",
            "source_id": "...",
            "timestamp": "...",
            "clip_type": "third_party|original_skip|needs_review",
            "clip_type_reasoning": "...",
            "suggested_use": "...",
            "legal_notes": "..."
        }}
    ],
    "enhanced_b_roll": [
        {{
            "description": "...",
            "purpose": "...",
            "search_queries": ["...", "..."],
            "visual_style": "...",
            "duration_needed": "..."
        }}
    ],
    "production_notes": {{
        "audio_mood": "...",
        "visual_style": "...",
        "legal_flags": ["..."],
        "accessibility_notes": ["..."]
    }}
}}

## RULES
1. EVERY BEAT must reference specific sources
2. CLIP TYPES must be classified with reasoning
3. EVERY B-ROLL item must have 2-3 specific search queries
4. Be REALISTIC about timing — beats should add up to total
5. GROUND IN RESEARCH — don't invent content not in the sources"""


# Stage 6: Self-Critique (Quality Review)
SELF_CRITIQUE_PROMPT = """## CONTEXT
You are reviewing a completed Producer Packet for quality.

Producer Packet (truncated):
{packet_json}

Source IDs available: {source_ids}

## TASK: QUALITY REVIEW
Review the entire packet and identify:

1. **Ungrounded Claims**: Any recommendation not traceable to a specific source
2. **Repetitive Language**: Same idea stated multiple ways
3. **Generic Filler**: Phrases that could apply to ANY topic (not specific to this research)
4. **Missing Source Refs**: Beats, suggestions, or claims without source_id attribution
5. **Inconsistencies**: Clip types or beat descriptions that don't match the selected angle

## OUTPUT (JSON)
{{
    "issues": [
        {{
            "section": "story_core|narrative_angles|hooks|blueprint|risk|titles",
            "severity": "critical|warning|info",
            "description": "What the issue is",
            "suggestion": "How to fix it"
        }}
    ],
    "revised_sections": {{
        "one_sentence_pitch": "Revised pitch if original was generic (or null if fine)",
        "recommendation_reasoning": "Revised reasoning if original was vague (or null if fine)"
    }},
    "quality_score": 75,
    "generic_phrase_count": 0
}}

## SCORING GUIDE
- 90-100: Specific, grounded, no generic filler — publishable
- 70-89: Mostly specific, minor hedging — usable with light edits
- 50-69: Contains generic passages — needs revision
- 0-49: Mostly generic filler — significant revision needed

## RULES
1. Be HARSH — flag anything that reads like generic AI output
2. "Could apply to any documentary" = GENERIC = flag it
3. Absence of specific source references = UNGROUNDED = flag it
4. Same concept restated in different words = REPETITIVE = flag it
5. Banned phrases: "it's important to note", "interestingly", "notably", "delve into", "rich tapestry", "multifaceted", "paradigm shift"
6. If revised_sections values are not needed, set them to null — do NOT rewrite things that are already good"""


def build_producer_prompt(stage: str, context: dict) -> str:
    """Build prompt for specific producer stage.

    Args:
        stage: One of 'story_core', 'structure', 'creative', 'risk', 'blueprint'
        context: Context dict with required fields

    Returns:
        Formatted prompt string
    """
    prompts = {
        "story_core": STORY_CORE_PROMPT,
        "structure": STRUCTURE_PROMPT,
        "creative": CREATIVE_ELEMENTS_PROMPT,
        "risk": RISK_CONTEXT_PROMPT,
        "blueprint": PRODUCTION_BLUEPRINT_PROMPT,
        "critique": SELF_CRITIQUE_PROMPT,
    }

    if stage not in prompts:
        raise ValueError(f"Unknown producer stage: {stage}")

    return prompts[stage].format(**context)
