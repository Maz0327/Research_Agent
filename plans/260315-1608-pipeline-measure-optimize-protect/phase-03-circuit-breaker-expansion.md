# Phase 3: Circuit Breaker Expansion

## Context Links

- [Plan Overview](plan.md)
- [Phase 1: Quality Score](phase-01-composite-quality-score.md) (independent)
- [Phase 2: Prompt Optimization](phase-02-prompt-optimization-loop.md) (independent, can run in parallel)
- [Research: Circuit Breaker Patterns](research/researcher-02-circuit-breaker-patterns.md)

## Overview

Extract the existing ad-hoc circuit breaker in `llm_judge.py` (`_PROVIDER_DISABLED` dict) into a shared `CircuitBreaker` class with proper CLOSED/OPEN/HALF_OPEN states. Apply it to transcript acquisition and Gemini extraction -- the two other external-call-heavy stages that currently have no circuit breaker protection.

## Key Insights

- `llm_judge.py` already has a module-level circuit breaker (`_PROVIDER_DISABLED: dict[str, str]`), but it's binary (on/off) with no recovery path -- provider stays disabled until worker restart
- Transcript acquisition has a 4-tier fallback chain (Supadata -> Whisper -> YouTube captions -> video_only) with NO circuit breaker -- each source retries all tiers even when a provider is known-down
- Semantic extraction uses ThreadPoolExecutor for parallel Gemini calls with retry logic but NO circuit breaker -- repeated Gemini failures waste time across all sources
- Research report recommends per-provider `ProviderCircuitBreaker` with CLOSED/OPEN/HALF_OPEN states and configurable thresholds
- The pipeline is synchronous (not async), so the implementation uses sync-compatible patterns (no asyncio)
- MetricsTracker currently only tracks LLM call counts and tokens -- no failure tracking

## Requirements

1. Shared `CircuitBreaker` class in `backend/pipeline/circuit_breaker.py`
2. States: CLOSED (normal), OPEN (blocking), HALF_OPEN (probing recovery)
3. Configurable per-provider: `failure_threshold`, `reset_timeout_seconds`, `success_threshold`
4. Apply to transcript acquisition fallback chain (3 providers: Supadata, Whisper, youtube_captions)
5. Apply to semantic extraction Gemini calls
6. Migrate `llm_judge.py` `_PROVIDER_DISABLED` to shared CircuitBreaker
7. Add `failure_count` and `failure_rate` to MetricsTracker
8. All circuit breakers are module-level (session-scoped, reset on worker restart) -- matches existing LLM Judge behavior

## Architecture

### CircuitBreaker Class

```python
class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    name: str
    failure_threshold: int = 3       # Failures before OPEN
    reset_timeout_seconds: int = 120  # Seconds before HALF_OPEN probe
    success_threshold: int = 1        # Successes in HALF_OPEN to reset

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig): ...
    def is_available(self) -> bool: ...
    def record_success(self) -> None: ...
    def record_failure(self, reason: str = "") -> None: ...
    def get_status(self) -> dict: ...
```

### Integration Points

```
transcript_acquisition.py
  _try_supadata()  -- guarded by CircuitBreaker("supadata")
  _try_whisper()   -- guarded by CircuitBreaker("whisper")
  _try_captions()  -- guarded by CircuitBreaker("youtube_captions")

semantic_extraction.py
  process_single_source() Gemini call -- guarded by CircuitBreaker("gemini")

llm_judge.py
  _try_openai_judge()  -- migrated from _PROVIDER_DISABLED to CircuitBreaker("gpt-4o")
  _try_kimi_judge()    -- new CircuitBreaker("kimi")
```

### Guard Pattern (sync, minimal change)

