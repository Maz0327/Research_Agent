# Legacy Code Audit — Phase 0.1.1

**Date:** 2026-03-11
**Branch:** `feature/kimi-visual-analysis-and-optimizations`
**Auditor:** Claude (automated scan)

---

## 1. Deprecated API Endpoints

### Already returning 410 Gone (dead code — handlers exist but always raise)

| Endpoint | Function | File:Lines | Deprecated Since |
|----------|----------|------------|-----------------|
| `POST /jobs` | `create_job_endpoint()` | `jobs_routes.py:118-146` | 2026-01-19 |
| `POST /preview` | `preview_job_endpoint()` | `jobs_routes.py:2546-2572` | 2026-01-19 |
| `POST /jobs/{id}/select-interpretation` | `select_interpretation()` | `jobs_routes.py:2905-2927` | 2026-01-19 |

### Deprecated but still functional

| Endpoint | Function | File:Lines | Deprecated Since | Notes |
|----------|----------|------------|-----------------|-------|
| `POST /jobs/{id}/iterate` | `run_job_iteration()` | `jobs_routes.py:1724-1962+` | 2026-01-26 | Full impl, deprecated docstring. Frontend does NOT call it. Has 10+ tests. |

### Legacy but NOT marked deprecated (still active)

| Endpoint | Function | File:Lines | Notes |
|----------|----------|------------|-------|
| `POST /jobs/{id}/sources` | `add_sources_to_job()` | `jobs_routes.py:603-795` | Part of "evolving jobs" pattern |
| `POST /jobs/{id}/process-pending` | `process_pending_sources()` | `jobs_routes.py:798-879` | Processes batched pending sources |

### Duplicate route (bug)

| Endpoint | Functions | File:Lines | Notes |
|----------|-----------|------------|-------|
| `POST /jobs/{id}/archive` | `archive_job()` + `archive_job_endpoint()` | `jobs_routes.py:2867-2902` + `3529-3567` | Two handlers for same route. First (2867) is dead — overridden by second (3529). |

---

## 2. Frontend Breakage Found

| Issue | File:Line | Detail |
|-------|-----------|--------|
| Calls dead `POST /preview` endpoint | `frontend/store/jobs.ts:587` | Endpoint returns 410; frontend will get error |

---

## 3. V1 Legacy Fields in JobRecord (`backend/models/job_record.py`)

### V1 inline document fields (lines 108-111)

| Field | Line | Type | Status |
|-------|------|------|--------|
| `source_ledger` | 108 | `Optional[dict]` | V1 legacy, migration only |
| `jump_start` | 109 | `Optional[dict]` | V1 legacy, migration only |
| `semantic_brief` | 110 | `Optional[dict]` | V1 legacy, migration only |
| `semantic_extractions` | 111 | `Optional[list[dict]]` | V1 legacy, migration only |

### V1 document path fields (lines 114-117)

| Field | Line | Type | Status |
|-------|------|------|--------|
| `doc_0_path` | 114 | `Optional[str]` | V1 legacy, still used in migration + frontend |
| `doc_1_path` | 115 | `Optional[str]` | V1 legacy, still used in migration + frontend |
| `doc_2_path` | 116 | `Optional[str]` | V1 legacy, still used in migration + frontend |
| `doc_3_path` | 117 | `Optional[str]` | **V1 legacy — currently means Producer Packet. Will mean Creator Brief in v2.** |

### V1 artifact fields (lines 120-130)

| Field | Line | Type | Status |
|-------|------|------|--------|
| `artifact_manifest` | 120-122 | `Optional[dict]` | **Abandoned** — not used anywhere |
| `booster_output` | 125 | `Optional[dict]` | V1 legacy, used in migration + frontend fallbacks |
| `booster_expansion_md` | 126 | `Optional[str]` | V1 legacy, used in migration + display |
| `producer_packet` | 129 | `Optional[dict]` | V1 legacy, used in migration |
| `producer_packet_md` | 130 | `Optional[str]` | V1 legacy, used in migration + fallback display |

### V1 iteration fields (line 137)

| Field | Line | Type | Status |
|-------|------|------|--------|
| `iterations` | 137 | `list[Iteration]` | **Deprecated** — comment says "Use runs[1:] instead" |

---

## 4. V1 Legacy Code in Worker (`backend/worker.py`)

### Orphaned task (safe to archive)

| Task | Function | Lines | Notes |
|------|----------|-------|-------|
| `run_gemini_video_job` | `run_gemini_video_job()` | 597-809 | Full 4-pass pipeline. Routed but never called by any endpoint. Test file marks as "Legacy". |

### Deprecated parameters (kept for backward compat)

| Function | Param | Line | Notes |
|----------|-------|------|-------|
| `run_research_job` | `slack_payload` | 60 | Ignored, Slack removed |
| `run_research_job` | `enable_parallel` | 61 | Ignored, no longer used |

### V1/V2 dual storage paths (must keep for backward compat)

| Function | Lines | What |
|----------|-------|------|
| `run_booster_task()` | 1466-1470 | Writes booster_output + booster_expansion_md at job level (V1) |
| `run_producer_task()` | 1717-1754 | Writes producer_packet at job level (V1) |
| `run_iteration_task()` | 2196-2370 | Full V1 iteration handling (V2 detected by `run_` prefix) |
| `run_claims_doc_task()` | 2645-2651 | Calls `ensure_runs_migrated()` for V1→V2 |

### Removed systems (comments only, no code)

| System | Line | Notes |
|--------|------|-------|
| Slack integration | 53 | Fully removed 2026-01-19 |
| `_run_disambiguated_job()` | 389-391 | Fully removed 2026-01-19 |
| Legacy fallbacks | 14 | Removed 2026-01-19 |

---

## 5. Action Items for Task 0.1.2

### Archive these (move handlers to `backend/archive/`):
1. `create_job_endpoint()` — already returns 410
2. `preview_job_endpoint()` — already returns 410
3. `select_interpretation()` — already returns 410
4. `run_job_iteration()` — deprecated, frontend doesn't use it
5. `archive_job()` (first duplicate at line 2867) — dead code, overridden
6. `run_gemini_video_job()` — orphaned task, never called

### Keep but mark deprecated:
1. `add_sources_to_job()` — still active, will be replaced by Iterate: expand_sources
2. `process_pending_sources()` — still active, paired with above
3. All V1 fields in JobRecord — needed for backward compat migration
4. V1/V2 dual storage in worker — needed until all V1 jobs migrated

### Fix:
1. Remove `POST /preview` call from `frontend/store/jobs.ts:587`
2. Remove duplicate `archive_job()` at line 2867

---

*Generated by Phase 0.1.1 legacy code audit*
