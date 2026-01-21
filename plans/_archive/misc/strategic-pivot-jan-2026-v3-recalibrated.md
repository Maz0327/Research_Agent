# Plan: Research Agent Strategic Pivot (Jan 2026)

**Date:** 2026-01-05
**Branch:** feature/vision-alignment-v1
**Status:** RECALIBRATED - Sequencing corrected after ChatGPT/Claude review

---

## Critical Recalibration (Jan 5, 2026 - 1:38 PM)

**Problem identified:** We designed the creative output (Producer Packet) before proving extraction works. The current system produces ZERO claims due to a bug we haven't fixed yet.

**The fix:** Correct the sequencing. Grounded output first, opinions later.

| Phase | What | Creative? | Ship? |
|-------|------|-----------|-------|
| 0 | Fix extraction bug | No | No |
| 1 | Test Gemini — timestamps + quotes only | No | No |
| 2 | Ship Clip Sheet + Quote Bank (grounded only) | No | **YES** |
| 3 | Add Quick Take + Structure with citations | Yes, grounded | Yes |
| 4 | Add confidence labels + iteration | Yes, calibrated | Yes |

**New rule:** Creative fields MUST cite grounded fields. No citation = no opinion.

---

## Two-Layer Output Architecture (ChatGPT insight)

**Problem:** Single output mixes facts with opinions. When opinion is wrong, you can't tell if it's because:
- Bad sources
- Bad extraction
- Bad synthesis
- Bad creative leap

**Solution:** Two separate layers with explicit dependency.

### Layer 1: Grounded Research Brief (Non-Negotiable)
- Ships in Phase 2
- **Boring, precise, ruthless**
- Contains: clips, quotes, claims, timeline, contradictions, gaps
- **No opinions. No narrative. No vibes.**
- If this layer is weak, everything downstream is invalid

### Layer 2: Producer Notes (Opinionated, Creative)
- Ships in Phase 3-4
- **MUST reference Layer 1 explicitly**
- Every opinion says "based on CLIP_X, QUOTE_Y"
- Must flag speculation as speculation
- Must include confidence level

**Why this matters:**
- Layer 1 failure = debug extraction
- Layer 2 failure = debug synthesis
- User can trust Layer 1 while questioning Layer 2

---

## Hallucination Prevention (Grounding Rules)

Every field must be verifiable. If unverifiable → flag it, don't trust it.

### Verification Rules by Field (UPDATED per ChatGPT review)

| Field | Verification Type | Levels |
|-------|-------------------|--------|
| `timestamp` | **Two-tier** | `range_verified` (within duration) + `quote_verified` (quote near timestamp) |
| `quote` | **Three-tier** | `exact` (95%+) / `fuzzy` (80-95%) / `fail` (<80%) |
| `claim` | **Two-tier** | `verified_claims` (has quote) + `candidate_claims` (has clip ref only) |
| `speaker` | Binary | verified against metadata OR use `SPEAKER_A/B` |
| `contradiction` | Binary | must cite two valid `clip_id`s OR discard |

### Timestamp Verification (Split)

```python
# Range-verified: cheap, weak
range_verified = timestamp_seconds <= video_duration

# Quote-verified: strong, requires timestamped transcript
quote_verified = quote_found_near_timestamp(quote, timestamp, tolerance=30)

# Final verification
timestamp_verified = range_verified and quote_verified
```

**Rule:** Only show ✅ if BOTH pass. Show ⚠️ if only range-verified.

### Quote Validation (Tiered)

| Match Level | Threshold | Action |
|-------------|-----------|--------|
| ✅ Exact | 95%+ similarity | `quote_confidence: "high"` |
| ⚠️ Fuzzy | 80-95% similarity | `quote_confidence: "medium"` |
| ❌ Fail | <80% similarity | Discard quote |

**Why tiered:** YouTube transcripts have punctuation/casing variations. Binary matching → empty outputs.

### Claims (Split into Two Categories)