```python
# Before (transcript_acquisition.py):
def _try_supadata(video_url):
    try:
        result = client.get_transcript(...)
        return result["text"], None, cost
    except Exception as e:
        return None, f"Supadata error: {e}", 0.0

# After:
from backend.pipeline.circuit_breaker import get_breaker

def _try_supadata(video_url):
    breaker = get_breaker("supadata")
    if not breaker.is_available():
        return None, f"Supadata skipped (circuit open)", 0.0
    try:
        result = client.get_transcript(...)
        breaker.record_success()
        return result["text"], None, cost
    except Exception as e:
        breaker.record_failure(str(e))
        return None, f"Supadata error: {e}", 0.0
```

### Module-Level Registry

```python
# circuit_breaker.py
_BREAKERS: dict[str, CircuitBreaker] = {}

def get_breaker(name: str, **config_overrides) -> CircuitBreaker:
    """Get or create a session-scoped circuit breaker by name."""
    if name not in _BREAKERS:
        config = CircuitBreakerConfig(name=name, **config_overrides)
        _BREAKERS[name] = CircuitBreaker(config)
    return _BREAKERS[name]

def get_all_breaker_status() -> dict[str, dict]:
    """Return status of all breakers (for observability)."""
    return {name: b.get_status() for name, b in _BREAKERS.items()}
```

## Related Code Files

| File | Role |
|------|------|
| `backend/pipeline/circuit_breaker.py` | NEW: shared CircuitBreaker + registry |
| `backend/pipeline/llm_judge.py` | Migrate `_PROVIDER_DISABLED` to CircuitBreaker |
| `backend/pipeline/transcript_acquisition.py` | Add breakers to `_try_supadata`, `_try_whisper`, `_try_captions` |
| `backend/pipeline/stages/semantic_extraction.py` | Add Gemini breaker to `process_single_source()` |
| `backend/pipeline/iteration/metrics_tracker.py` | Add failure tracking fields |
| `backend/pipeline/stage_runner.py` | Read-only reference for error handling patterns |

## Implementation Steps

### 3.1: Create `backend/pipeline/circuit_breaker.py`

- Define `CircuitState` enum (CLOSED, OPEN, HALF_OPEN)
- Define `CircuitBreakerConfig` dataclass with defaults
- Implement `CircuitBreaker` class:
  - `is_available()`: CLOSED=True, OPEN=check timeout->HALF_OPEN, HALF_OPEN=True
  - `record_success()`: HALF_OPEN->CLOSED if success_threshold met, CLOSED->reset failure count
  - `record_failure(reason)`: increment, trip to OPEN if threshold met, HALF_OPEN->OPEN immediately
  - `get_status() -> dict`: name, state, failure_count, last_failure_at, last_failure_reason
- Implement module-level registry: `get_breaker(name, **overrides)`, `get_all_breaker_status()`
- Full type hints, docstrings, loguru logging on state transitions

### 3.2: Write unit tests for CircuitBreaker

- Test CLOSED -> OPEN after failure_threshold failures
- Test OPEN -> HALF_OPEN after reset_timeout
- Test HALF_OPEN -> CLOSED after success_threshold successes
- Test HALF_OPEN -> OPEN on failure
- Test `is_available()` returns correct bool for each state
- Test `get_breaker()` registry creates once, returns same instance
- Test `get_all_breaker_status()` returns all registered breakers

### 3.3: Integrate into `transcript_acquisition.py`

- Add `get_breaker` import
- Guard `_try_supadata()`: check `is_available()`, call `record_success()`/`record_failure()`
- Guard `_try_whisper()`: same pattern
- Guard YouTube captions tier: same pattern (use name `"youtube_captions"`)
- Configure thresholds: Supadata `failure_threshold=3`, Whisper `failure_threshold=2` (more expensive), youtube_captions `failure_threshold=5` (free, lenient)
- Log when circuit trips with provider name and reason

### 3.4: Integrate into `semantic_extraction.py`

- Add `get_breaker` import
- In `process_single_source()` (or the Gemini call wrapper), guard with `CircuitBreaker("gemini")`
- Configure: `failure_threshold=5` (Gemini is primary, be conservative), `reset_timeout_seconds=180`
- On circuit open, extraction falls through to existing error handling (source gets `parse_error` flag)
- Log circuit state in extraction warnings

