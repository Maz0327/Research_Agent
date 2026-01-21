# Mode & Niche Impact on Source Collection - Scout Report

**Date:** 2025-12-30  
**Codebase:** Research Agent Backend  
**Focus:** How JobConfig.mode and niche affect source collection strategies

## Executive Summary

Mode (breaking_news/investigation/profile/controversy) and niche (downfalls/mysteries/political/etc.) control source collection through three mechanisms:

1. **YouTube enumeration**: Currently mode-controlled (breaking_news=disabled), but SHOULD ALWAYS BE ON per product requirements
2. **Reddit collection**: JobConfig.reddit.subreddits (from planning) + limit_per_sub; niche config stored but NOT applied to subreddit selection
3. **Source floors (Quality Gate)**: Mode sets type minimums (web/news/video/academic/discussion); niche CAN override but doesn't due to implementation oversight

**Key Findings:**
- ✓ Niche query expansion works (adds topic-specific search queries)
- ✗ Niche source_floors loaded but not applied to Quality Gate
- ✗ YouTube disabled for breaking_news (should always be enabled)
- ✓ Reddit subreddit selection works via JobConfig (populated by OpenAI planning)

---

## 1. YouTube Enumeration - Mode Currently Controls Enable/Disable (WRONG)

### Current Behavior
- **breaking_news mode**: YouTube DISABLED (seen as "too slow")
- **investigation/profile/controversy**: YouTube ENABLED

### Files
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/youtube.py` (lines 13-53)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/models/job_config.py` (lines 42-95, get_mode_config)

### Mode Configuration (get_mode_config)

```python
DocumentaryMode.BREAKING_NEWS: {
    "sources": {
        "youtube": {"enabled": False},  # ← WRONG: Too slow for breaking news
    },
},
DocumentaryMode.INVESTIGATION: {
    "sources": {
        "youtube": {"enabled": True, "max_videos": 30},
    },
},
DocumentaryMode.PROFILE: {
    "sources": {
        "youtube": {"enabled": True, "search_entity_name": True},
    },
},
DocumentaryMode.CONTROVERSY: {
    "sources": {
        "youtube": {"enabled": True, "diverse_channels": True},
    },
}
```

### Stage 4: YouTube Implementation

Two modes of operation:
1. **Channel enumeration** (original): If `ctx.job_config.youtube.channels` specified
2. **Topic search** (auto-discovery, Dec 2025): If no channels → search YouTube by topic

```python
def stage_4_youtube_enumeration(ctx: PipelineContext) -> None:
    if ctx.job_config.youtube.channels:
        result = enumerate_channel_uploads(ctx.job_config)
        ctx.youtube_videos = result.get("videos", [])
    else:
        # Topic-based search (NEW - always searches topic)
        max_videos = ctx.job_config.youtube.max_videos
        result = search_youtube_videos(
            query=ctx.topic,
            max_results=max_videos,
            exclude_shorts=ctx.job_config.youtube.exclude_shorts,
        )
        ctx.youtube_videos = result.get("videos", [])
```

### Product Requirement vs Implementation

| Feature | Current | Required |
|---------|---------|----------|
| YouTube enabled for breaking_news | NO | YES - always on |
| YouTube always primary source | NO | YES - big source for all niches |
| Search terms are smart/niche-aware | NO | YES - human-like relevance |

---

## 2. Reddit Collection - JobConfig Controls, Niche Ignored

### Files
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/web_capture.py` (lines 91-140, stage_6_5_reddit)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/models/job_config.py` (lines 134-149, RedditConfig)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/reddit_client.py`

### Stage 6.5: Reddit Collection Flow

```python
def stage_6_5_reddit(ctx: PipelineContext) -> None:
    reddit_client = RedditClient()
    
    # Use subreddits from job_config if available
    subreddits = None
    limit_per_sub = 5
    
    if ctx.job_config and hasattr(ctx.job_config, 'reddit'):
        if ctx.job_config.reddit.subreddits:
            subreddits = ctx.job_config.reddit.subreddits  # From planning stage
            logger.info(f"Using topic-specific subreddits: {subreddits}")
        limit_per_sub = ctx.job_config.reddit.limit_per_sub
    
    ctx.reddit_posts = reddit_client.search_multiple_subreddits(
        query=ctx.topic,
        subreddits=subreddits,              # From JobConfig.reddit
        limit_per_sub=limit_per_sub
    )
