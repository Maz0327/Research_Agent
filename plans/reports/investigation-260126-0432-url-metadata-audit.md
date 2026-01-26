# URL Metadata Audit Report

**Date:** 2026-01-26
**Branch:** claude/fix-metadata-supadata-ABW4P

## Summary

Audited all video URL input paths in the codebase to ensure YouTube metadata (title, creator, duration) is properly fetched and displayed in Doc 0.

## Video Processing Paths Audited

### 1. Mixed-Input Semantic Pipeline
**Location:** `backend/worker.py:213-234` (`_run_mixed_input_job`)
**Status:** ✅ FIXED (commit `be635d7`)
**Issue:** Called `build_source_identity_from_video()` directly without fetching Supadata metadata
**Fix:** Added `fetch_video_metadata()` + `_merge_supadata_metadata()` after building package

### 2. Transcript Extraction Job
**Location:** `backend/worker.py:445-480` (`run_transcript_extraction_job`)
**Status:** ✅ N/A
**Notes:** Extracts transcripts only, no Doc 0 generation. Metadata not applicable.

### 3. Full Research Assistant Pipeline (Legacy)
**Location:** `backend/worker.py:632-705`
**Status:** ✅ OK
**Notes:** Uses Gemini's `run_full_analysis_pipeline()` which extracts video titles directly from video content via Gemini vision. Different architecture - Gemini provides metadata in response.

### 4. Evolving Job Pipeline
**Location:** `backend/worker.py:955-985` (`process_evolving_job`)
**Status:** ✅ FIXED (commit `02a6edf`)
**Issues Found:**
- Called functions with wrong keyword arguments (`video_url=`, `source_id=`) that don't exist in function signatures
- Would have caused TypeError at runtime
- Missing metadata fetch

**Fix:**
- Corrected to use proper positional args (`video_data` dict, `source_index`)
- Added source_index extraction from source_id (e.g., "SRC_3" → 2)
- Added `fetch_video_metadata()` + `_merge_supadata_metadata()`
- Fixed `build_source_identity_from_text` call signature

### 5. Claim Extraction Pipeline
**Location:** `backend/worker.py:2317-2332` → `backend/pipeline/claim_extraction.py:538-574`
**Status:** ✅ FIXED (previous session, commit `fd1c553`)
**Notes:** Already has `fetch_video_metadata()` at lines 550-552

### 6. Standard Research Pipeline (Stage-based)
**Location:** `backend/pipeline/stages/source_identity.py:546-565` (`stage_source_identity`)
**Status:** ✅ OK
**Notes:** Already fetches metadata via `fetch_video_metadata()` and merges with `_merge_supadata_metadata()`

## Commits in This Branch

| Commit | Description |
|--------|-------------|
| `fd1c553` | fix: use correct transcript key and fetch video metadata for YouTube in claim extraction |
| `be635d7` | fix: add YouTube metadata fetch to mixed-input semantic pipeline |
| `02a6edf` | fix: repair evolving job source identity calls and add metadata fetch |

## Files Modified

- `backend/worker.py` - Fixed mixed-input pipeline and evolving job pipeline
- `backend/pipeline/claim_extraction.py` - Fixed transcript key and added metadata fetch (previous session)

## Verification

All video URL processing paths now either:
1. Fetch metadata via Supadata API and merge into source identity package
2. Use Gemini to extract video info directly from video content
3. Don't generate Doc 0 (transcript-only jobs)
