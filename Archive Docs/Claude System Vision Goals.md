# Research Agent: Project Vision & Architecture

## What We're Building (REVISED - Hybrid Approach)

A **dual-purpose research and documentary intelligence system** that both gathers comprehensive research for NotebookLM analysis AND transforms it into production-ready documentary blueprints. The system discovers unique angles on well-covered topics, helping create differentiated documentary content. The user triggers a job (via Slack or web UI), the system gathers comprehensive research, discovers unique perspectives, and outputs BOTH a NotebookLM packet AND a documentary blueprint.

---

## The Core Problem

The user creates YouTube mini-documentaries and livestreams covering news, politics, pop culture, and investigative topics. They need:

1. **Deep research** across YouTube videos, transcripts, Reddit threads, tweets, news articles, government docs
2. **Structured organization** — timelines, entities, claims with attribution
3. **Validation** — cross-referencing claims against other sources
4. **Unique angles** — discovering perspectives that haven't been covered (e.g., legal battles vs crimes)
5. **Dual outputs:**
   - **NotebookLM packet** — comprehensive research for deep analysis
   - **Documentary blueprint** — production-ready narrative with script outline, B-roll list, interview questions

Previous attempts using Make.com + Gemini + manual workflows broke down due to complexity, API chaining fragility, and AI "drift."

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Slack     │────▶│  FastAPI    │────▶│   Redis     │────▶│   Celery    │
│  Trigger    │     │  (Web API)  │     │   Queue     │     │   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                    ┌──────────────────────────────────────────────┘
                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                     RESEARCH PIPELINE                          │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
    │  │ YouTube  │  │   Web    │  │  Public  │  │Secondary │       │
    │  │Collector │  │Collector │  │  Docs    │  │ Sources  │       │
    │  │(transcr.)│  │(Perplx.) │  │(.gov)    │  │(guidance)│       │
    │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
    │       └──────────────┴──────────────┴──────────────┘           │
    │                          ▼                                     │
    │  ┌──────────────────────────────────────────────────────────┐ │
    │  │              EXTRACTION & STRUCTURING                     │ │
    │  │  • Entity Extraction (people, orgs, aliases)              │ │
    │  │  • Timeline Builder (events + dates + attribution)        │ │
    │  │  • Claims Extraction (claim + speaker + source)           │ │
    │  │  • Angle Discovery (unique perspectives & gaps)           │ │
    │  └──────────────────────────────────────────────────────────┘ │
    │                          ▼                                     │
    │  ┌──────────────────────────────────────────────────────────┐ │
    │  │              VALIDATION LAYER                             │ │
    │  │  • Generate validation queries from claims                │ │
    │  │  • Cross-reference via Perplexity                         │ │
    │  │  • Map: corroborating / contradicting / unclear           │ │
    │  └──────────────────────────────────────────────────────────┘ │
    └───────────────────────────────────────────────────────────────┘
                          ▼
    ┌──────────────────────────────────────────────────────────────┐
    │              DOCUMENTARY INTELLIGENCE LAYER                    │
    │  • Narrative Structure Detection (3-act structure)            │
    │  • Visual Moment Identification (B-roll opportunities)        │
    │  • Conflict Mapping (opposing viewpoints)                     │
    │  • Production Planning (interviews, graphics, runtime)        │
    └──────────────────────────────────────────────────────────────┘
                          ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                    DUAL OUTPUT SYSTEM                          │
    │  • NotebookLM Packet (comprehensive research)                 │
    │  • Documentary Blueprint (production-ready)                   │
    │  • Discovered Angles (unique perspectives)                    │
    │  • Saved to Supabase + Google Drive                          │
    │  • Links sent back to Slack/Web UI                           │
    └──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| API Server | FastAPI | HTTP endpoints, job creation, Slack webhooks |
| Task Queue | Redis + Celery | Async job processing (research takes 5-30 min) |
| Database | Supabase (PostgreSQL) | Job state, packets, artifacts (JSONB) |
| File Storage | Google Drive | Final research packets, docs |
| YouTube | YouTube Data API + youtube-transcript-api | Video search + transcript fetching |
| Web Search | Perplexity API | Deep web research with citations |
| LLM | OpenAI/Anthropic API | Entity extraction, claims parsing, validation queries |
| Trigger | Slack (slash commands or events API) | User-facing job initiation |
| Deployment | Render (web + worker) + Upstash Redis | Production hosting |

