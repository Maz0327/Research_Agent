# RESEARCH AGENT — PROJECT AUDIT REPORT

**Generated:** 2026-01-13 13:47
**Audited by:** Claude Code (Opus 4.5)
**Branch:** feature/vision-alignment-v1

---

## 1. PROJECT STRUCTURE

### Directory Tree

```
Research_Agent/
├── backend/                         # FastAPI + Celery backend
│   ├── app/                         # API layer
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── rate_limiter.py         # slowapi rate limiting
│   │   └── routes/                  # API route modules
│   │       ├── jobs_routes.py      # Job CRUD + video analysis
│   │       ├── export_routes.py    # Export endpoints
│   │       ├── transcripts_routes.py
│   │       ├── settings_routes.py
│   │       ├── admin_routes.py
│   │       └── slack_routes.py
│   ├── auth/                        # Authentication
│   │   ├── dependencies.py         # JWT verification
│   │   ├── ban_check.py            # User ban checking
│   │   └── admin.py                # Admin role checking
│   ├── config.py                   # Settings via pydantic-settings
│   ├── integrations/               # External API clients (23 files)
│   │   ├── gemini_client.py        # 60KB - Primary LLM client
│   │   ├── openai_client.py        # Planning/extraction
│   │   ├── perplexity_client.py    # Search
│   │   ├── exa_client.py           # Semantic search
│   │   ├── supadata_client.py      # Transcripts
│   │   ├── youtube_client.py       # YouTube Data API
│   │   ├── google_drive_docs.py    # Drive/Docs upload
│   │   └── ... (16 more clients)
│   ├── legacy/                      # DEPRECATED code (untracked)
│   │   ├── extraction.py           # Old extraction logic
│   │   └── transcripts.py          # Old transcript handling
│   ├── migrations/                  # SQL migrations (17 files)
│   ├── models/                      # Pydantic models
│   │   ├── job_record.py           # Core job model
│   │   ├── job_config.py           # Job configuration
│   │   ├── source.py               # Source + TranscriptProvenance
│   │   ├── claim.py                # Claim + Evidence models
│   │   ├── semantic_units.py       # NEW - Semantic types (untracked)
│   │   └── document_outputs.py     # NEW - Doc 0/1/2 models (untracked)
│   ├── pipeline/                    # Pipeline implementation
│   │   ├── context.py              # PipelineContext dataclass
│   │   ├── stages/                  # Stage implementations (12 files)
│   │   │   ├── __init__.py         # Exports 15 stages
│   │   │   ├── source_identity.py  # NEW - Not exported (untracked)
│   │   │   ├── semantic_extraction.py  # NEW - Not exported (untracked)
│   │   │   └── document_assembly.py    # NEW - Not exported (untracked)
│   │   ├── prompts/                 # LLM prompts (5 files)
│   │   ├── formats/                 # Export formatters (7 files)
│   │   ├── quality_gate.py         # Source filtering
│   │   ├── extraction.py           # Claim extraction
│   │   ├── dual_output.py          # ProducerPacket
│   │   └── _stages_deprecated.py   # Old stage implementations
│   ├── services/                    # Business logic services
│   ├── state/                       # Job persistence abstraction
│   │   ├── factory.py              # Store factory
│   │   └── impl/
│   │       ├── supabase_store.py   # Production store
│   │       └── in_memory.py        # Dev/test store
│   ├── tests/                       # pytest tests (13 files)
│   ├── utils/                       # Utility modules
│   │   ├── validators.py           # Input validation
│   │   ├── llm_validation.py       # LLM output validation
│   │   └── error_handling.py       # Error sanitization
│   └── worker.py                   # Celery task definitions
├── frontend/                        # Next.js frontend
│   ├── components/                  # React components
│   ├── pages/                       # Next.js pages
│   ├── stores/                      # Zustand state
│   └── styles/                      # CSS/Tailwind
├── docs/                            # Documentation
│   ├── authoritative/               # Spec documents
│   │   ├── INDEX.md                # Repo constitution
│   │   └── spec/                   # Specifications
│   │       └── RASS.md             # System spec (8 sections)
│   ├── architecture.md             # System architecture
│   ├── project-overview.md         # Project overview
│   └── code-standards.md           # Code standards
├── .claude/                         # ClaudeKit configuration
│   ├── rules/                       # Project rules
│   ├── skills/                      # AI skills
│   ├── commands/                    # Slash commands
│   └── workflows/                   # Development workflows
├── plans/                           # Plans and reports
└── CLAUDE.md                       # AI assistant instructions
```

