# Log Investigation Report

**Date:** 2026-01-21
**Scope:** Production logs from Railway Worker and Supabase DB export
**Mission:** INVESTIGATION ONLY — Identify recurring warning/error classes

---

## Executive Summary

Analyzed production logs to identify recurring error/warning patterns. Found **6 distinct issue classes**, with most being intentional quality controls rather than bugs. The warning count "explosion" (109 warnings in one job) is working as designed but may benefit from UI aggregation.

---

## Issue Classes Identified

### 1. QUOTE NOT FOUND IN TRANSCRIPT (52 occurrences)

**Source Code:**
`backend/pipeline/stages/semantic_extraction.py:367-370`

```python
warnings.append(
    f"[{source_id}] Claim {claim.claim_id}: "
    f"supporting quote not found in transcript"
)
```

**Root Cause:**
LLM extracts claims with `supporting_quotes` field, then quote verification (`verify_quote()`) fails to match the quote text against the actual transcript. This is **intentional hallucination prevention** — the LLM sometimes fabricates quotes.

**Impact:**
- **User-facing:** Low — warnings are stored but not prominently displayed
- **Correctness:** GOOD — system correctly removes hallucinated quotes
- **Performance:** None

**Recommendation:**
NO FIX NEEDED. This is working as designed. Consider aggregating warnings in UI: "52 unverified quotes removed" instead of 52 individual warnings.

---

### 2. CONFIDENCE DOWNGRADED TO LOW (39 occurrences)

**Source Code:**
`backend/pipeline/stages/semantic_extraction.py:374-379`
`backend/pipeline/semantic_validation.py:675-677, 697-699`

**Root Cause:**
Two triggers:
1. **All supporting quotes removed** → Claim confidence auto-downgraded to LOW
2. **Confidence ceiling enforcement** → Mode ceiling (e.g., MEDIUM for `caption_grounded`) forces downgrade

**Impact:**
- **User-facing:** None directly — affects output quality scores
- **Correctness:** GOOD — prevents overconfident claims without evidence
- **Performance:** None

**Recommendation:**
NO FIX NEEDED. Working as designed per architecture rules.

---

### 3. SINGLE SOURCE PERSPECTIVE WARNINGS (12 occurrences total)

**Warnings:**
- `[SRC_X] All key points from single source - limited perspective`
- `[SRC_X] All themes from single source - limited perspective`
- `[SRC_X] Confidence: Partial verification with some limitations`

**Source Code:**
`backend/pipeline/stages/semantic_validation_stage.py` (validation stage)

**Root Cause:**
Expected behavior for single-source jobs. System warns that cross-source verification wasn't possible.

**Impact:**
- **User-facing:** Low — informational warning
- **Correctness:** GOOD — accurate disclaimer

**Recommendation:**
NO FIX NEEDED. Consider suppressing for intentionally single-source jobs if user explicitly provides only one source.

---

### 4. GEMINI 503 UNAVAILABLE (2 occurrences)

**Source Code:**
`backend/integrations/gemini_client.py:640`
`backend/pipeline/stages/semantic_extraction.py:437`

**Log Entry:**
```
Gemini JSON generation failed: 503 UNAVAILABLE.
{'error': {'code': 503, 'message': 'The model is overloaded. Please try again later.'}}
```

**Root Cause:**
Google's Gemini API rate limiting / capacity constraints. External dependency.

**Impact:**
- **User-facing:** Job may fail if retry exhausted
- **Correctness:** GOOD — error properly logged
- **Performance:** Retry delays

**Recommendation:**
EXISTING RETRY LOGIC SUFFICIENT. If frequency increases, consider:
1. Adding exponential backoff with jitter
2. Model fallback (e.g., gemini-1.5-flash as backup)
3. Queue-based rate limiting

---

### 5. VALIDATION STATUS FAILURES (5 occurrences)

**Log Patterns:**
- `status=failed_with_warnings, confidence=medium, warnings=4`
- `status=failed, confidence=medium, warnings=2`

**Source Code:**
`backend/pipeline/semantic_validation.py:1014`

