# Circuit Breaker Patterns for AI/LLM Pipelines
**Research Date:** 2026-03-15 | **Scope:** Multi-provider fallback, async recovery, metrics tracking

---

## 1. Multi-Provider Fallback Chains

**Pattern:** Iterable provider chain with automatic failover to next provider on threshold breach.

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Callable, Any
from datetime import datetime, timedelta
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class ProviderConfig:
    name: str
    failure_threshold: int = 5  # Failures before trip
    success_threshold: int = 2  # Successes before reset
    reset_timeout: int = 60     # Seconds before half-open
    half_open_calls: int = 1    # Probe requests allowed

@dataclass
class CircuitStats:
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    last_failure_at: datetime | None = None
    last_state_change: datetime = None

    def __post_init__(self):
        if self.last_state_change is None:
            self.last_state_change = datetime.utcnow()

class ProviderCircuitBreaker:
    """Session-scoped circuit breaker for single provider."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()

    def is_available(self) -> bool:
        """Check if provider accepts requests."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = (datetime.utcnow() - self.stats.last_state_change).total_seconds()
            if elapsed >= self.config.reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        # HALF_OPEN: allow probes
        return True

    def record_success(self):
        """Record successful call."""
        self.stats.success_count += 1
        self.stats.total_calls += 1

        if self.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.config.success_threshold:
                self._reset()
        elif self.state == CircuitState.CLOSED:
            self.stats.failure_count = 0

    def record_failure(self):
        """Record failed call, trip if threshold exceeded."""
        self.stats.failure_count += 1
        self.stats.total_calls += 1
        self.stats.last_failure_at = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.CLOSED:
            if self.stats.failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _reset(self):
        """Reset to CLOSED on successful recovery."""
        self._transition_to(CircuitState.CLOSED)
        self.stats.failure_count = 0
        self.stats.success_count = 0

    def _transition_to(self, new_state: CircuitState):
        """Track state transition."""
        self.state = new_state
        self.stats.last_state_change = datetime.utcnow()
        # Log: f"Provider {self.config.name} → {new_state.value}"
```

---

## 2. Async Fallback Chain Manager

**Pattern:** Iterate providers in order; trip individual circuit breakers without blocking pipeline.

```python
class FallbackChainManager:
    """Multi-provider with per-provider circuit breakers."""

    def __init__(self, providers: List[ProviderConfig]):
        self.breakers = {
            p.name: ProviderCircuitBreaker(p) for p in providers
        }
        self.providers = [p.name for p in providers]

    async def try_providers(
        self,
        call_fn: Callable[[str], Any],  # async (provider_name) -> result
        skip_unavailable: bool = True
    ) -> tuple[str | None, Any]:
        """Try each provider until success; return (provider_name, result)."""
        last_error = None

        for provider_name in self.providers:
            breaker = self.breakers[provider_name]

            if not breaker.is_available():
                if skip_unavailable:
                    continue
                # Log: f"Skipping {provider_name}: circuit {breaker.state.value}"
                continue

            try:
                result = await call_fn(provider_name)
                breaker.record_success()
                return (provider_name, result)
            except Exception as e:
                breaker.record_failure()
                last_error = e
                # Log: f"Provider {provider_name} failed: {e}"
                continue

        # All providers exhausted
        raise RuntimeError(f"All providers failed. Last: {last_error}")

    def get_metrics(self) -> dict:
        """Return health summary for all providers."""
        return {
            p: {
                "state": self.breakers[p].state.value,
                "calls": self.breakers[p].stats.total_calls,
                "failures": self.breakers[p].stats.failure_count,
                "available": self.breakers[p].is_available(),
            }
            for p in self.providers
        }
```

---

## 3. Failure Rate Tracking & Metrics

**Pattern:** Sliding window + threshold enforcement for trip decisions.

```python
from collections import deque

class MetricsTracker:
    """Per-provider metrics with rolling failure percentage."""

    def __init__(self, window_size: int = 20):
        self.window: deque[bool] = deque(maxlen=window_size)  # True=success, False=fail
        self.failure_threshold: float = 0.5  # Trip at 50% failure rate

    def record_call(self, success: bool):
        """Add result to rolling window."""
        self.window.append(success)

    def failure_rate(self) -> float:
        """Calculate rolling failure percentage."""
        if not self.window:
            return 0.0
        return sum(1 for s in self.window if not s) / len(self.window)

    def should_trip(self) -> bool:
        """True if failure rate exceeds threshold."""
        return self.failure_rate() >= self.failure_threshold

    def report(self) -> dict:
        """Metrics snapshot."""
        return {
            "total_calls": len(self.window),
            "failures": sum(1 for s in self.window if not s),
            "failure_rate": self.failure_rate(),
            "should_trip": self.should_trip(),
        }
