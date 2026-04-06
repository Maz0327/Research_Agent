# Phase 00: Cleanup & Removals

## Context Links
- [Brainstorm](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md)
- [Architecture Rules](../../.claude/rules/architecture.md) -- source isolation, prompt guardrails
- [Implementation Rules](../../.claude/rules/implementation.md) -- archive don't delete

## Overview
- **Priority:** P1 -- blocks all other phases
- **Status:** pending
- **Effort:** 2-3 days
- **Description:** Remove dead code, unused packages, broken integrations. Merge gap+synthesis. Make Creator Brief on-demand.

## Key Insights
- `youtube-transcript-api` is BROKEN on cloud IPs (Railway, AWS). Documented in code comments. Safe to remove.
- 9 packages in `requirements.txt` may be unused. Must verify each with grep before removing.
- Gap analysis and synthesis operate on same input data. Merging saves ~8s and 1 LLM call.
- Creator Brief (Doc 3) always runs even if user doesn't need it. Make on-demand via iterate endpoint.

## Requirements

### Functional
- Remove broken `youtube-transcript-api` tier from fallback chain
- Remove verified-unused Python packages from `requirements.txt`
- Merge gap analysis + semantic synthesis into single Gemini call
- Make Creator Brief generation on-demand (not auto-triggered)
- Remove `next-themes` package and related dead code from frontend
- Clean up `frontend/archive/` dead files

### Non-Functional
- Zero behavior change for existing working features
- All existing tests must pass after cleanup
- Pipeline output identical except Doc 3 no longer auto-generated

## Architecture

No architectural changes. This is cleanup only.

**Merged gap+synthesis** is a prompt engineering change: one Gemini call produces both `gaps` and `synthesized_themes` in a single response schema. Temperature: 0.2 (current synthesis value).

## Related Code Files

### Backend Removals

| File | Change | Lines |
|------|--------|-------|
| `backend/pipeline/transcript_acquisition.py` | Remove `_try_youtube_captions()` (lines 220-252) and its call in fallback chain | ~35 lines removed |
| `backend/worker.py` | Remove unconditional `run_creator_brief_stage` call (line 475). Keep function, just don't auto-call. | ~2 lines |
| `requirements.txt` | Remove packages after grep verification | varies |
| `backend/pipeline/stages/gap_analysis.py` | Merge into new `gap_synthesis.py` | 222 lines -> archive |
| `backend/pipeline/stages/semantic_synthesis.py` | Merge into new `gap_synthesis.py` | 439 lines -> archive |
| `backend/pipeline/stages/__init__.py` | Update imports: remove old, add `stage_gap_synthesis` |  |
| `backend/pipeline/prompts/semantic_synthesis_prompt.py` | Merge gap prompt + synthesis prompt into single combined prompt |  |

### Frontend Removals

| File | Change |
|------|--------|
| `frontend/package.json` | Remove `next-themes` from dependencies |
| `frontend/app/providers.tsx` | Remove `ThemeProvider` import and wrapper (lines 17, 31-35, 41) |
| `frontend/components/ThemeToggle.tsx` | Delete entire file |
| `frontend/components/layout/theme-toggle-button.tsx` | Delete entire file |
| `frontend/components/layout/user-menu.tsx` | Remove `useTheme` import (line 9) and any theme toggle UI |
| `frontend/app/layout.tsx` | Remove `suppressHydrationWarning` comment/attr (line 46) |
| `frontend/archive/ThemeContext.tsx` | Delete (dead code) |
| `frontend/archive/` | Audit remaining files, delete confirmed dead code |

### Package Verification (grep before removing)

Run `grep -r "package_name" backend/ --include="*.py"` for each:

| Package | Likely Status | Verify With |
|---------|--------------|-------------|
| `praw` | Unused (Reddit API -- no active Reddit integration) | `grep -r "praw\|reddit" backend/ --include="*.py"` |
| `tavily-python` | Unused (commented out search) | `grep -r "tavily" backend/ --include="*.py"` |
| `exa-py` | Unused (search integration) | `grep -r "exa" backend/ --include="*.py"` |
| `datasketch` | Check if MinHash still used | `grep -r "datasketch\|MinHash" backend/ --include="*.py"` |
| `rank-bm25` | Check if BM25 still used | `grep -r "rank_bm25\|BM25" backend/ --include="*.py"` |
| `rapidfuzz` | Check if fuzzy match still used | `grep -r "rapidfuzz\|fuzz" backend/ --include="*.py"` |
| `spacy` | Likely unused (500MB model) | `grep -r "spacy\|en_core_web" backend/ --include="*.py"` |
| `mutagen` | Came with yt-dlp, may be unused directly | `grep -r "mutagen" backend/ --include="*.py"` |
| `youtube-transcript-api` | Being removed (broken on cloud) | N/A -- removing |

## Implementation Steps

