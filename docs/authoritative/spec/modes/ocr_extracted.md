# Analysis Mode: ocr_extracted

**Status:** AUTHORITATIVE
**Version:** 1.1
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Mode Definition

`ocr_extracted` applies when the user **uploads screenshots** and text is extracted via OCR/Vision. This mode has unique challenges: OCR errors, missing context, and inability to verify the original source.

### 1.1 When This Mode Applies

| Source Type | Input Method | Mode Assignment |
|-------------|--------------|-----------------|
| Screenshot | User uploads image | `ocr_extracted` |
| Reddit screenshot | Image of Reddit UI | `ocr_extracted` |
| Twitter/X screenshot | Image of tweet/thread | `ocr_extracted` |
| Forum screenshot | Image of forum post | `ocr_extracted` |
| Chat screenshot | Image of messages | `ocr_extracted` |

### 1.2 Mode Characteristics

| Property | Value |
|----------|-------|
| Confidence Ceiling | **MEDIUM** |
| Quotes Allowed | **YES — with warnings** |
| Observations Allowed | **YES** — OCR-derived |
| Timestamp Grounding | **N/A** |
| Semantic Precision | **MEDIUM** |
| Provenance | **OCR_EXTRACTED** — vision model processed |

---

## 2. Confidence Rules

### 2.1 Ceiling Enforcement

```
MAXIMUM ALLOWED CONFIDENCE: MEDIUM

Extraction may assign:
- medium: Clear text visible in screenshot
- low: Partially visible, OCR uncertain, or context-dependent

NEVER USE: high
```

### 2.2 Rationale for MEDIUM Ceiling

OCR-extracted content:
- May contain recognition errors
- Lacks surrounding context (what came before/after)
- Cannot be verified against original
- User curated what to screenshot (selection bias)

However, MEDIUM (not LOW) because:
- Actual text is being read, not inferred
- Visual evidence exists
- Better than pure video analysis

### 2.3 Auto-Downgrade Rule

```python
if confidence == "high":
    confidence = "medium"
    warnings.append("Confidence auto-downgraded: ocr_extracted ceiling is MEDIUM")
```

---

## 3. Quote Handling

### 3.1 Rule

**QUOTES ARE ALLOWED IN ocr_extracted MODE — WITH WARNINGS.**

### 3.2 Rationale

OCR extraction may introduce errors:
- Character misrecognition ("I" vs "l" vs "1")
- Word boundary issues
- Missing punctuation
- Formatting artifacts

However, if clear text is visible, quotes CAN be extracted
with appropriate warnings recommending user verification.

### 3.3 Warning Message

All quotes carry this warning:
```
"OCR-extracted content with N quote(s). May contain transcription errors.
User should verify accuracy."
```

### 3.4 Quote Marking

All quotes MUST be marked with:
```json
{
  "quote_id": "QT_1",
  "text": "...",
  "_accuracy_unverified": true,
  "_verification_warning": "OCR-extracted; may contain transcription errors",
  "ocr_confidence": "high | medium | low"
}
```

---

## 4. OCR Processing

### 4.1 Official Method: Gemini 2.5 Pro Direct Vision

**Model:** `gemini-2.5-pro`

The system uses Gemini 2.5 Pro for direct vision analysis:

- Send image directly to Gemini 2.5 Pro
- Model extracts and structures in one pass
- Single API call, no OCR preprocessing
- Strong UI element recognition
- Context-aware text extraction

**Configuration:**
```python
EXTRACTION_MODEL = "gemini-2.5-pro"
TEMPERATURE = 0.1  # Low for consistent extraction
```

**Rationale for Direct Vision:**
- Eliminates OCR preprocessing errors
- Understands platform-specific UI layouts
- Context-aware extraction (not just raw text)
- Handles complex formatting (threads, nested comments)
- Simpler pipeline (one step vs two)

### 4.2 Platform-Specific Guides

Each supported platform has a dedicated extraction guide with:
- UI elements to extract
- Extraction prompt templates
- Output schemas
- Edge case handling

