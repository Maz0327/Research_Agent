# E2E Test Report: Video Analysis (Pro Model)

**Date:** 2026-01-11 20:20 PST
**Job ID:** `a732085a-d50a-4779-a7a0-5b792f0291ac`
**Model:** `gemini-2.5-pro`
**Environment:** Production (Railway)

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Videos submitted | 5 |
| Model | gemini-2.5-pro |
| Estimated cost | $3.75 |
| Estimated duration | 50 min |

### Input URLs
1. `https://www.youtube.com/watch?v=5RZqgIzUn6w`
2. `https://www.youtube.com/watch?v=3CosWOMIvMQ`
3. `https://www.youtube.com/watch?v=fNgRdEpZC50`
4. `https://www.youtube.com/watch?v=UgL7xTERfxw`
5. `https://www.youtube.com/watch?v=hmx5auvTspU`

---

## Results Summary

| Metric | Value |
|--------|-------|
| **Final Status** | `completed_with_warnings` |
| **Total Duration** | ~11 minutes (20:04:27 → 20:15:08) |
| **Clips Extracted** | 38 |
| **Quotes Extracted** | 36 |
| **Quality Gate** | PASSED |
| **Videos Processed** | 4 of 5 |

---

## Progress Timeline

```
[20:04:27] 5%   - Job started
[20:11:03] 27%  - First video processing
[20:14:06] 50%  - Mid-point
[20:14:37] 72%  - Near completion
[20:15:08] 100% - Completed with warnings
```

---

## Clips Breakdown by Video

| Video ID | Clips |
|----------|-------|
| 5RZqgIzUn6w | 12 |
| fNgRdEpZC50 | 8 |
| UgL7xTERfxw | 10 |
| hmx5auvTspU | 8 |
| **3CosWOMIvMQ** | **0 (MISSING)** |

**Total:** 38 clips

---

## Verification Statistics

| Metric | Count | Rate |
|--------|-------|------|
| Quote verified | 0 | 0% |
| Range verified | 38 | 100% |

**Note:** All quotes marked `quote_verified: false` but `range_verified: true`. This indicates timestamps are accurate but verbatim text could not be verified against transcript.

---

## Sample Clips Output

```json
{
  "clip_id": "CLIP_1",
  "speaker": "Carlos Ghosn",
  "quote": "Everyone wanted to be in my shoes.",
  "timestamp_start": "00:08",
  "timestamp_end": "00:11",
  "video_url": "https://www.youtube.com/watch?v=5RZqgIzUn6w",
  "quote_type": "statement",
  "quote_verified": false,
  "range_verified": true,
  "verification_level": "unverified"
}
```

---

## Issues Identified

### 1. Missing Video (3CosWOMIvMQ)

**Severity:** Medium
**Impact:** 1 of 5 videos not processed

The video `https://www.youtube.com/watch?v=3CosWOMIvMQ` produced 0 clips.

**Video Details:**
- Title: "Carlos Ghosn : les dessous de sa grande évasion"
- Author: Investigation
- Language: **French**

Likely causes:
- French language transcript may have failed to parse
- Gemini extraction may have encountered language-specific issues
- Transcript acquisition failed for this specific video

**Action needed:** Check worker logs for this specific video's processing status.

### 2. No Quote Verification

**Severity:** Low
**Impact:** All 38 clips have `quote_verified: false`

This indicates transcript-based verification is not working or transcripts were not available. All clips have `range_verified: true`, meaning timestamp accuracy was confirmed but verbatim quote matching failed.

### 3. Warnings Not Visible in API Response

**Severity:** Low
**Impact:** Debugging difficulty

Status was `completed_with_warnings` but the `warnings` array in the job record was empty. Warning details are not being surfaced to the API response.

---

## Conclusions

### What Worked
- Job creation and queueing ✅
- Progress tracking (5% → 27% → 50% → 72% → 100%) ✅
- Gemini extraction for 4/5 videos ✅
- Clips with timestamps extracted ✅
- Quality gate passed ✅
- Producer packet structure correct ✅

### What Needs Investigation
- [ ] Why video `3CosWOMIvMQ` was skipped
- [ ] Why `quote_verified` is always `false` (transcript issue?)
- [ ] Why warnings array is empty despite `completed_with_warnings` status

---

## Unresolved Questions

1. Is video `3CosWOMIvMQ` a valid, public video?
2. Are transcripts being fetched successfully? (Supadata → YouTube captions fallback)
3. Should the warnings be populated in the job record for debugging?

---

**End of Report**
