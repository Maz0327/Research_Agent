# Product Requirements Document (PRD) v3.0
## Research Agent - Documentary Research Intelligence System

### Document Purpose
This PRD defines the requirements for Research Agent v3, incorporating lessons learned from v1 and v2 deployments. It prioritizes **cost efficiency**, **reliability**, and **speed** while maintaining comprehensive documentary research capabilities.

**CRITICAL FOR AI AGENTS:** This document supersedes PRD_v1.md and PRD_v2.md. Follow v3 specifications exactly.

---

## Section 0: Critical Instructions for AI Agents

### 0.1 Mission Statement
Research Agent is a documentary research intelligence system that gathers comprehensive research from multiple sources, validates claims, and transforms raw research into production-ready documentary blueprints.

### 0.2 The Three Guarantees
| Guarantee | Description |
|-----------|-------------|
| **EXHAUSTIVE** | Every research mode MUST search all configured sources. Never skip sources to "optimize". Documentary work cannot afford to miss the one source with the key revelation. |
| **STRUCTURED** | Every job MUST produce the guaranteed output schema. Partial results are acceptable, empty fields are not. User must always receive `claims[]`, `quotes[]`, `sources[]`, `timeline[]`. |
| **RESILIENT** | The pipeline MUST NOT fail silently. Every stage has retry logic, fallbacks, and checkpoints. User always gets SOMETHING, even if degraded. |

### 0.3 What We Are NOT Building
- NOT a real-time search engine (we do batch research jobs)
- NOT a social media monitoring tool (we analyze, not monitor)
- NOT a content generation platform (we research, not create)
- NOT a simple Q&A system (we produce structured documentary intelligence)

### 0.4 Locked Technology Stack

**DO NOT DEVIATE** - These technology choices are FINAL.

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend Framework | FastAPI | REST API, async support |
| Task Queue | Celery + Redis | Background job processing |
| Database | Supabase (PostgreSQL) | Job persistence, user data, RLS |
| Primary Search | Tavily | $0.01/search, AI-native |
| Content Extraction | Jina Reader | FREE (200 req/day), fast, clean markdown |
| News Discovery | GDELT | FREE, global news, 100K+ articles/day |
| Academic Search | Semantic Scholar | FREE, 200M papers |
| Video Discovery | YouTube Data API | FREE tier sufficient |
| Transcripts | youtube-transcript-api | FREE, Whisper fallback |
| Reddit | PRAW | FREE, firsthand accounts |
| LLM (Complex) | GPT-4o | Planning, synthesis, documentary |
| LLM (Simple) | GPT-4o-mini | Query generation, extraction |
| Export | Google Drive API | Docs, Sheets output |
| Frontend | Next.js 14 | Dashboard, job management |

### 0.5 Tools Changed from v2

| Tool | v2 Status | v3 Status | Reason |
|------|-----------|-----------|--------|
| Exa.ai | Primary search | REMOVED | Tavily is cheaper and more reliable |
| Perplexity | Validation only | REMOVED | GPT-4o handles validation adequately |
| Playwright | Fallback extraction | REMOVED | Too slow, brittle, high memory |
| ClaimBuster | Claim detection | REMOVED | Unnecessary complexity |
| Brave Search | Backup search | FALLBACK only | Tavily primary is sufficient |
| Wayback Machine | Listed but undefined | REMOVED | Not implemented, unclear value |
| LinkedIn | Profile mode | REMOVED | Legally risky, difficult access |

---

## Section 1: Product Overview

### 1.1 Problem Statement
Documentary filmmakers and investigative journalists spend 60-70% of their pre-production time on manual research tasks: finding sources, extracting content, verifying claims, and organizing findings into usable formats.

### 1.2 Solution
Research Agent automates the entire documentary research workflow:
1. Takes a research topic and mode selection
2. Searches multiple source types (web, news, video, academic, social)
3. Extracts and processes content from all sources
4. Synthesizes claims, quotes, timeline, and entities
5. Generates mode-specific Documentary Intelligence output
6. Exports to Google Drive and/or downloadable formats

### 1.3 Target Users
- Documentary filmmakers (primary)
- Investigative journalists
- Podcast producers researching episodes
- YouTube creators doing deep-dive content
- Research teams at media organizations

### 1.4 Value Proposition
**From research topic to production-ready documentary blueprint in 5-15 minutes, at $0.10-0.60 per job, with comprehensive source coverage and structured output.**

### 1.5 Success Metrics

| Metric | v2 Actual | v3 Target |
|--------|-----------|-----------|
| Job completion rate | ~70% | >95% |
| Average cost per job | $5-8 | $0.10-0.60 |
| Average duration | 15-25 min | 5-15 min |
| Sources per job | 20-30 | 30-50 |
| Claims extracted | 10-20 | 20-40 |