---

## Data Models

### Job
```python
{
    "id": "uuid",
    "topic": "Candace Owens Charlie Kirk controversy",
    "status": "pending | running | completed | failed",
    "config": {  # JSONB - stored per-job for reproducibility
        "research_mode": "investigation",  # quick | standard | deep | investigation
        "sources": {
            "youtube": {"enabled": True, "mode": "search", "max_results": 10},
            "web": {"enabled": True, "depth": "standard"},
            "public_docs": {"enabled": False},
            "secondary": {"mode": "guidance"}  # guidance | auto_if_possible
        },
        "validation_enabled": True,
        "max_validation_queries": 10
    },
    "progress": {"step": "collecting_youtube", "percent": 25},
    "created_at": "timestamp",
    "completed_at": "timestamp",
    "artifacts": {
        "packet_url": "https://drive.google.com/...",
        "folder_url": "https://drive.google.com/..."
    }
}
```

### ResearchPacket (Output 1 - NotebookLM)
```python
{
    "topic": "string",
    "summary_index": [...],  # Table of contents
    "entities": {
        "people": [{"name": "...", "aliases": [...], "role": "..."}],
        "organizations": [...],
        "places": [...],
        "key_terms": [...]
    },
    "timeline": [
        {"date": "2024-01-15", "event": "...", "who_said_it": "...", "source_url": "..."}
    ],
    "claims": [
        {
            "claim_text": "...",
            "speaker": "Candace Owens",
            "confidence": "high",
            "source_url": "...",
            "supporting_quote": "..."
        }
    ],
    "sources": [  # Deduplicated
        {"url": "...", "title": "...", "type": "youtube|article|reddit", "content": "..."}
    ],
    "validation_results": {
        "claim_id": {
            "corroborating": [...],
            "contradicting": [...],
            "unclear": [...]
        }
    },
    "manual_guidance": {  # For Reddit/X/TikTok when auto-scraping unreliable
        "reddit": ["Search: 'Candace Owens evidence' sort by new..."],
        "twitter": ["Search: from:CandaceOwens since:2024-01-01..."]
    }
}
```

### DocumentaryBlueprint (Output 2 - Production)
```python
{
    "topic": "string",
    "recommended_angle": {
        "title": "The Legal Chess Match",
        "description": "Focus on legal maneuvering rather than crime details",
        "uniqueness_score": 0.92
    },
    "discovered_angles": [  # Alternative angles
        {
            "angle_type": "untold_perspective|process_focus|temporal_shift",
            "title": "...",
            "key_sources_needed": [...],
            "production_notes": "..."
        }
    ],
    "narrative_structure": {
        "opening_hook": "Most compelling moment",
        "act_1_setup": {...},
        "act_2_investigation": {...},
        "act_3_resolution": {...}
    },
    "production_elements": {
        "interview_list": [...],
        "b_roll_moments": [...],
        "graphics_needed": [...],
        "estimated_runtime": "15-20 minutes"
    },
    "coverage_analysis": {
        "heavily_covered": ["crime details", "victim stories"],
        "rarely_covered": ["legal strategies", "jury perspectives"],
        "not_covered": ["economic impact", "systemic issues"]
    }
}
```

---

## Research Modes (REVISED - Documentary-Specific)

| Mode | Description | Focus | Angle Discovery | Max Time/Cost |
|------|-------------|-------|-----------------|---------------|
| `breaking_news` | Rapid response | Speed & recency | Quick gaps | 10min/$2 |
| `investigation` | Deep dive | Verification & connections | Full analysis | 45min/$15 |
| `profile` | Person/org focus | Single entity | Perspective mapping | 30min/$8 |
| `controversy` | Balanced coverage | All viewpoints | Conflict scoring | 30min/$10 |

---

## Key Design Principles

### 1. **Organize, Don't Analyze**
The system structures raw information — it does NOT draw conclusions. Gemini/LLMs are used for formatting and extraction, not opinion or synthesis. The user makes judgments in NotebookLM.

