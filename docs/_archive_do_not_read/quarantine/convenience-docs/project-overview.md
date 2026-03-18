# Research Agent - Project Overview

## What is Research Agent?

Research Agent is an AI-powered documentary research assistant that replaces human researchers for content creators. It aggregates and analyzes content from multiple sources (Reddit, YouTube, web articles, etc.) and produces:

1. **NotebookLM Packet** - Optimized for AI podcast generation
2. **Documentary Blueprint** - Optimized for video production
3. **Research Brief** - Human-readable analysis document (Jan 2026)
4. **Export Formats** - JSON, BibTeX, chapters, clips, social kit

## Production Status

- **Backend**: Railway (FastAPI + Celery + Redis)
- **Frontend**: Vercel (Next.js)
- **Database**: Supabase (PostgreSQL)
- **Status**: LIVE

| Service | URL |
|---------|-----|
| Frontend | https://your-frontend.vercel.app |
| API | https://your-api.up.railway.app |

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

### Job Creation
- **Research Depth Dropdown**: Select research thoroughness (quick → investigation)
- **Category Dropdown**: Guide source selection by topic type
- **Two-Step Preview Flow**: See interpreted plan before running
- **Editable Sources**: Toggle source types on/off in preview
- **Custom Subreddits**: Add or remove subreddits before confirmation

### Job Management
- **Delete Button**: Remove completed/failed jobs (with confirmation)
- **Archive Button**: Hide jobs without permanent deletion
- **Cancel Button**: Stop running/queued jobs
- **Topic Disambiguation**: Ambiguous topics pause for user clarification

### Layout & Navigation
- **Collapsible Sidebar**: Toggle between full and icon-only modes
- **Mobile-First Design**: Hamburger menu with slide-in navigation
- **Responsive Breakpoints**: Optimized for phone, tablet, desktop
- **Skip Links**: WCAG 2.1 AA accessibility compliance

### Results
- **View Results Link**: Direct link to Google Drive folder
- **Numbered Folders**: Multiple interpretations get numbered Drive folders
- **Progress Tracking**: Real-time stage updates with ETA

## Features (Jan 2026)

### Export Format Stack
- **Research Brief**: LLM-generated 2-5 page analysis with claims matrix, evidence levels
- **Citation Exports**: BibTeX, RIS for academic use
- **Chapter Markers**: YouTube timestamps, Podcast Chapters JSON
- **Clip Suggestions**: Short-form video ideas from research
- **Social Kit**: Pre-written social media content

### Reliability Improvements
- Rate limiter keys by user_id (not just IP)
- Job cancellation works reliably (Celery task_id = job_id)
- Validation errors return 422 (not 400)
- Frontend/backend prompt limits aligned (2000 chars)