**Verified Claims:** Have supporting `verbatim_quote` that passes validation.
```json
{
  "claim_id": "CLAIM_1",
  "canonical_claim": "Subject admitted to X",
  "verbatim_quote": "Yes, I did that",
  "claim_verified": true,
  "based_on": ["CLIP_3"]
}
```

**Candidate Claims:** Tied to clip but no verified quote. Still useful, clearly labeled.
```json
{
  "claim_id": "CLAIM_2",
  "canonical_claim": "Subject implied Y",
  "verbatim_quote": null,
  "claim_verified": false,
  "based_on": ["CLIP_7"],
  "verification_note": "Inference from context, no direct quote"
}
```

**Rule:** Both appear in output. Frontend distinguishes with color coding.

### Clip Selector (Deterministic Post-Step)

After extraction, run quality filter:

```python
def select_final_clips(raw_clips: list, max_clips: int = 12) -> list:
    # 1. Remove duplicates (same quote, similar timestamp)
    deduped = dedupe_by_similarity(raw_clips, threshold=0.85)

    # 2. Prioritize by type (receipts > contradictions > admissions > commentary)
    prioritized = sort_by_priority(deduped, PRIORITY_ORDER)

    # 3. Enforce diversity (max 3 clips per theme)
    diverse = enforce_theme_diversity(prioritized, max_per_theme=3)

    # 4. Cap at max
    return diverse[:max_clips]

PRIORITY_ORDER = [
    "contradiction",      # Highest value
    "primary_admission",  # Subject speaking
    "receipt",            # Document/evidence shown
    "emotional_peak",     # Visible reaction
    "expert_statement",
    "commentary"          # Lowest priority
]
```

**Why needed:** LLMs ignore "max 12" instructions. Deterministic filter enforces it.

### Quality Gate (Non-Negotiable)

Before marking job COMPLETE, verify minimum thresholds:

```python
def validate_job_quality(result: dict) -> JobStatus:
    clips = result.get("clips", [])
    quotes = result.get("quotes", [])
    verified_claims = [c for c in result.get("claims", []) if c.get("claim_verified")]

    if len(clips) < 4:
        return JobStatus.INCOMPLETE, "Too few clips extracted (min 4)"
    if len(quotes) < 8:
        return JobStatus.INCOMPLETE, "Too few quotes extracted (min 8)"
    if len(verified_claims) < 2:
        return JobStatus.INCOMPLETE, "Too few verified claims (min 2)"

    return JobStatus.COMPLETE, None
```

**What happens on INCOMPLETE:**
- Job shows as "Needs Review"
- User sees what's missing
- Option to: retry with different videos, or accept partial output

### Frontend Trust Indicators

| Indicator | Meaning |
|-----------|---------|
| ✅ Green | Fully verified (quote + timestamp) |
| ⚠️ Yellow | Partially verified (range only, or fuzzy match) |
| 🔍 Gray | Candidate/unverified (useful but check manually) |
| ❌ Red | Failed verification — excluded from output |

### What This Prevents

| Hallucination Type | Prevention |
|-------------------|------------|
| Fabricated timestamp | Two-tier verification (range + quote alignment) |
| Invented quote | Three-tier matching with fuzzy fallback |
| Unverifiable claims | Split into verified vs candidate |
| Too many/generic clips | Deterministic clip selector |
| Empty/garbage output | Quality gate blocks COMPLETE status |
| Wrong speaker | Fallback to SPEAKER_A/B |
| Fake contradiction | Require two valid clip_ids |

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

## Implementation Phases (CORRECTED SEQUENCING)

> **Key insight from ChatGPT/Claude review:**
> We were designing creative output before proving extraction works.
> Fixed: Grounded output first, opinions later.

---

### Phase 0: Fix Extraction Bug (1 hour) — CRITICAL
**Why**: Current pipeline produces ZERO claims. Nothing else matters until this works.

**File**: `backend/pipeline/extraction.py`
**Fix**: Add fallback in `_normalize_claim_response()`:
```python
if "canonical_claim" not in normalized and normalized.get("verbatim_quote"):
    normalized["canonical_claim"] = normalized["verbatim_quote"]
```