| Platform | Guide | Key Elements |
|----------|-------|--------------|
| Reddit | [reddit.md](./platforms/reddit.md) | Subreddit, votes, nesting |
| Twitter/X | [twitter.md](./platforms/twitter.md) | Handle, verification, retweets |
| Instagram | [instagram.md](./platforms/instagram.md) | Stories, hashtags, engagement |
| Facebook | [facebook.md](./platforms/facebook.md) | Privacy, reactions, groups |
| TikTok | [tiktok.md](./platforms/tiktok.md) | Sounds, duets, stitches |
| YouTube Comments | [youtube-comments.md](./platforms/youtube-comments.md) | Creator heart, pinned, membership |
| Generic Forum | [generic-forum.md](./platforms/generic-forum.md) | User rank, quotes, signatures |

See: [Platform Guides Index](./platforms/INDEX.md)

### 4.3 Platform Detection Logic

```
Screenshot provided → Gemini 2.5 Pro identifies platform

1. Check for platform-specific UI elements:
   ├── Reddit UI (r/, u/, upvotes) → Use reddit.md prompts
   ├── Twitter/X UI (@handles, retweets) → Use twitter.md prompts
   ├── Instagram UI (stories, reels) → Use instagram.md prompts
   ├── Facebook UI (reactions, share) → Use facebook.md prompts
   ├── TikTok UI (FYP, sounds) → Use tiktok.md prompts
   ├── YouTube comments → Use youtube-comments.md prompts
   └── Other forum/discussion → Use generic-forum.md prompts

2. If platform unclear:
   └── Use generic-forum.md patterns
```

### 4.4 Extraction Prompt Structure

```
System: Analyze this screenshot from [PLATFORM].
Extract structured information according to the platform guide.

PLATFORM: [platform_name]
EXTRACTION MODE: ocr_extracted

[Platform-specific extraction instructions from guide]

Return as structured JSON.
```

---

## 5. Input Requirements

### 5.1 Required Fields

```python
@dataclass
class ScreenshotSourceInput:
    """User-provided screenshot."""

    image: bytes                          # The screenshot image (REQUIRED)
    platform_hint: Optional[str] = None   # "reddit", "twitter", "forum", "other"
    title: Optional[str] = None           # User-provided title
    source_url: Optional[str] = None      # URL of page (NOT VERIFIED)
    context_note: Optional[str] = None    # User's context about what this shows
```

### 5.2 Size and Format Limits

| Limit | Value | Enforcement |
|-------|-------|-------------|
| Maximum file size | 10 MB | Hard reject |
| Maximum dimensions | 4000 x 4000 px | Hard reject |
| Minimum dimensions | 100 x 100 px | Soft warning |
| Supported formats | PNG, JPG, WEBP | Hard reject others |

### 5.3 Image Quality Checks

```python
def validate_screenshot(image: bytes) -> ValidationResult:
    errors = []
    warnings = []

    # Check file size
    if len(image) > 10_000_000:  # 10MB
        errors.append("Image exceeds 10MB limit")

    # Load and check dimensions
    img = Image.open(io.BytesIO(image))
    width, height = img.size

    if width > 4000 or height > 4000:
        errors.append("Image exceeds 4000x4000 pixel limit")

    if width < 100 or height < 100:
        warnings.append("Image is very small; OCR quality may be limited")

    # Check format
    if img.format not in ["PNG", "JPEG", "WEBP"]:
        errors.append(f"Unsupported format: {img.format}")

    return ValidationResult(errors=errors, warnings=warnings)
```

---

## 6. Observations Format

### 6.1 What to Extract

Extract **observations about the screenshot content**:
- What text is visible
- Who appears to be the author/speaker
- What platform indicators are visible
- What context is apparent

### 6.2 Observation Format

```json
{
  "observation_id": "OBS_1",
  "description": "A Reddit post by user 'throwaway_acct' discusses company layoffs",
  "platform": "reddit",
  "visible_elements": ["username", "subreddit_name", "post_content", "timestamp"],
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "medium",
  "input_mode": "screenshot"
}
```

