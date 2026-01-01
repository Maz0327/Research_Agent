# System Architecture

**Last Updated:** January 1, 2026
**Status:** Production + Export Formats + Reliability Fixes

## Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│   Celery    │
│   (Vercel)  │◀────│   (Railway) │◀────│   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Supabase   │     │    Redis    │
                    │   (Jobs)    │     │   (Queue)   │
                    └─────────────┘     └─────────────┘
```

## Components

### FastAPI API (`backend/app/main.py`)
- REST endpoints for job CRUD
- Authentication via Supabase JWT
- Rate limiting via slowapi

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs` | List user's jobs |
| POST | `/jobs` | Create new research job |
| GET | `/jobs/{id}` | Get job details |
| POST | `/jobs/preview` | Preview job plan before execution |
| POST | `/jobs/{id}/cancel` | Cancel running job |
| DELETE | `/jobs/{id}` | Delete job (soft delete) |
| POST | `/jobs/{id}/archive` | Archive completed job |
| POST | `/jobs/{id}/select-interpretation` | Select disambiguation option |
| GET | `/jobs/{id}/export` | Export job in specified format |
| GET | `/jobs/{id}/export/all` | Export all formats at once |

### Celery Worker (`backend/worker.py`)
- Async task processing
- 11-stage research pipeline
- Graceful error handling

### Pipeline Stages

| # | Stage | Current Service | Optimal Service | Cloud Status |
|---|-------|-----------------|-----------------|--------------|
| 1 | Initialize | - | - | ✅ |
| 2 | Planning | OpenAI GPT-4o-mini | **Gemini 2.5 Flash** | ✅ |
| 3 | Research Mapping | Perplexity | Perplexity (keep) | ✅ |
| 4 | Source Discovery | Perplexity | **Exa + Perplexity** | ✅ |
| 5 | YouTube Enumeration | YouTube Data API v3 | YouTube Data API v3 | ✅ (optional) |
| 6 | Transcript Extraction | Supadata → Whisper | Supadata → Whisper | ✅ |
| 7 | Web Capture | Jina/Trafilatura | Jina/Trafilatura (keep) | ✅ |
| 8 | Reddit Collection | PRAW | PRAW (keep) | ✅ |
| 9 | AI Extraction | OpenAI GPT-4o-mini | GPT-4o-mini (keep) | ✅ |
| 10 | Validation + Analysis | Perplexity/OpenAI | **Gemini 2.5 Pro** | ✅ |
| 11 | Drive Upload | Google APIs | Google APIs (keep) | ✅ |

**Note**: youtube-transcript-api REMOVED (fails on cloud IPs). Transcripts use Supadata → Whisper only.

## Research-Validated API Stack

### LLM Selection by Task

| Task | Optimal Model | Rationale |
|------|---------------|-----------|
| Planning | Gemini 2.5 Flash | 1M context, $0.30/$2.50, thinking mode |
| Extraction | GPT-4o-mini | Fast, cheap, structured output |
| Vision/PDF | Gemini 2.5 Pro | 1M context, multimodal-native |
| Synthesis | Gemini 2.5 Pro | Quality-critical final output |

### Search Selection by Mode

| Mode | APIs | Rationale |
|------|------|-----------|
| breaking_news | Perplexity | Speed: 358ms |
| investigation | Exa + Perplexity | Accuracy: 94.9% |
| profile | Exa | Semantic entity search |
| fallback | Serper > Tavily | Tavily has 10% 502 error rate |

## ML Optimization Opportunities

### Already Optimal (No LLM)
- **Quality Gate** (`backend/pipeline/quality_gate.py`): Deterministic filtering with BM25
- **Entity Extraction** (`backend/pipeline/entities.py`): spaCy NER
- **Claim Candidates** (`backend/pipeline/extraction.py`): Regex heuristics

### Completed Optimizations (Dec 2025)

| Component | Before | After | File |
|-----------|--------|-------|------|
| BM25 Relevance | +0.2 bonus | 60% blend into relevance | `quality_gate.py` |
| Recency Scoring | None | Mode-specific (10% weight) | `quality_gate.py` |
| Priority Keywords | Defined but unused | Active (+0.1 bonus) | `quality_gate.py` |
| Preferred Domains | Defined but unused | Active (+0.15 bonus) | `quality_gate.py` |
| Diversity Metric | None | Shannon entropy (monitoring) | `quality_gate.py` |

### Pending Optimizations

| Component | Current | Optimal | File |
|-----------|---------|---------|------|
| Claim Dedup | O(n²) Jaccard | MinHash LSH O(n) | `extraction.py` |
| spaCy Model | en_core_web_sm | en_core_web_trf | `entities.py` |
| Claim Threshold | score >= 3 | score >= 4 | `extraction.py` |

## Reliability Features (Dec 2025)

### Lazy Loading (`backend/integrations/lazy_loader.py`)
- All optional integrations are lazy-loaded
- Missing dependencies don't crash the app
- Graceful degradation when services unavailable

### Stage Error Recovery (`backend/pipeline/stage_runner.py`)
- `run_stage_with_recovery()` wraps all pipeline stages
- Fallback functions for non-critical stages (YouTube, Reddit, transcripts)
- `StageGroup` tracks aggregate results for parallel stages
- Critical stages (planning, research mapping) fail fast