### Structure Assessment

- [x] Consistent organization: Yes (backend/frontend split, clear module boundaries)
- [x] Clear separation of concerns: Yes (models/pipeline/integrations/state)
- [x] Follows standard patterns: Yes (FastAPI + Celery + Supabase)

**Issues Found:**
- New semantic pipeline files are untracked (not committed)
- Legacy code exists in `backend/legacy/` but not fully cleaned
- `_stages_deprecated.py` still in pipeline directory
- Some integration clients are unused (brave_search, claimbuster, gdelt, google_factcheck, semantic_scholar)

---

## 2. EXISTING DOCUMENTATION

### CLAUDE.md Summary

The CLAUDE.md is comprehensive (500+ lines) and covers:
- Two operational modes: Video Analysis (primary) and Topic Research (legacy)
- Technology stack: FastAPI, Celery, Redis, Supabase, Next.js
- 11-stage pipeline description for topic research
- API stack recommendations with costs
- Export formats (8 formats including JSON, BibTeX, chapters)
- **Semantic-First Architecture** section (Jan 2026) describing:
  - 3-document model (Doc 0/1/2)
  - Epistemic categories
  - ID/Citation scheme
  - Minimum depth requirements
  - Transcript provenance

### Other Docs Found

| Document | Location | Purpose | Status |
|----------|----------|---------|--------|
| RASS.md | docs/authoritative/spec/ | System specification | Current |
| INDEX.md | docs/authoritative/ | Repo constitution | Current |
| architecture.md | docs/ | System architecture | Current |
| project-overview.md | docs/ | Project overview | Current |
| code-standards.md | docs/ | Code standards | Current |
| gemini-pivot-implementation.md | docs/ | Gemini pivot guide | Current |

### Documentation Issues

1. **CLAUDE.md references non-existent code**: Semantic-First Architecture section describes stages that exist but aren't integrated:
   - `stage_source_identity` - exists but not exported from `__init__.py`
   - `stage_semantic_extraction` - exists but not exported
   - `stage_document_assembly` - exists but not exported

2. **Outdated references**: Some integration descriptions mention "planned" APIs that are already implemented (Exa, Serper)

3. **Missing**: No `DECISIONS.md` file for architectural decision records

---

## 3. DATABASE SCHEMA

### Tables

Based on Supabase store implementation and migrations:

| Table | Columns | Purpose | Status |
|-------|---------|---------|--------|
| `jobs` | id, user_id, title, pipeline, status, stage, stage_started_at, progress_percent, error, config_json, warnings, artifacts (JSONB), outputs (JSONB), created_at, interpretations, selected_interpretations | Job persistence | Active |
| `user_settings` | id, user_id, settings (JSONB), created_at, updated_at | User preferences | Active |
| `admin_users` | id, user_id, email, created_at | Admin role tracking | Active |
| `error_logs` | id, job_id, user_id, user_email, stage, error_type, error_message, stack_trace, created_at | Error tracking | Active |

### JSONB Field Structure

**artifacts** (JSONB):
```python
{
    "drive_folder_url": str,          # Google Drive folder
    "doc_urls": list[str],            # Google Doc URLs
    "clips": list[dict],              # Extracted video clips
    "quotes": list[dict],             # Extracted quotes
    "producer_packet": dict,          # Full ProducerPacket
    "quality_gate_passed": bool,      # Quality check result
    "content_blueprints": list[dict], # Phase 3: Structure analysis
    "gap_analysis": dict,             # Phase 3: Gap analysis
    "research_starter": dict,         # Phase 3: Research starter
}
```

**Missing from artifacts for 3-doc model:**
- `source_ledger`: dict (Doc 0)
- `jump_start`: dict (Doc 1)
- `semantic_brief`: dict (Doc 2)

### Schema Issues

1. **Artifacts model incomplete**: Missing fields for 3-document semantic architecture
2. **No blob storage**: Transcripts stored inline, not in Supabase Storage (spec says blob)
3. **Migration 016-017**: Add disambiguation fields and RPC permissions