```

### RedditConfig Model

```python
class RedditConfig(BaseModel):
    subreddits: list[str] = Field(
        default_factory=list,
        description="Suggested subreddits for this topic (e.g., 'FanTheories', 'television')"
    )
    limit_per_sub: int = Field(5, ge=1, le=20, description="Max posts per subreddit")
```

### How Subreddits Are Populated

1. **OpenAI planning** generates JobConfig → `plan_job()` creates reddit.subreddits list
2. **Default fallback** in reddit_client.py if subreddits not provided:
   ```python
   subreddits = ["politics", "news", "worldnews", "OutOfTheLoop", "NeutralPolitics"]
   ```

### Current Control
- ✓ JobConfig.reddit.subreddits controls which subreddits to search
- ✓ JobConfig.reddit.limit_per_sub controls posts per subreddit (default 5)
- ✗ Niche config is loaded but NOT used for subreddit selection

---

## 3. Source Floors & Quality Gate - Where Mode IS Working

### Files
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/quality_gate.py` (lines 95-106, 609-633)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/discovery.py` (lines 218-306, stage_3_5_quality_gate)

### Mode-Specific Source Floors

```python
SOURCE_FLOORS = {
    'quick': {'web': 3, 'news': 1, 'video': 1, 'academic': 0, 'discussion': 0, 'max_slots': 8},
    'breaking_news': {'web': 3, 'news': 4, 'video': 1, 'academic': 0, 'discussion': 1, 'max_slots': 15},
    'full': {'web': 4, 'news': 3, 'video': 3, 'academic': 2, 'discussion': 1, 'max_slots': 25},
    'investigation': {'web': 5, 'news': 3, 'video': 4, 'academic': 3, 'discussion': 3, 'max_slots': 40},
    'profile': {'web': 3, 'news': 3, 'video': 4, 'academic': 1, 'discussion': 1, 'max_slots': 25},
    'controversy': {'web': 3, 'news': 3, 'video': 3, 'academic': 2, 'discussion': 4, 'max_slots': 25},
}
```

**Translation:**
- breaking_news: Speed (high news:video ratio 4:1)
- investigation: Comprehensive (high max_slots=40, balanced sources)
- profile: Video-heavy (4 video + 3 news)
- controversy: Discussion-heavy (4 discussion for multiple perspectives)

### Stage 3.5: Quality Gate Application

```python
def stage_3_5_quality_gate(ctx: PipelineContext) -> None:
    mode = ctx.job_config.mode.value
    niche = ctx.job_config.niche
    
    result = run_quality_gate(
        sources=source_dicts,
        mode=mode,
        niche=niche,  # Passed but NOT used internally
        query_terms=ctx.key_terms
    )
```

### run_quality_gate → quality_gate Chain

```python
def run_quality_gate(sources, mode="full", niche=None, query_terms=None) -> Dict:
    output = quality_gate(sources, mode, niche, query_terms)
    return {
        "approved": [...],
        "soft_rejected": [...],
        "hard_rejected": [...],
        "stats": output.stats.to_dict(),
    }

def quality_gate(sources, mode="full", niche=None, query_terms=None):
    floors = SOURCE_FLOORS.get(mode, DEFAULT_FLOORS).copy()
    # niche parameter is ACCEPTED but NEVER USED
    # ... allocation algorithm uses mode floors only
