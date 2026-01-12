# Validation & Retry Rules Specification

**Research Agent System Specification — Addendum**

This document defines **deterministic validation**, **retry behavior**, **degradation rules**, and **job states** for all Research Agent outputs.

The goal is **reliability over fluency**.

---

## 0. PRINCIPLES (NON-NEGOTIABLE)

* Prefer **honest thin output** over padded output
* Never fabricate to satisfy quotas
* Retries are **bounded**
* Degradation is **visible**
* Failure is **actionable**

---

## 1. VALIDATION SCOPE

Validation occurs at **four levels**:

1. **Schema Validation** (machine)
2. **Grounding Validation** (machine)
3. **Structural Sufficiency** (heuristic)
4. **Confidence Calibration** (derived)

Only (1) and (2) can hard-fail a job.

---

## 2. SCHEMA VALIDATION (HARD FAIL)

### Applies to

* Gemini semantic extraction JSON
* Assembled Doc 0 / Doc 1 / Doc 2 JSON

### Rules

A **hard failure** occurs if:

* Output is not valid JSON
* Required top-level keys are missing
* IDs are malformed or missing
* Cross-references point to non-existent IDs

### Behavior

* Retry once with **schema-only correction prompt**
* If retry fails → **Job = FAILED**
* Error message must specify missing/invalid fields

---

## 3. GROUNDING VALIDATION (HARD FAIL)

### Applies to

* Key Points
* Claims
* Themes
* Tensions
* Speculative sections

### Rules

A **hard failure** occurs if:

* A Key Point has no source references
* A Claim has no supporting Quote
* A Theme references fewer than 2 Key Points
* Doc 1 or Doc 2 introduces facts not present in Doc 0

**Exception for video_only mode:**
For sources with `analysis_mode = video_only`:
- Claims are not required to have supporting Quotes
- Claims must reference approximate timestamp ranges
- Claims must be marked `confidence: low`
- Validation passes if these conditions are met

### Behavior

* Retry once with grounding-focused prompt
* If retry fails → **Stage = failed_with_warnings**

  Job continues with degraded output:
  - Doc 0: Produced deterministically (always possible)
  - Doc 1: Produced from deterministic gap rules + available metadata
  - Doc 2: Marked "thin/degraded: semantic extraction unavailable"

  **Job = FAILED only if:**
  - ALL sources fail (nothing usable remains)
  - Infrastructure/system failure (pipeline crash, DB outage)
  - Contract violation (no sources provided at all)

* Output must never silently drop ungrounded items

---

## 4. STRUCTURAL SUFFICIENCY (SOFT FAIL)

### Definition

Structural sufficiency is evaluated **relative to corpus size and diversity**, not absolute counts.

### Heuristic Indicators of Thin Output

Any of the following trigger a **soft fail**:

* Long source (≥30 min video or ≥3k words) with:

  * <3 Key Points
* All Key Points come from a single source
* Themes collapse into a single category
* No Gaps identified in a non-trivial topic
* Verification rate <50%

### Behavior on Soft Fail

* Retry **once** with constrained retry prompt
* If still thin:

  * Proceed
  * Mark job as **completed_with_warnings**
  * Downgrade confidence
  * Amplify Gaps + Next Steps

---

## 5. RETRY POLICY (GLOBAL)

### Maximum Retries

* **1 retry per stage**
* No chained retries
* No infinite loops

### Retry Triggers

* Invalid JSON
* Missing required fields
* Structural thinness
* Over-abstract output

### Retry Constraints

* Retry prompt must be **more constrained**, never broader
* Retry must not introduce new data
* Retry must reuse original input

---

## 6. CONFIDENCE CALIBRATION RULES

Confidence is derived automatically based on validation signals.

### High Confidence

* ≥2 sources
* Verification rate ≥70%
* No unresolved critical tensions

### Medium Confidence

* Limited sources
* Partial verification
* Some unresolved tensions

### Low Confidence

* Single perspective
* Thin extraction
* High uncertainty or unverifiable claims

Confidence level must be displayed in **Doc 2** and referenced in **Doc 1**.

---

## 7. JOB STATES (USER-VISIBLE)

### States

* `pending`
* `processing`
* `completed`
* `completed_with_warnings`
* `failed`

### State Rules

* `completed_with_warnings` is **not an error**
* Warnings must be human-readable
* `failed` must always include recovery guidance

---

