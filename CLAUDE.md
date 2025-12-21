# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research Agent is a cloud-based research backend that aggregates content from Reddit, Twitter, articles, YouTube, and other sources. It processes research topics through a multi-stage pipeline that includes AI-powered planning, web scraping, transcript extraction, claim validation, and Google Drive document generation.

**Current Phase:** Production Deployment (Phase 1-4 complete, deploying to Railway)

## Production Deployment Status (December 2024)

### Railway Project
- **Project ID:** `60023fa4-e900-4049-8dde-d90a43c295ad`
- **Environment:** production

### Services Deployed

| Service | Status | URL/Notes |
|---------|--------|-----------|
| **API (Research_Agent)** | ✅ LIVE | https://researchagent-production-2d94.up.railway.app |
| **Worker** | ⚠️ IN PROGRESS | Needs Dockerfile.worker configuration |
| **Redis** | ✅ Running | Internal: redis.railway.internal:6379 |

### Remaining Deployment Tasks
1. **Worker Service**: Configure Builder to "Dockerfile" and set path to `Dockerfile.worker`
2. **FRONTEND_ORIGINS**: Update to include Vercel domain once frontend is deployed
3. **Frontend (Vercel)**: Deploy Next.js frontend to Vercel

### Key Commands
```bash
# Link to Railway project
railway link -p 60023fa4-e900-4049-8dde-d90a43c295ad

# Check status
railway status
railway service status

# View logs
railway logs -n 50

# Switch between services
railway service Research_Agent
railway service Worker

# Deploy
railway up
```

## Architecture

### Backend (FastAPI + Celery)

The backend is a distributed system with three main components:

1. **FastAPI HTTP API** (`backend/app/main.py`) - REST API for job creation and status tracking
2. **Celery Worker** (`backend/worker.py`) - Asynchronous task processor for research pipeline
3. **Redis** - Message broker and result backend for Celery

#### Key Design Patterns

- **State Management**: Dual-mode job storage via factory pattern (`backend/state/factory.py`)
  - `SupabaseJobStore`: Production persistence with Supabase (when configured)
  - `InMemoryJobStore`: Local development fallback (when Supabase not configured)
  - The system automatically selects the appropriate implementation based on environment variables

- **Configuration**: Centralized settings using Pydantic (`backend/config.py`)
  - Environment-based configuration with `.env` file
  - Validation helpers for feature-specific settings (e.g., `require_supabase()`, `require_youtube()`)
  - All API keys and credentials are loaded from environment variables

- **Pipeline Stages**: The research pipeline (`backend/worker.py:run_research_job`) runs 10 sequential stages:
  1. Initialization
  2. Planning (OpenAI - generates JobConfig)
  3. Research mapping (Perplexity - identifies angles and key terms)
  4. Source discovery (Perplexity - finds relevant URLs)
  5. YouTube enumeration (YouTube Data API - finds relevant videos)
  6. Transcript fetching (youtube-transcript-api)
  7. Web capture (Playwright + Trafilatura)
  8. Claim extraction (OpenAI - generates quote bank and claims ledger)
  9. Claim validation (Perplexity - validates claims with evidence)
  10. Drive document generation (Google Drive + Docs APIs)

- **Error Handling**: Graceful degradation - stages can fail without stopping the entire pipeline. Warnings are collected in `JobRecord.warnings` and partial results are still saved.

### Frontend (Next.js)

- **Framework**: Next.js 14 with TypeScript
- **Pages Router**: Uses `pages/` directory structure (not App Router)
- **Styling**: Tailwind CSS with custom configuration

### Data Models

Key Pydantic models in `backend/models/`:

- `JobRecord`: Complete job state including status, progress, outputs, and artifacts
- `JobConfig`: Pipeline configuration (mode, budgets, YouTube channels, etc.)
- `SourceItem`: Web source or article with captured content
- `TranscriptItem`: YouTube video transcript
- `Claim`: Extracted claim from content
- `EvidenceRecord`: Validation result for a claim