```

**CRITICAL BUG:** Niche parameter accepted but ignored. Niche source_floors never applied.

### Allocation Algorithm (_allocate_slots)

```python
def _allocate_slots(
    sources: List[Source],
    floors: Dict[str, int],  # Mode-only floors passed here
    max_slots: int,
    type_weights: Dict[str, float],
) -> Tuple[List[Source], List[Source]]:
    
    # Phase 1: Fill floors first (guaranteed minimums by type)
    for source_type, floor in floors.items():
        # Allocate floor number of sources of this type
    
    # Phase 2: Fill remaining slots with best quality sources
    # Respect domain limits, type caps (75% max), total slot limits
```

---

## 4. Query Expansion - Where Niche IS Working

### Files
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/discovery.py` (lines 34-49)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/niche_loader.py` (lines 256-326)

### Stage 3: Query Expansion

```python
def stage_3_source_shortlist(ctx: PipelineContext) -> None:
    expanded_key_terms = list(ctx.key_terms)
    if ctx.niche_config:
        query_additions = ctx.niche_config.get("query_additions", [])
        if query_additions:
            # Expand queries with topic substitution
            for query in query_additions:
                expanded = query.replace("{topic}", ctx.topic)
                expanded_key_terms.append(expanded)  # ✓ WORKS
            logger.info(f"Added {len(query_additions)} niche queries")
        
        priority_keywords = ctx.niche_config.get("priority_keywords", [])
        if priority_keywords:
            expanded_key_terms.extend(priority_keywords)  # ✓ WORKS
```

### Example: Downfalls Niche (downfalls.yaml)

```yaml
query_additions:
  - "{topic} controversy timeline"
  - "{topic} allegations"
  - "{topic} response statement"
  - "{topic} reddit drama"
  - "{topic} exposed"
  - "{topic} cancelled"
  - "{topic} backlash"

priority_keywords:
  - controversy
  - scandal
  - allegation
  - backlash
  - evidence
```

**Status:** ✓ Working correctly - adds 7-10 niche-specific queries to search

---

## 5. Niche Loader - Source Floors Defined But Not Applied

### Files
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/niche_loader.py`
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/planning.py` (lines 68-81)

### Merge Function (niche_loader.py)

```python
def merge_mode_and_niche(mode: str, niche: Optional[str] = None):
    # Start with mode config
    result = {
        "mode": mode,
        "niche": niche,
        "source_floors": mode_config.source_floors.copy(),  # Mode floors
        "query_additions": [],
        ...
    }
    
    if not niche:
        return result
    
    niche_config = get_niche(niche)
    
    # OVERRIDE: source_floors (per PRD v4.3)
    if niche_config.source_floors:
        result["source_floors"] = niche_config.source_floors.copy()  # ← Set but not used
    
    # APPEND: query_additions
    result["query_additions"] = niche_config.query_additions.copy()
    
    return result
```

### Loading in Planning Stage

```python
# In stage_1_planning.py:
if ctx.job_config.niche:
    if is_valid_niche(ctx.job_config.niche):
        ctx.niche_config = merge_mode_and_niche(
            mode=ctx.job_config.mode.value,
            niche=ctx.job_config.niche
        )
        # niche_config now has:
        # - source_floors: OVERRIDDEN by niche ✓
        # - query_additions: APPENDED ✓
        # - priority_keywords, preferred_domains ✓
        logger.info(f"Loaded niche overlay: {ctx.job_config.niche}")
```

### Example: Downfalls Niche Source Floors

```yaml
# Override mode source floors for downfalls niche
source_floors:
  web: 2         # Reduced (was 3-5 in modes)
  news: 3        # Standard
  video: 5       # INCREASED - video receipts are primary evidence
  academic: 0    # None - rarely relevant for drama
  discussion: 4  # INCREASED - Reddit/forum reactions crucial