---

## Section 2: Research Modes

**CRITICAL:** Each mode is a DIFFERENT RECIPE, not just different portions. Modes have different stage behaviors, different tool priorities, different output formats. Do NOT combine modes or treat them as budget tiers.

### 2.1 Mode Overview

| Mode | Purpose | Duration | Cost |
|------|---------|----------|------|
| Quick | Fast answer, basic research | 2-3 min | $0.07-0.10 |
| Full | Comprehensive research | 8-12 min | $0.25-0.35 |
| Breaking News | Current events, last 72 hours | 2-4 min | $0.07-0.10 |
| Investigation | Deep dive, full documentary | 15-25 min | $0.50-0.80 |
| Profile | Person-focused research | 10-15 min | $0.25-0.40 |
| Controversy | Multi-perspective analysis | 10-15 min | $0.25-0.40 |

### 2.2 Quick Mode
**Purpose:** Fast answer with basic research coverage. Not for production use—for initial exploration and feasibility assessment.

**Configuration:**
| Parameter | Value |
|-----------|-------|
| Tavily searches | 5 |
| Include YouTube | NO |
| Include Academic | NO |
| Include News (GDELT) | Only if topic appears current |
| Include Reddit | NO |
| Max sources to extract | 10 |
| Extraction depth | Summary only |
| Claim validation | None |
| Timeout | 5 minutes |
| Max cost | $0.15 |

**Output: Research Brief**
```json
{
  "executive_summary": "string (3-5 sentences)",
  "key_findings": [
    { "finding": "string", "source_url": "string" }
  ],
  "notable_quotes": [
    { "text": "string", "speaker": "string?", "source_url": "string" }
  ],
  "sources": [ ... ],
  "further_research_suggested": [ "string" ]
}
```

### 2.3 Full Mode
**Purpose:** Comprehensive research across all source types. The standard research mode for most documentary projects.

**Configuration:**
| Parameter | Value |
|-----------|-------|
| Tavily searches | 15 |
| Include YouTube | YES (5-10 videos) |
| Include Academic | YES (if topic is technical) |
| Include News (GDELT) | YES (last 30 days) |
| Include Reddit | YES (3-5 threads) |
| Max sources to extract | 50 |
| Extraction depth | Full content |
| Claim validation | Cross-reference |
| Timeout | 15 minutes |
| Max cost | $0.50 |

**Output: Research Packet**
```json
{
  "executive_summary": "string",
  "background": "string (context and history)",
  "key_findings": [ ... ],
  "claims_analysis": {
    "verified_claims": [ ... ],
    "disputed_claims": [ ... ],
    "unverified_claims": [ ... ]
  },
  "timeline": [ { "date": "string", "event": "string", "source_url": "string" } ],
  "key_players": [ { "name": "string", "role": "string", "relevance": "string" } ],
  "quotes_bank": [ ... ],
  "source_evaluation": "string (which sources are strongest)",
  "gaps_and_limitations": [ "string" ]
}
```

### 2.4 Breaking News Mode
**Purpose:** Fast-turnaround research on current events. Prioritizes recency over depth.

**IMPORTANT:** Breaking News mode uses GDELT as primary source, NOT Tavily. GDELT has better real-time news coverage.

**Configuration:**
| Parameter | Value |
|-----------|-------|
| Primary source | GDELT (not Tavily) |
| Tavily searches | 5 (news filter only) |
| Time window | Last 48-72 hours |
| Include YouTube | NO (too slow to be current) |
| Include Academic | NO |
| Include Reddit | YES (real-time reactions) |
| Max sources to extract | 20 |
| Flag developing story | YES |
| Timeout | 5 minutes |
| Max cost | $0.15 |

**Output: Situation Report**
```json
{
  "headline": "string (one-line summary)",
  "status": "Developing | Confirmed | Breaking",
  "last_updated": "ISO timestamp",
  "what_we_know": [
    { "fact": "string", "source_url": "string", "confirmed_by": "int" }
  ],
  "what_we_dont_know": [ "string (open questions)" ],
  "key_players": [ ... ],
  "timeline_of_events": [ ... ],
  "conflicting_reports": [
    { "claim": "string", "source_a": "string", "source_b": "string" }
  ],
  "sources_summary": "string",
  "next_expected_updates": [ "string" ]
}
```

### 2.5 Investigation Mode
**Purpose:** Deep-dive investigative research for feature-length documentaries. Maximum depth, all sources, full validation. This is the flagship mode.

**Configuration:**
| Parameter | Value |
|-----------|-------|
| Tavily searches | 25 |
| Include YouTube | YES (10-20 videos) |
| Include Academic | YES |
| Include News (GDELT) | YES (full timeline) |
| Include Reddit | YES (10+ threads, firsthand accounts) |
| Max sources to extract | 100 |
| Extraction depth | Full content |
| Claim validation | Rigorous (cross-reference all) |
| Build entity graph | YES |
| Build timeline | YES |
| Flag contradictions | YES |
| Timeout | 30 minutes |
| Max cost | $1.00 |

