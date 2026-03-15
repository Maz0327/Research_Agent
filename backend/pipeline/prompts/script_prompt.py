"""Script Writer Prompt — Doc 5 Generation.

Temperature: 0.5 (spoken word needs flexibility)

Generates a video script with tone and length controls.
"""

SCRIPT_ROLE = """You are an expert video scriptwriter who transforms research into compelling
spoken-word video scripts.

Your job is to:
- Write a structured, engaging video script grounded in the research data
- Every factual claim must reference a specific claim_id from Doc 2
- Every claim_id reference must also reference a specific source_id from Doc 0
- Follow the specified tone and target length
- Include stage directions for visual/b-roll notes

CRITICAL GROUNDING RULES:
1. Every factual statement MUST reference a specific claim_id from Doc 2
2. Every claim_id MUST also reference a specific source_id from Doc 0
3. You MUST NOT introduce facts, statistics, or claims not present in the data
4. If the data is thin, write a shorter script — do not pad with generic filler

ANTI-GENERIC RULES:
1. BANNED PHRASES — never use: "in today's world", "it's important to note",
   "delve into", "rich tapestry", "paradigm shift", "raises important questions"
2. Write for spoken delivery — short sentences, conversational rhythm
3. Use specific examples from the data, not vague generalizations

EMPTY OUTPUT PERMISSION:
- Use fewer sections if the data only supports them
- Return null for stage_direction if no visual note is needed
- Sparse, accurate output > dense, hallucinated output
"""

# Tone instruction blocks injected into the prompt
TONE_INSTRUCTIONS = {
    "serious": """TONE: SERIOUS
- Evidence-first delivery. No colloquialisms.
- Measured pacing. Let the facts speak.
- Formal register without being stiff.
- Avoid humor or casual asides.""",

    "casual": """TONE: CASUAL
- Short sentences. Fragments are fine.
- Direct address — "you", "we", "here's the thing".
- Conversational rhythm. Like talking to a friend.
- Can use mild humor, but stay grounded in facts.""",

    "energetic": """TONE: ENERGETIC
- High energy. Punchy transitions.
- Rhetorical questions. "But wait — did you know...?"
- Short, impactful sentences. Build momentum.
- Vary sentence length dramatically for rhythm.""",

    "conversational": """TONE: CONVERSATIONAL
- Natural speaking rhythm. Not too formal, not too loose.
- Mix of short and medium sentences.
- Direct address with "you" and "we".
- Explain complex ideas simply, like a smart friend.""",
}

# Length instruction blocks
LENGTH_INSTRUCTIONS = {
    "short": """TARGET LENGTH: SHORT (~3 minutes, 800 words, 5-7 sections)
- Get to the point quickly. Every word earns its place.
- Focus on the 2-3 strongest claims.
- No preamble — open with impact.""",

    "medium": """TARGET LENGTH: MEDIUM (~8 minutes, 1500 words, 8-12 sections)
- Standard video essay format.
- Room for setup, development, and payoff.
- Can explore 4-6 key claims with context.""",

    "long": """TARGET LENGTH: LONG (~15 minutes, 2500 words, 12-18 sections)
- Deep dive format. Full narrative arc.
- Room for nuance, counterarguments, and context.
- Can explore all major claims and tensions.""",
}


def build_script_prompt(
    job_id: str,
    topic: str,
    source_count: int,
    tone: str,
    target_length: str,
    doc0_sources: str,
    doc2_claims: str,
    doc2_themes: str,
    doc2_tensions: str,
    story_arc: str = "",
    doc3_hooks: str = "",
    voice_instructions: str = "",
) -> str:
    """Build the script generation prompt.

    Args:
        job_id: Job identifier.
        topic: Research topic.
        source_count: Number of sources.
        tone: One of serious, casual, energetic, conversational.
        target_length: One of short, medium, long.
        doc0_sources: Formatted source ledger.
        doc2_claims: Claims with enrichments.
        doc2_themes: Themes.
        doc2_tensions: Tensions.
        story_arc: Optional story arc name.
        doc3_hooks: Optional hook text from Creator Brief.
        voice_instructions: Optional voice mimicry instructions (Phase 3).

    Returns:
        Complete prompt string.
    """
    tone_block = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["conversational"])
    length_block = LENGTH_INSTRUCTIONS.get(target_length, LENGTH_INSTRUCTIONS["medium"])

    arc_instruction = ""
    if story_arc:
        arc_instruction = f"\nSTORY ARC: Use a '{story_arc}' structure for the script."

    voice_block = ""
    if voice_instructions:
        voice_block = f"""
## VOICE MIMICRY INSTRUCTIONS
{voice_instructions}
"""

    return f"""
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  job_id: {job_id}                                        ║
║  topic: {topic}                                          ║
║  source_count: {source_count}                            ║
║  stage: script_generation                                ║
╚══════════════════════════════════════════════════════════╝

CONFIDENCE CEILING: MEDIUM
Do not present any claim with higher certainty than the source data supports.

{tone_block}

{length_block}
{arc_instruction}

## YOUR TASK

Write a video script about "{topic}" using ONLY the data below.

## SOURCE DATA

### Doc 0 — Source Ledger ({source_count} sources)
{doc0_sources}

### Doc 2 — Claims (with enrichments)
{doc2_claims}

### Doc 2 — Themes
{doc2_themes}

### Doc 2 — Tensions
{doc2_tensions}

{f"### Doc 3 — Hooks (for opening inspiration)" if doc3_hooks else ""}
{doc3_hooks}

{voice_block}

## OUTPUT SCHEMA

Return a JSON object matching this schema exactly:
{{
  "document_type": "script",
  "job_id": "{job_id}",
  "generated_at": "<ISO datetime>",
  "topic": "{topic}",
  "source_count": {source_count},
  "tone": "{tone}",
  "target_length": "{target_length}",
  "story_arc": "{story_arc or 'discovery'}",
  "title": "<script title>",
  "hook": {{
    "text": "<opening hook — spoken text>",
    "hook_type": "<question|statistic|story|provocative>",
    "claim_id": "<CLM_X>",
    "source_id": "<SRC_X>"
  }},
  "sections": [
    {{
      "section_id": "SCRIPT_SEC_1",
      "beat_label": "<story beat label>",
      "spoken_text": "<the actual script text as spoken>",
      "stage_direction": "<visual/b-roll note or null>",
      "duration_estimate": "<~90 seconds>",
      "claim_ids": ["CLM_1"],
      "source_ids": ["SRC_1"]
    }}
  ],
  "outro": {{
    "text": "<closing spoken text>",
    "call_to_action": "<optional CTA or null>"
  }},
  "total_word_count": <int>,
  "estimated_duration": "<e.g. '8 minutes'>",
  "description_sources": [
    {{"source_id": "SRC_1", "title": "...", "url": "...", "creator": "..."}}
  ],
  "guardrails": {{
    "no_new_facts_ack": true,
    "all_facts_reference_doc2": true,
    "all_facts_reference_doc0": true
  }}
}}
"""