---

## 4. DATA MODELS

### Pydantic Models Found

| Model | Location | Purpose | Used By |
|-------|----------|---------|---------|
| `JobRecord` | backend/models/job_record.py | Core job data | State stores, API |
| `Artifacts` | backend/models/job_record.py | Job artifacts | JobRecord |
| `Outputs` | backend/models/job_record.py | Markdown outputs | JobRecord |
| `JobConfig` | backend/models/job_config.py | Job configuration | Pipeline |
| `SourceItem` | backend/models/source.py | Normalized source | Pipeline stages |
| `TranscriptProvenance` | backend/models/source.py | Transcript metadata | Source processing |
| `Claim` | backend/models/claim.py | Extracted claim | Extraction |
| `EvidenceRecord` | backend/models/claim.py | Evidence validation | Validation |
| `AuthUser` | backend/auth/__init__.py | Authenticated user | Auth dependencies |
| **NEW** `SemanticExtractionResult` | backend/models/semantic_units.py | Extraction results | Unintegrated |
| **NEW** `SourceLedger` | backend/models/document_outputs.py | Doc 0 | Unintegrated |
| **NEW** `JumpStartDirections` | backend/models/document_outputs.py | Doc 1 | Unintegrated |
| **NEW** `SemanticBrief` | backend/models/document_outputs.py | Doc 2 | Unintegrated |

### Model Issues

- **Scattered definitions**: Some models in job_record.py, some in claim.py, some in source.py
- **New models not integrated**: semantic_units.py and document_outputs.py exist but not imported by worker
- **Missing from __init__.py**: New model files not exported from backend/models/__init__.py
- **Duplicate TranscriptProvenance**: Exists in both source.py and document_outputs.py

---

## 5. PIPELINE STAGES

### Current Flow (Topic Research - Legacy)

```
[Stage 0] Initialize
    ↓
[Stage 1] Planning (OpenAI) → JobConfig
    ↓
[Stage 2] Research Mapping (Perplexity) → angles, key_terms
    ↓
[Stage 3] Source Discovery (Perplexity/Exa) → web_sources
    ↓
[Stage 3.5] Quality Gate → filtered sources
    ↓
[PARALLEL] Collection:
    ├── [Stage 4] YouTube Enumeration → youtube_videos
    ├── [Stage 5] Transcripts (Supadata/Whisper) → transcripts
    ├── [Stage 6] Web Capture (Jina) → web content
    └── [Stage 6.5] Reddit (PRAW) → reddit_posts
    ↓
[Stage 7] Claim Extraction → claims
    ↓
[PARALLEL] Extraction:
    ├── [Stage 7.5] Timeline
    ├── [Stage 7.6] Entities
    └── [Stage 8] Validation
    ↓
[Stage 8.5] Angle Discovery
    ↓
[Stage 8.6] Documentary Intelligence
    ↓
[Stage 9] Drive Upload
    ↓
[Stage 10] Completion
```

### Current Flow (Video Analysis - Primary)

```
[Celery Task] run_gemini_video_job
    ↓
[GeminiClient.run_full_analysis_pipeline]
    ├── Pass 1: Extraction (clips/quotes)
    ├── Pass 2: Structure Analysis (ContentBlueprint)
    ├── Pass 3: Gap Analysis
    └── Pass 4: Research Starter
    ↓
[create_producer_packet_from_gemini]
    ↓
[Quality Gate + Triage]
    ↓
[Artifacts] → clips, quotes, producer_packet, content_blueprints, gap_analysis, research_starter
```

### Stages Implemented