### 3.5: Migrate `llm_judge.py` to shared CircuitBreaker

- Replace `_PROVIDER_DISABLED: dict[str, str] = {}` with `get_breaker()` calls
- In `_try_openai_judge()`:
  - Replace `if "GPT-4o" in _PROVIDER_DISABLED` with `if not get_breaker("gpt-4o").is_available()`
  - Replace `_PROVIDER_DISABLED["GPT-4o"] = "insufficient_quota"` with `get_breaker("gpt-4o").record_failure("insufficient_quota")`
  - Add `get_breaker("gpt-4o").record_success()` on success path
- In `_try_kimi_judge()`:
  - Add same circuit breaker pattern with `get_breaker("kimi")`
- Remove `_PROVIDER_DISABLED` dict entirely
- Keep existing try/except structure; circuit breaker wraps the availability check only

### 3.6: Add failure tracking to MetricsTracker

- Add `failure_count: int = 0` field
- Add `failed_providers: list[str] = field(default_factory=list)` field
- Add `record_failure(provider: str)` method
- Update `finalize()` to include failure data in IterationMetrics
- Add `failure_count` and `failed_providers` to IterationMetrics model (optional fields, backward compatible)

### 3.7: Write integration tests

- Test transcript acquisition skips provider when circuit is open
- Test semantic extraction handles Gemini circuit open gracefully
- Test LLM Judge fallback chain respects circuit breaker state
- Test MetricsTracker records failures

### 3.8: Verify existing tests pass

- `pytest backend/tests/ -v`
- Ensure no regressions in existing test assertions about `_PROVIDER_DISABLED`

## Todo List

- [ ] 3.1: Create `backend/pipeline/circuit_breaker.py`
- [ ] 3.2: Write unit tests for CircuitBreaker
- [ ] 3.3: Integrate into transcript_acquisition.py
- [ ] 3.4: Integrate into semantic_extraction.py
- [ ] 3.5: Migrate llm_judge.py to shared CircuitBreaker
- [ ] 3.6: Add failure tracking to MetricsTracker
- [ ] 3.7: Write integration tests
- [ ] 3.8: Run full test suite

## Success Criteria

- `CircuitBreaker` correctly transitions through CLOSED -> OPEN -> HALF_OPEN -> CLOSED
- Transcript acquisition skips known-down providers instantly (no wasted 4-6s per source)
- Gemini extraction stops hammering a down API after threshold failures
- LLM Judge uses shared CircuitBreaker instead of ad-hoc `_PROVIDER_DISABLED`
- `get_all_breaker_status()` returns observability data for all providers
- All existing tests pass without modification (backward compatible)
- New tests cover all state transitions and integration points

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing tests reference `_PROVIDER_DISABLED` directly | Test failure | Search for references; update test mocks to use `get_breaker()` |
| Circuit breaker too aggressive (low threshold) | Good provider skipped | Conservative defaults: 3-5 failures before trip, 120s reset |
| Thread safety in ThreadPoolExecutor (semantic extraction) | Race condition | CircuitBreaker uses simple counters; worst case is off-by-one on trip threshold -- acceptable |
| `reset_timeout_seconds` too short | Provider hammered during outage | Default 120s; Gemini gets 180s |
| Breaking change to IterationMetrics model | Frontend errors | New fields are Optional with defaults; backward compatible |

## Security Considerations

- No new external API calls introduced
- Circuit breaker state is in-memory only (not persisted); resets on worker restart
- No user input flows into circuit breaker configuration
- Provider failure reasons logged via loguru (may contain API error messages -- already the case in existing code)

## Next Steps

After Phase 3:
- Add circuit breaker status to job metadata for observability
- Future: configurable thresholds via environment variables
- Future: persistent circuit breaker state across worker restarts (Redis-backed)
- Future: circuit breaker dashboard in admin panel
