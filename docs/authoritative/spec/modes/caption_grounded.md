# Analysis Mode: caption_grounded

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14

---

## 1. Mode Definition

`caption_grounded` is a **degraded fidelity** analysis mode. It applies when only YouTube auto-generated or uploaded captions are available (after Supadata and Whisper fail).

### 1.1 When This Mode Applies

| Source Type | Caption Source | Mode Assignment |
|-------------|----------------|-----------------|
| YouTube | Auto-generated captions | `caption_grounded` |
| YouTube | Uploaded captions | `caption_grounded` |
| YouTube | Community-contributed captions | `caption_grounded` |

### 1.2 Mode Characteristics

| Property | Value |
|----------|-------|
| Confidence Ceiling | **MEDIUM** |
| Quotes Allowed | **YES** — marked approximate |
| Quote Verification | **PARTIAL** — tolerance for caption errors |
| Timestamp Grounding | **APPROXIMATE** — format `~MM:SS` |
| Semantic Precision | **MEDIUM** |

---

## 2. Confidence Rules

### 2.1 Ceiling Enforcement

```
MAXIMUM ALLOWED CONFIDENCE: MEDIUM

Extraction may assign:
- medium: Clear statements with reasonable caption support
- low: Inferred or weakly supported statements

NEVER USE: high
```

### 2.2 Confidence Assignment Criteria

| Confidence | Criteria |
|------------|----------|
| MEDIUM | Clear statement with supporting caption text |
| LOW | Implied or requires inference; caption may be garbled |

### 2.3 Auto-Downgrade Rule

```python
if confidence == "high":
    confidence = "medium"
    warnings.append("Confidence auto-downgraded: caption_grounded ceiling is MEDIUM")
```

---

## 3. Quote Extraction Rules

### 3.1 Requirements

- **Approximate text** — captions may have errors
- **Mark as approximate** — set `approximate: true`
- **Speaker attribution** — when identifiable
- **Approximate timestamp** — format `~MM:SS`

### 3.2 Quote Handling

Quotes in `caption_grounded` mode:
1. May contain transcription errors
2. Must be marked `approximate: true`
3. Should note caption quality issues
4. Are less reliable than `transcript_grounded`

### 3.3 Quote Format

```json
{
  "quote_id": "QT_1",
  "text": "We discovered the problem in march not june like they claimed",
  "speaker": "John Smith",
  "timestamp": "~14:32",
  "context": "Discussing timeline (caption quality: auto-generated)",
  "approximate": true
}
```

---

## 4. Validation Requirements

### 4.1 Mandatory Checks

| Check | Description | On Failure |
|-------|-------------|------------|
| V1 | Valid JSON matching schema | Hard fail, retry once |
| V2 | source_id matches input exactly | Hard fail, retry once |
| V3 | No confidence exceeds MEDIUM | Auto-downgrade, warn |
| V4 | Quote presence check (lenient) | Soft fail, warn |
| V5 | Timestamps within duration | Soft fail, warn |

### 4.2 Lenient Quote Verification

```python
def verify_caption_quote(quote_text: str, captions: str) -> VerificationResult:
    """Verify quote with tolerance for caption errors."""
    # Use 70% similarity threshold (vs 85% for transcript_grounded)
    similarity = fuzzy_match(normalize(quote_text), normalize(captions))

    if similarity >= 0.70:
        return VerificationResult(status="caption_matched", confidence=similarity)

    return VerificationResult(status="unverified", confidence=0.0)
```

---

## 5. Provenance Requirements

### 5.1 Required Metadata

```python
@dataclass
class CaptionGroundedProvenance:
    source_id: str                    # SRC_X format
    source_type: str                  # "youtube"
    input_mode: str                   # "url"
    analysis_mode: str = "caption_grounded"

    # Caption details
    caption_source: str               # "youtube_auto" | "youtube_uploaded"
    caption_language: str             # "en", "es", etc.
    caption_quality: str              # "auto_generated" | "human_uploaded"

    # Confidence
    confidence_ceiling: str = "medium"
    confidence_note: str = "Captions may contain transcription errors"
    system_verified: bool = True

    # Metadata
    title: str
    creator: Optional[str]
    url: str
    date: Optional[str]
    duration: str
```

### 5.2 Provenance Display

```
Source: SRC_1
Mode: caption_grounded (MEDIUM confidence)
Captions: YouTube auto-generated
Quotes: Approximate, may contain errors
Warning: Caption accuracy not guaranteed
```

---

## 6. Output Schema

```json
{
  "source_id": "SRC_1",
  "analysis_mode": "caption_grounded",
  "extraction_metadata": {
    "extracted_at": "2026-01-14T10:30:00Z",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "medium"
  },
  "key_points": [...],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "...",
      "confidence": "medium",
      "...": "..."
    }
  ],
  "quotes": [
    {
      "quote_id": "QT_1",
      "text": "approximate text from captions",
      "speaker": "string or null",
      "timestamp": "~MM:SS",
      "context": "brief context",
      "approximate": true
    }
  ],
  "themes": [...],
  "tensions": [...],
  "entities": [...],
  "gaps": [...]
}
```

---

## 7. Edge Cases

### 7.1 Auto-Generated Captions Are Garbled

**Scenario:** YouTube auto-captions are largely unintelligible.

**Handling:**
- Extract what is clearly understandable
- Mark all quotes approximate
- Add warning: "Caption quality severely degraded"
- Consider downgrading to `video_only` if <30% intelligible

### 7.2 Captions in Wrong Language

**Scenario:** Video is in English, captions are in Spanish.

**Handling:**
- Note language mismatch in provenance
- Do NOT attempt to translate
- Add warning: "Caption language mismatch detected"
- Proceed with extraction if content is still useful

### 7.3 Captions Have Significant Delays

**Scenario:** Caption timestamps are consistently 5+ seconds off.

**Handling:**
- Note timing offset in provenance
- Timestamps remain approximate (`~MM:SS`)
- Add warning: "Caption timing may be offset"

---

## 8. Degradation from transcript_grounded

This mode is a **fallback** from `transcript_grounded`:

| Aspect | transcript_grounded | caption_grounded |
|--------|---------------------|------------------|
| Confidence ceiling | HIGH | MEDIUM |
| Quote accuracy | Verbatim | Approximate |
| Timestamp format | `MM:SS` | `~MM:SS` |
| Verification threshold | 85% | 70% |
| Quote flag | None | `approximate: true` |

---

## 9. Prompt Template Reference

Use `Gemini_Semantic_Extraction.md` with:
- Quote Instructions template (with approximate flag)
- Schema WITH quotes
- Confidence ceiling: MEDIUM

---

## 10. Invariants (Always True)

1. **Confidence never exceeds MEDIUM** — auto-downgrade if violated
2. **All quotes marked approximate** — `approximate: true`
3. **Timestamps use approximate format** — `~MM:SS`
4. **Verification uses lenient threshold** — 70% similarity
5. **Caption quality noted in provenance** — auto vs uploaded

---

**END OF MODE SPECIFICATION**