**Output: Documentary Blueprint**
```json
{
  "hook": "string (most compelling claim for opening)",
  "logline": "string (one-sentence pitch)",
  "narrative_structure": {
    "act_1_setup": {
      "opening_scene": "string",
      "key_players": [ { "name": "string", "role": "string", "introduction": "string" } ],
      "context": "string",
      "inciting_incident": "string"
    },
    "act_2_investigation": {
      "rising_action": [ { "beat": "string", "source": "string" } ],
      "conflicts": [ { "conflict": "string", "sides": ["string"] } ],
      "turning_points": [ "string" ],
      "complications": [ "string" ]
    },
    "act_3_resolution": {
      "climax": "string",
      "verified_facts": [ ... ],
      "open_questions": [ "string" ],
      "ending_options": [ "string" ]
    }
  },
  "key_conflicts": [
    { "conflict": "string", "side_a": "string", "side_b": "string", "evidence_each_side": [...] }
  ],
  "visual_moments": [
    { "description": "string", "keywords": ["string"], "purpose": "string" }
  ],
  "interview_suggestions": [
    { "name": "string", "role": "string", "priority": "Must-have | Nice-to-have",
      "what_they_know": "string", "suggested_questions": ["string"] }
  ],
  "archival_needs": [ "string" ],
  "production_notes": {
    "estimated_runtime": "string",
    "tone": "Investigative | Balanced | Empathetic",
    "graphics_needed": ["string"],
    "music_suggestions": "string",
    "legal_warnings": ["string"]
  }
}
```

### 2.6 Profile Mode
**Purpose:** Character-driven biographical research on a specific person.

**Configuration:**
| Parameter | Value |
|-----------|-------|
| Search strategy | Person-focused (name variations) |
| Tavily searches | 15 |
| Include YouTube | YES (interviews priority) |
| Include Academic | Only if person is academic/expert |
| Include News (GDELT) | YES |
| Include Reddit | YES (public perception) |
| Build timeline | YES (career/life timeline) |
| Extract quotes | YES (attributed to subject) |
| Find controversies | YES |
| Timeout | 15 minutes |
| Max cost | $0.50 |

**Output: Character Study**
```json
{
  "subject_summary": {
    "name": "string",
    "title": "string",
    "one_line_description": "string",
    "why_they_matter": "string"
  },
  "biographical_arc": {
    "origin": "string (where they came from)",
    "rise": "string (how they got here)",
    "defining_moments": [ { "event": "string", "date": "string", "significance": "string" } ],
    "current_status": "string",
    "trajectory": "string (where they're heading)"
  },
  "character_traits": [
    { "trait": "string", "evidence": "string", "quotes": ["string"] }
  ],
  "relationships": [
    { "person": "string", "relationship_type": "string", "significance": "string" }
  ],
  "controversies": [
    { "issue": "string", "their_position": "string", "critics_position": "string", "evidence": [...] }
  ],
  "public_vs_private": "string (contradictions in persona)",
  "quotes_bank": [ ... ],
  "visual_moments": [ ... ],
  "interview_suggestions": {
    "the_subject": { "accessibility": "string", "approach": "string" },
    "allies": [ ... ],
    "critics": [ ... ],
    "neutral_experts": [ ... ]
  },
  "production_notes": { ... }
}
```

### 2.7 Controversy Mode
**Purpose:** Balanced multi-perspective analysis of contested topics. MUST find and present multiple viewpoints fairly.

**BALANCE REQUIRED:** Controversy mode MUST find at least 2 opposing viewpoints. If only one perspective is found, the job should WARN the user that coverage is one-sided.

**Configuration:**
| Parameter | Value |
|-----------|-------|
| Search strategy | Multi-perspective (explicit pro/con) |
| Tavily searches | 20 |
| Must find opposing views | YES (minimum 2 perspectives) |
| Include YouTube | YES |
| Include Academic | YES (expert opinions) |
| Include Reddit | YES (community perspectives) |
| Flag source bias | YES |
| Present both sides | YES (required) |
| Identify common ground | YES |
| Timeout | 15 minutes |
| Max cost | $0.60 |

