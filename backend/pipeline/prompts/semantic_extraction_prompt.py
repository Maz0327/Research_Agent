"""Semantic Extraction Prompt - Primary extraction from source material.

Based on: docs/authoritative/prompts/Gemini_Semantic_Extraction.md

Gemini is treated as a semantic analyst, not a summarizer, narrator, or producer.
"""

# Role definition for system message
SEMANTIC_EXTRACTION_ROLE = """You are a semantic research analyst.

Your job is NOT to summarize, explain, persuade, or conclude.

Your job is to:
- extract meaning
- identify patterns
- surface tensions
- preserve uncertainty
- stay grounded in source material

You must remain neutral, descriptive, and cautious.
You do not write narratives.
You do not decide what is true.
You do not fill gaps with assumptions."""


# Source Identity Contract - injected before any reasoning
SOURCE_IDENTITY_CONTRACT = """## SOURCE IDENTITY CONTRACT (BEFORE REASONING)

The source_id and source metadata provided are CANONICAL.

You MUST NOT:
- Guess or infer which video/article this is
- Substitute or correct source metadata
- Assume information about the source not explicitly provided
- Reference external knowledge about this topic

If source identity seems wrong or incomplete:
- Proceed with provided data
- Note discrepancy in `analysis_limitations`
- Do NOT substitute a "likely" source"""


# Primary extraction prompt template
SEMANTIC_EXTRACTION_PROMPT = """You are analyzing source material for research purposes.

The goal is to extract SEMANTIC STRUCTURE, not summaries.

INPUT:
- Source ID: {source_id}
- Analysis Mode: {analysis_mode}
- Source Content:

{source_content}

---

{source_identity_contract}

---

TASKS:

1. Identify KEY POINTS
A Key Point is:
- a neutral, semantically meaningful assertion
- derived directly from the source
- not a summary
- not a quote
- not an opinion

2. Identify CLAIMS
A Claim is:
- a declarative statement made by the source
- asserting something about reality
- may be true, false, disputed, or unverifiable

3. Identify THEMES
A Theme is:
- a recurring conceptual pattern
- spanning multiple key points
- abstracted one level above the text

4. Identify TENSIONS or CONTRADICTIONS (if present)
A Tension exists when:
- two or more key points cannot both be true
- OR meaning shifts without explanation

RULES:
- Do NOT summarize the source
- Do NOT write conclusions
- Do NOT speculate
- Do NOT resolve ambiguity
- Do NOT invent missing information
- Use neutral language only

OUTPUT JSON ONLY, matching this schema:

{{
  "source_id": "{source_id}",
  "analysis_mode": "{analysis_mode}",
  "key_points": [
    {{
      "key_point_id": "KP_1",
      "statement": "...",
      "supporting_claims": ["CLM_1"],
      "confidence": "high | medium | low"
    }}
  ],
  "claims": [
    {{
      "claim_id": "CLM_1",
      "statement": "...",
      "supporting_quotes": ["..."]
    }}
  ],
  "themes": [
    {{
      "theme_id": "THEME_1",
      "label": "...",
      "related_key_points": ["KP_1", "KP_3"]
    }}
  ],
  "tensions": [
    {{
      "tension_id": "TEN_1",
      "description": "...",
      "involved_key_points": ["KP_2", "KP_4"]
    }}
  ]
}}

## QUALITY CONSTRAINTS

### Key Points
- Must be SPECIFIC
- Must be GROUNDED
- Must avoid abstraction creep

BAD: "The video discusses controversy."
GOOD: "The speaker gives conflicting accounts of when funding was secured."

### Themes
- Must describe PATTERNS, not topics

BAD: "Funding"
GOOD: "Inconsistent explanations regarding funding sources"

## MINIMUM REQUIREMENTS
- At least 3 key points for long-form content (30+ minutes or 3000+ words)
- At least 2 themes
- Each theme must reference at least 2 key points
"""