## 8. PARTIAL SUCCESS RULES

* Failure of one source does **not** fail the job
* Partial outputs are allowed
* Each source has independent status:

  * ingested
  * failed
  * partial

Doc 1 and Doc 2 must reflect partial coverage honestly.

---

## 9. BOOSTER-SPECIFIC VALIDATION

### Deep Research Booster Failures

* Never block Doc 1 or Doc 2
* Add warning:

  > “External research expansion unavailable.”

### Booster Output Rules

* Booster may only:

  * add leads
  * add gaps
  * add suggested queries
* Booster must not:

  * add facts
  * modify Doc 0

---

## 10. LOGGING & OBSERVABILITY (MINIMAL)

The system must log:

* validation failures
* retry attempts
* downgrade triggers
* final job state

Logs are for debugging, not user display.

---

## 11. NON-GOALS (EXPLICIT)

This system does **not**:

* Score “truth”
* Resolve disputes
* Rank narratives
* Enforce completeness

---

## 12. TRANSCRIPT-AWARE VALIDATION RULES

Validation behavior changes based on **transcript provenance** for video sources.

---

### 12.1 If Transcript Exists (`transcript_grounded`)

| Validation Rule | Requirement |
|-----------------|-------------|
| Quote verification | Quotes MUST be verbatim matches |
| Timestamp grounding | Precise timestamps REQUIRED |
| Claim references | Claims MUST reference transcript segments |
| Confidence ceiling | High confidence available |

---

### 12.2 If Transcript Does NOT Exist (`video_only`)

| Validation Rule | Requirement |
|-----------------|-------------|
| Quote flagging | Quotes MUST be marked `unverified` |
| Confidence ceiling | Claims MUST be `low_confidence` maximum |
| Job completion | Job MUST still complete |
| Degradation disclosure | Warning MUST be added to Doc 0 and Doc 2 |

**CRITICAL:** Never fail job due to transcript absence alone.

---

### 12.3 If Captions Used (`caption_grounded`)

| Validation Rule | Requirement |
|-----------------|-------------|
| Quote accuracy | Quotes marked `approximate` |
| Confidence ceiling | Claims can be `medium_confidence` maximum |
| Timestamp grounding | Available but imprecise (±5 seconds) |
| Source note | Caption source MUST be noted in quote metadata |

---

### 12.4 Transcript Acquisition Retry Rules (LOCKED ORDER)

| Stage | Max Retries | On Failure |
|-------|-------------|------------|
| Supadata fetch | 1 | Try Whisper |
| Whisper fetch | 1 | Try YouTube captions |
| Captions fetch | 1 | Continue with `video_only` |
| Gemini stage | 1 | Fail stage, not job |

**Failure Escalation (LOCKED ORDER):**
1. Supadata fails → Try Whisper
2. Whisper fails → Try YouTube captions
3. Captions fail → Continue with `video_only` mode
4. Gemini fails → Mark source as `failed`, continue job with other sources

---

### 12.5 Provenance Validation (Hard Fail)

A **hard failure** occurs if:

* Video source has no `transcript_provenance` metadata
* `transcript_provenance.gemini_analysis_mode` is missing
* `transcript_provenance.verification_capabilities` is missing

This ensures downstream documents always know the reliability of their source material.

---

### 12.6 Confidence Ceiling Enforcement (Machine-Checked)

Confidence uses **CATEGORICAL values only**: `low`, `medium`, `high`

Do NOT use numeric values (0.0-1.0) or percentages.

| Analysis Mode | Max Confidence | Auto-Downgrade |
|---------------|----------------|----------------|
| transcript_grounded | high | No |
| caption_grounded | medium | Yes, if high |
| video_only | low | Yes, if medium or high |

If output exceeds mode ceiling:
1. Auto-downgrade to ceiling value
2. Add warning: "Confidence auto-downgraded from {original} to {ceiling}"

**RULE:** All specs must use low/medium/high — never 0.3, 0.7, etc.

---

### 12.7 Malformed Source Handling

If a source is malformed (invalid URL, deleted/private video, access denied):
1. Mark source as `failed` with explicit reason
2. Exclude from semantic extraction (no Gemini call)
3. Record in Doc 0 with failure_reason
4. Propagate degradation to Doc 1/2

Job continues with remaining valid sources.
**Job fails ONLY if no usable sources remain.**

---

## End of Validation & Retry Rules Specification (Draft v1)

---