### Task 0.1: Remove youtube-transcript-api
1. Open `backend/pipeline/transcript_acquisition.py`
2. Delete `_try_youtube_captions()` function (lines 220-252)
3. Find where `_try_youtube_captions` is called in the fallback chain (in `acquire_transcript()` around line 258+)
4. Remove that call from the fallback sequence. Chain becomes: Supadata -> Whisper -> VIDEO_ONLY
5. Remove `youtube-transcript-api>=0.6.0` from `requirements.txt` (line 55)
6. Run `pytest backend/tests/ -v`

### Task 0.2: Audit and remove unused packages
1. For each package in the table above, run the grep command
2. If zero results (excluding comments/requirements.txt), remove from `requirements.txt`
3. Archive any integration files that only serve removed packages to `backend/archive/`
4. Run `pytest backend/tests/ -v`

### Task 0.3: Merge gap analysis + synthesis
1. Create `backend/pipeline/stages/gap_synthesis.py`
2. Copy `aggregate_for_synthesis()` from `semantic_synthesis.py` -- this is the shared input
3. Create `stage_gap_synthesis(ctx: PipelineContext) -> PipelineContext` that:
   - Calls `aggregate_for_synthesis(ctx)` for input data
   - Builds combined prompt requesting BOTH gaps AND synthesis in one schema
   - Single Gemini call at temperature 0.2
   - Parses response into `ctx.identified_gaps` + `ctx.semantic_core` + `ctx.synthesized_themes` + `ctx.speculative_observations`
4. Update `backend/pipeline/prompts/semantic_synthesis_prompt.py`:
   - Add `build_combined_gap_synthesis_prompt()` that merges gap identification + synthesis instructions
   - Keep old prompts temporarily for reference
5. Update `backend/pipeline/stages/__init__.py`: export `stage_gap_synthesis`, remove old exports
6. Update `backend/worker.py`:
   - Replace the two separate calls (lines 465-469) with single `stage_gap_synthesis` call
   - Update progress percentages accordingly
7. Move old files to archive: `backend/archive/stages/gap_analysis.py`, `backend/archive/stages/semantic_synthesis.py`
8. Run `pytest backend/tests/ -v` -- verify output schema matches

### Task 0.4: Make Creator Brief on-demand
1. In `backend/worker.py` line 474-475, remove the unconditional `run_creator_brief_stage` call
2. Verify the iterate endpoint (`POST /jobs/{job_id}/iterate`) can trigger Creator Brief generation
3. If not, add a new iterate mode or a dedicated endpoint `POST /jobs/{job_id}/generate-brief`
4. Update `backend/app/routes/jobs_routes.py` if new endpoint needed
5. Run `pytest backend/tests/ -v`

### Task 0.5: Frontend theme cleanup
1. `npm uninstall next-themes` in `frontend/`
2. In `frontend/app/providers.tsx`: remove `ThemeProvider` import and JSX wrapper. Keep other providers.
3. Delete `frontend/components/ThemeToggle.tsx`
4. Delete `frontend/components/layout/theme-toggle-button.tsx`
5. In `frontend/components/layout/user-menu.tsx`: remove `useTheme` import and any theme toggle code
6. In `frontend/app/layout.tsx`: remove `suppressHydrationWarning` if only there for next-themes
7. Delete all files in `frontend/archive/` (confirmed dead: ThemeContext.tsx, iterate-legacy/, etc.)
8. Run `npm run lint && npm run build`

### Task 0.6: Verify and test
1. Run full backend test suite: `pytest backend/tests/ -v`
2. Run frontend build: `cd frontend && npm run build`
3. Manual smoke test: create a job, verify pipeline completes, Doc 0/1/2 generated, Doc 3 NOT auto-generated
4. Verify fallback chain: Supadata -> Whisper -> VIDEO_ONLY (no youtube-transcript-api step)

## Todo Checklist
- [ ] 0.1 Remove youtube-transcript-api from code + requirements.txt
- [ ] 0.2 Grep-verify and remove unused packages
- [ ] 0.3 Merge gap_analysis.py + semantic_synthesis.py into gap_synthesis.py
- [ ] 0.4 Make Creator Brief (Doc 3) on-demand only
- [ ] 0.5 Remove next-themes + frontend dead code
- [ ] 0.6 Full test suite pass (backend + frontend build)

## Success Criteria
- `requirements.txt` has no unused packages
- Pipeline produces same quality output with 1 fewer LLM call (merged gap+synthesis)
- Doc 3 no longer auto-generated; available on-demand
- Frontend builds without `next-themes`
- No `_try_youtube_captions` in codebase
- All tests pass

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Merged gap+synthesis produces lower quality | LOW | Same input data, same temperature, just combined prompt. A/B test output. |
| Removing package breaks hidden dependency | MEDIUM | Grep thoroughly. Run full test suite. Keep archived. |
| Doc 3 on-demand breaks existing UI | LOW | Frontend already has document generation buttons. Verify UI. |

## Security Considerations
- No security impact. Cleanup only.
