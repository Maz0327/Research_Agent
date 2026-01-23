# Iteration Loop Baseline Contracts Report

**Generated:** 2026-01-23 11:54
**Purpose:** Document existing baseline contracts for implementing Iteration Loop feature

---

## Executive Summary

Located all baseline contracts needed for Iteration Loop implementation. System uses:
- **Job Schema**: Pydantic models with JSONB storage in Supabase
- **Artifact Keys**: Storage paths (`doc_0_path`, `doc_1_path`, `doc_2_path`) + inline data fallback
- **Store Methods**: `get_job()`, `update_job()` with atomic JSONB operations
- **Pipeline**: Semantic extraction worker produces Doc 0/1/2 via document assembly stage

---

## 1. Job Schema Model

### Location
- **Primary Model**: `/Users/maz/Documents/GitHub/Research_Agent/backend/models/job_record.py`
- **API Models**: `/Users/maz/Documents/GitHub/Research_Agent/backend/models/job.py`

### Artifacts Schema (lines 8-40 in job_record.py)

```python
class Artifacts(BaseModel):
    """Artifacts associated with a job."""

    # SEMANTIC PIPELINE - Doc 0/1/2/3
    # Inline document data (for backward compatibility)
    source_ledger: Optional[dict[str, Any]] = Field(None, description="Doc 0 - Source Ledger (inline)")
    jump_start: Optional[dict[str, Any]] = Field(None, description="Doc 1 - Jump-Start Directions (inline)")
    semantic_brief: Optional[dict[str, Any]] = Field(None, description="Doc 2 - Semantic Research Brief (inline)")
    semantic_extractions: Optional[list[dict[str, Any]]] = Field(None, description="Per-source extractions")

    # Storage paths (lazy loading - frontend fetches via API)
    doc_0_path: Optional[str] = Field(None, description="Storage path for Source Ledger")
    doc_1_path: Optional[str] = Field(None, description="Storage path for Jump-Start")
    doc_2_path: Optional[str] = Field(None, description="Storage path for Semantic Brief")
    doc_3_path: Optional[str] = Field(None, description="Storage path for Producer Packet")

    # Artifact Manifest (Option B storage strategy)
    artifact_manifest: Optional[dict[str, Any]] = Field(
        None, description="Manifest of available artifacts with storage paths"
    )

    # Booster (Doc 1 expansion)
    booster_output: Optional[dict[str, Any]] = Field(None, description="Booster output for Doc 1 expansion")
    booster_expansion_md: Optional[str] = Field(None, description="Booster markdown for Doc 1")

    # Producer Packet (Doc 3)
    producer_packet: Optional[dict[str, Any]] = Field(None, description="Doc 3 - Producer Packet (inline)")
    producer_packet_md: Optional[str] = Field(None, description="Doc 3 markdown output")
```

### JobRecord Model (lines 90-164)

```python
class JobRecord(BaseModel):
    """Complete job record for storage."""

    # Core identifiers
    job_id: str
    user_id: Optional[str]
    title: Optional[str]
    pipeline: str = Field(default="investigation")
    niche: Optional[str]

    # Timestamps
    created_at: datetime
    stage_started_at: Optional[datetime]

    # Status and progress (main pipeline)
    status: str = Field(default="queued")  # queued, running, disambiguating, completed, failed, cancelled
    stage: Optional[str]
    progress_percent: int = Field(default=0, ge=0, le=100)
    error: Optional[str]
    warnings: list[str] = Field(default_factory=list)

    # Booster tracking (separate from main pipeline status)
    booster_status: Optional[str]  # queued, running, completed, failed
    booster_started_at: Optional[datetime]
    booster_completed_at: Optional[datetime]
    booster_error: Optional[str]
    booster_progress_percent: Optional[int]

    # Producer tracking (separate from main pipeline status)
    producer_status: Optional[str]  # queued, running, completed, failed
    producer_started_at: Optional[datetime]
    producer_completed_at: Optional[datetime]
    producer_error: Optional[str]
    producer_progress_percent: Optional[int]

    # Configuration
    config_json: dict[str, Any] = Field(default_factory=dict)

    # Metrics
    total_sources: Optional[int]
    total_claims: Optional[int]
    api_costs: Optional[dict[str, Any]]

    # Artifacts and outputs
    artifacts: Optional[Artifacts]
    outputs: Optional[Outputs]
```

