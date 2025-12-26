> **ARCHIVED:** This document has been superseded by PRD v6.0 (December 2024).
> See `Active Docs/PRD_v6.md` for the current authoritative specification.
>
> **Archive Reason:** Research validation found several claims in this document that did not match the actual implementation (DeepSeek V3 not implemented, 7 genre modes not implemented, cost tracking not implemented).

---

# Research Agent v5.0
## NotebookLM-First Research Gatherer with Documentary Intelligence

> **Version**: 5.0 (Complete Rewrite)
> **Purpose**: Gather comprehensive research from web and video sources, format for NotebookLM, and provide AI-generated documentary angles
> **Core Principle**: Gather. Organize. Don't Modify. The research stays untouched—AI analysis is separate.

---

## What This Tool Does

```
INPUT: Topic + Genre Mode

PROCESS:
1. Search the web intelligently (understands context, semantics, nuance)
2. Search YouTube for relevant videos
3. Search Reddit for discussions and firsthand accounts
4. Extract full content from web sources (unmodified)
5. Extract transcripts from videos (unmodified)
6. Organize everything for NotebookLM consumption
7. Generate Documentary Intelligence (AI analysis - separate document)

OUTPUT:
├── Research Packet (Google Doc)
│   └── Organized sources with full text, ready for NotebookLM
├── Documentary Intelligence (Google Doc)
│   └── AI-generated angles, themes, narrative suggestions
└── YouTube URLs List
    └── For direct import into NotebookLM
```

---

## What This Tool Does NOT Do

- ❌ Modify, rewrite, or summarize research content
- ❌ Replace your analysis (NotebookLM does that)
- ❌ Generate scripts or narratives from research
- ❌ Make editorial decisions about what's important
- ❌ Filter out "unimportant" sources (you decide what matters)

---

# Part 1: Core Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RESEARCH GATHERER                                │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     INTELLIGENT QUERY GENERATION                 │    │
│  │   • Understands topic context and nuance                        │    │
│  │   • Generates semantically diverse search queries               │    │
│  │   • Adapts queries based on genre mode                          │    │
│  │   • Captures different angles and perspectives                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         DISCOVERY                                │    │
│  │                                                                  │    │
│  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │    │
│  │   │ Tavily  │ │  GDELT  │ │Semantic │ │ YouTube │ │  PRAW   │  │    │
│  │   │  (web)  │ │ (news)  │ │ Scholar │ │ (video) │ │(Reddit) │  │    │
│  │   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        EXTRACTION                                │    │
│  │                                                                  │    │
│  │   ┌──────────────────┐        ┌──────────────────┐              │    │
│  │   │   Jina Reader    │        │    Supadata      │              │    │
│  │   │   (web → text)   │        │ (video → text)   │              │    │
│  │   │      FREE        │        │  (multi-platform)│              │    │
│  │   └──────────────────┘        └──────────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   ORGANIZE FOR NOTEBOOKLM                        │    │
│  │   • Group by source type                                         │    │
│  │   • Format with clear attribution                                │    │
│  │   • Preserve original content exactly                            │    │
│  │   • Use Google Docs tabs for efficient source count              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  OUTPUT 1: Research Packet (Google Doc with tabs)                       │
│  OUTPUT 2: YouTube URLs (for direct NotebookLM import)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DOCUMENTARY INTELLIGENCE                             │
│                     (Separate AI Analysis Layer)                         │
│                                                                          │
│   • Suggested angles and approaches                                     │
│   • Key themes and patterns identified                                  │
│   • Potential narrative structures                                      │
│   • Questions worth exploring                                           │
│   • Contradictions or controversies spotted                             │
│   • Missing perspectives to investigate                                 │
│                                                                          │
│   OUTPUT 3: Documentary Intelligence (Separate Google Doc)              │
│                                                                          │
│   ⚠️ CLEARLY LABELED AS AI ANALYSIS - NOT RESEARCH                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Request
    │
    ├── Topic: "MrBeast CryptoZoo scandal"
    ├── Mode: downfalls
    └── Options: (depth, etc.)
    │
    ▼
