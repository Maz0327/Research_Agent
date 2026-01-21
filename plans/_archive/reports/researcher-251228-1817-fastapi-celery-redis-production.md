# FastAPI + Celery + Redis Production Architecture (2025)

## API Design & Error Handling

**REST Best Practices**:
- Use standardized HTTP status codes with descriptive error bodies
- Implement request/response validation with Pydantic (automatic with FastAPI)
- Return consistent JSON error format across all endpoints
- Use JWT (OAuth2 + Password flow) or API keys for stateless authentication

**Error Handling Pattern**:
```python
try:
    result = await external_call()
except SpecificError as e:
    logger.error(f"Failed: {e}")
    raise HTTPException(status_code=500, detail="Service error")
```

**Rate Limiting**:
- Use `slowapi` or Redis-based rate limiting
- Implement per-user quotas via API keys
- Return proper 429 (Too Many Requests) responses

---

## Celery Task Patterns

**Retry Strategy** (Exponential Backoff):
```python
@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 2})
def process_task(self):
    try:
        # Task work
    except Exception as e:
        countdown = 2 ** self.request.retries  # Exponential backoff
        raise self.retry(exc=e, countdown=countdown)
```

**Key Configuration**:
- `task_acks_late=True` - Acknowledge after execution (prevents loss on worker crash)
- `worker_prefetch_multiplier=1` - Better task distribution
- `task_serializer="json"`, `result_serializer="json"` - Safe serialization
- Task soft/hard timeout limits prevent resource exhaustion

**Result Backend**:
- Use Redis for both broker + backend (simplifies architecture)
- Configure with TTL for automatic cleanup
- Consider Dead Letter Queues for permanently failed tasks

**Monitoring** (Flower):
- Real-time task tracking, worker health, queue depth
- Set alerts: failure rate >5%, queue bottlenecks, timeout patterns
- Use Sentry/Prometheus for structured logging with correlation IDs

---

## Security (OWASP API Top 10)

**Authentication**:
- **JWT + OAuth2**: Stateless, scalable (preferred for microservices)
- **API Keys**: Simple for internal/machine-to-machine
- Always use HTTPS in production
- Implement token expiration + refresh mechanism

**Input Validation**:
- Pydantic handles automatic validation (type safety)
- Define strict schemas, reject unknown fields
- Sanitize any dynamic database queries

**CORS & Authorization**:
- Configure CORS restrictively (only needed origins)
- Implement role-based access control (RBAC)
- Separate authentication (who) from authorization (what)

**Key Vulnerabilities to Address**:
- A1: Broken Authentication → Use JWT + secure token storage
- A2: Broken Authorization → RBAC, proper scope validation
- A3: Injection → Parameterized queries, input validation
- A6: Rate Limiting → Implement per-endpoint quotas
- A7: API Security → Use automated tools (Bandit, OWASP ZAP)

---

## Performance Optimization

**Connection Pooling** (Critical):
```python
# PostgreSQL with asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://...",
    pool_size=20,  # Keep connections alive
    max_overflow=10,  # Extra connections if needed
    pool_pre_ping=True,  # Verify connection health
    echo=False
)
```

**Best Practices**:
- Use async drivers: `asyncpg` (PostgreSQL), `aiomysql` (MySQL)
- Reuse connections across requests (don't create per-request)
- Set `max_inactive_connection_lifetime=300` to prevent stale connections
- Use `pool_pre_ping=True` to verify connection health

**Async I/O Patterns**:
- Define handlers as `async def` (non-blocking)
- Only use regular `def` for CPU-heavy work (offloads to threadpool)
- Avoid blocking operations in async contexts
- Use `asyncio` for concurrent external API calls

**Caching Strategy**:
- Redis for distributed caching (shared across workers)
- In-memory cache (functools.lru_cache) for read-heavy data
- Set appropriate TTLs, implement cache invalidation
- Don't cache CPU-intensive work—cache I/O results only

**Deployment**:
- Run multiple Uvicorn worker processes (`--workers N`)
- Use reverse proxy (nginx) for load balancing
- Monitor worker CPU/memory, scale horizontally as needed

---

## Code Organization

**Project Structure**:
```
backend/
├── app/main.py           # API + route definitions
├── pipeline/             # Business logic (stages, context)
├── integrations/         # External API clients
├── models/               # Pydantic schemas
├── state/                # Job persistence
├── config.py             # Configuration management
└── worker.py             # Celery task orchestration
```

**Dependency Injection**:
- Use FastAPI's `Depends()` for middleware-like dependencies
- Inject config, database, services into endpoints
- Makes code testable, reduces globals

**Separation of Concerns**:
- API layer: Request validation, routing, HTTP responses
- Business logic: Pipeline stages, extraction, synthesis
- Data access: State/database operations
- External services: Dedicated integration clients

---

## Unresolved Questions

1. **Celery Beat Scheduling**: Production gotchas for distributed Beat schedulers (lock management)?
2. **Database Transactions in Async Context**: Best patterns for Celery tasks with multi-stage database operations?
3. **Cost Tracking Integration**: How to decouple cost accounting from API response path?

---

## Sources

- [Celery - FastAPI + Celery Integration](https://derlin.github.io/introduction-to-fastapi-and-celery/03-celery/)
- [Production FastAPI Celery Redis Guide](https://python.elitedev.in/python/production-ready-background-task-processing-celery-redis-and-fastapi-integration-guide-2024-80ddc2f9/)
- [FastAPI Security Best Practices 2025](https://toxigon.com/python-fastapi-security-best-practices-2025)
- [Celery Task Resilience & Retries](https://blog.gitguardian.com/celery-tasks-retries-errors/)
- [FastAPI Async Connection Pooling](https://blog.poespas.me/posts/2024/08/08/fastapi-async-connection-pooling/)