### Key Artifact Keys (EXACT strings to use)

**Storage Paths** (primary):
- `artifacts.doc_0_path` — Storage path for Source Ledger
- `artifacts.doc_1_path` — Storage path for Jump-Start Directions
- `artifacts.doc_2_path` — Storage path for Semantic Brief
- `artifacts.doc_3_path` — Storage path for Producer Packet

**Inline Data** (fallback/legacy):
- `artifacts.source_ledger` — Doc 0 inline dict
- `artifacts.jump_start` — Doc 1 inline dict
- `artifacts.semantic_brief` — Doc 2 inline dict
- `artifacts.producer_packet` — Doc 3 inline dict

**Metadata**:
- `artifacts.semantic_extractions` — List of per-source extraction results
- `artifacts.artifact_manifest` — Manifest with storage paths and availability

---

## 2. Store Methods

### Location
- **Interface**: `/Users/maz/Documents/GitHub/Research_Agent/backend/state/__init__.py`
- **Implementation**: `/Users/maz/Documents/GitHub/Research_Agent/backend/state/impl/supabase_store.py`

### get_job() Function (lines 55-66 in __init__.py)

```python
def get_job(job_id: str) -> JobRecord | None:
    """
    Get a job by ID.

    Args:
        job_id: Job identifier

    Returns:
        JobRecord if found, None otherwise
    """
    store = get_job_store()
    return store.get_job(job_id)
```

**Implementation Details** (lines 229-275 in supabase_store.py):
- Validates UUID format
- HTTP GET to `/rest/v1/jobs?id=eq.{job_id}`
- Returns `None` if not found (404)
- Parses JSONB fields (`artifacts`, `outputs`, `config_json`)
- Handles corrupted JSONB (list/string) with `_normalize_jsonb_field()`

### update_job() Function (lines 69-156 in __init__.py)

```python
def update_job(
    job_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress_percent: int | None = None,
    title: str | None = None,
    error: str | None = None,
    partial_outputs: dict | None = None,
    partial_artifacts: dict | None = None,
    warnings_append: list[str] | None = None,
    config_json: dict | None = None,
    artifacts: Artifacts | None = None,
    warnings: list[str] | None = None,
    interpretations: list[dict] | None = None,
    selected_interpretations: list[int] | None = None,
    # Booster tracking fields
    booster_status: str | None = None,
    booster_started_at: datetime | None = None,
    booster_completed_at: datetime | None = None,
    booster_error: str | None = None,
    booster_progress_percent: int | None = None,
    # Producer tracking fields
    producer_status: str | None = None,
    producer_started_at: datetime | None = None,
    producer_completed_at: datetime | None = None,
    producer_error: str | None = None,
    producer_progress_percent: int | None = None,
) -> JobRecord | None:
```

**Key Features**:
- **Atomic Operations**: Uses `partial_artifacts` for JSONB merge (prevents race conditions)
- **Full Replacement**: Uses `artifacts` for complete replacement
- **Warning Guard**: Cannot mix `artifacts=` with atomic updates (`partial_artifacts`, `partial_outputs`, `warnings_append`)
- **Separate Tracking**: Booster and Producer have independent status fields (never modify main `job.status`)

**Implementation Routes** (lines 277-399 in supabase_store.py):
1. **Atomic Path**: When using `partial_*` or booster/producer fields → `_update_job_atomic()`
2. **Simple Path**: Basic field updates → `_update_job_simple()`

**Critical Guard** (lines 357-362):
```python
if needs_atomic and artifacts is not None:
    raise ValueError(
        "artifacts= cannot be used with atomic updates. "
        "Use partial_artifacts= instead for atomic merge semantics."
    )
```

---

