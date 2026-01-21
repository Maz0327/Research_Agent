# Gemini 2.5 Pro Video Integration Implementation Plan

## Overview

Integrate Gemini 2.5 Pro's native multimodal video analysis into Research Agent's pipeline to replace Supadata/Whisper transcription for YouTube videos.

**Scope:** YouTube videos only (Phase 1)
**Budget Impact:** $0.14-1.16 per job (Flash/Pro) vs $0.30+ current
**Timeline:** 2-3 days for Phase 1

---

## Phase 1: YouTube Video Analysis (Week 1)

### 1.1 Create Gemini Video Client

**File:** `backend/integrations/gemini_video.py`

```python
from google import genai
from loguru import logger
from backend.config import settings

class GeminiVideoAnalyzer:
    """Analyze YouTube videos with Gemini 2.5 Pro/Flash."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.api_key = settings.require_google_api_key()
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    async def analyze_videos(
        self,
        video_urls: list[str],
        analysis_type: str = "documentary"
    ) -> dict:
        """Analyze up to 10 videos for documentary extraction."""
        # Implementation here
```

**Configuration:** `backend/config.py`

```python
GEMINI_VIDEO_MODEL: str = "gemini-2.5-flash"  # or "gemini-2.5-pro"
GOOGLE_API_KEY: Optional[str] = None

def require_google_api_key(self) -> str:
    if not self.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY required for Gemini video analysis")
    return self.GOOGLE_API_KEY
```

### 1.2 Create Pipeline Stage

**File:** `backend/pipeline/stages.py` - New function: `stage_6_video_extraction()`

Replace current transcript extraction with:

```python
async def stage_6_video_extraction(ctx: PipelineContext):
    """Extract claims, quotes, contradictions using Gemini 2.5 multimodal."""

    youtube_urls = [
        url for url in ctx.collected_urls
        if is_youtube_url(url)
    ]

    if not youtube_urls:
        ctx.add_warning("No YouTube videos found")
        return

    # Batch up to 10 videos per request
    for batch in chunks(youtube_urls, 10):
        result = await gemini_analyzer.analyze_videos(
            video_urls=batch,
            analysis_type=ctx.job.category or "general"
        )

        ctx.extracted_claims.extend(result.claims)
        ctx.timeline_moments.extend(result.moments)
        ctx.contradictions.extend(result.contradictions)
```

### 1.3 Schema & Data Models

**File:** `backend/models/video_extraction.py`

```python
from pydantic import BaseModel

class VideoQuote(BaseModel):
    timestamp: str  # MM:SS format
    speaker: str
    quote: str
    context: str
    video_url: str

class VideoMoment(BaseModel):
    timestamp: str
    video_url: str
    description: str
    moment_type: str  # "topic_shift", "visual_evidence", "claim", etc.

class VideoContradiction(BaseModel):
    video_1_url: str
    video_1_timestamp: str
    claim_1: str
    video_2_url: str
    video_2_timestamp: str
    claim_2: str
    contradiction_type: str  # "factual", "tone", "definition", etc.

class VideoAnalysisResult(BaseModel):
    quotes: list[VideoQuote]
    moments: list[VideoMoment]
    contradictions: list[VideoContradiction]
```

### 1.4 Testing

**File:** `backend/tests/test_gemini_video.py`

- Mock YouTube URL analysis (use test video)
- Validate timestamp format (MM:SS)
- Verify quote extraction with speaker attribution
- Test batch processing (max 10 videos)
- Test fallback to transcript if Gemini fails

---

## Phase 2: Cost Optimization (Week 2)

### 2.1 Model Selection Strategy

**Configuration:** `backend/models/job_config.py`

```python
class VideoAnalysisConfig:
    """Configure Gemini video analysis."""

    model: str = "gemini-2.5-flash"  # Default: cost-optimized
    use_pro_for_contradictions: bool = True  # Pro for validation
    max_video_length_minutes: int = 60  # Chunk if longer
    speaker_context: Optional[list[str]] = None  # Known speakers
```

**Logic:**
- Use Flash for initial pass (cost: $0.14/hour)
- Use Pro for contradiction resolution (cost: $1.16/hour, higher accuracy)
- Estimated total: $0.35/hour hybrid approach

### 2.2 Token Monitoring

**File:** `backend/utils/token_tracker.py`

```python
async def track_video_tokens(video_urls: list[str], model: str) -> int:
    """Estimate tokens before API call."""
    # ~258 tokens/sec default, 66 tokens/sec low resolution
    # Return estimated count for budget checking
```

---

## Phase 3: Non-YouTube Videos (Week 3+)

### 3.1 File Upload Support

**Extend:** `backend/integrations/gemini_video.py`

```python
async def analyze_video_file(
    self,
    file_path: str,
    analysis_type: str = "documentary"
) -> dict:
    """Upload and analyze non-YouTube video."""
    # Use Files API for upload
    # Process like YouTube URLs
```

### 3.2 Error Recovery

**Fallback chain:**
1. Gemini 2.5 multimodal (preferred)
2. Supadata transcription (if Gemini fails)
3. Whisper transcription (fallback)

---

## Configuration Checklist

- [ ] Add `GOOGLE_API_KEY` to `.env`
- [ ] Update `backend/config.py` with Google API settings
- [ ] Create `backend/integrations/gemini_video.py`
- [ ] Create `backend/models/video_extraction.py`
- [ ] Update `backend/pipeline/stages.py` with new stage
- [ ] Update `backend/pipeline/context.py` with video fields
- [ ] Add tests in `backend/tests/test_gemini_video.py`
- [ ] Update cost tracker for video tokens
- [ ] Test with 3-5 YouTube videos (various lengths)
- [ ] Validate timestamp accuracy
- [ ] Validate quote attribution accuracy

---

## Validation Criteria (Before Release)

- ✅ YouTube video processing without manual upload
- ✅ Timestamps accurate to second (MM:SS)
- ✅ Speaker attribution consistent across video
- ✅ Quote extraction captures full context
- ✅ Contradiction detection works cross-video (batch 10)
- ✅ Cost per job ≤ $1.50 (Flash) or $3.00 (Pro)
- ✅ Processing time <5 min per video on average
- ✅ Fallback to Supadata if Gemini fails

---

## Environment Variables Required

```
GOOGLE_API_KEY=<your-google-api-key>
GEMINI_VIDEO_MODEL=gemini-2.5-flash  # or gemini-2.5-pro
GEMINI_VIDEO_USE_LOW_RESOLUTION=false  # Cost optimization
```

---

## Success Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| YouTube coverage | 90%+ of research jobs | Direct API, no upload |
| Timestamp accuracy | 95%+ second-level | Per benchmark: 84.8% VideoMME |
| Quote attribution | 95%+ correct speaker | Harder with 4+ speakers |
| Cross-video contradictions | 90%+ detection | Multimodal advantage |
| Cost reduction | 50-70% vs current | $0.14-1.16 vs $0.30+ |
| Latency | <5 min/video avg | Depends on video length |

