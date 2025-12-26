---
paths: backend/integrations/**/*.py
---

# API Integration Rules

## Client Structure

Every integration client must follow this pattern:

```python
from loguru import logger
from backend.config import settings

class ExampleClient:
    """Client for Example API."""

    def __init__(self):
        self.api_key = settings.require_example()
        self.base_url = "https://api.example.com"

    async def fetch(self, query: str) -> dict:
        """Fetch data from Example API."""
        logger.info(f"Fetching from Example: {query[:50]}...")
        try:
            # Implementation
            pass
        except Exception as e:
            logger.error(f"Example API error: {e}")
            raise
```

## Required Elements

1. **Configuration**: Add to `backend/config.py`
   ```python
   EXAMPLE_API_KEY: Optional[str] = None

   def require_example(self) -> str:
       if not self.EXAMPLE_API_KEY:
           raise ValueError("EXAMPLE_API_KEY not configured")
       return self.EXAMPLE_API_KEY
   ```

2. **Logging**: Use loguru for all API calls

3. **Error Handling**: Catch and log specific exceptions

4. **Rate Limiting**: Respect API rate limits

5. **Cost Tracking**: Log estimated cost per call

## Fallback Chains

| Function | Tier 1 | Tier 2 | Tier 3 |
|----------|--------|--------|--------|
| Web Capture | Jina Reader | Trafilatura | Playwright |
| Transcripts | Supadata | Whisper | youtube-api |
| Reddit | PRAW | Tavily site:reddit | - |
| Search | Perplexity | Tavily | Exa |

## Cost Awareness

Track API costs using:
- `ctx.add_cost("api_name", amount)` in pipeline context
- Log estimated cost in each client method
- Aggregate costs in job completion
