# Analysis Mode: transcript_grounded

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14

---

## 1. Mode Definition

`transcript_grounded` is the **highest fidelity** analysis mode. It applies when a full, accurate transcript is available from a primary source (Supadata API or Whisper transcription).

### 1.1 When This Mode Applies

| Source Type | Transcript Source | Mode Assignment |
|-------------|-------------------|-----------------|
| YouTube | Supadata API (full transcript) | `transcript_grounded` |
| YouTube | Whisper transcription | `transcript_grounded` |
| Podcast | Full transcript file | `transcript_grounded` |

### 1.2 Mode Characteristics

| Property | Value |
|----------|-------|
| Confidence Ceiling | **HIGH** |
| Quotes Allowed | **YES** — verbatim required |
| Quote Verification | **REQUIRED** — string matching |
| Timestamp Grounding | **PRECISE** — format `MM:SS` or `HH:MM:SS` |
| Semantic Precision | **HIGH** |

---

## 2. Confidence Rules

### 2.1 Ceiling Enforcement

```
MAXIMUM ALLOWED CONFIDENCE: HIGH

Extraction may assign:
- high: Strong, explicit statements with verbatim quote support
- medium: Statements with some ambiguity or context dependence
- low: Inferred or weakly supported statements
```

### 2.2 Confidence Assignment Criteria

| Confidence | Criteria |
|------------|----------|
| HIGH | Direct, unambiguous statement with exact quote match |
| MEDIUM | Clear statement but requires minor context interpretation |
| LOW | Implied or requires inference from surrounding content |

---

## 3. Quote Extraction Rules

### 3.1 Requirements

- **Verbatim text required** — exact words from transcript
- **Speaker attribution** — identify who said it when possible
- **Timestamp required** — precise format `MM:SS` or `HH:MM:SS`
- **Context note** — brief description of surrounding context

### 3.2 Quote Selection Criteria

Prioritize quotes that:
1. Support key points with direct evidence
2. Contain strong claims or revelations
3. Capture the source's main arguments
4. May be controversial or contested
5. Provide specific facts, dates, numbers

### 3.3 Quote Prohibitions

- **NO paraphrasing** — exact words only
- **NO combining** — each quote is atomic
- **NO invention** — quote must exist in transcript
- **NO cleaning up** — preserve filler words if part of quote

### 3.4 Quote Format

```json
{
  "quote_id": "QT_1",
  "text": "We discovered the problem in March, not June like they claimed",
  "speaker": "John Smith",
  "timestamp": "14:32",
  "context": "Discussing timeline discrepancy"
}
```

---

## 4. Validation Requirements

### 4.1 Mandatory Checks (V1-V5)

| Check | Description | On Failure |
|-------|-------------|------------|
| V1 | Valid JSON matching schema | Hard fail, retry once |
| V2 | source_id matches input exactly | Hard fail, retry once |
| V3 | No confidence exceeds HIGH | Auto-downgrade, warn |
| V4 | Quote verification via string match | Soft fail, warn, mark unverified |
| V5 | Timestamps within video duration | Soft fail, warn |

### 4.2 Quote Verification Process

```python
def verify_quote(quote_text: str, transcript: str) -> VerificationResult:
    """Verify quote exists in transcript."""
    normalized_quote = normalize_whitespace(quote_text.lower())
    normalized_transcript = normalize_whitespace(transcript.lower())

    if normalized_quote in normalized_transcript:
        return VerificationResult(status="verified", confidence=1.0)

    # Fuzzy match for minor variations
    similarity = fuzzy_match(normalized_quote, normalized_transcript)
    if similarity >= 0.85:
        return VerificationResult(status="partially_verified", confidence=similarity)

    return VerificationResult(status="unverified", confidence=0.0)
```

### 4.3 Verification Status Propagation

| Status | Action |
|--------|--------|
| `verified` | Quote included, full confidence |
| `partially_verified` | Quote included, marked approximate |
| `unverified` | Warning added, quote flagged |

---

## 5. Provenance Requirements

### 5.1 Required Metadata

```python
@dataclass
class TranscriptGroundedProvenance:
    source_id: str                    # SRC_X format
    source_type: str                  # "youtube"
    input_mode: str                   # "url"
    analysis_mode: str = "transcript_grounded"

    # Transcript details
    transcript_source: str            # "supadata" | "whisper"
    transcript_length: int            # Word count
    transcript_verified: bool = True

    # Confidence
    confidence_ceiling: str = "high"
    system_verified: bool = True

    # Metadata
    title: str
    creator: Optional[str]
    url: str
    date: Optional[str]
    duration: str                     # "HH:MM:SS"
```

### 5.2 Provenance Display

```
Source: SRC_1
Mode: transcript_grounded (HIGH confidence)
Transcript: Supadata API (verified)
Quotes: Verbatim, timestamp-grounded
```

---

## 6. Output Schema

```json
{
  "source_id": "SRC_1",
  "analysis_mode": "transcript_grounded",
  "extraction_metadata": {
    "extracted_at": "2026-01-14T10:30:00Z",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "high"
  },
  "key_points": [...],
  "claims": [...],
  "quotes": [
    {
      "quote_id": "QT_1",
      "text": "verbatim text",
      "speaker": "string or null",
      "timestamp": "MM:SS",
      "context": "brief context"
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

### 7.1 Transcript Contains Errors

**Scenario:** Supadata/Whisper transcript has transcription errors.

**Handling:**
- Quote verification may fail for correct extractions
- Use fuzzy matching with 85% threshold
- Add warning: "Transcript quality may affect quote verification"

### 7.2 Multiple Speakers Not Identified

**Scenario:** Transcript doesn't identify speakers.

**Handling:**
- Set speaker to null
- Add note in context field: "Speaker unidentified in transcript"
- Do not guess speaker identity

### 7.3 Timestamps Missing in Transcript

**Scenario:** Transcript source doesn't provide timestamps.

**Handling:**
- Set timestamp to null
- Add warning: "Timestamps unavailable from transcript source"
- Mode remains `transcript_grounded` (quotes still verbatim)

---

## 8. Prompt Template Reference

Use `Gemini_Semantic_Extraction.md` with:
- Quote Instructions template
- Schema WITH quotes
- Confidence ceiling: HIGH

---

## 9. Invariants (Always True)

1. **Quotes are verbatim** — never paraphrased
2. **Confidence ceiling is HIGH** — extraction may use high/medium/low
3. **Quote verification runs** — all quotes checked against transcript
4. **Timestamps are precise** — format `MM:SS`, not approximate
5. **Source is system-verified** — metadata from API, not user-provided

---

**END OF MODE SPECIFICATION**
