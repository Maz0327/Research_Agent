"""Transcript Grounded Mode - Full transcript available.

Analysis Mode: transcript_grounded
Confidence Ceiling: HIGH
Quotes: Yes (verbatim)

Used when: YouTube video with Supadata or Whisper transcript
"""

from .base import build_base_prompt


MODE_INSTRUCTIONS = """
## MODE: transcript_grounded

You have access to a VERIFIED TRANSCRIPT with accurate timestamps.

### Capabilities
- Extract VERBATIM quotes
- Use exact timestamps from transcript
- Maximum confidence: HIGH

### Quote Extraction Rules
- Quotes MUST be word-for-word from transcript
- Include speaker attribution when identifiable
- Include timestamp (format: MM:SS or HH:MM:SS)
- Quotes support claims which support key points

### Verification
- All quotes will be verified against transcript
- Mismatched quotes will be flagged
- Fabricated quotes will cause validation failure

### Output Requirements
Include "quotes" array with this structure:
```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "Exact verbatim text from transcript",
    "speaker": "Name or Unknown",
    "timestamp": "MM:SS",
    "context": "Brief context"
  }
]
```
"""


QUOTE_SCHEMA = """
### Quote Schema (transcript_grounded mode)

```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "string - EXACT verbatim text",
    "speaker": "string - speaker name or 'Unknown'",
    "timestamp": "string - MM:SS or HH:MM:SS",
    "context": "string - what was being discussed"
  }
]
```

CRITICAL: Quotes MUST be verbatim. Do NOT paraphrase or summarize.
"""


def build_transcript_grounded_prompt(
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Build prompt for transcript_grounded mode.

    Args:
        source_id: Stable source identifier
        source_content: Full transcript text
        title: Video title

    Returns:
        Complete prompt with all 5 components
    """
    return build_base_prompt(
        source_id=source_id,
        source_content=source_content,
        title=title,
        analysis_mode="transcript_grounded",
        confidence_ceiling="HIGH",
        mode_specific_instructions=MODE_INSTRUCTIONS,
        quote_schema_extension=QUOTE_SCHEMA,
    )
