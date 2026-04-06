# Phase 09: Gemini Multimodal YouTube Fallback

## Context Links
- [Brainstorm -- Multimodal](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#idea-1-gemini-multimodal-fallback-when-supadata-fails)
- [Technical Validation](../../plans/reports/researcher-260406-1233-brainstorm-validation.md#claim-2-gemini-multimodal-youtube-fallback)
- Transcript acquisition: `backend/pipeline/transcript_acquisition.py`

## Overview
- **Priority:** P3 (Phase 2 -- Growth)
- **Status:** pending
- **Effort:** 3-5 days
- **Depends on:** Phase 00 (youtube-transcript-api removed)
- **Description:** Add Gemini 2.5 Pro multimodal as transcript fallback. Direct YouTube URL input -- no download needed. New confidence tier: `MULTIMODAL_INFERRED`. Cap at 60-minute videos.

## Key Insights
- Gemini 2.5 Pro accepts YouTube URLs directly via API. Samples ~1 frame/sec, 66 tokens/frame.
- 1hr video = ~238K input tokens. Cost is significant but acceptable as fallback.
- Quality: gives *understanding* not verbatim transcript. New confidence tier needed.
- Supadata remains primary. Whisper remains Tier 2. Gemini multimodal = Tier 3 (replaces removed youtube-transcript-api).
- Cap at 60 minutes. Beyond that, quality degrades at 260K+ tokens. Fall through to VIDEO_ONLY.

## Requirements

### Functional
- New fallback tier in transcript chain: Supadata -> Whisper -> **Gemini Multimodal** -> VIDEO_ONLY
- New confidence tier: `MULTIMODAL_INFERRED` (between CAPTION_GROUNDED and VIDEO_ONLY)
- Confidence ceiling for MULTIMODAL_INFERRED: MEDIUM (quotes allowed but marked approximate)
- Video duration check: skip multimodal if video > 60 minutes
- Hard warning propagated to ALL downstream docs: "Transcript derived from multimodal analysis, not verbatim"
- Cost tracked per multimodal call

### Non-Functional
- Multimodal call timeout: 120 seconds (long video processing)
- Cost per call: ~$0.30-0.60 for 30-60 min video (Gemini Pro pricing)
- Fallback should not slow pipeline if skipped (duration check is fast)

## Architecture

### Updated Fallback Chain
```
Tier 1: Supadata (cheapest, fastest, verbatim)
  ↓ fail
Tier 2: Whisper via yt-dlp (accurate, $0.006/min)
  ↓ fail
Tier 3: Gemini 2.5 Pro multimodal (understanding, not verbatim)
  ↓ fail or >60min
Tier 4: VIDEO_ONLY (metadata only, no transcript)
```

### Confidence Tier
```python
class TranscriptMode(str, Enum):
    TRANSCRIPT_GROUNDED = "transcript_grounded"    # Supadata, HIGH ceiling
    CAPTION_GROUNDED = "caption_grounded"          # Whisper, MEDIUM ceiling
    MULTIMODAL_INFERRED = "multimodal_inferred"    # Gemini multimodal, MEDIUM ceiling
    VIDEO_ONLY = "video_only"                      # No transcript, LOW ceiling
```

### Gemini Multimodal Call
```python
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        genai.types.Content(
            parts=[
                genai.types.Part(
                    file_data=genai.types.FileData(
                        file_uri=f"https://www.youtube.com/watch?v={video_id}"
                    )
                ),
                genai.types.Part(text="Transcribe and summarize this video. Extract all key statements, quotes, and factual claims with timestamps.")
            ]
        )
    ]
)
```

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/pipeline/transcript_acquisition.py` | Add `_try_gemini_multimodal()` as Tier 3. Update `acquire_transcript()` chain. |
| `backend/models/semantic_units.py` | Add `MULTIMODAL_INFERRED` to TranscriptMode enum (if not already) |
| `backend/pipeline/context.py` | Handle new mode in confidence ceiling lookup |
| `backend/pipeline/prompts/` | Add multimodal warning text to all downstream prompts |
| `backend/pipeline/cost_tracker.py` | Track Gemini Pro multimodal cost |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/pipeline/multimodal_transcript.py` | Gemini multimodal transcript extraction logic | ~80 |

## Implementation Steps

### Task 9.1: Add MULTIMODAL_INFERRED confidence tier
1. In `backend/models/semantic_units.py`, add `MULTIMODAL_INFERRED = "multimodal_inferred"` to TranscriptMode
2. In Architecture Rule 4 ceiling table equivalent in code:
   ```python
   CONFIDENCE_CEILINGS = {
       "multimodal_inferred": ConfidenceLevel.MEDIUM,
   }
   ```
3. Update any ceiling enforcement code to handle new mode

### Task 9.2: Create multimodal transcript function
1. Create `backend/pipeline/multimodal_transcript.py`
2. `async_gemini_multimodal_transcript(video_id: str, duration_seconds: int) -> tuple[str, str, float]`:
   - Return: (transcript_text, error_message, cost_credits)
   - Check duration: if > 3600 (60min), return `(None, "Video too long for multimodal", 0.0)`
   - Build Gemini 2.5 Pro call with YouTube URL
   - Prompt: "Transcribe this video. For each segment, provide timestamps and verbatim quotes where possible. Mark any paraphrased content."
   - Parse response into transcript text
   - Calculate cost: input_tokens * $1.25/1M + output_tokens * $10/1M
   - Error handling: timeout at 120s, API errors -> return None

### Task 9.3: Integrate into fallback chain
1. In `backend/pipeline/transcript_acquisition.py`:
   - After Whisper fails (Tier 2), before VIDEO_ONLY:
   - Call `_try_gemini_multimodal(video_id, duration_seconds)`
   - If successful, set mode to `MULTIMODAL_INFERRED`
   - Add warning: "Transcript derived from multimodal AI analysis. Quotes may be paraphrased."
2. Need video duration: extract from yt-dlp metadata (already available during acquisition)

### Task 9.4: Propagate warnings to downstream docs
1. In pipeline context, when mode is `MULTIMODAL_INFERRED`:
   - Add persistent warning to `ctx.warnings`
   - Include in Doc 0, Doc 1, Doc 2, Doc 3 headers
2. In extraction prompts, include: "This source transcript is AI-inferred, not verbatim. Mark all quotes as approximate."

### Task 9.5: Test
1. Unit test: duration cap (61 min -> skip)
2. Unit test: confidence ceiling enforcement for new mode
3. Integration test: mock Gemini multimodal response, verify transcript extraction
4. Manual: find a video where Supadata fails, verify Gemini fallback activates
5. `pytest backend/tests/ -v`

## Todo Checklist
- [ ] 9.1 Add `MULTIMODAL_INFERRED` to TranscriptMode enum and ceiling config
- [ ] 9.2 Create `multimodal_transcript.py` with Gemini Pro call
- [ ] 9.3 Integrate as Tier 3 in fallback chain
- [ ] 9.4 Propagate multimodal warnings to all downstream documents
- [ ] 9.5 Test: unit, integration, manual fallback verification

## Success Criteria
- Fallback chain: Supadata -> Whisper -> Gemini Multimodal -> VIDEO_ONLY
- Videos < 60 min get multimodal transcript when higher tiers fail
- Videos > 60 min skip to VIDEO_ONLY
- Confidence never exceeds MEDIUM for multimodal sources
- Warning visible in all output documents
- Cost tracked accurately

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini multimodal quality varies | MEDIUM | MULTIMODAL_INFERRED confidence tier + warning labels. |
| Cost spike on many fallbacks | MEDIUM | ~$0.30-0.60/video. Monitor. Supadata succeeds 90%+ of time. |
| Gemini API rate limits on Pro | LOW | Multimodal is fallback-only. Low volume. |
| YouTube URL format changes | LOW | Simple URL pattern. Google maintains backward compat. |

## Security Considerations
- No additional API keys needed (Gemini Pro already configured)
- Video content processed by Google's API -- same trust level as current Gemini usage
- Duration limit prevents token abuse
