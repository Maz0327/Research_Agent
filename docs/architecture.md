# System Architecture

**Last Updated:** December 2025
**Status:** Production + Research-Validated Optimizations Pending

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
- **Quality Gate** (`backend/pipeline/quality_gate.py`): Deterministic filtering
- **Entity Extraction** (`backend/pipeline/entities.py`): spaCy NER
- **Claim Candidates** (`backend/pipeline/extraction.py`): Regex heuristics

### Pending Optimizations

| Component | Current | Optimal | File |
|-----------|---------|---------|------|
| Claim Dedup | O(n²) Jaccard | MinHash LSH O(n) | `extraction.py` |
| Source Scoring | Domain-only | Add BM25 relevance | `quality_gate.py` |
| spaCy Model | en_core_web_sm | en_core_web_trf | `entities.py` |
| Claim Threshold | score >= 3 | score >= 4 | `extraction.py` |

## Key Files

- `backend/pipeline/stages.py` - Pipeline orchestration
- `backend/pipeline/context.py` - Shared pipeline state
- `backend/pipeline/quality_gate.py` - Deterministic source filtering (565 lines)
- `backend/pipeline/extraction.py` - Claim extraction with hybrid approach
- `backend/pipeline/entities.py` - spaCy-based entity extraction
- `backend/state/factory.py` - Job store abstraction
- `backend/models/job_config.py` - Mode configurations

## Data Flow

1. User submits research topic
2. API creates job in Supabase
3. Celery picks up task from Redis
4. Pipeline runs 11 stages
5. Results uploaded to Google Drive
6. Job marked complete

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
