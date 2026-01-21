# Job State Machine Specification

> **Constitution:** `docs/authoritative/INDEX.md`
> This document is a **domain-specific orchestration spec** for job lifecycle. If anything conflicts with INDEX.md, INDEX.md wins.

**Purpose:** Definition of job lifecycle, status transitions, and failure handling.

**Status:** PRESCRIPTIVE — Claude Code implements to this spec.

---

## 1. Job Statuses

| Status | Description | Terminal? |
|--------|-------------|-----------|
| `pending` | Job created, not yet started | No |
| `acquiring_sources` | Fetching metadata and transcripts | No |
| `extracting` | Running semantic extraction per source | No |
| `validating` | Running validation checks on extractions | No |
| `synthesizing` | Cross-source synthesis (multi-source only) | No |
| `assembling` | Building Doc 0/1/2 | No |
| `completed` | All stages succeeded, artifacts ready | Yes |
| `completed_with_warnings` | Finished with degradation, artifacts ready | Yes |
| `failed` | Infrastructure failure, no artifacts | Yes |

### Status Invariants

- A job in a terminal status (`completed`, `completed_with_warnings`, `failed`) cannot transition to any other status
- `completed_with_warnings` is a SUCCESS state — artifacts are valid and usable
- `failed` means no usable output — this is rare

---

## 2. State Diagram

```
                              ┌─────────────────────────────────────────┐
                              │                                         │
                              ▼                                         │
┌─────────┐    job_start    ┌───────────────────┐                       │
│ pending │ ───────────────▶│ acquiring_sources │                       │
└─────────┘                 └───────────────────┘                       │
                                      │                                 │
                    ┌─────────────────┼─────────────────┐               │
                    │                 │                 │               │
                    ▼                 ▼                 ▼               │
              [all succeed]    [some fail]      [all fail]              │
                    │                 │                 │               │
                    │                 │                 ▼               │
                    │                 │          ┌──────────┐           │
                    │                 │          │  failed  │           │
                    │                 │          └──────────┘           │
                    │                 │                                 │
                    └────────┬────────┘                                 │
                             │                                          │
                             ▼                                          │
                      ┌──────────────┐                                  │
                      │  extracting  │                                  │
                      └──────────────┘                                  │
                             │                                          │
           ┌─────────────────┼─────────────────┐                        │
           │                 │                 │                        │
           ▼                 ▼                 ▼                        │
     [all succeed]    [some fail]      [all fail]                       │
           │                 │                 │                        │
           │                 │                 ▼                        │
           │                 │          ┌──────────┐                    │
           │                 │          │  failed  │                    │
           │                 │          └──────────┘                    │
           │                 │                                          │
           └────────┬────────┘                                          │
                    │                                                   │
                    ▼                                                   │
             ┌──────────────┐                                           │
             │  validating  │                                           │
             └──────────────┘                                           │
                    │                                                   │
                    │ (validation failures = warnings, not abort)       │
                    │                                                   │
                    ▼                                                   │
            ┌───────────────┐                                           │
            │ synthesizing  │◄──── (skip if single source)              │
            └───────────────┘                                           │
                    │                                                   │
                    ▼                                                   │
             ┌──────────────┐                                           │
             │  assembling  │                                           │
             └──────────────┘                                           │
                    │                                                   │
        ┌───────────┴───────────┐                                       │
        │                       │                                       │
        ▼                       ▼                                       │
┌───────────┐    ┌──────────────────────────┐                           │
│ completed │    │ completed_with_warnings  │                           │
└───────────┘    └──────────────────────────┘                           │
                                                                        │
                                                                        │
OPTIONAL EXTENSIONS (post-completion):                                  │
                                                                        │
┌───────────────────────┐      ┌─────────────────┐                      │
│ completed[_with_warn] │─────▶│ running_booster │──────────────────────┘
└───────────────────────┘      └─────────────────┘   (returns to completed state)
                                      
┌───────────────────────┐      ┌──────────────────┐
│ completed[_with_warn] │─────▶│ running_producer │──────────────────────┘
└───────────────────────┘      └──────────────────┘   (returns to completed state)
```

