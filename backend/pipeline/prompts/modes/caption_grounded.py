"""Caption Grounded Mode - YouTube captions available.

Analysis Mode: caption_grounded
Confidence Ceiling: MEDIUM
Quotes: Yes (approximate)

Used when: YouTube video with auto-generated or user-uploaded captions
"""

from .base import build_base_prompt


MODE_INSTRUCTIONS = """
## MODE: caption_grounded

You are analyzing video with YouTube CAPTIONS (auto-generated or user-uploaded).

### Important Limitations
- Captions may have transcription errors
- Timestamps are approximate (±5 seconds)
- Speaker attribution may be unreliable
- Auto-captions especially prone to errors

### Capabilities
- Extract quotes from captions (marked as approximate)
- Use caption timestamps (with variance acknowledged)
- Maximum confidence: MEDIUM

### Quote Extraction Rules
- Quotes are APPROXIMATE, not guaranteed verbatim
- All quotes MUST include `approximate: true`
- Include timestamp with note about ±5s variance
- Obvious transcription errors may be noted but not corrected

### Output Requirements
Include "quotes" array with this structure:
```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "Text from captions (may have minor errors)",
    "speaker": "Name or Unknown",
    "timestamp": "~MM:SS (±5s)",
    "context": "Brief context",
    "approximate": true,
    "caption_source": "auto-generated | user-uploaded | unknown"
  }
]
```
"""


QUOTE_SCHEMA = """
### Quote Schema (caption_grounded mode)

```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "string - text from captions",
    "speaker": "string - speaker name or 'Unknown'",
    "timestamp": "string - ~MM:SS (±5s)",
    "context": "string - what was being discussed",
    "approximate": true,
    "caption_source": "string - auto-generated | user-uploaded | unknown"
  }
]
```

NOTE: All quotes are marked approximate due to caption reliability limitations.
Timestamp variance of ±5 seconds is expected.
"""


def build_caption_grounded_prompt(
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Build prompt for caption_grounded mode.

    Args:
        source_id: Stable source identifier
        source_content: Caption text
        title: Video title

    Returns:
        Complete prompt with all 5 components
    """
    return build_base_prompt(
        source_id=source_id,
        source_content=source_content,
        title=title,
        analysis_mode="caption_grounded",
        confidence_ceiling="MEDIUM",
        mode_specific_instructions=MODE_INSTRUCTIONS,
        quote_schema_extension=QUOTE_SCHEMA,
    )
