# Pipeline Integration: New Stack Mapping

**Current Pipeline:** 12 stages (0-10, with substages)
**New Components:** Gemini, Exa, Claude, Serper, MinHash, BM25

---

## Pipeline Stage → API Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RESEARCH AGENT PIPELINE                              │
│                     With Human-Replacement Stack                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 0: Initialize                                                        │
│  └── No API (state management only)                                         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 1: Planning                                                          │
│  ├── CURRENT: OpenAI GPT-4o-mini                                            │
│  └── NEW: Gemini 2.5 Flash ─────────────────────────────────────────────┐  │
│          • 1M context window (can hold entire research brief)            │  │
│          • "Thinking mode" for complex reasoning                         │  │
│          • $0.04/job                                                     │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 2: Research Mapping                                                  │
│  ├── CURRENT: Perplexity                                                    │
│  └── KEEP: Perplexity ─────────────────────────────────────────────────┐   │
│          • Fast (358ms)                                                  │   │
│          • Good for identifying angles and key terms                     │   │
│          • $0.02/job                                                     │   │
│                                                                          │   │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 3: Source Shortlist ◀────────────── MAJOR CHANGE ───────────────┐   │
│  ├── CURRENT: Perplexity only                                           │   │
│  └── NEW: Mode-Based Routing ──────────────────────────────────────────┐│   │
│          │                                                              ││   │
│          ├── breaking_news ──▶ Perplexity (speed)                       ││   │
│          ├── investigation ──▶ Exa + Perplexity (94.9% accuracy)        ││   │
│          ├── profile ────────▶ Exa (semantic entity search)             ││   │
│          ├── controversy ────▶ Exa + Perplexity (multi-perspective)     ││   │
│          └── fallback ───────▶ Serper (NOT Tavily - 10% 502 rate)       ││   │
│                                                                         ││   │
│          Cost: $0.20-0.80/job depending on mode                         ││   │
│                                                                         ││   │
├─────────────────────────────────────────────────────────────────────────┘┘  │
│                                                                             │
│  STAGE 3.5: Quality Gate ◀───────────────── NEW STAGE ─────────────────┐   │
│  └── ADD: Deterministic filtering + BM25 scoring                        │   │
│          • Filter junk sources before extraction                         │   │
│          • Score by domain authority + BM25 relevance                    │   │
│          • Module exists: backend/pipeline/quality_gate.py               │   │
│          • Cost: $0 (local processing)                                   │   │
│                                                                          │   │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 4: YouTube Enumeration                                               │
│  └── KEEP: YouTube Data API (FREE)                                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 5: Transcript Extraction                                             │
│  └── KEEP: Supadata → Whisper → youtube-api                                 │
│          • Supadata required for cloud IPs ($17/month fixed)                │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 6: Web Capture                                                       │
│  ├── CURRENT: Jina → Trafilatura → Playwright                               │
│  └── ADD: Vision capture for infographics ──────────────────────────────┐  │
│          • Screenshot pages with charts/infographics                     │  │
│          • Pass to Gemini 2.5 Pro for analysis in Stage 7                │  │
│          • Cost: $0 (Jina is FREE)                                       │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 6.5: Reddit Collection                                               │
│  └── KEEP: PRAW (FREE)                                                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 7: Claim Extraction ◀─────────────── OPTIMIZE ───────────────────┐  │
│  ├── CURRENT: OpenAI GPT-4o-mini (all claims via LLM)                    │  │
│  └── NEW: Hybrid approach ─────────────────────────────────────────────┐│  │
│          │                                                              ││  │
│          ├── Step 1: Regex heuristics (score >= 4) ──▶ Candidates       ││  │
│          ├── Step 2: GPT-4o-mini canonicalization ──▶ Claims            ││  │
│          └── Step 3: MinHash LSH deduplication ──▶ Unique claims        ││  │
│                                                                         ││  │
│          • Reduces LLM calls by ~30%                                    ││  │
│          • O(n) dedup instead of O(n²)                                  ││  │
│          • Cost: $0.02/job                                              ││  │
│                                                                         ││  │
├─────────────────────────────────────────────────────────────────────────┘┘  │
│                                                                             │
│  STAGE 7.5: Timeline Extraction                                             │
│  ├── CURRENT: OpenAI GPT-4o-mini                                            │
│  └── NEW: Gemini 2.5 Pro ───────────────────────────────────────────────┐  │
│          • Better temporal reasoning                                     │  │
│          • Can process full context (1M tokens)                          │  │
│          • Cost: $0.08/job                                               │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 7.6: Entity Extraction                                               │
│  ├── CURRENT: spaCy en_core_web_sm + regex                                  │
│  └── UPGRADE: spaCy en_core_web_trf ────────────────────────────────────┐  │
│          • +6% F1 accuracy                                               │  │
│          • 500MB model (vs 12MB)                                         │  │
│          • Cost: $0 (local)                                              │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 7.7: Vision Analysis ◀────────────── NEW STAGE ──────────────────┐  │
│  └── ADD: Gemini 2.5 Pro for visual content                              │  │
│          • Analyze screenshots from Stage 6                              │  │
│          • Extract data from charts, infographics, PDFs                  │  │
│          • Cost: $0.10/job (only jobs with visual content)               │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 8: Claim Validation                                                  │
│  ├── CURRENT: Perplexity + OpenAI                                           │
│  └── NEW: Perplexity + Gemini 2.5 Pro ──────────────────────────────────┐  │
│          • Perplexity for fact-checking queries                          │  │
│          • Gemini Pro for evidence synthesis                             │  │
│          • Cost: $0.12/job                                               │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 8.5: Angle Discovery                                                 │
│  ├── CURRENT: OpenAI GPT-4o-mini                                            │
│  └── NEW: Gemini 2.5 Pro ───────────────────────────────────────────────┐  │
│          • Better pattern recognition across sources                     │  │
│          • Can hold full research context                                │  │
│          • Cost: $0.08/job                                               │  │
│                                                                          │  │
├──────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STAGE 8.6: Documentary Intelligence ◀───── MAJOR UPGRADE ─────────────┐   │
│  ├── CURRENT: OpenAI GPT-4o-mini                                         │   │
│  └── NEW: Claude Sonnet 4 (complex) / Gemini Pro (standard) ───────────┐│   │
│          │                                                              ││   │
│          ├── Simple jobs (breaking_news, quick) ──▶ Gemini 2.5 Pro     ││   │
│          └── Complex jobs (investigation) ────────▶ Claude Sonnet 4    ││   │
│                                                                         ││   │
│          • Claude: Superior narrative coherence                         ││   │
│          • Claude: Better contradiction identification                  ││   │
│          • Claude: More human-like synthesis                            ││   │
│          • Cost: $0.20-0.60/job                                         ││   │
│                                                                         ││   │
├─────────────────────────────────────────────────────────────────────────┘┘  │
│                                                                             │
│  STAGE 9: Drive Upload                                                      │
│  └── KEEP: Google Drive + Docs APIs (existing)                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 10: Completion                                                       │
│  └── No API (finalization only)                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary: What Changes Where

