# Run Abstraction - Data Contract Design

**Date:** 2026-01-25
**Status:** Draft

---

## Overview

The Run abstraction unifies baseline research, iterations, and regenerations under a single concept. Every research output set belongs to a Run.

---

## Run Model

### Core Definition

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RunType(str, Enum):
    """Type of research run."""
    BASELINE = "baseline"           # Initial research job
    ADD_SOURCES = "add_sources"     # Add more sources
    FIX_WEAK_SPOTS = "fix_weak"     # Address gaps/weaknesses
    COUNTERARGUMENT = "counter"     # Find opposing views
    DIFFERENT_ANGLE = "angle"       # Explore different perspective
    REGENERATE = "regenerate"       # Re-run synthesis with same sources


class RunStatus(str, Enum):
    """Run execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(BaseModel):
    """
    A single research run producing Doc 0/1/2 outputs.

    Runs are append-only. Once created, a run's outputs are immutable.
    New iterations create new runs that may inherit from previous runs.
    """

    # Identity
    run_id: str = Field(..., description="Unique run ID: run_0, run_1, ...")
    run_index: int = Field(..., ge=0, description="Sequential index (0 for baseline)")
    run_type: RunType = Field(..., description="Type of run")

    # Lineage
    parent_run_id: Optional[str] = Field(None, description="Parent run for iterations")

    # Request (what was asked)
    request: "RunRequest" = Field(..., description="What triggered this run")

    # Status
    status: RunStatus = Field(RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional["RunError"] = None

    # Outputs (set on completion)
    outputs: Optional["RunOutputs"] = None

    # Metrics
    metrics: Optional["RunMetrics"] = None

    # Run-scoped enhancements
    producer_packet: Optional["RunProducerPacket"] = None
    booster_expansion: Optional["RunBoosterExpansion"] = None


class RunRequest(BaseModel):
    """Request that triggered the run."""

    # User guidance
    user_prompt: Optional[str] = Field(None, max_length=2000)

    # For add_sources type
    new_source_urls: Optional[list[str]] = Field(None, description="URLs to add")
    max_new_sources: Optional[int] = Field(None, ge=1, le=10)

    # For fix_weak type
    gap_ids: Optional[list[str]] = Field(None, description="GAP IDs to address")

    # For counterargument type
    claim_ids: Optional[list[str]] = Field(None, description="CLM IDs to counter")

    # For different_angle type
    perspective: Optional[str] = Field(None, description="New angle to explore")

    # Common
    requested_by: str = Field(..., description="User ID who requested")
    requested_at: datetime = Field(default_factory=datetime.utcnow)


class RunOutputs(BaseModel):
    """Output documents from a completed run."""

    # Storage paths (primary)
    doc_0_path: Optional[str] = Field(None, description="GCS path to Source Ledger")
    doc_1_path: Optional[str] = Field(None, description="GCS path to Jump-Start")
    doc_2_path: Optional[str] = Field(None, description="GCS path to Semantic Brief")

    # Inline fallback (if storage failed)
    doc_0_inline: Optional[dict] = None
    doc_1_inline: Optional[dict] = None
    doc_2_inline: Optional[dict] = None

    # Doc 0 append metadata (for add_sources runs)
    doc_0_is_delta: bool = Field(False, description="True if Doc 0 only contains new sources")
    doc_0_parent_path: Optional[str] = Field(None, description="Parent Doc 0 to merge with")
    new_source_ids: Optional[list[str]] = Field(None, description="Source IDs added in this run")


class RunError(BaseModel):
    """Error details if run failed."""
    code: str
    message: str
    details: Optional[dict] = None


class RunMetrics(BaseModel):
    """Execution metrics for the run."""
    wall_time_ms: int = Field(0, ge=0)
    sources_processed: int = Field(0, ge=0)
    sources_new: int = Field(0, ge=0, description="New sources added (for add_sources)")
    key_points_found: int = Field(0, ge=0)
    claims_extracted: int = Field(0, ge=0)
    themes_identified: int = Field(0, ge=0)
    llm_cost_usd: float = Field(0.0, ge=0.0)


class RunProducerPacket(BaseModel):
    """Producer Packet (Doc 3) scoped to this run."""
    status: RunStatus = Field(RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    path: Optional[str] = None
    inline: Optional[dict] = None
    markdown: Optional[str] = None
    error: Optional[str] = None


class RunBoosterExpansion(BaseModel):
    """Booster expansion scoped to this run."""
    status: RunStatus = Field(RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    output: Optional[dict] = None
    markdown: Optional[str] = None
    error: Optional[str] = None
```

---

## Updated Artifacts Model

```python
class Artifacts(BaseModel):
    """
    Job artifacts container.

    V2: Uses runs[] for all outputs.
    V1 (legacy): Uses doc_*_path for baseline + iterations[] for iterations.
    """

    # V2: Run-based storage (preferred)
    runs: list[Run] = Field(default_factory=list, description="All runs (baseline + iterations)")

    # V1 (legacy): Baseline document paths
    # DEPRECATED: Use runs[0].outputs instead
    doc_0_path: Optional[str] = None
    doc_1_path: Optional[str] = None
    doc_2_path: Optional[str] = None
    doc_3_path: Optional[str] = None

    # V1 (legacy): Iteration history
    # DEPRECATED: Use runs[1:] instead
    iterations: list[Iteration] = Field(default_factory=list)

    # V1 (legacy): Job-level Booster/Producer
    # DEPRECATED: Use runs[n].booster_expansion/producer_packet
    booster_output: Optional[dict] = None
    booster_expansion_md: Optional[str] = None
    producer_packet: Optional[dict] = None
    producer_packet_md: Optional[str] = None

    # Shared data (used by all runs)
    video_metadata: Optional[dict] = None
    source_identity_packages: Optional[list[dict]] = None

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get run by ID."""
        for run in self.runs:
            if run.run_id == run_id:
                return run
        return None

    def get_baseline_run(self) -> Optional[Run]:
        """Get the baseline run (run_0)."""
        return self.get_run("run_0")

    def get_latest_run(self) -> Optional[Run]:
        """Get the most recent completed run."""
        completed = [r for r in self.runs if r.status == RunStatus.COMPLETED]
        if completed:
            return max(completed, key=lambda r: r.run_index)
        return None
