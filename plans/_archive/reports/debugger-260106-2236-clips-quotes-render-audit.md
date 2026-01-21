# Frontend Clips/Quotes Rendering Audit

**Date:** 2026-01-06
**Job ID:** a608d85
**Issue:** Job completed with 58 clips and 37 quotes but they don't display

## Root Cause Analysis

### Working as Designed

The backend **correctly** populates clips and quotes with all required fields. Worker uses `producer_packet.clips` and `producer_packet.quotes` which have `video_url` field (backend/worker.py:750-751):

```python
artifacts = Artifacts(
    clips=[c.to_dict() for c in producer_packet.clips],  # ProducerClip.to_dict() includes video_url
    quotes=[q.to_dict() for q in producer_packet.quotes],  # ProducerQuote.to_dict() includes video_url
    producer_packet=producer_packet.to_dict(),
    quality_gate_passed=passes_gate,
)
```

### Component Analysis

#### 1. ClipSheet.tsx (frontend/components/job-card/ClipSheet.tsx)

**Required Fields for Clip:**
```typescript
interface Clip {
  clip_id: string;
  video_url: string;          // REQUIRED for timestamp links
  timestamp_start: string;
  timestamp_end: string;
  speaker: string;
  quote: string;
  quote_type: string;
  range_verified: boolean;
  quote_verified: boolean;
  verification_level: 'verified' | 'probable' | 'unverified';
}
```

**Backend ProducerClip.to_dict() provides:**
- ✅ clip_id
- ✅ video_url
- ✅ timestamp_start
- ✅ timestamp_end
- ✅ speaker
- ✅ quote
- ✅ quote_type
- ✅ range_verified
- ✅ quote_verified
- ✅ verification_level (enum value)

**Rendering Logic:**
- Line 215-221: Shows "No clips extracted" if `clips.length === 0`
- Line 186-204: Filters by verification level
- Line 261-263: Maps filtered clips to ClipCard components
- Line 98: **Uses `video_url` to generate YouTube timestamp link**

**Conditional Rendering:**
- Line 200-204: Filter by `showVerifiedOnly` prop (hides unverified if true)
- Line 200-204: Filter by verification level (all/verified/probable)
- Line 266-270: Shows "No clips match filter" if filtered list empty

#### 2. QuoteList.tsx (frontend/components/job-card/QuoteList.tsx)

**Required Fields for Quote:**
```typescript
interface Quote {
  quote_id: string;
  video_url: string;          // REQUIRED for timestamp links
  text: string;
  speaker: string;
  timestamp: string;
  quote_verified: boolean;
  match_score: number;
}
```

**Backend ProducerQuote.to_dict() provides:**
- ✅ quote_id
- ✅ video_url
- ✅ text
- ✅ speaker
- ✅ timestamp
- ✅ quote_verified
- ✅ match_score

**Rendering Logic:**
- Line 195-201: Shows "No quotes extracted" if `quotes.length === 0`
- Line 169-189: Filters by verification status
- Line 238-240: Maps filtered quotes to QuoteCard components
- Line 68: **Uses `video_url` to generate YouTube timestamp link**

**Conditional Rendering:**
- Line 185: Filter by `showVerifiedOnly` prop (hides low-score if true)
- Line 187-188: Filter by verified/unverified
- Line 243-247: Shows "No quotes match filter" if filtered list empty

#### 3. JobResults.tsx (frontend/components/job-card/JobResults.tsx)

**Data Flow:**
```typescript
interface VideoArtifacts {
  clips?: Clip[];           // From job.artifacts.clips
  quotes?: Quote[];         // From job.artifacts.quotes
  producer_packet?: {...};
  quality_gate_passed?: boolean;
}
```

**Rendering Logic:**
- Line 75-76: Shows results for `completed`, `completed_with_warnings`, `failed_insufficient`
- Line 77-78: Extracts clips/quotes from artifacts: `artifacts.clips || []`
- Line 150: Shows tabs **only if** `clips.length > 0 || quotes.length > 0 || ...`
- Line 212-213: Passes clips/quotes to ClipSheet/QuoteList components

**Conditional Rendering:**
- Line 75-76: Must be video_analysis pipeline + completed status
- Line 150: Tabs hidden if no data exists
- No `showVerifiedOnly` prop passed (defaults to false)