## 3. Semantic Pipeline Worker Task

### Location
- **Worker**: `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py`
- **Document Assembly**: `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/document_assembly.py`
- **Completion Stage**: `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/initialization.py`

### Entry Point: run_research_job() (lines 52-155 in worker.py)

```python
@celery_app.task(name="backend.worker.run_research_job")
def run_research_job(
    job_id: str,
    topic: str,
    slack_payload: Optional[dict] = None,  # DEPRECATED
    enable_parallel: bool = True,  # DEPRECATED
) -> dict:
    """
    Research job task - USER-SUPPLIED SOURCES ONLY (New Pipeline).

    Pipeline stages:
    1. Source Identity (resolve analysis modes from user inputs)
    2. Semantic Extraction (Gemini - per source, isolated)
    3. Semantic Validation (confidence ceilings, quote verification)
    4. Gap Analysis (identify missing coverage)
    5. Semantic Synthesis (cross-source themes, tensions)
    6. Document Assembly (Doc 20/21/22)
    7. Completion (artifact manifest, Supabase storage)
    """
```

### Pipeline Execution: _run_mixed_input_job() (lines 157-369)

**Stage Sequence**:
```python
# Stage 1: Build source identity packages
update_job(job_id, status="running", stage="source_identity", progress_percent=5)
# ... process videos, articles, text inputs, screenshots

# Stage 2: Semantic Extraction
update_job(job_id, stage="semantic_extraction", progress_percent=20)
run_stage_with_recovery(stage_semantic_extraction, ctx, "semantic_extraction")

# Stage 3: Semantic Validation
update_job(job_id, stage="semantic_validation", progress_percent=35)
run_stage_with_recovery(stage_semantic_validation, ctx, "semantic_validation")

# Stage 4: Gap Analysis
update_job(job_id, stage="gap_analysis", progress_percent=50)
run_stage_with_recovery(stage_gap_analysis, ctx, "gap_analysis")

# Stage 5: Semantic Synthesis
update_job(job_id, stage="semantic_synthesis", progress_percent=65)
run_stage_with_recovery(stage_semantic_synthesis, ctx, "semantic_synthesis")

# Stage 6: Document Assembly
update_job(job_id, stage="document_assembly", progress_percent=80)
run_stage_with_recovery(stage_document_assembly, ctx, "document_assembly")

# Stage 7: Completion (stores docs in artifacts)
update_job(job_id, stage="completion", progress_percent=95)
return stage_10_completion(ctx)
```

### Document Assembly Stage

**Location**: `backend/pipeline/stages/document_assembly.py`

**Key Functions**:
1. `build_source_ledger()` (lines 51-150+) — Constructs Doc 0
2. `build_jump_start()` — Constructs Doc 1
3. `build_semantic_brief()` — Constructs Doc 2

**Assembly Order** (per RASS Section 4.5):
```python
# 1. DOC 0 — Source Ledger
source_ledger = build_source_ledger(topic, sources, extractions)

# 2. DOC 1 — Jump-Start Directions
jump_start = build_jump_start(source_ledger, extractions, gaps)

# 3. DOC 2 — Semantic Research Brief
semantic_brief = build_semantic_brief(source_ledger, extractions, themes, tensions)
```

### Completion Stage: stage_10_completion()

**Location**: `backend/pipeline/stages/initialization.py` (lines 24-74)

**Storage Strategy**:
1. **Try Storage Upload** (lines 24-74):
   - Uploads Doc 0/1/2/3 to Supabase Storage
   - Returns storage paths: `{doc_0_path, doc_1_path, doc_2_path, doc_3_path}`
   - Falls back to inline if storage unavailable

2. **Build Inline Artifacts** (lines 77-112):
   - Fallback for when storage is unavailable
   - Stores full document data in `artifacts.source_ledger`, `artifacts.jump_start`, etc.

