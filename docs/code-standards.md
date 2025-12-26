# Code Standards

## Python (Backend)

### Style
- PEP 8 compliance
- Type hints required for function signatures
- Docstrings for public functions
- Max line length: 100 characters

### Imports
```python
# Standard library
import os
from datetime import datetime

# Third party
from fastapi import FastAPI
from loguru import logger

# Local
from backend.config import settings
from backend.models import JobRecord
```

### Logging
```python
from loguru import logger

logger.info("Processing job", job_id=job_id)
logger.error("API failed", error=str(e))
```

### Error Handling
```python
try:
    result = external_call()
except SpecificError as e:
    logger.error(f"Failed: {e}")
    raise
```

## TypeScript (Frontend)

### Style
- ESLint + Prettier
- Strict TypeScript
- Functional components only

### Component Structure
```typescript
// Types first
interface Props {
  title: string;
  onSubmit: () => void;
}

// Component
export function MyComponent({ title, onSubmit }: Props) {
  // Hooks
  const [state, setState] = useState();

  // Handlers
  const handleClick = () => {};

  // Render
  return <div>{title}</div>;
}
```

## File Naming

- Python: `snake_case.py`
- TypeScript: `kebab-case.tsx`
- Components: `PascalCase.tsx`

## Commit Messages

Format: `type(scope): description`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples:
- `feat(pipeline): add quality gate stage`
- `fix(transcripts): handle Supadata timeout`
- `docs: update architecture diagram`

## Integration Patterns

### API Client Structure
```python
from loguru import logger
from backend.config import settings

class ExampleClient:
    """Client for Example API."""

    def __init__(self):
        self.api_key = settings.require_example()

    async def search(self, query: str) -> list[dict]:
        logger.info(f"Example search: {query[:50]}...")
        try:
            # Implementation
            pass
        except Exception as e:
            logger.error(f"Example API error: {e}")
            raise
```

### Fallback Chains
```python
async def search_with_fallback(query: str) -> list[dict]:
    """Search with cascading fallback."""
    # Tier 1: Primary
    try:
        return await primary_search(query)
    except Exception as e:
        logger.warning(f"Primary failed: {e}")

    # Tier 2: Backup
    try:
        return await backup_search(query)
    except Exception as e:
        logger.error(f"All APIs failed: {e}")
        return []
```

### LLM vs Traditional ML Decision

Use **LLM** when:
- Complex reasoning required
- Semantic understanding needed
- Creative synthesis

Use **Traditional ML** when:
- Deterministic processing (Quality Gate)
- Entity extraction (spaCy NER)
- Similarity/deduplication (MinHash LSH)
- Text ranking (BM25)
