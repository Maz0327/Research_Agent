> **ARCHIVED:** This document has been superseded by PRD v6.0 (December 2024).
> See `Active Docs/PRD_v6.md` for the current authoritative specification.
>
> **Archive Reason:** Research validation found several claims in this document that did not match the actual implementation (LLM configuration, mode count, Quality Gate integration status).

---

# Research Agent: Complete Implementation Specification

> **Version**: 4.3 (Quality Gate + Niche Overlays)
> **Purpose**: Single source of truth for implementing the Research Agent system
> **Audience**: Claude Opus/Sonnet for code generation
> **Principle**: Always deliver value. Discovery always works. Enhancement is bonus. No job ever fails.

---

## What Changed from v4.2

| Component | v4.2 | v4.3 |
|-----------|------|------|
| **Source Selection** | Relevance score only | Quality Gate: floors + discovery-informed weighting |
| **Source Quotas** | Fixed percentages | Source floors (minimums) + flexible pool |
| **Extraction Allocation** | Top N by relevance | Floors first, then quality wins regardless of type |
| **Niche Support** | None | Niche Overlay Framework (config-only modifications) |
| **Initial Niches** | N/A | "downfalls" and "mysteries" |
| **Anti-Overfit** | None | Baseline Coverage Reserve (25% balanced) |
| **Video Priority** | Equal to other types | Discovery-informed (video-heavy topics get more video) |
| **Junk Filtering** | None | Quality score with junk pattern penalization |

---

## Table of Contents

