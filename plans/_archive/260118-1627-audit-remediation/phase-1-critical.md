# Phase 1: Critical Issues Implementation

**Priority:** IMMEDIATE
**Total Effort:** ~5h
**Issues:** C1, C2, C3

---

## C1: Add Gemini Timeout Configuration

**File:** `backend/integrations/gemini_client.py`
**Lines:** 542-554
**Risk:** Workers blocked indefinitely on long-running LLM calls

### Current Code (line 550-554)
```python
response = self._client.models.generate_content(
    model=model,
    contents=prompt,
    config=config,
)
```

### Implementation Steps

1. Check if Gemini SDK supports timeout in `GenerateContentConfig`:
   - SDK docs: `google.genai.types.GenerateContentConfig`
   - If no native timeout, wrap with `asyncio.wait_for()` or `concurrent.futures`

2. Add timeout to config or wrap call:
   ```python
   # Option A: If SDK supports timeout parameter
   config = types.GenerateContentConfig(
       timeout=settings.timeout_api_default,  # 30s
       ...
   )

   # Option B: If no SDK support, wrap with timeout
   import concurrent.futures

   with concurrent.futures.ThreadPoolExecutor() as executor:
       future = executor.submit(
           self._client.models.generate_content,
           model=model,
           contents=prompt,
           config=config,
       )
       try:
           response = future.result(timeout=settings.timeout_api_default)
       except concurrent.futures.TimeoutError:
           raise RuntimeError(f"Gemini request timed out after {settings.timeout_api_default}s")
   ```

3. Apply same pattern to all Gemini calls:
   - `generate_json()` (line 550)
   - `analyze_youtube_video()` (line 610+)
   - Any other `generate_content` calls

### Tests
- [ ] Add test for timeout behavior
- [ ] Verify existing tests pass

---

## C2: Add OpenAI Timeout Configuration

**File:** `backend/integrations/openai_client.py`
**Lines:** 193, and all `OpenAI()` instantiations
**Risk:** Job planning blocked indefinitely

### Current Code (line 193)
```python
client = OpenAI(api_key=settings.openai_api_key)
```

### Implementation Steps

1. Add timeout to OpenAI client instantiation:
   ```python
   client = OpenAI(
       api_key=settings.openai_api_key,
       timeout=settings.timeout_api_default,  # 30s
   )
   ```

2. Find all `OpenAI()` instantiations and update:
   ```bash
   grep -n "OpenAI(" backend/integrations/openai_client.py
   ```

3. Consider creating a singleton/factory for consistent configuration:
   ```python
   def get_openai_client() -> OpenAI:
       """Get configured OpenAI client with timeout."""
       return OpenAI(
           api_key=settings.openai_api_key,
           timeout=settings.timeout_api_default,
       )
   ```

### Tests
- [ ] Add test for timeout behavior
- [ ] Verify existing tests pass

---

## C3: Implement Circuit Breaker Pattern

**File:** `backend/utils/rate_limiter.py`
**Lines:** 236-273
**Risk:** Failed services continue receiving retries, wasted quota

### Circuit Breaker States
```
CLOSED (normal) → [5 failures] → OPEN (reject all)
OPEN → [60s cooldown] → HALF_OPEN (test 1 request)
HALF_OPEN → [success] → CLOSED
HALF_OPEN → [failure] → OPEN
```

### Implementation Steps

1. Add circuit breaker state to `RateLimiterState`:
   ```python
   class CircuitState(Enum):
       CLOSED = "closed"      # Normal operation
       OPEN = "open"          # Rejecting requests
       HALF_OPEN = "half_open"  # Testing recovery

   @dataclass
   class RateLimiterState:
       last_request_time: float = 0.0
       request_count: int = 0
       failure_count: int = 0
       success_count: int = 0
       last_failure_time: float = 0.0
       # Circuit breaker additions
       circuit_state: CircuitState = CircuitState.CLOSED
       circuit_opened_at: float = 0.0
       consecutive_failures: int = 0
   ```

2. Add circuit breaker configuration:
   ```python
   @dataclass
   class RateLimitConfig:
       ...
       circuit_failure_threshold: int = 5   # Open after 5 failures
       circuit_cooldown_seconds: float = 60.0  # Wait 60s before testing
   ```

3. Add circuit breaker check before request:
   ```python
   def check_circuit_breaker(api_name: str) -> bool:
       """Check if circuit breaker allows request.

       Returns:
           True if request allowed, raises CircuitOpenError if blocked
       """
       state = _get_state(api_name)
       config = get_rate_limit_config(api_name)
       now = time.time()

       if state.circuit_state == CircuitState.OPEN:
           # Check if cooldown expired
           if now - state.circuit_opened_at >= config.circuit_cooldown_seconds:
               state.circuit_state = CircuitState.HALF_OPEN
               logger.info(f"{api_name} circuit breaker: OPEN → HALF_OPEN")
               return True
           raise CircuitOpenError(
               f"{api_name} circuit open, retry after "
               f"{config.circuit_cooldown_seconds - (now - state.circuit_opened_at):.0f}s"
           )

       return True
   ```

4. Update `record_failure()` to trip circuit:
   ```python
   def record_failure(api_name: str) -> None:
       state = _get_state(api_name)
       config = get_rate_limit_config(api_name)

       state.failure_count += 1
       state.consecutive_failures += 1
       state.last_failure_time = time.time()

       # Trip circuit breaker if threshold exceeded
       if (state.circuit_state == CircuitState.CLOSED and
           state.consecutive_failures >= config.circuit_failure_threshold):
           state.circuit_state = CircuitState.OPEN
           state.circuit_opened_at = time.time()
           logger.warning(f"{api_name} circuit breaker OPENED after {state.consecutive_failures} failures")

       # If half-open and failed, go back to open
       elif state.circuit_state == CircuitState.HALF_OPEN:
           state.circuit_state = CircuitState.OPEN
           state.circuit_opened_at = time.time()
           logger.warning(f"{api_name} circuit breaker: HALF_OPEN → OPEN (test failed)")
   ```

5. Update `record_success()` to reset circuit:
   ```python
   def record_success(api_name: str) -> None:
       state = _get_state(api_name)

       state.success_count += 1
       state.consecutive_failures = 0  # Reset failure count

       # If half-open, close circuit
       if state.circuit_state == CircuitState.HALF_OPEN:
           state.circuit_state = CircuitState.CLOSED
           logger.info(f"{api_name} circuit breaker: HALF_OPEN → CLOSED (test passed)")
   ```

6. Integrate into `with_rate_limit` decorator:
   ```python
   def with_rate_limit(api_name: str):
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               # Check circuit breaker FIRST
               check_circuit_breaker(api_name)

               # Then proceed with rate limiting
               config = get_rate_limit_config(api_name)
               ...
   ```

7. Add `CircuitOpenError` exception:
   ```python
   class CircuitOpenError(Exception):
       """Raised when circuit breaker is open."""
       pass
   ```

### Tests
- [ ] Test circuit opens after 5 consecutive failures
- [ ] Test circuit stays open during cooldown
- [ ] Test circuit transitions to half-open after cooldown
- [ ] Test circuit closes on successful test request
- [ ] Test circuit re-opens on failed test request
- [ ] Verify existing rate limiter tests pass

---

## Verification Checklist

After completing Phase 1:
- [ ] `pytest backend/tests/ -v` passes
- [ ] No new warnings or errors
- [ ] Commit: `fix: Add timeout configuration and circuit breaker (C1, C2, C3)`