**Output: Multi-Perspective Analysis**
```json
{
  "issue_summary": {
    "what_is_being_debated": "string",
    "why_it_matters": "string",
    "stakes": "string"
  },
  "perspectives": [
    {
      "name": "string (label for this viewpoint)",
      "core_argument": "string",
      "key_proponents": [ { "name": "string", "role": "string" } ],
      "strongest_evidence": [ { "claim": "string", "source": "string" } ],
      "weaknesses": [ "string" ],
      "best_quotes": [ "string" ]
    }
  ],
  "common_ground": [ "string (what all sides agree on)" ],
  "genuine_disputes": [ "string (what's actually contested)" ],
  "factual_baseline": "string (undisputed facts)",
  "misleading_claims": [
    { "claim": "string", "who_makes_it": "string", "why_misleading": "string", "actual_facts": "string" }
  ],
  "expert_opinions": [ ... ],
  "historical_context": "string",
  "visual_approach": "string (how to show both sides fairly)",
  "interview_suggestions": {
    "perspective_a_voices": [ ... ],
    "perspective_b_voices": [ ... ],
    "neutral_voices": [ ... ]
  },
  "production_notes": {
    "tone": "Balanced (required)",
    "fairness_checks": [ "string" ],
    "legal_considerations": [ "string" ]
  }
}
```

---

## Section 3: Pipeline Architecture

### 3.1 Pipeline Overview
The pipeline is organized into 5 phases containing 11 stages. Stages within a phase can run in parallel where dependencies allow.

```
PHASE 1: PLANNING
  └── Stage 1: Research Planning
  └── Stage 2: Query Generation

PHASE 2: DISCOVERY (parallel where possible)
  └── Stage 3: Web Discovery (Tavily)
  └── Stage 4: News Discovery (GDELT)
  └── Stage 5: YouTube Discovery
  └── Stage 6: Reddit Discovery
  └── Stage 7: Academic Discovery (conditional)

PHASE 3: EXTRACTION (parallel)
  └── Stage 8: Content Extraction (Jina)
  └── Stage 9: Transcript Extraction

PHASE 4: SYNTHESIS
  └── Stage 10a: Research Synthesis
  └── Stage 10b: Documentary Intelligence

PHASE 5: OUTPUT
  └── Stage 11: Export (Google Drive + Downloads)
```

### 3.2 Stage Specifications

#### Stage 1: Research Planning
| Attribute | Value |
|-----------|-------|
| Purpose | Break research topic into angles and sub-questions |
| Input | User's research topic (string) + selected mode |
| Output | Research plan with 3-5 angles + short title |
| Tool | GPT-4o (single call) |
| Cost | ~$0.01 |
| Timeout | 30 seconds |
| Required | YES - job fails if this fails |

**Quality Gate:** Must produce at least 3 distinct angles. If LLM returns fewer, use default generic angles (who, what, when, where, why).

**Fallback:** If GPT-4o fails after 3 retries, use GPT-4o-mini. If that fails, use hardcoded generic research plan.

#### Stage 2: Query Generation
| Attribute | Value |
|-----------|-------|
| Purpose | Generate search queries for each angle |
| Input | Research plan from Stage 1 |
| Output | 10-25 search queries (varies by mode) |
| Tool | GPT-4o-mini (single call) |
| Cost | ~$0.001 |
| Timeout | 20 seconds |
| Required | YES - job fails if this fails |

**Quality Gate:** At least 2 queries per angle. No duplicate queries.

**Fallback:** If LLM fails, generate basic queries from topic: `[topic]`, `[topic] news`, `[topic] controversy`, `[topic] history`, `[topic] key people`.

#### Stage 3: Web Discovery (Tavily)
| Attribute | Value |
|-----------|-------|
| Purpose | Find web sources using search queries |
| Input | Search queries from Stage 2 |
| Output | 30-50 source URLs with metadata |
| Tool | Tavily (parallel calls, 1 per query) |
| Cost | ~$0.10-0.25 (10-25 searches at $0.01 each) |
| Timeout | 60 seconds total |
| Required | YES - job fails if <10 sources found |

**Execution:** Run queries in parallel (max 5 concurrent). Deduplicate URLs. Rank by Tavily relevance score.

**Quality Gate:** Must find at least 10 unique sources. If fewer, run additional queries.

**Fallback:** If Tavily is down, switch to Brave Search for remaining queries.

#### Stage 4: News Discovery (GDELT)
| Attribute | Value |
|-----------|-------|
| Purpose | Find recent news articles on the topic |
| Input | Topic + key terms from Stage 1 |
| Output | 10-20 news article URLs |
| Tool | GDELT (single API call) |
| Cost | FREE |
| Timeout | 30 seconds |
| Required | NO - continue without if fails |

**Mode-specific behavior:**
- **Breaking News:** This is PRIMARY source, last 48-72 hours
- **Investigation:** Full timeline, no time restriction
- **Quick:** Skip unless topic appears to be current events

#### Stage 5: YouTube Discovery
| Attribute | Value |
|-----------|-------|
| Purpose | Find relevant YouTube videos |
| Input | Topic + search queries |
| Output | 10-20 video IDs with metadata |
| Tool | YouTube Data API |
| Cost | FREE (API quota) |
| Timeout | 30 seconds |
| Required | NO - continue without if fails |

