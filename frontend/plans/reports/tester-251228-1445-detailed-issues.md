# Detailed Issues & Code Examples

## Critical Issue #1: Thread Safety in Parallel Execution

### Problem Location
**File:** `backend/pipeline/context.py`
**Severity:** CRITICAL (Production Risk)
**Impact:** Data corruption, lost warnings, race conditions

### Current Code
```python
@dataclass
class PipelineContext:
    outputs: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    def set_output(self, key: str, value: str) -> None:
        self.outputs[key] = value
```

### Why It's Broken
When parallel executor runs 3 threads concurrently:
```
Thread 1 (YouTube):                 Thread 2 (Web):                Thread 3 (Reddit):
ctx.warnings.append("...")  ──>     ctx.web_sources[0].text = "..."     ctx.warnings.append("...")
         ↓
    [Lost! Overwritten by Thread 2's append]
```

### Test That Would Catch This
```python
def test_parallel_warnings_not_lost():
    ctx = PipelineContext(job_id="test", topic="test")

    def add_warnings_thread1():
        for i in range(100):
            ctx.add_warning(f"Warning {i}")

    def add_warnings_thread2():
        for i in range(100):
            ctx.add_warning(f"Warning {i+100}")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(add_warnings_thread1)
        executor.submit(add_warnings_thread2)

    # Should have 200 warnings, not < 200
    assert len(ctx.warnings) == 200, f"Expected 200 warnings, got {len(ctx.warnings)}"
```

### Fix
```python
from threading import Lock

@dataclass
class PipelineContext:
    outputs: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def add_warning(self, warning: str) -> None:
        with self._lock:
            self.warnings.append(warning)

    def set_output(self, key: str, value: str) -> None:
        with self._lock:
            self.outputs[key] = value
```

---

## Critical Issue #2: Missing Exception Handling in Parallel Execution

### Problem Location
**File:** `backend/worker.py` (lines 150-157)
**Severity:** CRITICAL (Silent Data Loss)
**Impact:** Job completes but missing source data

### Current Code
```python
# Parallel Group 1: Collection stages
if enable_parallel:
    logger.info(f"[{job_id}] Running collection stages in parallel")
    run_collection_stages_parallel(ctx)  # ← NO TRY-EXCEPT!
else:
    stage_4_youtube_enumeration(ctx)
    stage_5_transcripts(ctx)
    stage_6_web_capture(ctx)
    stage_6_5_reddit(ctx)

# Stage 7: Claim extraction (assumes all sources collected)
stage_7_extraction(ctx)  # ← Processes empty sources!
```

### Why It's Broken
If `run_collection_stages_parallel` crashes:
1. Exception is caught INSIDE parallel_executor
2. Exception stored as warning
3. Function returns normally
4. ctx.web_sources, ctx.transcripts, ctx.reddit_posts are EMPTY
5. stage_7_extraction processes empty data
6. Job completes "successfully" with no claims

### Scenario That Demonstrates The Bug
```python
def test_parallel_failure_detection():
    job_id = "test_job"
    ctx = PipelineContext(job_id=job_id, topic="test")

    # Mock: simulate web capture crash
    original_stage_6 = stage_6_web_capture
    def broken_stage_6(ctx):
        raise RuntimeError("API timeout")

    # Monkey patch
    import backend.pipeline.stages as stages_module
    stages_module.stage_6_web_capture = broken_stage_6

    try:
        run_collection_stages_parallel(ctx)
    except Exception as e:
        # Currently: No exception raised!
        assert False, f"Expected exception, but got none"

    # This assertion currently FAILS
    # because parallel executor silently swallows the error
    assert len(ctx.warnings) > 0, "Should have warnings"
    assert any("web capture" in w.lower() for w in ctx.warnings)
```