| Stage | File(s) | Status | Notes |
|-------|---------|--------|-------|
| Initialize | stages/initialization.py | Complete | Sets status, sends Slack |
| Planning | stages/planning.py | Complete | OpenAI-based |
| Research Mapping | stages/planning.py | Complete | Perplexity |
| Source Discovery | stages/discovery.py | Complete | Multi-search |
| Quality Gate | stages/discovery.py | Complete | BM25 filtering |
| YouTube | stages/youtube.py | Complete | Data API v3 |
| Transcripts | stages/youtube.py | Complete | Supadata→Whisper |
| Web Capture | stages/web_capture.py | Complete | Jina/Trafilatura |
| Reddit | stages/web_capture.py | Complete | PRAW |
| Extraction | stages/extraction_stages.py | Complete | OpenAI claims |
| Timeline | stages/extraction_stages.py | Complete | Event extraction |
| Entities | stages/extraction_stages.py | Complete | spaCy NER |
| Validation | stages/analysis.py | Complete | Cross-ref |
| Angle Discovery | stages/analysis.py | Complete | Theme detection |
| Documentary | stages/analysis.py | Complete | Full synthesis |
| Drive Upload | stages/output.py | Complete | Google APIs |
| **Source Identity** | stages/source_identity.py | **NOT EXPORTED** | Pre-LLM identity |
| **Semantic Extraction** | stages/semantic_extraction.py | **NOT EXPORTED** | Gemini semantic |
| **Document Assembly** | stages/document_assembly.py | **NOT EXPORTED** | Doc 0/1/2 |

### Pipeline Issues

1. **New semantic stages not integrated**: Three new stages exist but are not:
   - Exported from `stages/__init__.py`
   - Called from `worker.py`
   - Connected to PipelineContext

2. **PipelineContext missing fields** for semantic pipeline:
   - `source_identity_packages`
   - `semantic_extractions`
   - `source_ledger`
   - `jump_start`
   - `semantic_brief`

3. **Dual architecture**: Video analysis uses GeminiClient directly, bypassing stage system

4. **Missing `generate_json` method**: `semantic_extraction.py` calls `gemini_client.generate_json()` which doesn't exist

---

## 6. EXTERNAL SERVICES

### Integrations Found

| Service | Client Location | Methods Implemented | Status |
|---------|-----------------|---------------------|--------|
| **Gemini 2.5** | gemini_client.py (60KB) | generate, analyze_video, run_full_analysis_pipeline, etc. | Working |
| **OpenAI** | openai_client.py | plan_job, extract_claims, generate_timeline | Working |
| **Perplexity** | perplexity_client.py | search, research_mapping | Working |
| **Exa** | exa_client.py | semantic_search | Working |
| **Serper** | serper_client.py | search | Working |
| **Tavily** | tavily_client.py | search | Demoted (10% 502) |
| **Supadata** | supadata_client.py | get_transcript | Working |
| **YouTube Data API** | youtube_client.py | search, get_video_details | Working |
| **Google Drive/Docs** | google_drive_docs.py | create_doc, upload_to_drive | Working |
| **Jina Reader** | jina_reader_client.py | fetch_content | Working (FREE) |
| **Reddit PRAW** | reddit_client.py | search_subreddit, get_post | Working |
| **Slack** | slack.py | post_message | Working |
| **Whisper** | whisper_client.py | transcribe | Working (fallback) |
| Brave Search | brave_search_client.py | search | Unused |
| ClaimBuster | claimbuster_client.py | check_claim | Unused |
| GDELT | gdelt_client.py | search_articles | Unused |
| Google Factcheck | google_factcheck_client.py | factcheck | Unused |
| Semantic Scholar | semantic_scholar_client.py | search_papers | Unused |

### Integration Issues

1. **5 unused clients**: brave_search, claimbuster, gdelt, google_factcheck, semantic_scholar
2. **No `generate_json` in GeminiClient**: New semantic stage expects this method
3. **GeminiClient methods are SYNC**: New stages use async patterns

---

## 7. PROMPT TEMPLATES

### Prompts Found

| Prompt | Location | Purpose | Complete? |
|--------|----------|---------|-----------|
| `STRUCTURE_ANALYSIS_PROMPT` | prompts/structure_analysis_prompt.py | Pass 2: ContentBlueprint | Yes |
| `GAP_ANALYSIS_PROMPT` | prompts/gap_analysis_prompt.py | Pass 3: GapAnalysis | Yes |
| `RESEARCH_STARTER_PROMPT` | prompts/research_starter_prompt.py | Pass 4: ResearchStarter | Yes |
| `SEMANTIC_EXTRACTION_ROLE` | prompts/semantic_extraction_prompt.py | Semantic extraction (NEW) | Yes (untracked) |
| `SEMANTIC_SYNTHESIS_PROMPT` | prompts/semantic_synthesis_prompt.py | Brief synthesis (NEW) | Yes (untracked) |
| Planning prompts | openai_client.py (inline) | Job planning | Yes |
| Extraction prompts | gemini_client.py (inline) | Clip/quote extraction | Yes |

