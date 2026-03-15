"""Voice Profile Generation Stage.

Temperature: 0.2 (analytical extraction)

Analyzes creator video transcripts to build a voice profile.
Two LLM calls:
1. Style profile extraction (reuses existing creator analysis patterns)
2. Voice deep-dive: rhythm, transitions, emphasis patterns
"""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.voice_profile import (
    VoiceProfile,
    SentenceRhythm,
    TransitionPattern,
    EmphasisPatterns,
)

VOICE_ANALYSIS_TEMPERATURE = 0.2

VOICE_ANALYSIS_ROLE = """You are a linguistic analyst specializing in spoken communication patterns.
Your job is to analyze video transcripts and extract detailed voice characteristics.

Focus on:
1. Sentence rhythm — average length, variation, use of fragments
2. Transition patterns — how the speaker moves between ideas
3. Opening patterns — how they start videos/segments
4. Closing patterns — how they end videos/segments
5. Emphasis patterns — repetition, rhetorical questions, pauses

Be specific and cite examples from the transcript when possible.
"""

VOICE_ANALYSIS_PROMPT = """Analyze the following transcripts from {creator_name} and extract their voice patterns.

## TRANSCRIPTS
{transcripts}

## OUTPUT SCHEMA

Return a JSON object:
{{
  "sentence_rhythm": {{
    "avg_sentence_length": <int, average words per sentence>,
    "length_variation": "<uniform|varied|highly_varied>",
    "fragment_frequency": "<none|occasional|frequent>"
  }},
  "transition_patterns": [
    {{
      "from_context": "<e.g. 'evidence to opinion'>",
      "phrase": "<the actual transition phrase used>",
      "frequency": "<common|occasional|rare>"
    }}
  ],
  "opening_patterns": ["<description of how they open>"],
  "closing_patterns": ["<description of how they close>"],
  "emphasis_patterns": {{
    "repetition_style": "<description>",
    "rhetorical_questions": <true|false>,
    "pause_markers": ["...", "right?", etc.]
  }}
}}
"""


def generate_voice_profile(
    user_id: str,
    creator_name: str,
    transcripts: list[dict[str, str]],
) -> tuple[dict[str, Any], float, list[str]]:
    """Generate a voice profile from creator transcripts.

    Args:
        user_id: User who owns this profile.
        creator_name: Name of the creator being analyzed.
        transcripts: List of dicts with 'url' and 'text' keys.

    Returns:
        Tuple of (voice_profile_data dict, cost, warnings).

    Raises:
        ValueError: If analysis fails.
    """
    logger.info(f"Generating voice profile for {creator_name} from {len(transcripts)} transcripts")
    warnings: list[str] = []

    # Format transcripts for prompt
    formatted = []
    for i, t in enumerate(transcripts[:5], 1):
        url = t.get("url", "unknown")
        text = t.get("text", "")[:5000]  # Cap each transcript
        formatted.append(f"### Transcript {i} ({url})\n{text}")

    transcripts_str = "\n\n".join(formatted)

    prompt = VOICE_ANALYSIS_PROMPT.format(
        creator_name=creator_name,
        transcripts=transcripts_str,
    )

    client = GeminiClient()
    response = client.generate_json(
        prompt=prompt,
        system_message=VOICE_ANALYSIS_ROLE,
        temperature=VOICE_ANALYSIS_TEMPERATURE,
    )

    if response.get("error"):
        raise ValueError(f"LLM error: {response['error']}")

    raw_data = response.get("data", {})
    if not raw_data:
        raise ValueError("LLM returned empty voice analysis")

    cost = response.get("cost", 0.0)

    # Parse into structured data
    try:
        rhythm = SentenceRhythm(**raw_data.get("sentence_rhythm", {"avg_sentence_length": 12}))
    except Exception as e:
        logger.warning(f"Failed to parse sentence_rhythm: {e}")
        rhythm = SentenceRhythm(avg_sentence_length=12)
        warnings.append(f"Sentence rhythm parse error: {e}")

    transitions = []
    for tp_data in raw_data.get("transition_patterns", []):
        try:
            transitions.append(TransitionPattern(**tp_data))
        except Exception as e:
            logger.warning(f"Failed to parse transition_pattern: {e}")
            warnings.append(f"Transition pattern parse error: {e}")

    try:
        emphasis = EmphasisPatterns(**raw_data.get("emphasis_patterns", {}))
    except Exception as e:
        emphasis = EmphasisPatterns()
        warnings.append(f"Emphasis patterns parse error: {e}")

    profile_data = {
        "user_id": user_id,
        "creator_name": creator_name,
        "style_profile": {},
        "sentence_rhythm": rhythm.model_dump(),
        "transition_patterns": [tp.model_dump() for tp in transitions],
        "opening_patterns": raw_data.get("opening_patterns", []),
        "closing_patterns": raw_data.get("closing_patterns", []),
        "emphasis_patterns": emphasis.model_dump(),
        "source_video_urls": [t.get("url", "") for t in transcripts],
        "source_video_count": len(transcripts),
    }

    logger.info(
        f"Voice profile generated for {creator_name}: "
        f"{len(transitions)} transition patterns, "
        f"rhythm={rhythm.length_variation}"
    )

    return profile_data, cost, warnings
