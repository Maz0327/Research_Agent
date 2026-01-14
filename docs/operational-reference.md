# Research Agent — Operational Reference

**Purpose:** Quick reference for development commands, API costs, technology stack, and operational details.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Celery, Redis, Python 3.11 |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS |
| **Database** | Supabase (PostgreSQL) |
| **LLM** | Gemini 2.5 Pro/Flash |
| **Search** | Perplexity, Exa, Serper |
| **Transcripts** | Supadata, Whisper |
| **Deployment** | Railway (backend), Vercel (frontend) |

---

## Development Commands

### Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Start API server
uvicorn backend.app.main:app --reload

# Start Celery worker
celery -A backend.worker worker --loglevel=INFO

# Run tests
pytest backend/tests/ -v

# Health check
curl http://localhost:8000/health
```

### Frontend

```bash
cd frontend

# Start dev server
npm run dev

# Build
npm run build

# Lint
npm run lint
```

### Pre-Commit Checks

```bash
# Must pass before committing
pytest backend/tests/
cd frontend && npm run lint && npm run build
```

---

## API Cost Reference

### LLM Costs (per 1M tokens)

| Model | Input | Output | Use Case |
|-------|-------|--------|----------|
| Gemini 2.5 Flash | $0.30 | $2.50 | Planning, quick tasks |
| Gemini 2.5 Pro | $1.25 | $10.00 | Extraction, synthesis |
| GPT-4o-mini | $0.15 | $0.60 | Fallback extraction |

### Search Costs

| Service | Cost | Use Case |
|---------|------|----------|
| Perplexity | ~$0.20/job | Speed search |
| Exa | ~$0.50/job | Semantic search |
| Serper | $1/1k queries | Backup search |

### Content Costs

| Service | Cost | Use Case |
|---------|------|----------|
| Supadata | ~$0.28/job | Transcripts |
| Jina Reader | FREE | Web capture |

### Monthly Budget (~$115-120 for 60 jobs)

- Search: ~$25 (Exa + Perplexity + Serper)
- LLM: ~$70 (Gemini + GPT-4o-mini)
- Content: ~$17 (Supadata)
- ML: $0 (local processing)

---

## Export Formats

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

**API:** `GET /jobs/{id}/export?format=brief&download=true`

---

## External Services

### Active Integrations

| Service | Client | Purpose | Status |
|---------|--------|---------|--------|
| Gemini 2.5 | gemini_client.py | LLM extraction/synthesis | ✅ Active |
| Supadata | supadata_client.py | YouTube transcripts | ✅ Active |
| YouTube Data API | youtube_client.py | Video metadata | ✅ Active |
| Perplexity | perplexity_client.py | Research search | ✅ Active |
| Jina Reader | jina_reader_client.py | Web capture (FREE) | ✅ Active |
| Google Drive | google_drive_docs.py | Export to Drive | ✅ Active |

### Available but Unused

| Service | Client | Purpose | Status |
|---------|--------|---------|--------|
| Exa | exa_client.py | Semantic search | Available |
| Serper | serper_client.py | Backup search | Available |
| OpenAI | openai_client.py | Fallback LLM | Available |
| Whisper | whisper_client.py | Audio transcription | Available |
| Reddit | reddit_client.py | Reddit search | Available |

### Archived (Not Used)

| Service | Reason |
|---------|--------|
| Brave Search | No imports |
| ClaimBuster | No imports |
| GDELT | No imports |
| Google Factcheck | No imports |
| Semantic Scholar | No imports |
| Tavily | 10% 502 error rate |

---

## Environment Variables

### Required

```env
REDIS_URL=redis://localhost:6379
GOOGLE_API_KEY=your-gemini-api-key
SUPADATA_API_KEY=your-supadata-key
```

### Required for Production

```env
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

### Optional Integrations

```env
OPENAI_API_KEY=optional
PERPLEXITY_API_KEY=optional
YOUTUBE_API_KEY=optional
EXA_API_KEY=optional
SERPER_API_KEY=optional
```

### Feature Flags

```env
ENABLE_QUALITY_GATE=true
ENABLE_NICHES=false
USE_SEMANTIC_PIPELINE=true
```

---

## Common Patterns

### Adding an Integration

1. Create client in `backend/integrations/`
2. Add config to `backend/config.py`
3. Use in pipeline stage with try/except
4. Add fallback if applicable

### Modifying Pipeline

1. Add stage function in `backend/pipeline/stages/`
2. Add context field in `backend/pipeline/context.py`
3. Export from `stages/__init__.py`
4. Register in worker
5. Test with minimal job

### Error Handling

```python
try:
    result = external_api_call()
except ExternalAPIError as e:
    logger.error(f"API call failed: {e}")
    ctx.add_warning(f"Degraded: {e}")
    # Continue with fallback or degraded output
```

---

## Cloud Compatibility Notes

### YouTube Transcript API

- **youtube-transcript-api REMOVED** — fails on cloud IPs (Railway, AWS, GCP)
- **Transcription chain:** Supadata → Whisper → YouTube captions → video_only
- YouTube Data API v3 works on cloud (requires API key)

### Rate Limiting

- Gemini: 500ms delay between calls
- YouTube: Rate limited by API quota
- Perplexity: Built-in rate limiting

---

## Quality Gate

Active with the following scoring:

- BM25 blended into relevance (60% weight)
- Mode-specific recency scoring (10% weight)
- Niche priority keywords (+0.1 bonus)
- Niche preferred domains (+0.15 bonus)
- Shannon entropy diversity metric

---

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `jobs` | Job records and status |
| `user_settings` | User preferences |
| `admin_users` | Admin role tracking |
| `error_logs` | Error tracking |

### Jobs Table Key Fields

- `status`: queued, running, completed, failed, cancelled
- `stage`: Current pipeline stage
- `artifacts`: JSONB with clips, quotes, documents
- `outputs`: JSONB with markdown outputs

---

## Deployment

### Railway (Backend)

- Auto-deploys from main branch
- Environment variables in Railway dashboard
- Redis addon for Celery

### Vercel (Frontend)

- Auto-deploys from main branch
- Environment variables in Vercel dashboard
- API URL configured for Railway backend

---

**For implementation instructions, see CLAUDE.md**
**For system specification, see docs/authoritative/spec/RASS.md**
