"""External API integrations.

Updated 2026-01-19: Legacy search clients removed (topic-based discovery deprecated).
User-supplied sources only pipeline.

Active integrations:
- GeminiClient: LLM extraction, synthesis, validation, booster, producer
- SupadataClient: YouTube transcripts (primary)
- JinaReaderClient: Web content extraction
- WhisperClient: Transcript fallback
"""

# LLM clients
from backend.integrations.gemini_client import GeminiClient

# Content clients
from backend.integrations.jina_reader_client import JinaReaderClient
from backend.integrations.supadata_client import SupadataClient

__all__ = [
    "GeminiClient",
    "JinaReaderClient",
    "SupadataClient",
]