### Fix
```python
# In worker.py, stage collection:
try:
    run_collection_stages_parallel(ctx)
except Exception as e:
    logger.error(f"[{job_id}] Parallel collection failed: {e}", exc_info=True)
    ctx.add_warning(f"Parallel execution failed: {str(e)}")

    # Option 1: Fail the job
    raise

    # Option 2: Fall back to sequential (safer)
    # logger.info(f"Falling back to sequential execution...")
    # stage_4_youtube_enumeration(ctx)
    # stage_5_transcripts(ctx)
    # stage_6_web_capture(ctx)
    # stage_6_5_reddit(ctx)

# In parallel_executor.py, check results:
def run_parallel_stages(ctx, stages, ...):
    results = {}  # {stage_name: exception_or_none}
    with ThreadPoolExecutor(...) as executor:
        # ... run stages ...
        for future in as_completed(...):
            # results[name] = exception_or_none

    # NEW: Check for failures
    failed = {name: exc for name, exc in results.items() if exc}
    if failed:
        logger.error(f"Parallel execution had failures: {failed}")
        # Return failures for caller to handle

    return results
```

---

## Critical Issue #3: GDELT Integration Has No Tests

### Problem Location
**File:** `backend/pipeline/stages.py` (lines 176-218)
**Severity:** CRITICAL (Untested Code Path)
**Impact:** breaking_news mode may silently fail

### Current Code
```python
if ctx.job_config.mode.value in ("breaking_news", "BREAKING_NEWS"):
    try:
        from backend.integrations.gdelt_client import search_news_gdelt
        from backend.models.source import SourceItem, SourceType

        gdelt_articles = search_news_gdelt(
            query=ctx.topic,
            timespan="24h",
            max_records=20
        )

        gdelt_sources = []
        for article in gdelt_articles:
            if article.get("url"):  # ← What if key missing?
                source = SourceItem(
                    url=article["url"],
                    title=article.get("title", ""),
                    source_type=SourceType.NEWS,
                    text="",
                    published_at=article.get("published_date"),
                    notes=f"GDELT: {article.get('source', 'unknown')}"
                )
                gdelt_sources.append(source)
```

### Problems With This Code

1. **No validation of article structure:**
   ```python
   article.get("url")  # Returns None if missing
   # But then uses: article["url"]  # KeyError!
   ```

2. **No validation of URL format:**
   ```python
   url = article["url"]
   if not url.startswith("http"):  # MISSING!
       # Skip invalid URLs
       pass
   ```

3. **GDELT client import could fail:**
   ```python
   try:
       from backend.integrations.gdelt_client import search_news_gdelt
       # ← But this is inside the breaking_news check
       # If gdelt_client.py has a syntax error, job dies here
   except Exception as gdelt_error:
       logger.warning(...)  # ← Just logs, doesn't fail
   ```

4. **No test file exists:**
   - File list shows: test_api_clients.py, test_youtube_client.py, test_transcripts.py
   - Missing: test_gdelt_client.py

### Test That Should Exist (But Doesn't)
```python
# tests/test_gdelt_client.py (MISSING!)

import pytest
from unittest.mock import MagicMock, patch
from backend.pipeline.stages import stage_3_source_shortlist
from backend.pipeline.context import PipelineContext
from backend.models.job_config import JobConfig, ResearchMode

def test_gdelt_integration_breaking_news():
    """Test GDELT integration for breaking_news mode."""
    ctx = PipelineContext(job_id="test", topic="test event")
    ctx.job_config = JobConfig(topic="test event", mode=ResearchMode.BREAKING_NEWS)
    ctx.angles = ["angle1"]
    ctx.key_terms = ["keyword1"]

    # Mock GDELT response
    with patch('backend.integrations.gdelt_client.search_news_gdelt') as mock_gdelt:
        mock_gdelt.return_value = [
            {
                "url": "https://example.com/article1",
                "title": "Breaking News",
                "published_date": "2025-12-28",
                "source": "NewsOrg"
            },
            {
                "url": "https://example.com/article2",
                "title": "Follow-up Story",
                "published_date": "2025-12-28",
                "source": "NewsOrg"
            }
        ]

        stage_3_source_shortlist(ctx)

        # Assertions
        assert len(ctx.web_sources) >= 2
        assert any("GDELT" in s.notes for s in ctx.web_sources)

def test_gdelt_handles_malformed_articles():
    """Test GDELT handling of malformed article data."""
    ctx = PipelineContext(job_id="test", topic="test")
    ctx.job_config = JobConfig(topic="test", mode=ResearchMode.BREAKING_NEWS)
    ctx.angles = ["angle1"]
    ctx.key_terms = ["keyword1"]

    with patch('backend.integrations.gdelt_client.search_news_gdelt') as mock_gdelt:
        mock_gdelt.return_value = [
            {"url": "https://valid.com/article"},  # Valid
            {"title": "Missing URL"},  # Missing URL
            {"url": "not-a-url"},  # Invalid URL
            {"url": None},  # Null URL
            {"url": ""},  # Empty URL
        ]

        stage_3_source_shortlist(ctx)

        # Should only add valid URLs
        valid_sources = [s for s in ctx.web_sources if s.url.startswith("http")]
        assert len(valid_sources) >= 1

def test_gdelt_failure_doesnt_crash_job():
    """Test job continues if GDELT fails."""
    ctx = PipelineContext(job_id="test", topic="test")
    ctx.job_config = JobConfig(topic="test", mode=ResearchMode.BREAKING_NEWS)

    with patch('backend.integrations.gdelt_client.search_news_gdelt') as mock_gdelt:
        mock_gdelt.side_effect = RuntimeError("GDELT API timeout")

        # Should not raise
        stage_3_source_shortlist(ctx)

        # Should have warning
        assert any("GDELT" in w for w in ctx.warnings)
```