### Integrations (`backend/integrations/`)

**Core Integrations:**
- `openai_client.py`: Job planning and claim extraction using GPT-4
- `perplexity_client.py`: Research mapping, source discovery, and claim validation
- `youtube_client.py`: Channel enumeration and video metadata
- `transcripts.py`: YouTube transcript fetching
- `web_capture.py`: Playwright-based web scraping with Trafilatura text extraction
- `google_drive_docs.py`: Google Drive folder and Docs creation
- `slack.py`: Slack webhook integration for notifications

**V2 API Integrations (added December 2024):**
- `exa_client.py`: Exa.ai semantic search
- `brave_search_client.py`: Brave Search API
- `jina_reader_client.py`: Jina Reader for content extraction
- `claimbuster_client.py`: ClaimBuster fact-checking API
- `google_factcheck_client.py`: Google Fact Check Tools API
- `gdelt_client.py`: GDELT news/events API
- `semantic_scholar_client.py`: Academic paper search
- `whisper_client.py`: OpenAI Whisper transcription
- `reddit_client.py`: Reddit API (PRAW)

## Development Commands

### Backend Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your API keys and credentials
```

### Running the Backend

```bash
# Start Redis (required)
brew services start redis  # macOS with Homebrew
# or: redis-server

# Start Celery worker (in separate terminal)
celery -A backend.worker worker --loglevel=INFO

# Start API server (in separate terminal)
uvicorn backend.app.main:app --reload
```

API available at `http://localhost:8000` (Swagger docs at `/docs`)

### Frontend Setup and Running

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build
npm start

# Lint
npm run lint
```

Frontend runs on `http://localhost:3000`

### Testing the System

```bash
# Health check
curl http://localhost:8000/health

# Create research job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "AI safety research", "pipeline": "quick"}'

# Check job status (replace {job_id})
curl http://localhost:8000/jobs/{job_id}
```

## Important Configuration Notes

- **Supabase**: If `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are not set, the system uses in-memory storage (jobs lost on restart)
- **Pipeline Modes**: Two modes available - `quick` (lower budgets, faster) and `full` (higher budgets, comprehensive)
- **CORS**: Frontend origins must be explicitly configured in `FRONTEND_ORIGINS` (comma-separated list)
- **Budget Controls**: Pipeline respects budget limits in `JobConfig.budgets` (max URLs, transcription minutes, claims to validate)

## Key Files to Know

- `backend/worker.py`: Main research pipeline orchestration
- `backend/app/main.py`: API endpoints and request/response handling
- `backend/config.py`: Configuration management and validation
- `backend/state/factory.py`: Job storage abstraction
- `backend/models/job_record.py`: Job state schema
- `backend/models/job_config.py`: Pipeline configuration schema
- `.env.example`: Template for required environment variables

## Common Development Patterns

**Adding a new integration:**
1. Create client in `backend/integrations/`
2. Add configuration to `backend/config.py` with validation helper
3. Import and use in `backend/worker.py` pipeline stage
4. Update `JobConfig` model if new settings are needed

**Modifying the pipeline:**
- All stages in `backend/worker.py:run_research_job()`
- Update job progress with `update_job()` between stages
- Collect warnings in `warnings` list for non-fatal errors
- Store outputs in `outputs` dict, artifacts in separate dict

**Adding a new API endpoint:**
1. Add route in `backend/app/main.py` or create new router in `backend/app/routes.py`
2. Create request/response models in `backend/models/job.py`
3. Use `get_job()`, `create_job()`, or `update_job()` from `backend/state/`

## Environment Variables Required

See `.env.example` for complete list. Critical ones:

- `REDIS_URL`: Redis connection string (required)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: Job persistence (optional, uses in-memory if not set)
- `OPENAI_API_KEY`: Required for planning and extraction stages
- `PERPLEXITY_API_KEY`: Required for research mapping and validation
- `YOUTUBE_API_KEY`: Optional, for YouTube integration
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`: Optional, for Drive uploads
- `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN`: Optional, for Slack notifications
