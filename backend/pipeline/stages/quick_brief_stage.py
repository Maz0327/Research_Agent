"""
Quick Brief Stage — Single LLM call preview of Creator Brief.

Generates a lightweight Creator Brief preview from search candidate
snippets + topic. Uses Gemini Flash for speed. Target: <15 seconds.

This is NOT a full pipeline run. It produces a simplified brief
with is_preview=True for display purposes only. The full pipeline
run will replace it when the user approves sources.
"""
from typing import Any

from loguru import logger

from backend.pipeline.search.relevance_validator import SearchCandidate
from backend.pipeline.style_enforcer import enforce_style


async def generate_quick_brief(
    topic: str,
    candidates: list[SearchCandidate],
) -> dict[str, Any]:
    """
    Generate a Quick Brief preview from search candidates.

    This is a single LLM call that produces a simplified Creator Brief
    structure for preview purposes. Not a full extraction+synthesis run.

    Args:
        topic: Research topic
        candidates: Scored search candidates with snippets

    Returns:
        Dict matching Creator Brief structure (simplified, preview mode)
    """
    # Build context from top candidates
    top_candidates = candidates[:6]  # Use top 6 for preview

    snippets_text = "\n\n".join([
        f"Source: {c.title}\nURL: {c.url}\nSnippet: {c.snippet}"
        for c in top_candidates
    ])

    prompt = f"""You are a research analyst writing for content creators.

Your audience makes YouTube videos, podcasts, and articles.
They need to absorb your findings fast and build scripts from them.

You write like a sharp colleague explaining findings — not like a professor.
You do NOT invent facts. Everything must come from the snippets below.

WRITING STYLE — MANDATORY:
- Max sentence length: 25 words. Break longer ones.
- Lead with the insight, not the setup.
  BAD: "Modern films often lack the feel of their predecessors, a phenomenon explored by essayists..."
  GOOD: "Old movies feel more real than new ones. Here's why that's not an accident."
- No hedging. Assert directly.
  BANNED: "is attributed to," "is said to," "is perceived as," "it could be argued," "a phenomenon explored by"
  USE: "X happened." "Sources disagree on Y."
- Transitions must feel human, not academic.
  BANNED: "furthermore," "additionally," "in contrast," "moreover," "consequently"
  USE: "But here's the thing." "That's not the whole story."
- No academic vocabulary.
  BANNED: "corpus," "paradigm," "cinematic output," "visual fidelity," "haptic visuality"

TOPIC: {topic}

AVAILABLE SOURCE SNIPPETS:
{snippets_text}

Based ONLY on these snippets (not your training data), create a quick preview brief.
This is a PREVIEW — it will be replaced by a full analysis later.

Return a JSON object with this structure:
{{
  "is_preview": true,
  "brief_type": "quick",
  "topic": "<the research topic>",
  "hook_options": [
    {{
      "hook_id": "HOOK_A",
      "text": "<sharp, direct hook — lead with the surprising or counterintuitive thing>",
      "why_it_works": "<brief explanation>"
    }},
    {{
      "hook_id": "HOOK_B",
      "text": "<alternative angle — try a different entry point into the story>",
      "why_it_works": "<brief explanation>"
    }}
  ],
  "setup": {{
    "text": "<2-3 SHORT sentences. Assert what's true. No hedging, no 'observers note that', no 'it is attributed to'.>"
  }},
  "core_facts": [
    {{
      "fact_id": "FACT_1",
      "statement": "<key fact from snippets — one direct sentence>",
      "significance": "high|medium|low",
      "say_it_like": "<how a YouTuber would actually say this on camera>"
    }},
    {{
      "fact_id": "FACT_2",
      "statement": "<another key fact — one direct sentence>",
      "significance": "high|medium|low",
      "say_it_like": "<how a YouTuber would actually say this on camera>"
    }},
    {{
      "fact_id": "FACT_3",
      "statement": "<another key fact — one direct sentence>",
      "significance": "high|medium|low",
      "say_it_like": "<how a YouTuber would actually say this on camera>"
    }}
  ],
  "source_count": {len(top_candidates)},
  "preview_note": "This is a quick preview based on source snippets. Run full research for complete analysis with verified claims."
}}

RULES:
- Only use information from the snippets above
- Do not invent facts
- Every sentence under 25 words
- Return valid JSON only
"""

    try:
        import asyncio
        from backend.integrations.gemini_client import GeminiClient

        client = GeminiClient()
        # generate_json is synchronous — run in executor to avoid blocking
        raw = await asyncio.to_thread(
            client.generate_json,
            prompt=prompt,
            model="gemini-2.5-flash",  # Fast model for preview
            temperature=0.3,
        )
        # generate_json returns {"data": {...}, "cost": ...}
        result = raw.get("data", raw) if isinstance(raw, dict) else raw

        # Ensure preview flags are set
        if isinstance(result, dict):
            result["is_preview"] = True
            result["brief_type"] = "quick"

            # Run style enforcement on LLM output (warnings only for preview)
            style_warnings = _check_brief_style(result)
            if style_warnings:
                result["_style_warnings"] = style_warnings
                logger.warning(
                    f"Quick brief style violations ({len(style_warnings)}): "
                    f"{style_warnings[:3]}"
                )

        logger.info(f"Quick brief generated for topic: {topic[:50]}")
        return result

    except Exception as e:
        logger.error(f"Quick brief generation failed: {e}")
        # Return a minimal fallback
        return {
            "is_preview": True,
            "brief_type": "quick",
            "topic": topic,
            "hook_options": [
                {
                    "hook_id": "HOOK_A",
                    "text": f"What if everything you knew about {topic} was wrong?",
                    "why_it_works": "Creates curiosity gap",
                },
                {
                    "hook_id": "HOOK_B",
                    "text": f"Here's what the sources are saying about {topic}…",
                    "why_it_works": "Direct and informative",
                },
            ],
            "setup": {
                "text": f"We found {len(top_candidates)} sources about {topic}. Run full research for detailed analysis.",
            },
            "core_facts": [],
            "source_count": len(top_candidates),
            "preview_note": "Quick preview unavailable. Run full research for complete analysis.",
        }


def _check_brief_style(result: dict[str, Any]) -> list[str]:
    """Run enforce_style() on all text fields in a quick brief result.

    Args:
        result: Quick brief dict from LLM

    Returns:
        List of style violation strings (empty if clean)
    """
    warnings: list[str] = []

    # Collect all text fields worth checking
    texts_to_check: list[tuple[str, str]] = []

    # Setup text
    setup = result.get("setup", {})
    if isinstance(setup, dict) and setup.get("text"):
        texts_to_check.append(("setup", setup["text"]))

    # Hook texts
    for hook in result.get("hook_options", []):
        if isinstance(hook, dict) and hook.get("text"):
            texts_to_check.append((hook.get("hook_id", "hook"), hook["text"]))

    # Core fact statements and say_it_like
    for fact in result.get("core_facts", []):
        if isinstance(fact, dict):
            if fact.get("statement"):
                texts_to_check.append((fact.get("fact_id", "fact"), fact["statement"]))
            if fact.get("say_it_like"):
                texts_to_check.append((f"{fact.get('fact_id', 'fact')}.say_it_like", fact["say_it_like"]))

    # Run style checks on each field
    for field_name, text in texts_to_check:
        passes, violations = enforce_style(text)
        if not passes:
            for v in violations:
                warnings.append(f"[{field_name}] {v}")

    return warnings