**Mode-specific behavior:**
- **Quick:** SKIP entirely
- **Breaking News:** SKIP (videos not current enough)
- **Profile:** Prioritize interviews with/about the subject
- **Investigation:** Find up to 20 videos

#### Stage 6: Reddit Discovery
| Attribute | Value |
|-----------|-------|
| Purpose | Find relevant Reddit discussions and firsthand accounts |
| Input | Topic + key terms |
| Output | 5-15 Reddit threads with top comments |
| Tool | PRAW (Reddit API) |
| Cost | FREE |
| Timeout | 30 seconds |
| Required | NO - continue without if fails |

**Mode-specific behavior:**
- **Quick:** SKIP entirely
- **Breaking News:** Search last 72 hours only, prioritize megathreads
- **Profile:** Search for AMAs, mentions in relevant subreddits
- **Investigation:** Deep search, include deleted/archived threads if accessible
- **Controversy:** Search multiple perspective subreddits

**Search Strategy:**
1. Search relevant subreddits for topic keywords
2. Filter by upvotes (>50 for relevance)
3. Extract top 10-20 comments per thread
4. Flag firsthand accounts (identified by language patterns)

#### Stage 7: Academic Discovery
| Attribute | Value |
|-----------|-------|
| Purpose | Find academic papers and research |
| Input | Topic + key terms |
| Output | 5-10 papers with abstracts |
| Tool | Semantic Scholar API |
| Cost | FREE |
| Timeout | 30 seconds |
| Required | NO - conditional on topic type |

**Execution:** Only run if topic is scientific, technical, medical, or policy-related. Search for highly-cited papers. Prefer last 5 years.

**Mode-specific behavior:**
- **Quick:** SKIP
- **Breaking News:** SKIP
- **Controversy:** Include (expert opinions important)

#### Stage 8: Content Extraction (Jina)
| Attribute | Value |
|-----------|-------|
| Purpose | Extract full text content from discovered URLs |
| Input | URLs from Stages 3, 4, 7 |
| Output | Markdown content for each URL |
| Tool | Jina Reader (parallel calls) |
| Cost | FREE (rate-limited: 200 req/day) |
| Timeout | 120 seconds total |
| Required | PARTIAL - need at least 5 successful extractions |

**Rate Limit Handling:**
- Jina free tier: 200 requests/day
- If limit reached: Switch to Trafilatura (local, no limit)
- Track daily usage across jobs

**Execution:** Run in parallel (max 10 concurrent). Truncate content >10K words.

**Quality Gate:** Discard extractions with <100 words. Need at least 5 successful extractions.

**Fallback:** If Jina is rate-limited or down, use Trafilatura (local, no API dependency).

#### Stage 9: Transcript Extraction
| Attribute | Value |
|-----------|-------|
| Purpose | Get transcripts from YouTube videos |
| Input | Video IDs from Stage 5 |
| Output | Transcripts with timestamps |
| Tool (primary) | youtube-transcript-api |
| Tool (fallback) | Whisper API ($0.006/min) |
| Cost | FREE or $0.06-0.60 if Whisper needed |
| Timeout | 120 seconds total |
| Required | NO - continue without if all fail |

**Whisper Budget Guard:**
Before using Whisper, calculate total cost:
```python
total_minutes = sum(video.duration_minutes for video in videos_without_captions)
whisper_cost = total_minutes * 0.006
if whisper_cost > remaining_budget:
    # Skip Whisper, add warning
    warnings.append(f"Skipped {len(videos)} video transcriptions (would cost ${whisper_cost:.2f})")
```

**Quality Gate:** Flag auto-generated vs manual captions. Skip videos with no transcript and insufficient Whisper budget.

#### Stage 10a: Research Synthesis
| Attribute | Value |
|-----------|-------|
| Purpose | Extract claims, quotes, timeline, entities from all content |
| Input | All extracted content from Stages 8-9 + Reddit from Stage 6 |
| Output | Structured research data (claims, quotes, timeline, entities) |
| Tool | GPT-4o (batched calls) |
| Cost | ~$0.05-0.15 |
| Timeout | 180 seconds |
| Required | YES - job fails if this fails |

**Execution:** Batch content into chunks that fit context window. Process each chunk. Merge and deduplicate results.

**Quality Gate:** Must extract at least 10 claims. Each claim must have source attribution. Flag conflicting claims.

#### Stage 10b: Documentary Intelligence
| Attribute | Value |
|-----------|-------|
| Purpose | Transform research into mode-specific documentary output |
| Input | Research synthesis from Stage 10a + mode config |
| Output | Mode-specific documentary blueprint (see Section 2) |
| Tool | GPT-4o (single call with structured output) |
| Cost | ~$0.02-0.10 |
| Timeout | 120 seconds |
| Required | YES - but degrades gracefully |