┌─────────────────┐
│  Query Gen LLM  │──► Generates 15-25 intelligent search queries
└─────────────────┘    tailored to topic + mode
    │
    ▼
┌─────────────────┐
│   DISCOVERY     │──► Parallel searches across all sources
│   (parallel)    │    YouTube prioritized, then web, news, Reddit
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   EXTRACTION    │──► Full content from each source
│   Jina + Supadata    UNMODIFIED - exactly as found
└─────────────────┘
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
┌─────────────────┐            ┌─────────────────┐
│ Research Packet │            │  Documentary    │
│ (Google Doc)    │            │  Intelligence   │
│                 │            │  (Google Doc)   │
│ • Web sources   │            │                 │
│ • Video trans.  │            │ • Angles        │
│ • Reddit threads│            │ • Themes        │
│ • News articles │            │ • Questions     │
│ • Academic      │            │ • Structures    │
│                 │            │                 │
│ UNMODIFIED      │            │ AI ANALYSIS     │
└─────────────────┘            └─────────────────┘
    │                                  │
    └──────────────┬───────────────────┘
                   ▼
            Google Drive Folder
            └── /Research/{topic}_{date}/
                ├── Research_Packet.gdoc
                ├── Documentary_Intelligence.gdoc
                └── YouTube_URLs.txt
```

---

# Part 2: Tool Stack

## Locked Technology Choices

| Function | Tool | Cost | Why This Tool |
|----------|------|------|---------------|
| **Web Search** | Tavily | ~$0.01/search | AI-native, reliable, good for RAG |
| **Web Extraction** | Jina Reader | FREE | Stable, scalable, clean markdown |
| **Video Transcripts** | Supadata | ~$0.01/video | Works on cloud, multi-platform |
| **News Discovery** | GDELT | FREE | Massive scale, global coverage |
| **Academic Search** | Semantic Scholar | FREE | 200M+ papers |
| **Video Discovery** | YouTube Data API | FREE tier | Official, reliable |
| **Reddit** | PRAW | FREE | Official API, you have access |
| **Query Generation** | DeepSeek V3 | ~$0.001/job | Cheap, good reasoning |
| **Documentary Intel** | DeepSeek V3 | ~$0.05/job | Cheap, good analysis |
| **Export** | Google Drive API | FREE | Direct to your Drive |
| **Backend** | FastAPI + Celery | - | Async job processing |
| **Database** | Supabase | FREE tier | Job tracking, user data |

## Tool Details

### Tavily (Web Search)
```yaml
tavily:
  purpose: Primary web search
  pricing: ~$0.01 per search credit
  features:
    - AI-native search optimized for LLM consumption
    - Returns snippets + URLs
    - Can filter by recency, domain, etc.
  usage:
    - 10-20 searches per job depending on mode
    - Estimated: $0.10-0.20 per job
```

### Jina Reader (Web Extraction)
```yaml
jina_reader:
  purpose: Extract clean text from any URL
  pricing: FREE (rate limited, sufficient for our use)
  usage: "Simply prepend https://r.jina.ai/ to any URL"
  features:
    - Returns clean markdown
    - Handles JavaScript-rendered pages
    - Strips ads, navigation, clutter
    - 2-3 second response time
  limits:
    - Rate limited but generous for our volume
    - No API key needed for basic usage
```

### Supadata (Video Transcription)
```yaml
supadata:
  purpose: Get transcripts from video platforms
  pricing: ~1-2 credits per transcript
  platforms:
    - YouTube (high reliability)
    - TikTok (medium reliability)
    - Instagram (medium reliability)
    - Twitter/X (medium reliability)
    - Facebook (medium reliability)
  fallback_chain:
    1. Supadata native transcript (if available)
    2. Supadata AI-generated transcript
    3. OpenAI Whisper (last resort)
  on_failure: "Keep video in packet as link, note failure reason"
```

### PRAW (Reddit)
```yaml
praw:
  purpose: Extract Reddit posts and comments
  pricing: FREE (official API)
  features:
    - Full thread extraction
    - Comment hierarchies preserved
    - User metadata available
  fallback:
    - If PRAW fails: Tavily search with "site:reddit.com"
    - If that fails: Note as "manual review needed"
  output: "Full thread text with attribution"