### 6.3 Observation Language Guidelines

**Use phrases like:**
- "The screenshot shows..."
- "Visible text indicates..."
- "The OCR-extracted content states..."
- "Based on the image, the user appears to write..."

**Include OCR disclaimer:**
- "Content extracted via OCR; accuracy not guaranteed"

---

## 7. Missing Context Warning

### 7.1 The Problem

Screenshots often capture mid-conversation content:
- Previous comments provided context
- Thread structure is lost
- Replies may reference invisible content

### 7.2 Detection

LLM should flag when content seems incomplete:
- References to "above" or "previous" content
- Reply indicators without visible parent
- Partial sentences or cut-off text

### 7.3 Handling

```python
if detected_missing_context:
    warnings.append({
        "code": "missing_context",
        "message": "This content may lack surrounding context",
        "suggestion": "User can provide context_note to clarify"
    })
```

---

## 8. Validation Requirements

### 8.1 Mandatory Checks

| Check | Description | On Failure |
|-------|-------------|------------|
| V1 | Valid JSON matching schema | Hard fail, retry once |
| V2 | source_id matches input exactly | Hard fail, retry once |
| V3 | No confidence exceeds MEDIUM | Auto-downgrade, warn |
| V5 | No quotes array in output | Hard fail, reject |
| V6 | All observations marked approximate | Auto-fix, warn |
| V7 | OCR quality assessment included | Soft warning |

### 8.2 OCR Quality Assessment

Include quality assessment in extraction metadata:

```python
class OCRQualityAssessment:
    overall_quality: str          # "good", "medium", "poor"
    issues_detected: list[str]    # ["blurry_text", "low_contrast", "partial_content"]
    confidence_score: float       # 0.0 - 1.0
```

---

## 9. Provenance Requirements

### 9.1 Required Metadata

```python
@dataclass
class OCRExtractedProvenance:
    source_id: str                    # SRC_X format
    source_type: str = "screenshot"
    input_mode: str = "screenshot"
    analysis_mode: str = "ocr_extracted"

    # OCR details
    ocr_method: str = "direct_vision" # Always direct vision
    ocr_model: str = "gemini-2.5-pro" # Official model
    ocr_quality: str                  # "good" | "medium" | "poor"

    # Platform
    platform_hint: Optional[str]      # User-provided
    detected_platform: Optional[str]  # System-detected

    # Verification status
    provenance: str = "ocr_extracted"
    system_verified: bool = False     # ALWAYS FALSE

    # Confidence
    confidence_ceiling: str = "medium"
    confidence_note: str = "Extracted from screenshot via vision model"

    # User-provided metadata
    title: Optional[str]
    url: Optional[str]                # NOT VERIFIED
    context_note: Optional[str]
```

### 9.2 Provenance Display (Prominent Warning)

```
Source: SRC_3
Mode: ocr_extracted (MEDIUM confidence)
Type: Screenshot (platform: reddit)

WARNING: Content extracted from screenshot via OCR/Vision.
- Text may contain OCR errors
- Surrounding context is not available
- Original source cannot be verified
- Quotes are not available (OCR accuracy not guaranteed)
- Screenshot may capture mid-conversation content

OCR Quality: medium
Issues: [partial_content, small_text]

User-provided context: "This is from a thread about company layoffs"
```

---

## 10. Output Schema

```json
{
  "source_id": "SRC_3",
  "analysis_mode": "ocr_extracted",
  "extraction_metadata": {
    "extracted_at": "2026-01-14T10:30:00Z",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "medium",
    "provenance": "ocr_extracted",
    "system_verified": false,
    "ocr_quality": {
      "overall": "medium",
      "issues": ["partial_content"],
      "confidence_score": 0.75
    }
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
      "description": "semantic description of visible content",
      "platform": "reddit",
      "visible_elements": ["username", "post_content"],
      "type": "observation",
      "approximate": true,
      "ocr_confidence": "medium"
    }
  ],
  "themes": [...],
  "tensions": [...],
  "entities": [...],
  "gaps": [...],
  "context_warnings": [
    {
      "type": "missing_context",
      "message": "Screenshot may capture mid-conversation content"
    }
  ]
}
```

