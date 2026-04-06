# Research Agent: Deep Exploration Report

## Executive Summary

The Research Agent is a sophisticated multi-source research pipeline that ingests videos, articles, screenshots, and text, extracts semantic structure with AI, synthesizes findings, and generates multiple output documents (briefs, scripts, articles, social content). The system uses a **3-LLM provider strategy**: Gemini (primary extraction/planning), OpenAI (Whisper for transcription), and Anthropic Claude (reserved for future complex synthesis).

**Key Integration: Supadata is the PRIMARY YouTube transcript fetcher**, with a 4-tier fallback chain (Supadata → Whisper → YouTube Captions → None).

---

## 1. SUPADATA INTEGRATION — YouTube Transcript Fetching

### Location: `/backend/integrations/supadata_client.py`

**Role:** PRIMARY transcript acquisition method (per PRD v4.3)

**API Details:**
- **Endpoint:** `https://api.supadata.ai/v1/transcript`
- **Authentication:** `x-api-key` header (from `SUPADATA_API_KEY` env var)
- **Modes:**
  - `native` (1 credit) — existing platform transcripts only (cheaper)
  - `generate` (1-2 credits) — AI transcription if native unavailable (more expensive)
  - `auto` — tries native first, falls back to generate
- **Pricing (Dec 2024 validated):**
  - Native transcript: 1 credit
  - AI-generated: 1-2 credits + compute time (up to 60s per video)
  - Web scrape: 1 credit
  - Free tier: 100 requests
- **Other Capabilities:**
  - `scrape_url()` — web content extraction (1 credit/request)
  - `fetch_metadata()` — unified metadata schema across platforms (title, author, stats, duration, thumbnails)

**Supported Platforms:** YouTube, TikTok, Instagram, X (Twitter), Facebook

**Implementation Highlights:**
- **HTTP-only** (SDK removed Dec 2025 due to cloud environment issues)
- Rate limiting: wrapped with `@with_rate_limit("supadata")`
- Timeout: 60 seconds for long transcriptions
- Error handling: raises `SupadataError` with sanitized error messages
- Response parsing: handles both list-of-segments and string formats
- Metadata is additive/non-blocking — failures don't block pipeline

---

## 2. 4-TIER TRANSCRIPT ACQUISITION FALLBACK CHAIN

### Location: `/backend/pipeline/transcript_acquisition.py`

**LOCKED ORDER (per RASS.md Section 8.1):**

```
Tier 1: Supadata (native → generate) ───────────────┐
        SUCCESS → transcript_grounded (HIGH)         │
        FAIL ↓                                        │
                                                      ↓
Tier 2: Whisper (OpenAI speech-to-text) ────────────┤
        SUCCESS → transcript_grounded (HIGH)         │
        FAIL ↓                                        │
                                                      ↓
Tier 3: YouTube Captions (youtube-transcript-api) ──┤
        SUCCESS → caption_grounded (MEDIUM)          │
        ⚠️  NOTE: FAILS ON CLOUD IPs (Railway, AWS)  │
        FAIL ↓                                        │
                                                      ↓
Tier 4: None ─────────────────────────────────────→ video_only (LOW)
```

**Analysis Mode Derivation:**
- `TRANSCRIPT_GROUNDED` (HIGH confidence ceiling) — Tiers 1-2 success
- `CAPTION_GROUNDED` (MEDIUM confidence ceiling) — Tier 3 success
- `VIDEO_ONLY` (LOW confidence ceiling) — All tiers fail

**Key Functions:**
- `acquire_transcript(video_url)` — main entry point, returns `TranscriptResult`
- `TranscriptResult` contains:
  - `transcript_source` — which tier succeeded
  - `analysis_mode` — derived from source
  - `text` — full transcript/captions
  - `cost_credits` — 0-2 credits depending on tier
  - `status` — success/failed with error messages

---

## 3. GEMINI'S ROLE IN THE PIPELINE

### Location: `/backend/integrations/gemini_client.py`

**Primary Responsibility:** Semantic extraction, vision analysis, synthesis planning

**Models Used:**
- **Gemini 2.5 Flash** ($0.30/$2.50 per M tokens) — fast, planning, query generation
- **Gemini 2.5 Pro** ($1.25/$10 per M tokens) — vision, validation, synthesis

**Core Capabilities:**

