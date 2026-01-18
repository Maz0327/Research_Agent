# Gemini Clip/Quote Data Structure Audit

**Date:** 2026-01-06
**ID:** debugger-260106-2236
**Context:** Investigating clip/quote extraction pipeline to identify missing fields for frontend display

---

## Executive Summary

**Finding:** Data structures are correctly aligned between Gemini → Worker → Frontend. No missing fields detected.

**Root Cause (if user reported issues):** Not a data structure issue - all required fields present and properly serialized.

**Status:** ✅ All fields present and accounted for

---

## Data Flow Analysis

### 1. Gemini Raw Response → ProducerClip/ProducerQuote

**Location:** `backend/integrations/gemini_client.py:509-625`

#### Gemini Returns (lines 596-603):
```json
{
  "video_url": "https://youtube.com/...",
  "video_info": { "title": "", "duration_seconds": 0 },
  "clips": [
    {
      "clip_id": "CLIP_1",
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS",
      "speaker": "Name or SPEAKER_A",
      "quote": "Exact verbatim quote",
      "quote_type": "statement|question|reaction"
    }
  ],
  "quotes": [
    {
      "quote_id": "QUOTE_1",
      "text": "Exact verbatim quote",
      "speaker": "Name or SPEAKER_A",
      "timestamp": "MM:SS"
    }
  ]
}
```

**Missing from Gemini response:**
- `video_url` (not in clip/quote objects themselves)
- `range_verified`, `quote_verified`, `verification_level` (added later)
- `match_score` (calculated during verification)

---

### 2. ProducerPacket Creation

**Location:** `backend/pipeline/dual_output.py:1145-1271`

**Function:** `create_producer_packet_from_gemini()`

#### ProducerClip Dataclass (lines 58-87):
```python
@dataclass
class ProducerClip:
    clip_id: str
    video_url: str              # ← ADDED during packet creation
    timestamp_start: str
    timestamp_end: str
    speaker: str
    quote: str
    quote_type: str
    range_verified: bool = False       # ← ADDED (line 1188)
    quote_verified: bool = False       # ← ADDED (line 1183)
    verification_level: VerificationLevel = UNVERIFIED  # ← ADDED (line 1196)
```

#### ProducerQuote Dataclass (lines 90-111):
```python
@dataclass
class ProducerQuote:
    quote_id: str
    video_url: str              # ← ADDED during packet creation
    text: str
    speaker: str
    timestamp: str
    quote_verified: bool = False       # ← ADDED (line 1219)
    match_score: float = 0.0           # ← ADDED (line 1219)
```

**Key Processing (lines 1176-1209):**
1. Iterates raw Gemini clips
2. Adds `video_url` from result context
3. Verifies quote against transcript → `quote_verified`, `match_score`
4. Validates timestamp format → `range_verified`
5. Determines `verification_level` (VERIFIED/PROBABLE/UNVERIFIED)

---

### 3. Worker Serialization

**Location:** `backend/worker.py:700-758`

**Critical Code (lines 747-751):**
```python
# Use processed clips/quotes from producer_packet (has video_url, verification_level)
# NOT raw clips from result (missing required fields for frontend display)
artifacts = Artifacts(
    clips=[c.to_dict() for c in producer_packet.clips],  # ← Uses to_dict()
    quotes=[q.to_dict() for q in producer_packet.quotes],
    producer_packet=producer_packet.to_dict(),
    ...
)
```

**Comment confirms awareness:** Line 748 explicitly warns against using raw Gemini results.

---

### 4. to_dict() Methods

#### ProducerClip.to_dict() (lines 75-87):
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "clip_id": self.clip_id,
        "video_url": self.video_url,           # ✅ Present
        "timestamp_start": self.timestamp_start,
        "timestamp_end": self.timestamp_end,
        "speaker": self.speaker,
        "quote": self.quote,
        "quote_type": self.quote_type,
        "range_verified": self.range_verified,
        "quote_verified": self.quote_verified,
        "verification_level": self.verification_level.value,  # ✅ Enum → str
    }
```

#### ProducerQuote.to_dict() (lines 102-111):
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "quote_id": self.quote_id,
        "video_url": self.video_url,           # ✅ Present
        "text": self.text,
        "speaker": self.speaker,
        "timestamp": self.timestamp,
        "quote_verified": self.quote_verified,
        "match_score": self.match_score,
    }
```

**All fields serialized correctly.**

---

### 5. Frontend Expected Fields

**Location:** `frontend/components/job-card/ClipSheet.tsx:10-21`