---

## 3. Transition Rules

### 3.1 `pending` → `acquiring_sources`

**Trigger:** Celery task `run_semantic_job` begins execution

**Actions:**
1. Update job status to `acquiring_sources`
2. Update `started_at` timestamp
3. For each source URL:
   - Fetch metadata (Supadata API)
   - Assign `source_id` (SRC_1, SRC_2, ...)
   - Attempt transcript acquisition (D1 chain)
   - Record `TranscriptProvenance`

**Failure Handling:**
- Single source fails metadata → Mark source as `failed`, continue with others
- Single source fails transcript → Set `video_only` mode, continue
- All sources fail metadata → Transition to `failed`

---

### 3.2 `acquiring_sources` → `extracting`

**Trigger:** All sources have been processed (success or degraded)

**Preconditions:**
- At least 1 source has usable identity (metadata resolved)
- Each source has `TranscriptProvenance` (even if `video_only`)

**Actions:**
1. Update job status to `extracting`
2. For each source with valid identity:
   - Build mode-specific prompt
   - Call Gemini
   - Store `SemanticExtractionResult`

**Failure Handling:**
- Single extraction fails → Retry once with constrained prompt
- Single extraction still fails → Mark source as `extraction_failed`, add warning, continue
- All extractions fail → Transition to `failed`

---

### 3.3 `extracting` → `validating`

**Trigger:** All extraction attempts complete

**Preconditions:**
- At least 1 source has `SemanticExtractionResult`

**Actions:**
1. Update job status to `validating`
2. For each extraction result, run V1-V9 checks
3. Record validation results per source

**Failure Handling:**
- Validation failure → Add warning, mark extraction as `degraded`
- Quote verification fails → Remove invalid quotes, add warning
- Confidence ceiling violated → Clamp to ceiling, add warning
- **Validation NEVER aborts the job**

---

### 3.4 `validating` → `synthesizing`

**Trigger:** All validations complete

**Preconditions:**
- At least 1 validated (or degraded-but-usable) extraction

**Skip Condition:**
- If exactly 1 source → Skip synthesis, go directly to `assembling`

**Actions:**
1. Update job status to `synthesizing`
2. Run cross-source synthesis prompt
3. Identify themes, tensions, conflicts across sources
4. Store `SynthesisResult`

**Failure Handling:**
- Synthesis fails → Retry once
- Synthesis still fails → Use individual extractions without cross-references, add warning

---

### 3.5 `synthesizing` → `assembling`

**Trigger:** Synthesis complete (or skipped for single-source)

**Actions:**
1. Update job status to `assembling`
2. Build Doc 0 (Source Ledger)
3. Build Doc 1 (Jump-Start Directions)
4. Build Doc 2 (Semantic Brief)
5. Generate markdown versions
6. Store in `artifacts` field

**Failure Handling:**
- Assembly fails → This is infrastructure failure → Transition to `failed`

---

### 3.6 `assembling` → `completed` or `completed_with_warnings`

**Trigger:** All documents assembled

**Decision Logic:**
```python
if len(job.warnings) == 0:
    status = "completed"
else:
    status = "completed_with_warnings"
```

**Actions:**
1. Update job status
2. Update `completed_at` timestamp
3. Calculate `processing_time`
4. Store final artifacts

---

### 3.7 `completed[_with_warnings]` → `running_booster`

**Trigger:** User requests booster via API (`POST /jobs/{id}/booster`)

**Preconditions:**
- Job is in `completed` or `completed_with_warnings` status
- Booster not already run for this job

**Actions:**
1. Update job status to `running_booster`
2. Run 4-stage booster pipeline
3. Augment Doc 1 with booster results
4. Return to previous completed status

**Failure Handling:**
- Booster fails → Add warning, return to previous completed status
- Booster does not abort the job

---

### 3.8 `completed[_with_warnings]` → `running_producer`

