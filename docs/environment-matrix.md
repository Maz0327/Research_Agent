# Environment Variables Matrix

Documents which environment variables are required for each feature.

## Core Infrastructure

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | Yes* | Celery message broker (e.g., `redis://localhost:6379/0`) |
| `SUPABASE_URL` | Yes* | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes* | Supabase service role key (backend only) |
| `SUPABASE_JWT_SECRET` | Yes* | JWT secret for auth validation |
| `FRONTEND_ORIGINS` | Yes | Allowed CORS origins (comma-separated) |

*Required for production. In-memory mode works without Supabase for local development.

## LLM APIs

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | Claim extraction | GPT-4o-mini for canonicalization |
| `PERPLEXITY_API_KEY` | Research mapping | Perplexity search API |
| `GOOGLE_API_KEY` | Gemini models (planned) | For planning and synthesis |

## Search APIs

| Variable | Required For | Description |
|----------|-------------|-------------|
| `PERPLEXITY_API_KEY` | Web search | Primary search provider |
| `EXA_API_KEY` | Semantic search (planned) | High-accuracy entity search |
| `SERPER_API_KEY` | Fallback search (planned) | Backup when others fail |
| `TAVILY_API_KEY` | RAG search | Demoted to fallback (10% 502 rate) |

## Content Sources

| Variable | Required For | Description |
|----------|-------------|-------------|
| `SUPADATA_API_KEY` | YouTube transcripts | Primary transcript provider |
| `YOUTUBE_API_KEY` | Video enumeration | YouTube Data API v3 |
| `REDDIT_CLIENT_ID` | Reddit posts | PRAW OAuth |
| `REDDIT_CLIENT_SECRET` | Reddit posts | PRAW OAuth |
| `REDDIT_USER_AGENT` | Reddit posts | PRAW identification |
| `JINA_API_KEY` | Web capture (optional) | Jina Reader (often FREE tier) |

## External Services

| Variable | Required For | Description |
|----------|-------------|-------------|
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Drive upload | Base64-encoded service account JSON |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive upload | Parent folder for job outputs |
| `SLACK_WEBHOOK_URL` | Notifications (optional) | Slack channel webhook |

## Feature Requirements Matrix

| Feature | Required Variables |
|---------|-------------------|
| Run API locally | None (in-memory mode) |
| Run API with persistence | `SUPABASE_*`, `REDIS_URL` |
| Claim extraction | `OPENAI_API_KEY` |
| Research mapping | `PERPLEXITY_API_KEY` |
| YouTube transcripts | `SUPADATA_API_KEY` |
| YouTube enumeration | `YOUTUBE_API_KEY` |
| Reddit collection | `REDDIT_*` (all three) |
| Drive upload | `GOOGLE_SERVICE_ACCOUNT_KEY`, `GOOGLE_DRIVE_FOLDER_ID` |
| Admin dashboard | `SUPABASE_*` |

## Minimal Development Setup

```bash
# .env.local for basic local development
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
```

## Production Setup

```bash
# All required for production
REDIS_URL=redis://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
FRONTEND_ORIGINS=https://your-frontend.vercel.app

# LLM
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...

# Content
SUPADATA_API_KEY=...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=ResearchAgent/1.0

# Output
GOOGLE_SERVICE_ACCOUNT_KEY=base64...
GOOGLE_DRIVE_FOLDER_ID=...
```

## Notes

- Missing optional keys result in graceful degradation, not crashes
- Startup logs which services are configured/unavailable
- Health endpoint (`/health`) shows dependency status
