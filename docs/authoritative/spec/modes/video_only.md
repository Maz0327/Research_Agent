# Analysis Mode: video_only

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14

---

## 1. Mode Definition

`video_only` is the **most degraded** analysis mode for video sources. It applies when NO text content is available — no transcript, no captions. Extraction relies solely on Gemini's multimodal video understanding.

### 1.1 When This Mode Applies

| Source Type | Text Available | Mode Assignment |
|-------------|----------------|-----------------|
| YouTube | None (all transcript methods failed) | `video_only` |
| Video file | No transcript provided | `video_only` |

### 1.2 Mode Characteristics

| Property | Value |
|----------|-------|
| Confidence Ceiling | **LOW** |
| Quotes Allowed | **NO** |
| Observations Allowed | **YES** — approximate only |
| Timestamp Grounding | **UNAVAILABLE** — use ranges `~MM:SS - MM:SS` |
| Semantic Precision | **LOW** |

---

## 2. Confidence Rules

### 2.1 Ceiling Enforcement

```
MAXIMUM ALLOWED CONFIDENCE: LOW

Extraction may ONLY assign:
- low: All statements

NEVER USE: high, medium
```

### 2.2 Confidence Assignment

**All claims and key points MUST be low confidence.**

```python
if confidence in ["high", "medium"]:
    confidence = "low"
    warnings.append("Confidence auto-downgraded: video_only ceiling is LOW")
```

---

## 3. Quote Prohibition

### 3.1 Critical Rule

**QUOTES ARE FORBIDDEN IN video_only MODE.**

The model cannot verify what was said without text. Any "quote" would be a hallucination.

### 3.2 Schema Enforcement

The output schema for `video_only` mode:
- Does NOT contain a `quotes` array
- Contains `approximate_observations` array instead

```python
# Validation check
if analysis_mode == "video_only" and "quotes" in extraction_output:
    raise ValidationError("quotes array forbidden in video_only mode")
```

---

## 4. Approximate Observations

### 4.1 What Observations Are

Observations are **semantic descriptions** of what was perceived in the video:
- What topics were discussed
- What visual elements appeared
- What emotions or tones were conveyed
- What events occurred

### 4.2 What Observations Are NOT

- Verbatim quotes
- Exact transcriptions
- Precise timestamps
- High-confidence claims

### 4.3 Observation Format

```json
{
  "observation_id": "OBS_1",
  "description": "The speaker discusses financial challenges faced by the company",
  "timestamp_range": "~05:30 - 08:15",
  "type": "observation",
  "approximate": true,
  "confidence": "low"
}
```

### 4.4 Observation Language Guidelines

**Use phrases like:**
- "The speaker appears to discuss..."
- "The content shows..."
- "Visual elements suggest..."
- "The tone conveys..."

**Do NOT use:**
- Direct quotation marks
- "He said" or "She stated"
- Claims of verbatim accuracy
- Specific attribution without visual confirmation

---

## 5. Validation Requirements

### 5.1 Mandatory Checks

| Check | Description | On Failure |
|-------|-------------|------------|
| V1 | Valid JSON matching schema | Hard fail, retry once |
| V2 | source_id matches input exactly | Hard fail, retry once |
| V3 | No confidence exceeds LOW | Auto-downgrade, warn |
| V5 | No quotes array in output | Hard fail, reject extraction |
| V6 | All observations marked approximate | Auto-fix, warn |

### 5.2 Quote Detection and Rejection

```python
def validate_video_only_output(extraction: dict) -> ValidationResult:
    errors = []

    # Check for forbidden quotes
    if "quotes" in extraction and len(extraction["quotes"]) > 0:
        errors.append("FORBIDDEN: quotes array not allowed in video_only mode")

    # Verify all observations are marked approximate
    for obs in extraction.get("approximate_observations", []):
        if not obs.get("approximate", False):
            obs["approximate"] = True
            warnings.append(f"Auto-fixed: {obs['observation_id']} marked approximate")

    return ValidationResult(errors=errors, warnings=warnings)
```

---

## 6. Provenance Requirements

### 6.1 Required Metadata

```python
@dataclass
class VideoOnlyProvenance:
    source_id: str                    # SRC_X format
    source_type: str                  # "youtube"
    input_mode: str                   # "url"
    analysis_mode: str = "video_only"

    # Degradation details
    transcript_attempted: bool = True
    transcript_failure_reason: str    # "supadata_failed, whisper_failed, captions_unavailable"

    # Confidence
    confidence_ceiling: str = "low"
    confidence_note: str = "No text available; visual/audio analysis only"
    system_verified: bool = True

    # Metadata
    title: str
    creator: Optional[str]
    url: str
    date: Optional[str]
    duration: str
```

### 6.2 Provenance Display (Prominent Warning)

```
Source: SRC_1
Mode: video_only (LOW confidence)

WARNING: No transcript or captions available for this source.
- Quotes are NOT available
- All observations are approximate
- Confidence is limited to LOW
- Content is based on visual/audio analysis only

Transcript acquisition failed: Supadata unavailable, Whisper failed, no captions
```

---

## 7. Output Schema

```json
{
  "source_id": "SRC_1",
  "analysis_mode": "video_only",
  "extraction_metadata": {
    "extracted_at": "2026-01-14T10:30:00Z",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "low"
  },
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string",
      "confidence": "low",
      "timestamp": "~MM:SS or null",
      "supporting_observation_ids": ["OBS_1"]
    }
  ],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "string",
      "confidence": "low",
      "timestamp_range": "~MM:SS - MM:SS"
    }
  ],
  "approximate_observations": [
    {
      "observation_id": "OBS_1",
      "description": "semantic description",
      "timestamp_range": "~MM:SS - MM:SS",
      "type": "observation",
      "approximate": true
    }
  ],
  "themes": [...],
  "tensions": [...],
  "entities": [...],
  "gaps": [...]
}
```

**Critical:** No `quotes` array exists in this schema.

---

## 8. Edge Cases

### 8.1 Video Has No Audio

**Scenario:** Video is silent or audio track is corrupted.

**Handling:**
- Rely on visual analysis only
- Note in provenance: "Audio unavailable"
- Observations describe only visual elements
- Confidence remains LOW

### 8.2 Video Is Mostly Text-on-Screen

**Scenario:** Video displays text (slides, documents) but has no transcript.

**Handling:**
- Gemini can "read" on-screen text
- Still use observations, not quotes
- Note: "Content extracted from on-screen text"
- Confidence remains LOW (OCR-equivalent)

### 8.3 Video Quality Is Very Poor

**Scenario:** Video is low resolution, blurry, or corrupted.

**Handling:**
- Extract what is discernible
- Note quality issues in observations
- Add warning: "Video quality severely limits analysis"
- Consider marking source as `extraction_failed` if nothing useful

---

## 9. Prompt Template Reference

Use `Gemini_Semantic_Extraction.md` with:
- Observation Instructions template
- Schema WITHOUT quotes
- Confidence ceiling: LOW

---

## 10. Invariants (Always True)

1. **Confidence is always LOW** — no exceptions
2. **No quotes array** — schema physically lacks it
3. **All observations marked approximate** — `approximate: true`
4. **Timestamp ranges** — `~MM:SS - MM:SS`, not precise
5. **Degradation is disclosed** — prominent warning in output
6. **Transcript failure recorded** — provenance shows what was attempted

---

## 11. Terminology Compliance

**ALWAYS use:** `approximate_observations`
**NEVER use:** "approximate quotes", "inferred quotes", "visual quotes"

Quotes require verbatim text. This mode has no verbatim text. Therefore, no quotes.

---

**END OF MODE SPECIFICATION**