```

---

## Storage Path Convention

```
jobs/{job_id}/
├── runs/
│   ├── run_0/                    # Baseline
│   │   ├── doc_0.json
│   │   ├── doc_1.json
│   │   ├── doc_2.json
│   │   ├── producer_packet.json  # If generated
│   │   └── booster_output.json   # If generated
│   │
│   ├── run_1/                    # Iteration 1
│   │   ├── doc_0_delta.json      # Only new sources (for add_sources)
│   │   ├── doc_0_merged.json     # Full merged Doc 0 (cached)
│   │   ├── doc_1.json
│   │   ├── doc_2.json
│   │   └── producer_packet.json  # If generated
│   │
│   └── run_2/                    # Regenerate
│       ├── doc_1.json            # New synthesis
│       └── doc_2.json            # New brief
│
└── shared/                       # Shared across runs
    ├── source_packages.json
    └── video_metadata.json
```

---

## Doc 0 Append Behavior

### For `add_sources` Run Type

1. **Run creates delta Doc 0** with only NEW sources
2. **Stores reference** to parent Doc 0 in `doc_0_parent_path`
3. **UI merges on display** by loading parent + delta
4. **Optional:** Store merged Doc 0 as cache in `doc_0_merged.json`

```python
def get_merged_doc_0(run: Run, artifacts: Artifacts) -> dict:
    """
    Get the complete Doc 0 for a run, merging parent + delta if needed.
    """
    outputs = run.outputs
    if not outputs:
        return {}

    if not outputs.doc_0_is_delta:
        # Not a delta, return as-is
        return load_doc(outputs.doc_0_path) or outputs.doc_0_inline or {}

    # Delta run: need to merge with parent
    parent_doc_0 = {}
    if outputs.doc_0_parent_path:
        parent_doc_0 = load_doc(outputs.doc_0_parent_path) or {}

    delta_doc_0 = load_doc(outputs.doc_0_path) or outputs.doc_0_inline or {}

    # Merge: parent sources + new sources
    merged = {
        **parent_doc_0,
        "sources": parent_doc_0.get("sources", []) + delta_doc_0.get("sources", []),
        "source_manifest": parent_doc_0.get("source_manifest", []) + delta_doc_0.get("source_manifest", []),
    }
    merged["source_count"] = len(merged["sources"])

    return merged