```

### GDELT (News)
```yaml
gdelt:
  purpose: News discovery (global, real-time)
  pricing: FREE
  scale: "100,000+ articles per day"
  features:
    - 65 languages
    - Configurable time windows
    - Entity extraction built-in
```

### DeepSeek V3 (LLM)
```yaml
deepseek:
  purpose: 
    - Query generation (understanding topic nuance)
    - Documentary Intelligence (analysis)
  pricing:
    input_cache_hit: $0.028 / 1M tokens
    input_cache_miss: $0.28 / 1M tokens
    output: $0.42 / 1M tokens
  why: "10-30x cheaper than Claude/GPT, comparable quality"
  note: "NOT used to modify research content"
```

## Cost Estimate Per Job

```yaml
standard_job:
  tavily_searches_15: $0.15
  jina_extractions_25: $0.00  # FREE
  supadata_transcripts_5: $0.05
  deepseek_query_gen: $0.02
  deepseek_documentary_intel: $0.08
  total: ~$0.30

comprehensive_job:
  tavily_searches_25: $0.25
  jina_extractions_40: $0.00
  supadata_transcripts_10: $0.10
  deepseek_query_gen: $0.03
  deepseek_documentary_intel: $0.12
  total: ~$0.50

monthly_projection:
  jobs_60: $18-30
  buffer: $10
  total: ~$30-40/month
  
  # Well under $120 budget
```

---

# Part 3: Genre Modes

## Why Modes?

Different topics require different research approaches:
- A **mystery/conspiracy** topic needs debunker content + believer content
- A **downfall/scandal** topic needs timeline + receipts + reactions
- A **profile** topic needs biographical info + interviews + opinions
- A **current affairs** topic needs breaking news + multiple perspectives

Modes tell the system **what kind of sources to prioritize** and **what angles to search**.

## Available Modes

### 1. GENERAL (Default)
```yaml
general:
  description: "Balanced research for topics that don't fit other modes"
  
  query_strategy:
    - "{topic} overview"
    - "{topic} explained"
    - "{topic} history"
    - "{topic} controversy" 
    - "{topic} facts"
    - "{topic} analysis"
    - "{topic} reddit"
    - "{topic} documentary"
  
  source_priorities:
    youtube: high      # Always prioritize video
    web: high
    news: medium
    reddit: medium
    academic: low
  
  min_sources:
    youtube: 5
    web: 10
    reddit: 3
    total: 25
```

### 2. MYSTERIES
```yaml
mysteries:
  description: "Conspiracies, unsolved cases, paranormal, ARGs, unexplained"
  inspired_by: "Why Files, Lemmino, Alex Bale"
  
  query_strategy:
    - "{topic} evidence"
    - "{topic} debunked"
    - "{topic} explained"
    - "{topic} believers vs skeptics"
    - "{topic} origin theory"
    - "{topic} documentary"
    - "{topic} investigation"
    - "{topic} reddit theories"
    - "{topic} scientific explanation"
  
  source_priorities:
    youtube: very_high  # Long-form docs are primary sources
    web: medium
    academic: high      # Debunker/scientific content
    reddit: high        # Community theories
    news: low
  
  min_sources:
    youtube: 8
    web: 8
    reddit: 5
    academic: 3
    total: 30
  
  documentary_intel_focus:
    - "Evidence FOR vs AGAINST structure"
    - "Origin of claims"
    - "Key figures on each side"
    - "What remains genuinely unexplained"
    - "Debunk status of major claims"
```

### 3. DOWNFALLS
```yaml
downfalls:
  description: "Scandals, controversies, public falls from grace, drama"
  inspired_by: "Internet Anarchist, Patrick CC, Coffeezilla"
  
  query_strategy:
    - "{topic} controversy timeline"
    - "{topic} scandal"
    - "{topic} allegations"
    - "{topic} response apology"
    - "{topic} exposed"
    - "{topic} receipts"
    - "{topic} reddit drama"
    - "{topic} victim statements"
    - "{topic} sponsor drop"
    - "{topic} documentary"
  
  source_priorities:
    youtube: very_high  # Video receipts are primary
    reddit: very_high   # Community reactions matter
    news: high          # Breaking coverage
    web: medium
    academic: none
  
  min_sources:
    youtube: 10
    reddit: 8
    news: 5
    web: 7
    total: 35
  
  documentary_intel_focus:
    - "Timeline of events"
    - "Key evidence/receipts"
    - "Public vs private statements"
    - "Community reaction phases"
    - "What's confirmed vs alleged vs disputed"