### Prompt Issues

1. **Inline prompts**: Many prompts embedded in client files, not centralized
2. **New prompts untracked**: semantic_extraction_prompt.py and semantic_synthesis_prompt.py exist but not committed
3. **Guardrails**: Prompts include JSON schema enforcement but variable quality

---

## 8. API ENDPOINTS

### Endpoints Found

| Method | Path | Handler | Status |
|--------|------|---------|--------|
| POST | `/jobs` | create_job_endpoint | Working |
| GET | `/jobs` | list_jobs_endpoint | Working |
| GET | `/jobs/{id}` | get_job_endpoint | Working |
| POST | `/jobs/preview` | preview_job_endpoint | Working |
| POST | `/jobs/{id}/cancel` | cancel_job_endpoint | Working |
| DELETE | `/jobs/{id}` | delete_job_endpoint | Working |
| POST | `/jobs/{id}/archive` | archive_job_endpoint | Working |
| POST | `/jobs/{id}/select-interpretation` | select_interpretation_endpoint | Working |
| **POST** | `/jobs/video-analysis` | create_video_analysis_job | Working (PRIMARY) |
| GET | `/jobs/video-analysis/{id}` | get_video_analysis_status | Working |
| GET | `/jobs/{id}/export` | export_job | Working |
| GET | `/jobs/{id}/export/all` | export_all | Working |
| POST | `/transcripts/extract` | extract_transcripts | Working |
| GET | `/transcripts/jobs/{id}` | get_transcript_job | Working |
| GET | `/settings` | get_user_settings | Working |
| PUT | `/settings` | update_user_settings | Working |
| POST | `/slack/events` | handle_slack_event | Working |
| GET | `/admin/errors` | list_errors | Working (admin only) |

### API Issues

- No issues found. Endpoints are comprehensive and follow REST conventions.
- Rate limiting implemented via slowapi.
- JWT auth properly integrated with Supabase.

---

## 9. CELERY TASKS

### Tasks Found

| Task | Location | Purpose | Status |
|------|----------|---------|--------|
| `run_research_job` | worker.py:64 | Topic-based research (legacy) | Working |
| `run_transcript_job` | worker.py:440 | Batch transcript extraction | Working |
| `run_gemini_video_job` | worker.py:621 | Video analysis (PRIMARY) | Working |

### Task Chain/Orchestration

```
run_research_job:
    → stage_0_initialize
    → stage_1_planning
    → stage_2_research_mapping
    → stage_3_source_shortlist
    → stage_3_5_quality_gate
    → [PARALLEL] collection stages
    → stage_7_extraction
    → [PARALLEL] extraction stages
    → stage_8_5_angle_discovery
    → stage_8_6_documentary_intelligence
    → stage_9_drive_upload
    → stage_10_completion

run_gemini_video_job:
    → GeminiClient.run_full_analysis_pipeline (Pass 1-4)
    → create_producer_packet_from_gemini
    → Quality gate + triage
    → Update artifacts
```

### Task Issues

1. **Dual implementations**: Topic-based uses stage system, video-based uses GeminiClient directly
2. **New stages not called**: `stage_source_identity`, `stage_semantic_extraction`, `stage_document_assembly` exist but aren't invoked
3. **Worker comment at line 586-613**: Documents planned `transcript_acquisition` stage but implementation not connected

---

## 10. TESTS

### Test Files Found

| File | Tests | Focus |
|------|-------|-------|
| test_auth.py | 10 | JWT verification, ban check |
| test_datetime_utils.py | 8 | Date/time utilities |
| test_document_helpers.py | 7 | Document generation |
| test_error_handling.py | ~15 | Error sanitization |
| test_jobs_routes.py | ~20 | API endpoints |
| test_phase3_pipeline.py | ~30 | Phase 3 pipeline |
| test_pipeline_stages.py | ~15 | Stage functions |
| test_rate_limiter.py | ~12 | Rate limiting |
| test_state.py | ~15 | State management |
| test_validators.py | ~10 | Input validation |

**Total: 142 tests collected**

### Test Coverage Assessment

