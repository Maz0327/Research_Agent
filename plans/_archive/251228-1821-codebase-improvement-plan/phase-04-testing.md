# Phase 04: Testing

## Context Links
- [Comprehensive Quality Audit](../reports/code-reviewer-251228-1459-comprehensive-quality-audit.md)
- [Pipeline Modularization Audit](../reports/code-reviewer-251228-1819-pipeline-modularization-audit.md)
- [Frontend Stores Audit](../reports/tester-251228-1516-frontend-stores-audit.md)

## Overview

| Field | Value |
|-------|-------|
| Priority | P2 (Medium) |
| Status | Pending |
| Effort | 8 hours |
| Risk | Low |

Address testing gaps identified in code review. Focus on critical paths and newly modularized code.

**Current State:**
- Backend: 8 test files exist, but no pipeline stage tests
- Frontend: Only 2 test files (`JobCard.test.tsx`, `jobs.test.ts`)
- Coverage: Unknown (not measured)

## Requirements

### Functional
1. Add unit tests for modularized pipeline stages
2. Add integration tests for claim extraction
3. Add frontend store tests for error handling
4. Add validation utility tests

### Non-Functional
- All tests must pass in CI
- Target 80% coverage for critical paths
- Tests should run in <60s

## Test Strategy

### Backend Testing

| Component | Test Type | Priority | Effort |
|-----------|-----------|----------|--------|
| `stages/planning.py` | Unit | High | 1h |
| `extraction/deduplication.py` | Unit | High | 1h |
| `quality_gate/scoring.py` | Unit | Medium | 1h |
| Integration clients | Integration | Medium | 2h |

### Frontend Testing

| Component | Test Type | Priority | Effort |
|-----------|-----------|----------|--------|
| `admin.ts` error handling | Unit | High | 1h |
| `jobs.ts` error handling | Unit | High | 1h |
| `validation.ts` utilities | Unit | Medium | 30min |

## Implementation Steps

### Step 1: Backend - Pipeline Stage Tests (2h)

Create `backend/tests/test_pipeline_stages.py`:

```python
# backend/tests/test_pipeline_stages.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.pipeline.context import PipelineContext
from backend.models.job_config import JobConfig

# Test fixtures
@pytest.fixture
def mock_context():
    """Create mock pipeline context."""
    ctx = Mock(spec=PipelineContext)
    ctx.job_id = "test-job-123"
    ctx.prompt = "Test research topic"
    ctx.config = JobConfig(mode="investigation", budgets={})
    ctx.sources = []
    ctx.claims = []
    ctx.warnings = []
    ctx.add_warning = Mock()
    return ctx


class TestInitializationStage:
    """Tests for stage_0_initialize."""

    @patch("backend.pipeline.stages.initialization.update_job")
    async def test_initialize_sets_job_status(self, mock_update, mock_context):
        """Initialize stage should set job status to running."""
        from backend.pipeline.stages.initialization import stage_0_initialize

        await stage_0_initialize(mock_context)

        mock_update.assert_called()
        call_args = mock_update.call_args
        assert call_args[1]["status"] == "running"


class TestPlanningStage:
    """Tests for stage_1_planning."""

    @patch("backend.pipeline.stages.planning.openai_client")
    async def test_planning_generates_plan(self, mock_openai, mock_context):
        """Planning stage should generate research plan."""
        from backend.pipeline.stages.planning import stage_1_planning

        mock_openai.plan_job.return_value = {
            "search_queries": ["query1", "query2"],
            "youtube_channels": [],
        }

        await stage_1_planning(mock_context)

        mock_openai.plan_job.assert_called_once()
        assert len(mock_context.search_queries) > 0

    @patch("backend.pipeline.stages.planning.openai_client")
    async def test_planning_handles_failure(self, mock_openai, mock_context):
        """Planning stage should add warning on failure."""
        from backend.pipeline.stages.planning import stage_1_planning

        mock_openai.plan_job.side_effect = Exception("API error")

        await stage_1_planning(mock_context)

        mock_context.add_warning.assert_called()


class TestQualityGateStage:
    """Tests for stage_3_5_quality_gate."""

    async def test_quality_gate_filters_sources(self, mock_context):
        """Quality gate should filter low-quality sources."""
        from backend.pipeline.stages.discovery import stage_3_5_quality_gate

        mock_context.sources = [
            {"url": "https://example.com/article", "type": "article"},
            {"url": "https://facebook.com/post", "type": "social"},  # Should filter
        ]

        await stage_3_5_quality_gate(mock_context)

        # Quality gate should filter social media
        assert len(mock_context.filtered_sources) <= len(mock_context.sources)
```