### Fix
```python
if ctx.job_config.mode.value in ("breaking_news", "BREAKING_NEWS"):
    try:
        from backend.integrations.gdelt_client import search_news_gdelt
        from backend.models.source import SourceItem, SourceType

        logger.info(f"[{ctx.job_id}] Fetching GDELT news")

        gdelt_articles = search_news_gdelt(
            query=ctx.topic,
            timespan="24h",
            max_records=20
        )

        if not isinstance(gdelt_articles, list):
            logger.warning(f"GDELT returned invalid type: {type(gdelt_articles)}")
            gdelt_articles = []

        gdelt_sources = []
        for i, article in enumerate(gdelt_articles):
            try:
                # Validate article structure
                if not isinstance(article, dict):
                    logger.warning(f"GDELT article {i} is not dict: {type(article)}")
                    continue

                url = article.get("url", "").strip()
                if not url:
                    logger.debug(f"GDELT article {i} missing URL")
                    continue

                # Validate URL format
                if not (url.startswith("http://") or url.startswith("https://")):
                    logger.debug(f"GDELT article {i} has invalid URL format: {url}")
                    continue

                # Create source with validation
                source = SourceItem(
                    url=url,
                    title=article.get("title", "Untitled")[:200],  # Limit title length
                    source_type=SourceType.NEWS,
                    text="",
                    published_at=article.get("published_date"),
                    notes=f"GDELT: {article.get('source', 'unknown')}"
                )
                gdelt_sources.append(source)

            except Exception as item_error:
                logger.warning(f"Failed to process GDELT article {i}: {item_error}")
                continue

        if gdelt_sources:
            ctx.web_sources.extend(gdelt_sources)
            logger.info(f"[{ctx.job_id}] Added {len(gdelt_sources)} GDELT sources")

            # Append to shortlist markdown
            gdelt_md = "\n\n## GDELT News Sources\n\n"
            for src in gdelt_sources[:10]:
                gdelt_md += f"- [{src.title or 'Untitled'}]({src.url})\n"
            current_md = ctx.outputs.get("source_shortlist_md", "")
            ctx.set_output("source_shortlist_md", current_md + gdelt_md)
        else:
            logger.info(f"[{ctx.job_id}] No GDELT sources found or all invalid")

    except ImportError as import_error:
        logger.warning(f"GDELT client not available: {import_error}")
        ctx.add_warning(f"GDELT integration not available: {str(import_error)}")
    except Exception as gdelt_error:
        logger.warning(f"GDELT search failed: {gdelt_error}")
        ctx.add_warning(f"GDELT news search failed: {str(gdelt_error)}")
```

---

## Critical Issue #4: Job State Loss on Worker Crash

### Problem Location
**File:** `backend/worker.py` (lines 136-175)
**Severity:** CRITICAL (Orphaned Jobs)
**Impact:** No progress checkpoints between stages

