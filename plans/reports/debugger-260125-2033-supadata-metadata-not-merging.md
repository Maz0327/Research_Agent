# Debugger Report: Supadata Metadata Not Flowing to Doc 0

**Date:** 2026-01-25
**Issue:** Metadata from Supadata not appearing in Doc 0 (Source Ledger)
**Status:** FIXED

## Problem Description

User reported that metadata (title, creator, published date, duration) from Supadata was not being included in Doc 0 (Source Ledger) despite Supadata API calls succeeding.

## Investigation

### 1. Traced Data Flow

```
Supadata API → fetch_video_metadata() → video_metadata dict → artifacts.video_metadata
                                                              ↑
                                                    STORED BUT NEVER USED
                                                              ↓
build_source_identity_from_video() → SourceIdentityPackage → Doc 0 (Source Ledger)
                                      ↑
                         METADATA FIELDS EMPTY (from sparse YouTube discovery data)
```

### 2. Root Cause Identified

In `backend/pipeline/stages/source_identity.py`:

1. **Line 507**: `build_source_identity_from_video(video, source_index)` called FIRST
2. Package built with metadata from `video_data` dict (YouTube discovery - often sparse)
3. **Lines 514-521**: Supadata metadata fetched AFTER package is built
4. **Lines 600-602**: Metadata stored in `artifacts.video_metadata`
5. **BUG**: Metadata NEVER merged back into the `SourceIdentityPackage`

Result:
- `package.creator`, `package.published`, `package.duration_seconds` remained empty/None
- When Doc 0 was assembled in `stage_document_assembly()`, these empty fields flowed through
- Rich Supadata metadata sat unused in `artifacts.video_metadata`

## Fix Applied

### Added `_merge_supadata_metadata()` helper function

```python
def _merge_supadata_metadata(package: SourceIdentityPackage, metadata: dict) -> None:
    """
    Merge Supadata metadata into SourceIdentityPackage (in-place).
    Only updates fields that are currently empty/None.
    """
    if not metadata:
        return

    # Update title if currently generic/empty
    supadata_title = metadata.get("title")
    if supadata_title and package.title in ("Untitled Video", "", None):
        package.title = supadata_title

    # Update creator from author.name
    author = metadata.get("author", {})
    supadata_creator = author.get("name") if isinstance(author, dict) else None
    if supadata_creator and not package.creator:
        package.creator = supadata_creator

    # Update published from createdAt
    supadata_published = metadata.get("createdAt")
    if supadata_published and not package.published:
        package.published = supadata_published

    # Update duration from media.duration (in seconds)
    media = metadata.get("media", {})
    supadata_duration = media.get("duration") if isinstance(media, dict) else None
    if supadata_duration and not package.duration_seconds:
        package.duration_seconds = int(supadata_duration)
        package.duration_minutes = supadata_duration / 60.0
```

### Called merge after fetching metadata

```python
if metadata:
    video_metadata[url] = metadata
    # Merge metadata into package to enrich Doc 0 source entries
    _merge_supadata_metadata(package, metadata)
    logger.info(f"  ✓ Metadata acquired and merged for {package.source_id}")
```

## Data Flow After Fix

```
Supadata API → fetch_video_metadata() → metadata dict
                                              ↓
                                    _merge_supadata_metadata()
                                              ↓
                        SourceIdentityPackage (enriched with Supadata data)
                                              ↓
                        stage_document_assembly() → Doc 0 with full metadata
```

## Files Modified

1. `backend/pipeline/stages/source_identity.py`:
   - Added `_merge_supadata_metadata()` helper function (lines 112-150)
   - Modified metadata fetch loop to call merge function (line 557)

2. `backend/tests/test_supadata_metadata.py`:
   - Added `TestMergeSupadataMetadata` class (5 tests)
   - Added `TestMetadataMergedIntoPackage` class (1 integration test)

## Verification

- Syntax check passed for all modified files
- New tests cover:
  - Merge updates empty fields
  - Merge does NOT overwrite existing fields
  - Handles missing metadata fields gracefully
  - Handles None/empty metadata gracefully
  - Integration test verifies full stage flow

## Why This Wasn't Caught Before

1. The existing tests only verified metadata was STORED in artifacts
2. No tests verified metadata was MERGED into packages
3. The metadata storage in artifacts gave false confidence the feature worked
4. Without comparing Doc 0 output to Supadata response, the gap wasn't visible

## Lessons Learned

1. When adding "enrichment" features, test the END-TO-END flow to final output
2. Storing data in artifacts != using data in the pipeline output
3. Need integration tests that verify data flows through to final documents