### Step 2: Backend - Extraction Tests (1.5h)

Create `backend/tests/test_extraction.py`:

```python
# backend/tests/test_extraction.py
import pytest
from backend.pipeline.extraction.deduplication import deduplicate_claims
from backend.pipeline.extraction.chunking import chunk_transcript_text


class TestClaimDeduplication:
    """Tests for claim deduplication logic."""

    def test_dedupe_identical_claims(self):
        """Identical claims should be deduplicated."""
        claims = [
            {"id": "1", "text": "The sky is blue", "score": 0.9},
            {"id": "2", "text": "The sky is blue", "score": 0.8},
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 1
        assert result[0]["score"] == 0.9  # Keep higher score

    def test_dedupe_similar_claims(self):
        """Similar claims (>0.7 Jaccard) should be deduplicated."""
        claims = [
            {"id": "1", "text": "The company reported record profits", "score": 0.9},
            {"id": "2", "text": "The company reported high profits", "score": 0.8},
        ]

        result = deduplicate_claims(claims, threshold=0.7)

        assert len(result) == 1

    def test_dedupe_different_claims(self):
        """Different claims should not be deduplicated."""
        claims = [
            {"id": "1", "text": "The sky is blue", "score": 0.9},
            {"id": "2", "text": "Water is essential for life", "score": 0.8},
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 2

    def test_dedupe_empty_list(self):
        """Empty list should return empty."""
        result = deduplicate_claims([])
        assert result == []

    def test_dedupe_single_claim(self):
        """Single claim should return unchanged."""
        claims = [{"id": "1", "text": "Test claim", "score": 0.9}]
        result = deduplicate_claims(claims)
        assert result == claims


class TestChunking:
    """Tests for transcript chunking."""

    def test_chunk_short_text(self):
        """Short text should be single chunk."""
        text = "This is a short text."
        chunks = chunk_transcript_text(text, min_words=100)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_long_text(self):
        """Long text should be split into chunks."""
        words = ["word"] * 2500  # ~10 minutes of transcript
        text = " ".join(words)
        chunks = chunk_transcript_text(text, min_words=1200)

        assert len(chunks) > 1
        for chunk in chunks:
            word_count = len(chunk.split())
            assert word_count <= 1500  # Max words per chunk

    def test_chunk_preserves_content(self):
        """Chunking should preserve all content."""
        text = "The quick brown fox jumps over the lazy dog."
        chunks = chunk_transcript_text(text, min_words=3)

        reconstructed = " ".join(chunks)
        assert len(reconstructed) >= len(text) - 10  # Allow small overlap
```

### Step 3: Backend - Quality Gate Tests (1h)

Create `backend/tests/test_quality_gate.py`:

```python
# backend/tests/test_quality_gate.py
import pytest
from backend.pipeline.quality_gate.scoring import calculate_quality_score
from backend.pipeline.quality_gate.filtering import check_hard_rejection
from backend.pipeline.quality_gate.models import Source


class TestQualityScoring:
    """Tests for source quality scoring."""

    def test_high_quality_source(self):
        """High-quality source should score high."""
        source = Source(
            url="https://reuters.com/article/test",
            type="article",
            title="Breaking News Report",
            domain="reuters.com",
        )

        score = calculate_quality_score(source)

        assert score >= 0.7

    def test_low_quality_source(self):
        """Low-quality source should score low."""
        source = Source(
            url="https://example.blogspot.com/spam",
            type="blog",
            title="",
            domain="example.blogspot.com",
        )

        score = calculate_quality_score(source)

        assert score < 0.5

    def test_domain_whitelist_bonus(self):
        """Whitelisted domains should get bonus."""
        whitelisted = Source(
            url="https://nytimes.com/article",
            type="article",
            domain="nytimes.com",
        )
        generic = Source(
            url="https://random-blog.com/article",
            type="article",
            domain="random-blog.com",
        )

        whitelist_score = calculate_quality_score(whitelisted)
        generic_score = calculate_quality_score(generic)

        assert whitelist_score > generic_score


class TestHardRejection:
    """Tests for hard rejection rules."""

    def test_reject_social_media(self):
        """Social media URLs should be rejected."""
        assert check_hard_rejection("https://facebook.com/post/123") is True
        assert check_hard_rejection("https://twitter.com/status/123") is True
        assert check_hard_rejection("https://instagram.com/p/123") is True

    def test_reject_search_engines(self):
        """Search engine URLs should be rejected."""
        assert check_hard_rejection("https://google.com/search?q=test") is True
        assert check_hard_rejection("https://bing.com/search?q=test") is True

    def test_accept_valid_articles(self):
        """Valid article URLs should be accepted."""
        assert check_hard_rejection("https://reuters.com/article/123") is False
        assert check_hard_rejection("https://bbc.com/news/article") is False

    def test_reject_paywall_patterns(self):
        """Paywall patterns should be rejected."""
        assert check_hard_rejection("https://example.com/login") is True
        assert check_hard_rejection("https://example.com/subscribe") is True
```