```

### For Other Run Types

- `fix_weak_spots`: Doc 0 unchanged, reuse parent's
- `counterargument`: May add new sources, use delta approach
- `different_angle`: Doc 0 unchanged, reuse parent's
- `regenerate`: Doc 0 unchanged, reuse parent's

---

## API Endpoints

### Create Run (Iteration)
```
POST /api/jobs/{job_id}/runs
Body: {
    "run_type": "add_sources",
    "parent_run_id": "run_0",
    "request": {
        "new_source_urls": ["https://..."],
        "user_prompt": "Optional guidance"
    }
}
Response: {
    "run_id": "run_1",
    "status": "queued"
}
```

### Get Run
```
GET /api/jobs/{job_id}/runs/{run_id}
Response: Run object
```

### Get Run Documents
```
GET /api/jobs/{job_id}/runs/{run_id}/doc/{doc_num}
Query: ?merged=true (for Doc 0 in add_sources runs)
Response: Document JSON or markdown
```

### Trigger Producer for Run
```
POST /api/jobs/{job_id}/runs/{run_id}/producer
Response: { "status": "queued" }
```

### Trigger Booster for Run
```
POST /api/jobs/{job_id}/runs/{run_id}/booster
Response: { "status": "queued" }
```

---

## Backward Compatibility Shim

```python
def ensure_runs_exist(job: JobRecord) -> None:
    """
    Ensure job has runs[] populated.
    Migrates legacy artifacts to run_0 if needed.
    """
    artifacts = job.artifacts
    if not artifacts:
        return

    # Already has runs
    if artifacts.runs:
        return

    # Create run_0 from legacy baseline
    if artifacts.doc_0_path or artifacts.doc_1_path or artifacts.doc_2_path:
        run_0 = Run(
            run_id="run_0",
            run_index=0,
            run_type=RunType.BASELINE,
            status=RunStatus.COMPLETED,
            request=RunRequest(requested_by=job.user_id or "system"),
            outputs=RunOutputs(
                doc_0_path=artifacts.doc_0_path,
                doc_1_path=artifacts.doc_1_path,
                doc_2_path=artifacts.doc_2_path,
            ),
            created_at=job.created_at,
            completed_at=job.completed_at,
        )

        # Migrate job-level producer/booster to run_0
        if artifacts.producer_packet or artifacts.producer_packet_md:
            run_0.producer_packet = RunProducerPacket(
                status=RunStatus.COMPLETED,
                inline=artifacts.producer_packet,
                markdown=artifacts.producer_packet_md,
            )

        if artifacts.booster_output or artifacts.booster_expansion_md:
            run_0.booster_expansion = RunBoosterExpansion(
                status=RunStatus.COMPLETED,
                output=artifacts.booster_output,
                markdown=artifacts.booster_expansion_md,
            )

        artifacts.runs.append(run_0)

    # Migrate legacy iterations to runs
    for iteration in artifacts.iterations:
        run = Run(
            run_id=f"run_{iteration.index}",
            run_index=iteration.index,
            run_type=_map_iteration_mode_to_run_type(iteration.request.mode),
            parent_run_id=f"run_{iteration.index - 1}",
            status=RunStatus(iteration.status),
            request=RunRequest(
                user_prompt=iteration.request.user_prompt,
                requested_by=iteration.request.user_id or "system",
            ),
            created_at=datetime.fromisoformat(iteration.created_at),
            started_at=datetime.fromisoformat(iteration.started_at) if iteration.started_at else None,
            completed_at=datetime.fromisoformat(iteration.completed_at) if iteration.completed_at else None,
        )

        if iteration.outputs:
            run.outputs = RunOutputs(
                doc_0_path=iteration.outputs.doc_0_path,
                doc_1_path=iteration.outputs.doc_1_path,
                doc_2_path=iteration.outputs.doc_2_path,
                doc_0_inline=iteration.outputs.doc_0_inline,
                doc_1_inline=iteration.outputs.doc_1_inline,
                doc_2_inline=iteration.outputs.doc_2_inline,
            )

        artifacts.runs.append(run)


