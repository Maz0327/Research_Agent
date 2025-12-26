---
name: research-agent
description: Research Agent pipeline development skill. Activate when working on pipeline stages, integrations, job processing, documentary modes, or niche overlays. Trigger terms: pipeline, stage, integration, job, celery, worker, documentary, niche, quality gate.
allowed-tools: Read, Glob, Grep, Edit, Write, Bash
---

# Research Agent Development Skill

## Purpose

This skill provides specialized knowledge for developing the Research Agent system - an AI-powered documentary research platform that aggregates content from multiple sources and produces NotebookLM packets and documentary blueprints.

## When to Activate

Activate this skill when the task involves:
- Modifying pipeline stages
- Adding or updating integrations
- Working with job processing
- Configuring documentary modes
- Implementing niche overlays
- Quality gate development
- Cost tracking

## Architecture Overview

```
Backend Architecture:
├── backend/app/main.py       # FastAPI endpoints
├── backend/worker.py         # Celery task definitions
├── backend/pipeline/
│   ├── stages.py             # 11-stage pipeline
│   ├── context.py            # Shared state
│   ├── quality_gate.py       # Source filtering
│   ├── dual_output.py        # NotebookLM + Documentary
│   ├── documentary_intelligence.py
│   └── niche_loader.py       # Niche overlays
├── backend/integrations/     # External API clients
├── backend/models/           # Pydantic models
├── backend/state/            # Job storage
└── backend/config.py         # Configuration
```

## Pipeline Development

### Adding a New Stage

1. **Define stage function** in `stages.py`:
```python
async def stage_my_new_stage(ctx: PipelineContext) -> None:
    """Description of what this stage does."""
    logger.info(f"[{ctx.job_id}] Running my_new_stage")

    try:
        # Stage logic here
        result = await my_operation(ctx)
        ctx.my_result = result
    except Exception as e:
        ctx.add_warning(f"my_new_stage failed: {e}")
```

2. **Register in pipeline** in `worker.py`:
```python
stages = [
    # ... existing stages ...
    ("my_new_stage", stage_my_new_stage, 8.5),  # (name, func, progress)
]
```

3. **Add context field** in `context.py`:
```python
@dataclass
class PipelineContext:
    # ... existing fields ...
    my_result: list = field(default_factory=list)
```

### Mode-Specific Behavior

Check the mode in stage logic:
```python
mode = ctx.job_config.mode if ctx.job_config else DocumentaryMode.INVESTIGATION
mode_config = get_mode_config(mode)

if mode == DocumentaryMode.BREAKING_NEWS:
    # Fast, 72hr window
    pass
elif mode == DocumentaryMode.INVESTIGATION:
    # Deep verification
    pass
```

## Integration Development

### Adding a New Integration

1. **Create client** in `backend/integrations/my_client.py`:
```python
from loguru import logger
from backend.config import settings

class MyClient:
    def __init__(self):
        self.api_key = settings.require_my_api()

    async def fetch(self, query: str) -> dict:
        logger.info(f"MyAPI: {query[:50]}...")
        # Implementation
```

2. **Add config** in `backend/config.py`:
```python
MY_API_KEY: Optional[str] = None

def require_my_api(self) -> str:
    if not self.MY_API_KEY:
        raise ValueError("MY_API_KEY not configured")
    return self.MY_API_KEY
```

3. **Implement fallback** if applicable:
```python
try:
    result = await primary_client.fetch(query)
except PrimaryError:
    ctx.add_warning("Primary failed, using fallback")
    result = await fallback_client.fetch(query)
```

## Niche Overlay System

Niches customize mode behavior. Located in `backend/config/niches/`:

```yaml
# Example: downfalls.yaml
name: downfalls
description: Scandal and career decline research

mode_overrides:
  investigation:
    focus_areas:
      - public_statements
      - timeline_of_events
      - media_coverage
    additional_prompts:
      - "Identify turning points in their public perception"
```

## Quality Gate

The quality gate filters sources. Key functions in `quality_gate.py`:

- `canonicalize_url()` - Normalize URLs for deduplication
- `is_junk_source()` - Filter low-quality sources
- `score_source()` - Calculate quality score
- `filter_sources()` - Apply mode-specific floors

## Key Commands

```bash
# Run backend locally
uvicorn backend.app.main:app --reload

# Run Celery worker
celery -A backend.worker worker --loglevel=INFO

# Test endpoint
curl http://localhost:8000/health

# Create job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test topic", "pipeline": "quick"}'
```

## Common Issues

1. **Transcripts failing**: youtube-transcript-api blocked on cloud IPs. Use Supadata or Whisper.

2. **Job stuck**: Check Celery worker logs. Job state in Supabase `research_jobs` table.

3. **API cost overrun**: Check mode budget limits in `job_config.py`.

4. **Quality Gate not filtering**: Ensure stage is called in pipeline and mode floors are set.

## References

- @./docs/architecture.md
- @./docs/project-overview.md
- @./.claude/rules/research-agent.md
- @./.claude/rules/api-integrations.md
