# Phase 08: Source Discovery

## Context Links
- [Brainstorm -- Source Discovery](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#source-discovery--find-sources-for-me-phase-2)
- Existing search infrastructure: `backend/pipeline/search/`, `backend/app/routes/search_routes.py`

## Overview
- **Priority:** P3 (Phase 2 -- Growth)
- **Status:** pending
- **Effort:** 2 weeks
- **Depends on:** Phase 07 (Quick mode)
- **Description:** "Find sources for me" -- user enters topic, system suggests top YouTube videos + articles. User picks sources, then runs research. Closes the loop so creators never leave the tool.

## Key Insights
- Current input requires users to ALREADY have URLs. Most creators start with a topic.
- Without this, they still need Perplexity/YouTube search first.
- Search infrastructure partially exists: `search_routes.py`, `backend/pipeline/search/`
- Gemini Flash can generate search queries from a topic
- YouTube Data API v3 for video search, Google Custom Search or Brave for articles

## Requirements

### Functional
- New input mode: "Find Sources" -- user enters topic only
- System generates search queries and finds:
  - Top 5-10 YouTube videos (title, channel, duration, thumbnail)
  - Top 5-10 articles/web pages (title, domain, snippet)
- User selects which sources to include (checkbox)
- Selected sources feed into Quick or Full pipeline
- Relevance scoring: sources ranked by topic relevance
- Preview: show source titles + descriptions before committing

### Non-Functional
- Discovery results in < 10s
- Support at least YouTube + web results
- Graceful fallback if search API fails

## Architecture

### Discovery Flow
```
User enters topic
  -> Backend generates search queries (Gemini Flash)
  -> Parallel: YouTube Data API + Web Search API
  -> Rank results by relevance
  -> Return candidate list to frontend
  -> User selects sources
  -> Create job with selected URLs
```

### API Requirements
- YouTube Data API v3 (`search.list`) -- free quota: 10,000 units/day, search costs 100 units
- Web search: Brave Search API (free tier: 2,000/mo) or existing Exa integration
- Gemini Flash: generate 3-5 diverse search queries from topic

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/app/routes/search_routes.py` | Add/update source discovery endpoints |
| `backend/pipeline/search/` | Extend search pipeline for discovery use case |
| `frontend/components/dashboard/single-screen-input.tsx` | Add "Find Sources" button/mode |
| `frontend/store/jobs.ts` | Already has `SearchCandidate`, `SearchDiscoveryResponse` types |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/services/source_discovery.py` | Orchestrate search queries, aggregate results | ~120 |
| `frontend/components/dashboard/source-discovery-panel.tsx` | Source suggestion list with checkboxes | ~120 |
| `frontend/components/dashboard/source-discovery-card.tsx` | Individual suggested source card (thumbnail, title, stats) | ~60 |

### Check first
- `backend/pipeline/search/` -- what search infrastructure exists?
- `backend/app/routes/search_routes.py` -- existing search endpoints?
- YouTube Data API key in config?

## Implementation Steps

### Task 8.1: Audit existing search infrastructure
1. Read `backend/pipeline/search/` directory
2. Read `backend/app/routes/search_routes.py`
3. Check for YouTube Data API, Brave Search, Exa integration
4. Determine what can be reused vs what needs building

### Task 8.2: Create source discovery service
1. Create `backend/services/source_discovery.py`
2. `generate_search_queries(topic: str) -> list[str]`:
   - Gemini Flash call to generate 3-5 diverse search queries
   - E.g., topic "electric cars" -> ["electric car comparison 2026", "EV market analysis", "Tesla vs Rivian review"]
3. `search_youtube(queries: list[str], max_results: int = 10) -> list[SourceCandidate]`:
   - YouTube Data API v3 search.list
   - Return: title, channel, duration, thumbnail, URL, view count
4. `search_web(queries: list[str], max_results: int = 10) -> list[SourceCandidate]`:
   - Brave Search API or Exa
   - Return: title, domain, snippet, URL
5. `discover_sources(topic: str) -> DiscoveryResult`:
   - Call `generate_search_queries()`
   - Parallel: `search_youtube()` + `search_web()`
   - Deduplicate results
   - Rank by relevance (Gemini scoring or heuristic)

### Task 8.3: Create discovery API endpoint
1. In `backend/app/routes/search_routes.py`:
   - `POST /sources/discover` -- accepts `{ topic: str }`, returns `DiscoveryResult`
   - Rate limit: 5 requests/minute per user
   - Auth required

### Task 8.4: Create frontend discovery components
1. Create `frontend/components/dashboard/source-discovery-card.tsx`:
   - YouTube: thumbnail, title, channel name, duration, view count
   - Article: favicon, title, domain, snippet
   - Checkbox for selection
2. Create `frontend/components/dashboard/source-discovery-panel.tsx`:
   - Grid of `SourceDiscoveryCard` components
   - "Select All" / "Deselect All" buttons
   - "Add Selected to Research" button -> populates SingleScreenInput sources
   - Loading skeleton while searching
3. In `frontend/components/dashboard/single-screen-input.tsx`:
   - Add "Find Sources" button next to "Add YouTube/Article" buttons
   - Clicking opens `SourceDiscoveryPanel` in a dialog/drawer
   - Selected sources added as chips in main input

### Task 8.5: Test
1. Backend: unit test query generation with sample topics
2. Backend: integration test YouTube + web search (with API keys)
3. Manual: enter topic, verify relevant sources suggested
4. Manual: select sources, verify they populate input correctly
5. `pytest backend/tests/ -v` && `npm run build`

## Todo Checklist
- [ ] 8.1 Audit existing search infrastructure
- [ ] 8.2 Create `source_discovery.py` service
- [ ] 8.3 Create `POST /sources/discover` endpoint
- [ ] 8.4 Create frontend discovery components
- [ ] 8.5 Test: unit, integration, manual

## Success Criteria
- User enters topic, gets 10-20 relevant source suggestions in < 10s
- Mix of YouTube videos and articles
- Selected sources flow into job creation seamlessly
- Results are genuinely relevant to topic

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| YouTube API quota exhaustion | MEDIUM | 100 searches/day on free tier. Monitor usage. Upgrade if needed ($0). |
| Search results not relevant | MEDIUM | Gemini-generated queries improve relevance. Manual testing. |
| API costs for discovery | LOW | Gemini query generation: ~$0.002. YouTube/Brave search: free tier. |

## Security Considerations
- Rate limit discovery endpoint (prevent scraping)
- Validate topic string (max length, no injection)
- YouTube API key stored in env vars
