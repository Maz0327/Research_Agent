# Plan: Research Agent Strategic Pivot (Jan 2026)

**Date:** 2026-01-05
**Branch:** feature/vision-alignment-v1
**Status:** DECISION MADE - Ready for implementation

---

## Critical User Feedback (100% of users)

| Issue | Description |
|-------|-------------|
| Sources wrong/irrelevant | Collected content doesn't match needs |
| Not enough depth | Too shallow, missing key info |
| Can't find specific info | Buried in walls of text |
| No timestamps/clips | Video creators need specific moments |
| Feels thin/generic | "Info I can find on Google in 2 mins" |

**Root Cause:** Document-first architecture. LLM synthesis = generic summaries. Users need specific, timestamped, clip-ready moments.

---

## Research Completed (Jan 5, 2026)

### 1. NotebookLM Deep Research
**Report:** `plans/reports/researcher-260105-1219-notebooklm-capabilities.md`

| Feature | Status | Impact |
|---------|--------|--------|
| Deep Research (web) | ✅ Works | Web-only, no video analysis |
| YouTube transcripts | ✅ Works | Free extraction |
| Quote citations | ✅ Works | Text-level, not timestamps |
| **Automatic timestamps** | ❌ Missing | Critical gap |
| **Clip boundaries** | ❌ Missing | Critical gap |
| Speaker identification | ❌ Missing | Would be helpful |

**Verdict:** Useful for quote discovery, but doesn't solve the core problem (timestamps/clips).

### 2. Gemini 2.5 Pro Video Analysis
**Report:** `plans/reports/researcher-260105-1232-gemini-video-capabilities.md`

| Feature | Status | Impact |
|---------|--------|--------|
| YouTube URL input | ✅ Direct | No transcription service needed |
| Automatic timestamps | ✅ MM:SS | Solves core problem |
| Semantic queries | ✅ Works | "Find where X talks about Y" |
| Cross-video analysis | ✅ Batch 10 | Contradiction detection |
| Speaker diarization | ✅ Built-in | No extra service |
| Cost | $0.14-1.16/hr | 50-70% cheaper than current |

**Verdict:** This is the tool. Directly solves timestamp + clip extraction.

### 3. Opus Clip / Clip Generators
**Report:** `plans/reports/researcher-260105-1232-opus-clip-approach.md`

| Aspect | Finding |
|--------|---------|
| Technology | Multimodal AI (visual + audio + transcript) |
| Processing | 2 min for 30 min video |
| Accuracy | 95% for viral prediction |
| API | Closed beta, returns clips not metadata |
| **Gap** | Optimized for virality, not research importance |

**Verdict:** Architecture lessons only. Wrong optimization target for documentary.

---

## Recommended Direction: Gemini-Powered Deep Extraction

### The Pivot

| Before | After |
|--------|-------|
| "AI researcher finds sources" | "AI makes your sources scannable" |
| User enters topic | User enters YouTube URLs |
| System finds videos | System analyzes videos deeply |
| Output: documents | Output: timestamped moments + clips |
| Value: breadth | Value: depth |

### New Architecture

```
User provides: 3-10 YouTube URLs

         ┌─────────────────────────────────────────┐
         │         GEMINI 2.5 PRO                  │
         │                                          │
         │  • Accepts YouTube URLs directly        │
         │  • Multimodal analysis (visual + audio) │
         │  • Semantic queries supported           │
         │  • Cross-video contradiction detection  │
         └─────────────────────────────────────────┘
                          │
                          ▼
         ┌─────────────────────────────────────────┐
         │         OUTPUT (per video)              │
         ├─────────────────────────────────────────┤
         │ VIDEO: "Interview with X" (2:34:12)    │
         │                                          │
         │ KEY MOMENTS:                             │
         │ [0:05:23] Background explanation        │
         │   "I started this in 2019..."           │
         │   📎 Clip: 0:05:00 - 0:07:30            │
         │                                          │
         │ [0:45:12] Controversial claim ⚠️        │
         │   "The data shows..."                   │
         │   🔴 CONTRADICTS: Video #3 @ 1:12:00    │
         │   📎 Clip: 0:44:00 - 0:47:00            │
         │                                          │
         │ CROSS-VIDEO ANALYSIS:                   │
         │ • Timeline inconsistency detected       │
         │ • Story changes between V1 & V4         │
         └─────────────────────────────────────────┘
```

