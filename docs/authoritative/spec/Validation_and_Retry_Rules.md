# Validation and Retry Rules

**Purpose:** Defines how the system validates outputs, handles failures, and manages retries.
**Authority:** These rules are non-negotiable. Validation failures must be handled as specified.

---

## Validation Philosophy

### Core Principles

1. **Fail gracefully, not silently** — Problems must be visible, not hidden
2. **Prefer thin over hallucinated** — Sparse accurate output beats dense fabricated output
3. **Continue when possible** — One failure shouldn't kill the whole job
4. **Log everything** — Every validation failure is recorded

### Validation Timing

```
SOURCE IDENTITY → EXTRACTION → [VALIDATION] → SYNTHESIS → ASSEMBLY
                                    ↑
                          Validation happens here,
                          per-source, before synthesis
```

---

## Validation Checks

### V1: JSON Schema Validation

**When:** After every LLM call that expects JSON output

**Check:** Response parses as valid JSON matching expected schema

**On Failure:**
- Severity: **HARD FAIL**
- Action: Retry once with same prompt
- If retry fails: Mark source as `failed`, continue job with warning

**Implementation:**
```python
try:
    data = json.loads(response)
    validated = PydanticModel(**data)
except json.JSONDecodeError:
    # HARD FAIL - retry
except pydantic.ValidationError:
    # HARD FAIL - retry
```

---

### V2: Source ID Consistency

**When:** After extraction, before synthesis

**Check:** All extracted items reference valid `source_id` from current job

**On Failure:**
- Severity: **HARD FAIL**
- Action: Retry once
- If retry fails: Remove invalid items, log warning, continue

**Implementation:**
```python
valid_source_ids = {s.source_id for s in job.sources}
for item in extraction.key_points:
    for sid in item.source_ids:
        if sid not in valid_source_ids:
            # HARD FAIL - invalid source reference
```

---

### V3: Confidence Ceiling Enforcement

**When:** After extraction, before synthesis

**Check:** No item has confidence higher than source's ceiling

**On Failure:**
- Severity: **SOFT FAIL**
- Action: Auto-downgrade confidence to ceiling, log warning
- Never retry for this — just fix and continue

**Implementation:**
```python
ceiling_map = {"high": 3, "medium": 2, "low": 1}

if ceiling_map[item.confidence] > ceiling_map[source.confidence_ceiling]:
    item.confidence = source.confidence_ceiling
    warnings.append(f"Downgraded {item.id} from {original} to {source.confidence_ceiling}")
```

**Ceiling Reference:**
| Mode | Ceiling |
|------|---------|
| `transcript_grounded` | high |
| `caption_grounded` | medium |
| `video_only` | low |
| `text_provided` | medium |
| `ocr_extracted` | medium |
| `article_fetched` | high |

---

### V4: Quote Verification

**When:** After extraction, for modes that allow quotes

**Check:** Extracted quotes exist in source text

**On Failure:**
- Severity: **SOFT FAIL**
- Action: Mark quote as `unverified`, do NOT remove, continue

**Implementation:**
```python
def verify_quote(quote_text: str, source_text: str) -> str:
    # Exact match
    if quote_text in source_text:
        return "verified"
    
    # Fuzzy match (80% similarity threshold)
    ratio = fuzz.ratio(quote_text.lower(), best_match.lower())
    if ratio >= 80:
        return "partial"
    
    return "unverified"
```

**Verification Statuses:**
| Status | Meaning | Action |
|--------|---------|--------|
| `verified` | Exact or near-exact match found | Keep as-is |
| `partial` | Similar text found (80%+ match) | Keep, flag |
| `unverified` | No match found | Keep, flag, warn |

**Note:** Unverified quotes are NOT removed. They are flagged and the user decides.

---

### V5: Quote Permission Check

**When:** After extraction

**Check:** Quotes only exist for modes that allow them

**On Failure:**
- Severity: **HARD FAIL**
- Action: Remove quotes, convert to observations if possible, log error

**Modes That Allow Quotes:**
- `transcript_grounded` ✅
- `caption_grounded` ✅
- `article_fetched` ✅

**Modes That Forbid Quotes:**
- `video_only` ❌
- `text_provided` ❌
- `ocr_extracted` ❌

