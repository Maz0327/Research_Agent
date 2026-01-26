# Debug Report: YouTube Metadata Missing in Claim Extractor Doc 0

**Debugger:** Claude
**Date:** 2026-01-26 04:12 UTC
**Branch:** claude/fix-metadata-supadata-ABW4P
**Severity:** Medium - Feature partially broken, affects UX

---

## Executive Summary

YouTube video metadata (title, author, duration, published date) not displaying in Claim Extractor doc 0.

**Root causes identified:**
1. Wrong key used to extract transcript text from SupadataClient response
2. Title field incorrectly read from get_transcript() which doesn't return it
3. fetch_metadata() not called in claim extraction pipeline
4. SourceSummary model missing metadata fields
5. No metadata merge logic for claim extraction

**Impact:** Users see generic titles like "Video 1" instead of actual video metadata in claims document.

---

## Technical Analysis

### 1. Transcript Text Extraction Bug

**File:** `backend/pipeline/claim_extraction.py`
**Line:** 549

**Current code:**
```python
transcript_result = supadata.get_transcript(url)
transcript = transcript_result.get("transcript", "")  # WRONG KEY
video_title = transcript_result.get("title", f"Video {i+1}")  # MISSING FIELD
```

**What get_transcript() actually returns** (from `backend/integrations/supadata_client.py:122-129`):
```python
return {
    "text": text,              # NOT "transcript"!
    "url": url,
    "method": f"supadata_{mode.value}",
    "lang": data.get("lang", lang),
    "duration_seconds": data.get("duration"),
    "cost_credits": 1,
}
```