### Cost Model (Pinned)

**Per Video Hour:**
| Task | Model | Cost/hr |
|------|-------|---------|
| Initial extraction | Gemini 2.5 Flash | $0.14 |
| Cross-video contradictions | Gemini 2.5 Pro | $1.16 |
| Hybrid target | Flash + Pro for flags | ~$0.35 |

**Per Job Estimates:**
| Scenario | Videos | Hours | Cost |
|----------|--------|-------|------|
| Quick scan | 3 | 2 hrs | $0.70 |
| Standard job | 5 | 5 hrs | $1.75 |
| Deep investigation | 10 | 15 hrs | $5.25 |

**Budget Controls:**
- Warn user if job > $5 estimated
- Hard cap: $10/job (require confirmation)
- Track actual vs estimated in job metadata

**Comparison to Current Stack:**
- Current: ~$3/job + 2-4 hrs manual timestamp work
- New: ~$2/job + 0 manual work
- Net: Cheaper AND faster

### What This Solves

| User Complaint | Solution |
|----------------|----------|
| Sources wrong/irrelevant | User provides sources |
| Not enough depth | Deep extraction per video |
| Can't find specific info | Semantic search within videos |
| No timestamps/clips | Automatic MM:SS timestamps |
| Feels thin/generic | Verbatim quotes with context |

---

## Key Insight

**The bottleneck isn't finding sources — it's extracting usable moments from long sources.**

| Task | Time | AI Value |
|------|------|----------|
| Finding videos on topic | 30 min | Low — Google works |
| Watching 2-hr interview for 5 min of content | 2+ hrs | **HIGH — this is the bottleneck** |
| Taking notes with timestamps | 1 hr | High |
| Figuring out the story | User skill | None — keep this human |

**This is "AI makes long videos scannable" not "AI does your research"**

---

## Decision: Mode-Driven Pipeline Behavior

### Core Principle
**Mode determines pipeline behavior, not just output format.**

Instead of choosing one universal pipeline shape, the research mode configures:
- Whether to follow leads
- Contradiction detection sensitivity
- Gap handling behavior
- Producer Packet template
- Iteration behavior

### Mode-Specific Behavior Matrix

| Mode | Follow Leads | Contradiction Priority | Gap Handling | Iteration Default |
|------|--------------|----------------------|--------------|-------------------|
| **Breaking News** | No — speed matters | Low | Note only | One-shot, fast |
| **Pop Culture** | No — scope bounded | Medium (fan debates) | Note | One-shot, complete |
| **Mystery/Conspiracy** | Yes — rabbit holes are the point | HIGH | Auto-suggest | Suggest iteration |
| **Investigation/Profile** | Selective — credibility leads | CRITICAL | Flag critical | Verify before output |
| **Controversy** | Selective — both sides | CRITICAL | Must fill | Warn if one-sided |

### Mode Configuration

```python
class ModeConfig:
    follow_leads: bool | str  # True, False, or "selective"
    contradiction_sensitivity: str  # "low" | "medium" | "high" | "critical"
    gap_behavior: str  # "note" | "suggest" | "flag-critical" | "auto-chase"
    packet_template: str  # Producer Packet variant
    iteration_default: str  # "one-shot" | "suggest-iteration" | "verify-before-output"

MODE_CONFIGS = {
    "breaking_news": ModeConfig(
        follow_leads=False,
        contradiction_sensitivity="low",
        gap_behavior="note",
        packet_template="breaking_news",
        iteration_default="one-shot"
    ),
    "mystery": ModeConfig(
        follow_leads=True,
        contradiction_sensitivity="high",
        gap_behavior="suggest",
        packet_template="mystery_conspiracy",
        iteration_default="suggest-iteration"
    ),
    "investigation": ModeConfig(
        follow_leads="selective",
        contradiction_sensitivity="critical",
        gap_behavior="flag-critical",
        packet_template="investigation",
        iteration_default="verify-before-output"
    ),
}
```

### Gap Handling Examples

**Breaking News:**
```
GAPS:
- Official statement not yet released
- [Note: Add when available]
```

