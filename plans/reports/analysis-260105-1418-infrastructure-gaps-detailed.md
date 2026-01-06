# Infrastructure Gaps: Detailed Reference

**Date:** 2026-01-05
**Context:** Gaps identified during ChatGPT/Claude review of strategic pivot plan
**Status:** Reference for Phase 1.5 implementation

---

## Gap 1: Celery Task Timeout

**Problem:** Default Celery timeout (often 5-10 min) will kill Gemini tasks mid-processing.

**Evidence:** 2-hour video → 5-10 min Gemini analysis time.

**Fix:**
```python
# In worker.py or celery config
@celery.task(time_limit=1800, soft_time_limit=1500)  # 30 min hard, 25 min soft
def gemini_extraction_task(job_id, urls):
    ...
```

**Check current config:**
```python
# Look for these in celery config
CELERY_TASK_TIME_LIMIT = ???
CELERY_TASK_SOFT_TIME_LIMIT = ???
```

**Priority:** HIGH — Gemini will fail without this.

---

## Gap 2: Per-Video Error Handling

**Problem:** If video 3/5 fails (private, age-restricted, region-locked), whole job fails.

**Fix:**
```python
results = {}
errors = []

for i, url in enumerate(urls):
    try:
        results[f"video_{i+1}"] = await process_video(url)
    except VideoUnavailableError as e:
        errors.append({"video": url, "error": str(e), "status": "skipped"})

# Job completes with partial results + warnings
return {
    "results": results,
    "errors": errors,
    "status": "completed_with_warnings" if errors else "completed"
}
```

**Priority:** HIGH — One bad URL shouldn't crash entire job.

---

## Gap 3: Per-Video Progress Updates

**Problem:** User sees "processing" for 15 min with no feedback.

**Current:** `pending → processing → complete`

**Fix:**
```python
await update_job(job_id, {
    "status": "processing",
    "stage": "gemini_extraction",
    "progress": {
        "current_video": 2,
        "total_videos": 5,
        "current_video_url": "youtube.com/...",
        "videos_completed": ["video_1"],
        "videos_pending": ["video_3", "video_4", "video_5"]
    }
})
```

**Frontend:** Show "Processing video 2 of 5..." instead of spinner.

**Priority:** MEDIUM — UX improvement, not blocking.

---

## Gap 4: Duration/Cost Limits

**Problem:** User submits 10 × 2-hour videos = 20 hours = $23 at Pro rates.

**Fix:**
```python
MAX_TOTAL_DURATION_MINUTES = 300  # 5 hours max
MAX_VIDEOS_PER_JOB = 10
COST_WARNING_THRESHOLD = 5.00
COST_HARD_CAP = 10.00

async def validate_job_inputs(urls: list[str]) -> ValidationResult:
    durations = [await get_video_duration(url) for url in urls]
    total_minutes = sum(durations)

    if total_minutes > MAX_TOTAL_DURATION_MINUTES:
        return ValidationResult(
            valid=False,
            error=f"Total duration {total_minutes}min exceeds {MAX_TOTAL_DURATION_MINUTES}min limit"
        )

    estimated_cost = calculate_cost(total_minutes)
    if estimated_cost > COST_HARD_CAP:
        return ValidationResult(valid=False, error=f"Estimated cost ${estimated_cost} exceeds limit")

    return ValidationResult(
        valid=True,
        warnings=[f"Estimated cost: ${estimated_cost}"] if estimated_cost > COST_WARNING_THRESHOLD else []
    )
```

**Priority:** MEDIUM — Prevents runaway costs.

---

## Gap 5: Chunk Strategy for Long Videos

**Problem:** Gemini accuracy degrades to 40-50% on videos >3 hours.

**Fix:**
```python
CHUNK_DURATION_SECONDS = 3600  # 1 hour chunks

async def process_long_video(url: str, total_duration: int) -> list[dict]:
    if total_duration <= CHUNK_DURATION_SECONDS:
        return [await process_video_chunk(url, 0, total_duration)]

    chunks = []
    for start in range(0, total_duration, CHUNK_DURATION_SECONDS):
        end = min(start + CHUNK_DURATION_SECONDS, total_duration)
        chunk_result = await process_video_chunk(url, start, end)
        chunks.append(chunk_result)

    return merge_chunk_results(chunks)
```

**Gemini time ranges:**
```python
f"{video_url}#t={start_seconds},{end_seconds}"
```

**Priority:** MEDIUM — Needed for long interviews/documentaries.

---

## Gap 6: Timestamp Alignment Verification

**Problem:** Current plan only checks timestamp within video bounds. Doesn't verify quote near timestamp.

**Current (weak):**
```python
timestamp_verified = parse_timestamp(clip.timestamp) < video_duration_seconds
```

**Better (if timestamped transcript available):**
```python
def verify_timestamp_alignment(clip, timestamped_transcript, tolerance_seconds=30):
    claimed_time = parse_timestamp(clip.timestamp)

    for segment in timestamped_transcript:
        if clip.quote.lower() in segment.text.lower():
            actual_time = segment.start_time
            if abs(claimed_time - actual_time) <= tolerance_seconds:
                return True, actual_time
            else:
                return False, actual_time  # Quote exists but wrong timestamp

    return None, None  # Quote not found
```

**Note:** Requires Gemini to return timestamped transcript. Test in Phase 1.

**Priority:** LOW — Enhancement after core works.

---

## Gap 7: Unverified Content UX

**Problem:** Plan has verification flags but no UX spec.

**Recommendation:**
1. **Show everything** — Don't hide unverified (might be valid)
2. **Sort verified first** — Green checkmarks at top
3. **Visual distinction** — Unverified items muted
4. **Filter option** — Toggle "show only verified"

```typescript
<ClipSheet>
  {clips
    .sort((a, b) => (b.quote_verified ? 1 : 0) - (a.quote_verified ? 1 : 0))
    .map(clip => (
      <ClipCard
        key={clip.clip_id}
        clip={clip}
        verified={clip.quote_verified && clip.timestamp_verified}
        className={clip.quote_verified ? '' : 'opacity-70'}
      />
    ))}
</ClipSheet>
```

**Priority:** LOW — Phase 5 frontend work.

---

## Summary

| Gap | Priority | When | File |
|-----|----------|------|------|
| Celery timeout | HIGH | Phase 1.5 | `backend/worker.py` |
| Per-video errors | HIGH | Phase 1.5 | `backend/worker.py` |
| Progress updates | MEDIUM | Phase 1.5 | `backend/pipeline/stages.py` |
| Duration limits | MEDIUM | Phase 1.5 | `backend/app/routes/jobs_routes.py` |
| Chunk strategy | MEDIUM | Phase 1.5 | `backend/integrations/gemini_client.py` |
| Timestamp alignment | LOW | Phase 2+ | `backend/pipeline/extraction.py` |
| Unverified UX | LOW | Phase 5 | `frontend/components/ClipSheet.tsx` |

---

## Source

Analysis from ChatGPT/Claude conversation: `App Improvement Strategy Evaluation (3).md` (lines 3349-3500)