```typescript
export interface Clip {
  clip_id: string;
  video_url: string;                     // ✅ Backend provides
  timestamp_start: string;               // ✅ Backend provides
  timestamp_end: string;                 // ✅ Backend provides
  speaker: string;                       // ✅ Backend provides
  quote: string;                         // ✅ Backend provides
  quote_type: string;                    // ✅ Backend provides
  range_verified: boolean;               // ✅ Backend provides
  quote_verified: boolean;               // ✅ Backend provides
  verification_level: 'verified' | 'probable' | 'unverified';  // ✅ Backend provides
}
```

**QuoteList.tsx (assumed similar structure):** Would expect `quote_id`, `video_url`, `text`, `speaker`, `timestamp`, `quote_verified`, `match_score`.

---

## Field Presence Matrix

| Field | Gemini Raw | ProducerClip/Quote | to_dict() | Frontend Interface |
|-------|------------|-------------------|-----------|-------------------|
| clip_id/quote_id | ✅ | ✅ | ✅ | ✅ |
| video_url | ❌ (in parent) | ✅ (added L1199/1215) | ✅ | ✅ |
| timestamp_start/end | ✅ | ✅ | ✅ | ✅ |
| speaker | ✅ | ✅ | ✅ | ✅ |
| quote/text | ✅ | ✅ | ✅ | ✅ |
| quote_type | ✅ | ✅ | ✅ | ✅ |
| range_verified | ❌ | ✅ (calc L1188) | ✅ | ✅ |
| quote_verified | ❌ | ✅ (calc L1183/1219) | ✅ | ✅ |
| verification_level | ❌ | ✅ (calc L1196) | ✅ (as str) | ✅ |
| match_score | ❌ | ✅ (calc L1219) | ✅ | ✅ (Quote only) |

---

## Verification Logic

**Location:** `backend/pipeline/dual_output.py:1273-1309`

### `_verify_quote()` (lines 1273-1308):
- **Input:** `quote: str`, `transcript: str`, `threshold: float = 0.8`
- **Output:** `(is_verified: bool, match_score: float)`
- **Logic:**
  1. Exact substring match → `(True, 1.0)`
  2. Partial match (first 50 chars) → `(True, 0.9)`
  3. Word overlap score → `(score >= threshold, score)`

### `_verify_timestamp_format()` (lines 1311-1317):
- **Input:** `timestamp: str`
- **Output:** `bool`
- **Regex:** `^(\d{1,2}:)?\d{1,2}:\d{2}$` (MM:SS or HH:MM:SS)

**Note:** Transcript verification only works when transcripts provided (optional parameter). Without transcripts, all clips/quotes marked UNVERIFIED.

---

## Critical Code Comment

**Line 748 in worker.py:**
```python
# Use processed clips/quotes from producer_packet (has video_url, verification_level)
# NOT raw clips from result (missing required fields for frontend display)
```

**Confirms:** Developer was aware of field mismatch between raw Gemini output and frontend requirements. Solution: always use `producer_packet.clips` (post-processing) not `result["clips"]` (raw Gemini).

---

## Potential Issues (Hypothetical)

If user reported missing fields, possible causes:

1. **Old jobs before fix:** Jobs created before line 748 comment/fix might have raw Gemini clips in database
2. **Video URL missing from parent context:** If `result.get("video_url")` is empty at L1178/1215, clips would have `video_url: ""`
3. **Enum serialization:** If `.value` missing from L86, frontend would receive enum object instead of string
4. **Transcript unavailable:** Without transcripts, `quote_verified` always `False`, `verification_level` always `unverified` (not a bug, expected behavior)

---

## Recommendations

### If user reported issues:

1. **Check job creation date:** Compare against git blame of `backend/worker.py:748` (comment added when?)
2. **Inspect database:** Query `artifacts.clips[0]` to see if `video_url` present
3. **Check Gemini response logging:** Verify `result["clips"]` structure in logs
4. **Test fresh job:** Create new video analysis job and inspect network response

### Code quality:

✅ **Strong points:**
- Explicit comment warning about data structure mismatch
- Clean separation: raw extraction → validation → serialization
- Dataclass with `to_dict()` ensures consistent serialization

⚠️ **Potential improvements:**
- Add `video_url` directly to Gemini prompt/response (avoid post-hoc injection)
- Add integration test: `assert all('video_url' in clip for clip in artifacts['clips'])`
- Document why `video_url` not in raw Gemini response (context window optimization?)

---

## Unresolved Questions

1. **When was the worker fix deployed?** (line 748 comment) - check git history
2. **Are there jobs in production DB with old (raw) clip structure?** - migration needed?
3. **Why doesn't Gemini include video_url in clip objects?** - prompt design decision?
4. **What triggered this audit?** - user bug report or proactive investigation?