**Trigger:** User requests producer packet via API (`POST /jobs/{id}/producer`)

**Preconditions (Gating - V10):**
- Job is in `completed` or `completed_with_warnings` status
- Job has ≥4 sources
- At least 1 source has `confidence_ceiling = HIGH`
- Producer packet not already generated

**Actions:**
1. Update job status to `running_producer`
2. Run 4-stage producer pipeline
3. Store Doc 3 (Producer Packet)
4. Return to previous completed status

**Failure Handling:**
- Gating check fails → Return error, do not start pipeline
- Producer pipeline fails → Add warning, return to previous completed status

---

## 4. Failure Classification

### 4.1 Infrastructure Failures (Abort Job)

These cause transition to `failed`:

| Failure | Stage | Result |
|---------|-------|--------|
| Database unreachable | Any | `failed` |
| Redis/Celery down | Any | `failed` |
| All sources fail metadata | acquiring_sources | `failed` |
| All extractions fail | extracting | `failed` |
| Document assembly exception | assembling | `failed` |
| Zero usable sources after all stages | Any | `failed` |

### 4.2 Degradation Failures (Add Warning, Continue)

These add warnings but job continues:

| Failure | Stage | Warning Added |
|---------|-------|---------------|
| Single source metadata fails | acquiring_sources | `source_metadata_failed` |
| Transcript unavailable | acquiring_sources | `transcript_unavailable` |
| Single extraction fails after retry | extracting | `extraction_failed` |
| Validation check fails | validating | `validation_{check}_failed` |
| Quote verification fails | validating | `invalid_quotes_removed` |
| Confidence ceiling violated | validating | `confidence_clamped` |
| Synthesis fails after retry | synthesizing | `synthesis_failed_using_individual` |
| Booster fails | running_booster | `booster_failed` |
| Producer fails | running_producer | `producer_failed` |

---

## 5. Multi-Source Handling

### Source Counting Rules

```python
total_sources = len(job.source_urls)
acquired_sources = len([s for s in sources if s.metadata_resolved])
extracted_sources = len([s for s in sources if s.extraction_result is not None])
valid_sources = len([s for s in sources if s.validation_passed or s.validation_degraded])
```

### Continuation Thresholds

| Stage | Minimum to Continue | If Below Minimum |
|-------|--------------------|--------------------|
| acquiring_sources | 1 acquired | `failed` |
| extracting | 1 extracted | `failed` |
| validating | 1 valid or degraded | `failed` |
| synthesizing | 1 source (skip synthesis) | N/A |

### Example Scenarios

**Scenario A: 5 sources, 3 fail transcript**
- 2 sources: `transcript_grounded`
- 3 sources: `video_only`
- Result: `completed_with_warnings` (3 warnings for transcript unavailable)

**Scenario B: 5 sources, 3 fail extraction**
- 2 sources: valid extractions
- 3 sources: extraction failed
- Result: `completed_with_warnings` (3 warnings, synthesis uses 2 sources)

**Scenario C: 5 sources, 5 fail extraction**
- 0 usable extractions
- Result: `failed`

**Scenario D: 1 source, transcript unavailable**
- 1 source: `video_only` mode
- Result: `completed_with_warnings` (1 warning, thin output acceptable)

---

## 6. Warning Structure

```python
@dataclass
class JobWarning:
    code: str                    # e.g., "transcript_unavailable"
    stage: str                   # e.g., "acquiring_sources"
    source_id: Optional[str]     # e.g., "SRC_2" (if source-specific)
    message: str                 # Human-readable description
    timestamp: datetime
    details: Optional[dict]      # Additional context
```

### Standard Warning Codes