**Quality Gates:**
- Hook must be non-empty and <50 words
- All narrative sections must be present
- Every claim must cite a source
- Controversy mode: Both sides must be represented

**Fallback chain:**
1. Try GPT-4o with full prompt
2. If fails: Try GPT-4o with simplified prompt
3. If fails: Try GPT-4o-mini with simplified prompt
4. If all fail: Return research packet only (no documentary layer) with warning

#### Stage 11: Export
| Attribute | Value |
|-----------|-------|
| Purpose | Export final output to user's preferred format |
| Input | Complete job output (research + documentary) |
| Output | Google Doc URL(s) and/or downloadable files |
| Tool | Google Drive API + Google Docs API |
| Cost | FREE |
| Timeout | 60 seconds |
| Required | NO - job completes even if export fails |

**Export Options:**
1. **Google Drive** (default): Create Google Doc with formatted output
2. **JSON Download**: Raw structured data via API
3. **Markdown Download**: Formatted markdown file

**Fallback:** If Google Drive fails, output is always available via API. User can manually download from dashboard.

---

## Section 4: Quality Gates and Validation

### 4.1 Input Requirements by Mode

Before Stage 10b (Documentary Intelligence) runs, the research synthesis must meet minimum thresholds:

| Mode | Min Sources | Min Claims | Min Quotes | If Not Met |
|------|-------------|------------|------------|------------|
| Quick | 5 | 3 | 2 | Still produce brief |
| Full | 15 | 10 | 5 | Produce with warnings |
| Breaking | 5 | 3 | 2 | Add "limited info" flag |
| Investigation | 25 | 20 | 10 | Downgrade to "Full" output |
| Profile | 10 | 8 | 5 | Produce with gaps noted |
| Controversy | 15 (both sides) | 10 | 6 | FAIL if single-sided |

### 4.2 Output Validation Rules

After Stage 10b completes, validate the documentary output:

| Check | Requirement | If Fails |
|-------|-------------|----------|
| Hook exists | Non-empty, <50 words | Generate generic hook from top claim |
| Narrative complete | All required sections present | Fill missing with "[NEEDS RESEARCH]" |
| Sources cited | Every claim has source_url | Flag unsourced claims |
| Balance (Controversy) | ≥2 perspectives represented | FAIL job, warn user |
| Interview suggestions | At least 3 people | Reduce to "key players" list |
| Visual moments | At least 10 items (Investigation) | Reduce to 5 with warning |
| JSON valid | Output parses as valid JSON | Retry with simplified prompt |

---

## Section 5: Failure Handling and Resilience

### 5.1 Retry Strategy

All external API calls use exponential backoff:

```
Retry Configuration:
  max_retries: 3
  base_delay: 1 second
  max_delay: 30 seconds
  backoff: exponential (delay = base_delay * 2^attempt)

Retry Conditions:
  - HTTP 5xx errors: RETRY
  - HTTP 429 (rate limit): RETRY with longer delay (4x normal)
  - HTTP 4xx errors: DO NOT RETRY (except 429)
  - Timeout: RETRY
  - Connection error: RETRY
```

### 5.2 Circuit Breaker Pattern

Each external service has a circuit breaker to prevent cascading failures:

```
Circuit Breaker Configuration:
  failure_threshold: 5 consecutive failures
  reset_timeout: 60 seconds

States:
  CLOSED: Normal operation, requests allowed
  OPEN: Service failing, requests blocked, use fallback
  HALF-OPEN: After reset_timeout, allow one request to test

Services with circuit breakers:
  - tavily
  - jina
  - youtube
  - openai
  - gdelt
  - semantic_scholar
  - reddit
```

### 5.3 Fallback Chain

| Primary Tool | Fallback | Last Resort |
|--------------|----------|-------------|
| Tavily | Brave Search | Job fails (required stage) |
| Jina Reader | Trafilatura (local) | Skip URL, continue others |
| youtube-transcript-api | Whisper (if budget allows) | Skip video |
| GPT-4o | GPT-4o-mini | Hardcoded defaults |
| GDELT | Tavily (news filter) | Skip news stage |
| Semantic Scholar | Skip academic | Skip academic |
| PRAW (Reddit) | Skip Reddit | Skip Reddit |
| Google Drive export | Return data via API | Return data via API |

### 5.4 Required vs Optional Stages

