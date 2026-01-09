# Semantic Validation Skill

**Skill ID:** `semantic-validation`
**Auto-Trigger:** When implementing validation logic for pipeline outputs
**Purpose:** Enforce hard/soft failure handling and transcript-aware validation

---

## When This Skill Activates

- Writing validation code for Gemini outputs
- Implementing retry logic
- Working with confidence calibration
- Handling degraded sources

---

## Validation Hierarchy

```
Schema Validation (Hard Fail)
    ↓
Grounding Validation (Hard Fail)
    ↓
Transcript-Aware Validation (Mode-dependent)
    ↓
Structural Sufficiency (Soft Fail)
    ↓
Confidence Calibration (Derived)
```

---

## Hard Fail Conditions

### Schema Validation
- Invalid JSON
- Missing required fields
- Malformed IDs
- Cross-references to non-existent IDs

### Grounding Validation
- Key Point with no source references
- Claim with no supporting Quote
- Theme with <2 Key Points
- Doc 1/2 introduces facts not in Doc 0

**Action:** Retry once, then FAIL job.

---

## Transcript-Aware Validation

Validation behavior changes based on `transcript_provenance.gemini_analysis_mode`:

### `transcript_grounded`
| Rule | Enforcement |
|------|-------------|
| Quotes | MUST be verbatim |
| Timestamps | REQUIRED |
| Max confidence | High |

### `caption_grounded`
| Rule | Enforcement |
|------|-------------|
| Quotes | Marked `approximate` |
| Timestamps | ±5 seconds |
| Max confidence | Medium |

### `video_only`
| Rule | Enforcement |
|------|-------------|
| Quotes | Marked `unverified` |
| Timestamps | Unavailable |
| Max confidence | Low |
| Job status | MUST complete |

**CRITICAL:** Never fail job due to transcript absence alone.

---

## Soft Fail Conditions

Indicators of thin output:
- Long source (30+ min) with <3 Key Points
- All Key Points from single source
- Themes collapse to single category
- No Gaps identified
- Verification rate <50%

**Action:** Retry once, then proceed with:
- `status: "completed_with_warnings"`
- Downgraded confidence
- Amplified gaps + next steps

---

## Confidence Calibration

```python
def calibrate_confidence(validation_results):
    if (sources >= 2 and verification_rate >= 0.7
        and no_critical_tensions):
        return "high"
    elif (sources >= 1 and verification_rate >= 0.5):
        return "medium"
    else:
        return "low"
```

Confidence must be displayed in Doc 2 and referenced in Doc 1.

---

## Retry Policy

| Trigger | Max Retries | Constraint |
|---------|-------------|------------|
| Invalid JSON | 1 | Schema-only prompt |
| Missing grounding | 1 | Grounding-focused prompt |
| Thin output | 1 | Constrained prompt |
| Supadata fail | 1 | Try YouTube captions |
| Captions fail | 1 | Continue video_only |

**Rules:**
- Retry prompt must be MORE constrained, never broader
- No chained retries
- No new data in retry

---

## Provenance Validation (Hard Fail)

Video source validation fails if:
- Missing `transcript_provenance`
- Missing `gemini_analysis_mode`
- Missing `verification_capabilities`

This ensures downstream documents know source reliability.

---

## Implementation Pattern

```python
def validate_extraction(result: dict, mode: str) -> ValidationResult:
    errors = []
    warnings = []

    # 1. Schema validation (hard fail)
    if not is_valid_json(result):
        return ValidationResult(passed=False, errors=["Invalid JSON"])

    # 2. Grounding validation (hard fail)
    for kp in result.get("key_points", []):
        if not kp.get("sources"):
            errors.append(f"Key point {kp['id']} has no sources")

    # 3. Transcript-aware validation (mode-dependent)
    if mode == "video_only":
        for quote in result.get("quotes", []):
            if not quote.get("unverified"):
                warnings.append(f"Quote {quote['id']} should be marked unverified")

    # 4. Structural sufficiency (soft fail)
    if len(result.get("key_points", [])) < 8:
        warnings.append("Thin extraction: fewer than 8 key points")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        confidence=calibrate_confidence(result, mode)
    )
```

---

## Checklist Before Commit

- [ ] Schema validation catches all required fields
- [ ] Grounding validation checks all cross-references
- [ ] Transcript-aware rules implemented per mode
- [ ] Retry logic bounded (max 1)
- [ ] Confidence calibration derives from signals
- [ ] Provenance validation present for video sources
- [ ] Soft failures proceed with warnings, not errors

---

## Reference Documents

- `Active Docs/REVIEW THESE FILES/Validation & Retry Rules Specification.md` - All rules
- `Active Docs/REVIEW THESE FILES/Research Agent System Specification (RASS).md` - Section 8
- `backend/models/source.py` - TranscriptProvenance model
