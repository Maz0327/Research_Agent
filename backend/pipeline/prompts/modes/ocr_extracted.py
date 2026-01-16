"""OCR Extracted Mode - Text from screenshot via OCR.

Analysis Mode: ocr_extracted
Confidence Ceiling: MEDIUM
Quotes: Yes (with OCR warning)

Used when: Text extracted from screenshot via Optical Character Recognition

Owner Decision (2026-01-15): Quotes ARE allowed for ocr_extracted mode,
but must be marked as potentially containing OCR errors.
"""

from .base import build_base_prompt


MODE_INSTRUCTIONS = """
## MODE: ocr_extracted

You are analyzing text extracted from a SCREENSHOT via OCR.

### Source Characteristics
- Content was extracted via Optical Character Recognition (OCR)
- OCR may introduce errors, missing characters, or formatting issues
- Visual context from original image may be lost

### Common OCR Errors to Expect
- Missing spaces: "thedetective" should be "the detective"
- Misread characters: "rn" vs "m", "l" vs "I", "0" vs "O"
- Truncated text: content may be cut off at edges
- Line break issues: sentences split incorrectly
- Special character problems: quotes, dashes, bullets

### Capabilities
- Extract quotes from OCR text (with accuracy warnings)
- Maximum confidence: MEDIUM (never HIGH)
- Note any text that appears garbled or uncertain

### Quote Handling (per Owner Decision 2026-01-15)
- Quotes ARE allowed but carry accuracy warnings
- All quotes MUST include `_accuracy_unverified: true`
- Include warning: "OCR-extracted; may contain transcription errors"
- OCR may have introduced character-level errors
- User should verify quote accuracy against original

### Output Requirements
Include "quotes" array with this structure:
```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "Text from OCR extraction",
    "speaker": "Name or Unknown",
    "context": "Brief context",
    "_accuracy_unverified": true,
    "_verification_warning": "OCR-extracted; may contain transcription errors",
    "ocr_confidence": "high | medium | low"
  }
]
```

MUST include "analysis_limitations":
```json
"analysis_limitations": [
  "Content extracted via OCR — text may contain transcription errors",
  "Quote accuracy cannot be guaranteed",
  "Visual context from original image may be lost"
]
```

If you notice likely OCR errors, note them:
```json
"ocr_issues_detected": [
  "Possible character confusion at 'rnatter' (likely 'matter')",
  "Missing spaces in several words"
]
```
"""


QUOTE_SCHEMA = """
### Quote Schema (ocr_extracted mode)

```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "string - text from OCR extraction",
    "speaker": "string - speaker name or 'Unknown'",
    "context": "string - what was being discussed",
    "_accuracy_unverified": true,
    "_verification_warning": "OCR-extracted; may contain transcription errors",
    "ocr_confidence": "string - high | medium | low"
  }
],

"analysis_limitations": [
  "Content extracted via OCR — text may contain transcription errors",
  "Quote accuracy cannot be guaranteed",
  "Visual context from original image may be lost"
],

"ocr_issues_detected": [
  "string - description of detected OCR error or uncertainty"
]
```

NOTE: Quotes are allowed but marked with OCR warning.
Character-level errors (rn→m, l→I, 0→O) are common.
"""


def build_ocr_extracted_prompt(
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Build prompt for ocr_extracted mode.

    Args:
        source_id: Stable source identifier
        source_content: OCR-extracted text
        title: Screenshot description

    Returns:
        Complete prompt with all 5 components
    """
    return build_base_prompt(
        source_id=source_id,
        source_content=source_content,
        title=title,
        analysis_mode="ocr_extracted",
        confidence_ceiling="MEDIUM",
        mode_specific_instructions=MODE_INSTRUCTIONS,
        quote_schema_extension=QUOTE_SCHEMA,
    )