**Mystery/Conspiracy:**
```
GAPS:
- Subject references "the original document" at 12:34 — not in sources
- [Suggest: Search "Original [doc] leak" — want me to find this?]
```

**Investigation:**
```
GAPS:
⚠️ CRITICAL: Subject claims "I was cleared in court" — no court records
[Flag: Verify before publishing. Search: "[Name] court case [year]"]
```

### Contradiction Detection Examples

**Pop Culture:**
```
CONTRADICTIONS:
- Fan theory origin disputed (Alex Bale vs Reddit) — minor, note for completeness
```

**Investigation:**
```
CONTRADICTIONS:
⚠️ CRITICAL: Subject's timeline doesn't match
- Video 1 [04:23]: "I left the company in March"
- Video 3 [12:45]: "I was there through the summer launch"
- Document: Employment records show May departure
- Assessment: Deliberate inconsistency — highlight in script
```

### This Resolves the Pipeline Shape Question

Instead of picking one answer:
- **Breaking News:** One-shot, no following leads (speed > depth)
- **Pop Culture:** One-shot, bounded scope (contained topic)
- **Mystery:** Suggest iteration, rabbit holes expected (depth > speed)
- **Investigation:** Selective iteration, verification required (accuracy > everything)

---

## Producer Packet Output Format

### Base Structure (All Modes)

```
PRODUCER PACKET: [Topic]

QUICK TAKE (10 lines max)
├── Topic summary
├── What's been covered by others
├── Possible gaps (2-3 bullets)
├── What couldn't be verified
└── "Your call — what angle?"

CLIP SHEET
├── 6-12 clips with MM:SS timestamps
├── Each: timestamp, duration, speaker, quote, why it matters, suggested use

QUOTE BANK
├── Usable quotes grouped by theme/beat
├── Attribution + source link for each

KEY PLAYERS
├── Who's who (2-3 sentences each)
├── Position, credibility, relationships

TIMELINE
├── Key dates, one line each

RECEIPTS
├── Every claim with source + verified status

GAPS & FOLLOW-UPS
├── What couldn't be found
├── Suggested additional sources
└── Unresolved questions
```

### Mode-Specific Templates

**Breaking News Packet:**
```
WHAT WE KNOW (verified)
WHAT'S CLAIMED (unverified)
WHAT'S MISSING (expected soon)
KEY CLIPS (for live coverage)
```

**Mystery/Conspiracy Packet:**
```
QUICK TAKE
THE THEORIES (ranked by evidence)
EVIDENCE FOR EACH
HOLES IN EACH THEORY
RABBIT HOLES TO EXPLORE
CLIP SHEET
```

**Investigation Packet:**
```
QUICK TAKE
KEY PLAYERS (with credibility assessment)
TIMELINE (with source conflicts noted)
CONTRADICTIONS (prioritized by severity)
LANDMINES (legal, factual, ethical)
ONE POSSIBLE STRUCTURE
CLIP SHEET
RECEIPTS
```

**Controversy Packet:**
```
QUICK TAKE
SIDE A PERSPECTIVE (sources, quotes, clips)
SIDE B PERSPECTIVE (sources, quotes, clips)
WHERE THEY AGREE
WHERE THEY CONFLICT
MISSING PERSPECTIVES
LANDMINES
```

---

## Implementation Phases

### Phase 0: Fix Extraction Bug (1 hour) — FALLBACK
**Why**: Current pipeline produces nothing. Need working fallback if Gemini fails.

**File**: `backend/pipeline/extraction.py`
**Fix**: Add fallback in `_normalize_claim_response()`:
```python
if "canonical_claim" not in normalized and normalized.get("verbatim_quote"):
    normalized["canonical_claim"] = normalized["verbatim_quote"]
```

### Phase 1: Producer Packet Prompt (2 hours)
**Why**: Design the prompt BEFORE building integration. Validate output schema.

**File**: `backend/prompts/producer_packet.py` — NEW