1. [Philosophy & Guarantees](#part-1-philosophy--guarantees)
2. [Architecture](#part-2-architecture)
3. [LLM Configuration](#part-3-llm-configuration)
4. [Research Modes](#part-4-research-modes)
5. [Pipeline Stages](#part-5-pipeline-stages)
6. [Quality Gate](#part-6-quality-gate)
7. [External Services](#part-7-external-services)
8. [Documentary Intelligence](#part-8-documentary-intelligence)
9. [Output Schemas](#part-9-output-schemas)
10. [System Prompts](#part-10-system-prompts)
11. [Graceful Degradation](#part-11-graceful-degradation)
12. [Quality & User Guidance](#part-12-quality--user-guidance)
13. [Progress Messaging](#part-13-progress-messaging)
14. [Niche Overlay System](#part-14-niche-overlay-system)
15. [Configuration Reference](#part-15-configuration-reference)

---

# Part 1: Philosophy & Guarantees

## Core Philosophy

```yaml
packet_first_principle:
  statement: |
    Every research job produces an organized, ranked source packet.
    This packet is the FOUNDATION that always works.
    Everything else (extraction, transcription, synthesis) is ENHANCEMENT.
    Enhancement can fail gracefully. The packet cannot.

never_fail_principle:
  statement: |
    No job ever returns an error or empty response.
    Partial results with explanation > complete failure.
    User always gets something useful + knows what's missing.

honest_gaps_principle:
  statement: |
    Every limitation is surfaced, not hidden.
    Every gap comes with an explanation.
    Every explanation comes with actionable guidance.

# NEW in v4.3
quality_over_assumptions_principle:
  statement: |
    The topic determines where information lives, not our assumptions.
    Video can be primary. Reddit can be primary. Academic can be primary.
    Discovery results inform extraction priority, not hardcoded quotas.
    We ensure minimum coverage everywhere, then let quality win.
```

## The Three Guarantees

### Guarantee 1: Always Deliver

```yaml
definition: |
  Every job returns a valid response with useful content.
  Minimum: Organized source packet with links.
  Enhanced: Extracted content + synthesis + narrative.
  Never: Empty response, hard failure, or silent skip.

implementation:
  - Discovery layer runs first, always succeeds
  - Quality Gate filters junk before paid extraction
  - Enhancement layer runs second, can partially fail
  - Gap report generated regardless of enhancement success
  - User guidance generated for any gaps

# CRITICAL: Packet succeeds even if ALL LLMs are down
llm_independence:
  query_generation:
    on_llm_failure: "Immediate fallback to templates (0ms timeout)"
    behavior: "Do not wait for LLM retry—switch to templates instantly"
    templates_always_work: true
  
  synthesis_narrative:
    on_llm_failure: "Return packet without synthesis"
    behavior: "User still gets organized sources + NotebookLM bundle"
```

### Guarantee 2: Honest Assessment

```yaml
definition: |
  Quality standards are targets, not gates.
  When standards aren't met, we explain why.
  Assessment is transparent: what we searched, found, extracted, missed.

implementation:
  - Standards evaluated after job completion
  - Each unmet standard explained with reason
  - Overall quality rating: comprehensive/good/partial/limited
  - Never hide limitations in logs—surface in response
```

### Guarantee 3: Actionable Guidance

```yaml
definition: |
  Every gap comes with specific next steps.
  User knows exactly what to do manually.
  Suggestions are concrete: specific queries, sources, platforms.

implementation:
  - Generate manual action items from gap analysis
  - Prioritize by impact (high/medium/low)
  - Include specific search queries to try
  - Include specific sources to check
  - Include access workarounds for paywalls
```

---

# Part 2: Architecture

## Two-Layer System with Quality Gate

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LAYER 1: PACKET                                  │
│                    (Always executes, always succeeds)                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     QUERY GENERATION                              │   │
│  │   LLM (instant fallback to templates if unavailable)             │   │
│  │   + Niche query additions if niche selected                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        DISCOVERY                                  │   │
│  │                                                                   │   │
│  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │   │
│  │   │ Tavily  │ │ GDELT   │ │ Sem.Sch │ │ YouTube │ │  PRAW   │  │   │
│  │   │  (web)  │ │ (news)  │ │ (acad)  │ │ (video) │ │(optional)│  │   │
│  │   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   QUALITY GATE (NEW v4.3)                         │   │
│  │   • Deduplicate + canonicalize URLs                               │   │
│  │   • Penalize junk patterns                                        │   │
│  │   • Apply source floors (minimums)                                │   │
│  │   • Discovery-informed weighting                                  │   │
│  │   • Baseline coverage reserve (if niche active)                   │   │
│  │   • Max 60% cap per source type                                   │   │
│  │   • Max 2 per domain diversity constraint                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              ORGANIZE & RANK                                      │   │
│  │  • Categorize by type                                             │   │
│  │  • Detect paywall/access status                                   │   │
│  │  • Generate NotebookLM bundle                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Output: ResearchPacket (organized links, snippets, rankings)            │
│  Reliability: 99%+ | Cost: $0.02-0.08 | Time: 30-90 seconds             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: ENHANCEMENT                              │
│                    (Best effort, graceful degradation)                   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                       EXTRACTION                                  │   │
│  │   Tavily Extract (batched, 5 URLs) → Supadata Scrape (fallback)  │   │
│  │   • Only extracts Quality Gate approved sources                   │   │
│  │   • Track what failed and why                                     │   │
│  │   • Continue on failures                                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      TRANSCRIPTION                                │   │
│  │   Supadata (all platforms) → Whisper (fallback)                  │   │
│  │   • YouTube, TikTok, Instagram, Twitter, Facebook                │   │
│  │   • Track transcription method used                               │   │
│  │   • Videos without transcripts stay in packet                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                DOCUMENTARY INTELLIGENCE                           │   │
│  │   Claude Sonnet 4.5 (primary) | DeepSeek (--cheap) | Groq (fast) │   │
│  │   • Extract claims with source attribution                        │   │
│  │   • Assess confidence (high/medium/low/uncorroborated)           │   │
│  │   • Identify contradictions                                       │   │
│  │   • Generate grounded narrative (niche format if selected)        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Output: EnhancedResults (content, claims, narrative)                   │
│  Reliability: 70-90% | Cost: $0.10-1.50 | Time: 2-20 minutes           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ALWAYS: GAP ANALYSIS                                │
│  • Standards evaluation (met/not met + explanation)                     │
│  • Sources found but not extracted (with reasons)                       │
│  • Quality Gate filtering stats (what was rejected + why)               │
│  • Perspectives sought but not found                                    │
│  • Manual action suggestions (prioritized)                              │
│  • NotebookLM bundle for user                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow with Quality Gate

```
REQUEST
    │
    ▼
┌─────────────────┐
│  Parse Request  │
│  • topic        │
│  • mode         │
│  • niche (opt)  │
│  • --cheap flag │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Merge Configs   │
│ • mode config   │
│ • niche overlay │  ◄── NEW: Niche modifies queries, floors, weights
│ • stage caps    │
│ • budgets       │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Query Gen       │
│ Mode queries +  │
│ Niche additions │──► FAIL? ──► Immediate templates (0ms)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   DISCOVERY     │
│   (parallel)    │
│ • web           │
│ • news          │
│ • academic      │
│ • video         │
│ • discussion*   │
└─────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    QUALITY GATE (NEW)                        │
│  1. Dedupe + canonicalize URLs                               │
│  2. Calculate quality scores (penalize junk patterns)        │
│  3. Calculate relevance scores                               │
│  4. Discovery-informed type weighting                        │
│  5. Apply source floors (ensure minimum coverage)            │
│  6. Allocate flexible pool (quality wins)                    │
│  7. Apply baseline reserve if niche active (25%)             │
│  8. Enforce max 60% per type, max 2 per domain               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│ PACKET CREATED  │◄── Job is already "successful" at this point
└─────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│   EXTRACTION (Batched - 5 URLs per Tavily call)    │
│   Only extracts Quality Gate approved sources       │
│   budget_guard() before each batch                  │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│ TRANSCRIPTION   │
│ budget_guard()  │
│ before each vid │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   SYNTHESIS     │◄── Uses niche synthesis options if active
│ • claims        │
│ • confidence    │
│ • contradictions│
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   NARRATIVE     │◄── Uses niche narrative format if active
│ • grounded text │
│ • [CLM-XXX]     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  GAP ANALYSIS   │
│ • quality check │
│ • gate stats    │  ◄── NEW: What Quality Gate filtered out
│ • suggestions   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│     EXPORT      │
│ • full response │
│ • status: done  │
└─────────────────┘
```

---

# Part 3: LLM Configuration

## Provider Stack

```yaml
providers:
  claude:
    name: Claude Sonnet 4.5
    endpoint: https://api.anthropic.com/v1/messages
    model: claude-sonnet-4-5-20250929
    pricing:
      input: $3.00 / 1M tokens
      output: $15.00 / 1M tokens
    context_window: 200K tokens
    strengths:
      - Best instruction following
      - Excellent structured output
      - Superior documentary writing
    use_for: Quality modes (full, investigation, profile, controversy)
  
  groq:
    name: Groq (configurable model)
    endpoint: https://api.groq.com/openai/v1
    model: ${GROQ_MODEL}  # Config-first, not hardcoded
    default_model: llama-3.3-70b-versatile
    pricing:  # Verify at groq.com/pricing
      input: $0.59 / 1M tokens
      output: $0.79 / 1M tokens
    context_window: 128K tokens
    strengths:
      - 5-10x faster than alternatives
      - Good reasoning quality
      - OpenAI-compatible API
    use_for: Breaking news mode (speed priority)
  
  deepseek:
    name: DeepSeek V3
    endpoint: https://api.deepseek.com
    model: deepseek-chat
    pricing:
      input_cache_hit: $0.028 / 1M tokens
      input_cache_miss: $0.28 / 1M tokens
      output: $0.42 / 1M tokens
    context_window: 128K tokens
    strengths:
      - 10-30x cheaper than Claude
      - Comparable reasoning quality
      - 90% cache discount on repeated prompts
      - OpenAI-compatible API
    use_for: --cheap flag, fallback when primary down
```

## Mode-to-LLM Mapping

```yaml
mode_defaults:
  quick:
    llm: claude-sonnet-4.5
  breaking:
    llm: ${GROQ_MODEL}
  full:
    llm: claude-sonnet-4.5
  investigation:
    llm: claude-sonnet-4.5
  profile:
    llm: claude-sonnet-4.5
  controversy:
    llm: claude-sonnet-4.5
```

## --cheap Flag Override

```yaml
cheap_mode:
  flag: "--cheap"
  behavior: "Forces DeepSeek for all LLM calls in the job"
  affects:
    - query_generation
    - synthesis
    - narrative
  does_not_affect:
    - discovery (no LLM)
    - quality_gate (no LLM)
    - extraction (no LLM)
    - transcription (no LLM)
```

## Fallback Chain

```yaml
fallback_behavior:
  query_generation:
    if: "LLM returns error OR timeout"
    action: "IMMEDIATE switch to template queries (0ms wait)"
    log: "Query gen LLM unavailable, using templates"
  
  primary_down:
    if: "Claude API returns 5xx or timeout"
    action: "Switch to DeepSeek for this job"
  
  groq_down:
    if: "Groq API returns 5xx or timeout"
    action: "Switch to DeepSeek for breaking mode"
  
  all_down:
    if: "All LLM providers fail"
    action: "Return packet without synthesis/narrative"
```

---

# Part 4: Research Modes

## Mode Configuration Matrix

| Mode | Sources | Queries | Max Time | Budget | LLM | Discussion |
|------|---------|---------|----------|--------|-----|------------|
| quick | web | 5 | 3 min | $0.15 | Claude | No |
| breaking | news, web | 5 | 4 min | $0.15 | Groq | No |
| full | web, news, academic, video | 15 | 12 min | $0.50 | Claude | No |
| investigation | ALL | 25 | 25 min | $1.50 | Claude | **Yes** |
| profile | web, news, video | 15 | 15 min | $0.60 | Claude | No |
| controversy | web, news, discussion | 15 | 15 min | $0.60 | Claude | **Yes** |

## Default Source Floors (NEW in v4.3)

Each mode has minimum source floors (not quotas). After floors are met, remaining slots go to highest-quality sources regardless of type.

```yaml
source_floors_by_mode:
  quick:
    web: 2
    news: 0
    video: 0
    academic: 0
    discussion: 0
    max_extraction_slots: 5
  
  breaking:
    web: 2
    news: 3      # News is primary for breaking
    video: 0
    academic: 0
    discussion: 0
    max_extraction_slots: 10
  
  full:
    web: 3
    news: 2
    video: 2
    academic: 2
    discussion: 0
    max_extraction_slots: 20
  
  investigation:
    web: 3
    news: 2
    video: 3     # Video often critical for investigations
    academic: 2
    discussion: 2
    max_extraction_slots: 30
  
  profile:
    web: 2
    news: 2
    video: 3     # Interviews, appearances matter
    academic: 0
    discussion: 0
    max_extraction_slots: 20
  
  controversy:
    web: 2
    news: 2
    video: 2
    academic: 1
    discussion: 3  # Discussion critical for controversy
    max_extraction_slots: 20
```

## Baseline Coverage Reserve (NEW in v4.3)

When a niche is active, reserve 25% of extraction slots for balanced default strategy.

```yaml
baseline_coverage_reserve:
  enabled_when: niche_is_active
  reserve_percentage: 0.25  # 25% of slots
  behavior: |
    Reserved slots use mode's default source floors and discovery-informed
    weighting, ignoring niche overrides. This ensures crossover results
    even if niche is too narrow or wrong for the topic.
  
  example:
    mode: investigation
    niche: downfalls
    max_extraction_slots: 30
    reserved_slots: 8        # 25% of 30
    niche_slots: 22          # 75% of 30
    
    # Reserved 8 slots use investigation defaults
    # Remaining 22 slots use downfalls niche overrides
```

## Mode Specifications

### Quick Mode

```yaml
quick:
  purpose: "Fast surface-level research on a topic"
  
  discovery:
    sources: [web]
    discussion: false
    queries: 5
  
  source_floors:
    web: 2
    max_extraction_slots: 5
  
  enhancement:
    extraction:
      max_sources: 5
    transcription:
      enabled: false
    synthesis:
      depth: brief
      llm: claude-sonnet-4.5
    narrative:
      format: executive_summary
  
  standards:
    minimum_sources: 3
    minimum_extracted: 2
  
  caps:
    max_time: 180s
    max_cost: $0.15
```

### Breaking News Mode

```yaml
breaking:
  purpose: "Time-sensitive current events research"
  
  discovery:
    sources: [news, web]
    discussion: false
    queries: 5
    gdelt_priority: true
  
  source_floors:
    web: 2
    news: 3
    max_extraction_slots: 10
  
  enhancement:
    extraction:
      max_sources: 10
      priority: recency
    transcription:
      enabled: false
    synthesis:
      depth: timeline
      mark_unverified: true
      llm: ${GROQ_MODEL}
    narrative:
      format: timeline
  
  standards:
    minimum_sources: 5
    minimum_extracted: 3
    require_recent: true
  
  caps:
    max_time: 240s
    max_cost: $0.15
```

### Full Mode

```yaml
full:
  purpose: "Comprehensive research on a topic"
  
  discovery:
    sources: [web, news, academic, video]
    discussion: false
    queries: 15
  
  source_floors:
    web: 3
    news: 2
    video: 2
    academic: 2
    max_extraction_slots: 20
  
  enhancement:
    extraction:
      max_sources: 20
    transcription:
      max_videos: 5
    synthesis:
      depth: full
      llm: claude-sonnet-4.5
    narrative:
      format: full_report
  
  standards:
    minimum_sources: 15
    minimum_extracted: 10
    minimum_source_types: 2
  
  caps:
    max_time: 720s
    max_cost: $0.50
```

### Investigation Mode

```yaml
investigation:
  purpose: "Deep investigative research with all sources"
  
  discovery:
    sources: [web, news, academic, video, discussion]
    discussion: true
    queries: 25
    video_platforms: [youtube, tiktok, instagram, twitter, facebook]
  
  source_floors:
    web: 3
    news: 2
    video: 3
    academic: 2
    discussion: 2
    max_extraction_slots: 30
  
  enhancement:
    extraction:
      max_sources: 30
    transcription:
      max_videos: 10
    synthesis:
      depth: comprehensive
      entity_extraction: true
      timeline_extraction: true
      llm: claude-sonnet-4.5
    narrative:
      format: investigation_dossier
  
  standards:
    minimum_sources: 25
    minimum_extracted: 15
    minimum_source_types: 3
    minimum_perspectives: 2
    minimum_video_transcripts: 3
  
  caps:
    max_time: 1500s
    max_cost: $1.50
```

### Profile Mode

```yaml
profile:
  purpose: "Research on a specific person/entity"
  
  discovery:
    sources: [web, news, video]
    discussion: false
    queries: 15
    entity_focused: true
  
  source_floors:
    web: 2
    news: 2
    video: 3
    max_extraction_slots: 20
  
  enhancement:
    extraction:
      max_sources: 20
      priority: source_authority
    transcription:
      max_videos: 5
      prefer_interviews: true
    synthesis:
      depth: biographical
      llm: claude-sonnet-4.5
    narrative:
      format: profile
  
  standards:
    minimum_sources: 10
    minimum_extracted: 7
    requires_recent_source: true
  
  caps:
    max_time: 900s
    max_cost: $0.60
```

### Controversy Mode

```yaml
controversy:
  purpose: "Research on contested/debated topics"
  
  discovery:
    sources: [web, news, discussion]
    discussion: true
    queries: 15
    query_strategy: opposing_viewpoints
  
  source_floors:
    web: 2
    news: 2
    video: 2
    academic: 1
    discussion: 3
    max_extraction_slots: 20
  
  enhancement:
    extraction:
      max_sources: 20
      priority: perspective_balance
    transcription:
      max_videos: 3
    synthesis:
      depth: full
      perspective_detection: true
      llm: claude-sonnet-4.5
    narrative:
      format: controversy
  
  standards:
    minimum_sources: 15
    minimum_extracted: 10
    minimum_perspectives: 2
  
  caps:
    max_time: 900s
    max_cost: $0.60
```

---

# Part 5: Pipeline Stages

## Stage Overview

| # | Stage | Required | Layer | Can Fail Gracefully |
|---|-------|----------|-------|---------------------|
| 1 | Planning | Yes | Packet | No (config only) |
| 2 | Query Generation | Yes | Packet | Yes (INSTANT template fallback) |
| 3 | Web Discovery | Yes | Packet | Yes (try fallback search) |
| 4 | News Discovery | Mode-dependent | Packet | Yes (continue without) |
| 5 | Academic Discovery | Mode-dependent | Packet | Yes (continue without) |
| 6 | Video Discovery | Mode-dependent | Packet | Yes (continue without) |
| 7 | Discussion Discovery | Mode-dependent | Packet | Yes (continue without) |
| **8** | **Quality Gate** | **Yes** | **Packet** | **No (deterministic)** |
| 9 | Content Extraction | Enhancement | Enhancement | Yes (mark unextracted) |
| 10 | Video Transcription | Enhancement | Enhancement | Yes (keep video as link) |
| 11a | Research Synthesis | Enhancement | Enhancement | Yes (return claims only) |
| 11b | Narrative Generation | Enhancement | Enhancement | Yes (return synthesis only) |
| 12 | Gap Analysis | Yes | Always | No (always runs) |
| 13 | Export | Yes | Always | No (always returns response) |

## Per-Stage Caps

```yaml
stage_caps:
  query_generation:
    max_time: 30s
    max_tokens: 4000
    fallback: immediate
  
  web_discovery:
    max_calls: 15
    max_time: 60s
  
  news_discovery:
    max_calls: 10
    max_time: 45s
  
  academic_discovery:
    max_calls: 10
    max_time: 30s
  
  video_discovery:
    max_calls: 10
    max_quota_units: 1000
    max_time: 30s
  
  discussion_discovery:
    max_calls: 10
    max_time: 30s
    enabled_modes: [investigation, controversy]
  
  quality_gate:
    max_time: 5s  # Deterministic, should be fast
  
  extraction:
    max_urls: 30
    batch_size: 5
    max_time: 180s
    max_per_batch_time: 30s
  
  transcription:
    max_videos: 10
    max_total_minutes: 60
    max_time: 300s
  
  synthesis:
    max_input_tokens: 32000
    max_time: 90s
  
  narrative:
    max_input_tokens: 32000
    max_time: 90s
```

## Stage 1: Planning

```yaml
planning:
  inputs:
    - topic: string
    - mode: quick | breaking | full | investigation | profile | controversy
    - niche: string (optional)
    - cheap_flag: boolean
  
  outputs:
    - merged_config: MergedConfiguration
    - llm_provider: claude | groq | deepseek
    - stage_caps: StageCaps
    - job_budget: JobBudget
  
  logic: |
    1. Load mode configuration
    2. If niche specified, load niche config and merge (Part 14 rules)
    3. If --cheap flag, override LLM to deepseek
    4. Calculate baseline reserve if niche active
    5. Set stage caps
    6. Calculate job budget (cost AND time)
    7. Initialize progress tracking
    8. Initialize budget_guard with job limits
```

## Stage 2: Query Generation

```yaml
query_generation:
  inputs:
    - topic: string
    - merged_config: MergedConfiguration
    - llm_provider: string
  
  outputs:
    - queries: QuerySet[]
    - generation_method: "llm" | "templates"
  
  caps:
    max_time: 30s
    max_tokens: 4000
  
  logic: |
    # Get base queries for mode
    base_queries = mode_config.queries
    
    # Add niche query additions if active
    if niche_config:
      niche_queries = niche_config.query_additions
      all_query_templates = base_queries + niche_queries
    else:
      all_query_templates = base_queries
    
    try:
      response = llm.generate(QUERY_PROMPT, timeout=25s)
      queries = parse_queries(response)
      return queries, "llm"
    except (LLMError, TimeoutError, ParseError):
      # INSTANT fallback - do not retry
      queries = generate_from_templates(topic, all_query_templates)
      return queries, "templates"
```

## Stages 3-7: Discovery

Discovery stages remain similar to v4.2. See Part 7 (External Services) for details.

Key change: All discovered sources are passed to Quality Gate before extraction decisions.

## Stage 8: Quality Gate (NEW)

See [Part 6: Quality Gate](#part-6-quality-gate) for complete specification.

## Stage 9: Content Extraction

```yaml
content_extraction:
  primary: tavily_extract
  fallback: supadata_scrape
  
  caps:
    max_urls: 30
    batch_size: 5
    max_time: 180s
    max_per_batch_time: 30s
  
  # ONLY extracts sources approved by Quality Gate
  logic: |
    approved_sources = quality_gate_output.approved_for_extraction
    
    batches = chunk(approved_sources, size=5)
    
    for batch in batches:
      estimated_cost = 0.002 * len(batch)
      if not budget_guard("extraction", estimated_cost):
        mark_remaining_unextracted(remaining)
        break
      
      try:
        results = tavily.extract(urls=[s.url for s in batch])
        # ... process results
      except TavilyExtractError:
        # Fallback to Supadata per-URL
        for source in batch:
          try:
            content = supadata.scrape(source.url)
            # ... process
          except SupadataError:
            source.extraction_status = "failed"
            continue
```

## Stage 10: Video Transcription

```yaml
video_transcription:
  primary: supadata
  fallback: whisper
  
  platforms: [youtube, tiktok, instagram, twitter, facebook]
  
  # Handle TikTok/Instagram gracefully
  platform_notes:
    youtube:
      reliability: high
      method: supadata_native → supadata_ai → whisper
    tiktok:
      reliability: medium  # Less tested
      method: supadata → whisper
      on_failure: keep_as_link
    instagram:
      reliability: medium
      method: supadata → whisper
      on_failure: keep_as_link
    twitter:
      reliability: medium
      method: supadata → whisper
      on_failure: keep_as_link
  
  logic: |
    for video in videos_to_transcribe:
      estimated_cost = estimate_transcription_cost(video.duration)
      if not budget_guard("transcription", estimated_cost):
        mark_remaining_untranscribed(remaining)
        break
      
      try:
        transcript = supadata.get_transcript(video.url)
        video.transcript = transcript
        video.transcription_method = "supadata_native"
      except NoTranscriptError:
        try:
          transcript = supadata.generate_transcript(video.url)
          video.transcript = transcript
          video.transcription_method = "supadata_ai"
        except SupadataError:
          try:
            audio = download_audio(video.url)
            transcript = whisper.transcribe(audio)
            video.transcript = transcript
            video.transcription_method = "whisper"
          except WhisperError as e:
            video.transcription_status = "failed"
            video.transcription_note = str(e)
            # Video stays in packet without transcript
            continue
```

## Stages 11-13: Synthesis, Narrative, Gap Analysis, Export

These remain similar to v4.2, with the addition of niche-specific options for synthesis and narrative format.

```yaml
synthesis_with_niche:
  logic: |
    # Apply niche synthesis options if active
    if niche_config and niche_config.synthesis:
      synthesis_options = merge(mode_config.synthesis, niche_config.synthesis)
    else:
      synthesis_options = mode_config.synthesis
    
    # Generate synthesis with merged options
    # ...

narrative_with_niche:
  logic: |
    # Use niche narrative format if specified
    if niche_config and niche_config.narrative_format:
      format = niche_config.narrative_format
    else:
      format = mode_config.narrative.format
    
    # Generate narrative with format
    # ...
```

---

# Part 6: Quality Gate

## Overview

The Quality Gate is a deterministic (no LLM) filter between Discovery and Extraction. It prevents paying to extract junk while ensuring diverse, high-quality source coverage.

```yaml
quality_gate:
  purpose: |
    1. Don't pay to extract/summarize junk
    2. Ensure minimum coverage across source types
    3. Let discovery results inform where information actually lives
    4. Prevent any single source type from dominating
    5. Maintain crossover results even when niche is active
  
  position: After Discovery, Before Extraction
  
  cost: $0 (no LLM, no API calls)
  
  time: <5 seconds (deterministic rules)
```

## Quality Gate Pipeline

```
Discovery Results (all sources found)
    │
    ▼
┌─────────────────────────────────────┐
│  STEP 1: Deduplicate + Canonicalize │
│  • Normalize URLs (strip tracking)  │
│  • Keep first occurrence            │
│  • Log duplicates removed           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  STEP 2: Calculate Quality Scores   │
│  • Base score from source authority │
│  • Penalize junk patterns           │
│  • Penalize thin snippets           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  STEP 3: Calculate Relevance Scores │
│  • Keyword overlap (topic + query)  │
│  • Title/snippet matching           │
│  • (Existing v4.2 logic)            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  STEP 4: Combined Scoring           │
│  final = relevance * 0.6 +          │
│          quality * 0.4              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  STEP 5: Discovery-Informed Weight  │
│  • Calculate avg relevance per type │
│  • Quantity bonus per type          │
│  • Normalize to weights             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  STEP 6: Allocate Slots             │
│  • Fill source floors first         │
│  • Allocate flexible pool by weight │
│  • Apply baseline reserve if niche  │
│  • Enforce max 60% per type         │
│  • Enforce max 2 per domain         │
└─────────────────────────────────────┘
    │
    ▼
Approved Sources (for extraction)
```

## Step 1: URL Canonicalization

```python
def canonicalize_url(url: str) -> str:
    """
    Normalize URL to canonical form for deduplication.
    """
    parsed = urlparse(url)
    
    # Remove tracking parameters
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid'
    }
    
    query_params = parse_qs(parsed.query)
    cleaned_params = {k: v for k, v in query_params.items() 
                      if k.lower() not in tracking_params}
    
    # Normalize
    canonical = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip('/'),
        '',
        urlencode(cleaned_params, doseq=True),
        ''
    ))
    
    return canonical


def deduplicate_sources(sources: List[PacketSource]) -> List[PacketSource]:
    """
    Remove duplicate sources based on canonical URL.
    Keep first occurrence (usually highest-ranked from discovery).
    """
    seen_urls = set()
    unique_sources = []
    duplicates_removed = []
    
    for source in sources:
        canonical = canonicalize_url(source.url)
        
        if canonical not in seen_urls:
            seen_urls.add(canonical)
            source.canonical_url = canonical
            unique_sources.append(source)
        else:
            duplicates_removed.append(source.url)
    
    log.info(f"Deduplication: {len(sources)} → {len(unique_sources)} "
             f"({len(duplicates_removed)} duplicates removed)")
    
    return unique_sources
```

## Step 2: Quality Score Calculation

```python
# Junk patterns that indicate low-quality pages
JUNK_PATTERNS = [
    r'/category/',
    r'/tag/',
    r'/tags/',
    r'/page/\d+',
    r'/author/',
    r'/archive/',
    r'/archives/',
    r'\?p=\d+$',           # WordPress permalink
    r'/wp-content/',
    r'/feed/',
    r'/rss/',
    r'/sitemap',
    r'/search\?',
    r'/login',
    r'/register',
    r'/cart',
    r'/checkout',
    r'/#',                  # Anchor-only links
]

# Patterns that indicate thin content
THIN_CONTENT_INDICATORS = [
    'click here',
    'read more',
    'subscribe to',
    'sign up for',
    'cookie policy',
    'privacy policy',
    'terms of service',
]

# Domain authority tiers (simplified)
HIGH_AUTHORITY_DOMAINS = {
    'nytimes.com', 'washingtonpost.com', 'wsj.com', 'bbc.com', 'bbc.co.uk',
    'theguardian.com', 'reuters.com', 'apnews.com', 'npr.org',
    'nature.com', 'science.org', 'arxiv.org',
    'github.com', 'stackoverflow.com',
}

MEDIUM_AUTHORITY_TLDS = ['.gov', '.edu', '.ac.uk', '.org']


def calculate_quality_score(source: PacketSource) -> float:
    """
    Calculate quality score (0-1) based on source characteristics.
    Higher = better quality, more likely to have real content.
    """
    score = 0.5  # Base score
    
    # Domain authority bonus
    domain = source.domain.lower()
    if domain in HIGH_AUTHORITY_DOMAINS:
        score += 0.2
    elif any(domain.endswith(tld) for tld in MEDIUM_AUTHORITY_TLDS):
        score += 0.1
    
    # Junk pattern penalties
    url_lower = source.url.lower()
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, url_lower):
            score -= 0.15
            break  # Only penalize once
    
    # Homepage penalty (often not useful for research)
    parsed = urlparse(source.url)
    if parsed.path in ['', '/', '/index.html', '/index.php']:
        score -= 0.2
    
    # Thin snippet penalty
    snippet = (source.snippet or '').lower()
    if len(snippet) < 50:
        score -= 0.1
    
    for indicator in THIN_CONTENT_INDICATORS:
        if indicator in snippet:
            score -= 0.05
    
    # Video sources get slight bonus (often rich content)
    if source.type == 'video':
        score += 0.1
    
    # Clamp to 0-1
    return max(0.0, min(1.0, score))
```

## Step 3: Combined Scoring

```python
def calculate_final_score(source: PacketSource) -> float:
    """
    Combine relevance and quality scores.
    Weight relevance higher (we want on-topic content)
    but quality matters too (we don't want junk).
    """
    relevance = source.relevance_score  # Already calculated in discovery
    quality = calculate_quality_score(source)
    
    source.quality_score = quality
    source.final_score = (relevance * 0.6) + (quality * 0.4)
    
    return source.final_score
```

## Step 4: Discovery-Informed Weighting

```python
def calculate_type_weights(sources: List[PacketSource]) -> Dict[str, float]:
    """
    Calculate weights for each source type based on discovery results.
    Types with higher-quality sources get more weight.
    This lets the TOPIC determine where information lives.
    """
    type_scores = {}
    
    for source_type in ["web", "news", "video", "academic", "discussion"]:
        type_sources = [s for s in sources if s.type == source_type]
        
        if not type_sources:
            type_scores[source_type] = 0
            continue
        
        # Average final_score of top 5 sources in this type
        sorted_sources = sorted(type_sources, key=lambda s: s.final_score, reverse=True)
        top_5 = sorted_sources[:5]
        avg_score = sum(s.final_score for s in top_5) / len(top_5)
        
        # Quantity bonus: more sources found = richer source type for this topic
        # Cap at 0.2 bonus for 20+ sources
        quantity_bonus = min(len(type_sources) / 100, 0.2)
        
        type_scores[source_type] = avg_score + quantity_bonus
    
    # Normalize to weights (sum to 1.0)
    total = sum(type_scores.values())
    if total == 0:
        return {"web": 0.4, "news": 0.25, "video": 0.2, "academic": 0.1, "discussion": 0.05}
    
    weights = {k: v / total for k, v in type_scores.items()}
    
    log.info(f"Discovery-informed weights: {weights}")
    
    return weights
```

## Step 5: Slot Allocation

```python
def allocate_extraction_slots(
    sources: List[PacketSource],
    mode_config: ModeConfig,
    niche_config: Optional[NicheConfig],
    type_weights: Dict[str, float]
) -> List[PacketSource]:
    """
    Allocate extraction slots using:
    1. Source floors (minimums per type)
    2. Discovery-informed flexible pool
    3. Baseline reserve (if niche active)
    4. Max constraints (60% per type, 2 per domain)
    """
    
    # Get configuration
    if niche_config and niche_config.source_floors:
        floors = niche_config.source_floors
    else:
        floors = mode_config.source_floors
    
    max_slots = mode_config.max_extraction_slots
    
    # Track allocations
    allocated = []
    allocated_by_type = {t: [] for t in ["web", "news", "video", "academic", "discussion"]}
    allocated_domains = {}
    
    # STEP 1: Fill floors first
    floor_slots_used = 0
    
    for source_type, floor in floors.items():
        if source_type == "max_extraction_slots":
            continue
        
        type_sources = sorted(
            [s for s in sources if s.type == source_type],
            key=lambda s: s.final_score,
            reverse=True
        )
        
        added = 0
        for source in type_sources:
            if added >= floor:
                break
            
            # Enforce max 2 per domain even in floors
            domain = source.domain
            if allocated_domains.get(domain, 0) >= 2:
                continue
            
            allocated.append(source)
            allocated_by_type[source_type].append(source)
            allocated_domains[domain] = allocated_domains.get(domain, 0) + 1
            added += 1
            floor_slots_used += 1
    
    log.info(f"Floor allocation: {floor_slots_used} slots used")
    
    # STEP 2: Calculate remaining flexible pool
    remaining_slots = max_slots - floor_slots_used
    
    # STEP 3: Apply baseline reserve if niche active
    if niche_config:
        reserve_slots = int(max_slots * 0.25)
        niche_slots = remaining_slots - reserve_slots
        
        # Reserve slots use balanced allocation (ignore niche weights)
        # Niche slots use niche-influenced allocation
        log.info(f"Baseline reserve: {reserve_slots} slots, Niche pool: {niche_slots} slots")
    else:
        reserve_slots = 0
        niche_slots = remaining_slots
    
    # STEP 4: Allocate flexible pool
    # Get all sources not yet allocated, sorted by final_score
    remaining_sources = [s for s in sources if s not in allocated]
    remaining_sources.sort(key=lambda s: s.final_score, reverse=True)
    
    flexible_allocated = 0
    max_per_type = int(max_slots * 0.6)  # 60% cap
    
    for source in remaining_sources:
        if flexible_allocated >= (niche_slots + reserve_slots):
            break
        
        source_type = source.type
        domain = source.domain
        
        # Enforce max 60% per type
        if len(allocated_by_type[source_type]) >= max_per_type:
            continue
        
        # Enforce max 2 per domain
        if allocated_domains.get(domain, 0) >= 2:
            continue
        
        allocated.append(source)
        allocated_by_type[source_type].append(source)
        allocated_domains[domain] = allocated_domains.get(domain, 0) + 1
        flexible_allocated += 1
    
    log.info(f"Flexible pool allocation: {flexible_allocated} slots used")
    log.info(f"Total allocated: {len(allocated)} sources")
    log.info(f"By type: {{{', '.join(f'{k}: {len(v)}' for k, v in allocated_by_type.items())}}}")
    
    return allocated
```

## Complete Quality Gate Function

```python
def quality_gate(
    discovery_results: DiscoveryResults,
    mode_config: ModeConfig,
    niche_config: Optional[NicheConfig] = None
) -> QualityGateOutput:
    """
    Main Quality Gate function.
    Filters discovery results into extraction-ready sources.
    
    Deterministic, no LLM, no API calls.
    """
    all_sources = discovery_results.get_all_sources()
    
    # Step 1: Deduplicate
    sources = deduplicate_sources(all_sources)
    
    # Step 2 & 3: Calculate quality and final scores
    for source in sources:
        calculate_final_score(source)
    
    # Step 4: Discovery-informed weighting
    type_weights = calculate_type_weights(sources)
    
    # Step 5: Allocate slots
    approved = allocate_extraction_slots(
        sources=sources,
        mode_config=mode_config,
        niche_config=niche_config,
        type_weights=type_weights
    )
    
    # Build output
    rejected = [s for s in sources if s not in approved]
    
    return QualityGateOutput(
        approved_for_extraction=approved,
        rejected_sources=rejected,
        stats=QualityGateStats(
            total_discovered=len(all_sources),
            after_dedup=len(sources),
            approved_count=len(approved),
            rejected_count=len(rejected),
            type_weights=type_weights,
            by_type={
                t: len([s for s in approved if s.type == t])
                for t in ["web", "news", "video", "academic", "discussion"]
            }
        )
    )
```

## Quality Gate Output Schema

```typescript
interface QualityGateOutput {
  approved_for_extraction: PacketSource[];
  rejected_sources: PacketSource[];
  stats: QualityGateStats;
}

interface QualityGateStats {
  total_discovered: number;
  after_dedup: number;
  approved_count: number;
  rejected_count: number;
  
  // Discovery-informed weights
  type_weights: {
    web: number;
    news: number;
    video: number;
    academic: number;
    discussion: number;
  };
  
  // Final allocation by type
  by_type: {
    web: number;
    news: number;
    video: number;
    academic: number;
    discussion: number;
  };
  
  // Rejection reasons
  rejection_breakdown: {
    duplicate: number;
    low_quality: number;
    domain_limit: number;
    type_cap: number;
    slot_exhausted: number;
  };
}
```

---

# Part 7: External Services

## Service Configuration

### Tavily (Web Search + Extraction)

```yaml
tavily:
  base_url: https://api.tavily.com
  
  endpoints:
    search: /search
    extract: /extract
  
  pricing:
    search: 1-2 credits per call
    extract: 1-2 credits per 5 successful URLs
  
  rate_limits:
    dev_tier: 100 RPM
    prod_tier: 1000 RPM
    default_assumption: 100 RPM
```

### Brave (Search Fallback)

```yaml
brave:
  base_url: https://api.search.brave.com
  
  endpoints:
    web_search: /res/v1/web/search
  
  pricing:
    free_tier: 2000 queries/month
    paid: $0.003 per query
```

### GDELT (News Discovery)

```yaml
gdelt:
  base_url: https://api.gdeltproject.org/api/v2
  
  endpoints:
    doc: /doc/doc
  
  pricing: free
  
  usage:
    query: string
    mode: "artlist"
    format: "json"
    maxrecords: 50
    timespan: "7d" | "30d" | "1y"
```

### Semantic Scholar (Academic Discovery)

```yaml
semantic_scholar:
  base_url: https://api.semanticscholar.org
  
  endpoints:
    search: /graph/v1/paper/search
  
  pricing: free
  
  rate_limits:
    requests_per_second: 1 (with API key)
```

### YouTube Data API (Video Discovery)

```yaml
youtube:
  base_url: https://www.googleapis.com/youtube/v3
  
  pricing:
    quota: 10,000 units/day
    search.list: 100 units
    videos.list: 1 unit
  
  caps:
    max_searches_per_job: 10
```

### Reddit/PRAW (Discussion Discovery)

```yaml
reddit:
  library: praw
  
  rate_limits:
    requests_per_minute: 100
  
  enabled_modes: [investigation, controversy]
  
  fallback:
    method: web_search
    query_modifier: "site:reddit.com"
```

### Supadata (Transcription + Extraction Fallback)

```yaml
supadata:
  base_url: https://api.supadata.ai
  
  capabilities:
    primary: Video transcription (all platforms)
    secondary: Web extraction (fallback only)
  
  platforms:
    youtube: high_reliability
    tiktok: medium_reliability
    instagram: medium_reliability
    twitter: medium_reliability
    facebook: medium_reliability
  
  pricing:
    transcript_native: ~$0.006
    transcript_ai_per_minute: ~$0.012
    web_scrape: ~$0.006
```

### OpenAI Whisper (Transcription Fallback)

```yaml
whisper:
  base_url: https://api.openai.com/v1
  
  pricing:
    per_minute: $0.006
```

### Claude (Primary LLM)

```yaml
claude:
  base_url: https://api.anthropic.com/v1
  model: claude-sonnet-4-5-20250929
  
  pricing:
    input: $3.00 / 1M tokens
    output: $15.00 / 1M tokens
```

### Groq (Speed LLM)

```yaml
groq:
  base_url: https://api.groq.com/openai/v1
  model: ${GROQ_MODEL}
  
  pricing:
    input: $0.59 / 1M tokens
    output: $0.79 / 1M tokens
```

### DeepSeek (Budget/Fallback LLM)

```yaml
deepseek:
  base_url: https://api.deepseek.com
  model: deepseek-chat
  
  pricing:
    input_cache_hit: $0.028 / 1M tokens
    input_cache_miss: $0.28 / 1M tokens
    output: $0.42 / 1M tokens
```

---

# Part 8: Documentary Intelligence

## Overview

```yaml
documentary_intelligence:
  purpose: |
    Transform raw sources into structured claims with confidence ratings,
    then generate a grounded narrative that cites every claim.
    
  stages:
    1. Claim Extraction (synthesis)
    2. Confidence Assessment (with independence heuristic)
    3. Contradiction Detection
    4. Narrative Generation (grounded, niche format if active)
```

## Claim Schema

```typescript
interface Claim {
  claim_id: string;            // "CLM-001"
  statement: string;           // Clear, specific factual statement
  
  confidence: "high" | "medium" | "low" | "uncorroborated";
  confidence_reason: string;
  corroboration_attempts: number;
  
  source_ids: string[];
  corroborated: boolean;       // ≥2 independent sources?
  
  category: "factual" | "statistic" | "quote" | "opinion" | "disputed" | "unverified";
  topic_area: string;
  entities_mentioned: string[];
}
```

## Confidence Levels

```yaml
confidence_levels:
  high:
    criteria: "≥2 INDEPENDENT sources confirm"
    independence: "Determined by independence heuristic"
    narrative_language: "Direct assertion"
  
  medium:
    criteria: "1 reputable source OR multiple non-independent sources"
    narrative_language: "Hedged language"
  
  low:
    criteria: "1 source with caveats OR source reliability uncertain"
    narrative_language: "Explicit uncertainty"
  
  uncorroborated:
    criteria: "Could not verify after max_attempts"
    max_attempts: 3
    narrative_language: "Explicit non-verification"
```

## Independence Heuristic

```python
WIRE_MARKERS = {
    "reuters", "associated press", "ap news", "afp",
    "agence france-presse", "bloomberg", "pr newswire",
    "business wire", "globe newswire"
}

SYNDICATORS = {
    "yahoo.com", "msn.com", "smartnews.com",
    "news.google.com", "flipboard.com"
}

def is_wire_or_syndicated(source: PacketSource) -> bool:
    text = " ".join([
        (source.source_name or ""),
        (source.title or ""),
        (source.extracted_content or "")[:2000],
    ]).lower()
    
    if any(marker in text for marker in WIRE_MARKERS):
        return True
    
    if source.domain in SYNDICATORS:
        return True
    
    return False


def are_independent(source_a: PacketSource, source_b: PacketSource) -> bool:
    # Same domain → not independent
    if source_a.domain == source_b.domain:
        return False
    
    # Wire/syndication → not independent
    if is_wire_or_syndicated(source_a) or is_wire_or_syndicated(source_b):
        return False
    
    # Different domains, neither is wire/syndicated → independent
    return True
```

## Narrative Grounding Rules

```yaml
grounding_rules:
  mandatory:
    - Every factual statement MUST cite [CLM-XXX]
    - No new facts in narrative (only presentation of claims)
    - Confidence reflected in language
  
  language_by_confidence:
    high: "Direct statement: 'The company was founded in 2015 [CLM-001].'"
    medium: "Attribution: 'According to the Wall Street Journal... [CLM-002].'"
    low: "Uncertainty: 'One unverified report suggests... [CLM-003].'"
    uncorroborated: "Non-verification: 'This claim could not be independently verified... [CLM-004].'"
```

---

# Part 9: Output Schemas

## Complete Response Schema

```typescript
interface ResearchResponse {
  job_id: string;
  topic: string;
  mode: string;
  niche?: string;  // NEW in v4.3
  cheap_mode: boolean;
  created_at: string;
  completed_at: string;
  
  status: "completed" | "partial";
  status_reason?: string;
  
  packet: ResearchPacket;
  quality_gate: QualityGateStats;  // NEW in v4.3
  enhancement?: EnhancementResults;
  documentary?: DocumentaryResults;
  
  quality_assessment: QualityAssessment;
  gap_report: GapReport;
  cost_report: CostReport;
}
```

## Research Packet Schema

```typescript
interface ResearchPacket {
  discovery: {
    queries_executed: QueryExecution[];
    query_generation_method: "llm" | "templates";
    niche_queries_added: number;  // NEW
    total_sources_found: number;
    sources_by_type: {
      web: number;
      news: number;
      academic: number;
      video: number;
      discussion: number;
    };
  };
  
  // Quality Gate results
  quality_gate: {
    approved_for_extraction: number;
    rejected: number;
    type_weights: Record<string, number>;
    final_allocation: Record<string, number>;
  };
  
  sources: {
    web: PacketSource[];
    news: PacketSource[];
    academic: PacketSource[];
    video: PacketSource[];
    discussion: PacketSource[];
  };
  
  key_sources: string[];
  suggested_reading_order: string[];
  notebooklm_bundle: NotebookLMBundle;
}

interface PacketSource {
  source_id: string;
  url: string;
  canonical_url: string;  // NEW
  title: string;
  domain: string;
  
  snippet: string;
  source_name: string;
  published_date?: string;
  discovered_via: string;
  
  relevance_score: number;
  quality_score: number;  // NEW
  final_score: number;    // NEW
  
  access_status: "open" | "likely_paywalled" | "requires_login" | "unknown";
  
  // Quality Gate decision
  gate_decision: "approved" | "rejected";
  gate_rejection_reason?: string;
  
  extraction_status?: "success" | "failed" | "skipped" | "not_attempted";
  extraction_method?: "tavily" | "supadata";
  extracted_content?: string;
  
  transcript?: string;
  transcription_method?: "supadata_native" | "supadata_ai" | "whisper";
}
```

## Gap Report Schema (Updated)

```typescript
interface GapReport {
  standards_evaluation: StandardEvaluation[];
  
  // Quality Gate stats
  quality_gate_summary: {
    total_discovered: number;
    approved: number;
    rejected: number;
    rejection_reasons: Record<string, number>;
    type_coverage: Record<string, number>;
  };
  
  extraction_gaps: {
    sources_not_extracted: SourceGap[];
    extraction_rate: number;
    budget_exhausted: boolean;
  };
  
  transcription_gaps: {
    videos_not_transcribed: VideoGap[];
    transcription_rate: number;
    platform_failures: Record<string, number>;  // NEW: track by platform
  };
  
  content_gaps: {
    missing_perspectives: string[];
    uncorroborated_claims: string[];
    open_questions: string[];
  };
  
  budget_status: {
    cost_budget_remaining: number;
    time_budget_remaining: number;
    stages_skipped_due_to_budget: string[];
  };
  
  user_guidance: UserGuidance[];
  notebooklm_bundle: NotebookLMBundle;
}
```

---

# Part 10: System Prompts

## Query Generation Prompt (Updated for Niches)

```markdown
SYSTEM:
You are a research query generator. Generate search queries to thoroughly research a topic.

TASK:
Generate {query_count} diverse search queries for: {topic}

MODE: {mode}
{niche_context}

REQUIREMENTS:
1. Cover different angles: who, what, when, where, why, how
2. Mix broad queries ("topic overview") with specific queries ("topic + specific aspect")
3. Include synonyms and related terms
{niche_requirements}

OUTPUT FORMAT:
```json
{
  "queries": [
    {
      "query": "search query text",
      "intent": "what we're looking for",
      "expected_sources": ["web", "news", "video"]
    }
  ]
}
```
```

## Research Synthesis Prompt

```markdown
SYSTEM:
You are a research analyst extracting structured claims from source material.

YOUR TASK:
1. Read all provided sources carefully
2. Extract factual claims with proper attribution
3. Assess confidence based on corroboration
4. Identify contradictions between sources
5. Note gaps in the research

{niche_synthesis_instructions}

CONFIDENCE LEVELS:

HIGH confidence:
- Claim appears in ≥2 INDEPENDENT sources
- Independence means: different domains, not wire/syndicated content

MEDIUM confidence:
- 1 reputable source OR multiple non-independent sources

LOW confidence:
- Single source with caveats OR contradicted claim

UNCORROBORATED:
- Checked multiple sources but could not find confirmation

OUTPUT SCHEMA:
[Standard claim schema]
```

## Narrative Generation Prompt (Updated for Niches)

```markdown
SYSTEM:
You are a documentary writer creating a research report from structured claims.

YOUR TASK:
Write a {format} report using ONLY the provided claims.

{niche_narrative_instructions}

CRITICAL GROUNDING RULES:
1. Every factual statement MUST cite [CLM-XXX]
2. NO new facts - only present what's in the claims
3. Confidence level determines language

FORMAT: {format_template}

CLAIMS TO USE:
{claims_json}

CONTRADICTIONS TO ADDRESS:
{contradictions_json}
```

---

# Part 11: Graceful Degradation

## Universal Rules

```yaml
universal_rules:
  rule_1_never_hard_fail:
    description: "All stages wrapped in try/catch"
  
  rule_2_always_explain:
    description: "Every degradation → gap report entry"
  
  rule_3_preserve_partial:
    description: "Keep everything obtained before failure"
  
  rule_4_surface_not_bury:
    description: "Gaps in main output, not just logs"
```

## Budget Guard (Universal)

```yaml
budget_guard:
  description: |
    Every external call MUST pass budget_guard() BEFORE making the call.
  
  checks:
    - cost: "Is estimated_cost within remaining budget?"
    - time: "Is estimated_time within remaining time budget?"
  
  on_denied:
    - Skip remaining work in that stage
    - Log gap entry with reason
    - Continue to next stage
```

## Quality Gate Degradation

```yaml
quality_gate_degradation:
  # Quality Gate is deterministic and should not fail
  # But handle edge cases gracefully
  
  if_no_sources_discovered:
    action: "Return empty approved list"
    gap_entry: "No sources found in discovery"
  
  if_all_sources_filtered:
    action: "Lower quality threshold, retry allocation"
    gap_entry: "All sources initially filtered, lowered threshold"
  
  if_timeout:
    action: "Return partial allocation"
    gap_entry: "Quality gate timeout, partial filtering applied"
```

## Platform-Specific Transcription Degradation

```yaml
transcription_degradation:
  youtube:
    reliability: high
    on_failure: try_whisper
  
  tiktok:
    reliability: medium
    on_failure: keep_as_link
    gap_entry: "TikTok transcription failed - video available as link"
  
  instagram:
    reliability: medium
    on_failure: keep_as_link
    gap_entry: "Instagram transcription failed - video available as link"
  
  twitter:
    reliability: medium
    on_failure: keep_as_link
    gap_entry: "Twitter video transcription failed - video available as link"
```

---

# Part 12: Quality & User Guidance

## Quality Assessment Logic

Same as v4.2, with additional Quality Gate metrics factored in.

## User Guidance Generation (Updated)

```python
def generate_user_guidance(gap_report: GapReport) -> List[UserGuidance]:
    guidance = []
    
    # Quality Gate rejected high-relevance sources
    for source in gap_report.quality_gate_summary.rejected_high_relevance:
        guidance.append(UserGuidance(
            priority="medium",
            action=f"Manually check: {source.title}",
            reason=f"Filtered by Quality Gate ({source.gate_rejection_reason})",
            resources=[source.url]
        ))
    
    # Platform-specific transcription failures
    for platform, count in gap_report.transcription_gaps.platform_failures.items():
        if count > 0:
            guidance.append(UserGuidance(
                priority="medium",
                action=f"Watch {count} {platform} video(s) manually",
                reason=f"{platform} transcription failed",
                resources=gap_report.transcription_gaps.failed_urls_by_platform[platform]
            ))
    
    # ... other guidance (paywalls, perspectives, etc.)
    
    return guidance
```

---

# Part 13: Progress Messaging

## Two-Audience System

Same as v4.2:
- Admin: Redis Streams + SSE (real-time)
- User: Supabase + polling

## Quality Gate Progress Messages

```yaml
quality_gate_messages:
  start:
    admin: "Running Quality Gate on {n} discovered sources"
    user: "Analyzing sources..."
  
  complete:
    admin: "Quality Gate: {approved}/{total} approved. Weights: {weights}"
    user: "Selected {approved} best sources"
```

---

# Part 14: Niche Overlay System

## Overview

Niches are **config-only modifications** that overlay on existing modes. They do NOT create new pipelines.

```yaml
niche_overlay_system:
  purpose: |
    Customize research for specific content types without
    duplicating infrastructure. Niches modify:
    - Query templates (what to search)
    - Source floors (minimum coverage per type)
    - Extraction priorities
    - Synthesis options
    - Narrative format
  
  design_principles:
    - Additive, not multiplicative complexity
    - Config changes only, no new code paths
    - Baseline reserve ensures crossover results
    - User prompt always overrides niche
```

## Niche Configuration Schema

```yaml
# Schema for niche config files
niche_config_schema:
  name: string                    # Niche identifier
  description: string             # What this niche is for
  
  # Query modifications
  query_additions: string[]       # Additional query templates
  query_modifiers: string[]       # Keywords to add to all queries
  
  # Source floor overrides
  source_floors:
    web: number
    news: number
    video: number
    academic: number
    discussion: number
  
  # Extraction priorities
  extraction_priority: string[]   # e.g., ["recency", "discussion", "video"]
  
  # Synthesis options
  synthesis:
    force_timeline: boolean
    rumor_labeling: boolean
    include_reactions: boolean
    perspective_pairs: boolean
    # ... other synthesis options
  
  # Narrative format override
  narrative_format: string        # e.g., "timeline_with_reactions"
  narrative_instructions: string  # Additional prompt instructions
```

## Niche: downfalls

```yaml
# config/niches/downfalls.yaml
niche:
  name: downfalls
  description: |
    Scandal timelines, public reactions, rumor vs fact.
    Inspired by: Internet Anarchist, Patrick CC
  
  query_additions:
    - "{topic} controversy timeline"
    - "{topic} allegations"
    - "{topic} response statement"
    - "{topic} reddit drama"
    - "{topic} apology"
    - "{topic} sponsor drop"
    - "{topic} receipts"
    - "{topic} exposed"
  
  query_modifiers:
    - "controversy"
    - "drama"
    - "scandal"
  
  source_floors:
    web: 2
    news: 3
    video: 5        # Higher - receipts are often videos
    academic: 0     # Rarely relevant
    discussion: 4   # Reddit reactions matter
  
  extraction_priority:
    - recency
    - discussion
    - video
  
  synthesis:
    force_timeline: true
    rumor_labeling: true
    include_reactions: true
  
  narrative_format: timeline_with_reactions
  
  narrative_instructions: |
    Structure the narrative as:
    1. THE RISE: Background on the subject before controversy
    2. THE FALL: Timeline of events with [CLM-XXX] citations
    3. THE RECEIPTS: Key evidence and sources
    4. THE REACTIONS: Public/community response
    5. THE AFTERMATH: Current status and ongoing developments
    
    For each claim, explicitly note if it's:
    - CONFIRMED (2+ independent sources)
    - ALLEGED (single source or unverified)
    - DISPUTED (contradictory claims exist)
```

## Niche: mysteries

```yaml
# config/niches/mysteries.yaml
niche:
  name: mysteries
  description: |
    Myths, ARGs, conspiracy analysis, pro/con evidence.
    Inspired by: Why Files, Alex Bale
  
  query_additions:
    - "{topic} evidence"
    - "{topic} debunked"
    - "{topic} explained"
    - "{topic} origin"
    - "{topic} theory"
    - "{topic} skeptic analysis"
    - "{topic} believers"
    - "{topic} documentary"
  
  query_modifiers:
    - "mystery"
    - "theory"
    - "truth"
  
  source_floors:
    web: 2
    news: 1
    video: 6        # YouTube docs are primary sources
    academic: 2     # Debunker/scientific content
    discussion: 2   # Community theories
  
  extraction_priority:
    - video
    - academic
    - discussion
  
  synthesis:
    perspective_pairs: true   # Believer vs skeptic
    origin_tracking: true     # Where did this claim originate?
    evidence_categorization: true
  
  narrative_format: mystery_case_file
  
  narrative_instructions: |
    Structure the narrative as a case file:
    
    ## THE MYSTERY
    [Brief, compelling description of the phenomenon]
    
    ## ORIGIN
    [Where/when this first emerged, with citations]
    
    ## THE EVIDENCE
    ### Evidence FOR
    - [Evidence point] [CLM-XXX]
    - [Evidence point] [CLM-XXX]
    
    ### Evidence AGAINST
    - [Debunk/skeptic point] [CLM-XXX]
    - [Debunk/skeptic point] [CLM-XXX]
    
    ## KEY FIGURES
    [Who are the main voices on each side?]
    
    ## OPEN QUESTIONS
    [What remains genuinely unexplained?]
    
    ## VERDICT
    [Balanced assessment based on evidence strength]
    
    Mark each claim with confidence and note contradictions explicitly.
```

## Mode + Niche Merge Rules

```yaml
merge_rules:
  # When user specifies: --mode investigation --niche downfalls
  
  query_additions:
    rule: append
    behavior: "Niche queries added to mode queries"
  
  source_floors:
    rule: override
    behavior: "Niche floors replace mode floors"
  
  extraction_priority:
    rule: override
    behavior: "Niche priority replaces mode priority"
  
  synthesis:
    rule: merge
    behavior: "Niche synthesis options added to mode options"
  
  narrative_format:
    rule: override
    behavior: "Niche format replaces mode format"
  
  narrative_instructions:
    rule: append
    behavior: "Niche instructions added after mode instructions"
  
  # These are NOT affected by niche
  unchanged:
    - llm_provider (use mode default or --cheap)
    - max_time (use mode cap)
    - max_cost (use mode cap)
    - max_extraction_slots (use mode limit)
  
  # Baseline reserve always applies
  baseline_reserve:
    always_active_when_niche: true
    percentage: 0.25
```

## Precedence Rules

```yaml
precedence:
  # Highest to lowest
  1_user_prompt: "Explicit user instructions override everything"
  2_niche_config: "Niche-specific settings"
  3_mode_config: "Mode defaults"
  4_system_defaults: "Global fallbacks"
  
  examples:
    - scenario: "User says 'focus on academic sources' with mysteries niche"
      result: "Academic sources prioritized despite niche preferring video"
    
    - scenario: "User specifies --mode quick --niche downfalls"
      result: "Quick mode caps apply, but downfalls query additions used"
    
    - scenario: "No niche specified"
      result: "Pure mode behavior, no niche modifications"
```

## Using Niches

```bash
# Command line
/research "Logan Paul CryptoZoo" --mode investigation --niche downfalls
/research "Bermuda Triangle" --mode full --niche mysteries

# Without niche (pure mode)
/research "Federal Reserve policy" --mode full

# With --cheap
/research "MrBeast drama" --mode investigation --niche downfalls --cheap
```

## Future Niches (Not Yet Implemented)

These are defined but not implemented in v4.3. Add based on usage patterns:

```yaml
future_niches:
  curiosities:
    description: "Weird facts, trivia, engaging narration (Thoughty2, Side Projects)"
    status: planned
  
  history_religion:
    description: "Deep events, doctrinal debates, primary sources"
    status: planned
  
  profile_deep:
    description: "Guest prep, interview questions, biographical deep dive"
    note: "May overlap with profile mode - evaluate need"
    status: planned
  
  pop_culture:
    description: "Reality TV, entertainment, viral moments, fan theories"
    status: planned
  
  current_affairs:
    description: "News, politics, stakeholder mapping, competing frames"
    note: "May overlap with breaking/controversy modes"
    status: planned
```

---

# Part 15: Configuration Reference

## Environment Variables

```bash
# === CORE INFRASTRUCTURE ===
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
REDIS_URL=redis://localhost:6379

# === SEARCH SERVICES ===
TAVILY_API_KEY=xxx
BRAVE_API_KEY=xxx

# === TRANSCRIPTION SERVICES ===
SUPADATA_API_KEY=xxx
OPENAI_API_KEY=xxx

# === LLM SERVICES ===
ANTHROPIC_API_KEY=xxx
GROQ_API_KEY=xxx
GROQ_MODEL=llama-3.3-70b-versatile
DEEPSEEK_API_KEY=xxx

# === DISCOVERY SERVICES ===
SEMANTIC_SCHOLAR_API_KEY=xxx
YOUTUBE_API_KEY=xxx
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT=xxx

# === FEATURE FLAGS ===
ENABLE_CHEAP_MODE=true
ENABLE_ADMIN_SSE=true
ENABLE_NICHES=true           # NEW
ENABLE_VIDEO_TRANSCRIPTION=true
ENABLE_ACADEMIC_SEARCH=true
```

## Quality Gate Configuration

```yaml
# config/quality_gate.yaml
quality_gate:
  # URL canonicalization
  tracking_params_to_strip:
    - utm_source
    - utm_medium
    - utm_campaign
    - utm_term
    - utm_content
    - fbclid
    - gclid
    - ref
    - source
    - mc_cid
    - mc_eid
  
  # Junk patterns (regex)
  junk_patterns:
    - '/category/'
    - '/tag/'
    - '/tags/'
    - '/page/\d+'
    - '/author/'
    - '/archive/'
    - '/feed/'
    - '/search\?'
    - '/login'
    - '/cart'
  
  # Scoring weights
  scoring:
    relevance_weight: 0.6
    quality_weight: 0.4
  
  # Constraints
  constraints:
    max_per_domain: 2
    max_per_type_percentage: 0.60
  
  # Baseline reserve
  baseline_reserve:
    percentage: 0.25
    applies_when: niche_active
```

## Niche Registry

```yaml
# config/niches/registry.yaml
niches:
  enabled:
    - downfalls
    - mysteries
  
  disabled:
    - curiosities
    - history_religion
    - profile_deep
    - pop_culture
    - current_affairs
  
  default: null  # No niche by default
```

## Mode Budget Configuration

```yaml
# config/modes.yaml
modes:
  quick:
    max_cost: 0.15
    max_time: 180
    llm: claude
    source_floors: {web: 2}
    max_extraction_slots: 5
  
  breaking:
    max_cost: 0.15
    max_time: 240
    llm: ${GROQ_MODEL}
    source_floors: {web: 2, news: 3}
    max_extraction_slots: 10
  
  full:
    max_cost: 0.50
    max_time: 720
    llm: claude
    source_floors: {web: 3, news: 2, video: 2, academic: 2}
    max_extraction_slots: 20
  
  investigation:
    max_cost: 1.50
    max_time: 1500
    llm: claude
    source_floors: {web: 3, news: 2, video: 3, academic: 2, discussion: 2}
    max_extraction_slots: 30
  
  profile:
    max_cost: 0.60
    max_time: 900
    llm: claude
    source_floors: {web: 2, news: 2, video: 3}
    max_extraction_slots: 20
  
  controversy:
    max_cost: 0.60
    max_time: 900
    llm: claude
    source_floors: {web: 2, news: 2, video: 2, academic: 1, discussion: 3}
    max_extraction_slots: 20
```

---

# Implementation Checklist

## Core Architecture
- [ ] Packet layer runs independently and always succeeds
- [ ] Quality Gate between Discovery and Extraction
- [ ] Enhancement layer failures don't break packet delivery
- [ ] Gap report always generated
- [ ] Per-stage caps enforced
- [ ] Budget guard called BEFORE every external API call

## Quality Gate (NEW)
- [ ] URL canonicalization + deduplication
- [ ] Quality score calculation with junk pattern detection
- [ ] Discovery-informed type weighting
- [ ] Source floors allocation
- [ ] Flexible pool allocation
- [ ] Baseline coverage reserve when niche active
- [ ] Max 60% per type constraint
- [ ] Max 2 per domain constraint
- [ ] Quality Gate stats in response

## Niche System (NEW)
- [ ] Niche config loading from YAML
- [ ] Mode + niche merge logic
- [ ] Query additions from niche
- [ ] Source floor overrides
- [ ] Synthesis option merging
- [ ] Narrative format override
- [ ] Baseline reserve activation
- [ ] "downfalls" niche implemented
- [ ] "mysteries" niche implemented

## LLM Integration
- [ ] Claude configured as primary
- [ ] Groq model configurable via env var
- [ ] DeepSeek as fallback and --cheap override
- [ ] Instant query gen fallback to templates

## Discovery
- [ ] All 5 discovery types implemented
- [ ] Discussion only for investigation/controversy
- [ ] Video discovery includes YouTube, TikTok, Instagram, Twitter

## Transcription
- [ ] Platform-specific reliability tracking
- [ ] Graceful degradation for TikTok/Instagram
- [ ] Videos without transcripts stay in packet

## Documentary Intelligence
- [ ] Independence heuristic implemented
- [ ] Confidence includes "uncorroborated"
- [ ] Niche narrative formats supported

## Response
- [ ] Quality Gate stats in response
- [ ] Niche info in response
- [ ] All schemas valid

---

# Part 16: Validated API Recommendations (December 2025)

> **Research Date:** December 23, 2025
> **Purpose:** Validated pricing, capabilities, and recommendations based on current API documentation
> **Sources:** Official API documentation from Tavily, Exa, Perplexity, Groq, DeepSeek, Anthropic, Supadata, Jina, Firecrawl, Parallel.ai, Google

---

## 16.1 Search APIs - Validated Pricing

### Primary: Tavily (KEEP)

```yaml
tavily:
  pricing:
    free_tier: 1,000 credits/month
    project_plan: $30/month = 4,000 credits
    bootstrap_plan: $100/month = 15,000 credits
    startup_plan: $220/month = 38,000 credits
    growth_plan: $500/month = 100,000 credits
    pay_as_you_go: $0.008/credit

  credit_costs:
    search_basic: 1 credit/request
    search_advanced: 2 credits/request
    extract_basic: 1 credit per 5 successful URLs
    extract_advanced: 2 credits per 5 successful URLs
    map_basic: 1 credit per 10 pages
    map_with_instructions: 2 credits per 10 pages
    research_pro: 15-250 credits/request
    research_mini: 4-110 credits/request

  verdict: "KEEP as PRIMARY - Best cost/capability balance, Extract feature is unique"
  source: "https://docs.tavily.com/documentation/api-credits"
```

### Secondary: Exa.ai (KEEP)

```yaml
exa:
  pricing:
    free_tier: "$10 in credits, no expiration"
    search_fast_auto: $5/1k requests (1-25 results)
    search_deep: $15/1k requests
    contents_text: $1/1k pages
    contents_highlights: $1/1k pages
    contents_summary: $1/1k pages
    answer: $5/1k answers
    research_api:
      exa_research: $5/1k searches + $5/1k pages + $5/1M reasoning tokens
      exa_research_pro: $5/1k searches + $10/1k pages + $5/1M reasoning tokens

  accuracy: "94.9% reported on semantic search benchmarks"

  verdict: "KEEP for ACADEMIC/SEMANTIC search - Neural search is superior for investigation mode"
  source: "https://exa.ai/pricing"
```

### Tertiary: Brave Search (KEEP)

```yaml
brave:
  pricing:
    free_tier: 2,000 queries/month
    paid: $0.003/query

  verdict: "KEEP as FALLBACK - Good free tier for backup"
  source: "https://api.search.brave.com"
```

---

## 16.2 Extraction APIs - Validated Pricing

### Primary: Jina Reader (PROMOTE)

```yaml
jina_reader:
  pricing:
    free_tier: "Unlimited via r.jina.ai prefix (rate limited)"
    with_api_key: "Token-based, shared across all Jina services"
    new_users: "10 million tokens free"

  rate_limits:
    free: 20 RPM
    paid_api_key: 500 RPM
    premium: 5,000 RPM

  speed: "2-3 seconds per page"

  features:
    - "Clean markdown output"
    - "LLM-ready formatting"
    - "Search via s.jina.ai"
    - "ReaderLM-v2 for HTML to markdown"

  verdict: "PROMOTE to PRIMARY - FREE saves significant cost"
  source: "https://jina.ai/reader/"
```

### Secondary: Tavily Extract (KEEP for batches)

```yaml
tavily_extract:
  pricing:
    basic: 1 credit per 5 successful URLs
    advanced: 2 credits per 5 successful URLs
    failed_extractions: "No charge"

  verdict: "KEEP for BATCH operations - 5-URL batches are cost-effective"
  source: "https://docs.tavily.com/documentation/api-credits"
```

### Tertiary: Trafilatura (KEEP)

```yaml
trafilatura:
  pricing: "FREE (local library)"
  verdict: "KEEP as LOCAL FALLBACK"
```

### Updated Extraction Chain

```yaml
extraction_fallback_chain:
  order:
    1: jina_reader    # FREE, 2-3 sec/page, cloud-friendly
    2: tavily_extract # 1-2 credits per 5 URLs (batched)
    3: trafilatura    # FREE, local fallback
```

---

## 16.3 Transcription APIs - Validated Pricing (UPDATED)

### Primary: Supadata (KEEP as #1)

```yaml
supadata:
  pricing:
    free_tier: 100 credits/month
    basic_plan: $5/month = 300 credits
    pro_plan: $17/month = 3,000 credits
    mega_plan: $47/month = 30,000 credits
    giga_plan: $297/month = 300,000 credits
    auto_recharge: $10 per 1,000 credits (varies by plan)

  credit_costs:
    transcript_fetch: 1 credit
    transcript_generate_ai: 2 credits/minute
    youtube_data: 1 credit
    url_scrape: 1 credit
    translation: 30 credits/minute

  platforms: [youtube, tiktok, instagram, twitter, facebook]
  cloud_friendly: true

  verdict: "KEEP as PRIMARY - Multi-platform, works from cloud IPs"
  source: "https://supadata.ai/pricing"
```

### Secondary: OpenAI Whisper (PROMOTE to #2)

```yaml
openai_whisper:
  pricing:
    whisper_standard: $0.006/minute ($0.36/hour)
    gpt4o_transcribe: $0.006/minute
    gpt4o_mini_transcribe: $0.003/minute ($0.18/hour)

  free_credits: "$5 for new users (833 minutes with Whisper)"

  cloud_friendly: true  # Downloads audio via yt-dlp, then transcribes

  verdict: "PROMOTE to SECONDARY - Works from cloud IPs (downloads audio first)"
  source: "https://openai.com/pricing"
```

### Tertiary: youtube-transcript-api (DEMOTE to #3)

```yaml
youtube_transcript_api:
  pricing: "FREE"
  cloud_friendly: false  # Often blocked by cloud IPs (Railway, Vercel, etc.)

  verdict: "DEMOTE to TERTIARY - Unreliable from cloud infrastructure"
  source: "https://github.com/jdepoix/youtube-transcript-api"
```

### Updated Transcription Chain (CRITICAL CHANGE)

```yaml
transcription_fallback_chain:
  # UPDATED ORDER - Prioritizes cloud-friendly services
  order:
    1: supadata           # PRIMARY - Multi-platform, cloud-friendly
    2: openai_whisper     # SECONDARY - Downloads audio, cloud-friendly
    3: youtube_transcript_api  # TERTIARY - FREE but blocked by cloud IPs
    4: manual_fallback    # FINAL - User instructions

  rationale: |
    youtube-transcript-api is demoted because cloud IPs (Railway, Vercel, AWS, GCP)
    are frequently blocked by YouTube. Supadata and Whisper both work reliably
    from cloud infrastructure.
```

### Manual Fallback Specification (NEW)

```yaml
manual_fallback:
  trigger: "All automated methods fail"

  response_format:
    error_summary:
      message: "Unable to automatically transcribe {count} video(s)"
      failures_per_video:
        - video_url: string
        - video_title: string
        - supadata_error: string
        - whisper_error: string
        - youtube_api_error: string

    manual_instructions:
      option_1_copy_paste:
        title: "YouTube Transcript Copy/Paste (Easiest)"
        steps:
          - "Open the video: {video_url}"
          - "Click the '...' menu below the video"
          - "Select 'Show transcript'"
          - "Click three dots in transcript panel → 'Toggle timestamps'"
          - "Select all (Ctrl/Cmd+A) and copy (Ctrl/Cmd+C)"
          - "Paste into a text file or NotebookLM directly"

      option_2_local_api:
        title: "YouTube Transcript API (Run Locally)"
        description: "Run from your local machine (not cloud) to avoid IP blocks"
        code: |
          from youtube_transcript_api import YouTubeTranscriptApi

          video_ids = ["{video_id_1}", "{video_id_2}"]

          for vid_id in video_ids:
              try:
                  transcript = YouTubeTranscriptApi.get_transcript(vid_id)
                  text = " ".join([t['text'] for t in transcript])
                  with open(f"{vid_id}.txt", "w") as f:
                      f.write(text)
                  print(f"✓ Saved {vid_id}.txt")
              except Exception as e:
                  print(f"✗ Failed {vid_id}: {e}")

    videos_for_manual_processing:
      - url: string
        title: string
        duration: string
        channel: string

  gap_report_entry:
    category: "transcription_failure"
    priority: "medium"
    action: "Manual transcript extraction required"
    resources: ["list of video URLs"]
```

---

## 16.4 LLM APIs - Validated Pricing (Per Million Tokens)

### Current: OpenAI (REDUCE usage)

```yaml
openai:
  models:
    gpt-4o:
      input: $2.50
      output: $10.00
      context: 128K
    gpt-4o-mini:
      input: $0.15
      output: $0.60
      context: 128K

  verdict: "REDUCE - Use only when quality is critical; DeepSeek is 10-100x cheaper"
  source: "https://openai.com/pricing"
```

### ADD: DeepSeek V3 (--cheap mode)

```yaml
deepseek:
  models:
    deepseek-chat:  # DeepSeek-V3.2
      input_cache_hit: $0.028   # 90% discount on repeated prompts
      input_cache_miss: $0.28
      output: $0.42
      context: 128K
    deepseek-reasoner:  # Thinking mode
      input_cache_hit: $0.028
      input_cache_miss: $0.28
      output: $0.42
      context: 128K

  cost_comparison:
    vs_gpt4o_input: "10-100x cheaper"
    vs_gpt4o_output: "24x cheaper"
    vs_claude_sonnet: "10-100x cheaper"

  verdict: "ADD for --cheap mode - 96% cost savings with comparable quality"
  source: "https://api-docs.deepseek.com/quick_start/pricing"
```

### ADD: Groq (breaking_news mode)

```yaml
groq:
  models:
    llama-4-scout:
      input: $0.11
      output: $0.34
      speed: "594 tokens/sec"
    llama-4-maverick:
      input: $0.20
      output: $0.60
      speed: "562 tokens/sec"
    llama-3.3-70b-versatile:
      input: $0.59
      output: $0.79
      speed: "394 tokens/sec"
    llama-3.1-8b-instant:
      input: $0.05
      output: $0.08
      speed: "840 tokens/sec"

  batch_api: "50% discount on all models"

  built_in_tools:
    basic_search: $5/1k requests
    advanced_search: $8/1k requests
    visit_website: $1/1k requests

  whisper_transcription:
    whisper_large_v3: $0.111/hour
    whisper_turbo: $0.04/hour  # 228x realtime speed

  verdict: "ADD for breaking_news mode - 5-10x faster inference, very cheap"
  source: "https://groq.com/pricing"
```

### ADD: Anthropic Claude (quality mode)

```yaml
anthropic:
  models:
    claude-sonnet-4.5:
      input: $3.00
      output: $15.00
      context: 200K (long context: $6/$22.50)
    claude-sonnet-4:
      input: $3.00
      output: $15.00
    claude-haiku:
      input: $0.25
      output: $1.25

  batch_api: "50% discount"
  prompt_caching: "Up to 90% discount on repeated inputs"

  verdict: "ADD for quality documentary synthesis - Superior instruction following"
  source: "https://www.anthropic.com/pricing"
```

### Updated LLM Configuration

```yaml
llm_provider_matrix:
  modes:
    quick:
      default: deepseek-chat
      quality_override: claude-sonnet-4.5

    breaking_news:
      default: groq/llama-4-scout  # Speed priority
      fallback: deepseek-chat

    full:
      default: claude-sonnet-4.5
      cheap_override: deepseek-chat

    investigation:
      default: claude-sonnet-4.5
      cheap_override: deepseek-chat

    profile:
      default: claude-sonnet-4.5
      cheap_override: deepseek-chat

    controversy:
      default: claude-sonnet-4.5
      cheap_override: deepseek-chat

  cheap_flag:
    behavior: "Forces DeepSeek for ALL LLM calls"
    savings: "~96% vs GPT-4o, ~95% vs Claude"

  fallback_chain:
    primary_down: "Switch to DeepSeek"
    groq_down: "Switch to DeepSeek for breaking mode"
    all_down: "Return packet without synthesis"
```

---

## 16.5 Validation APIs - Validated Pricing

### ClaimBuster (KEEP)

```yaml
claimbuster:
  pricing: "FREE (API key registration required)"
  capabilities:
    - claim_scoring
    - fact_check_matching
    - claim_similarity

  verdict: "KEEP - FREE, filters 40-60% of claims before paid validation"
  source: "https://idir.uta.edu/claimbuster/api/"
```

### Google Fact Check Tools (KEEP)

```yaml
google_factcheck:
  pricing: "FREE (standard GCP API)"
  capabilities:
    - claim_search
    - existing_factcheck_lookup

  verdict: "KEEP - FREE, queries existing fact-checks from trusted orgs"
  source: "https://developers.google.com/fact-check/tools/api"
```

### Perplexity (KEEP for final validation)

```yaml
perplexity_validation:
  pricing:
    sonar: $5-12/1k requests (varies by depth)
    sonar_pro: $6-14/1k requests
    tokens: $1-3 input, $1-15 output per 1M

  verdict: "KEEP for FINAL validation only - Use after free APIs filter claims"
  source: "https://docs.perplexity.ai/getting-started/pricing"
```

### Validation Chain (Unchanged - Already Optimal)

```yaml
validation_chain:
  order:
    1: claimbuster        # FREE - Score and filter claims
    2: google_factcheck   # FREE - Find existing fact-checks
    3: perplexity         # PAID - Only for remaining unverified

  cost_optimization: |
    ClaimBuster filters 40-60% of claims as not check-worthy.
    Google Fact Check finds existing checks for 10-20% more.
    Only 20-50% of claims reach Perplexity (paid).
```

---

## 16.6 Deep Research APIs - Emerging Options

### Gemini Deep Research (EVALUATE)

```yaml
gemini_deep_research:
  pricing:
    input: $2.00/million tokens

  access: "Interactions API (public beta)"
  agent: "deep-research-pro-preview-12-2025"

  benchmarks:
    humanitys_last_exam: "46.4%"
    deep_search_qa: "66.1%"
    browse_comp: "59.2%"

  verdict: "EVALUATE - Very cheap for agent-based research, could simplify architecture"
  source: "https://ai.google.dev/gemini-api/docs/deep-research"
```

### Exa Research API (EVALUATE)

```yaml
exa_research:
  pricing:
    exa_research:
      search: $5/1k queries
      page_reads: $5/1k pages
      reasoning: $5/1M tokens
    exa_research_pro:
      search: $5/1k queries
      page_reads: $10/1k pages
      reasoning: $5/1M tokens

  completion_times:
    exa_research: "p50 ~45s, p90 ~90s"
    exa_research_pro: "p50 ~90s, p90 ~180s"

  verdict: "EVALUATE - Good for complex research tasks, async operation"
  source: "https://docs.exa.ai/reference/exa-research"
```

### Parallel.ai (EVALUATE for accuracy-critical)

```yaml
parallel:
  pricing:
    search_core: $25/1k requests (77% accuracy)
    search_base: $10/1k requests (75% accuracy)
    search_lite: $5/1k requests (64% accuracy)
    task_api: $5-2,400/1k requests (varies by tier)

  accuracy:
    browse_comp: "48% (highest available)"

  verdict: "EVALUATE - Only if accuracy issues arise with current stack"
  source: "https://parallel.ai/pricing"
```

---

## 16.7 Cost Projections

### Per-Job Cost Comparison

```yaml
investigation_mode_costs:
  current_implementation:
    search_15_queries: $0.30
    extraction_20_urls: $0.10
    transcription_5_videos: $0.30
    llm_planning: $0.50
    llm_synthesis: $1.00
    llm_narrative: $0.80
    validation: $0.20
    total: $3.20

  optimized_implementation:
    search_15_queries: $0.15      # Tavily optimized
    extraction_20_urls: $0.02     # Jina Reader FREE
    transcription_5_videos: $0.30 # Unchanged
    llm_planning: $0.05           # DeepSeek
    llm_synthesis: $0.10          # DeepSeek
    llm_narrative: $0.08          # DeepSeek
    validation: $0.05             # Free tiers first
    total: $0.75

  savings: "77%"
```

### Monthly Projections (100 jobs/month)

```yaml
monthly_costs:
  current:
    investigation_50_jobs: $160.00
    full_30_jobs: $30.00
    quick_20_jobs: $6.00
    total: $196.00

  optimized:
    investigation_50_jobs: $37.50
    full_30_jobs: $12.00
    quick_20_jobs: $2.00
    total: $51.50

  monthly_savings: $144.50
  annual_savings: $1,734.00
```

---

## 16.8 Implementation Priority

### HIGH PRIORITY (Implement Now)

```yaml
high_priority:
  1_transcription_chain_update:
    change: "Reorder to Supadata → Whisper → youtube-api → Manual"
    effort: "Low"
    impact: "High (reliability)"
    reason: "Cloud IP blocking mitigation"

  2_add_deepseek:
    change: "Add DeepSeek V3 for --cheap mode"
    effort: "Medium"
    impact: "Very High (96% cost savings)"
    reason: "Comparable quality at fraction of cost"

  3_promote_jina_reader:
    change: "Use Jina Reader as primary extraction"
    effort: "Low"
    impact: "Medium (cost savings)"
    reason: "FREE tier is generous"

  4_manual_fallback:
    change: "Add graceful failure with manual instructions"
    effort: "Low"
    impact: "High (UX)"
    reason: "Users always get something actionable"
```

### MEDIUM PRIORITY (Next Phase)

```yaml
medium_priority:
  5_add_groq:
    change: "Add Groq Llama for breaking_news mode"
    effort: "Medium"
    impact: "High (5-10x faster)"
    reason: "Speed-critical mode needs fast inference"

  6_add_claude:
    change: "Add Claude Sonnet 4.5 for quality mode"
    effort: "Medium"
    impact: "Medium (quality improvement)"
    reason: "Superior documentary synthesis"

  7_quality_gate:
    change: "Implement full Quality Gate from PRD v4.3"
    effort: "High"
    impact: "High (cost + quality)"
    reason: "Deterministic filtering saves extraction costs"
```

### CONSIDER (Future Evaluation)

```yaml
future_evaluation:
  8_gemini_deep_research:
    change: "Evaluate as alternative research pipeline"
    effort: "High"
    impact: "Uncertain"
    reason: "$2/M tokens is very competitive"

  9_parallel_ai:
    change: "Evaluate for accuracy-critical research"
    effort: "High"
    impact: "Quality for edge cases"
    reason: "Highest accuracy (48% on BrowseComp)"
```

---

## 16.9 Environment Variables (Updated)

```bash
# === SEARCH SERVICES ===
TAVILY_API_KEY=xxx                    # PRIMARY search + extraction
EXA_API_KEY=xxx                       # Secondary semantic search
BRAVE_SEARCH_API_KEY=xxx              # Tertiary fallback

# === EXTRACTION SERVICES ===
JINA_AI_READER_API_KEY=xxx            # PRIMARY extraction (optional - free without)

# === TRANSCRIPTION SERVICES ===
SUPADATA_API_KEY=xxx                  # PRIMARY transcription
OPENAI_API_KEY=xxx                    # SECONDARY (Whisper) + legacy LLM

# === LLM SERVICES (NEW) ===
ANTHROPIC_API_KEY=xxx                 # Claude Sonnet 4.5 (quality mode)
DEEPSEEK_API_KEY=xxx                  # DeepSeek V3 (--cheap mode)
GROQ_API_KEY=xxx                      # Groq Llama (breaking_news mode)
GROQ_MODEL=llama-4-scout              # Configurable Groq model

# === VALIDATION SERVICES ===
CLAIMBUSTER_API_KEY=xxx               # FREE claim scoring
# Google Fact Check uses YOUTUBE_API_KEY (reused)

# === FEATURE FLAGS ===
ENABLE_CHEAP_MODE=true                # Allow --cheap flag
ENABLE_QUALITY_MODE=true              # Allow quality LLM selection
DEFAULT_LLM_PROVIDER=deepseek         # Default: cheapest option
```

---

## 16.10 API Comparison Matrix

| Category | Tool | Cost | Speed | Accuracy | Cloud-Friendly | Verdict |
|----------|------|------|-------|----------|----------------|---------|
| **Search** | Tavily | $0.008/credit | Fast | High | ✅ | PRIMARY |
| **Search** | Exa.ai | $5/1k | Fast | 94.9% | ✅ | SEMANTIC |
| **Search** | Brave | $0.003/query | Fast | ~80% | ✅ | FALLBACK |
| **Extract** | Jina Reader | FREE | 2-3s | High | ✅ | PRIMARY |
| **Extract** | Tavily Extract | 1-2 credits/5 URLs | Fast | High | ✅ | BATCH |
| **Transcript** | Supadata | 1-2 credits | Medium | High | ✅ | PRIMARY |
| **Transcript** | Whisper | $0.006/min | Medium | High | ✅ | SECONDARY |
| **Transcript** | youtube-api | FREE | Fast | Medium | ❌ | TERTIARY |
| **LLM** | DeepSeek | $0.028-0.28 input | Medium | High | ✅ | CHEAP MODE |
| **LLM** | Groq Llama | $0.11-0.59 input | **594 TPS** | High | ✅ | SPEED MODE |
| **LLM** | Claude 4.5 | $3 input | Medium | **Best** | ✅ | QUALITY MODE |
| **LLM** | GPT-4o | $2.50 input | Medium | High | ✅ | LEGACY |
| **Validation** | ClaimBuster | FREE | Fast | Good | ✅ | FILTER |
| **Validation** | Google FC | FREE | Fast | N/A | ✅ | LOOKUP |
| **Validation** | Perplexity | $5-14/1k | Medium | 85.8% | ✅ | FINAL |

---

*End of Part 16: Validated API Recommendations*

---

# Part 17: Architecture Recommendations (December 2025)

> **Research Date:** December 24, 2025
> **Sources:** Anthropic Engineering, Google Developers Blog, Industry Best Practices
> **Purpose:** Validated architectural patterns for building a production-ready research agent

---

## 17.1 Current Architecture Validation

The existing Celery + Redis + FastAPI architecture aligns with industry best practices:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   FastAPI       │────▶│     Redis       │────▶│   Celery        │
│   (API Layer)   │     │   (Broker)      │     │   (Worker)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                           ┌─────────────────┐
│   Supabase      │                           │   10-Stage      │
│   (State/Auth)  │                           │   Pipeline      │
└─────────────────┘                           └─────────────────┘
```

```yaml
architecture_validation:
  verdict: "CORRECT - Do not replace"

  reasons:
    async_essential: "AI agents involve slow tasks (scraping, API calls, model chaining)"
    redis_speed: "Sub-millisecond task queuing and retrieval"
    celery_features: "Built-in retry logic, error handling, distributed execution"
    supabase_value: "Persistent state + authentication + real-time updates"

  industry_alignment:
    - "Redis and Celery offer a robust, scalable solution for agentic workflows"
    - "Modern applications increasingly rely on agentic workflows that autonomously execute complex tasks"
    - "Full-stack apps need instant responses while heavy lifting happens in background"

  source: "https://medium.com/@nimetha.21/scaling-agentic-workflows-with-redis-and-celery"
```

---

## 17.2 Lead Agent + Subagent Pattern (Anthropic Research System)

Based on Anthropic's production multi-agent research system that achieved 90.2% performance improvement:

```yaml
anthropic_pattern:
  name: "Orchestrator-Worker (Lead Agent + Subagents)"
  source: "https://www.anthropic.com/engineering/multi-agent-research-system"

  lead_agent:
    role: "LeadResearcher"
    responsibilities:
      - "Analyze incoming queries and develop research strategies"
      - "Create specialized subagents for parallel exploration"
      - "Synthesize findings and decide if additional research needed"
      - "Use extended thinking to plan approaches"
      - "Save plans to external memory when approaching 200K token limit"

  subagents:
    web_search_agent:
      focus: "Web articles, news, academic papers"
      tools: [tavily_search, exa_search, brave_search]

    video_agent:
      focus: "YouTube, TikTok, Instagram transcripts"
      tools: [supadata_transcript, whisper_transcribe, youtube_enumerate]

    discussion_agent:
      focus: "Reddit threads, forum discussions, comments"
      tools: [reddit_search, web_capture]

    validation_agent:
      focus: "Fact-checking, claim verification, evidence gathering"
      tools: [claimbuster_score, google_factcheck, perplexity_validate]

  subagent_design_requirements:
    - "Specific objective clearly defined"
    - "Output format specified"
    - "Tool guidance provided"
    - "Task boundaries explicit to prevent duplication"
```

### Scaling Rules (Critical)

```yaml
scaling_rules:
  description: "Anthropic found early agents spawned 50 subagents for simple queries"

  rules:
    simple_factcheck:
      agents: 1
      tool_calls: "3-10"
      example: "What year was X founded?"

    comparison_task:
      agents: "2-4"
      tool_calls_each: "10-15"
      example: "Compare company A vs company B"

    complex_investigation:
      agents: "10+"
      tool_calls_each: "15-30"
      division: "Clearly divided responsibilities"
      example: "Full investigation into controversy X"

  mapping_to_modes:
    quick: "simple_factcheck rules"
    full: "comparison_task rules"
    breaking_news: "simple_factcheck rules (speed priority)"
    investigation: "complex_investigation rules"
    profile: "comparison_task rules"
    controversy: "complex_investigation rules"
```

---

## 17.3 Parallelization Strategy (Up to 90% Time Reduction)

Anthropic achieved dramatic performance improvements through parallelization:

```yaml
parallelization_types:
  1_multi_subagent:
    description: "Lead agents spawn 3-5 subagents in parallel"
    implementation: "Celery group()"

  2_multi_tool:
    description: "Subagents invoke 3+ tools simultaneously"
    implementation: "asyncio.gather() within Celery task"

current_pipeline:  # Sequential
  stages:
    - planning: "5 min"
    - discovery: "3 min"
    - extraction: "4 min"
    - transcription: "5 min"
    - synthesis: "3 min"
  total: "20 min"

optimized_pipeline:  # Parallel
  phase_1_planning: "5 min (sequential - required first)"
  phase_2_discovery:  # PARALLEL
    web_search_agent: "3 min"
    video_agent: "5 min"  # Longest determines phase time
    discussion_agent: "2 min"
  phase_3_synthesis: "3 min (sequential - requires all inputs)"
  total: "13 min"
  improvement: "35% faster"

implementation_pattern:
  code: |
    from celery import group

    @celery_app.task
    def run_research_job(job_id, topic):
        # Phase 1: Planning (sequential - must complete first)
        config = plan_job(topic)

        # Phase 2: Discovery (PARALLEL)
        discovery_group = group(
            web_search_agent.s(topic, config),
            video_agent.s(topic, config),
            discussion_agent.s(topic, config),
        )
        results = discovery_group.apply_async().get()

        # Phase 3: Synthesis (sequential - needs all results)
        return synthesize_findings(results)
```

---

## 17.4 Context Management for Long Research

From Anthropic: "Agents summarize completed work phases and store essential information in external memory."

```yaml
context_management:
  problem: "200K token limit easily exceeded in complex research"

  solution_external_memory:
    storage: "Redis (fast) or Supabase (persistent)"
    store:
      - research_plan
      - completed_phases
      - key_findings_summary
      - source_citations
      - entity_relationships

  solution_subagent_compression:
    description: "Each subagent may use 10K-50K tokens internally"
    returns: "Condensed summary of 1,000-2,000 tokens"
    benefit: "Lead agent stays within context limits"

  solution_handoff_pattern:
    trigger: "Approaching context limit (e.g., 180K tokens)"
    action: "Spawn fresh subagent with memory retrieval"
    preserves: "Plans and prior findings from external memory"

  implementation:
    redis_keys:
      job_plan: "job:{job_id}:plan"
      job_memory: "job:{job_id}:memory"
      job_findings: "job:{job_id}:findings"

    memory_schema:
      plan: |
        {
          "objective": "string",
          "strategy": "string",
          "phases_completed": ["phase1", "phase2"],
          "key_findings": ["finding1", "finding2"],
          "next_steps": ["step1", "step2"]
        }
```

---

## 17.5 Error Handling and Graceful Degradation

From Anthropic: "One step failing can cause agents to explore entirely different trajectories."

```yaml
error_handling:
  principle: "Combination of AI adaptability with deterministic safeguards"

  strategies:
    retry_with_backoff:
      api_failures:
        max_retries: 3
        backoff: "exponential (1s, 2s, 4s)"

    circuit_breaker:
      trigger: "5 consecutive failures for source type"
      action: "Skip that source type for remainder of job"
      fallback: "Use cached/alternative data if available"

    graceful_degradation:
      transcription_fails:
        action: "Keep video links in packet"
        provide: "Manual extraction instructions"

      search_fails:
        action: "Fall back to cached results"
        alternative: "Use simpler/broader queries"

      llm_fails:
        action: "Return raw data without synthesis"
        note: "Packet still valuable for manual review"

    checkpoint_recovery:
      description: "Resume from last successful stage"
      implementation: "Store stage completion status in Supabase"
      benefit: "Avoid re-running expensive completed stages"

  agent_intelligence:
    description: "Let agents adapt when tools fail"
    example: "If Tavily fails, agent autonomously tries Exa"
    implementation: "Include fallback guidance in tool descriptions"
```

---

## 17.6 Tool Design Principles

From Anthropic: "Bad tool descriptions cause failures. A tool-testing agent reduced task completion time by 40%."

```yaml
tool_design:
  principle_1_distinct_purpose:
    bad_example:
      name: "search_web"
      description: "Searches the web"

    good_example:
      name: "search_news"
      description: |
        Searches recent news articles from the last 7 days.
        Best for: Breaking stories, current events, recent developments.
        Returns: Title, URL, snippet, publication date, source name.
        Limit: Max 10 results per query.

  principle_2_explicit_heuristics:
    example: |
      ## Tool Selection Guide

      Use tavily_search for:
      - General web content and articles
      - News and current events
      - Product/company information

      Use exa_search for:
      - Academic papers and research
      - Semantic/conceptual queries ("papers similar to X")
      - Finding authoritative sources on technical topics

      Use reddit_search for:
      - Community discussions and opinions
      - Controversy and debate perspectives
      - Real user experiences and reviews

  principle_3_clear_output_format:
    example: |
      Returns: List[SourceItem]
      Each item contains:
        - url: str (full URL)
        - title: str (page title)
        - snippet: str (first 500 chars of relevant content)
        - source_type: Enum[WEB, NEWS, ACADEMIC, DISCUSSION]
        - published_date: Optional[datetime]
        - credibility_score: Optional[float] (0-1)

  principle_4_failure_guidance:
    example: |
      If this tool fails or returns no results:
      1. Try broadening the search query
      2. Fall back to tavily_search with same query
      3. If all searches fail, note the gap in findings
```

---

## 17.7 Token Economics

From Anthropic: "Multi-agent systems work mainly because they help spend enough tokens to solve the problem."

```yaml
token_economics:
  baseline_comparison:
    chat_interaction: "1x tokens"
    single_agent: "4x tokens"
    multi_agent: "15x tokens"

  key_insight: "Token usage explains 80% of the variance in evaluation performance"

  economic_viability:
    rule: "Multi-agent systems require tasks where value justifies 15x token overhead"

    viable_modes:
      investigation: "High-value task, justifies full token spend"
      controversy: "High-value task, justifies full token spend"
      profile: "Medium-value, use subagent compression"

    cost_sensitive_modes:
      quick: "Use single agent, minimize token spend"
      breaking_news: "Speed priority, use fast models (Groq)"

  optimization_strategies:
    subagent_compression:
      internal_usage: "10K-50K tokens per subagent"
      returned_summary: "1K-2K tokens"
      savings: "80-95% token reduction in lead agent context"

    cheap_mode_flag:
      description: "Force DeepSeek for all LLM calls"
      token_cost: "10-100x cheaper than GPT-4o"
      use_case: "Budget-conscious users, bulk processing"
```

---

## 17.8 Framework Decision: Stay Custom

Based on comprehensive framework comparison:

```yaml
framework_comparison:
  langgraph:
    pros:
      - "Fine-grained control over state in DAG"
      - "Good for stateful workflows"
      - "Vendor-agnostic (works with any LLM)"
    cons:
      - "Fast-evolving codebase causes instability"
      - "5 layers of abstraction to customize behavior"
      - "Broken tutorials after updates"
      - "Learning curve significant"
    verdict: "Great for starting from scratch, not for migration"

  crewai:
    pros:
      - "Team semantics out-of-the-box"
      - "Less graph plumbing"
    cons:
      - "Built-in autonomous deliberation adds latency"
      - "Less control than custom pipeline"
    verdict: "Good for simple multi-agent, overkill for your use case"

  autogen:
    pros:
      - "Rich multi-agent conversations"
      - "Modular LLM backends"
    cons:
      - "Research-focused, less production-ready"
      - "Moderate performance"
    verdict: "Better for prototyping than production"

  custom_celery_pipeline:
    pros:
      - "Already built and working"
      - "Direct control, no abstraction overhead"
      - "Efficient Celery task distribution"
      - "Familiar codebase"
    cons:
      - "Must implement patterns manually"
      - "No built-in graph visualization"
    verdict: "KEEP - Apply Anthropic patterns within existing architecture"

decision: |
  Do NOT migrate to LangGraph or other frameworks.
  Instead: Apply Anthropic's patterns (parallelization, subagents, memory)
  within the existing Celery architecture.

  Reason: "The most successful implementations use simple, composable patterns
  rather than complex frameworks." - Anthropic
```

---

## 17.9 Evolution Roadmap

### Phase 1: Optimize Current Pipeline (Low Effort, High Impact)

```yaml
phase_1:
  priority: "HIGH"
  effort: "Low"
  impact: "High"

  changes:
    1_transcription_chain:
      action: "Reorder to Supadata → Whisper → youtube-api → Manual"
      reason: "Cloud IP blocking mitigation"

    2_manual_fallback:
      action: "Add graceful failure with user instructions"
      reason: "Guarantee 1: Always deliver something"

    3_deepseek_integration:
      action: "Add DeepSeek V3 for --cheap mode"
      reason: "96% cost savings"

    4_jina_promotion:
      action: "Use Jina Reader as primary extraction"
      reason: "FREE tier saves cost"

    5_budget_guard:
      action: "Add budget_guard() before every API call"
      reason: "Prevent cost overruns"
```

### Phase 2: Add Parallelization (Medium Effort, High Impact)

```yaml
phase_2:
  priority: "MEDIUM"
  effort: "Medium"
  impact: "High (up to 35% faster)"

  changes:
    1_parallel_discovery:
      action: "Run web + video + discussion agents simultaneously"
      implementation: "Celery group()"

    2_parallel_extraction:
      action: "Batch URLs to Jina/Tavily in parallel"
      implementation: "asyncio.gather() or Celery group()"

    3_parallel_validation:
      action: "Validate multiple claims simultaneously"
      implementation: "Celery group() with rate limiting"

    4_groq_integration:
      action: "Add Groq Llama for breaking_news mode"
      reason: "5-10x faster inference"
```

### Phase 3: Subagent Architecture (Higher Effort, Transformative)

```yaml
phase_3:
  priority: "FUTURE"
  effort: "High"
  impact: "Transformative (90%+ improvement on complex tasks)"

  changes:
    1_lead_agent_refactor:
      action: "Refactor worker.py into LeadResearcher agent"
      components:
        - query_analyzer
        - strategy_planner
        - subagent_spawner
        - result_synthesizer

    2_specialized_subagents:
      action: "Create dedicated subagent modules"
      agents:
        - WebSearchAgent
        - VideoAgent
        - DiscussionAgent
        - ValidationAgent

    3_external_memory:
      action: "Add Redis-based working memory"
      stores:
        - research_plan
        - completed_phases
        - key_findings
        - entity_graph

    4_scaling_rules:
      action: "Implement dynamic scaling based on query complexity"
      logic: "Simple queries get 1 agent, complex get 10+"

    5_inter_agent_coordination:
      action: "Enable subagents to share findings mid-execution"
      benefit: "Avoid duplicate work, fill gaps dynamically"
```

---

## 17.10 MCP Server Configuration

Tavily MCP server has been added to enable enhanced search capabilities:

```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp"
    },
    "tavily": {
      "command": "npx",
      "args": ["-y", "@tavily/mcp@latest"],
      "env": {
        "TAVILY_API_KEY": "${TAVILY_API_KEY}"
      }
    }
  }
}
```

```yaml
tavily_mcp_tools:
  tavily-search:
    description: "Performs real-time web searches with filtering options"
    parameters:
      query: "Search terms (required)"
      search_depth: "basic | advanced"
      topic: "general | news"
      max_results: "Number of results"
      domain_filter: "Restrict to specific domains"

  tavily-extract:
    description: "Extracts and processes content from URLs"
    parameters:
      url: "Target webpage (required)"

  usage_pattern: |
    Combined for comprehensive research:
    1. Search for relevant articles
    2. Extract full content from top results
    3. Process with LLM for synthesis
```

---

## 17.11 References

```yaml
primary_sources:
  anthropic_multi_agent:
    title: "How we built our multi-agent research system"
    url: "https://www.anthropic.com/engineering/multi-agent-research-system"
    authors: ["Jeremy Hadfield", "Barry Zhang", "Kenneth Lien", "Florian Scholz"]

  anthropic_effective_agents:
    title: "Building Effective AI Agents"
    url: "https://www.anthropic.com/research/building-effective-agents"

  google_multi_agent:
    title: "Architecting efficient context-aware multi-agent framework for production"
    url: "https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/"

  celery_redis_scaling:
    title: "Scaling Agentic Workflows with Redis and Celery"
    url: "https://medium.com/@nimetha.21/scaling-agentic-workflows-with-redis-and-celery"

  framework_comparison:
    title: "Best AI Agent Frameworks in 2025"
    url: "https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025"

  langgraph_alternatives:
    title: "We Tested 8 LangGraph Alternatives for Scalable Agent Orchestration"
    url: "https://www.zenml.io/blog/langgraph-alternatives"

  tavily_mcp:
    title: "Tavily MCP Server Documentation"
    url: "https://docs.tavily.com/documentation/mcp"

key_insights:
  - "Multi-agent systems work mainly because they help spend enough tokens to solve the problem"
  - "Token usage alone explains 80% of the variance in evaluation performance"
  - "The most successful implementations use simple, composable patterns rather than complex frameworks"
  - "One step failing can cause agents to explore entirely different trajectories"
  - "A tool-testing agent reduced task completion time by 40%"
  - "Up to 90% research time reduction achieved through parallelization"
```

---

*End of Part 17: Architecture Recommendations*

---

*End of Complete Implementation Specification v4.3*