```

### 4. HISTORY_RELIGION
```yaml
history_religion:
  description: "Historical events, religious topics, ancient mysteries"
  inspired_by: "Historia Civilis, ReligionForBreakfast, Fall of Civilizations"
  
  query_strategy:
    - "{topic} history"
    - "{topic} origins"
    - "{topic} primary sources"
    - "{topic} scholarly analysis"
    - "{topic} documentary"
    - "{topic} debate controversy"
    - "{topic} timeline"
    - "{topic} archaeological evidence"
  
  source_priorities:
    youtube: high       # Educational docs
    academic: very_high # Primary & scholarly sources
    web: high           # Reference articles
    news: low
    reddit: low
  
  min_sources:
    youtube: 6
    academic: 8
    web: 10
    total: 30
  
  documentary_intel_focus:
    - "Primary source availability"
    - "Scholarly consensus vs debate"
    - "Timeline of key events"
    - "Different interpretations"
    - "Gaps in historical record"
```

### 5. POP_CULTURE
```yaml
pop_culture:
  description: "Entertainment, celebrities, viral moments, fandom"
  inspired_by: "Defunctland, Super Eyepatch Wolf"
  
  query_strategy:
    - "{topic} explained"
    - "{topic} behind the scenes"
    - "{topic} controversy"
    - "{topic} fan reaction"
    - "{topic} interview"
    - "{topic} documentary"
    - "{topic} reddit discussion"
    - "{topic} viral moment"
  
  source_priorities:
    youtube: very_high  # Clips, reactions, docs
    reddit: high        # Fan communities
    news: medium        # Entertainment news
    web: medium
    academic: none
  
  min_sources:
    youtube: 10
    reddit: 6
    news: 4
    web: 5
    total: 30
  
  documentary_intel_focus:
    - "Cultural impact"
    - "Fan vs critic perspectives"
    - "Behind-the-scenes context"
    - "Evolution over time"
    - "Controversies and responses"
```

### 6. CURRENT_AFFAIRS
```yaml
current_affairs:
  description: "Breaking news, politics, current events"
  inspired_by: "Johnny Harris, TLDR News"
  
  query_strategy:
    - "{topic} latest news"
    - "{topic} explained"
    - "{topic} analysis"
    - "{topic} different perspectives"
    - "{topic} timeline"
    - "{topic} stakeholders"
    - "{topic} reddit discussion"
    - "{topic} expert opinion"
  
  source_priorities:
    news: very_high     # Breaking coverage
    youtube: high       # Analysis videos
    web: high           # In-depth articles
    reddit: medium      # Public reaction
    academic: low
  
  min_sources:
    news: 12
    youtube: 6
    web: 8
    reddit: 4
    total: 35
  
  time_filter: "last 30 days prioritized"
  
  documentary_intel_focus:
    - "Multiple stakeholder perspectives"
    - "Timeline of events"
    - "What's confirmed vs developing"
    - "Expert vs public opinion"
    - "Potential future developments"
```

### 7. PROFILE
```yaml
profile:
  description: "Person-focused research, interview prep"
  
  query_strategy:
    - "{person} interview"
    - "{person} biography"
    - "{person} controversy"
    - "{person} quotes"
    - "{person} career timeline"
    - "{person} documentary"
    - "{person} reddit"
    - "{person} criticism"
    - "{person} achievements"
  
  source_priorities:
    youtube: very_high  # Interviews are gold
    web: high           # Profiles, articles
    news: high          # Coverage
    reddit: medium      # Public perception
    academic: low
  
  min_sources:
    youtube: 8          # Interviews prioritized
    web: 10
    news: 5
    reddit: 3
    total: 30
  
  documentary_intel_focus:
    - "Key biographical facts"
    - "Public persona vs private"
    - "Major controversies"
    - "Notable quotes and positions"
    - "Relationships and influences"