```

---

## 6. Critical Bug: Niche Floors Never Applied to Quality Gate

### The Problem

Niche source_floors are created in `merge_mode_and_niche()` but `quality_gate()` function **ignores** the niche parameter.

### Evidence

**Stage 3.5 calls quality gate WITH niche:**
```python
result = run_quality_gate(
    sources=source_dicts,
    mode=mode,          # ✓ Used
    niche=niche,        # Passed
    query_terms=ctx.key_terms
)
```

**quality_gate function signature accepts but ignores:**
```python
def quality_gate(
    sources: List[Dict],
    mode: str = "full",
    niche: Optional[str] = None,  # ← Parameter accepted
    query_terms: Optional[List[str]] = None,
) -> QualityGateOutput:
    # ...
    floors = SOURCE_FLOORS.get(mode, DEFAULT_FLOORS).copy()
    # ↑ Uses SOURCE_FLOORS dict (mode-only)
    # ↑ Never uses niche parameter
```

### Impact

For a **downfalls** niche research (e.g., "Elon Musk downfall"):
- **Expected:** video=5, discussion=4 sources (receipts + reactions)
- **Actual:** Uses investigation mode defaults: video=4, discussion=3
- **Result:** Missing 1 video and 1 discussion source per job

### Fix Required

```python
def quality_gate(
    sources: List[Dict],
    mode: str = "full",
    niche: Optional[str] = None,
    query_terms: Optional[List[str]] = None,
) -> QualityGateOutput:
    # Get mode floors
    floors = SOURCE_FLOORS.get(mode, DEFAULT_FLOORS).copy()
    max_slots = floors.pop('max_slots')
    
    # MISSING: Override with niche if provided
    if niche:
        from backend.pipeline.niche_loader import get_source_floors
        try:
            niche_floors = get_source_floors(mode, niche)
            if niche_floors:
                # Merge niche overrides
                floors.update(niche_floors)
                logger.info(f"Applied niche '{niche}' source floors: {niche_floors}")
        except Exception as e:
            logger.warning(f"Failed to apply niche floors: {e}")
    
    # ... rest of allocation continues with niche-aware floors
```

---

## 7. Data Flow - Mode and Niche Through Pipeline

### Full Stage Progression

```
Stage 0: Initialize
   └─ Set job status to "running"

Stage 1: Planning (OpenAI)
   └─ Generate JobConfig (with youtube, reddit config, niche)
   └─ Load niche_config via merge_mode_and_niche()
      ├─ niche_config.source_floors: Created ✓ (not used later ✗)
      ├─ niche_config.query_additions: Created ✓ (used in Stage 3 ✓)
      └─ niche_config.priority_keywords: Created ✓ (used in Stage 3 ✓)

Stage 2: Research Mapping (Perplexity)
   └─ Generate angles and key_terms

Stage 3: Source Shortlist
   ├─ Determine search strategy:
   │  └─ breaking_news → Perplexity (speed)
   │  └─ investigation/controversy/profile → Exa (94.9% accuracy)
   ├─ Expand queries with niche additions ✓ WORKS
   │  └─ Add 7-10 niche-specific queries
   ├─ Add priority_keywords ✓ WORKS
   └─ Search with Exa/Perplexity

Stage 3.5: Quality Gate
   ├─ Pass sources to quality_gate()
   ├─ Use mode.source_floors ✓ WORKS
   ├─ Receive niche parameter ✓ But IGNORE IT ✗
   └─ Allocate sources by type with mode-only floors

Stage 4: YouTube
   ├─ Check if YouTube enabled (mode-based check)
   │  └─ breaking_news=disabled ✗ (should be enabled)
   │  └─ others=enabled ✓
   ├─ Search YouTube by topic
   └─ Fetch up to max_videos

Stage 5: Transcripts (Supadata → Whisper)

Stage 6: Web Capture (Jina → Trafilatura → Playwright)

Stage 6.5: Reddit
   ├─ Use JobConfig.reddit.subreddits ✓
   ├─ Use JobConfig.reddit.limit_per_sub ✓
   └─ Ignore niche config ✗

Stage 7: Extraction (OpenAI - claims)

Stage 8: Validation

Stage 9: Drive Upload