### Step 4: Frontend - Store Error Handling Tests (2h)

Create `frontend/__tests__/stores/admin.test.ts`:

```typescript
// frontend/__tests__/stores/admin.test.ts
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAdminStore } from '../../store/admin';

// Mock fetch
global.fetch = jest.fn();

describe('AdminStore', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset store state
    useAdminStore.setState({
      stats: null,
      users: [],
      jobs: [],
      errorLogs: [],
      error: null,
      isLoadingStats: false,
    });
  });

  describe('fetchStats', () => {
    it('should set error state on API failure', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchStats();
      });

      expect(result.current.error).toBe('Network error');
      expect(result.current.isLoadingStats).toBe(false);
    });

    it('should clear error on successful fetch', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ total_jobs: 10, total_users: 5 }),
      });

      const { result } = renderHook(() => useAdminStore());

      // Set initial error
      useAdminStore.setState({ error: 'Previous error' });

      await act(async () => {
        await result.current.fetchStats();
      });

      expect(result.current.error).toBe(null);
      expect(result.current.stats).toEqual({ total_jobs: 10, total_users: 5 });
    });

    it('should handle timeout errors', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('AbortError'));

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchStats();
      });

      expect(result.current.error).toContain('timeout');
    });
  });

  describe('cancelJob', () => {
    it('should update job status optimistically', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

      const { result } = renderHook(() => useAdminStore());

      useAdminStore.setState({
        jobs: [{ id: 'job-1', status: 'running' }],
      });

      await act(async () => {
        await result.current.cancelJob('job-1');
      });

      const job = result.current.jobs.find((j) => j.id === 'job-1');
      expect(job?.status).toBe('cancelled');
    });

    it('should handle non-existent job gracefully', async () => {
      const { result } = renderHook(() => useAdminStore());

      // No jobs in state
      useAdminStore.setState({ jobs: [] });

      // Should not throw
      await act(async () => {
        await result.current.cancelJob('non-existent');
      });

      expect(result.current.jobs).toEqual([]);
    });
  });
});
```

Create `frontend/__tests__/stores/jobs.test.ts` (expand existing):

```typescript
// frontend/__tests__/stores/jobs.test.ts
import { renderHook, act } from '@testing-library/react';
import { useJobsStore } from '../../store/jobs';

global.fetch = jest.fn();

describe('JobsStore Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useJobsStore.setState({
      jobs: [],
      isLoading: false,
      error: null,
    });
  });

  describe('fetchJobs', () => {
    it('should set error on 401 response', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.error).toContain('Session expired');
      expect(result.current.jobs).toEqual([]);
    });

    it('should handle malformed JSON response', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.error).toContain('Invalid response');
    });
  });

  describe('refreshJob', () => {
    it('should not overwrite with undefined fields', async () => {
      const existingJob = {
        id: 'job-1',
        status: 'running',
        stage: 'extraction',
        progress_percent: 50,
        title: 'Test Job',
      };

      useJobsStore.setState({ jobs: [existingJob] });

      // API returns partial data
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'completed' }),
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.refreshJob('job-1');
      });

      const job = result.current.jobs.find((j) => j.id === 'job-1');
      expect(job?.status).toBe('completed');
      expect(job?.title).toBe('Test Job'); // Preserved
    });
  });
});
```