```

---

# Part 4: NotebookLM Optimization

## NotebookLM Constraints

Understanding these constraints is critical for output formatting:

```yaml
notebooklm_limits:
  sources_per_notebook: 50          # Free tier
  words_per_source: 500000          # Generous
  file_size: 200MB                  # Per source
  
  what_it_can_import:
    - Google Docs (including tabs)
    - PDFs
    - Text files
    - YouTube URLs (with captions)
    - Web URLs (text only, no paywalls)
  
  what_it_cannot_do:
    - Import images or embedded videos
    - Access paywalled content
    - Import YouTube videos without captions
  
  optimization_strategy:
    - Use Google Docs tabs to consolidate sources
    - Each tab = one logical source (article, thread, etc.)
    - This way, one Google Doc can contain 20+ sources
    - But counts as only 1 source in NotebookLM
```

## Research Packet Structure

The Research Packet is a single Google Doc optimized for NotebookLM:

```
Research Packet: {Topic}
Generated: {Date}
Mode: {Genre Mode}

═══════════════════════════════════════════════════════════════════

TAB 1: WEB SOURCES
───────────────────────────────────────────────────────────────────

## Source 1: {Title}
**URL:** {url}
**Published:** {date}
**Publisher:** {source_name}

{Full extracted text, unmodified}

---

## Source 2: {Title}
**URL:** {url}
**Published:** {date}
**Publisher:** {source_name}

{Full extracted text, unmodified}

---
[...continues for all web sources...]

═══════════════════════════════════════════════════════════════════

TAB 2: VIDEO TRANSCRIPTS
───────────────────────────────────────────────────────────────────

## Video 1: {Title}
**URL:** {youtube_url}
**Channel:** {channel_name}
**Published:** {date}
**Duration:** {duration}

{Full transcript, unmodified}

---

## Video 2: {Title}
[...continues...]

═══════════════════════════════════════════════════════════════════

TAB 3: REDDIT DISCUSSIONS
───────────────────────────────────────────────────────────────────

## Thread 1: {Post Title}
**URL:** {reddit_url}
**Subreddit:** r/{subreddit}
**Posted:** {date}
**Score:** {upvotes}

### Original Post:
{post_content}

### Top Comments:
**u/{username}** ({score} points):
{comment_text}

**u/{username}** ({score} points):
{comment_text}

[...continues with comment thread...]

---

## Thread 2: {Post Title}
[...continues...]

═══════════════════════════════════════════════════════════════════

TAB 4: NEWS ARTICLES
───────────────────────────────────────────────────────────────────

[Same format as web sources]

═══════════════════════════════════════════════════════════════════

TAB 5: ACADEMIC SOURCES
───────────────────────────────────────────────────────────────────

## Paper 1: {Title}
**URL:** {url}
**Authors:** {authors}
**Published:** {date}
**Journal/Source:** {journal}

### Abstract:
{abstract}

### Key Content:
{extracted_content if available}

---

═══════════════════════════════════════════════════════════════════

TAB 6: SOURCES WITH ISSUES
───────────────────────────────────────────────────────────────────

These sources were found but could not be fully extracted.
Manual review recommended.

## {Title}
**URL:** {url}
**Issue:** {reason - e.g., "Paywall detected", "Extraction failed"}
**Recommendation:** {how to access manually}

---
```

## YouTube URLs File

Separate file for direct NotebookLM import:

```
YouTube Videos for NotebookLM Import
Topic: {Topic}
Generated: {Date}

Instructions: You can import these URLs directly into NotebookLM.
NotebookLM will extract the transcripts automatically.

───────────────────────────────────────────────────────────────────

1. {Video Title}
   {youtube_url}
   Channel: {channel_name}
   Duration: {duration}

2. {Video Title}
   {youtube_url}
   Channel: {channel_name}
   Duration: {duration}

[...continues...]

───────────────────────────────────────────────────────────────────

