# Frontend/Backend Alignment Audit

**Scout Report** | Generated: 2026-01-19 00:28  
**Scope:** Research Agent v3.0 (Phase 10)  
**Status:** Alignment gaps identified in configuration exposure, hallucination controls, and advanced settings

---

## Executive Summary

The Research Agent backend exposes **extensive configuration options** that are **largely inaccessible to frontend users**. The backend `JobConfig` model includes sophisticated hallucination prevention controls (LLM judge, RAG grounding, semantic entropy) and granular budget/source configuration, yet the frontend only exposes:

- Basic pipeline selection (6 modes)
- Topic and niche selection
- RAG grounding toggle (single control)
- Source addition (video, article, text, screenshot)

**Gap severity:** HIGH. Users cannot access 80% of available backend configuration without direct API calls.

---

## Backend Capabilities vs. Frontend Exposure

### 1. HALLUCINATION PREVENTION CONTROLS

#### Available in Backend (`HallucinationConfig`)

| Control | Type | Default | Exposed in Frontend |
|---------|------|---------|-------------------|
| `enable_llm_judge` | bool | TRUE | ❌ No |
| `llm_judge_model` | str | "gpt-4o" | ❌ No |
| `enable_rag_grounding` | bool | FALSE | ✅ Yes (toggle only) |
| `rag_confidence_threshold` | str | "high" | ❌ No |
| `max_claims_to_rag_verify` | int | 10 | ❌ No |
| `enable_semantic_entropy` | bool | FALSE | ❌ No |
| `entropy_samples` | int | 5 | ❌ No |
| `entropy_threshold` | float | 0.75 | ❌ No |
| `auto_enable_for_investigation` | bool | TRUE | ❌ No |

**Gap Analysis:**
- Frontend exposes only `enable_rag_grounding` as a toggle
- No access to LLM judge configuration (GPT-4o cross-model validation)
- No semantic entropy detection controls (useful for INVESTIGATION mode)
- No RAG threshold or claim count controls for cost/performance tuning
- Users cannot choose validation model or fine-tune entropy detection

---

### 2. SOURCE CONFIGURATION

#### Available in Backend (`SourcesConfig`)

| Control | Type | Default | Exposed in Frontend |
|---------|------|---------|-------------------|
| `web` | bool | TRUE | ❌ No |
| `include_reddit_public` | bool | FALSE | ✅ Via AddSourceModal (subreddits) |
| `include_news` | bool | TRUE | ❌ No |
| `include_academic` | bool | FALSE | ❌ No |
| `include_gov` | bool | FALSE | ❌ No |

**YouTube Specifics (`YouTubeConfig`):**
- `channels` - Frontend allows URLs, not channel IDs
- `include_livestreams` (default: FALSE) - Not exposed
- `exclude_shorts` (default: TRUE) - Not exposed
- `max_videos` (default: 10, range: 1-50) - Not exposed
- `fetch_transcripts` (default: TRUE) - Not exposed

**Reddit Specifics (`RedditConfig`):**
- `subreddits` - Frontend allows custom subreddits in preview UI
- `limit_per_sub` (default: 5, range: 1-20) - Not exposed

**Gap Analysis:**
- No toggle for academic/government sources
- Reddit configuration only accessible during preview, not in main job creation
- YouTube livestream/shorts filtering not exposed
- Transcript fetching not configurable
- Videos per channel limit not adjustable

---

### 3. BUDGET CONTROLS

#### Available in Backend (`BudgetsConfig`)

| Control | Type | Default | Range | Exposed in Frontend |
|---------|------|---------|-------|-------------------|
| `max_web_urls` | int | 30 | 1-200 | ❌ No |
| `max_transcription_minutes` | int | 120 | 1-1000 | ❌ No |
| `max_claims_to_validate` | int | 20 | 1-100 | ❌ No |
| `max_validation_links_per_claim` | int | 5 | 1-20 | ❌ No |

**Backend Preset Budgets by Pipeline:**

```
quick:          {web: 20, transcribe: 60, claims: 10, links: 3}
full:           {web: 50, transcribe: 120, claims: 25, links: 6}
breaking_news:  {web: 15, transcribe: 30, claims: 8, links: 4}
investigation:  {web: 40, transcribe: 100, claims: 20, links: 6}
profile:        {web: 25, transcribe: 60, claims: 12, links: 5}
controversy:    {web: 30, transcribe: 80, claims: 15, links: 5}
```

**Gap Analysis:**
- Budgets are pipeline-specific but not user-adjustable
- No cost control available (important for API cost management)
- No ability to tune transcription vs. web search balance
- Claims validation is "all or nothing" - no granular control

---

### 4. TIME WINDOW & DOCUMENTARY MODES

