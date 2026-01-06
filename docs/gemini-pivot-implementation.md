# Gemini Pivot Implementation Documentation

**Date:** January 5, 2026
**Branch:** `feature/vision-alignment-v1`
**Status:** Phase 5 Complete - Frontend Display Components

---

## Executive Summary

This document captures the complete decision-making process, technical implementation, and reasoning behind the Research Agent's strategic pivot from topic-based research to URL-first video analysis powered by Gemini 2.5.

**The Core Pivot:**
| Before | After |
|--------|-------|
| User enters topic | User enters YouTube URLs |
| System finds sources | System analyzes user's sources |
| Output: Documents, walls of text | Output: Timestamped clips + quotes |
| Value: Breadth (find sources) | Value: Depth (make sources scannable) |

---

## Table of Contents

1. [Strategic Decision](#1-strategic-decision)
2. [Options Evaluated](#2-options-evaluated)
3. [User Feedback That Drove This Change](#3-user-feedback-that-drove-this-change)
4. [Technical Implementation](#4-technical-implementation)
5. [Files Changed](#5-files-changed)
6. [Data Structures](#6-data-structures)
7. [Quality Gate](#7-quality-gate)
8. [Frontend Components](#8-frontend-components)
9. [Cost Model](#9-cost-model)
10. [How to Revert](#10-how-to-revert)
11. [Future Enhancements](#11-future-enhancements)

---

## 1. Strategic Decision

### The Problem We Solved

User feedback (100% of surveyed users) identified these issues with the original system:
- **Sources wrong/irrelevant** - AI-discovered content didn't match user needs
- **Not enough depth** - Too shallow, missing key info
- **Can't find specific info** - Buried in walls of text
- **No timestamps/clips** - Video creators need specific moments
- **Feels thin/generic** - "Info I can find on Google in 2 mins"

### The Insight

> **The bottleneck isn't finding sources — it's extracting usable moments from long sources.**

| Task | User Time | AI Value |
|------|-----------|----------|
| Finding videos on topic | 30 min | Low — Google works |
| Watching 2-hr video for 5 min of content | 2+ hrs | **HIGH — THIS IS THE BOTTLENECK** |
| Taking notes with timestamps | 1 hr | High |
| Figuring out the story | Variable | None — keep this human |

### The Decision: Option A (Full Pivot)

Three options were evaluated:

| Option | Description | Verdict |
|--------|-------------|---------|
| **A: Full Pivot** | Replace topic flow with URL-first | ✅ **CHOSEN** |
| B: Keep Both Modes | Parallel pipelines | Complexity risk |
| C: Refactor Integration | Move Gemini into existing Stage 6 | Partial solution |

**Why Option A?** All strategic documents agreed: This is a **replacement**, not a supplement. The existing architecture optimized for breadth; users need depth.

---

## 2. Options Evaluated

### Option A: Full Pivot (CHOSEN)

**Pros:**
- Matches all strategic document recommendations
- Simpler architecture (one path)
- User provides sources → guaranteed relevance
- Gemini handles timestamps natively

**Cons:**
- Users must have URLs already
- Discovery phase removed

### Option B: Keep Both Modes

**Pros:**
- Covers users without URLs
- Gradual migration path

**Cons:**
- Doubles maintenance surface
- Confusing UX (which mode?)
- Splits development focus

### Option C: Refactor Integration

**Pros:**
- Less disruptive
- Reuses existing pipeline

**Cons:**
- Franken-architecture
- Doesn't address core problem
- Topic → discovery → extraction still produces irrelevant sources

---

## 3. User Feedback That Drove This Change

### Direct Quotes from User Research

1. "I spend hours finding the 5 good minutes in a 2-hour podcast"
2. "The documents are nice but I need timestamps for editing"
3. "I already know which videos I want analyzed, just help me extract"
4. "Stop finding sources for me, I have my sources"
5. "Every clip needs a timestamp or it's useless"

### Key Insight

Users aren't asking "what should I research?" — they're asking "help me process what I already found."

---

## 4. Technical Implementation

### Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Fix extraction bug (canonical_claim fallback) | ✅ Complete |
| 1 | Test Gemini extraction (4/4 videos passed) | ✅ Complete |
| 1.5 | Infrastructure (timeouts, chunking, error handling) | ✅ Complete |
| 2 | ProducerPacket models and export | ✅ Complete |
| 3 | Backend API (video-analysis endpoint) | ✅ Complete |
| 4 | Frontend (mode toggle, URL input) | ✅ Complete |
| 5 | Results display (ClipSheet, QuoteList) | ✅ Complete |
| 6 | Documentation | ✅ This document |

### Architecture Overview

```
User Input: 1-10 YouTube URLs
         │
         ▼
┌─────────────────────────────────────────┐
│     POST /jobs/video-analysis           │
│     - Validates URLs                     │
│     - Estimates cost/duration            │
│     - Creates job record                 │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     Celery: run_gemini_video_job        │
│     - GeminiClient.analyze_youtube_videos_batch()
│     - Per-video error handling          │
│     - Chunking for >1hr videos          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     ProducerPacket                      │
│     - Clips with timestamps             │
│     - Quotes with verification          │
│     - Quality gate check                │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     Frontend: ClipSheet + QuoteList     │
│     - Verification badges               │
│     - Copy buttons                      │
│     - Timestamp links to YouTube        │
└─────────────────────────────────────────┘
```

---

## 5. Files Changed

### Backend

| File | Change |
|------|--------|
| `backend/models/job.py` | Added `VideoAnalysisRequest`, `VideoAnalysisResponse`, `VideoAnalysisStatusResponse` |
| `backend/models/job_record.py` | Extended `Artifacts` with `clips`, `quotes`, `producer_packet`, `quality_gate_passed` |
| `backend/app/routes/jobs_routes.py` | Added `POST /jobs/video-analysis` and `GET /jobs/video-analysis/{job_id}` |
| `backend/worker.py` | Enhanced `run_gemini_video_job` with ProducerPacket generation |
| `backend/integrations/gemini_client.py` | Already had `analyze_youtube_video()`, `analyze_youtube_videos_batch()` |
| `backend/pipeline/dual_output.py` | Already had `ProducerPacket`, `ProducerClip`, `ProducerQuote`, `create_producer_packet_from_gemini()` |
| `backend/utils/validators.py` | Already had `validate_video_job_inputs()` |

### Frontend

| File | Change |
|------|--------|
| `frontend/store/jobs.ts` | Added `createVideoAnalysisJob()`, expanded `Job` interface with video artifacts |
| `frontend/pages/dashboard.tsx` | Added mode toggle (Video/Topic), URL textarea, model selector |
| `frontend/components/job-card/ClipSheet.tsx` | **NEW** - Display clips with timestamps |
| `frontend/components/job-card/QuoteList.tsx` | **NEW** - Display quotes with verification |
| `frontend/components/job-card/JobResults.tsx` | Updated to show video analysis results |
| `frontend/components/job-card/job-card-config.ts` | Added `video_analysis` pipeline label |
| `frontend/components/job-card/index.ts` | Exported new components |

---

## 6. Data Structures

### ProducerClip (Backend)

```python
@dataclass
class ProducerClip:
    clip_id: str
    video_url: str
    timestamp_start: str  # MM:SS format
    timestamp_end: str    # MM:SS format
    speaker: str
    quote: str            # Verbatim quote
    quote_type: str       # statement, question, reaction
    range_verified: bool  # Timestamp within video bounds
    quote_verified: bool  # Quote found in transcript
    verification_level: VerificationLevel  # VERIFIED, PROBABLE, UNVERIFIED
```

### ProducerQuote (Backend)

```python
@dataclass
class ProducerQuote:
    quote_id: str
    video_url: str
    text: str           # Verbatim quote
    speaker: str
    timestamp: str      # MM:SS format
    quote_verified: bool
    match_score: float  # 0-1, how well quote matches transcript
```

### Frontend Interfaces

```typescript
interface Clip {
  clip_id: string;
  video_url: string;
  timestamp_start: string;
  timestamp_end: string;
  speaker: string;
  quote: string;
  quote_type: string;
  range_verified: boolean;
  quote_verified: boolean;
  verification_level: 'verified' | 'probable' | 'unverified';
}

interface Quote {
  quote_id: string;
  video_url: string;
  text: string;
  speaker: string;
  timestamp: string;
  quote_verified: boolean;
  match_score: number;
}
```

---

## 7. Quality Gate

### Thresholds

Jobs are marked with quality gate status:

| Metric | Minimum | Meaning |
|--------|---------|---------|
| Clips | ≥ 4 | Enough moments for a video |
| Quotes | ≥ 8 | Enough verbatim content |
| Verified Claims | ≥ 2 | At least some grounded facts |

### What Happens on Failure

- Job completes but shows "Analysis Complete (Low Extraction)"
- User sees what's missing
- Quality gate failures displayed in UI
- User can accept partial results or retry with different videos

### Implementation

```python
def passes_quality_gate(self) -> tuple[bool, List[str]]:
    failures = []
    if len(self.clips) < 4:
        failures.append(f"clips: {len(self.clips)} < 4 required")
    if len(self.quotes) < 8:
        failures.append(f"quotes: {len(self.quotes)} < 8 required")
    if len(self.verified_claims) < 2:
        failures.append(f"verified_claims: {len(self.verified_claims)} < 2 required")
    return len(failures) == 0, failures
```

---

## 8. Frontend Components

### Mode Toggle

```
┌─────────────────────────────────────────┐
│  🎬 Video Analysis  │  📚 Topic Research │
│      [ACTIVE]       │      [legacy]      │
└─────────────────────────────────────────┘
```

- Video Analysis is PRIMARY (purple accent)
- Topic Research is LEGACY (blue accent, marked as "Legacy")

### ClipSheet Component

Displays clips with:
- Timestamp range (clickable, links to YouTube at that time)
- Speaker attribution
- Verbatim quote
- Quote type (statement, question, reaction)
- Verification badge (✓ Verified, ~ Probable, ? Unverified)
- Copy button

Filter options: All, Verified only, Probable only

### QuoteList Component

Displays quotes with:
- Timestamp (clickable)
- Speaker
- Quote text
- Verification indicator
- Match score progress bar (for unverified quotes)
- Copy button on hover

### JobResults Enhancement

For `pipeline === 'video_analysis'`:
- Shows quality gate status (passed/failed)
- Displays clip count vs. threshold
- Displays quote count vs. threshold
- Tab navigation: Clips | Quotes
- Scrollable content area (max 400px)

---

## 9. Cost Model

### Per Video Hour

| Model | Cost/hr | Use Case |
|-------|---------|----------|
| Gemini 2.5 Flash | ~$0.15 | Default extraction |
| Gemini 2.5 Pro | ~$1.15 | Complex/long videos |

### Per Job Estimates

| Scenario | Videos | Hours | Cost |
|----------|--------|-------|------|
| Quick scan | 3 | 2 hrs | ~$0.30 |
| Standard | 5 | 5 hrs | ~$0.75 |
| Deep | 10 | 15 hrs | ~$2.25 |

### Cost Controls

- Show estimated cost before job creation
- Warn if > $5 estimated
- Max 10 videos per job
- Max 5 hours total duration (configurable)

---

## 10. How to Revert

If the Gemini pivot doesn't work out, here's how to revert:

### Remove Video Analysis UI

1. Delete mode toggle in `frontend/pages/dashboard.tsx`
2. Restore topic input as primary
3. Remove ClipSheet and QuoteList components
4. Revert JobResults to Drive-only display

### Remove Video Analysis API

1. Remove `/jobs/video-analysis` endpoint from `jobs_routes.py`
2. Remove `VideoAnalysisRequest/Response` from `backend/models/job.py`
3. Keep `run_gemini_video_job` in worker if needed for other uses

### Key Files to Restore

```bash
git checkout main -- frontend/pages/dashboard.tsx
git checkout main -- frontend/components/job-card/JobResults.tsx
git checkout main -- frontend/store/jobs.ts
git checkout main -- backend/app/routes/jobs_routes.py
```

### Delete New Files

```bash
rm frontend/components/job-card/ClipSheet.tsx
rm frontend/components/job-card/QuoteList.tsx
```

---

## 11. Future Enhancements

### Chrome Extension (Deferred)

**Status:** DEFERRED - Revisit after core product working

**Concept:** "Research Capture" browser extension
- Adds "Capture for Research" button on YouTube video pages
- User collects videos while browsing naturally
- One-click "Send to Research Agent" when ready
- Zero-friction discovery → seamless handoff to extraction

**Why Wait:**
1. Core product must work first
2. Extension adds distribution complexity (Chrome Web Store)
3. Users can paste URLs manually for MVP
4. Extension is enhancement, not requirement

### Export Formats

Already implemented:
- JSON (lossless structured data)
- Markdown (human-readable)

Planned:
- Chapter markers (for podcast editing)
- YouTube chapters format
- Clip suggestions for shorts

### Cross-Video Analysis

Future enhancement to detect:
- Contradictions across videos
- Timeline inconsistencies
- Corroborated claims

---

## Appendix A: Strategic Documents Referenced

| Document | Location |
|----------|----------|
| Strategic Pivot v3 | `plans/strategic-pivot-jan-2026-v3-recalibrated.md` |
| NotebookLM Research | `plans/reports/researcher-260105-1219-notebooklm-capabilities.md` |
| Gemini Video Research | `plans/reports/researcher-260105-1232-gemini-video-capabilities.md` |
| Opus Clip Approach | `plans/reports/researcher-260105-1232-opus-clip-approach.md` |

---

## Appendix B: API Reference

### POST /jobs/video-analysis

**Request:**
```json
{
  "video_urls": ["https://youtube.com/...", "https://youtube.com/..."],
  "title": "Optional project title",
  "model": "gemini-2.5-flash"  // or "gemini-2.5-pro"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "estimated_cost": 0.45,
  "total_duration_minutes": 180,
  "video_count": 3,
  "warnings": ["Video 2 is longer than 1 hour, will be processed in chunks"]
}
```

### GET /jobs/video-analysis/{job_id}

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "progress_percent": 100,
  "current_video": null,
  "total_videos": 3,
  "clips_count": 12,
  "quotes_count": 24,
  "producer_packet": { ... }
}
```

---

## Appendix C: Verification Levels

| Level | Meaning | UI Display |
|-------|---------|------------|
| VERIFIED | Quote found in transcript, timestamp confirmed | ✓ Green |
| PROBABLE | High confidence (>80% match) but not exact | ~ Yellow |
| UNVERIFIED | Extracted but not cross-verified | ? Gray |

---

*Document created: January 5, 2026*
*Last updated: January 5, 2026*