```

---

## 4. Async Autoresearch Loop with Recovery

**Pattern:** Trial → record → decision loop with exponential backoff on circuit recovery.

```python
class AsyncAutoresearchLoop:
    """Autoresearch with provider recovery loop."""

    def __init__(self, chain_mgr: FallbackChainManager):
        self.chain = chain_mgr
        self.backoff_base = 1.0  # Initial backoff: 1 second
        self.backoff_max = 60.0  # Max backoff: 60 seconds

    async def search_with_recovery(
        self,
        query: str,
        max_iterations: int = 5,
    ) -> str:
        """Execute search with automatic recovery attempts."""
        iteration = 0
        backoff = self.backoff_base

        while iteration < max_iterations:
            try:
                # Try all available providers
                provider, result = await self.chain.try_providers(
                    lambda p: self._search_provider(p, query)
                )
                return result
            except RuntimeError as e:
                iteration += 1
                if iteration >= max_iterations:
                    raise

                # Log recovery attempt
                # logger.warning(f"Iteration {iteration}: {e}. Waiting {backoff}s...")

                # Check if any circuit is in HALF_OPEN (recovering)
                recovering = [
                    p for p, b in self.chain.breakers.items()
                    if b.state == CircuitState.HALF_OPEN
                ]

                if recovering:
                    # Wait for probe period; probes happen in is_available()
                    await asyncio.sleep(min(backoff, 5.0))
                    backoff = min(backoff * 1.5, self.backoff_max)
                else:
                    # No recovery in progress; wait full backoff
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 1.5, self.backoff_max)

        raise RuntimeError(f"Max iterations ({max_iterations}) exceeded")

    async def _search_provider(self, provider: str, query: str) -> str:
        """Dummy provider call."""
        # Simulate call
        await asyncio.sleep(0.1)
        return f"Result from {provider}"
```

---

## 5. Best Practices Summary

| Concern | Practice |
|---------|----------|
| **Trip Decision** | Use failure rate + count threshold (both must trigger) |
| **Half-Open** | Allow 1–2 probe requests; reset if ANY succeeds |
| **Backoff** | Exponential (1s → 2s → 4s) capped at reset_timeout |
| **Metrics** | Rolling window (20–50 calls) + real-time failure % |
| **Async** | Trip decisions non-blocking; probes within is_available() |
| **Session Scope** | One CircuitBreaker instance per provider per request lifecycle |
| **Recovery** | Automatic via HALF_OPEN; no manual reset needed |

---

## Key Takeaways

1. **Per-provider circuit breakers** isolate failures; one failing provider doesn't block fallbacks.
2. **Half-open state** is automatic recovery; trips trigger after reset_timeout without manual intervention.
3. **Failure rate tracking** (not just counts) prevents brittle thresholds on low-traffic providers.
4. **Async-friendly trip logic** uses is_available() checks; actual calls try/catch separately.
5. **Autoresearch loops** iterate with backoff, leveraging HALF_OPEN probes for natural recovery.

---

## Sources

- [aiobreaker · PyPI](https://pypi.org/project/aiobreaker/)
- [circuitbreaker - Python Circuit Breaker pattern implementation](https://pypi.org/project/circuitbreaker/)
- [GitHub - danielfm/pybreaker: Python implementation of the Circuit Breaker pattern](https://github.com/danielfm/pybreaker)
- [Retries, fallbacks, and circuit breakers in LLM apps: what to use when](https://portkey.ai/blog/retries-fallbacks-and-circuit-breakers-in-llm-apps/)
- [Handling Errors Gracefully with Asyncio Retries | ProxiesAPI](https://proxiesapi.com/articles/handling-errors-gracefully-with-asyncio-retries)
- [Tenacity — Tenacity documentation](https://tenacity.readthedocs.io/)
- [How to Implement Circuit Breakers in Python](https://oneuptime.com/blog/post/2026-01-23-python-circuit-breakers/view)
- [Implementing the Circuit Breaker Pattern in Python Microservices with PyBreaker](https://thebackenddevelopers.substack.com/p/implementing-the-circuit-breaker)