Stage 10: Completion
```

---

## 8. Summary: What Works, What's Broken, What's Missing

### ✓ WORKING - Mode Effects

| Component | Effect | Implementation |
|-----------|--------|-----------------|
| Source type floors | Allocates minimums for web/news/video/academic/discussion | quality_gate() uses SOURCE_FLOORS[mode] |
| Max slots per mode | investigation=40, full=25, breaking=15 | quality_gate() enforces max_slots |
| Search strategy | breaking_news uses Perplexity; others use Exa | stage_3_source_shortlist() checks mode |
| YouTube enabled | investigation/profile/controversy enabled | get_mode_config() config dict |
| Reddit included | Collected in all modes | stage_6_5_reddit() always runs |

### ✓ WORKING - Niche Effects

| Component | Effect | Implementation |
|-----------|--------|-----------------|
| Search query expansion | +7-10 topic-specific queries | stage_3_source_shortlist() reads niche_config.query_additions |
| Priority keywords | Enhanced BM25 scoring | niche_config.priority_keywords added to terms |
| Query terms for BM25 | Relevance bonus applied | quality_gate(query_terms) |

### ✗ NOT WORKING - Niche Source Floors

| Component | Expected | Actual | Issue |
|-----------|----------|--------|-------|
| Niche source_floors applied | Override mode floors | Mode floors used | quality_gate(niche=...) parameter ignored |
| Example: downfalls video=5 | 5 video sources | 4 video sources | Niche floors never consulted |
| Example: downfalls discussion=4 | 4 discussion sources | 3 discussion sources | Uses mode defaults instead |

### ✗ WRONG - YouTube Strategy

| Issue | Current | Required | Impact |
|-------|---------|----------|--------|
| breaking_news YouTube | Disabled (slow) | Always enabled | Missing video evidence in breaking news |
| YouTube priority | Low for breaking news | High for all topics | Video is major documentary source |
| Smart search terms | Topic only | Human-like filtering | Could get irrelevant videos |

### ✗ NOT IMPLEMENTED - Potential Niche Features

| Feature | Purpose | Status |
|---------|---------|--------|
| Niche-specific subreddit defaults | Different subreddits per niche | Not implemented |
| YouTube search refinement | Niche-aware query expansion for YouTube | Not implemented |
| Domain preference enforcement | Boost preferred_domains in scoring | Loaded but unused |

---

## Product Requirements vs Implementation Gaps

| Requirement | Status | Gaps |
|------------|--------|------|
| Mode-aware source distribution | ✓ Mostly working | Niche overrides broken |
| Niche-aware query expansion | ✓ Working | — |
| YouTube always primary source | ✗ Broken | Disabled for breaking_news |
| Smart human-like search | ~ Partial | Niche queries work, YouTube/Reddit less smart |
| Niche affects source distribution | ✗ Broken | Niche floors not applied |

---

## File Map

### Core Models
- `/Users/maz/Documents/GitHub/Research_Agent/backend/models/job_config.py` - JobConfig, DocumentaryMode, RedditConfig, YouTubeConfig

### Pipeline Stages
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/planning.py` - Niche loading
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/discovery.py` - Query expansion
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/youtube.py` - YouTube enumeration
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/web_capture.py` - Reddit collection

### Quality Gate & Filtering
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/quality_gate.py` - Source allocation (BUG: niche parameter ignored)

### Niche System
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/niche_loader.py` - Merge mode/niche
- `/Users/maz/Documents/GitHub/Research_Agent/backend/config/niches/` - YAML configs (downfalls.yaml, mysteries.yaml, etc.)

### Integrations
- `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/reddit_client.py` - Reddit API
- `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/youtube_client.py` - YouTube API

---

## Questions & Recommendations

### Questions Answered
1. **Niche source_floors oversight?** Yes - loaded but not applied in quality_gate
2. **What does preferred_domains mean?** Listed in niche config for reference, not enforced in scoring
3. **Should Reddit subreddits be niche-aware?** Yes - downfalls niche should suggest different subreddits than political niche
4. **YouTube search should be smart?** Yes - use niche-specific search terms like query_additions
5. **YouTube always on?** Yes - should be enabled for all modes and niches