### 2. **Stability Over Features**
Reddit/X/TikTok scrapers are fragile. Default to "manual guidance" (search phrases, keywords to look for) rather than brittle automation. Add auto-scraping only when proven reliable.

### 3. **Per-Job Config**
Every job stores its full config in JSONB. This enables reproducible runs and different strategies without schema changes.

### 4. **Validation ≠ Truth-Finding**
Validation maps evidence to claims (corroborating/contradicting/unclear). It does NOT declare what's true. The user interprets.

### 5. **Progressive Enhancement**
Build in phases. Start simple (YouTube search + Perplexity + basic packet), then add transcript fetching, entity extraction, validation, etc.

---

## Build Phases

### Phase 0: Stabilize Foundation
- [x] Consolidate config.py / settings.py
- [x] Fix URL typing issues
- [ ] Remove unused Supabase client dependency
- [ ] Add proper secret management (.env)

### Phase 1: Job Config System
- [ ] Add `config` JSONB column to jobs table
- [ ] Create JobConfig Pydantic model with validation
- [ ] Store config on job creation

### Phase 2: Collectors (Build as functions, NOT full plugin system yet)
- [ ] **YouTube Collector** (`backend/collectors/youtube.py`)
  - Search mode: YouTube API → video URLs
  - Transcript fetch: youtube-transcript-api (free) → full text
  - Channel mode: last N videos from specific channel
- [ ] **Web Collector** (`backend/collectors/web.py`)
  - Perplexity API → sources + snippets
  - Optional: Playwright content extraction for top K URLs
- [ ] **Public Docs Collector** (`backend/collectors/public_docs.py`)
  - Perplexity with domain hints (site:.gov)
  - Return links + extracted text

### Phase 3: Extraction & Structuring
- [ ] **Entity Extraction** (`backend/extractors/entities.py`)
  - Start with regex/NER, add LLM later
  - Output: people, orgs, places, aliases
- [ ] **Timeline Builder** (`backend/extractors/timeline.py`)
  - Explicit dates first (from metadata)
  - Add LLM extraction for implicit dates later
- [ ] **Claims Extraction** (`backend/extractors/claims.py`)
  - LLM-powered, use structured outputs (JSON mode)
  - Batch process, cache results
- [ ] **Angle Discovery** (`backend/pipeline/angle_discovery.py`)
  - Analyze existing coverage patterns
  - Identify gaps and unique perspectives
  - Score angles by uniqueness & feasibility

### Phase 4: Validation Layer
- [ ] **Query Builder** (`backend/validation/query_builder.py`)
  - Generate targeted queries from claims/entities
  - Budget limit (max 5-10 queries per job)
- [ ] **Validator** (`backend/validation/validator.py`)
  - Perplexity search per query
  - Map results to claims: corroborating/contradicting/unclear

### Phase 5: Documentary Intelligence
- [ ] **Documentary Analysis** (`backend/pipeline/documentary_intelligence.py`)
  - Narrative structure detection
  - Visual moment identification
  - Conflict mapping
  - Production planning

### Phase 6: Dual Output System
- [ ] **NotebookLM Packet** (`backend/exporters/notebooklm.py`)
  - Comprehensive research compilation
  - Clean headings, bullets, citations
  - NotebookLM-optimized format
- [ ] **Documentary Blueprint** (`backend/exporters/documentary.py`)
  - Three-act structure with hooks
  - B-roll list with timestamps
  - Interview questions & production notes
  - Discovered angles with uniqueness scores

### Phase 7: Secondary Sources (Guidance-First)
- [ ] Default: produce search phrases + what to look for
- [ ] Auto-if-possible: include public Reddit/X from Perplexity results
- [ ] Reddit integration with user's API key

### Phase 8: Frontend (After backend works)
- [ ] Job creation UI with documentary mode presets
- [ ] Status polling + progress display
- [ ] Dual output download (packet + blueprint)
- [ ] Angle selection interface

### Phase 9: Deployment
- [ ] Render: FastAPI web service + Celery worker
- [ ] Upstash: Managed Redis
- [ ] Supabase: Production DB with correct schema
- [ ] Slack: Slash command integration

