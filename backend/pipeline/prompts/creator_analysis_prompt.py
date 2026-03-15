"""Prompt templates for Creator Analysis — style profile extraction.

Analyzes 3-5 video transcripts from a single creator to produce a
Creator Style Profile capturing their unique patterns.

Temperature: 0.4 (brainstorm-level — needs variety in descriptions)
"""

CREATOR_ANALYSIS_ROLE = (
    "You are an expert content analyst and media coach who specializes in "
    "reverse-engineering creator styles. You analyze video transcripts to "
    "identify unique patterns in hooks, narrative structure, vocabulary, "
    "tone, and aesthetic choices. Your output helps other creators understand "
    "and learn from successful content styles."
)


def build_creator_analysis_prompt(
    creator_name: str,
    transcripts: list[dict],
) -> str:
    """Build the prompt for creator style analysis.

    Args:
        creator_name: Name of the creator being analyzed.
        transcripts: List of dicts with keys: title, transcript, url.

    Returns:
        Prompt string for Gemini.
    """
    transcript_sections = []
    for i, t in enumerate(transcripts, 1):
        title = t.get("title", f"Video {i}")
        text = t.get("transcript", "")
        # Truncate very long transcripts to stay within token limits
        if len(text) > 15000:
            text = text[:15000] + "\n[... transcript truncated for analysis ...]"
        transcript_sections.append(
            f"=== VIDEO {i}: {title} ===\n{text}\n"
        )

    transcripts_block = "\n".join(transcript_sections)

    return f"""Analyze the following {len(transcripts)} video transcripts from creator "{creator_name}" and produce a comprehensive Creator Style Profile.

CREATOR: {creator_name}
VIDEO COUNT: {len(transcripts)}

{transcripts_block}

YOUR TASK:
Analyze ALL transcripts above and identify the creator's unique style patterns across these dimensions:

1. HOOK PATTERNS: Identify recurring opening hook types (question hooks, stat hooks, story hooks, contradiction hooks, visual hooks). For each, provide a specific example from the transcripts and note how frequently it appears.

2. NARRATIVE STRUCTURE: What structure does the creator typically use? (Hero's Journey, Five-Act, Problem-Solution, Chronological, Mystery-Reveal). Describe their pacing and transition style.

3. VOCABULARY FINGERPRINT: What phrases does this creator use repeatedly? What filler words? Any unique expressions or catchphrases? What tone markers define their language?

4. AESTHETIC PROFILE: Based on the content, describe their visual style, color palette preferences, B-roll approach, music tone, pacing, and typography style. Infer from transcript cues and content type.

5. TONE DESCRIPTORS: Rate formality (very_formal to very_casual), humor usage (none/occasional/frequent/core_element), emotional range, authority level (peer/expert/mentor/entertainer), and energy level (calm/moderate/high/intense).

6. SYNTHESIS: Provide a style_summary (2-3 sentences capturing the essence), recommended_voice (how to write in their style), recommended_hook_style (how to open videos like them), and recommended_structure (how to structure content like them).

Be SPECIFIC — cite actual phrases, patterns, and examples from the transcripts. Avoid generic descriptions.
"""
