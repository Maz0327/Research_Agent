# CLAUDE.md

This file provides guidance to Claude Code when working with Research Agent.

## Project Overview

Research Agent is an AI-powered documentary research assistant that aggregates content from multiple sources (Reddit, YouTube, web articles) and produces:
1. **NotebookLM Packet** - Optimized for AI podcast generation
2. **Documentary Blueprint** - Optimized for video production
3. **Research Brief** - Human-readable analysis with evidence hierarchy (Jan 2026)

**Status**: Production (Railway backend, Vercel frontend, Supabase database)

## Directory Map

```
./
├── backend/                    # FastAPI + Celery backend
│   ├── app/main.py            # API endpoints
│   ├── pipeline/              # 11-stage research pipeline
│   │   ├── stages.py          # Stage implementations
│   │   ├── context.py         # Shared pipeline state
│   │   ├── quality_gate.py    # Source filtering
│   │   └── dual_output.py     # NotebookLM + Documentary
│   ├── integrations/          # External API clients
│   ├── models/                # Pydantic models
│   ├── state/                 # Job storage (Supabase/memory)
│   └── config.py              # Configuration
├── frontend/                   # Next.js frontend
│   ├── pages/                 # Page routes
│   ├── components/            # React components
│   └── stores/                # Zustand state
├── docs/                       # Project documentation
└── .claude/                    # ClaudeKit configuration
    ├── rules/                 # Project-specific rules
    ├── skills/                # AI skills
    ├── commands/              # Slash commands
    └── workflows/             # Development workflows
```

## Export Formats (Jan 2026)

| Format | Extension | Use Case |
|--------|-----------|----------|
| JSON | .json | Lossless data for AI pipelines |
| BibTeX | .bib | Academic citations |
| RIS | .ris | Reference manager import |
| Chapters | .json | Podcast chapter markers |
| YouTube Chapters | .txt | Video description timestamps |
| Clips | .json | Short-form video suggestions |
| Social | .json | Social media content kit |
| Brief | .md | Human-readable research analysis |

API: `GET /jobs/{id}/export?format=brief&download=true`

## Technology Stack

- **Backend**: FastAPI, Celery, Redis, Python 3.11
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **LLM**: OpenAI GPT-4o-mini (current), Gemini 2.5 Flash/Pro (planned)
- **Search**: Perplexity, Exa (planned), Tavily (demoted to fallback)
- **Deployment**: Railway (backend), Vercel (frontend)

## Final API Stack (December 2025)

**Budget:** $130/month | **Volume:** 60 jobs | **Goal:** Human-replacement quality

### LLM Selection by Task
| Task | Model | Cost | Status |
|------|-------|------|--------|
| Planning | Gemini 2.5 Flash | $0.30/$2.50 | Add |
| Extraction | GPT-4o-mini | $0.15/$0.60 | ✅ Keep |
| Vision/PDF | Gemini 2.5 Pro | $1.25/$10 | Add |
| Validation | Gemini 2.5 Pro | $1.25/$10 | Add |
| Synthesis | Claude Sonnet 4 (complex) / Gemini Pro | $3/$15 | Add |

### Search Selection by Mode
| Mode | APIs | Cost/Job |
|------|------|----------|
| breaking_news | Perplexity | $0.20 |
| investigation | Exa + Perplexity (40 searches) | $0.80 |
| profile | Exa (semantic entity) | $0.50 |
| fallback | Serper (NOT Tavily - 10% 502 rate) | $0.01 |

### ML Optimizations (FREE - Local)
- **Quality Gate**: Deterministic - ✅ Optimal (Dec 2025 accuracy improvements)
  - BM25 blended into relevance (60% weight)
  - Mode-specific recency scoring (10% weight)
  - Niche priority keywords (+0.1 bonus)
  - Niche preferred domains (+0.15 bonus)
  - Shannon entropy diversity metric
- **Entity Extraction**: spaCy en_core_web_trf (+6% F1)
- **Claim Dedup**: MinHash LSH (O(n) scaling)
- **Source Scoring**: BM25 hybrid ranking

### Monthly Cost Breakdown (~$115-120)
- Search: ~$25 (Exa + Perplexity + Serper)
- LLM: ~$70 (Gemini Flash/Pro + GPT-4o-mini + Claude)
- Content: ~$17 (Supadata)
- ML: $0 (local processing)

## Development Commands

```bash
# Backend
source venv/bin/activate
uvicorn backend.app.main:app --reload        # API server
celery -A backend.worker worker --loglevel=INFO  # Worker

# Frontend
cd frontend && npm run dev                    # Dev server
npm run build && npm run lint                 # Build + lint

# Testing
pytest                                        # Backend tests
curl http://localhost:8000/health             # Health check
```