```python
PRODUCER_PACKET_SYSTEM = """You are a documentary research assistant. Your job is to extract
clip-ready moments from video content for video producers.

Output ONLY valid JSON matching the schema below. No markdown, no explanation."""

PRODUCER_PACKET_PROMPT = """Analyze this video and extract documentary-ready content.

VIDEO: {video_url}
RESEARCH FOCUS: {topic}
MODE: {mode}  # breaking_news | mystery | investigation | controversy | profile

Return JSON matching this exact schema:

{
  "video_metadata": {
    "title": "string",
    "duration_seconds": number,
    "speakers_identified": ["name1", "name2"] or ["SPEAKER_A", "SPEAKER_B"]
  },

  "clip_sheet": [
    {
      "timestamp": "MM:SS",
      "end_timestamp": "MM:SS",
      "speaker": "name or SPEAKER_A",
      "quote": "verbatim transcription",
      "why_it_matters": "1 sentence explaining documentary value",
      "suggested_use": "cold_open | setup | evidence | b_roll | soundbite | contradiction",
      "importance": "high | medium | low"
    }
  ],

  "quote_bank": [
    {
      "quote": "verbatim text",
      "speaker": "name",
      "timestamp": "MM:SS",
      "theme": "topic category this relates to"
    }
  ],

  "key_claims": [
    {
      "claim": "statement made",
      "speaker": "name",
      "timestamp": "MM:SS",
      "verifiable": true | false,
      "verification_query": "search query to fact-check this"
    }
  ],

  "timeline_events": [
    {
      "date": "YYYY-MM-DD or description",
      "event": "what happened",
      "mentioned_at": "MM:SS",
      "source_type": "stated | implied | external"
    }
  ],

  "contradictions": [
    {
      "claim_a": {"text": "...", "timestamp": "MM:SS"},
      "claim_b": {"text": "...", "timestamp": "MM:SS"},
      "severity": "critical | notable | minor",
      "assessment": "1 sentence analysis"
    }
  ],

  "gaps": [
    {
      "missing": "what information is absent",
      "why_it_matters": "why this gap is significant",
      "suggested_search": "query to fill this gap"
    }
  ]
}

EXTRACTION RULES:
1. Timestamps must be MM:SS format (or HH:MM:SS for videos > 1hr)
2. Quotes must be VERBATIM — no paraphrasing
3. clip_sheet: 6-12 clips, prioritize by documentary value
4. quote_bank: 10-20 quotes grouped by theme
5. key_claims: Only verifiable factual claims, not opinions
6. contradictions: Only include if genuinely conflicting (not just nuance)
7. gaps: What a producer would want to know that isn't in the video

MODE-SPECIFIC BEHAVIOR:
- breaking_news: Prioritize recency, skip deep verification
- mystery: Flag all theories, note evidence quality
- investigation: Flag ALL contradictions, note credibility
- controversy: Ensure both sides represented equally
- profile: Focus on biographical timeline, personality quotes
"""

# Cross-video analysis prompt (for 2+ videos)
CROSS_VIDEO_PROMPT = """Analyze these {n} videos together for cross-references and contradictions.

VIDEOS:
{video_list}

FOCUS: {topic}

Return JSON with:
{
  "cross_contradictions": [
    {
      "video_a": {"title": "...", "timestamp": "MM:SS", "claim": "..."},
      "video_b": {"title": "...", "timestamp": "MM:SS", "claim": "..."},
      "severity": "critical | notable",
      "assessment": "analysis"
    }
  ],
  "timeline_conflicts": [...],
  "corroborated_claims": [...]  # Same claim in multiple videos
}
"""
```

### Phase 2: Test Prompt on Real Videos (1 day)
**Why**: Validate before building. Test on YOUR content types.

**Test Cases:**
| # | Type | Video | Duration |
|---|------|-------|----------|
| 1 | Fan theory | Alex Bale-style analysis | ~30 min |
| 2 | Interview/podcast | Long-form conversation | 2+ hrs |
| 3 | Controversy | Multi-perspective topic | ~45 min |
| 4 | Panel discussion | 3+ speakers | ~1 hr |

**Pass/Fail Criteria (must pass 4/5):**
```
□ YouTube URL input works without upload (test 5 URLs)
□ Timestamps accurate within ±5 seconds (spot-check 10 moments)
□ Speaker attribution correct for 2-speaker content (test 2 videos)
□ Processing time < 3 min for 30-min video
□ Structured JSON output matches schema (no manual parsing)
```