| Code | Stage | Description |
|------|-------|-------------|
| `source_metadata_failed` | acquiring_sources | Could not fetch metadata for source |
| `transcript_unavailable` | acquiring_sources | All transcript methods failed |
| `transcript_degraded` | acquiring_sources | Using captions instead of full transcript |
| `extraction_failed` | extracting | Extraction failed after retry |
| `extraction_thin` | extracting | Extraction produced minimal output |
| `validation_schema_failed` | validating | JSON schema validation failed |
| `validation_quotes_removed` | validating | Invalid quotes removed |
| `validation_confidence_clamped` | validating | Confidence exceeded ceiling |
| `validation_grounding_failed` | validating | Missing source_ids |
| `synthesis_failed` | synthesizing | Cross-source synthesis failed |
| `booster_failed` | running_booster | Booster pipeline failed |
| `producer_gating_failed` | running_producer | Did not meet Doc 3 requirements |
| `producer_failed` | running_producer | Producer pipeline failed |

---

## 7. Database Fields

### Jobs Table Updates

```sql
-- Existing fields
status TEXT NOT NULL DEFAULT 'pending'

-- Add these fields if not present
started_at TIMESTAMP
completed_at TIMESTAMP
processing_time_seconds INTEGER
warning_count INTEGER DEFAULT 0
warnings JSONB DEFAULT '[]'
```

### Status Enum Values

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    ACQUIRING_SOURCES = "acquiring_sources"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SYNTHESIZING = "synthesizing"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    RUNNING_BOOSTER = "running_booster"
    RUNNING_PRODUCER = "running_producer"
```

---

## 8. Implementation Notes

### Status Update Pattern

```python
async def update_job_status(job_id: str, new_status: JobStatus, warning: Optional[JobWarning] = None):
    """Atomic status update with optional warning."""
    async with db.transaction():
        job = await db.jobs.get(job_id)
        
        # Validate transition
        if job.status in TERMINAL_STATUSES:
            raise InvalidTransitionError(f"Cannot transition from terminal status {job.status}")
        
        # Update status
        job.status = new_status
        
        # Add warning if provided
        if warning:
            job.warnings.append(warning)
            job.warning_count += 1
        
        # Set timestamps
        if new_status == JobStatus.ACQUIRING_SOURCES:
            job.started_at = datetime.utcnow()
        elif new_status in TERMINAL_STATUSES:
            job.completed_at = datetime.utcnow()
            job.processing_time_seconds = (job.completed_at - job.started_at).seconds
        
        await db.jobs.update(job)
```

### Transition Validation

```python
VALID_TRANSITIONS = {
    JobStatus.PENDING: [JobStatus.ACQUIRING_SOURCES],
    JobStatus.ACQUIRING_SOURCES: [JobStatus.EXTRACTING, JobStatus.FAILED],
    JobStatus.EXTRACTING: [JobStatus.VALIDATING, JobStatus.FAILED],
    JobStatus.VALIDATING: [JobStatus.SYNTHESIZING, JobStatus.ASSEMBLING],  # Skip synthesis for single source
    JobStatus.SYNTHESIZING: [JobStatus.ASSEMBLING],
    JobStatus.ASSEMBLING: [JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_WARNINGS, JobStatus.FAILED],
    JobStatus.COMPLETED: [JobStatus.RUNNING_BOOSTER, JobStatus.RUNNING_PRODUCER],
    JobStatus.COMPLETED_WITH_WARNINGS: [JobStatus.RUNNING_BOOSTER, JobStatus.RUNNING_PRODUCER],
    JobStatus.RUNNING_BOOSTER: [JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_WARNINGS],
    JobStatus.RUNNING_PRODUCER: [JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_WARNINGS],
    JobStatus.FAILED: [],  # Terminal
}
```

---

## 9. Invariants (Always True)

1. **Terminal is terminal:** Once `completed`, `completed_with_warnings`, or `failed`, no further transitions except booster/producer extensions
2. **Warnings accumulate:** Warnings are never removed, only added
3. **At least one source:** If we reach `extracting`, at least 1 source was acquired
4. **Artifacts on completion:** If status is `completed` or `completed_with_warnings`, Doc 0/1/2 exist
5. **Failed means no output:** If status is `failed`, no artifacts are available
6. **Booster/Producer are extensions:** They don't change the core completion status

---

**END OF SPECIFICATION**