1. **Semantic Extraction (`extract_semantic_units()`)**
   - Processes transcripts/articles to extract: key_points, claims, themes, tensions, quotes
   - Uses JSON schema validation
   - Temperature: 0.1 (deterministic)
   - Per-source isolation (Rule 1: each source in separate LLM call)

2. **Video Analysis (`analyze_youtube_video()`, `analyze_youtube_video_chunked()`)**
   - For `video_only` mode when no transcript available
   - Extracts ApproximateObservations (NO quotes allowed)
   - Uses chunked analysis for videos >2 hours
   - Model: `gemini-2.5-flash`
   - Temperature: varies by task

3. **Vision/PDF Processing (`process_pdf_file()`, etc.)**
   - Screenshot/PDF content extraction
   - OCR coordinate resolution
   - Multi-page document analysis

4. **Quote Verification (`verify_extraction_results()`)**
   - Cross-reference quotes against source text
   - Return confidence scores for each quote
   - Integrated into validation stage

**Configuration:**
- **API Key:** `GOOGLE_API_KEY` env var
- **Rate Limiting:** Enforced via `@with_rate_limit("gemini")`
- **Response Parsing:** Multiple fallback strategies (```json blocks, raw JSON, truncated JSON repair)
- **Error Handling:** `GeminiParseError`, `GeminiTimeoutError`, `GeminiTruncationError`

---

## 4. DOCUMENT GENERATION PIPELINE — "Doc 0" & Friends

### Architecture: 3-Document Model (Core) + 4 Optional Documents

**Canonical Documents (always produced):**

1. **Doc 0: Source Ledger** — Canonical data layer
   - `build_source_ledger()` in `/backend/pipeline/stages/document_assembly.py`
   - Contains: source metadata, extraction status, skim summary, claim/theme IDs, full text
   - Includes TranscriptProvenance for video sources (transcript source, analysis mode, confidence ceiling)
   - Per-source failure reason if extraction failed
   - **Purpose:** Single source of truth for all source data

2. **Doc 1: Jump-Start Directions** — Research direction layer
   - `build_jump_start()` in `/backend/pipeline/stages/document_assembly.py`
   - Built from: gaps, key_points aggregated by theme
   - Contains: research threads (grouped key points), research directions (from gaps), cross-cutting analysis
   - **Purpose:** Outline for next research phase

3. **Doc 2: Semantic Research Brief** — 80% of primary output
   - Produced in `stage_document_assembly()`
   - Contains: semantic core, themes, tensions, key_points, gaps, speculative observations
   - Sources all data from Doc 0
   - **Purpose:** Research synthesis ready for further analysis

**Optional Documents (user-triggered or phase-specific):**

4. **Doc 3: Creator Brief** — Hero output document
   - Generated by `run_creator_brief_stage()`
   - Temperature: 0.3 (creative but grounded)
   - Reads: Doc 0 (sources), Doc 2 (themes/tensions)
   - Outputs: CreatorBriefDocument with hooks, structure, narrative arc, key messages
   - **Failure mode:** NON-FATAL — adds warning but doesn't fail job
   - **Provenance validation:** All claim_ids and source_ids must trace to Doc 0/2

5. **Doc 4: Producer Packet**
   - Generated by `run_producer_pipeline()`
   - Gating: requires 4+ sources AND 1+ HIGH confidence source
   - Outputs: production-ready research breakdown

6. **Doc 5: Script**
   - Generated by `run_script_stage()`
   - Temperature: 0.5 (spoken word flexibility); 0.55 with voice mimicry
   - Reads: Doc 0, Doc 2, Doc 3 (optional)
   - Outputs: ScriptDocument with video script structure

7. **Doc 6: Blog Post**
   - Generated by `run_blog_post_stage()`
   - Temperature: 0.4 (creative writing, fact-grounded)
   - Reads: Doc 0, Doc 2, Doc 3 (optional)
   - Outputs: BlogPostDocument as HTML + markdown

8. **Doc 7: Social Kit**
   - Generated by `run_social_kit_stage()`
   - Outputs: TikTok/Instagram/Twitter-formatted content variations

### Document Assembly Flow (`stage_document_assembly()`)

**Order (LOCKED per RASS Section 4.5):**
1. **Build Doc 0 (Source Ledger)** from ingested sources + extractions
2. **Build Doc 1 (Jump-Start)** from Doc 0 + gaps
3. **Build Doc 2 (Semantic Brief)** from Doc 0 + extractions + synthesis
4. **No Doc 1/2 may introduce new data** — all references must trace to Doc 0
5. **If Doc 0 is thin → Doc 1/2 reflect this explicitly**

**Key Constraint:** Provenance chain integrity (Rule 14a)
```
Doc 4 (Producer) → references → Doc 3 (Creator Brief)
Doc 3 (Creator) → references → Doc 2 (Semantic Brief) claim_ids
Doc 3 (Creator) → references → Doc 0 (Source Ledger) source_ids
Doc 2 (Brief)   → references → Doc 0 (Source Ledger) source_ids
Doc 1 (Starter) → references → Doc 0 (Source Ledger) source_ids
```

---

## 5. MAIN PIPELINE FLOW & OUTPUT GENERATION

### Location: `/backend/worker.py` (orchestration) + `/backend/pipeline/stages/` (implementations)

**Entry Point:** `run_research_job(job_id, topic)` (Celery task)

**Pipeline Stages (NEW SEMANTIC-ONLY, Dec 2025):**

```
Stage 0: Initialization
  └─ Resolve input type (videos, articles, text, screenshots)

Stage 1: Source Identity
  └─ build_source_identity_from_video() → SourceIdentityPackage
  └─ build_source_identity_from_article() → SourceIdentityPackage
  └─ build_source_identity_from_text() → SourceIdentityPackage
  └─ build_source_identity_from_screenshot() → SourceIdentityPackage
  └─ fetch_video_metadata() — additive Supadata metadata

Stage 2: Semantic Extraction
  └─ Parallel per-source processing (ThreadPoolExecutor, 5 max workers)
  └─ Gemini extracts: key_points, claims, themes, tensions, quotes/observations
  └─ For video_only mode: extract_video_observations() (Gemini video analysis)
  └─ Returns: SemanticExtractionResult[] with cost tracking

Stage 3: Semantic Validation
  └─ Confidence ceiling enforcement (per analysis_mode)
  └─ Quote verification (verify_quote → fuzzy match against source)
  └─ Re-retry mechanism if validation fails

Stage 4: Gap Analysis
  └─ Identify missing coverage from extracted themes/key_points
  └─ Return: Gap[] with reasoning and related themes

Stage 5: Semantic Synthesis
  └─ Gemini synthesizes cross-source patterns
  └─ Creates: synthesized_themes, tensions, speculative_observations
  └─ Builds: semantic_core (2-4 sentence essence)

Stage 6: Document Assembly (LOCKED ORDER)
  └─ build_source_ledger() → Doc 0
  └─ build_jump_start() → Doc 1
  └─ build_semantic_brief() → Doc 2
  └─ No new data introduced in Docs 1/2

Stage 7: Creator Brief (Optional, NON-FATAL)
  └─ run_creator_brief_stage() → Doc 3
  └─ Gemini with temperature 0.3
  └─ Failure adds warning but doesn't fail job

Stage 10: Completion
  └─ Artifact manifest, Supabase storage, cost aggregation
```

**Trigger-Based Output Generation:**
- **Doc 4** → `run_producer_task()` (requires gating: 4+ sources, 1+ HIGH)
- **Doc 5** → `run_script_task()` (with optional voice_profile_id)
- **Doc 6** → `run_blog_post_task()`
- **Doc 7** → `run_social_kit_task()`

**Cost Tracking:**
- Each stage logs cost via `ctx.add_cost(provider, amount)`
- Aggregated at completion
- Tracked by provider: gemini, openai, kimi, anthropic, etc.

---

## 6. LLM PROVIDER CONFIGURATION

### Configured Providers (from `requirements.txt` & `config.py`)

| Provider | Library | Role | Status |
|----------|---------|------|--------|
| **Google Gemini** | `google-genai==1.56.0` | PRIMARY: Extraction, synthesis, planning, vision | 🟢 ACTIVE |
| **OpenAI** | `openai>=1.10.0` | Whisper (Tier 2 transcripts), title generation | 🟢 ACTIVE |
| **Anthropic Claude** | `anthropic>=0.39.0` | RESERVED: Complex synthesis (configured but not used in current flow) | 🟡 CONFIGURED |
| **Kimi/Moonshot** | `kimi_vision_client.py` | LLM Judge (frame analysis, validation) | 🟡 ACTIVE (optional) |

### Environment Variables

```bash
# Gemini
GOOGLE_API_KEY = "AIza..."

# OpenAI (Whisper + GPT-4o-mini for title generation)
OPENAI_API_KEY = "sk-..."

# Anthropic Claude (reserved for synthesis)
ANTHROPIC_API_KEY = "sk-ant-..."

# Kimi/Moonshot (vision validation)
KIMI_API_KEY = "..."

# Supadata (transcript fetching)
SUPADATA_API_KEY = "..."

# Search APIs
EXA_API_KEY = "..."
SERPER_API_KEY = "..."
TAVILY_API_KEY = "..."
```

### Temperature Configuration (Rule 16)

```python
# From backend/utils/llm_temperature.py
TEMP_FACTUAL = 0.1        # Extraction (deterministic)
TEMP_SYNTHESIS = 0.2      # Synthesis (slight flexibility)
TEMP_CREATOR = 0.3        # Creator Brief (creative but grounded)
TEMP_DEEP_DIVE = 0.4      # Booster/gap directions (variety wanted)
TEMP_PRODUCER = 0.3-0.5   # Producer packet
TEMP_BLOG = 0.4           # Blog post (creative writing)
TEMP_SCRIPT = 0.5         # Video script (spoken word flexibility)
TEMP_SCRIPT_VOICE = 0.55  # Script with voice mimicry
```

---

## 7. FALLBACK MECHANISMS FOR TRANSCRIPT FETCHING

### Implemented Fallbacks

**Primary Chain (Tier-based):**
1. Supadata (native mode) → if empty, retry with generate mode
2. Whisper (OpenAI speech-to-text) → if Supadata fails
3. YouTube captions (youtube-transcript-api) → if Whisper fails (local only!)
4. None → fallback to video_only mode

**Known Limitation:**
- **Tier 3 (YouTube captions) FAILS ON CLOUD IPs** (Railway, AWS, GCP)
- GitHub issue: https://github.com/jdepoix/youtube-transcript-api/issues/303
- On cloud deployments, Tier 3 returns None automatically, falls through to Tier 4
- This is documented and expected behavior per RASS.md

**Configuration:**
- `enable_quality_gate` (default: true) — filters sources between discovery and extraction
- `semantic_extraction_max_workers` (default: 9) — parallel extraction concurrency

### Error Handling Pattern

```python
# From transcript_acquisition.py
try:
    result = _try_supadata(video_url)  # Tier 1
    if result.text:
        return TranscriptResult(..., analysis_mode=TRANSCRIPT_GROUNDED, ...)
except Exception as e:
    logger.warning(f"Tier 1 failed: {e}")

try:
    result = _try_whisper(video_id)  # Tier 2
    if result.text:
        return TranscriptResult(..., analysis_mode=TRANSCRIPT_GROUNDED, ...)
except Exception as e:
    logger.warning(f"Tier 2 failed: {e}")

# ... and so on
return TranscriptResult(..., analysis_mode=VIDEO_ONLY, status=FAILED)
```

---

## 8. DATA FLOW DIAGRAM

```
USER INPUT
├─ Videos (YouTube, TikTok, etc.)
├─ Articles (URLs)
├─ Text (raw markdown/text)
└─ Screenshots (image files)
         │
         ↓
STAGE 1: SOURCE IDENTITY
├─ Transcript Acquisition (Supadata → Whisper → Captions → None)
├─ Content Extraction (Jina Reader, Trafilatura, OCR)
├─ Metadata Enrichment (Supadata unified schema)
└─ SourceIdentityPackage[] (analysis_mode, transcript_source, etc.)
         │
         ↓
STAGE 2: SEMANTIC EXTRACTION (Parallel)
├─ Gemini per-source processing
├─ Extract: key_points, claims, themes, tensions, quotes/observations
├─ Apply confidence ceiling (HIGH/MEDIUM/LOW based on analysis_mode)
└─ SemanticExtractionResult[] with cost tracking
         │
         ↓
STAGE 3-4: VALIDATION & GAPS
├─ Confidence ceiling enforcement
├─ Quote verification (fuzzy match)
├─ Gap analysis (identify missing coverage)
└─ Validated extractions + Gap[]
         │
         ↓
STAGE 5: SEMANTIC SYNTHESIS
├─ Gemini cross-source synthesis
├─ Create synthesized themes/tensions
├─ Build semantic_core (essence)
└─ Speculative observations
         │
         ↓
STAGE 6: DOCUMENT ASSEMBLY (LOCKED ORDER)
├─ Doc 0: Source Ledger (canonical data layer)
├─ Doc 1: Jump-Start Directions (research roadmap)
├─ Doc 2: Semantic Research Brief (80% output)
└─ All documents trace provenance to Doc 0
         │
         ↓
OPTIONAL STAGE 7: CREATOR BRIEF
├─ Gemini (temperature 0.3) synthesizes hook/narrative
└─ Doc 3 (NON-FATAL failure)
         │
         ↓
TRIGGER-BASED OUTPUTS (User requests)
├─ Doc 4: Producer Packet (requires 4+ sources, 1+ HIGH)
├─ Doc 5: Video Script (with optional voice mimicry)
├─ Doc 6: Blog Post (HTML + Markdown)
└─ Doc 7: Social Kit (TikTok/Instagram/Twitter variations)
         │
         ↓
COMPLETION
├─ Artifact manifest stored
├─ Cost aggregation (Gemini, OpenAI, Kimi, Anthropic)
└─ Supabase storage + user notification
```

---

## 9. KEY FILES REFERENCE

| File | Purpose |
|------|---------|
| `/backend/integrations/supadata_client.py` | Supadata API wrapper (PRIMARY transcript source) |
| `/backend/pipeline/transcript_acquisition.py` | 4-tier fallback chain orchestration |
| `/backend/integrations/gemini_client.py` | Gemini API wrapper (extraction, synthesis, vision) |
| `/backend/integrations/openai_client.py` | OpenAI API wrapper (Whisper, title generation) |
| `/backend/config.py` | Environment variable configuration + validation |
| `/backend/worker.py` | Celery task definitions + main pipeline entry point |
| `/backend/pipeline/stages/semantic_extraction.py` | Per-source semantic extraction (Gemini) |
| `/backend/pipeline/stages/semantic_synthesis.py` | Cross-source synthesis (Gemini) |
| `/backend/pipeline/stages/document_assembly.py` | Doc 0/1/2 assembly (locked order) |
| `/backend/pipeline/stages/creator_brief_stage.py` | Doc 3 generation (non-fatal) |
| `/backend/pipeline/stages/script_stage.py` | Doc 5 (Script) generation |
| `/backend/pipeline/stages/blog_post_stage.py` | Doc 6 (Blog Post) generation |
| `/backend/models/document_outputs.py` | Document model definitions (SourceLedger, JumpStart, SemanticBrief) |
| `/backend/models/semantic_units.py` | KeyPoint, Claim, Theme, Tension, Quote, etc. |

---

## 10. UNRESOLVED QUESTIONS

1. **Claude Usage:** Why is Anthropic Claude configured but not currently used in the pipeline?
   - Is it reserved for future synthesis iterations?
   - Should it replace Gemini for synthesis given cost/capability trade-offs?

2. **Supadata API Stability:** The HTTP-only implementation (Dec 2025) removed SDK. Are there metrics on:
   - Success rate improvements?
   - Cloud deployment (Railway, AWS) compatibility issues?

3. **Video Analysis Chunking:** Videos >2 hours use 1-hour chunks. Is this threshold optimal?
   - Gemini's 1M token limit — how does it map to video duration?

4. **Creator Brief Non-Fatal Failure:** Why is Doc 3 failure non-fatal while Docs 0/1/2 are fatal?
   - Is this intentional for graceful degradation?
   - Should failure analysis be more granular?

5. **Confidence Ceiling Enforcement:** Validation catches overconfident extractions, but does it:
   - Log statistical data on how often ceilings are exceeded?
   - Provide feedback to Gemini to improve calibration?

6. **Cost Optimization:** Is there opportunity to:
   - Use GPT-4o-mini for extraction instead of Gemini Flash to reduce costs?
   - Cache common prompts/schemas to reduce token usage?

---

**Report Generated:** 2026-04-05
**Exploration Scope:** Full backend pipeline architecture
**Data Sources:** Code analysis, config inspection, integration review