| Stage | Required? | If Fails |
|-------|-----------|----------|
| 1. Planning | YES | Job fails |
| 2. Queries | YES | Job fails |
| 3. Web Discovery | YES | Job fails if <10 sources |
| 4. News | NO | Continue without news |
| 5. YouTube | NO | Continue without videos |
| 6. Reddit | NO | Continue without Reddit |
| 7. Academic | NO | Continue without papers |
| 8. Extraction | PARTIAL | Need ≥5 successful |
| 9. Transcripts | NO | Continue without transcripts |
| 10a. Synthesis | YES | Job fails |
| 10b. Documentary | DEGRADES | Return research only |
| 11. Export | NO | Data available via API |

### 5.5 Checkpoint System

After each stage completes, save a checkpoint to the job record:

```json
{
  "stage": "stage_3_web_discovery",
  "status": "completed",
  "timestamp": "ISO timestamp",
  "outputs": { "...stage outputs..." },
  "costs": { "tavily": 0.15 },
  "warnings": [ "...any warnings..." ]
}
```

Benefits:
- If pipeline crashes, can resume from last checkpoint
- Partial results always available
- Cost tracking is accurate
- Debugging is easier

---

## Section 6: Cost Tracking and Budget Enforcement

### 6.1 Cost Per Service

| Service | Unit | Cost |
|---------|------|------|
| Tavily search | Per search | $0.01 |
| Jina Reader | Per page | FREE (200/day) |
| GDELT | Per query | FREE |
| Semantic Scholar | Per query | FREE |
| YouTube Data API | Per query | FREE |
| youtube-transcript-api | Per video | FREE |
| PRAW (Reddit) | Per request | FREE |
| Whisper API | Per minute | $0.006 |
| GPT-4o (input) | Per 1K tokens | $0.005 |
| GPT-4o (output) | Per 1K tokens | $0.015 |
| GPT-4o-mini | Per 1K tokens | $0.00015 |
| Brave Search | Per search | FREE (2000/mo) then $0.003 |
| Google Drive API | Per operation | FREE |

### 6.2 Budget Limits by Mode

| Mode | Tavily | LLM | Whisper | Max Total |
|------|--------|-----|---------|-----------|
| Quick | $0.05 | $0.03 | $0 | $0.15 |
| Full | $0.15 | $0.15 | $0.20 | $0.50 |
| Breaking | $0.05 | $0.05 | $0 | $0.15 |
| Investigation | $0.25 | $0.25 | $0.50 | $1.00 |
| Profile | $0.15 | $0.15 | $0.20 | $0.50 |
| Controversy | $0.20 | $0.20 | $0.20 | $0.60 |

### 6.3 Budget Enforcement

```python
# Before each API call:
if cost_tracker.total + estimated_cost > budget_limit:
    if stage is required:
        # Try cheaper alternative (e.g., GPT-4o-mini instead of GPT-4o)
        pass
    else:
        # Skip this operation
        warnings.append(f"Skipped {operation} due to budget")

# After each API call:
cost_tracker.add(service, actual_cost)
update_job_record(costs=cost_tracker.breakdown)

# Budget exceeded behavior:
# - Stop non-essential stages
# - Use cheaper fallbacks for essential stages
# - Complete job with partial results
# - Add warning: "Budget limit reached, some stages skipped"
```

### 6.4 Cost Reporting

Every job record includes a cost breakdown:

```json
{
  "costs": {
    "total": 0.37,
    "budget_limit": 0.50,
    "breakdown": {
      "tavily": 0.15,
      "openai_gpt4o": 0.18,
      "openai_gpt4o_mini": 0.002,
      "whisper": 0.036,
      "jina": 0,
      "gdelt": 0,
      "reddit": 0,
      "youtube_api": 0
    },
    "budget_warnings": []
  }
}
```

---

## Section 7: Guaranteed Output Schema

**CONTRACT:** This schema is GUARANTEED. Every completed job produces this structure. Fields may be empty arrays but they always exist.

### 7.1 Complete Job Output

```json
{
  "job_id": "uuid",
  "status": "completed | failed | partial",
  "mode": "quick | full | breaking_news | investigation | profile | controversy",
  "topic": "string",
  "title": "string (AI-generated short title)",
  "created_at": "ISO timestamp",
  "completed_at": "ISO timestamp",
  "duration_seconds": "number",

  "research": {
    "summary": "string",
    "claims": [
      {
        "claim": "string",
        "source_url": "string",
        "source_title": "string",
        "confidence": "high | medium | low",
        "supporting_sources": ["url"],
        "contradicting_sources": ["url"]
      }
    ],
    "quotes": [
      {
        "text": "string",
        "speaker": "string | null",
        "source_url": "string",
        "context": "string"
      }
    ],
    "timeline": [
      {
        "date": "string (ISO or descriptive)",
        "event": "string",
        "source_url": "string",
        "precision": "exact | approximate | inferred"
      }
    ],
    "entities": [
      {
        "name": "string",
        "type": "person | organization | location",
        "role": "string",
        "mentions": "number"
      }
    ],
    "sources": [
      {
        "url": "string",
        "title": "string",
        "type": "web | news | youtube | academic | reddit",
        "extracted": "boolean",
        "word_count": "number"
      }
    ],
    "gaps": ["string (what couldn't be found)"]
  },

  "documentary": {
    "// Mode-specific structure (see Section 2)": "",
    "// Always present, structure varies by mode": ""
  },

  "metadata": {
    "stages_completed": ["string"],
    "stages_skipped": ["string"],
    "stages_failed": ["string"],
    "costs": { "...": "" },
    "warnings": ["string"]
  }
}
```

