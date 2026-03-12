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

    prompt = f"""You are a research assistant creating a PREVIEW brief for a content creator.

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
      "text": "<compelling opening hook based on snippets>",
      "why_it_works": "<brief explanation>"
    }},
    {{
      "hook_id": "HOOK_B",
      "text": "<alternative hook angle>",
      "why_it_works": "<brief explanation>"
    }}
  ],
  "setup": {{
    "text": "<2-3 sentences explaining the core topic based on snippets>"
  }},
  "core_facts": [
    {{
      "fact_id": "FACT_1",
      "statement": "<key fact from snippets>",
      "significance": "high|medium|low",
      "say_it_like": "<how to present this fact compellingly>"
    }},
    {{
      "fact_id": "FACT_2",
      "statement": "<another key fact>",
      "significance": "high|medium|low",
      "say_it_like": "<presentation guidance>"
    }},
    {{
      "fact_id": "FACT_3",
      "statement": "<another key fact>",
      "significance": "high|medium|low",
      "say_it_like": "<presentation guidance>"
    }}
  ],
  "source_count": {len(top_candidates)},
  "preview_note": "This is a quick preview based on source snippets. Run full research for complete analysis with verified claims."
}}

IMPORTANT:
- Only use information present in the snippets above
- Do not invent facts or details not in the snippets
- Keep it concise — this is a preview, not a full brief
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
            model="gemini-2.0-flash",  # Fast model for preview
            temperature=0.3,
        )
        # generate_json returns {"data": {...}, "cost": ...}
        result = raw.get("data", raw) if isinstance(raw, dict) else raw

        # Ensure preview flags are set
        if isinstance(result, dict):
            result["is_preview"] = True
            result["brief_type"] = "quick"

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