**Failure Recovery:**
- If URL input fails → test with video file upload
- If timestamps off by >10s → add instruction to use transcript timestamps
- If speakers wrong → add "identify speakers by voice" instruction

### Phase 3: Build Gemini Integration (3 days)
**Files to create**:
- `backend/integrations/gemini_video_client.py` — NEW
- `backend/pipeline/stages/gemini_extraction.py` — NEW

**Architecture**:
```
YouTube URL → Gemini 2.5 Pro → Producer Packet JSON → Output Formatter
```

### Phase 4: Build Producer Packet Formatter (2 days)
**Why**: Transform Gemini JSON into final deliverable format.

**Files**:
- `backend/output/producer_packet.py` — NEW
- `backend/output/templates/` — Markdown/HTML templates

### Phase 5: Frontend Updates (2 days)
- Replace topic input with URL list input
- Display Producer Packet with collapsible sections
- GAPS section with "Add more sources" action

---

## Fallback Strategy

If Gemini fails (rate limit, API issue, unsupported video):

```
Gemini fails
    ↓
Fall back to: Supadata transcript → OpenAI extraction → Limited output
    ↓
Producer Packet without timestamps (degraded but usable)
    ↓
GAPS section notes: "Timestamps unavailable — manual verification needed"
```

---

## Research Reports (Full Details)

| Report | Location |
|--------|----------|
| NotebookLM Capabilities | `.claude/plans/reports/researcher-260105-1219-notebooklm-capabilities.md` |
| Gemini Video Analysis | `.claude/plans/reports/researcher-260105-1232-gemini-video-capabilities.md` |
| Opus Clip Approach | `.claude/plans/reports/researcher-260105-1232-opus-clip-approach.md` |
| App Improvement Discussion | `App Improvement Strategy Evaluation.md` |

---

---

## Appendix: Legacy Maintenance (Move to Separate File)

> **TODO:** Move this section to `plans/legacy-pipeline-maintenance.md`
> This is for the OLD pipeline. Primary development is now Gemini-based.
> Keep for reference only — implement only if Gemini integration fails.

### ✅ Already Fixed
| Finding | Commit |
|---------|--------|
| Claim extraction threshold (score >= 3) | bb091a2 |
| verbatim_quote relaxed matching | bb091a2 |
| Chunk overlap 100→150 words | bb091a2 |
| Rate limiter user_id keying | 97eff99 |
| Status codes 400→422 | 97eff99 |
| Celery task_id=job_id | 97eff99 |
| Frontend prompt length 500→2000 | 97eff99 |
| RPC permissions (migration 017) | session |
| JWT startup validation | session |
| Admin graceful degradation (501) | session |
| Claims fallback floor | session |
| Store behavior alignment | session |
| Startup health checks | session |
| Enhanced /health endpoint | session |
| Environment matrix docs | session |
| README testing section | session |

### 🔲 Remaining Items (Deprioritized pending strategic decision)

---

## Phase 1: Security Hardening (HIGH Priority)

### 1.1 RPC Function Permission Fix
**File:** `backend/migrations/014_add_atomic_jsonb_merge.sql`

**Issue:** `atomic_update_job` is SECURITY DEFINER and GRANTed to `authenticated`. Could allow cross-tenant updates if exposed.

**Fix:**
```sql
-- Revoke from authenticated, restrict to service_role only
REVOKE EXECUTE ON FUNCTION atomic_update_job FROM authenticated;
GRANT EXECUTE ON FUNCTION atomic_update_job TO service_role;

-- Add ownership check inside function as defense-in-depth
```

**New Migration:** `backend/migrations/015_restrict_rpc_permissions.sql`

### 1.2 JWT Startup Validation
**Files:** `backend/config.py`, `backend/app/main.py`

**Issue:** JWT misconfiguration silently fails on first request, not at startup.

**Fix:**
- Add `validate_jwt_config()` in config.py
- Call at startup in main.py `@app.on_event("startup")`
- Fail fast with clear error message if SUPABASE_JWT_SECRET missing

---

## Phase 2: Reliability (MEDIUM Priority)

### 2.1 Admin Endpoints Graceful Degradation
**File:** `backend/app/routes/admin_routes.py`