**Implementation:**
```python
QUOTE_ALLOWED_MODES = {"transcript_grounded", "caption_grounded", "article_fetched"}

if source.analysis_mode not in QUOTE_ALLOWED_MODES:
    if len(extraction.quotes) > 0:
        # HARD FAIL - quotes not allowed
        # Convert to observations or remove
```

---

### V6: Timestamp Validation

**When:** After extraction, for video sources

**Check:** Timestamps are within source duration

**On Failure:**
- Severity: **SOFT FAIL**
- Action: Remove invalid timestamp (set to null), log warning

**Implementation:**
```python
if source.duration_seconds and item.timestamp_seconds:
    if item.timestamp_seconds > source.duration_seconds:
        item.timestamp_seconds = None
        item.timestamp = None
        warnings.append(f"Removed invalid timestamp from {item.id}")
```

---

### V7: Empty Output Check

**When:** After extraction

**Check:** Extraction produced minimum required content

**On Failure:**
- Severity: **SOFT FAIL**
- Action: Retry once with constrained prompt, then accept thin output

**Minimum Thresholds:**
| Field | Minimum | On Miss |
|-------|---------|---------|
| `key_points` | 1 | Retry once |
| `claims` | 0 | Accept |
| `quotes` (if allowed) | 0 | Accept |
| `themes` | 0 | Accept (synthesis may find) |

**Note:** Empty output is acceptable if the source genuinely has no relevant content. The prompt explicitly permits this.

---

### V8: Provenance Chain Validation

**When:** During assembly, before finalizing Doc 2

**Check:** All references trace back to Doc 0

**On Failure:**
- Severity: **HARD FAIL**
- Action: Remove broken references, log error

**Chain Requirements:**
```
Theme.supporting_key_points → must exist in Doc 2 key_points
KeyPoint.source_ids → must exist in Doc 0 sources
KeyPoint.supporting_evidence.quotes → must exist in Doc 0 indexes.quotes
Tension.sources_involved → must exist in Doc 0 sources
```

---

### V9: Cardinality Check

**When:** After assembly

**Check:** Output meets target cardinality ranges

**On Failure:**
- Severity: **WARNING ONLY**
- Action: Log warning, continue (targets are goals, not requirements)

**Targets:**
| Doc | Field | Min | Target | Max |
|-----|-------|-----|--------|-----|
| Doc 1 | gaps | 3 | 5-8 | 15 |
| Doc 1 | research_directions | 2 | 4-6 | 10 |
| Doc 1 | top_three_next_steps | 3 | 3 | 3 |
| Doc 2 | themes | 2 | 4-6 | 10 |
| Doc 2 | key_points | 5 | 8-15 | 25 |

---

### V10: Doc 3 Gating Validation

**When:** Before generating Producer Packet

**Check:** All gating requirements met

**On Failure:**
- Severity: **HARD FAIL**
- Action: Reject request, return clear error message

**Requirements:**
```python
def can_generate_producer_packet(job) -> tuple[bool, str]:
    if len(job.sources) < 4:
        return False, f"Need 4+ sources, have {len(job.sources)}"
    
    high_confidence = sum(1 for s in job.sources if s.confidence_ceiling == "high")
    if high_confidence < 1:
        return False, "Need at least 1 high-confidence source"
    
    if job.status != "completed":
        return False, f"Job must be completed, currently {job.status}"
    
    return True, "OK"
```

---

## Retry Rules

### Retry Limits

| Stage | Max Retries | Backoff |
|-------|-------------|---------|
| Transcript acquisition (Supadata) | 1 | None (try next method) |
| Transcript acquisition (Whisper) | 1 | None (try next method) |
| Transcript acquisition (Captions) | 1 | None (degrade to video_only) |
| Semantic extraction | 1 | None |
| Synthesis | 1 | None |
| Assembly | 0 | N/A (deterministic) |
| Booster stages | 1 each | None |
| Producer stages | 1 each | None |

### Retry Prompt Modification

On retry, add constraint block to prompt:

```
RETRY CONTEXT:
Previous attempt failed validation.
Error: {validation_error}

Be MORE conservative:
- Prefer fewer, higher-quality items over many low-quality items
- If uncertain, omit rather than guess
- Empty arrays are acceptable
```

### No Retry Cascade

If a retry fails, do NOT retry again. Accept degraded output or fail the stage.