## Verification Before Commit

```bash
# Must pass before committing
pytest                                        # Backend tests
cd frontend && npm run lint && npm run build  # Frontend checks
```

## Key Rules

@./.claude/rules/research-agent.md
@./.claude/rules/api-integrations.md
@./.claude/workflows/development-rules.md

## Core Documentation

@./docs/project-overview.md
@./docs/architecture.md
@./docs/code-standards.md

## Skills to Activate

For Research Agent development, activate:
- `research-agent` - Pipeline and integration development
- `debugging` - Issue investigation
- `code-review` - Post-implementation review

## Research Modes

| Mode | Focus | Budget | Time Window |
|------|-------|--------|-------------|
| breaking_news | Speed + Recency | $2 | 72 hours |
| investigation | Deep Verification | $15 | No limit |
| profile | Single Entity | $8 | No limit |
| controversy | Multiple Perspectives | $10 | No limit |

## Pipeline Stages

1. Initialize → 2. Planning (OpenAI) → 3. Research Mapping (Perplexity)
4. Source Discovery → 5. YouTube → 6. Transcripts (Supadata/Whisper)
7. Web Capture (Jina/Trafilatura) → 8. Reddit (PRAW)
9. Extraction (Claims/Timeline/Entities) → 10. Validation + Analysis
11. Drive Upload → Complete

## External Services

| Service | Purpose | Status | Notes |
|---------|---------|--------|-------|
| OpenAI GPT-4o-mini | Extraction | ✅ Keep | Fast, cheap |
| Gemini 2.5 Flash | Planning | ❌ Add | 1M context, thinking mode |
| Gemini 2.5 Pro | Vision, synthesis | ❌ Add | Multimodal-native |
| Perplexity | Speed search | ✅ Keep | 358ms |
| Exa | Semantic search | ❌ Add | 94.9% accuracy |
| Serper | Backup search | ❌ Add | $1/1k, 93.5% success |
| Tavily | RAG search | ⚠️ Demote | 10% 502 errors - fallback only |
| Supadata | Transcripts | ✅ Keep | Tier 1 |
| Jina Reader | Web capture | ✅ Keep | FREE |
| PRAW | Reddit API | ✅ Keep | Needs credentials |

## Environment Variables

Critical variables in `.env`:
- `REDIS_URL` - Required for Celery
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` - Job persistence
- `OPENAI_API_KEY` - Required for extraction
- `PERPLEXITY_API_KEY` - Required for research

Planned additions (research-validated):
- `GOOGLE_API_KEY` - For Gemini 2.5 Flash/Pro
- `EXA_API_KEY` - For semantic search (94.9% accuracy)
- `SERPER_API_KEY` - For backup search ($1/1k)

See `.env.example` for complete list.

## Common Patterns

**Adding an integration**:
1. Create client in `backend/integrations/`
2. Add config to `backend/config.py`
3. Use in pipeline stage with try/except
4. Add fallback if applicable

**Modifying pipeline**:
1. Add stage function in `backend/pipeline/stages.py`
2. Add context field in `backend/pipeline/context.py`
3. Register in worker stage list
4. Test with minimal job

## Important Notes

### Cloud Compatibility (Dec 2025)
- **youtube-transcript-api REMOVED** - fails on cloud IPs (Railway, AWS, GCP)
- **Transcription chain**: Supadata → Whisper (no youtube-transcript-api)
- YouTube Data API v3 (enumeration) works on cloud but requires API key

### Pipeline
- Quality Gate: Active with BM25 scoring
- Claim dedup: MinHash LSH (O(n) scaling)
- Always use `ctx.add_warning()` for non-fatal errors
- Follow YAGNI/KISS/DRY principles

## Implementation Priorities (Research-Validated)

**Tier 1 - Critical (Immediate)**:
1. Raise claim threshold: `score >= 4` (saves 30% LLM calls)
2. Activate Quality Gate in pipeline
3. Fix transcription order

**Tier 2 - API Stack Upgrades**:
1. Add Exa for semantic search (94.9% accuracy)
2. Add Gemini 2.5 Flash for planning
3. Add Gemini 2.5 Pro for vision/synthesis
4. Demote Tavily to fallback (10% 502 errors)

**Tier 3 - ML Optimizations**:
1. MinHash LSH for claim dedup (O(n) vs O(n²))
2. Add BM25 to Quality Gate scoring
3. Upgrade spaCy to en_core_web_trf (+6% F1)

## Research Reports

See `plans/reports/` for detailed analysis:
- `api-validation-*-best-stack-recommendations.md`
- `ml-vs-llm-analysis-*-traditional-ml-opportunities.md`