**Result:**
- `transcript` variable is always empty string (key mismatch)
- `video_title` always defaults to "Video {i+1}" (field doesn't exist)
- Claims extraction proceeds with empty transcript
- SourceSummary created with generic title

**Evidence from working code** (`backend/pipeline/transcript_acquisition.py:184-191`):
```python
result = client.get_transcript(video_url, mode=TranscriptMode.NATIVE)
if result.get("text"):  # Correctly uses "text" key
    return result["text"], None, result.get("cost_credits", 1.0)
```

---

### 2. Missing Metadata Fetch

**Comparison: Semantic Pipeline vs Claim Extraction**

#### Semantic Pipeline (WORKING)
File: `backend/pipeline/stages/source_identity.py:556-564`

```python
# Fetch Supadata metadata (additive, non-blocking)
url = video.get("url", video.get("video_url", ""))
if url:
    try:
        metadata = fetch_video_metadata(url)  # ✓ FETCHES METADATA
        if metadata:
            video_metadata[url] = metadata
            _merge_supadata_metadata(package, metadata)  # ✓ MERGES INTO PACKAGE
            logger.info(f"  ✓ Metadata acquired and merged for {package.source_id}")
    except Exception as e:
        logger.warning(f"  ⚠ Metadata fetch failed for {package.source_id}: {e}")
```

**What fetch_metadata() returns** (`backend/integrations/supadata_client.py:201-242`):
```python
{
    "platform": "youtube",
    "title": "Actual Video Title",
    "author": {"name": "Channel Name", "url": "..."},
    "stats": {"views": 1000, "likes": 100},
    "media": {"thumbnailUrl": "...", "duration": 600},
    "createdAt": "2024-01-01T00:00:00Z"
}
```

#### Claim Extraction Pipeline (BROKEN)
File: `backend/pipeline/claim_extraction.py:538-579`

```python
# Process YouTube videos
for i, url in enumerate(video_urls):
    supadata = SupadataClient()
    transcript_result = supadata.get_transcript(url)  # Only gets transcript
    # ❌ NO metadata fetch
    # ❌ NO _merge_supadata_metadata call

    transcript = transcript_result.get("transcript", "")  # Wrong key
    video_title = transcript_result.get("title", f"Video {i+1}")  # Missing field

    claims, summary = extract_claims_from_youtube(
        gemini_client, url, video_title, transcript, source_id, model
    )
```

**Missing:**
- No call to `fetch_video_metadata(url)`
- No merge logic to populate metadata fields
- No metadata storage in artifacts

---

### 3. SourceSummary Model Limitations

**File:** `backend/models/claims.py:94-107`

**Current model:**
```python
class SourceSummary(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    url: Optional[str] = None
    claim_count: int = default=0
    explicit_count: int = default=0
    implied_count: int = default=0
    # ❌ Missing: creator, published, duration_seconds, thumbnail, views
```

**Compare to SourceIdentityPackage** (semantic pipeline):
```python
class SourceIdentityPackage:
    # ... basic fields ...
    title: str
    creator: Optional[str] = None          # ✓ Has creator
    published: Optional[str] = None         # ✓ Has published
    duration_seconds: Optional[int] = None  # ✓ Has duration
    # ... provenance fields ...
```

**Gap:** SourceSummary doesn't have fields to store fetched metadata.

---

### 4. Recent Work on Metadata (Not Applied to Claims)

**Commits:**
- `0fa98e9` - feat(backend): Add Supadata video metadata retrieval
- `02a9472` - fix(backend): merge Supadata metadata into source identity packages

**What was implemented:**
1. `SupadataClient.fetch_metadata()` method added
2. `fetch_video_metadata()` convenience function (non-blocking)
3. Wired into `source_identity.py` stage
4. `_merge_supadata_metadata()` helper to enrich packages
5. Stored in `artifacts.video_metadata` keyed by URL
6. 274 tests added

**What was NOT done:**
- Claims pipeline not updated to use metadata fetch
- SourceSummary model not extended with metadata fields
- No tests for claims pipeline metadata integration

---

## Data Flow Comparison

### Semantic Pipeline (WORKING)
```
1. source_identity stage runs
2. fetch_video_metadata(url) called
3. Metadata returned: {title, author, media, createdAt, stats}
4. _merge_supadata_metadata(package, metadata) enriches SourceIdentityPackage
5. Package has: title="Real Title", creator="Channel", duration_seconds=600
6. Doc 0 displays full metadata
```

### Claim Extraction Pipeline (BROKEN)
```
1. run_claim_extraction_pipeline() runs
2. get_transcript(url) called (no metadata fetch)
3. Wrong key "transcript" used → empty transcript
4. Missing key "title" → defaults to "Video {i+1}"
5. SourceSummary created with generic title, no metadata
6. Doc 0 shows "Video 1" with no author/duration/date
```

---

## Actionable Recommendations

### Immediate Fixes (Priority 1)

**Fix 1: Correct transcript extraction keys**
File: `backend/pipeline/claim_extraction.py:548-550`

```python
# BEFORE:
transcript_result = supadata.get_transcript(url)
transcript = transcript_result.get("transcript", "")
video_title = transcript_result.get("title", f"Video {i+1}")

# AFTER:
transcript_result = supadata.get_transcript(url)
transcript = transcript_result.get("text", "")  # Fixed key
video_title = f"Video {i+1}"  # Will be replaced by metadata
```

**Fix 2: Add metadata fetch to claim extraction**
File: `backend/pipeline/claim_extraction.py:545-565`

```python
# After line 550, add:
# Fetch video metadata (non-blocking)
metadata = None
try:
    from backend.integrations.supadata_client import fetch_video_metadata
    metadata = fetch_video_metadata(url)
    if metadata:
        video_title = metadata.get("title", video_title)
        logger.info(f"Fetched metadata for {source_id}: {video_title}")
except Exception as e:
    logger.warning(f"Metadata fetch failed for {url}: {e}")
```

**Fix 3: Pass metadata to extract_claims_from_youtube**
File: `backend/pipeline/claim_extraction.py:563-565`

Update function signature and call:
```python
claims, summary = extract_claims_from_youtube(
    gemini_client, url, video_title, transcript, source_id, model,
    metadata=metadata  # Add this param
)
```

**Fix 4: Update extract_claims_from_youtube to accept metadata**
File: `backend/pipeline/claim_extraction.py:165-276`

```python
def extract_claims_from_youtube(
    gemini_client: Any,
    video_url: str,
    title: str,
    transcript: str,
    source_id: str,
    model: str = "gemini-2.5-flash",
    metadata: Optional[dict] = None,  # Add param
) -> tuple[list[Claim], SourceSummary]:
    """..."""

    # ... extraction logic ...

    # Build SourceSummary with metadata
    source_summary = SourceSummary(
        source_id=source_id,
        source_type=SourceType.YOUTUBE,
        title=title,
        url=video_url,
        claim_count=len(claims),
        explicit_count=explicit_count,
        implied_count=implied_count,
        # If we extend SourceSummary model:
        # creator=metadata.get("author", {}).get("name") if metadata else None,
        # published=metadata.get("createdAt") if metadata else None,
        # duration_seconds=metadata.get("media", {}).get("duration") if metadata else None,
    )
```

### Long-term Improvements (Priority 2)

**Improvement 1: Extend SourceSummary model**
File: `backend/models/claims.py:94-107`

```python
class SourceSummary(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    url: Optional[str] = None
    claim_count: int = Field(default=0)
    explicit_count: int = Field(default=0)
    implied_count: int = Field(default=0)

    # Add metadata fields (optional for backward compat)
    creator: Optional[str] = Field(None, description="Content creator/author")
    published: Optional[str] = Field(None, description="ISO8601 publish date")
    duration_seconds: Optional[int] = Field(None, description="Video duration")
    thumbnail_url: Optional[str] = Field(None, description="Video thumbnail")
    view_count: Optional[int] = Field(None, description="View count if available")
```

**Improvement 2: Add _merge_metadata_into_summary helper**
Similar to `_merge_supadata_metadata()` in source_identity.py

**Improvement 3: Store video_metadata in artifacts**
Like semantic pipeline does in source_identity stage

---

## Supporting Evidence

### Log traces (expected behavior)

**Semantic pipeline** (working):
```
[source_identity] Processing 1 video sources
  ✓ Transcript acquired: supadata_native (1500 words)
  ✓ Metadata acquired and merged for SRC_001
  Title: "How AI Will Change Everything"
  Creator: "Tech Insights"
  Duration: 600s
```

**Claim extraction** (broken):
```
[claim_extraction] Processing video 1/1
Supadata transcript: https://youtube.com/watch?v=... (mode=native)
Extracted 15 claims from YouTube video: Video 1  # ← Generic title
```

### Test Coverage Gap

**Semantic pipeline metadata tests:**
- `test_supadata_metadata.py` - 274 lines, 8 test methods
- Coverage: fetch_metadata, merge logic, pipeline integration

**Claim extraction metadata tests:**
- ❌ No tests for metadata in claim extraction
- ❌ No tests for SourceSummary metadata fields
- Gap: ~200 lines of test coverage needed

---

## Unresolved Questions

1. Should SourceSummary model be extended with all metadata fields, or should metadata be stored separately?
2. Should claims pipeline store metadata in artifacts.video_metadata like semantic pipeline?
3. Do we need migration for existing ClaimsDocuments with missing metadata?
4. Should we backfill metadata for completed claim extraction jobs?
5. What happens if fetch_metadata fails but get_transcript succeeds? (Current: continues with generic title)

---

## Next Steps

1. Fix transcript key bug (5 min)
2. Add metadata fetch to claim extraction pipeline (15 min)
3. Pass metadata through to extract_claims_from_youtube (10 min)
4. Test with real YouTube URL (5 min)
5. Verify doc 0 displays correct metadata (5 min)

**Total estimated time:** 40 minutes

Optional follow-up:
6. Extend SourceSummary model with metadata fields (20 min)
7. Add tests for claim extraction metadata (30 min)
8. Update to_markdown() to display metadata if present (15 min)

---

## References

**Code locations:**
- Broken: `backend/pipeline/claim_extraction.py:538-579`
- Working: `backend/pipeline/stages/source_identity.py:556-564`
- Model: `backend/models/claims.py:94-107`
- Client: `backend/integrations/supadata_client.py:73-129, 201-242`

**Commits:**
- `0fa98e9` - Added fetch_metadata to SupadataClient
- `02a9472` - Added merge logic to semantic pipeline
- `9f2cbc5` - Added Claim Extractor pipeline (didn't include metadata)
- `b94da6e` - Fixed article scraping (didn't fix video metadata)

**Tests:**
- `backend/tests/test_supadata_metadata.py` - Semantic pipeline tests
- Missing: Claim extraction metadata tests
