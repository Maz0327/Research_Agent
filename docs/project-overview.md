# Research Agent - Project Overview

## What is Research Agent?

Research Agent is an AI-powered documentary research assistant that replaces human researchers for content creators. It aggregates and analyzes content from multiple sources (Reddit, YouTube, web articles, etc.) and produces two outputs:

1. **NotebookLM Packet** - Optimized for AI podcast generation
2. **Documentary Blueprint** - Optimized for video production

## Production Status

- **Backend**: Railway (FastAPI + Celery + Redis)
- **Frontend**: Vercel (Next.js)
- **Database**: Supabase (PostgreSQL)
- **Status**: LIVE

| Service | URL |
|---------|-----|
| Frontend | https://research-agent-kohl.vercel.app |
| API | https://api-production-1c52.up.railway.app |

## Technology Stack

### Backend
- FastAPI (REST API)
- Celery (async task processing)
- Redis (message broker)
- Supabase (job persistence)
- OpenAI GPT-4o-mini (LLM)
- Perplexity (research mapping)
- Tavily (web search)

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS
- Zustand (state)

## Research Modes

| Mode | Focus | Budget |
|------|-------|--------|
| quick | Fast, surface-level | $1 |
| breaking_news | Recent events (72hr) | $2 |
| full | Balanced coverage | $5 |
| investigation | Deep verification | $15 |
| profile | Single entity | $8 |

## Category/Niche System

Users can select a category to guide source selection:

| Category | Description | Source Priority |
|----------|-------------|-----------------|
| Auto-detect | AI determines category | Balanced |
| Pop Culture | TV, movies, celebrities | Video, Discussion |
| Political | Government, policy | News, Academic |
| True Crime | Cases, investigations | News, Video |
| Mysteries | Theories, conspiracies | Video, Academic |
| Downfalls | Scandals, drama | News, Discussion |
| Controversy | Multiple perspectives | Discussion, News |

Each category affects:
- Which subreddits to search
- Source type minimums (more video vs more news)
- Search query expansions
- Priority keywords for relevance scoring

## Pipeline Overview

```
Planning → Discovery → Collection → Extraction → Synthesis → Output
```

11 stages total, with graceful degradation for failures.

## UI Features (Dec 2025)

- **Research Depth Dropdown**: Select research thoroughness
- **Category Dropdown**: Guide source selection by topic type
- **Topic Disambiguation**: Ambiguous topics pause for user clarification
- **Numbered Folders**: Multiple interpretations get numbered Drive folders