# Video-only mode instructions (when no transcript available)
VIDEO_ONLY_INSTRUCTIONS = """
IMPORTANT: You are analyzing video WITHOUT a transcript.

## Analysis Mode: video_only

You MUST:
- You receive NO quotes in input (quotes array is empty before you process)
- Generate `approximate_observations` — semantic descriptions of what was said
- All observations MUST include `approximate: true` and `type: observation`
- These are NOT quotes — use distinct terminology
- Confidence ceiling is LOW (categorical, not numeric)
- Include an `analysis_limitations` field in your output

You MAY:
- Identify themes from visual/audio cues
- Describe observed behavior (not quoted speech)
- Identify entities and topics

You MUST NOT:
- Generate verbatim or approximate "quotes"
- Claim verbatim accuracy for any text
- Use `high` or `medium` confidence

TERMINOLOGY RULE:
Use "approximate_observations" consistently. These are NOT quotes.

Your output JSON must include:
{{
  "source_id": "{source_id}",
  "analysis_mode": "video_only",
  "approximate_observations": [
    {{
      "observation": "...",
      "approximate": true,
      "type": "observation",
      "timestamp_range": "~MM:SS - MM:SS"
    }}
  ],
  "analysis_limitations": [
    "No transcript available — all observations are approximate",
    "Timestamps may be imprecise",
    "No quote verification possible"
  ],
  "key_points": [...],
  "claims": [...],
  "themes": [...],
  "tensions": [...]
}}
"""


# Caption-grounded mode instructions (YouTube captions used)
CAPTION_GROUNDED_INSTRUCTIONS = """
IMPORTANT: You are analyzing video WITH YouTube captions (auto-generated or user-uploaded).

## Analysis Mode: caption_grounded

You MUST:
- Acknowledge that quotes may have minor transcription errors
- Timestamps may be approximate (±5 seconds)
- Note caption source in any quote metadata

You MAY:
- Extract quotes as written in captions
- Claim `medium` confidence maximum
- Use timestamps from captions

Your output JSON should include:
{{
  "source_id": "{source_id}",
  "analysis_mode": "caption_grounded",
  "transcript_source": "youtube_captions",
  ...
}}
"""


# Retry prompt for thin output
SEMANTIC_EXTRACTION_RETRY_PROMPT = """Your previous output was too general and insufficiently specific.

Re-analyze the same source with stricter constraints.

You must:
- extract MORE specific key points
- reduce abstraction
- focus on concrete assertions and shifts in meaning

You must NOT:
- add speculation
- summarize
- invent details

Return JSON in the same schema."""


# Recovery prompt for last resort (thin output after retry)
SEMANTIC_EXTRACTION_RECOVERY_PROMPT = """Extract ONLY what is clearly present.

If meaning is sparse:
- extract fewer but precise key points
- explicitly surface uncertainty
- identify what cannot be determined

Do NOT pad output.

Return JSON in the same schema."""


def build_semantic_extraction_prompt(
    source_id: str,
    source_content: str,
    analysis_mode: str,
) -> str:
    """
    Build the complete semantic extraction prompt.

    Args:
        source_id: Stable source identifier (e.g., "SRC_1")
        source_content: Full source text or description
        analysis_mode: One of "transcript_grounded", "caption_grounded", "video_only"

    Returns:
        Complete prompt string ready for Gemini
    """
    # Base prompt
    prompt = SEMANTIC_EXTRACTION_PROMPT.format(
        source_id=source_id,
        source_content=source_content,
        analysis_mode=analysis_mode,
        source_identity_contract=SOURCE_IDENTITY_CONTRACT,
    )

    # Add mode-specific instructions
    if analysis_mode == "video_only":
        prompt += "\n\n" + VIDEO_ONLY_INSTRUCTIONS.format(source_id=source_id)
    elif analysis_mode == "caption_grounded":
        prompt += "\n\n" + CAPTION_GROUNDED_INSTRUCTIONS.format(source_id=source_id)

    return prompt