- [x] Authentication tested: Yes
- [x] API endpoints tested: Yes
- [x] Pipeline stages tested: Partial (legacy stages)
- [ ] Semantic stages tested: No (new code)
- [x] State management tested: Yes
- [x] Error handling tested: Yes

### Test Issues

1. **No tests for new semantic stages**: source_identity, semantic_extraction, document_assembly
2. **No tests for semantic models**: semantic_units.py, document_outputs.py
3. **Phase 3 tests exist**: test_phase3_pipeline.py covers video analysis

---

## 11. CONFIGURATION

### Environment Variables Expected

| Variable | Required? | Has Default? | Purpose |
|----------|-----------|--------------|---------|
| REDIS_URL | Yes | Yes (localhost) | Celery broker |
| SUPABASE_URL | No* | No | Job persistence |
| SUPABASE_SERVICE_ROLE_KEY | No* | No | Supabase auth |
| SUPABASE_JWT_SECRET | No* | No | JWT verification |
| OPENAI_API_KEY | Yes | No | Planning/extraction |
| PERPLEXITY_API_KEY | Yes | No | Research mapping |
| GOOGLE_API_KEY | Yes | No | Gemini API |
| SUPADATA_API_KEY | Yes | No | Transcripts |
| YOUTUBE_API_KEY | No | No | YouTube enumeration |
| EXA_API_KEY | No | No | Semantic search |
| SERPER_API_KEY | No | No | Backup search |
| TAVILY_API_KEY | No | No | Fallback search |
| GOOGLE_OAUTH_* | No | No | Drive upload |
| REDDIT_CLIENT_ID/SECRET | No | No | Reddit API |
| SLACK_* | No | No | Slack integration |

*Required for production, optional for dev (in-memory store fallback)

### Config Issues

1. **No .env.example**: Users must guess required variables
2. **JWT validation strict**: 64+ char minimum, may block some test setups
3. **Feature flags exist**: `ENABLE_QUALITY_GATE`, `ENABLE_NICHES` but not well documented

---

## 12. DEAD CODE & REDUNDANCY

### Unused Files

| File | Reason Unused | Recommendation |
|------|---------------|----------------|
| backend/integrations/brave_search_client.py | No imports found | Archive |
| backend/integrations/claimbuster_client.py | No imports found | Archive |
| backend/integrations/gdelt_client.py | No imports found | Archive |
| backend/integrations/google_factcheck_client.py | No imports found | Archive |
| backend/integrations/semantic_scholar_client.py | No imports found | Archive |
| backend/pipeline/_stages_deprecated.py | Replaced by stages/ | Delete |

### Unused Functions

| Function | Location | Recommendation |
|----------|----------|----------------|
| (5 integration clients above) | integrations/ | Archive entire files |
| Legacy stage functions | _stages_deprecated.py | Already deprecated |

### Duplicate Implementations

| Functionality | Locations | Recommendation |
|---------------|-----------|----------------|
| TranscriptProvenance | source.py, document_outputs.py | Keep document_outputs.py |
| Stage orchestration | worker.py (2x) | Merge into unified pipeline |
| Slack messaging | stages/helpers.py, _stages_deprecated.py | Keep stages/helpers.py |

### TODO/FIXME Comments

| Location | Comment | Priority |
|----------|---------|----------|
| worker.py:586-613 | Documents transcript_acquisition stage, not implemented | High |
| gemini_client.py | Various TODOs for error handling | Medium |

### Untracked Files (git status)

```
?? backend/legacy/
?? backend/models/document_outputs.py
?? backend/models/semantic_units.py
?? backend/pipeline/prompts/semantic_extraction_prompt.py
?? backend/pipeline/prompts/semantic_synthesis_prompt.py
?? backend/pipeline/semantic_validation.py
?? backend/pipeline/stages/document_assembly.py
?? backend/pipeline/stages/semantic_extraction.py
?? backend/pipeline/stages/source_identity.py
?? backend/pipeline/transcript_acquisition.py
```

---

## 13. SUMMARY

### What's Built and Working

1. **Video Analysis Pipeline**: Gemini-based 4-pass analysis fully functional
2. **Topic Research Pipeline**: 11-stage legacy pipeline working
3. **API Layer**: Complete CRUD + video analysis endpoints
4. **Authentication**: JWT via Supabase with ban checking
5. **Export System**: 8 formats (JSON, BibTeX, RIS, chapters, clips, social, brief)
6. **External Integrations**: 18 working integrations
7. **Tests**: 142 tests covering core functionality