**Issue:** Admin stats/jobs fail when using in-memory store.

**Fix:**
```python
@router.get("/stats")
async def get_admin_stats(...):
    if settings.use_in_memory_store:
        raise HTTPException(501, "Admin stats require Supabase configuration")
    # ... existing logic
```

### 2.2 Claims Extraction Fallback Floor
**File:** `backend/pipeline/stages/extraction_stages.py`

**Issue:** If LLM returns 0 claims, outputs are empty.

**Fix:**
```python
def stage_7_extraction(ctx: PipelineContext) -> None:
    claims, quote_bank_md, claims_ledger_md = extract_claims(...)

    # Fallback: If 0 claims, extract from source titles/snippets
    if not claims and (ctx.transcripts or ctx.web_sources):
        claims, quote_bank_md, claims_ledger_md = _fallback_extraction(ctx)
        ctx.add_warning("Used fallback extraction (0 LLM claims)")
```

### 2.3 Store Behavior Alignment
**Files:** `backend/state/impl/in_memory.py`, `backend/state/impl/supabase_store.py`

**Issue:** Stores handle None values differently for partial merges.

**Fix:**
- Add `_safe_merge()` helper shared by both stores
- Unit tests for edge cases (None outputs, None artifacts, warnings append)

---

## Phase 3: Observability (LOW Priority)

### 3.1 Extraction Logging
**File:** `backend/pipeline/extraction.py`

Add logging for claim candidate counts:
```python
logger.info(f"[{job_id}] Claim candidates: {len(candidates)} before filter, {len(filtered)} after")
```

### 3.2 Startup Health Checks
**File:** `backend/app/main.py`

Check at startup:
- Required env vars set
- Redis connection
- Supabase connection (if configured)
- Playwright binaries (if web capture enabled)

---

## Phase 4: Documentation (LOW Priority)

### 4.1 Environment Matrix
**File:** `docs/environment-matrix.md` (NEW)

Document which features need which keys:
| Feature | Required Keys | Optional Keys |
|---------|--------------|---------------|
| Core API | REDIS_URL, SUPABASE_* | - |
| Extraction | OPENAI_API_KEY | - |
| Research Mapping | PERPLEXITY_API_KEY | EXA_API_KEY |
| Web Capture | - | JINA_API_KEY |
| Transcripts | SUPADATA_API_KEY | OPENAI_API_KEY (Whisper) |

### 4.2 Testing README Section
**File:** `README.md`

Add:
```markdown
## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run backend tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend
```
```

---

## Execution Order

1. **Phase 1.1** - RPC permissions (security, quick win)
2. **Phase 1.2** - JWT startup validation (security)
3. **Phase 2.1** - Admin graceful degradation (reliability)
4. **Phase 2.2** - Claims fallback floor (output quality insurance)
5. **Phase 2.3** - Store alignment (tech debt)
6. **Phase 3.1-3.2** - Observability (nice to have)
7. **Phase 4** - Documentation (last)

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/migrations/015_restrict_rpc_permissions.sql` | NEW - security fix |
| `backend/config.py` | Add JWT validation |
| `backend/app/main.py` | Startup checks |
| `backend/app/routes/admin_routes.py` | 501 for in-memory |
| `backend/pipeline/stages/extraction_stages.py` | Fallback extraction |
| `backend/state/impl/in_memory.py` | Safe merge helper |
| `backend/state/impl/supabase_store.py` | Safe merge helper |
| `backend/pipeline/extraction.py` | Logging |
| `docs/environment-matrix.md` | NEW - env docs |
| `README.md` | Testing section |

---

## Out of Scope (Future)

- Redis-backed rate limiter for multi-worker (Railway is single-worker)
- Targeted retrieval in validation (expensive, should be opt-in mode)
- Test consolidation (tests/ vs backend/tests/ - low impact)

---

## Estimated Effort

| Phase | Time | Risk |
|-------|------|------|
| Phase 1 (Security) | 30 min | Low |
| Phase 2 (Reliability) | 1 hr | Medium |
| Phase 3 (Observability) | 20 min | Low |
| Phase 4 (Docs) | 20 min | Low |
| **Total** | ~2 hrs | - |
