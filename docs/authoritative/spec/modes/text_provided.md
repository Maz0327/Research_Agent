# Analysis Mode: text_provided

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14

---

## 1. Mode Definition

`text_provided` applies when the user **pastes text content directly** into the system. The system has no ability to verify the authenticity, accuracy, or provenance of this content.

### 1.1 When This Mode Applies

| Source Type | Input Method | Mode Assignment |
|-------------|--------------|-----------------|
| User text | Copy-paste into text field | `text_provided` |
| Paywalled article | User pastes accessible content | `text_provided` |
| Email/document | User pastes text | `text_provided` |
| Forum post | User pastes content | `text_provided` |

### 1.2 Mode Characteristics

| Property | Value |
|----------|-------|
| Confidence Ceiling | **MEDIUM** |
| Quotes Allowed | **YES — with warnings** |
| Observations Allowed | **YES** — marked unverified |
| Timestamp Grounding | **N/A** — text has no timestamps |
| Semantic Precision | **MEDIUM** |
| Provenance | **USER_PROVIDED** — not system-verified |

---

## 2. Confidence Rules

### 2.1 Ceiling Enforcement

```
MAXIMUM ALLOWED CONFIDENCE: MEDIUM

Extraction may assign:
- medium: Clear statements in the provided text
- low: Inferred or ambiguous statements

NEVER USE: high
```

### 2.2 Rationale for MEDIUM Ceiling

User-provided text:
- Cannot be independently verified by the system
- May be edited, truncated, or taken out of context
- May be from unreliable sources
- Chain of custody is unknown

However, MEDIUM (not LOW) because:
- Text IS available for analysis
- Content is explicit, not inferred from video
- User has explicitly provided this as source material

### 2.3 Auto-Downgrade Rule

```python
if confidence == "high":
    confidence = "medium"
    warnings.append("Confidence auto-downgraded: text_provided ceiling is MEDIUM")
```

---

## 3. Quote Handling

### 3.1 Rule

**QUOTES ARE ALLOWED IN text_provided MODE — WITH WARNINGS.**

### 3.2 Rationale

The system cannot verify:
- That the text is verbatim from an original source
- That the text hasn't been modified by the user
- That the text is complete and not selectively edited
- The original source's identity

However, if the user has the text content, quotes CAN be extracted
with appropriate warnings recommending user verification.

### 3.3 Warning Levels

**With Source Metadata (URL, author, title provided):**
```
"User-provided source with N quote(s). Accuracy unconfirmed by system.
User should verify quotes match original."
```

**Without Source Metadata:**
```
"Source not identified. N quote(s) extracted from user-pasted text.
Cannot verify authenticity. User should confirm source and quote accuracy."
```

### 3.4 Quote Marking

All quotes MUST be marked with:
```json
{
  "quote_id": "QT_1",
  "text": "...",
  "_accuracy_unverified": true,
  "_verification_warning": "User-provided source; accuracy unconfirmed"
}
```

---

## 4. Observations Format

### 4.1 What to Extract

Since quotes are forbidden, extract **observations about the text content**:
- What topics are discussed
- What claims are made
- What entities are mentioned
- What arguments are presented

### 4.2 Observation Format

```json
{
  "observation_id": "OBS_1",
  "description": "The text discusses financial irregularities in Q3 reporting",
  "location": "paragraph 3",
  "type": "observation",
  "approximate": true,
  "input_mode": "text_provided"
}
```

### 4.3 Observation Language Guidelines

**Use phrases like:**
- "The text states that..."
- "According to the provided content..."
- "The author claims..."
- "The document indicates..."

**Include disclaimer:**
- "Content is user-provided and not system-verified"

---

## 5. Input Requirements

### 5.1 Required Fields

```python
@dataclass
class TextSourceInput:
    """User-provided text content."""

    content: str                          # The pasted text (REQUIRED)
    title: str                            # User-provided title (REQUIRED)
    creator: Optional[str] = None         # Who wrote/said this
    source_url: Optional[str] = None      # Where it came from (NOT VERIFIED)
    date: Optional[str] = None            # When published
    source_description: Optional[str] = None  # User's context note
```

### 5.2 Size Limits

| Limit | Value | Enforcement |
|-------|-------|-------------|
| Maximum characters | 50,000 | Hard reject |
| Maximum words | ~10,000 | Soft warning at 8,000 |
| Minimum characters | 100 | Soft warning |

### 5.3 Validation on Input

```python
def validate_text_input(input: TextSourceInput) -> ValidationResult:
    errors = []
    warnings = []

    if len(input.content) > 50_000:
        errors.append("Text exceeds 50,000 character limit")

    if len(input.content) < 100:
        warnings.append("Text is very short; extraction may be limited")

    if not input.title or len(input.title) < 3:
        errors.append("Title is required (minimum 3 characters)")

    return ValidationResult(errors=errors, warnings=warnings)
```

---

## 6. Validation Requirements

### 6.1 Mandatory Checks