### LLM Validation (`backend/utils/llm_validation.py`)
- `validate_and_repair()` validates LLM output against Pydantic schemas
- Retry loop with LLM-based repair for invalid outputs
- Falls back to degraded defaults when repair fails

### Niche/Category System (`backend/config/niches/`)
- 5 niche categories: pop_culture, political, true_crime, mysteries, downfalls
- Each niche defines: source_floors, query_additions, priority_keywords, preferred_domains
- Quality Gate applies:
  - Niche source_floors (override mode defaults)
  - Priority keywords boost (+0.1 max for matching sources)
  - Preferred domains bonus (+0.15 for niche-relevant domains)

## Key Files

- `backend/pipeline/stages.py` - Pipeline orchestration
- `backend/pipeline/context.py` - Shared pipeline state
- `backend/pipeline/stage_runner.py` - Error recovery wrapper
- `backend/pipeline/quality_gate.py` - Deterministic source filtering
- `backend/pipeline/extraction.py` - Claim extraction with hybrid approach
- `backend/pipeline/entities.py` - spaCy-based entity extraction
- `backend/integrations/lazy_loader.py` - Lazy integration loading
- `backend/utils/llm_validation.py` - LLM output validation
- `backend/state/factory.py` - Job store abstraction
- `backend/models/job_config.py` - Mode configurations

## Data Flow

### Two-Step Job Creation

1. User enters topic and selects mode/category
2. Frontend calls `/jobs/preview` to get interpreted plan
3. User reviews: interpreted topic, sources, subreddits
4. User can modify sources/subreddits before confirming
5. User confirms → Frontend calls `/jobs` to create job
6. API creates job in Supabase with user's selections
7. Celery picks up task from Redis
8. Pipeline runs 11 stages
9. Results uploaded to Google Drive
10. Job marked complete

### Job Lifecycle

```
preview → queued → running → completed
                          ↘ failed
                          ↘ cancelled
                          ↘ disambiguating → (user input) → queued
```

### Soft Delete Pattern

Jobs use soft deletion via status field:
- `DELETE /jobs/{id}` → sets status to "deleted"
- `POST /jobs/{id}/archive` → sets status to "archived"
- Both remove job from user's visible list without data loss

## Error Handling

- Stages can fail without stopping pipeline
- Warnings collected in `JobRecord.warnings`
- Fallback chains for external APIs
- Partial results preserved on failure

## Graceful Degradation Chains

| Function | Tier 1 | Tier 2 | Tier 3 |
|----------|--------|--------|--------|
| Web Capture | Jina Reader (FREE) | Trafilatura | Playwright |
| Transcripts | Supadata | Whisper | youtube-api* |
| Search | Exa/Perplexity | Serper | Tavily |
| LLM | Gemini Flash | GPT-4o-mini | - |

*youtube-transcript-api fails on cloud IPs (Railway, AWS)

## Frontend Architecture

### Layout (`frontend/components/Layout.tsx`)
- Collapsible sidebar (icons-only mode on desktop)
- Mobile-first responsive design
- Hamburger menu for mobile navigation
- Slide-in sidebar with overlay

### State Management (`frontend/store/jobs.ts`)
- Zustand store for job state
- `preview` state for two-step job creation
- `previewJob()` → calls `/jobs/preview`
- `createJob()` → calls `/jobs` with custom options
- `deleteJob()` / `archiveJob()` → job management

### Job Cards (`frontend/components/job-card/`)
- `JobCard.tsx` - Main card with status display
- `JobActions.tsx` - Cancel/Delete/Archive buttons
- `DisambiguationPanel.tsx` - User input for ambiguous topics
- `JobProgress.tsx` - Progress bar and stage display

### Dashboard (`frontend/pages/dashboard.tsx`)
- Research form with mode/category dropdowns
- Preview confirmation card with editable sources
- Subreddit add/remove functionality
- Job list with real-time refresh

## Export System (Jan 2026)

### Export Formats (`backend/pipeline/formats/`)
- `json_export.py` - Lossless structured data
- `citation_export.py` - BibTeX/RIS citations
- `chapter_export.py` - Podcast/YouTube chapters
- `clip_export.py` - Short-form video suggestions
- `social_export.py` - Social media content kit
- `brief_export.py` - Research Brief (LLM synthesis)
- `export_manager.py` - Unified interface

### Research Brief
Uses Gemini 2.5 Pro with GPT-4o-mini fallback:
- Claims matrix with evidence levels (VERIFIED/PROBABLE/SPECULATIVE/DISPUTED)
- Key figures with roles and quotes
- Timeline with source attribution
- Multiple perspectives (mainstream/alternative/unexplored)

### Rate Limiting (`backend/app/rate_limiter.py`)
Key function priority:
1. Authenticated user_id (prevents NAT throttling)
2. X-Forwarded-For (proxy support)
3. Client IP (fallback)

### Bug Fixes (Jan 2026)
- Celery `apply_async(task_id=job_id)` enables reliable cancellation
- Validation errors return 422 (FastAPI convention)
- In-memory store initializes models before merging
- Frontend MAX_PROMPT_LENGTH = 2000 (matches backend)