```python
MAX_RETRIES = 1

for attempt in range(MAX_RETRIES + 1):
    result = call_llm(prompt)
    if validate(result):
        return result
    if attempt < MAX_RETRIES:
        prompt = add_retry_context(prompt, validation_error)
    else:
        return handle_final_failure(result)
```

---

## Failure Severity Levels

### HARD FAIL

**Definition:** Validation failure that prevents proceeding without fix

**Actions:**
1. Retry once (if retries available)
2. If retry fails: 
   - For single source: mark source failed, continue job
   - For synthesis: fail stage, produce degraded output
   - For assembly: should not happen (deterministic)

**Examples:**
- Invalid JSON from LLM
- Source ID doesn't exist
- Quotes in no-quote mode

### SOFT FAIL

**Definition:** Validation failure that can be auto-corrected

**Actions:**
1. Apply auto-correction
2. Log warning
3. Continue processing

**Examples:**
- Confidence exceeds ceiling → downgrade
- Quote not found in source → mark unverified
- Timestamp out of range → remove timestamp

### WARNING

**Definition:** Non-ideal state that doesn't require action

**Actions:**
1. Log warning
2. Continue processing
3. Surface in job warnings

**Examples:**
- Below target cardinality
- Low verification rate
- High percentage of unverified quotes

---

## Stage-Specific Failure Handling

### Source Identity Stage

| Failure | Handling |
|---------|----------|
| Can't fetch metadata | Use URL as title, log warning |
| Invalid URL | Fail source, continue job |
| All sources invalid | Fail job |

### Transcript Acquisition

| Failure | Handling |
|---------|----------|
| Supadata fails | Try Whisper |
| Whisper fails | Try YouTube captions |
| All methods fail | Continue with `video_only` mode |
| Non-video source | N/A (skip transcript acquisition) |

### Semantic Extraction

| Failure | Handling |
|---------|----------|
| Invalid JSON | Retry once |
| Empty extraction | Retry once, then accept |
| Invalid source refs | Retry once, then remove invalid |
| Exceeds ceiling | Auto-downgrade |

### Validation

| Failure | Handling |
|---------|----------|
| Quote not found | Mark unverified, continue |
| Quotes in wrong mode | Remove/convert, log error |
| Timestamp invalid | Remove timestamp |
| Broken provenance | Remove broken refs |

### Synthesis

| Failure | Handling |
|---------|----------|
| Invalid JSON | Retry once |
| No cross-source themes | Accept (may be single source) |
| Conflicting synthesis | Log, keep both interpretations |

### Assembly

| Failure | Handling |
|---------|----------|
| Missing required field | Use default/empty |
| Template error | Log error, return raw JSON |

---

## Error Logging Format

All validation failures must be logged with:

```json
{
  "timestamp": "ISO-8601",
  "job_id": "string",
  "stage": "string",
  "source_id": "string | null",
  "validation_check": "V1 | V2 | V3 | ...",
  "severity": "hard_fail | soft_fail | warning",
  "message": "string",
  "details": {},
  "action_taken": "string",
  "retry_attempted": "boolean"
}
```

---

## Job Status Based on Failures

| Scenario | Final Status |
|----------|--------------|
| All validations pass | `completed` |
| Soft fails only | `completed` (warnings in job.warnings) |
| Some sources hard fail, others succeed | `completed_with_warnings` |
| Synthesis hard fails after retry | `completed_with_warnings` (degraded output) |
| All sources hard fail | `failed` |
| Assembly fails | `failed` |

---

## Validation Summary Table

| Check | ID | Severity | Auto-Correct | Retry |
|-------|-----|----------|--------------|-------|
| JSON Schema | V1 | Hard | No | Yes |
| Source ID Consistency | V2 | Hard | No | Yes |
| Confidence Ceiling | V3 | Soft | Yes (downgrade) | No |
| Quote Verification | V4 | Soft | Yes (flag) | No |
| Quote Permission | V5 | Hard | Partial (convert) | No |
| Timestamp Range | V6 | Soft | Yes (remove) | No |
| Empty Output | V7 | Soft | No | Yes |
| Provenance Chain | V8 | Hard | Yes (remove) | No |
| Cardinality | V9 | Warning | No | No |
| Doc 3 Gating | V10 | Hard | No | No |

---

**END OF VALIDATION AND RETRY RULES**