### What's Built but Broken/Incomplete

1. **Semantic Pipeline Stages** — Exist but not integrated:
   - `stage_source_identity` (not exported)
   - `stage_semantic_extraction` (not exported)
   - `stage_document_assembly` (not exported)

2. **Semantic Models** — Exist but not used:
   - `semantic_units.py` (untracked)
   - `document_outputs.py` (untracked)

3. **PipelineContext** — Missing fields for semantic pipeline:
   - `source_identity_packages`
   - `semantic_extractions`
   - `source_ledger`, `jump_start`, `semantic_brief`

4. **GeminiClient** — Missing `generate_json()` method that semantic_extraction.py expects

5. **Artifacts Model** — Missing 3-doc fields:
   - `source_ledger`
   - `jump_start`
   - `semantic_brief`

### What's Not Built Yet

1. **Deep Research Booster** (RASS Section 4.6)
2. **Blob storage** for transcripts (RASS Section 5.2)
3. **Verification stage** (RASS Section 4.4)
4. **DOC 0 → DOC 2 reference enforcement** (RASS Section 3)

### What Should Be Archived/Removed

1. **backend/pipeline/_stages_deprecated.py** — Replaced by stages/ directory
2. **5 unused integration clients** — brave_search, claimbuster, gdelt, google_factcheck, semantic_scholar
3. **backend/legacy/** — Old extraction code

### Critical Issues to Address First

1. **Export semantic stages to __init__.py** — Blocking integration
2. **Add missing PipelineContext fields** — Blocking semantic pipeline
3. **Add `generate_json()` to GeminiClient** — Blocking semantic extraction
4. **Add 3-doc fields to Artifacts** — Blocking document output storage
5. **Connect semantic stages to worker.py** — Required for full semantic pipeline

---

## 14. RECOMMENDED NEXT STEPS

Before implementing new features, I recommend:

1. **Commit existing semantic code** (currently untracked):
   ```bash
   git add backend/models/semantic_units.py backend/models/document_outputs.py
   git add backend/pipeline/stages/source_identity.py
   git add backend/pipeline/stages/semantic_extraction.py
   git add backend/pipeline/stages/document_assembly.py
   git add backend/pipeline/transcript_acquisition.py
   git add backend/pipeline/prompts/semantic_*.py
   ```

2. **Update stages/__init__.py** to export new stages:
   ```python
   from .source_identity import stage_source_identity
   from .semantic_extraction import stage_semantic_extraction
   from .document_assembly import stage_document_assembly
   ```

3. **Add missing PipelineContext fields**:
   ```python
   source_identity_packages: list = field(default_factory=list)
   semantic_extractions: list = field(default_factory=list)
   source_ledger: Optional[dict] = None
   jump_start: Optional[dict] = None
   semantic_brief: Optional[dict] = None
   ```

4. **Add `generate_json()` to GeminiClient** or modify semantic_extraction to use existing `generate()` method

5. **Update Artifacts model** with 3-doc fields

6. **Archive unused integrations** to reduce maintenance burden

7. **Add tests** for new semantic stages before integration

---

## 15. QUESTIONS FOR PROJECT OWNER

Things I need clarification on before proceeding:

1. **Which pipeline should semantic stages integrate with?**
   - Video Analysis (run_gemini_video_job) only?
   - Topic Research (run_research_job) too?
   - Both via unified pipeline?

2. **Should semantic stages REPLACE or AUGMENT existing Gemini 4-pass?**
   - Replace: Remove existing passes, use semantic stages
   - Augment: Keep passes, add semantic stages after

3. **What's the intended blob storage strategy?**
   - RASS says Supabase Storage for transcripts
   - Current code stores inline
   - When should migration happen?

4. **Should we delete the 5 unused integration clients?**
   - brave_search, claimbuster, gdelt, google_factcheck, semantic_scholar
   - Or keep for potential future use?

5. **What's the target for Deep Research Booster?**
   - RASS Section 4.6 describes it
   - No implementation exists
   - Priority vs semantic pipeline?

---

**END OF AUDIT REPORT**
