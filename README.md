# Research Agent

AI-powered documentary research assistant that makes long-form video content scannable. Two modes:

**Primary Mode (Jan 2026): Video Analysis**
- User provides YouTube URLs → Gemini extracts timestamped clips and quotes
- Output: ProducerPacket with verified clips, quotes, and quality gate status

**Legacy Mode: Topic Research**
- User enters topic → System discovers sources → Extraction pipeline
- Output: NotebookLM Packet, Documentary Blueprint, Research Brief

## Production Status

| Service | Status | URL |
|---------|--------|-----|
| **Frontend** | ✅ Live | https://research-agent-kohl.vercel.app |
| **API** | ✅ Live | https://api-production-1c52.up.railway.app |
| **Worker** | ✅ Live | Celery worker (internal) |
| **Redis** | ✅ Live | redis.railway.internal:6379 |

## Features

### Semantic Pipeline (Primary)
- **6 Analysis Modes**: transcript_grounded, caption_grounded, video_only, text_provided, ocr_extracted, article_fetched
- **Source Isolation**: Each source extracted in separate LLM call (prevents cross-contamination)
- **Confidence Ceilings**: Mode-based confidence limits (HIGH/MEDIUM/LOW)
- **Quote Verification**: Fuzzy matching against source transcripts
- **Provenance Tracking**: Every claim traces back to source with timestamp/quote
- **Multi-Source Synthesis**: Cross-source themes, tensions, and gaps

### Input Types
- **YouTube Videos**: Full transcript or caption-based analysis
- **Web Articles**: Article text extraction via Jina/Trafilatura
- **Text Input**: User-provided text content (copy-paste)
- **Screenshots**: OCR extraction with platform hints

### Output Documents
- **Doc 0 (Source Ledger)**: Full transcripts, metadata, indexes
- **Doc 1 (Jump-Start)**: Gaps, research directions, next steps
- **Doc 2 (Semantic Brief)**: Themes, key points, tensions, confidence
- **Doc 3 (Producer Packet)**: Creative interpretation (optional, gated)

### Extended Features
- **Evolving Jobs**: Add sources to completed jobs with addendum
- **Deep Research Booster**: Suggests research directions (not facts)
- **Cross-Reference Stage**: Identifies supports/contradicts between sources

### Quality Assurance
- **948 Automated Tests**: Comprehensive test coverage
- **Validation Stage**: Quote verification, ceiling enforcement, provenance check
- **Rate Limiting**: 60 req/min with exponential backoff

### User Experience
- **Dark Mode UI**: Modern dark-mode-first design with glow effects and animations
- **Real-time Progress**: Stage-based ETA calculation with accurate time estimates
- **Expanding Job Cards**: Inline job details without page navigation
- **AI-Generated Titles**: Concise titles generated from verbose prompts
- **User Authentication**: Supabase-based auth with per-user job isolation
- **Multi-folder Support**: Link up to 3 Google Drive folders per user

### Admin Features
- **Admin Dashboard**: User management, job monitoring, error tracking
- **Error Logging**: Centralized error tracking with stack traces
- **Job Management**: View and manage all user jobs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐         ┌─────────────────────────────────┐│
│  │    VERCEL       │         │           RAILWAY               ││
│  │                 │         │                                 ││
│  │  ┌───────────┐  │  HTTPS  │  ┌─────────┐    ┌───────────┐  ││
│  │  │  Next.js  │◄─┼────────►│  │   API   │◄──►│   Redis   │  ││
│  │  │  Frontend │  │         │  │ FastAPI │    │           │  ││
│  │  └───────────┘  │         │  └────┬────┘    └───────────┘  ││
│  │                 │         │       │                         ││
│  └─────────────────┘         │  ┌────▼────┐                    ││
│                              │  │  Worker │                    ││
│                              │  │  Celery │                    ││
│                              │  └─────────┘                    ││
│                              └─────────────────────────────────┘│
│                                         │                        │
│                              ┌──────────▼──────────┐            │
│                              │     SUPABASE        │            │
│                              │   (PostgreSQL)      │            │
│                              └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (for Celery broker/backend)
- Supabase project (for database and auth)

## Project Structure

