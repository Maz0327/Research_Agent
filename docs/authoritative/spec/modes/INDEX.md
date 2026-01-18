# Analysis Modes — Index

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14

---

## Overview

The Research Agent supports **6 analysis modes** that determine how sources are processed. Each mode has specific rules for confidence ceilings, quote handling, and validation.

---

## Quick Reference Table

| Mode | Confidence Ceiling | Quotes Allowed | Schema Type | Provenance |
|------|-------------------|----------------|-------------|------------|
| `transcript_grounded` | HIGH | YES (verbatim) | WITH quotes | system_extracted |
| `caption_grounded` | MEDIUM | YES (approximate) | WITH quotes | system_extracted |
| `video_only` | LOW | NO | WITHOUT quotes | system_extracted |
| `text_provided` | MEDIUM | YES (with warnings) | WITH quotes | user_provided |
| `ocr_extracted` | MEDIUM | YES (with warnings) | WITH quotes | ocr_extracted |
| `article_fetched` | HIGH | YES (verbatim) | WITH quotes | system_extracted |

---

## Mode Selection Logic

### For YouTube/Video URLs

```
1. Attempt Supadata API
   ├── Success → transcript_grounded (HIGH)
   └── Fail → Continue

2. Attempt Whisper transcription
   ├── Success → transcript_grounded (HIGH)
   └── Fail → Continue

3. Attempt YouTube captions
   ├── Success → caption_grounded (MEDIUM)
   └── Fail → Continue

4. All failed → video_only (LOW)
```

### For Article URLs

```
1. Attempt content extraction
   ├── Success → article_fetched (HIGH)
   └── Fail → Continue

2. Paywall detected
   └── Return error with suggestion to use text_provided

3. Extraction failed
   └── Source excluded, job continues
```

### For User Input

```
Text paste → text_provided (MEDIUM)
Screenshot upload → ocr_extracted (MEDIUM)
```

---

## Mode Specifications

### HIGH Confidence Modes (Quotes Allowed)

| Mode | Spec File | Use Case |
|------|-----------|----------|
| `transcript_grounded` | [transcript_grounded.md](./transcript_grounded.md) | YouTube with full transcript |
| `article_fetched` | [article_fetched.md](./article_fetched.md) | Web articles, news, blog posts |

### MEDIUM Confidence Modes

| Mode | Spec File | Quotes? | Use Case |
|------|-----------|---------|----------|
| `caption_grounded` | [caption_grounded.md](./caption_grounded.md) | YES (approximate) | YouTube with captions only |
| `text_provided` | [text_provided.md](./text_provided.md) | NO | User-pasted text |
| `ocr_extracted` | [ocr_extracted.md](./ocr_extracted.md) | NO | Screenshots |

### LOW Confidence Modes

| Mode | Spec File | Use Case |
|------|-----------|----------|
| `video_only` | [video_only.md](./video_only.md) | Video with no text available |

---

## Quote vs Observation Rules

### Modes WITH Verified Quotes

```
transcript_grounded: Verbatim quotes with timestamps (MM:SS)
caption_grounded: Approximate quotes with ~timestamps (~MM:SS)
article_fetched: Verbatim quotes with paragraph references
```

### Modes WITH Unverified Quotes (Warnings Required)

```
text_provided: Quotes with user verification warning
ocr_extracted: Quotes with OCR accuracy warning
```

### Modes WITHOUT Quotes (Observations Only)

```
video_only: Approximate observations with timestamp ranges (~MM:SS - MM:SS)
```

---

## Validation Checks by Mode

| Check | transcript | caption | video_only | text | ocr | article |
|-------|-----------|---------|------------|------|-----|---------|
| V1: Valid JSON | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| V2: source_id match | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| V3: Confidence ceiling | HIGH | MEDIUM | LOW | MEDIUM | MEDIUM | HIGH |
| V4: Quote verification | ✅ | ✅ (lenient) | N/A | ⚠️ (warn) | ⚠️ (warn) | ✅ |
| V5: No quotes check | N/A | N/A | ✅ | N/A | N/A | N/A |
| V6: Observations marked | N/A | N/A | ✅ | Optional | Optional | N/A |

---

## Provenance Types

| Provenance | Meaning | Modes |
|------------|---------|-------|
| `system_extracted` | System fetched and verified content | transcript_grounded, caption_grounded, video_only, article_fetched |
| `user_provided` | User supplied content directly | text_provided |
| `ocr_extracted` | System extracted via vision/OCR | ocr_extracted |

---

## Output Schema Selection

### Schema WITH Quotes

Used by: `transcript_grounded`, `caption_grounded`, `article_fetched`

```json
{
  "quotes": [
    {
      "quote_id": "QT_1",
      "text": "verbatim or approximate text",
      "speaker": "...",
      "timestamp": "MM:SS or ~MM:SS",
      "context": "..."
    }
  ]
}
```

### Schema WITHOUT Quotes

Used by: `video_only`, `text_provided`, `ocr_extracted`

```json
{
  "approximate_observations": [
    {
      "observation_id": "OBS_1",
      "description": "semantic description",
      "timestamp_range": "~MM:SS - MM:SS",
      "type": "observation",
      "approximate": true
    }
  ]
}
```

---

## Invariants (Apply to ALL Modes)

1. **Confidence cannot exceed ceiling** — auto-downgrade if violated
2. **source_id must match exactly** — hard fail if wrong
3. **Empty arrays are acceptable** — prefer sparse over hallucinated
4. **Mode is determined BEFORE extraction** — not during
5. **Mode propagates to all outputs** — Doc 0, Doc 1, Doc 2

---

## Cross-References

- **Prompt Contract:** `docs/authoritative/prompts/Gemini_Semantic_Extraction.md`
- **Validation Rules:** `docs/authoritative/spec/Validation_and_Retry_Rules.md`
- **Pipeline Spec:** `docs/authoritative/spec/RASS.md` Section 4.2-4.3
- **Extended Input Types:** `docs/authoritative/spec/EXTENDED_SPECIFICATIONS.md` Part 1

---

**END OF INDEX**