**Code Pattern** (lines 36-68):
```python
# Doc 0: Source Ledger
if ctx.outputs.get("source_ledger"):
    doc_data = {
        "data": ctx.outputs["source_ledger"],
        "markdown": ctx.outputs.get("source_ledger_md"),
    }
    paths["doc_0_path"] = storage_client.upload_document(ctx.job_id, "doc_0", doc_data)

# Doc 1: Jump-Start Directions
if ctx.outputs.get("jump_start"):
    doc_data = {
        "data": ctx.outputs["jump_start"],
        "markdown": ctx.outputs.get("jump_start_md"),
    }
    paths["doc_1_path"] = storage_client.upload_document(ctx.job_id, "doc_1", doc_data)

# Doc 2: Semantic Brief
if ctx.outputs.get("semantic_brief"):
    doc_data = {
        "data": ctx.outputs["semantic_brief"],
        "markdown": ctx.outputs.get("semantic_brief_md"),
    }
    paths["doc_2_path"] = storage_client.upload_document(ctx.job_id, "doc_2", doc_data)
```

**Final Artifacts Update**:
```python
update_job(
    job_id,
    status="completed",
    progress_percent=100,
    artifacts={
        "doc_0_path": "documents/{job_id}/doc_0.json",
        "doc_1_path": "documents/{job_id}/doc_1.json",
        "doc_2_path": "documents/{job_id}/doc_2.json",
        "semantic_extractions": [extraction.to_dict() for extraction in extractions],
    }
)
```

---

## Implementation Patterns for Iteration Loop

### Pattern 1: Read Existing Baseline Artifacts

```python
# Get job
job = get_job(job_id)
if not job:
    raise ValueError(f"Job {job_id} not found")

# Get artifacts
artifacts = job.artifacts if hasattr(job, "artifacts") else None
if not artifacts:
    raise ValueError("No artifacts found")

# Option A: Read from storage paths (preferred)
doc_0_path = artifacts.doc_0_path
doc_1_path = artifacts.doc_1_path
doc_2_path = artifacts.doc_2_path

if doc_0_path:
    storage_client = get_storage_client()
    doc_0_data = storage_client.download_document(doc_0_path)
    # Note: Storage wraps docs in {"data": {...}, "markdown": "..."}
    baseline_doc_0 = doc_0_data["data"] if "data" in doc_0_data else doc_0_data

# Option B: Read inline (fallback)
baseline_doc_0 = artifacts.source_ledger
baseline_doc_1 = artifacts.jump_start
baseline_doc_2 = artifacts.semantic_brief
```

### Pattern 2: Store Iteration Artifacts (Atomic Merge)

```python
# CORRECT: Use partial_artifacts for atomic merge
update_job(
    job_id,
    partial_artifacts={
        "iteration_1_doc_0_path": "documents/{job_id}/iterations/iter_1/doc_0.json",
        "iteration_1_doc_1_path": "documents/{job_id}/iterations/iter_1/doc_1.json",
        "iteration_1_doc_2_path": "documents/{job_id}/iterations/iter_1/doc_2.json",
        "iteration_history": [
            {
                "iteration_num": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "baseline_snapshot": {"doc_0_path": doc_0_path, "doc_1_path": doc_1_path},
                "iteration_snapshot": {"doc_0_path": "...", "doc_1_path": "..."},
            }
        ],
    }
)

# WRONG: Don't use artifacts= with existing data (will overwrite)
# update_job(job_id, artifacts=Artifacts(doc_0_path=...))  # ❌ Loses existing data
```

### Pattern 3: Append Warnings (Atomic)

```python
# CORRECT: Use warnings_append for atomic array append
update_job(
    job_id,
    warnings_append=[
        "Iteration 1: Some key points from baseline lost semantic coherence",
        "Iteration 1: New contradictions detected in source SRC_5",
    ]
)

# WRONG: Don't fetch-modify-store manually (race condition)
# job = get_job(job_id)
# job.warnings.extend([...])  # ❌ Lost updates if another worker modifies
# update_job(job_id, warnings=job.warnings)
```

### Pattern 4: Track Iteration State Separately