#### 4. Jobs Store (frontend/store/jobs.ts)

**State Management:**
- Line 411-445: `refreshJob()` fetches job and updates artifacts
- Line 439: Maps `data.artifacts` directly to job state
- No transformation/filtering of clips/quotes

**Type Definitions Match Backend:**
```typescript
// Lines 48-72
interface Clip { ... }      // Matches ProducerClip
interface Quote { ... }     // Matches ProducerQuote
```

## Possible Causes of Non-Display

### 1. Empty Arrays from Backend
If backend returns `clips: []` and `quotes: []`:
- JobResults shows quality gate panel but **no tabs** (line 150 condition)
- ClipSheet shows "No clips extracted" message (line 215-221)
- QuoteList shows "No quotes extracted" message (line 195-201)

### 2. All Clips/Quotes Filtered Out
If `showVerifiedOnly=true` and all data is unverified:
- ClipSheet filters to empty list (line 200-204)
- QuoteList filters to empty list (line 184-189)
- Shows "No clips/quotes match filter" (line 266-270, 243-247)

### 3. Job Status Not in Valid Set
If job status is not `completed`, `completed_with_warnings`, or `failed_insufficient`:
- JobResults returns null (line 286)
- No clips/quotes displayed at all

### 4. Pipeline Type Mismatch
If `pipeline !== 'video_analysis'`:
- Video results section skipped (line 76)
- Falls through to topic research section or null

### 5. Missing `artifacts` Object
If `job.artifacts` is null/undefined:
- `artifacts.clips` evaluates to undefined
- `clips || []` becomes `[]`
- Displays "No clips extracted"

### 6. Frontend Type Mismatch
If backend sends wrong field names:
- TypeScript interfaces expect exact field names
- Missing `video_url` → runtime error when generating links (line 98/68)
- Would show in browser console

## Debugging Recommendations

1. **Check Browser Console** for:
   - TypeScript errors
   - Failed API calls
   - Missing field errors

2. **Inspect Job Record** in database:
   ```sql
   SELECT artifacts FROM jobs WHERE job_id = '<job_id>';
   ```
   - Verify `clips` and `quotes` arrays not empty
   - Verify `video_url` field exists in each object

3. **Check Frontend Network Tab**:
   - GET `/jobs/{id}` response includes artifacts
   - Verify JSON structure matches TypeScript interfaces

4. **Verify Job Status**:
   - Must be: `completed`, `completed_with_warnings`, or `failed_insufficient`
   - Check `pipeline` field is `video_analysis`

5. **Check Filter State**:
   - Open React DevTools
   - Find ClipSheet/QuoteList components
   - Check `filter` state and `filteredClips`/`filteredQuotes` arrays

6. **Verify Backend Serialization**:
   - Log `producer_packet.clips[0].to_dict()` in worker
   - Confirm all fields present before storing

## Required Fields Summary

### Clips (ClipSheet)
- ✅ clip_id, video_url, timestamp_start, timestamp_end, speaker, quote, quote_type, range_verified, quote_verified, verification_level

### Quotes (QuoteList)
- ✅ quote_id, video_url, text, speaker, timestamp, quote_verified, match_score

### Conditional Logic That Could Hide Data

**ClipSheet:**
- `showVerifiedOnly=true` → hides unverified clips
- Filter state → hides non-matching clips
- Empty array → shows "No clips" message

**QuoteList:**
- `showVerifiedOnly=true` → hides quotes with match_score < 0.8
- Filter state → hides non-matching quotes
- Empty array → shows "No quotes" message

**JobResults:**
- Status not in {completed, completed_with_warnings, failed_insufficient} → returns null
- Pipeline not "video_analysis" → skips video section
- clips.length === 0 AND quotes.length === 0 → hides tabs entirely

## Unresolved Questions

1. What is the actual job status for the job with 58 clips/37 quotes?
2. Are clips/quotes actually in database `artifacts` field or only in `producer_packet`?
3. Is browser console showing any errors?
4. What does network response for GET `/jobs/{id}` show?
5. Is `showVerifiedOnly` prop being passed somewhere in parent component?