**Root Cause:**
Validation detected issues that couldn't be auto-corrected:
- **failed**: Critical schema/grounding issues
- **failed_with_warnings**: Structural issues but usable output

Note: Per `semantic_validation_stage.py:151`, the job completed successfully ("quotes=40/40 verified (100.0%), warnings=11") despite per-source validation failures. The system aggregates and recovers.

**Impact:**
- **User-facing:** Job completes with warnings
- **Correctness:** GOOD — issues tracked, quality affected
- **Performance:** Retry attempts add latency

**Recommendation:**
NO FIX NEEDED. Validation working as designed. The per-source failures are recovered at the job level.

---

### 6. CELERY SUPERUSER WARNING (1 occurrence per startup)

**Log Entry:**
```
SecurityWarning: You're running the worker with superuser privileges: this is absolutely not recommended!
```

**Source Code:**
External — Celery library (`/usr/local/lib/python3.11/site-packages/celery/platforms.py:829`)

**Root Cause:**
Railway containers run as root (uid=0). Celery warns about this.

**Impact:**
- **User-facing:** None
- **Correctness:** None
- **Performance:** None
- **Security:** Minor concern in containerized environment

**Recommendation:**
LOW PRIORITY FIX. Options:
1. Create non-root user in Dockerfile
2. Suppress warning with `C_FORCE_ROOT=true` environment variable
3. Accept warning in containerized context (common practice)

---

## JSONB Normalization Warnings

**Current Status:** No JSONB normalization warnings in logs.

The `_normalize_jsonb_field()` function was recently enhanced with better logging (field_name, job_id). The warning "Normalized corrupted JSONB list to dict" would appear if corrupted data exists, but none was found in these logs.

**Conclusion:** JSONB corruption is not currently occurring in production, or the fix deployed earlier has resolved it.

---

## Warning Count Explosion Analysis

**Observed:** One job with 109 warnings.

**Breakdown:**
| Category | Count |
|----------|-------|
| Quote not found | 52 |
| Confidence downgraded | 39 |
| Single source perspective | 6 |
| Confidence partial | 6 |
| Other | 6 |

**Root Cause:**
Multi-source job (6 sources) with many claims. Each claim's quote verification failure generates TWO warnings:
1. "quote not found"
2. "confidence downgraded"

This is **multiplication effect**: 26 claims × 2 warnings = 52 + related downgrades.

**Recommendation:**
Consider UI/UX improvement:
1. Aggregate similar warnings: "26 claims had unverified quotes (confidence downgraded)"
2. Group by source: "SRC_1: 8 warnings, SRC_2: 12 warnings"
3. Add `warning_summary` field to job for frontend display

---

## Summary Table

| Issue Class | Frequency | Severity | Fix Needed? |
|-------------|-----------|----------|-------------|
| Quote not found | 52/job | Low | No - working as designed |
| Confidence downgraded | 39/job | Low | No - working as designed |
| Single source warnings | 12/job | Low | No - working as designed |
| Gemini 503 | 2 total | Medium | No - retry exists |
| Validation failures | 5/job | Low | No - job recovers |
| Celery superuser | 1/startup | Low | Optional fix |

---

## Railway Log Format Note

The Railway logs have a quirk where the JSON `"level":"error"` attribute appears even for INFO/DEBUG level messages. This is a **log collection format issue**, not actual errors. The actual log level is in the message itself (e.g., `| INFO |`, `| DEBUG |`).

Only **2 actual ERROR level messages** were found:
1. Gemini 503 at gemini_client.py:640
2. Gemini error propagation at semantic_extraction.py:437

---

## Recommendations Summary

### No Action Required
- Quote verification warnings (working as designed)
- Confidence downgrades (working as designed)
- Validation failures (job-level recovery works)

### Low Priority Improvements
1. **Warning Aggregation:** Add `warning_summary` field for UI display
2. **Celery User:** Create non-root user in Dockerfile or set `C_FORCE_ROOT=true`

### Monitor
- Gemini 503 frequency — if increasing, add model fallback

---

*Report generated: 2026-01-21*