| Stage | Current API | New API | Change Type |
|-------|-------------|---------|-------------|
| 1. Planning | OpenAI GPT-4o-mini | **Gemini 2.5 Flash** | Replace |
| 2. Research Mapping | Perplexity | Perplexity | Keep |
| 3. Source Shortlist | Perplexity | **Exa + Perplexity + Serper** | Upgrade |
| 3.5. Quality Gate | (doesn't exist) | **BM25 + deterministic** | Add |
| 4. YouTube | YouTube API | YouTube API | Keep |
| 5. Transcripts | Supadata | Supadata | Keep |
| 6. Web Capture | Jina | Jina + **screenshot capture** | Upgrade |
| 6.5. Reddit | PRAW | PRAW | Keep |
| 7. Claim Extract | GPT-4o-mini | GPT-4o-mini + **MinHash** | Optimize |
| 7.5. Timeline | GPT-4o-mini | **Gemini 2.5 Pro** | Replace |
| 7.6. Entity | spaCy sm | **spaCy trf** | Upgrade |
| 7.7. Vision | (doesn't exist) | **Gemini 2.5 Pro** | Add |
| 8. Validation | Perplexity + OpenAI | Perplexity + **Gemini Pro** | Replace |
| 8.5. Angles | GPT-4o-mini | **Gemini 2.5 Pro** | Replace |
| 8.6. Documentary | GPT-4o-mini | **Claude Sonnet / Gemini Pro** | Replace |
| 9. Drive Upload | Google APIs | Google APIs | Keep |

---

## New Files to Create

| File | Purpose |
|------|---------|
| `backend/integrations/gemini_client.py` | Gemini 2.5 Flash + Pro |
| `backend/integrations/exa_client.py` | Exa semantic search |
| `backend/integrations/serper_client.py` | Serper fallback search |
| `backend/integrations/claude_client.py` | Claude Sonnet synthesis |
| `backend/pipeline/vision_analysis.py` | Stage 7.7 implementation |
| `backend/pipeline/search_router.py` | Mode-based search routing |

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/pipeline/stages.py` | Add stage_3_5_quality_gate, stage_7_7_vision, update LLM calls |
| `backend/pipeline/extraction.py` | Add MinHash dedup, raise threshold |
| `backend/pipeline/quality_gate.py` | Add BM25 scoring |
| `backend/pipeline/entities.py` | Upgrade to en_core_web_trf |
| `backend/worker.py` | Add new stages to execution order |
| `backend/config.py` | Add GOOGLE_API_KEY, EXA_API_KEY, etc. |

---

## Execution Flow Diagram

```
User submits topic
        │
        ▼
┌───────────────────┐
│ Stage 0: Init     │
└───────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 1: Planning │────▶│ Gemini 2.5 Flash│ NEW
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 2: Research │────▶│ Perplexity      │ KEEP
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 3: Sources  │────▶│ Exa + Perplexity│ NEW (mode-based)
└───────────────────┘     │ + Serper backup │
        │                 └─────────────────┘
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 3.5: QGate  │────▶│ BM25 + Rules    │ NEW STAGE
└───────────────────┘     └─────────────────┘
        │
        ├────────────────────────────────────┐
        ▼                                    ▼
┌───────────────────┐                ┌───────────────────┐
│ Stage 4: YouTube  │                │ Stage 6: Web      │
└───────────────────┘                │ + Screenshots     │
        │                            └───────────────────┘
        ▼                                    │
┌───────────────────┐                        │
│ Stage 5: Transcr. │◀───────────────────────┘
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Stage 6.5: Reddit │
└───────────────────┘
        │
        ├────────────────────────────────────┐
        ▼                                    ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 7: Claims   │────▶│ GPT-4o-mini +   │
│ + MinHash dedup   │     │ MinHash LSH     │ OPTIMIZED
└───────────────────┘     └─────────────────┘
        │
        ├────────────────────────────────────┐
        ▼                                    ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 7.5: Time   │────▶│ Gemini 2.5 Pro  │ NEW
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 7.6: Entity │────▶│ spaCy trf       │ UPGRADED
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 7.7: Vision │────▶│ Gemini 2.5 Pro  │ NEW STAGE
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 8: Validate │────▶│ Perplexity +    │
│                   │     │ Gemini Pro      │ NEW
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────┐
│ Stage 8.5: Angles │────▶│ Gemini 2.5 Pro  │ NEW
└───────────────────┘     └─────────────────┘
        │
        ▼
┌───────────────────┐     ┌─────────────────────────┐
│ Stage 8.6: Doc    │────▶│ Claude Sonnet (complex) │ NEW
│ Intelligence      │     │ Gemini Pro (standard)   │
└───────────────────┘     └─────────────────────────┘
        │
        ▼
┌───────────────────┐
│ Stage 9: Upload   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Stage 10: Done    │
└───────────────────┘
        │
        ▼
   NotebookLM Packet
   + Documentary Blueprint
```

---

## Cost Per Stage (Investigation Mode)

| Stage | API | Tokens/Calls | Cost |
|-------|-----|--------------|------|
| 1. Planning | Gemini Flash | 8K in, 15K out | $0.04 |
| 2. Research | Perplexity | 5 queries | $0.03 |
| 3. Sources | Exa + Perplexity | 40 + 15 | $0.25 |
| 3.5. QGate | Local | - | $0.00 |
| 5. Transcripts | Supadata | ~10 videos | $0.28 |
| 6. Web | Jina | ~20 pages | $0.00 |
| 7. Claims | GPT-4o-mini | 80K in, 30K | $0.03 |
| 7.5. Timeline | Gemini Pro | 30K in, 8K | $0.12 |
| 7.6. Entity | spaCy | Local | $0.00 |
| 7.7. Vision | Gemini Pro | 50K in, 5K | $0.10 |
| 8. Validate | Perplexity + Pro | 10 + 20K | $0.15 |
| 8.5. Angles | Gemini Pro | 40K in, 10K | $0.15 |
| 8.6. Doc Intel | Claude Sonnet | 50K in, 15K | $0.60 |
| **TOTAL** | | | **~$1.75** |

*Plus Supadata monthly: $17/60 = $0.28/job*
*Plus buffer for retries: ~$0.20/job*

**Total per investigation job: ~$2.20** ✅ Within $2.17 target