def _map_iteration_mode_to_run_type(mode: str) -> RunType:
    """Map legacy iteration mode to RunType."""
    return {
        "more_sources": RunType.ADD_SOURCES,
        "deeper": RunType.FIX_WEAK_SPOTS,
        "custom": RunType.REGENERATE,
        "different_angle": RunType.DIFFERENT_ANGLE,
    }.get(mode, RunType.REGENERATE)
```

---

## Frontend Types

```typescript
// frontend/types/run.ts

export type RunType =
  | 'baseline'
  | 'add_sources'
  | 'fix_weak'
  | 'counter'
  | 'angle'
  | 'regenerate';

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface Run {
  run_id: string;
  run_index: number;
  run_type: RunType;
  parent_run_id: string | null;
  status: RunStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  request: RunRequest;
  outputs: RunOutputs | null;
  metrics: RunMetrics | null;
  producer_packet: RunProducerPacket | null;
  booster_expansion: RunBoosterExpansion | null;
  error: RunError | null;
}

export interface RunRequest {
  user_prompt?: string;
  new_source_urls?: string[];
  max_new_sources?: number;
  gap_ids?: string[];
  claim_ids?: string[];
  perspective?: string;
  requested_by: string;
  requested_at: string;
}

export interface RunOutputs {
  doc_0_path: string | null;
  doc_1_path: string | null;
  doc_2_path: string | null;
  doc_0_is_delta: boolean;
  doc_0_parent_path: string | null;
  new_source_ids: string[] | null;
}

// Run type display labels
export const RUN_TYPE_LABELS: Record<RunType, string> = {
  baseline: 'Baseline',
  add_sources: 'Add Sources',
  fix_weak: 'Fix Weak Spots',
  counter: 'Counterargument',
  angle: 'Different Angle',
  regenerate: 'Regenerate',
};
```

---

## Implementation Order

1. **Add Run models** to `backend/models/run_models.py`
2. **Add backward compat shim** to `backend/models/job_record.py`
3. **Create run storage manager** at `backend/pipeline/runs/storage.py`
4. **Update routes** to support `/runs/{run_id}/producer` and `/runs/{run_id}/booster`
5. **Create new iteration modes** in `backend/pipeline/runs/modes/`
6. **Update worker tasks** to use run-based storage
7. **Update frontend** types and components
8. **Migrate existing data** (optional, shim handles on-read)

---

## Acceptance Criteria

1. **Baseline as run_0:** New jobs create run_0 on completion
2. **Iteration creates run_N:** Each iteration creates new run with parent linkage
3. **Producer/Booster scoped:** `/runs/{run_id}/producer` works
4. **Doc 0 append:** add_sources run only adds new sources to Doc 0
5. **Backward compat:** Existing jobs work without migration
6. **UI shows runs:** Dropdown shows all runs, not just iterations
