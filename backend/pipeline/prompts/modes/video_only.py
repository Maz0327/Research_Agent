"""Video Only Mode - No transcript available.

Analysis Mode: video_only
Confidence Ceiling: LOW
Quotes: NO - use approximate_observations instead

Used when: YouTube video without any transcript or captions
"""

from .base import build_base_prompt


MODE_INSTRUCTIONS = """
## MODE: video_only

You are analyzing video WITHOUT any transcript or captions.

### CRITICAL CONSTRAINTS
- NO QUOTES ALLOWED
- Maximum confidence: LOW (always, no exceptions)
- Use "approximate_observations" instead of quotes
- All observations are approximate and unverified

### What You CAN Do
- Identify themes from visual/audio cues
- Describe observed behavior (not quoted speech)
- Identify entities and topics
- Note approximate time ranges for observations

### What You MUST NOT Do
- Generate verbatim or approximate "quotes"
- Claim verbatim accuracy for any text
- Use "high" or "medium" confidence for anything
- Present observations as verified facts

### Terminology
Use "approximate_observations" consistently.
These are NOT quotes. They are semantic descriptions of what appears
to have been communicated, without claiming verbatim accuracy.

### Output Requirements
Include "approximate_observations" array (NOT "quotes"):
```json
"approximate_observations": [
  {
    "observation_id": "OBS_1",
    "observation": "Description of what was communicated",
    "approximate": true,
    "type": "observation",
    "timestamp_range": "~MM:SS - MM:SS",
    "confidence": "low"
  }
]
```

MUST include "analysis_limitations":
```json
"analysis_limitations": [
  "No transcript available — all observations are approximate",
  "Timestamps are estimates from visual cues",
  "No quote verification possible"
]
```
"""


OBSERVATION_SCHEMA = """
### Observation Schema (video_only mode)

```json
"approximate_observations": [
  {
    "observation_id": "OBS_1",
    "observation": "string - semantic description of what was communicated",
    "approximate": true,
    "type": "observation",
    "timestamp_range": "string - ~MM:SS - MM:SS",
    "confidence": "low"
  }
],

"analysis_limitations": [
  "No transcript available — all observations are approximate",
  "Timestamps are estimates from visual cues",
  "No quote verification possible"
]
```

CRITICAL: Do NOT include a "quotes" array. Use "approximate_observations" only.
All confidence values MUST be "low".
"""


def build_video_only_prompt(
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Build prompt for video_only mode.

    Args:
        source_id: Stable source identifier
        source_content: Video description or frame descriptions
        title: Video title

    Returns:
        Complete prompt with all 5 components
    """
    return build_base_prompt(
        source_id=source_id,
        source_content=source_content,
        title=title,
        analysis_mode="video_only",
        confidence_ceiling="LOW",
        mode_specific_instructions=MODE_INSTRUCTIONS,
        quote_schema_extension=OBSERVATION_SCHEMA,
    )