---

## Critical Technical Notes

### Rate Limits & Costs
- YouTube API: 10k quota/day
- Perplexity: ~$0.20-1.00 per query
- LLM APIs: ~$0.50-5.00 per job (depending on depth)
- Google Drive: Strict rate limits, use concurrency=1

### Error Handling
- Celery workers can crash mid-job → need heartbeat + recovery
- Some videos lack transcripts → graceful fallback
- Empty Perplexity results → don't crash pipeline

### Concurrency
- Start with `concurrency=1` for Celery worker
- Drive API throttles aggressively on parallel writes

### Progress Tracking
- Jobs can take 5-30 minutes
- Update `progress` field: `{"step": "extracting_entities", "percent": 65}`
- Slack/UI should poll status

---

## File Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── jobs.py          # Job CRUD endpoints
│   │   └── slack.py         # Slack webhook handlers
│   └── models/
│       ├── job.py           # Job Pydantic models
│       ├── packet.py        # ResearchPacket model
│       └── blueprint.py     # DocumentaryBlueprint model
├── collectors/
│   ├── youtube.py
│   ├── web.py
│   ├── reddit.py           # Reddit API integration
│   └── public_docs.py
├── extractors/
│   ├── entities.py
│   ├── timeline.py
│   └── claims.py
├── pipeline/
│   ├── angle_discovery.py  # Find unique perspectives
│   └── documentary_intelligence.py  # Documentary analysis
├── validation/
│   ├── query_builder.py
│   └── validator.py
├── exporters/
│   ├── notebooklm.py       # NotebookLM packet
│   └── documentary.py      # Documentary blueprint
├── integrations/
│   ├── reddit_client.py    # Reddit API client
│   └── perplexity_client.py
├── worker/
│   ├── celery_app.py        # Celery configuration
│   └── tasks.py             # Research pipeline task
└── config.py                # Centralized settings
```

---

## Example Slack Workflow

1. User: `/research Candace Owens Charlie Kirk controversy`
2. Slack handler:
   - Immediately ack (within 3 seconds)
   - Create job in Supabase
   - Enqueue to Celery
   - Reply: "🔍 Research job started. Job ID: abc123"
3. Celery worker:
   - Run collectors (YouTube → Web → etc.)
   - Run extractors (entities → timeline → claims)
   - Run validation
   - Build packet
   - Upload to Drive
   - Update job status + artifacts
4. Slack notification: "✅ Research complete! [View Packet](drive.google.com/...)"

---

## What This System is NOT

- ❌ An opinion generator — it organizes, doesn't conclude
- ❌ A real-time scraper — jobs take minutes, not seconds
- ❌ A replacement for NotebookLM — it prepares input for NotebookLM
- ❌ A brittle Make.com workflow — it's a resilient Python pipeline
- ❌ Fully automated social media scraping — secondary sources default to guidance

---

## Success Criteria (REVISED - Hybrid System)

1. User can trigger `/research [topic] [mode]` from Slack or Web UI
2. System creates job with documentary-specific mode (investigation/profile/controversy/breaking_news)
3. Discovers unique angles by analyzing coverage gaps
4. Outputs TWO deliverables:
   - **NotebookLM Packet:** Comprehensive research with timeline, entities, claims, validation
   - **Documentary Blueprint:** Three-act structure, discovered angles, B-roll list, interview questions
5. Both outputs upload to Google Drive
6. User receives links to both deliverables
7. User can:
   - Upload packet to NotebookLM for deep analysis
   - Use blueprint to produce differentiated documentary content
   - Select from discovered angles for unique perspective

---

## Commands for Claude Code

When working on this project:

```bash
# Start local development
cd /path/to/research-agent
redis-server &
celery -A backend.worker.celery_app worker --loglevel=INFO --concurrency=1 &
uvicorn backend.app.main:app --reload

# Test a job manually
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"topic": "test topic", "config": {"research_mode": "quick"}}'

# Check job status
curl http://localhost:8000/jobs/{job_id}
```

---

*This document represents the consolidated vision from multiple planning sessions. Start with Phase 0/1, validate the foundation, then build collectors incrementally.*