```
Research_Agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application (27 routes)
│   │   └── routes.py            # Additional routers
│   ├── auth/
│   │   ├── __init__.py          # Auth models and utilities
│   │   ├── dependencies.py      # FastAPI auth dependencies
│   │   └── admin.py             # Admin role management
│   ├── integrations/
│   │   ├── openai_client.py     # OpenAI API for planning/extraction
│   │   ├── perplexity_client.py # Perplexity for research/validation
│   │   ├── youtube_client.py    # YouTube Data API
│   │   ├── google_drive_docs.py # Google Drive/Docs integration
│   │   ├── exa_client.py        # Exa.ai semantic search
│   │   ├── brave_search_client.py # Brave Search API
│   │   ├── jina_reader_client.py  # Jina Reader for content extraction
│   │   ├── claimbuster_client.py  # ClaimBuster fact-checking
│   │   ├── reddit_client.py     # Reddit API integration
│   │   └── ...                  # Other integrations
│   ├── pipeline/
│   │   ├── extraction.py        # Claim extraction
│   │   ├── validation.py        # Claim validation
│   │   ├── timeline.py          # Timeline event extraction
│   │   ├── entities.py          # Entity extraction
│   │   ├── angle_discovery.py   # Documentary angle discovery
│   │   └── documentary_intelligence.py # Documentary blueprint generation
│   ├── models/
│   │   ├── job.py               # API request/response models
│   │   ├── job_record.py        # Database job model
│   │   ├── job_config.py        # Pipeline configuration
│   │   ├── user_settings.py     # User settings model
│   │   └── ...                  # Other models
│   ├── state/
│   │   ├── __init__.py          # State management exports
│   │   ├── factory.py           # Job store factory
│   │   ├── settings_store.py    # User settings CRUD
│   │   └── impl/                # Store implementations
│   ├── services/
│   │   ├── transcript_service.py # Transcript processing
│   │   └── error_logger.py      # Error logging service
│   ├── migrations/              # SQL migrations (001-010)
│   ├── config.py                # Settings with Pydantic
│   └── worker.py                # Celery worker and tasks
├── frontend/
│   ├── pages/
│   │   ├── index.tsx            # Landing page
│   │   ├── dashboard.tsx        # Job dashboard
│   │   ├── settings.tsx         # User settings
│   │   ├── login.tsx            # Authentication
│   │   ├── transcripts.tsx      # Transcript extraction
│   │   └── admin/               # Admin pages
│   ├── components/
│   │   ├── JobCard.tsx          # Expandable job card
│   │   ├── Layout.tsx           # Main layout with sidebar
│   │   └── ui/                  # UI component library
│   │       ├── AnimatedButton.tsx
│   │       ├── GlowCard.tsx
│   │       ├── GradientText.tsx
│   │       ├── ProgressRing.tsx
│   │       ├── Skeleton.tsx
│   │       └── StageIndicator.tsx
│   ├── hooks/
│   │   └── useETA.ts            # Stage-based ETA calculation
│   └── store/                   # Zustand state stores
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Unified container (API + Worker)
├── entrypoint.sh                # Service selector (SERVICE_TYPE env var)
├── docker-compose.yml           # Local development
└── DEPLOYMENT_GUIDE.md          # Production deployment guide
```

## Setup

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

### Frontend Setup

```bash
cd frontend
npm install
```

## Running Locally

### Start Backend

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
source venv/bin/activate
celery -A backend.worker worker --loglevel=INFO

# Terminal 3: Start API server
source venv/bin/activate
uvicorn backend.app.main:app --reload
```

API available at `http://localhost:8000` (Swagger docs at `/docs`)

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend available at `http://localhost:3000`

## Testing

### Backend Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all backend tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing

# Run specific test file
pytest backend/tests/test_extraction.py -v
```

### Frontend Tests

```bash
cd frontend

# Run linting
npm run lint

# Type check
npx tsc --noEmit

# Build (includes type checking)
npm run build
```

### Pre-commit Checks

```bash
# Backend
source venv/bin/activate
pytest backend/tests/

# Frontend
cd frontend
npm run lint && npm run build
```

## API Endpoints

### Authentication
- `GET /auth/me` - Get current user info

### User Settings
- `GET /settings` - Get user settings
- `PUT /settings` - Update user settings
- `POST /settings/validate-folder` - Validate Google Drive folder
- `GET /settings/check-username` - Check username availability
- `GET /settings/oauth-status` - Check Google OAuth connection status

### Video Analysis (Primary)
- `POST /jobs/video-analysis` - Create video analysis job (accepts YouTube URLs)
- `GET /jobs/video-analysis/{job_id}` - Get video analysis status with clips/quotes

### Research Jobs (Legacy)
- `POST /jobs` - Create research job
- `GET /jobs` - List user's jobs
- `GET /jobs/{job_id}` - Get job status
- `POST /jobs/{job_id}/cancel` - Cancel job

### Transcript Extraction
- `POST /transcripts` - Extract YouTube transcripts
- `GET /transcripts/{job_id}` - Get transcript job status

### Admin (Requires admin role)
- `GET /admin/check` - Check admin status
- `GET /admin/stats` - Dashboard statistics
- `GET /admin/users` - List users
- `GET /admin/jobs` - List all jobs
- `GET /admin/errors` - List error logs
- And more...

## Environment Variables

See `.env.example` for the complete list. Key variables:

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `SUPABASE_JWT_SECRET` | JWT secret for auth |
| `SUPABASE_JWT_AUDIENCE` | JWT audience claim (default: "authenticated") |
| `GOOGLE_API_KEY` | Google API key for Gemini 2.5 (video analysis) |
| `OPENAI_API_KEY` | OpenAI API key |
| `PERPLEXITY_API_KEY` | Perplexity API key |
| `GOOGLE_OAUTH_*` | Google OAuth credentials |
| `FRONTEND_ORIGINS` | Allowed CORS origins |

## Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production deployment to Railway and Vercel.

## Documentation

### Core Documentation
- **[Gemini Pivot](docs/gemini-pivot-implementation.md)** - Video analysis implementation (Jan 2026)
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code
- **[Architecture](docs/architecture.md)** - System architecture overview
- **[Code Standards](docs/code-standards.md)** - Coding conventions

### Strategic Planning
- `plans/strategic-pivot-jan-2026-v3-recalibrated.md` - Strategic decision rationale
- `plans/reports/` - Research reports and analysis

### Deployment & Operations
- `DEPLOYMENT_GUIDE.md` - Production deployment instructions

### Archived
- See `Archive Docs/` for superseded PRDs (v2, v3, v4.3, v5.0)

## License

Proprietary - All rights reserved.