#### Available in Backend

**Documentary Modes (newer):**
- `BREAKING_NEWS` - Fast, recent events, 72-hour window
- `INVESTIGATION` - Deep dive, verification, no time limit
- `PROFILE` - Single entity focus, biographical timeline
- `CONTROVERSY` - Multiple viewpoints, balanced

**Legacy Modes (deprecated but functional):**
- `CLAIMS_EVIDENCE`, `TIMELINE`, `QUICK_BRIEF`

**Time Window Config (`TimeWindow`):**
- `start` (date) - Not exposed
- `end` (date) - Not exposed

**Gap Analysis:**
- Frontend uses generic "pipeline" naming (quick/full/investigation/profile)
- Documentary modes mapped to pipelines but naming differs
- Time window filtering not accessible to users
- No temporal scope control (useful for recent vs. historical research)

---

### 5. OUTPUT CONFIGURATION

#### Available in Backend (`OutputConfig`)

| Control | Type | Default | Exposed in Frontend |
|---------|------|---------|-------------------|
| `drive_folder_name` | str | "Research Packets" | ❌ No |

**Gap Analysis:**
- Users cannot customize output folder name
- Default folder name is generic, not topic-specific
- No option to select existing Drive folders

---

## Frontend Controls Present

### In UnifiedInputPanel.tsx
- **Topic input** - Free text (500 char max)
- **Source management** - Add/remove videos, articles, text, screenshots
- **RAG grounding toggle** - Enable/disable verification
- **Max sources** - Hard limit of 20 sources

### In Dashboard.tsx (Research Mode)
- **Pipeline selection** - quick/breaking_news/full/investigation/profile/controversy
- **Niche selection** - pop_culture/political/true_crime/mysteries/downfalls/controversy/auto-detect
- **Preview + confirmation** - LLM interprets request before creation
- **Source type preview** - Shows which sources will be used

### In Dashboard.tsx (Quick Video Mode)
- **Video URLs** - Paste multiple (max 10)
- **Project title** - Optional custom title
- **Analysis model** - Flash (faster/cheaper) or Pro (more accurate)

### In Settings
- **Default pipeline** - User preference, applies to new jobs
- **Auto-extract claims** - Toggle claim extraction
- **Max sources per job** - 5-50, saved as preference (not per-job override)
- **Notification preferences** - Email on complete/failure

---

## Critical Alignment Issues

### Issue 1: Hallucination Controls Completely Hidden
**Severity:** HIGH  
**Impact:** Users cannot trade accuracy for cost/speed  
**Affected Configs:**
- LLM judge model selection
- Semantic entropy detection (critical for INVESTIGATION mode)
- RAG grounding thresholds
- Entropy sampling and thresholds

**Example:** Investigation mode auto-enables semantic entropy in backend, but user has no visibility or control.

---

### Issue 2: Source Filtering Not Exposable in Job Creation
**Severity:** MEDIUM  
**Impact:** Users cannot exclude academic/news/government sources  
**Affected Configs:**
- `SourcesConfig.include_academic`, `.include_gov`
- `YouTubeConfig.include_livestreams`, `.exclude_shorts`, `.fetch_transcripts`
- `RedditConfig.limit_per_sub`

**Example:** User wants Reddit-only research (exclude web/news), no UI control exists.

---

### Issue 3: Budget Controls Are Pipeline-Fixed
**Severity:** MEDIUM  
**Impact:** Cannot optimize for cost/speed beyond pipeline selection  
**Affected Configs:**
- `BudgetsConfig` - Fixed per pipeline, not adjustable
- No cost visualization before job creation

**Example:** Investigation mode defaults to 40 web URLs. User cannot lower to 15 for faster results on a fast-moving story.

---

### Issue 4: Time Windows Unused
**Severity:** LOW  
**Impact:** Temporal filtering not available  
**Affected Configs:**
- `TimeWindow.start` and `.end`
- Documentary mode time windows (72h breaking_news, unlimited investigation)

**Example:** Breaking news mode hardcoded to 72 hours, user cannot change.

---

### Issue 5: Settings Store vs. Job Config Mismatch
**Severity:** MEDIUM  
**Impact:** Settings preferences not applied to jobs  
**User Settings:**
- `default_pipeline` (applied on dashboard)
- `auto_extract_claims` (stored but not used)
- `max_sources` (5-50, stored but job max is hardcoded to 20 in mixed-input)

**Backend Job Config:**
- Similar but independent
- No per-user settings transmission to backend

**Example:** User sets `max_sources=50` in settings, but job creation UI caps at 20 and backend receives no user preference context.

---

## API Endpoint Analysis

### `/jobs/mixed-input` (Main endpoint for unified input)