| Check | Description | On Failure |
|-------|-------------|------------|
| V1 | Valid JSON matching schema | Hard fail, retry once |
| V2 | source_id matches input exactly | Hard fail, retry once |
| V3 | No confidence exceeds MEDIUM | Auto-downgrade, warn |
| V5 | No quotes array in output | Hard fail, reject |
| V6 | All observations marked approximate | Auto-fix, warn |

### 6.2 Provenance Disclaimer Check

Output MUST include provenance disclaimer in metadata:

```python
def validate_provenance_disclosure(output: dict) -> bool:
    provenance = output.get("extraction_metadata", {}).get("provenance", "")
    return "user_provided" in provenance
```

---

## 7. Provenance Requirements

### 7.1 Required Metadata

```python
@dataclass
class TextProvidedProvenance:
    source_id: str                    # SRC_X format
    source_type: str = "user_text"
    input_mode: str = "text"
    analysis_mode: str = "text_provided"

    # Verification status
    provenance: str = "user_provided"
    system_verified: bool = False     # ALWAYS FALSE

    # Confidence
    confidence_ceiling: str = "medium"
    confidence_note: str = "Content provided by user, not system-verified"

    # User-provided metadata (NOT VERIFIED)
    title: str                        # User-provided
    creator: Optional[str]            # User-provided
    url: Optional[str]                # User-provided, NOT VERIFIED
    date: Optional[str]               # User-provided
    source_description: Optional[str] # User's context
```

### 7.2 Provenance Display (Prominent Warning)

```
Source: SRC_2
Mode: text_provided (MEDIUM confidence)
Type: User-provided text

WARNING: This content was provided by the user and is NOT system-verified.
- The system cannot confirm authenticity or accuracy
- The original source URL (if provided) was not fetched or verified
- Content may be edited, truncated, or taken out of context
- Quotes are not available (content not verified)
- User is responsible for chain of custody

User-provided metadata:
- Title: [user-provided title]
- Source: [user-provided URL, NOT VERIFIED]
- Creator: [user-provided, NOT VERIFIED]
```

---

## 8. Output Schema

```json
{
  "source_id": "SRC_2",
  "analysis_mode": "text_provided",
  "extraction_metadata": {
    "extracted_at": "2026-01-14T10:30:00Z",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "medium",
    "provenance": "user_provided",
    "system_verified": false
  },
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string",
      "confidence": "medium",
      "supporting_observation_ids": ["OBS_1"]
    }
  ],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "string",
      "confidence": "medium"
    }
  ],
  "approximate_observations": [
    {
      "observation_id": "OBS_1",
      "description": "semantic description of text content",
      "location": "paragraph/section reference",
      "type": "observation",
      "approximate": true,
      "input_mode": "text_provided"
    }
  ],
  "themes": [...],
  "tensions": [...],
  "entities": [...],
  "gaps": [...]
}
```

**Critical:** No `quotes` array. Uses `approximate_observations` instead.

---

## 9. Edge Cases

### 9.1 User Provides URL But Pastes Text

**Scenario:** User provides a source URL but also pastes the text content.

**Handling:**
- Mode is `text_provided` (text was pasted, not fetched)
- URL is stored but marked "NOT VERIFIED"
- System does NOT attempt to fetch the URL
- Add note: "URL provided but content was user-supplied"

### 9.2 Text Appears to Be Copy-Pasted From Chat/Email

**Scenario:** Text has formatting suggesting chat messages or email thread.

**Handling:**
- Extract as-is, note format in observations
- Do not attempt to parse structure
- Note: "Content appears to be from messaging/email format"
- Confidence remains MEDIUM

### 9.3 Text Contains Embedded Quotes

**Scenario:** User-provided text contains quotation marks around passages.

**Handling:**
- These are NOT quotes for our system
- The system cannot verify the quoted text is verbatim
- Extract as observations: "The text contains attributed statements..."
- Do NOT extract as quotes array

### 9.4 Text Is Too Short for Meaningful Extraction

**Scenario:** User provides only 1-2 sentences.

**Handling:**
- Proceed with extraction
- Return thin results with warning
- Note: "Limited content may result in sparse extraction"
- Empty arrays are acceptable

---

## 10. Prompt Template Reference

Use `Gemini_Semantic_Extraction.md` with:
- Observation Instructions template
- Schema WITHOUT quotes
- Confidence ceiling: MEDIUM
- Additional context: "This is user-provided text, not system-fetched"

---

## 11. Invariants (Always True)

1. **Confidence never exceeds MEDIUM** — auto-downgrade if violated
2. **No quotes array** — forbidden even though text exists
3. **system_verified is FALSE** — user-provided content is never verified
4. **Provenance marked user_provided** — always
5. **Prominent disclaimer in output** — user must see verification warning
6. **URL is stored but NOT VERIFIED** — even if provided

---

## 12. Comparison to Similar Modes

| Aspect | text_provided | article_fetched |
|--------|---------------|-----------------|
| Text source | User paste | System fetch |
| Confidence ceiling | MEDIUM | HIGH |
| Quotes allowed | NO | YES |
| system_verified | FALSE | TRUE |
| URL verified | NO | YES |

---

**END OF MODE SPECIFICATION**
