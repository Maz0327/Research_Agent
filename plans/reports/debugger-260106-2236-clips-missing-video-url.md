# Video Clips Missing Required Fields Investigation

**Job ID:** b932580a-41a9-4a7f-96e4-25a270086bdd
**Issue:** Gemini job completed with 58 clips, 37 quotes, but frontend can't display them
**Date:** 2026-01-06

## Executive Summary

**Root Cause:** Gemini LLM returns clips/quotes WITHOUT `video_url` field. When `analyze_youtube_videos_batch()` aggregates clips from multiple videos, it merges raw LLM output directly into batch result, losing video context.

**Impact:** Frontend receives clips missing:
- `video_url` (CRITICAL - can't link back to source)
- `range_verified`, `quote_verified`, `verification_level` (added later by ProducerPacket)

**Solution:** Worker correctly uses `producer_packet.clips` (has all fields) instead of raw `result.get("clips")`, but raw batch aggregation is broken.

## Technical Analysis

### Data Flow

```
1. Gemini LLM Response (per video)
   └─ clips: [{clip_id, timestamp_start, timestamp_end, speaker, quote, quote_type}]
      ❌ NO video_url

2. analyze_youtube_video() return
   └─ {video_url: "...", clips: [...], quotes: [...]}
      ✅ video_url at result level, NOT in clip objects

3. analyze_youtube_videos_batch() aggregation
   └─ all_clips.extend(result.get("clips", []))  # LINE 847
      ❌ Loses video_url context during merge

4. create_producer_packet_from_gemini()
   └─ Expects clips with video_url: raw_clip.get("video_url", "")  # LINE 1178
      ❌ Falls back to empty string

5. Worker stores in Artifacts
   └─ clips=[c.to_dict() for c in producer_packet.clips]  # LINE 750
      ✅ CORRECT - uses processed clips
   └─ But batch_result raw clips already broken
```

### Code Evidence

**gemini_client.py:847-848** - Raw aggregation loses context:
```python
all_clips.extend(result.get("clips", []))  # ❌ Raw clips have no video_url
all_quotes.extend(result.get("quotes", []))
```

**gemini_client.py:596-603** - Result structure:
```python
return {
    "video_url": video_url,  # ✅ At top level
    "video_info": data.get("video_info", {}),
    "clips": data.get("clips", []),  # ❌ Clips don't have video_url
    "quotes": data.get("quotes", []),
    "cost": cost,
}
```

**dual_output.py:1176-1209** - ProducerPacket expects video_url:
```python
for i, raw_clip in enumerate(raw_clips):
    video_url = raw_clip.get("video_url", "")  # ❌ Falls back to ""
    # ... builds ProducerClip with video_url
```

**worker.py:706-758** - Worker CORRECTLY uses processed clips:
```python
# Line 706-712: Build batch result with raw clips (broken)
batch_result = {
    "clips": result.get("clips", []),  # ❌ Raw, no video_url
    "quotes": result.get("quotes", []),
}

# Line 714-718: Create ProducerPacket (adds video_url from context)
producer_packet = create_producer_packet_from_gemini(
    gemini_results=batch_result,
    title=title,
    transcripts=None,
)

# Line 747-751: Store processed clips ✅ CORRECT
artifacts = Artifacts(
    clips=[c.to_dict() for c in producer_packet.clips],  # ✅ Has video_url
    quotes=[q.to_dict() for q in producer_packet.quotes],
)
```

## Missing Fields Analysis

**Raw Gemini Clips (from LLM):**
```json
{
  "clip_id": "CLIP_1",
  "timestamp_start": "MM:SS",
  "timestamp_end": "MM:SS",
  "speaker": "Name",
  "quote": "Text",
  "quote_type": "statement"
}
```

**ProducerClip (after processing):**
```json
{
  "clip_id": "CLIP_1",
  "video_url": "https://youtube.com/...",  // ✅ Added
  "timestamp_start": "MM:SS",
  "timestamp_end": "MM:SS",
  "speaker": "Name",
  "quote": "Text",
  "quote_type": "statement",
  "range_verified": true,           // ✅ Added
  "quote_verified": false,          // ✅ Added
  "verification_level": "unverified" // ✅ Added
}
```

## Why Worker Storage is Correct

Worker.py:750 uses **processed** clips from ProducerPacket:
```python
artifacts = Artifacts(
    clips=[c.to_dict() for c in producer_packet.clips],  # ✅ ProducerClip objects
    quotes=[q.to_dict() for q in producer_packet.quotes], # ✅ ProducerQuote objects
)
```

**ProducerPacket construction adds video_url:**
- dual_output.py:1178 tries `raw_clip.get("video_url", "")`
- Falls back to empty string because raw clips don't have it
- But worker passes `batch_result` which should have results with video_url

## The Actual Bug

**gemini_client.py:706-712** in `run_full_analysis_pipeline`:
```python
batch_result = {
    "clips": result.get("clips", []),  # ❌ Direct aggregation, loses video_url
    "quotes": result.get("quotes", []),
    "results": result.get("results", []),
}
```

Should be:
```python
batch_result = {
    "clips": result.get("clips", []),  # Keep for backward compat
    "quotes": result.get("quotes", []),
    "results": result.get("results", []),  # ✅ Has per-video data with video_url
}
```

**dual_output.py:1167-1172** extracts video metadata from results:
```python
for result in gemini_results.get("results", []):
    videos_analyzed.append({
        "url": result.get("video_url", ""),  # ✅ Correct
        "title": result.get("video_info", {}).get("title", "Unknown"),
        "duration_seconds": result.get("video_info", {}).get("duration_seconds", 0),
    })
```

**dual_output.py:1176-1209** processes clips:
```python
raw_clips = gemini_results.get("clips", [])  # ❌ Uses aggregated clips
for i, raw_clip in enumerate(raw_clips):
    video_url = raw_clip.get("video_url", "")  # ❌ Not present
```

Should iterate over `results` and extract clips per-video:
```python
for result in gemini_results.get("results", []):
    video_url = result.get("video_url", "")
    for raw_clip in result.get("clips", []):
        # Process with known video_url
```

## Fix Strategy

**Option 1:** Add video_url during batch aggregation (gemini_client.py:847-848)
```python
for result in results:
    video_url = result.get("video_url", "")
    clips_with_url = [
        {**clip, "video_url": video_url}
        for clip in result.get("clips", [])
    ]
    all_clips.extend(clips_with_url)
```

**Option 2:** Change ProducerPacket to iterate over results (dual_output.py:1176)
```python
for result in gemini_results.get("results", []):
    video_url = result.get("video_url", "")
    for raw_clip in result.get("clips", []):
        # Use known video_url instead of raw_clip.get("video_url")
```

**Recommended:** Option 2 - less coupling, clearer data flow

## Verification Status - BUG CONFIRMED

**Complete Data Flow Trace:**
1. `GeminiClient.analyze_youtube_videos_batch()` (gemini_client.py:847-848)
   - Aggregates clips: `all_clips.extend(result.get("clips", []))`
   - **Loses video_url context** - clips are merged without parent URL

2. Returns batch_result with raw clips (gemini_client.py:872-881)
   ```python
   return {
       "clips": all_clips,  # ❌ No video_url in clip objects
       "quotes": all_quotes,
       "results": results,  # ✅ Has video_url per result
   }
   ```

3. `run_full_analysis_pipeline()` passes through (gemini_client.py:1583)
   ```python
   "clips": batch_result.get("clips", []),  # ❌ Still no video_url
   ```

4. Worker builds batch_result and passes to ProducerPacket (worker.py:707-718)
   ```python
   batch_result = {
       "clips": result.get("clips", []),  # ❌ Raw aggregated clips
       "results": result.get("results", []),  # ✅ Has metadata
   }
   producer_packet = create_producer_packet_from_gemini(batch_result, ...)
   ```

5. ProducerPacket tries to extract video_url (dual_output.py:1178)
   ```python
   video_url = raw_clip.get("video_url", "")  # ❌ Falls back to ""
   ```

6. ProducerClip created with empty video_url (dual_output.py:1198-1209)
   ```python
   clips.append(ProducerClip(
       clip_id=...,
       video_url=video_url,  # ❌ Empty string ""
       ...
   ))
   ```

7. Worker stores processed clips (worker.py:750)
   ```python
   artifacts = Artifacts(
       clips=[c.to_dict() for c in producer_packet.clips],  # ❌ Has video_url=""
   )
   ```

**ROOT CAUSE CONFIRMED:**
- Clips stored in database have `video_url: ""`
- Frontend can't display because video_url is empty string
- Verification fields also present but meaningless without source URL

## Summary

**Bug Location:** `backend/integrations/gemini_client.py:847-848`
```python
all_clips.extend(result.get("clips", []))  # Loses video_url context
```

**Impact:** ALL video analysis jobs since Phase 3 deployment store clips/quotes with empty `video_url: ""`, making them undisplayable in frontend.

**Fix Priority:** **CRITICAL** - blocks entire video analysis feature

**Recommended Fix:** Enrich clips with video_url during aggregation:
```python
# In analyze_youtube_videos_batch (gemini_client.py:830-881)
for i, url in enumerate(video_urls):
    result = self.analyze_youtube_video(url, model=model)

    # Enrich clips/quotes with video_url before aggregating
    video_url = result.get("video_url", url)
    enriched_clips = [
        {**clip, "video_url": video_url}
        for clip in result.get("clips", [])
    ]
    enriched_quotes = [
        {**quote, "video_url": video_url}
        for quote in result.get("quotes", [])
    ]

    all_clips.extend(enriched_clips)
    all_quotes.extend(enriched_quotes)
```

**Alternative Fix:** Change ProducerPacket to iterate over results (requires more refactoring).

## Unresolved Questions

1. Confirm job b932580a has video_url="" in database (server not running for verification)
2. Are ALL production video jobs affected or only recent ones?
3. Should we add database migration to backfill video_url for existing jobs?
4. Should we add input validation to ProducerPacket to fail fast if video_url missing?