```python
# Follow booster/producer pattern: separate status fields
update_job(
    job_id,
    # DO NOT modify job.status (stays "completed")
    iteration_status="running",  # New field: running, completed, failed
    iteration_started_at=datetime.now(timezone.utc),
    iteration_progress_percent=25,
    partial_artifacts={
        "current_iteration": 1,
        "iteration_config": {
            "prompt": "Focus more on economic impacts",
            "preserve_baseline": True,
        },
    }
)
```

---

## Critical Implementation Notes

### 1. Storage vs Inline Strategy
- **Preferred**: Use storage paths (`doc_0_path`, `doc_1_path`, `doc_2_path`)
- **Fallback**: Use inline data (`source_ledger`, `jump_start`, `semantic_brief`)
- **Check Both**: Always check storage path first, fall back to inline if missing
- **Unwrapping**: Storage returns `{"data": {...}, "markdown": "..."}` — extract `data` field

### 2. Atomic Operations
- **Use `partial_artifacts`** for merging new keys without overwriting existing
- **Use `warnings_append`** for appending warnings without race conditions
- **Never use `artifacts=`** when other atomic operations are in the same call
- **ValidationError**: Guard will raise if mixing `artifacts=` with `partial_artifacts`

### 3. Status Tracking Pattern
- **Main Pipeline**: `job.status`, `job.stage`, `job.progress_percent`
- **Booster**: `job.booster_status`, `job.booster_progress_percent` (independent)
- **Producer**: `job.producer_status`, `job.producer_progress_percent` (independent)
- **Iteration**: Should follow same pattern — `job.iteration_status`, `job.iteration_progress_percent`
- **NEVER**: Modify `job.status` from auxiliary tasks (booster/producer/iteration)

### 4. Document Storage Paths Pattern
```
Baseline:
  documents/{job_id}/doc_0.json
  documents/{job_id}/doc_1.json
  documents/{job_id}/doc_2.json

Iterations (proposed):
  documents/{job_id}/iterations/iter_1/doc_0.json
  documents/{job_id}/iterations/iter_1/doc_1.json
  documents/{job_id}/iterations/iter_1/doc_2.json
  documents/{job_id}/iterations/iter_2/doc_0.json
  ...
```

### 5. Supabase Storage Client
- **Get Client**: `from backend.integrations.supabase_storage import get_storage_client`
- **Upload**: `storage_client.upload_document(job_id, "doc_key", doc_data)`
- **Download**: `storage_client.download_document(doc_path)`
- **Availability**: Check `if storage_client:` before use (may be `None` if not configured)

---

## Unresolved Questions

1. **Iteration State Schema**: Should we add `iteration_status`, `iteration_started_at`, etc. as new JobRecord fields? Or track in `config_json`?

2. **Storage Path Pattern**: Confirm path convention for iteration artifacts:
   - Option A: `documents/{job_id}/iterations/iter_{N}/doc_{0,1,2}.json`
   - Option B: `documents/{job_id}/doc_{0,1,2}_iter_{N}.json`

3. **Artifact Manifest Strategy**: Should we use `artifact_manifest` (Option B in Artifacts schema) to track iterations, or use custom keys like `iteration_history`?

4. **Iteration Limit**: Is there a max number of iterations per job? Should we enforce in validation?

5. **Cost Tracking**: Should iterations have separate cost fields (`iteration_api_costs`) or merge into main `api_costs`?

6. **Database Schema**: Do we need a new `iterations` table, or store everything in `jobs.artifacts` JSONB?

---

## References

- **Job Schema**: `backend/models/job_record.py`
- **Store Interface**: `backend/state/__init__.py`
- **Store Implementation**: `backend/state/impl/supabase_store.py`
- **Worker Task**: `backend/worker.py` (lines 52-369)
- **Document Assembly**: `backend/pipeline/stages/document_assembly.py`
- **Completion Stage**: `backend/pipeline/stages/initialization.py`
- **Booster Pattern**: `backend/worker.py` (lines 1220-1450) — Reference for separate status tracking
- **Producer Pattern**: `backend/worker.py` (lines 1453-1665) — Reference for atomic artifacts updates

---

**End of Report**