### 7.2 Error Response Schema

```json
{
  "job_id": "uuid",
  "status": "failed",
  "error": {
    "stage": "string (which stage failed)",
    "message": "string",
    "recoverable": "boolean",
    "partial_results_available": "boolean"
  },
  "partial_research": { "...if available...": "" },
  "metadata": {
    "stages_completed": ["string"],
    "costs": { "...": "" }
  }
}
```

---

## Section 8: API Endpoints

### 8.1 Jobs API

**POST /jobs** - Create a new research job

Request:
```json
{
  "topic": "string (required)",
  "mode": "quick | full | breaking_news | investigation | profile | controversy",
  "options": {
    "include_youtube": "boolean",
    "include_academic": "boolean",
    "include_reddit": "boolean",
    "max_cost": "number",
    "export_to_drive": "boolean",
    "export_formats": ["google_drive", "json", "markdown"]
  }
}
```

Response:
```json
{
  "job_id": "uuid",
  "status": "queued",
  "estimated_duration": "string",
  "estimated_cost": "number"
}
```

**GET /jobs/{job_id}** - Get job status and results

Response (running):
```json
{
  "job_id": "uuid",
  "status": "running",
  "current_stage": "string",
  "progress": "number (0-100)",
  "stages_completed": ["string"],
  "current_costs": { "...": "" }
}
```

Response (completed):
```json
{
  "// Full job output schema (see Section 7.1)": ""
}
```

**GET /jobs/{job_id}/download/{format}** - Download job output

Formats: `json`, `markdown`

**DELETE /jobs/{job_id}** - Cancel a running job or delete a completed job

### 8.2 Health API

**GET /health**

Response:
```json
{
  "status": "healthy | degraded | unhealthy",
  "services": {
    "database": "up | down",
    "redis": "up | down",
    "tavily": "up | down | rate_limited",
    "openai": "up | down | rate_limited",
    "jina": "up | down | rate_limited",
    "reddit": "up | down"
  },
  "version": "string",
  "uptime_seconds": "number"
}
```

---

## Section 9: Implementation Checklist

### Core Pipeline
- [ ] Stage 1: Research Planning (GPT-4o)
- [ ] Stage 2: Query Generation (GPT-4o-mini)
- [ ] Stage 3: Web Discovery (Tavily)
- [ ] Stage 4: News Discovery (GDELT)
- [ ] Stage 5: YouTube Discovery
- [ ] Stage 6: Reddit Discovery (PRAW)
- [ ] Stage 7: Academic Discovery (Semantic Scholar)
- [ ] Stage 8: Content Extraction (Jina + Trafilatura fallback)
- [ ] Stage 9: Transcript Extraction (youtube-transcript-api + Whisper)
- [ ] Stage 10a: Research Synthesis
- [ ] Stage 10b: Documentary Intelligence
- [ ] Stage 11: Export (Google Drive + Downloads)

### Research Modes
- [ ] Quick mode
- [ ] Full mode
- [ ] Breaking News mode (GDELT primary)
- [ ] Investigation mode (full pipeline)
- [ ] Profile mode (person-focused)
- [ ] Controversy mode (multi-perspective)

### Cost & Quality
- [ ] Per-API cost tracking
- [ ] Budget enforcement
- [ ] Quality gates at each stage
- [ ] Checkpoint system
- [ ] Circuit breakers

### Export Options
- [ ] Google Drive export
- [ ] JSON download
- [ ] Markdown download

---

## Appendix A: Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
OPENAI_API_KEY=sk-your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key

# Optional - Enhances research
YOUTUBE_API_KEY=your-youtube-api-key
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USERNAME=your-reddit-username
REDDIT_PASSWORD=your-reddit-password
JINA_API_KEY=your-jina-api-key  # Optional, free tier works
BRAVE_API_KEY=your-brave-api-key  # Fallback for Tavily

# Google Drive Export
GOOGLE_OAUTH_CLIENT_ID=your-google-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_OAUTH_REFRESH_TOKEN=your-google-oauth-refresh-token
GOOGLE_DRIVE_ROOT_FOLDER_ID=your-drive-folder-id

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

*END OF PRD v3.0*
