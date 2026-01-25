# Run Abstraction Implementation Progress

**Date:** 2026-01-25
**Branch:** `claude/fix-metadata-supadata-ABW4P`

---

## Summary

Implemented V2 Run Abstraction system that unifies baseline research, iterations, and regenerations under a single Run model. This enables Producer/Booster to be scoped to individual runs.

---

## Completed Work

### 1. Run Models (`backend/models/run_models.py`)

| Model | Purpose |
|-------|---------|
| `Run` | Core run object with status, outputs, lineage |
| `RunType` | Enum: baseline, add_sources, fix_weak, counter, angle, regenerate |
| `RunStatus` | Enum: queued, running, completed, failed |
| `RunRequest` | Request params (user_prompt, new_source_urls, gap_ids, etc.) |
| `RunOutputs` | Doc 0/1/2 paths + delta metadata |
| `RunMetrics` | Execution metrics (time, tokens, cost) |
| `RunProducerPacket` | Run-scoped producer output |
| `RunBoosterExpansion` | Run-scoped booster output |

**Helper Functions:**
- `ensure_runs_migrated()` - Backward compat shim for V1 artifacts
- `create_baseline_run()` - Create run_0 for new jobs
- `create_iteration_run()` - Create iteration run from parent
- `map_iteration_mode_to_run_type()` - Legacy mode → RunType mapping

### 2. Updated Artifacts Model (`backend/models/job_record.py`)

- Added `runs: list[Any]` field for V2 storage
- Added helper methods: `get_run()`, `get_baseline_run()`, `get_latest_completed_run()`
- Marked legacy fields as deprecated (doc_*_path, iterations[], producer_packet, booster_output)
- Added `video_metadata` and `source_identity_packages` as shared data

### 3. Run Storage Manager (`backend/pipeline/runs/storage.py`)

| Function | Purpose |
|----------|---------|
| `store_run_outputs()` | Store Doc 0/1/2 for a run |
| `load_run_document()` | Load document from GCS |
| `get_merged_doc_0()` | Merge parent + delta for add_sources runs |
| `store_run_producer()` | Store producer packet for a run |
| `store_run_booster()` | Store booster output for a run |

**Storage Path Convention:**
```
jobs/{job_id}/runs/{run_id}/
├── doc_0.json (or doc_0_delta.json for add_sources)
├── doc_1.json
├── doc_2.json
├── producer_packet.json (optional)
└── booster_output.json (optional)
```

### 4. API Endpoints (`backend/app/routes/jobs_routes.py`)

| Endpoint | Purpose |
|----------|---------|
| `POST /{job_id}/runs` | Create new run (V2 iteration) |
| `POST /{job_id}/runs/{run_id}/producer` | Trigger producer for specific run |
| `POST /{job_id}/runs/{run_id}/booster` | Trigger booster for specific run |

**Run Types Supported:**
- `add_sources` - Add more sources (Doc 0 append-only)
- `fix_weak` - Address gaps/weaknesses
- `counter` - Find counterarguments
- `angle` - Different perspective
- `regenerate` - Re-run synthesis

### 5. Worker Tasks (`backend/worker.py`)

Updated both tasks to accept optional `run_id` parameter:

- `run_producer_task(job_id, user_id, run_id=None)`
- `run_booster_task(job_id, user_id, run_id=None)`

When `run_id` provided:
- Stores in run-scoped path
- Updates run object in artifacts.runs[]

When `run_id` is None:
- V1 behavior (job-level storage)

### 6. Run Mode Executors (`backend/pipeline/runs/modes/`)

| File | Purpose |
|------|---------|
| `base.py` | `RunModeExecutor` base class with progress, metrics, storage |
| `add_sources.py` | Add new sources, create delta Doc 0, regenerate Doc 1/2 |
| `regenerate.py` | Re-run synthesis with same sources, optional user guidance |

**add_sources mode:**
- Searches for sources via Tavily integration
- Creates delta Doc 0 (new sources only)
- Merges parent + delta for full Doc 0 on display
- Regenerates Doc 1/2 with all sources

**regenerate mode:**
- Inherits parent Doc 0 unchanged
- Regenerates Doc 1/2 with optional user prompt guidance

---

### 7. Worker Task V2 Support (`backend/worker.py`)

Updated `run_iteration_task` to support both V1 and V2:

- Detects V2 runs by `run_id.startswith("run_")`
- Routes V2 runs to `_run_v2_run_task()` helper
- Uses run mode executors (add_sources, regenerate)
- Falls back to regenerate for unimplemented modes
- Includes `_mark_run_failed()` for consistent error handling

---

### 8. Frontend UI Components

#### TypeScript Types (`frontend/types/run.ts`)

- `RunStatus`, `RunType` - Status and type enums
- `Run` interface - Complete run object
- `RunRequest`, `RunOutputs`, `RunMetrics` - Supporting interfaces
- `RUN_TYPE_LABELS`, `RUN_TYPE_ICONS` - Display constants
- Helper functions: `isV2Run()`, `getRunLabel()`, `getRunIcon()`

#### RunSelector Component (`frontend/components/job-detail/RunSelector.tsx`)

Unified dropdown supporting both V2 runs and V1 iterations:
- Shows baseline option with badge
- V2 RUNS section with type icons and labels
- V1 ITERATIONS section (legacy) with mode labels
- Relative time formatting
- Run type badge colors

#### ArtifactCardGrid Updates (`frontend/components/job-detail/ArtifactCardGrid.tsx`)

- Replaced `IterationSelector` with `RunSelector`
- Updated `getArtifactState()` to handle V2 runs
- Updated `openDocViewer()` to load V2 run documents
- Added `runs` to `JobArtifacts` type in store

---

## Commits

```
f2a3b6e feat(backend): add Run abstraction for unified research output management
315a8f6 feat(api): add run-scoped Producer/Booster endpoints
4bb3d9d feat(worker): add run-scoped storage for Producer/Booster
6be369d feat(api): add V2 run-based iteration endpoint
8ee1436 feat(pipeline): add V2 run mode executors
9cca824 feat(worker): wire run_iteration_task to V2 run modes
95c779a feat(frontend): add V2 run types and RunSelector component
a79267e feat(frontend): integrate RunSelector in ArtifactCardGrid
```

---

## Remaining Work

### High Priority

1. ~~**Run Iteration Modes**~~ ✅ Implemented add_sources and regenerate modes

2. ~~**Worker Task Update**~~ ✅ Wired run_iteration_task to V2 run modes

3. ~~**UI Updates**~~ ✅ RunSelector component with V2 run support

### Medium Priority

4. **Run Status Endpoint** - Add `GET /{job_id}/runs/{run_id}` for polling
5. **Run-scoped Producer/Booster UI buttons** - Update UI to call run-scoped endpoints

### Low Priority

6. **Migration Script** - Optional: migrate existing iterations[] to runs[]
7. **Cleanup** - Remove legacy iteration code after transition

---

## Backward Compatibility

- Existing V1 jobs work via `ensure_runs_migrated()` shim
- Legacy `/iterate` endpoint still works
- Job-level Producer/Booster continue to work (run_id=None)
- Iteration tracking fields reused for run status polling

---

## Testing Notes

All syntax verified. Full integration testing needed:
- [ ] Create run via POST /runs
- [ ] Run-scoped producer via POST /runs/{run_id}/producer
- [ ] Run-scoped booster via POST /runs/{run_id}/booster
- [ ] Doc 0 delta merging for add_sources runs
- [ ] Backward compat with V1 jobs