**Validation**: Run extraction on 1 test transcript → must produce >0 claims.

---

### Phase 1: Test Gemini Grounded Extraction (1 day) — GROUNDED ONLY
**Why**: Prove Gemini can extract timestamps + quotes before adding opinions.

**What to test (NO creative output yet):**
- YouTube URL input works
- Timestamps accurate within ±5 seconds
- Verbatim quotes match actual speech
- Speaker identification works

**Prompt for Phase 1 (minimal, grounded only):**
```
Extract clips and quotes from this video. NO opinions, NO analysis.

Return JSON:
{
  "clips": [{"clip_id": "CLIP_1", "timestamp": "MM:SS", "end": "MM:SS", "speaker": "...", "quote": "..."}],
  "quotes": [{"quote_id": "QUOTE_1", "text": "...", "speaker": "...", "timestamp": "MM:SS"}],
  "claims": [{"claim_id": "CLAIM_1", "statement": "...", "timestamp": "MM:SS", "verifiable": true}]
}
```

**Ship criteria**: 4/5 test videos pass accuracy check.

---

### Phase 1.5: Infrastructure Prep (Before Phase 2 Ships)
**Why:** Gemini tasks are long-running. Current infrastructure will break without these changes.

**Required before Phase 2:**
- [ ] Celery timeout increase (30 min for Gemini tasks)
- [ ] Per-video error handling (partial failures don't kill job)
- [ ] Per-video progress updates (frontend shows "Processing video 2/5")
- [ ] Max duration limit (warn > 5 hrs total, block > 10 hrs)
- [ ] Chunk strategy for >1 hour videos (process in <1hr segments)
- [ ] **Quality gate** (job cannot be COMPLETE unless: clips >= 4, quotes >= 8, verified_claims >= 2)
- [ ] **Clip selector** (deterministic post-step: dedupe, prioritize, enforce max 12)

**Deferred until needed:**
- Full idempotency checkpoints (add if debugging becomes painful)
- Coverage metrics (add after baseline data exists)

**Reference:** See `plans/reports/analysis-260105-1418-infrastructure-gaps-detailed.md` for implementation details.

---

### Phase 2: Ship Grounded Output (2 days) — FIRST SHIPPABLE VERSION
**Why**: Users get value from timestamps + quotes alone. Ship this before opinions.

**Output (Grounded Research Brief):**
- Clip Sheet (timestamps, quotes, speakers)
- Quote Bank (organized by theme)
- Timeline Events (dates mentioned)
- Key Claims (verifiable statements)
- Contradictions (factual conflicts only)
- Gaps (what's missing from sources)

**NO opinions in this phase. No "why it matters", no "suggested use", no "landmines".**

---

### Phase 3: Add Producer Notes with Citations (2 days) — OPINIONS ENTER
**Why**: Now that grounded layer is stable, layer opinions on top WITH citation requirements.

**New fields (all require `based_on` citations):**
```json
{
  "why_it_matters": "1 sentence",
  "based_on": ["CLIP_3", "QUOTE_7"],  // REQUIRED
  "confidence": "high | medium | speculative"
}
```

**Rule**: If LLM cannot cite evidence → field says "speculative" or is omitted.

---

### Phase 4: Add Confidence Calibration (1 day) — TRUST CALIBRATION
**Why**: Let user learn when to trust LLM opinions vs. when to verify.

**Add to every opinion field:**
- `confidence: "high"` = multiple sources agree
- `confidence: "medium"` = single source, seems reliable
- `confidence: "speculative"` = inference, no direct evidence

**Frontend**: Color-code confidence levels (green/yellow/red).

---

### Phase 5: Frontend Updates (2 days)
- Replace topic input with URL list input
- Display two layers: Grounded Brief + Producer Notes
- Collapsible sections for each layer
- Click citation → jumps to source clip

---

## Manual Input Support (Progressive Rollout)

User provides their own sources instead of relying on system discovery.

| Phase | Format | Implementation |
|-------|--------|----------------|
| Phase 2 | YouTube URLs | Textarea, one URL per line (already have transcript extraction) |
| Phase 3 | Plain text paste | Textarea for raw transcript/notes |
| Phase 4 | PDF, .md, .txt upload | File upload component + server-side parsing |
| Future | Google Docs, Notion, etc. | Only if users request |

**Limits to prevent "dump everything" problem:**
- Max 10 sources per job (soft limit, warn user)
- Show estimated processing time before running
- Show cost estimate if applicable

**UI Flow:**
```
Input Mode:
( ) Let system find sources for me [LEGACY - keep for now]
(•) I'll provide my own sources [NEW - primary path]

→ [Paste YouTube URLs]     [one per line, max 10]
→ [Paste text/transcript]  [Phase 3]
→ [Upload files]           [Phase 4: .pdf, .md, .txt]
```

**Why this order:**
1. YouTube URLs = already working, highest value (timestamps)
2. Text paste = trivial to implement, common use case
3. File upload = more complexity, but PDF is high-value for research docs

---

### OLD Phase 1: Producer Packet Prompt (MOVED TO PHASE 3)
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
      "clip_id": "CLIP_1",  // For citation reference
      "timestamp": "MM:SS",
      "end_timestamp": "MM:SS",
      "speaker": "name or SPEAKER_A",
      "quote": "verbatim transcription",
      // GROUNDED ONLY - no opinions in clip_sheet
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
      "gap_id": "GAP_1",
      "missing": "what information is absent",
      "evidence_for_gap": ["CLIP_3", "QUOTE_7"],  // What shows this is missing
      "suggested_search": "query to fill this gap"
    }
  ],

  // ============================================
  // LAYER 2: PRODUCER NOTES (Phase 3-4 only)
  // Every opinion MUST cite grounded evidence
  // ============================================
  "producer_notes": {
    "quick_take": {
      "summary": "2-3 sentence overview",
      "based_on": ["CLIP_1", "CLIP_4", "QUOTE_2"],  // REQUIRED
      "confidence": "high | medium | speculative"
    },
    "clip_assessments": [
      {
        "clip_id": "CLIP_1",  // Reference to grounded clip
        "why_it_matters": "1 sentence",
        "suggested_use": "cold_open | setup | evidence | b_roll",
        "confidence": "high | medium | speculative"
      }
    ],
    "suggested_structure": {
      "beats": ["Beat 1 description", "Beat 2 description"],
      "based_on": ["CLIP_1", "CLIP_5", "CONTRADICTION_1"],  // REQUIRED
      "confidence": "high | medium | speculative"
    },
    "landmines": [
      {
        "risk": "description of risk",
        "evidence": ["CLIP_3", "QUOTE_7"],  // REQUIRED - why this is a landmine
        "severity": "high | medium | low"
      }
    ]
  }
}

EXTRACTION RULES:
1. Timestamps must be MM:SS format (or HH:MM:SS for videos > 1hr)
2. Quotes must be VERBATIM — no paraphrasing
3. clip_sheet: 6-12 clips max
4. quote_bank: 10-20 quotes grouped by theme
5. key_claims: Only verifiable factual claims, not opinions
6. contradictions: Only include if genuinely conflicting (not just nuance)
7. gaps: What a producer would want to know that isn't in the video

SELECTION CRITERIA (how to filter from 200 moments to 12):
PRIORITIZE (include these first):
1. Contradictions between sources or within same speaker
2. Primary source statements (subject speaking, not commentary about subject)
3. Receipts (documents shown, dates stated, names named, numbers cited)
4. Emotional peaks (visible reaction, raised voice, long pause, crying, laughing)
5. First-person admissions ("I did X", "We knew that", "I was wrong")

DISCARD (do not include):
- Generic commentary without new information
- Repetition of points already captured in another clip
- Low-signal small talk, pleasantries, filler
- Second-hand reporting when primary source is available
- Opinions about subject from non-credible sources

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
