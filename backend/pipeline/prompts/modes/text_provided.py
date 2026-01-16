"""Text Provided Mode - User-pasted content.

Analysis Mode: text_provided
Confidence Ceiling: MEDIUM
Quotes: Yes (with unverified warning)

Used when: User pastes text content (paywalled article, email, document)

Owner Decision (2026-01-15): Quotes ARE allowed for text_provided mode,
but must be marked as unverified since system cannot confirm authenticity.
"""

from .base import build_base_prompt


MODE_INSTRUCTIONS = """
## MODE: text_provided

You are analyzing USER-PROVIDED TEXT content.

### Source Characteristics
- Content was pasted by user (e.g., paywalled article, email, document)
- Source authenticity CANNOT be verified by system
- Content may be complete, excerpted, or modified

### Capabilities
- Extract quotes from provided text
- Maximum confidence: MEDIUM (never HIGH)
- Focus on semantic content extraction

### Quote Handling (per Owner Decision 2026-01-15)
- Quotes ARE allowed but carry verification warnings
- All quotes MUST include `_accuracy_unverified: true`
- Include warning: "User-provided source; accuracy unconfirmed"
- System cannot confirm quotes match any original source
- User should verify quote accuracy

### Output Requirements
Include "quotes" array with this structure:
```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "Verbatim text from user-provided content",
    "speaker": "Name or Unknown",
    "context": "Brief context",
    "_accuracy_unverified": true,
    "_verification_warning": "User-provided source; accuracy unconfirmed"
  }
]
```

MUST include "analysis_limitations":
```json
"analysis_limitations": [
  "Source is user-provided text — cannot verify authenticity",
  "Content may be incomplete or modified",
  "Quote accuracy cannot be confirmed by system"
]
```
"""


QUOTE_SCHEMA = """
### Quote Schema (text_provided mode)

```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "string - verbatim text from user-provided content",
    "speaker": "string - speaker name or 'Unknown'",
    "context": "string - what was being discussed",
    "_accuracy_unverified": true,
    "_verification_warning": "User-provided source; accuracy unconfirmed"
  }
],

"analysis_limitations": [
  "Source is user-provided text — cannot verify authenticity",
  "Content may be incomplete or modified",
  "Quote accuracy cannot be confirmed by system"
]
```

NOTE: Quotes are allowed but marked as unverified.
User should confirm quote accuracy against original source.
"""


def build_text_provided_prompt(
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Build prompt for text_provided mode.

    Args:
        source_id: Stable source identifier
        source_content: User-provided text
        title: Document title or description

    Returns:
        Complete prompt with all 5 components
    """
    return build_base_prompt(
        source_id=source_id,
        source_content=source_content,
        title=title,
        analysis_mode="text_provided",
        confidence_ceiling="MEDIUM",
        mode_specific_instructions=MODE_INSTRUCTIONS,
        quote_schema_extension=QUOTE_SCHEMA,
    )