**Critical:** No `quotes` array. Uses `approximate_observations` instead.

---

## 11. Edge Cases

### 11.1 Screenshot Contains Multiple Posts/Comments

**Scenario:** User screenshots a thread with multiple visible comments.

**Handling:**
- Extract ALL visible content as separate observations
- Do NOT attempt to reconstruct threading
- Each visible post = separate observation
- Note: "Multiple posts visible in single screenshot"

### 11.2 Text Is Partially Cut Off

**Scenario:** Screenshot cuts off mid-sentence or mid-word.

**Handling:**
- Extract what is visible
- Note truncation in observation: "Text appears truncated"
- Add context warning: "Partial content visible"
- Confidence may be reduced to LOW for truncated content

### 11.3 Screenshot Is Of Code or Technical Content

**Scenario:** Screenshot shows code, terminal output, or technical diagrams.

**Handling:**
- Extract as-is, note content type
- OCR of code has higher error rates
- Add warning: "Technical content may have OCR errors"
- Consider if content is relevant to research topic

### 11.4 Platform Cannot Be Identified

**Scenario:** No platform_hint provided and UI is unrecognizable.

**Handling:**
- Set detected_platform to "unknown"
- Extract general text content
- Note: "Platform could not be identified"
- Proceed with generic extraction

### 11.5 Image Contains No Readable Text

**Scenario:** Screenshot is of visual content (memes, images) with minimal text.

**Handling:**
- Extract visual observations instead
- Note: "Minimal text content detected"
- Lower confidence to LOW
- Consider if source is useful for research

---

## 12. Prompt Template Reference

Use `Gemini_Semantic_Extraction.md` with:
- Model: `gemini-2.5-pro` (direct vision)
- Temperature: 0.1 (consistent extraction)
- Observation Instructions template
- Schema WITHOUT quotes
- Confidence ceiling: MEDIUM
- Additional context: "This is OCR-extracted from a screenshot"
- Include platform_hint if provided
- Platform-specific prompts from `./platforms/` guides

---

## 13. Invariants (Always True)

1. **Confidence never exceeds MEDIUM** — auto-downgrade if violated
2. **No quotes array** — OCR accuracy insufficient for verbatim quotes
3. **system_verified is FALSE** — screenshot content cannot be verified
4. **OCR quality assessment included** — always document extraction quality
5. **Missing context warning possible** — flag incomplete content
6. **Platform hint recorded** — helps with structured extraction

---

## 14. Comparison to Similar Modes

| Aspect | ocr_extracted | text_provided |
|--------|---------------|---------------|
| Input type | Image | Text |
| Text source | OCR extraction | User paste |
| Processing needed | Vision/OCR | None |
| Error sources | OCR + user curation | User editing |
| Platform detection | Automatic | N/A |

---

## 15. Cross-References

### Platform Guides

| Platform | Guide Location |
|----------|----------------|
| Reddit | `./platforms/reddit.md` |
| Twitter/X | `./platforms/twitter.md` |
| Instagram | `./platforms/instagram.md` |
| Facebook | `./platforms/facebook.md` |
| TikTok | `./platforms/tiktok.md` |
| YouTube Comments | `./platforms/youtube-comments.md` |
| Generic Forum | `./platforms/generic-forum.md` |
| **Index** | `./platforms/INDEX.md` |

### Related Specifications

- **Mode Index:** `./INDEX.md`
- **Validation Rules:** `../Validation_and_Retry_Rules.md`
- **Main Spec:** `../RASS.md`
- **Prompt Pack:** `../../prompts/Gemini_Semantic_Extraction.md`

---

**END OF MODE SPECIFICATION**