### Step 5: Frontend - Validation Tests (30 min)

Create `frontend/__tests__/lib/validation.test.ts`:

```typescript
// frontend/__tests__/lib/validation.test.ts
import {
  validateUsername,
  validatePrompt,
  validateDriveFolderUrl,
  validateYouTubeUrls,
} from '../../lib/validation';

describe('Validation Utilities', () => {
  describe('validateUsername', () => {
    it('should reject short usernames', () => {
      const result = validateUsername('ab');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('at least 3');
    });

    it('should reject long usernames', () => {
      const result = validateUsername('a'.repeat(31));
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('exceed');
    });

    it('should reject invalid characters', () => {
      const result = validateUsername('user@name!');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('letters, numbers');
    });

    it('should accept valid usernames', () => {
      expect(validateUsername('valid_user-123').isValid).toBe(true);
      expect(validateUsername('john_doe').isValid).toBe(true);
    });
  });

  describe('validatePrompt', () => {
    it('should reject empty prompts', () => {
      const result = validatePrompt('');
      expect(result.isValid).toBe(false);
    });

    it('should reject whitespace-only prompts', () => {
      const result = validatePrompt('   ');
      expect(result.isValid).toBe(false);
    });

    it('should accept valid prompts', () => {
      const result = validatePrompt('Research AI ethics in healthcare');
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateYouTubeUrls', () => {
    it('should accept valid YouTube URLs', () => {
      const result = validateYouTubeUrls('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
      expect(result.isValid).toBe(true);
    });

    it('should reject non-YouTube URLs', () => {
      const result = validateYouTubeUrls('https://vimeo.com/123456');
      expect(result.isValid).toBe(false);
    });

    it('should accept multiple valid URLs', () => {
      const urls = `https://youtube.com/watch?v=abc
https://youtu.be/def`;
      const result = validateYouTubeUrls(urls);
      expect(result.isValid).toBe(true);
    });
  });
});
```

### Step 6: Run All Tests (30 min)

```bash
# Backend
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate
pytest -v

# Frontend
cd frontend
npm test
```

## Related Code Files

### Files to Create

| File | Description |
|------|-------------|
| `backend/tests/test_pipeline_stages.py` | Stage unit tests |
| `backend/tests/test_extraction.py` | Extraction unit tests |
| `backend/tests/test_quality_gate.py` | Quality gate tests |
| `frontend/__tests__/stores/admin.test.ts` | Admin store tests |
| `frontend/__tests__/lib/validation.test.ts` | Validation tests |

### Files to Modify

| File | Description |
|------|-------------|
| `frontend/__tests__/stores/jobs.test.ts` | Expand with error tests |

## Todo List

### Backend Tests
- [ ] Create test_pipeline_stages.py
- [ ] Add tests for stage_0_initialize
- [ ] Add tests for stage_1_planning
- [ ] Add tests for stage_3_5_quality_gate
- [ ] Create test_extraction.py
- [ ] Add tests for deduplicate_claims
- [ ] Add tests for chunk_transcript_text
- [ ] Create test_quality_gate.py
- [ ] Add tests for calculate_quality_score
- [ ] Add tests for check_hard_rejection

### Frontend Tests
- [ ] Create admin.test.ts
- [ ] Add tests for fetchStats error handling
- [ ] Add tests for cancelJob error handling
- [ ] Expand jobs.test.ts
- [ ] Add tests for 401 handling
- [ ] Add tests for JSON parsing errors
- [ ] Create validation.test.ts
- [ ] Add tests for validateUsername
- [ ] Add tests for validatePrompt
- [ ] Add tests for validateYouTubeUrls

### Verification
- [ ] Run pytest - all pass
- [ ] Run npm test - all pass
- [ ] Generate coverage report

## Success Criteria

- [ ] All new tests pass
- [ ] No regressions in existing tests
- [ ] Backend coverage for critical paths >80%
- [ ] Frontend store error handling tested
- [ ] Validation utilities 100% covered

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Flaky async tests | Medium | Medium | Use proper waitFor/act |
| Mock leakage | Medium | Low | beforeEach cleanup |
| CI timeout | Low | Medium | Parallelize tests |

## Next Steps

After completing this phase:
1. Set up coverage reporting in CI
2. Add integration tests for full pipeline
3. Consider E2E tests with Playwright (future)