### Current Code
```python
try:
    # Stage 0-3: Sequential initialization and discovery
    stage_0_initialize(ctx)        # ✓ Updates job
    stage_1_planning(ctx)          # ✓ Updates job
    stage_2_research_mapping(ctx)  # ✗ No checkpoint
    stage_3_source_shortlist(ctx)  # ✗ No checkpoint
    stage_3_5_quality_gate(ctx)    # ✗ No checkpoint

    # Parallel Group 1: Collection stages
    if enable_parallel:
        run_collection_stages_parallel(ctx)  # ✗ No checkpoint

    # Stage 7: Claim extraction
    stage_7_extraction(ctx)        # ✗ No checkpoint
    # ... continues with more stages
```

### Why It's Broken

**Scenario:** Worker process dies after stage 6 (web capture):
1. Job record shows `stage="source_discovery"` (last update from stage 3)
2. But actually at stage 6!
3. User sees job is stuck
4. All web sources collected (in memory) are LOST
5. Only option: restart, lose all progress

### Test That Would Catch This
```python
def test_job_state_checkpoints():
    """Verify job state is saved after each stage."""
    job_id = "test_checkpoint"

    # Mock update_job to track calls
    updates = []
    original_update = update_job

    def track_update(job_id, **kwargs):
        updates.append((job_id, kwargs))
        return original_update(job_id, **kwargs)

    with patch('backend.worker.update_job', side_effect=track_update):
        # Run pipeline through stage 6
        ctx = PipelineContext(job_id=job_id, topic="test")

        stage_0_initialize(ctx)
        stage_1_planning(ctx)
        stage_2_research_mapping(ctx)
        stage_3_source_shortlist(ctx)
        stage_3_5_quality_gate(ctx)
        # stage 4-6 ...

        # Check that stage name was updated after each stage
        stage_names = [u[1].get('stage') for u in updates if 'stage' in u[1]]

        expected = ["initializing", "planning", "research_mapping",
                   "source_discovery", "quality_gate", "youtube_enumeration",
                   "transcript_fetching", "web_capture"]

        for expected_stage in expected:
            assert expected_stage in stage_names, \
                f"Missing checkpoint for {expected_stage}"
```

### Fix
```python
# After each important stage, add checkpoint:

try:
    stage_0_initialize(ctx)
    update_job(ctx.job_id, stage="initialized", progress_percent=2)

    stage_1_planning(ctx)
    config_dict = ctx.job_config.model_dump() if ctx.job_config else {}
    update_job(ctx.job_id, stage="planned", progress_percent=5,
              partial_outputs={"job_config": config_dict})

    stage_2_research_mapping(ctx)
    update_job(ctx.job_id, stage="research_mapped", progress_percent=20,
              partial_outputs={"research_map": ctx.outputs.get("research_map_md", "")})

    stage_3_source_shortlist(ctx)
    # Serialize web sources
    web_sources_data = [
        {
            "url": s.url,
            "title": s.title,
            "source_type": s.source_type.value if hasattr(s.source_type, 'value') else str(s.source_type)
        }
        for s in ctx.web_sources
    ]
    update_job(ctx.job_id, stage="source_shortlisted", progress_percent=25,
              partial_outputs={
                  "source_shortlist": ctx.outputs.get("source_shortlist_md", ""),
                  "web_sources_count": len(ctx.web_sources),
                  "web_sources": web_sources_data[:10]  # Save first 10 for reference
              })

    stage_3_5_quality_gate(ctx)
    update_job(ctx.job_id, stage="quality_gated", progress_percent=30,
              partial_outputs={"quality_gate_stats": ctx.quality_gate_stats})

    # Similar checkpoints for stages 4-10
```

---

## Major Issue #1: Reddit Collection ImportError Not Handled

### Problem Location
**File:** `backend/pipeline/stages.py` (lines 496-534)
**Severity:** MAJOR (Silent Crash)
**Impact:** Code continues after error set_output without returning

