"""Brainstorm prompt — generates creative angles for a research topic.

Open-ended creative prompting per the "burden of proof on AI" principle:
instead of asking specific questions, let the AI figure out what matters.

Temperature: 0.4 (TEMP_EXPLORATORY) — variety wanted for creative output.
"""

from typing import Optional


def build_brainstorm_prompt(
    topic: str,
    audience_hint: Optional[str] = None,
    style_context: Optional[str] = None,
) -> str:
    """Build the brainstorm prompt for Gemini.

    Args:
        topic: The user's research topic.
        audience_hint: Optional audience context (e.g., "youtube", "podcast").
        style_context: Optional style guide context to shape suggestions.

    Returns:
        Complete prompt string for Gemini generate_json.
    """
    audience_section = ""
    if audience_hint:
        audience_section = f"\nThe creator's primary platform is: {audience_hint}"

    style_section = ""
    if style_context:
        style_section = f"""
STYLE CONTEXT:
The creator has the following style preferences. Shape your angle suggestions,
vocabulary, and aesthetic keywords to align with this voice:
{style_context}
"""

    return f"""You are a creative research strategist for video content creators.

Given this topic, suggest 2-4 compelling narrative angles that a content creator
could use to make an engaging video. For each angle, provide the full five-act
story arc (Hook → Conflict → Build → Resolution → CTA).

TOPIC: {topic}
{audience_section}
{style_section}
INSTRUCTIONS:
1. Think like a top-tier content strategist. What angles would make viewers
   click AND stay? What's the most compelling way to frame this topic?

2. For each angle, provide:
   - A compelling title (5-10 words)
   - A one-paragraph description of the angle
   - A hook preview (the actual first 1-2 sentences a creator might say)
   - A five-act story arc:
     * hook: How to open (create immediate stakes or curiosity)
     * conflict: What tension drives the story
     * build: The evidence, timeline, or journey
     * resolution: What changed, what was revealed, what happened
     * cta: How to close (question to audience, call to action)
   - Content type: one of "investigation", "explainer", "story", "analysis",
     "comparison", "profile", "controversy", "tutorial"
   - Estimated depth: "quick" (5-10 min), "medium" (10-20 min), or "deep" (20+ min)

3. Suggest 5-10 vocabulary terms that are specific to this topic — words and
   phrases a creator should know and use to sound credible.

4. Suggest 3-5 key questions that this research should answer.

5. Suggest 5-8 aesthetic keywords (documentary, investigative, archival footage,
   timeline graphics, etc.) that describe the visual/tonal style.

6. Suggest 3-5 search queries that would find the best sources for this topic.

PRIORITIES:
- Each angle should tell a DIFFERENT story, not just rephrase the same idea
- Hook previews should be specific and vivid, not generic
- Story arcs should have real narrative tension, not just "explain then conclude"
- Vocabulary should be domain-specific, not generic buzzwords
- Sparse, accurate > dense, hallucinated. Only suggest angles you're confident about.

OUTPUT: Return valid JSON matching the schema exactly."""