**What Frontend Sends:**
```json
{
  "topic": "string",
  "video_urls": ["url1", "url2"],
  "article_urls": ["url3"],
  "text_inputs": [{"title": "str", "content": "str", "platform_hint": "str"}],
  "screenshots": [{"filename": "str", "base64": "str", "platform_hint": "str"}],
  // RAG grounding toggle:
  "hallucination": {"enable_rag_grounding": true}
}
```

**What Backend Accepts (in JobConfig):**
```python
{
  "topic": str,
  "mode": ResearchMode,
  "niche": Optional[str],
  "time_window": TimeWindow,
  "youtube": YouTubeConfig,
  "reddit": RedditConfig,
  "sources": SourcesConfig,
  "budgets": BudgetsConfig,
  "output": OutputConfig,
  "hallucination": HallucinationConfig  # Only rag_grounding used
}
```

**Gap:** Frontend sends only 6 fields, backend accepts 10+ configuration objects with 50+ total parameters.

---

### `/jobs/video-analysis` (Gemini video extraction)

**Endpoint accepts:**
- `video_urls` (array)
- `model` (gemini-2.5-flash or gemini-2.5-pro)
- `title` (optional)

**Missing from UI:**
- No cost estimation display before job creation
- No configuration for extraction depth/detail
- No way to control output format preferences

---

### `/jobs/{job_id}/booster` (Deep research expansion)

**Not accessible in current UI** - No UI button or control to trigger booster

---

### `/jobs/{job_id}/producer-packet` (Creative output Doc 3)

**Not accessible in current UI** - No UI button or control to trigger producer packet

---

## Unresolved Questions

1. **Should per-job overrides be added to the UI?** (e.g., "Use different budget for THIS job only")
2. **Is the 20-source cap in unified-input intentional?** Backend BudgetsConfig allows higher, but UI blocks at 20.
3. **Why does auto-enable semantic entropy exist?** Should users see a warning when INVESTIGATION mode auto-enables expensive verification?
4. **Are settings supposed to be global defaults or job-specific?** Currently stored per-user but not transmitted to backend.
5. **Should Booster and Producer Packet have UI triggers?** Currently hidden, only accessible via direct API calls.

---

## Recommendations

### Priority 1: Expose Core Hallucination Controls
- Add toggle for LLM judge (GPT-4o validation)
- Add toggle for semantic entropy detection
- Show cost impact of each toggle
- Display which validations are auto-enabled by mode

### Priority 2: Expose Source Filtering
- Checkbox group for academic/government sources
- YouTube livestream/shorts controls in quick video mode
- Reddit posts-per-subreddit slider
- Backend call `/jobs/preview` should return source selection UI state

### Priority 3: Expose Budget Controls (Advanced)
- "Advanced Budget" section (collapsed by default)
- Allow per-job budget override
- Show cost/time estimate impact
- Apply user's settings.max_sources to job creation

### Priority 4: Add UI Controls for Optional Pipelines
- "Generate Producer Packet (Doc 3)" button on completed jobs
- "Run Deep Research Booster" button on completed jobs
- Gating warnings if requirements not met

### Priority 5: Fix Settings Sync
- Transmit user.settings to backend on job creation
- Apply default_pipeline on dashboard
- Actually use auto_extract_claims (currently unused)

---

## Files Requiring Changes

### Backend
- `backend/app/routes/jobs_routes.py` - Add `/jobs/{id}/booster` and `/jobs/{id}/producer-packet` UI support
- `backend/models/job_config.py` - Already complete, no changes needed

### Frontend
- `frontend/components/unified-input/UnifiedInputPanel.tsx` - Add advanced config section
- `frontend/pages/dashboard.tsx` - Add control for Booster/Producer Packet
- `frontend/components/JobCard.tsx` - Add trigger buttons for optional pipelines
- `frontend/components/settings/` - Sync settings to backend
- New component: `frontend/components/AdvancedJobConfig.tsx` - Hallucination/budget controls

---

## Summary Table

| Category | Backend Config | Frontend Control | Gap Severity |
|----------|---|---|---|
| Hallucination Prevention | 9 options | 1 toggle (RAG only) | 🔴 HIGH |
| Source Selection | 8 options | Manual source add | 🟡 MEDIUM |
| Budget Constraints | 4 knobs (pipeline-fixed) | None (fixed) | 🟡 MEDIUM |
| Time Windows | 2 fields | None | 🟢 LOW |
| Output Settings | 1 field | None | 🟢 LOW |
| Optional Pipelines | Booster, Producer Packet | Not in UI | 🔴 HIGH |
| Settings Sync | Settings model | UI only, not sent to API | 🟡 MEDIUM |