### Current Code
```python
def stage_6_5_reddit(ctx: PipelineContext) -> None:
    try:
        from backend.integrations.reddit_client import RedditClient, extract_reddit_content
        from backend.models.source import SourceItem, SourceType

        reddit_client = RedditClient()
        ctx.reddit_posts = reddit_client.search_multiple_subreddits(...)

    except ImportError:
        logger.info(f"[{ctx.job_id}] Reddit integration not available")
        ctx.set_output("reddit_discussions_md", "# Reddit Discussions\n\n*Reddit integration not installed*")
        # ← MISSING RETURN! Code continues...

    except Exception as e:
        logger.warning(f"Reddit collection failed: {e}")
        ctx.add_warning(f"Reddit collection failed: {str(e)}")
        ctx.set_output("reddit_discussions_md", f"# Reddit Discussions\n\n*Error: {str(e)}*")

    # This continues even after ImportError above!
    if ctx.reddit_posts:  # ← ctx.reddit_posts was never set!
        reddit_md = extract_reddit_content(ctx.reddit_posts)  # ← Crashes here
```

### Test That Would Catch This
```python
def test_reddit_import_error_handled():
    """Test that missing Reddit client doesn't crash stage."""
    ctx = PipelineContext(job_id="test", topic="test")

    with patch.dict('sys.modules', {'backend.integrations.reddit_client': None}):
        # This should not raise AttributeError
        stage_6_5_reddit(ctx)

        # Should have set output
        assert "Reddit" in ctx.outputs.get("reddit_discussions_md", "")
        assert ctx.reddit_posts == []  # Should initialize to empty list
```

### Fix
```python
def stage_6_5_reddit(ctx: PipelineContext) -> None:
    logger.info(f"[{ctx.job_id}] Stage 6.5: Reddit collection")
    update_job(ctx.job_id, stage="reddit_collection", progress_percent=58)

    try:
        from backend.integrations.reddit_client import RedditClient, extract_reddit_content
        from backend.models.source import SourceItem, SourceType

        reddit_client = RedditClient()
        ctx.reddit_posts = reddit_client.search_multiple_subreddits(
            query=ctx.topic,
            limit_per_sub=5
        )

        if ctx.reddit_posts:
            reddit_md = extract_reddit_content(ctx.reddit_posts)
            ctx.set_output("reddit_discussions_md", reddit_md)

            reddit_source = SourceItem(
                url="https://reddit.com/search",
                title="Reddit Discussions",
                source_type=SourceType.REDDIT,
                text=reddit_md,
                notes="Aggregated Reddit discussions"
            )
            ctx.web_sources.append(reddit_source)
            logger.info(f"[{ctx.job_id}] Collected {len(ctx.reddit_posts)} Reddit posts")
        else:
            ctx.set_output("reddit_discussions_md", "# Reddit Discussions\n\nNo relevant Reddit posts found.")

    except ImportError as e:
        logger.info(f"[{ctx.job_id}] Reddit integration not available: {e}")
        ctx.set_output("reddit_discussions_md", "# Reddit Discussions\n\nReddit integration not available.")
        ctx.reddit_posts = []
        return  # ← MUST RETURN

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Reddit collection failed: {e}")
        ctx.add_warning(f"Reddit collection failed: {str(e)}")
        ctx.set_output("reddit_discussions_md", f"# Reddit Discussions\n\n*Error: {str(e)}*")
        ctx.reddit_posts = []
```

---

## Summary of Issues Fixed

| Issue | File | Line | Fix Effort | Priority |
|-------|------|------|-----------|----------|
| Thread safety | context.py | 80-97 | 30 min | CRITICAL |
| Parallel exception handling | worker.py | 150-170 | 20 min | CRITICAL |
| GDELT tests missing | N/A | N/A | 2 hours | CRITICAL |
| Job state checkpoints | worker.py | 136-175 | 2 hours | CRITICAL |
| Reddit import not handled | stages.py | 527 | 15 min | MAJOR |
| Web capture fallback errors | stages.py | 424-476 | 1 hour | MAJOR |
| GDELT URL validation | stages.py | 176-218 | 1 hour | MAJOR |
| Cost summary null check | worker.py | 177 | 10 min | MAJOR |

**Total Effort:** 1-2 weeks for complete fixes