Note: Videos without captions may not import successfully.
Full transcripts are also included in the Research Packet.
```

---

# Part 5: Documentary Intelligence

## What This Is

Documentary Intelligence is a **separate AI-generated analysis** that helps you find angles and approaches for your documentary. It is:

- ✅ Clearly labeled as AI analysis
- ✅ Based on the gathered research
- ✅ Meant to spark ideas, not replace your judgment
- ✅ A starting point for your own analysis in NotebookLM

## What This Is NOT

- ❌ A replacement for your analysis
- ❌ A script or narrative
- ❌ Modified research
- ❌ The "truth" about the topic

## Documentary Intelligence Structure

```
═══════════════════════════════════════════════════════════════════
DOCUMENTARY INTELLIGENCE REPORT
═══════════════════════════════════════════════════════════════════

Topic: {Topic}
Mode: {Genre Mode}
Generated: {Date}

⚠️ THIS IS AI-GENERATED ANALYSIS
   Use as a starting point. Verify everything in the research.
   Your judgment and NotebookLM analysis are the final authority.

═══════════════════════════════════════════════════════════════════

## 1. EXECUTIVE SUMMARY

{2-3 paragraph overview of what the research reveals about this topic.
What's the story here? What makes it interesting/significant?}

───────────────────────────────────────────────────────────────────

## 2. POTENTIAL ANGLES

These are different ways you could approach this topic:

### Angle A: {Title}
{Description of this angle and why it might work}
**Key sources that support this angle:** {list}

### Angle B: {Title}
{Description}
**Key sources:** {list}

### Angle C: {Title}
{Description}
**Key sources:** {list}

───────────────────────────────────────────────────────────────────

## 3. KEY THEMES IDENTIFIED

Patterns and themes that emerged across multiple sources:

1. **{Theme}**
   {Explanation}
   Appears in: {sources where this appears}

2. **{Theme}**
   {Explanation}
   Appears in: {sources}

3. **{Theme}**
   {Explanation}
   Appears in: {sources}

───────────────────────────────────────────────────────────────────

## 4. CONTRADICTIONS & CONTROVERSIES

Points where sources disagree or where there's active debate:

### Contradiction 1: {Topic}
- **Side A says:** {position}
  Sources: {list}
- **Side B says:** {position}
  Sources: {list}
- **Current status:** {resolved/ongoing/unclear}

### Contradiction 2: {Topic}
[...continues...]

───────────────────────────────────────────────────────────────────

## 5. QUESTIONS WORTH EXPLORING

Questions your documentary could investigate:

1. {Question}
   Why it matters: {explanation}
   
2. {Question}
   Why it matters: {explanation}

3. {Question}
   Why it matters: {explanation}

───────────────────────────────────────────────────────────────────

## 6. MISSING PERSPECTIVES

Viewpoints or sources we couldn't find that might be valuable:

- {Missing perspective}
  Suggestion: {how to find}

- {Missing perspective}
  Suggestion: {how to find}

───────────────────────────────────────────────────────────────────

## 7. NARRATIVE STRUCTURES

Ways you might structure this story:

### Structure A: Chronological
{How this would work}

### Structure B: Thematic
{How this would work}

### Structure C: {Other structure type}
{How this would work}

───────────────────────────────────────────────────────────────────

## 8. KEY FIGURES/ENTITIES

People, organizations, or entities central to this story:

| Name | Role | Relevance | Notable Sources |
|------|------|-----------|-----------------|
| {name} | {role} | {why they matter} | {sources} |
| {name} | {role} | {why they matter} | {sources} |

───────────────────────────────────────────────────────────────────

## 9. SUGGESTED TIMELINE

If applicable, key dates/events:

| Date | Event | Significance | Source |
|------|-------|--------------|--------|
| {date} | {event} | {why it matters} | {source} |
| {date} | {event} | {why it matters} | {source} |

═══════════════════════════════════════════════════════════════════

END OF DOCUMENTARY INTELLIGENCE REPORT

Remember: This analysis is generated by AI to help spark ideas.
Always verify against the original research in the Research Packet.

═══════════════════════════════════════════════════════════════════
```

---

# Part 6: Graceful Degradation

## The Golden Rule

**Something is always better than nothing.**

Every stage has fallbacks. Every failure is reported. The user always gets value.

## Degradation Hierarchy

```
IDEAL                    FALLBACK 1               FALLBACK 2               LAST RESORT
────────────────────────────────────────────────────────────────────────────────────────

Web Extraction:
Jina Reader          →   Tavily Extract       →   Firecrawl            →   URL + "Manual needed"
(free)                   (paid, batched)          (paid)                   (user extracts manually)

Video Transcripts:
Supadata native      →   Supadata AI          →   Whisper              →   URL + "Watch manually"
(fast, cheap)            (slower, reliable)       (slower, reliable)       (video still in packet)

Reddit:
PRAW full thread     →   PRAW top comments    →   Tavily site:reddit   →   URL + "Manual needed"
(complete)               (partial)                (search only)            (user reads thread)

YouTube Discovery:
YouTube API          →   Tavily video search  →   Manual suggestions   →   "Try searching: {queries}"
(official)               (web search)             (guidance)

News:
GDELT                →   Tavily news filter   →   General web search   →   "Check: {news sites}"
(free, massive)          (paid)                   (less targeted)

Query Generation:
LLM (DeepSeek)       →   Template queries     →   Basic variations     →   User's exact topic
(intelligent)            (pre-defined)            ("{topic}" + modifiers)

Documentary Intel:
LLM Analysis         →   Basic summary        →   Source list only     →   "Analysis unavailable"
(full report)            (abbreviated)            (no AI insights)         (packet still delivered)
```

## Error Reporting

Every failure goes into the output:

```yaml
# Included in Research Packet footer

EXTRACTION STATUS REPORT
═══════════════════════════════════════════════════════════════════

Successful Extractions:
- Web sources: 23/25 (92%)
- Video transcripts: 4/5 (80%)
- Reddit threads: 3/3 (100%)

Failed Extractions:
┌─────────────────────────────────────────────────────────────────┐
│ Source: "WSJ Article: The Scandal Unfolds"                       │
│ URL: https://wsj.com/article/...                                │
│ Issue: Paywall detected                                          │
│ Action: URL provided in "Sources with Issues" section           │
│ Manual fix: Access via library subscription or WSJ account      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Source: YouTube Video "Full Documentary"                         │
│ URL: https://youtube.com/watch?v=...                            │
│ Issue: No captions available, Supadata AI transcription failed  │
│ Action: Video listed in YouTube URLs file                       │
│ Manual fix: Watch video, take notes manually                    │
└─────────────────────────────────────────────────────────────────┘
```

---

# Part 7: System Prompts

## Query Generation Prompt

```
SYSTEM:
You are a research query generator for documentary production. Your job is to generate intelligent, diverse search queries that will find comprehensive sources on a topic.

CONTEXT:
- Topic: {topic}
- Genre Mode: {mode}
- Mode Description: {mode_description}

YOUR TASK:
Generate {query_count} search queries that will find:
1. Primary sources and firsthand accounts
2. Analysis and expert opinions
3. Different perspectives (supporters, critics, neutrals)
4. Historical context and background
5. Recent developments
6. Community discussions and reactions

IMPORTANT:
- Understand the NUANCE of the topic (sarcasm, controversy, emotion)
- Consider what a documentary filmmaker would actually need
- Include queries that find VIDEO content (YouTube prioritized)
- Include queries for Reddit discussions
- Vary specificity: some broad, some narrow
- Think about what angles might be MISSED by obvious searches

OUTPUT FORMAT:
Return a JSON array of queries with intent:
[
  {
    "query": "search query text",
    "intent": "what we're looking for",
    "platform_hint": "youtube|web|reddit|news|academic"
  }
]
```

## Documentary Intelligence Prompt

```
SYSTEM:
You are a documentary research analyst. You've been given a collection of sources about a topic. Your job is to analyze these sources and provide insights that will help a documentary filmmaker find angles, themes, and narrative structures.

CRITICAL RULES:
1. You are ANALYZING, not summarizing
2. Your output is SEPARATE from the research
3. Always cite which sources support your observations
4. Acknowledge uncertainty and gaps
5. Present multiple perspectives fairly
6. DO NOT make up information not in the sources

CONTEXT:
- Topic: {topic}
- Genre Mode: {mode}
- Number of sources analyzed: {count}

SOURCES:
{sources_content}

YOUR TASK:
Generate a Documentary Intelligence Report that includes:
1. Executive Summary (what's the story here?)
2. Potential Angles (different ways to approach this)
3. Key Themes (patterns across sources)
4. Contradictions & Controversies (where sources disagree)
5. Questions Worth Exploring (what should be investigated)
6. Missing Perspectives (what we couldn't find)
7. Narrative Structures (how to organize the story)
8. Key Figures (who matters and why)
9. Timeline (if applicable)

Be insightful but honest about limitations.
```

---

# Part 8: Web UI & Job Management

## Interface Requirements

```yaml
web_ui:
  framework: Next.js 14
  hosting: Vercel or similar
  auth: Supabase Auth
  
  pages:
    /: Dashboard (recent jobs, quick stats)
    /new: Create new research job
    /jobs/{id}: View job status and results
    /settings: API keys, preferences
    
  job_creation_form:
    fields:
      - topic: text (required)
      - mode: dropdown (general, mysteries, downfalls, etc.)
      - depth: slider (quick/standard/comprehensive)
      - notes: textarea (optional context for AI)
    
    submit_action: "Creates async job, redirects to status page"
```

## Job Status Flow

```
SUBMITTED → QUEUED → PROCESSING → COMPLETE
                         │
                         ├── Discovery (searching...)
                         ├── Extraction (extracting content...)
                         ├── Transcription (getting transcripts...)
                         ├── Organization (formatting for NotebookLM...)
                         └── Intelligence (generating analysis...)
```

## Export Options

```yaml
export_options:
  primary:
    destination: Google Drive
    folder_structure: "/Research Agent/{topic}_{date}/"
    files:
      - Research_Packet.gdoc
      - Documentary_Intelligence.gdoc
      - YouTube_URLs.txt
      - Job_Metadata.json
  
  secondary:
    - Download as ZIP (all files)
    - Copy Research Packet to clipboard (markdown)
    - Share link (temporary, expires 7 days)
```

---

# Part 9: Implementation Checklist

## Phase 1: Core Pipeline (MVP)
- [ ] FastAPI backend with basic job management
- [ ] Tavily integration for web search
- [ ] Jina Reader integration for extraction
- [ ] Supadata integration for transcripts
- [ ] PRAW integration for Reddit
- [ ] Basic query generation (templates)
- [ ] Research Packet formatting
- [ ] Google Drive export
- [ ] Simple web UI for job creation

## Phase 2: Intelligence Layer
- [ ] DeepSeek integration for LLM
- [ ] Intelligent query generation
- [ ] Documentary Intelligence generation
- [ ] YouTube URL list generation

## Phase 3: Polish
- [ ] All 7 genre modes configured
- [ ] Full graceful degradation
- [ ] Error reporting in output
- [ ] Job history and management
- [ ] Settings and preferences

## Phase 4: Optimization
- [ ] Caching for repeated queries
- [ ] Parallel extraction
- [ ] Cost tracking
- [ ] Usage analytics

---

# Part 10: Quick Reference

## Estimated Costs

| Job Type | Sources | Cost | Time |
|----------|---------|------|------|
| Quick (testing) | ~15 | $0.15 | 2-3 min |
| Standard | ~25 | $0.30 | 5-8 min |
| Comprehensive | ~40 | $0.50 | 10-15 min |

**Monthly (60 jobs):** $20-40

## Tool Priority

1. **YouTube** - Always search first, most information ends up here
2. **Web** - Tavily for articles, blogs, reference content
3. **Reddit** - PRAW for discussions, reactions, firsthand accounts
4. **News** - GDELT for current events
5. **Academic** - Semantic Scholar for scholarly content

## Output Summary

| Output | Content | Purpose |
|--------|---------|---------|
| Research Packet | Unmodified source content | Import to NotebookLM |
| YouTube URLs | List of video links | Direct NotebookLM import |
| Documentary Intelligence | AI analysis | Spark ideas, find angles |

---

*End of Research Agent v5.0 Specification*
