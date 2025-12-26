"""External API integrations.

Research-validated stack (Dec 2025):

Search APIs (priority order):
1. Exa (semantic) - 94.9% accuracy, primary for investigation/profile/controversy
2. Perplexity (speed) - 358ms, primary for breaking_news
3. Serper (backup) - $1/1k, reliable fallback
4. Tavily (fallback) - DEMOTED due to 10% 502 error rate

LLM APIs:
1. Gemini 2.5 Flash - Planning, query gen ($0.30/$2.50 per M)
2. GPT-4o-mini - Extraction ($0.15/$0.60 per M)
3. Gemini 2.5 Pro - Vision/PDF, validation ($1.25/$10 per M)
4. Claude Sonnet - Complex synthesis ($3/$15 per M)

Content APIs:
1. Supadata - YouTube transcripts ($17/mo)
2. Jina Reader - Web extraction (FREE)
3. PRAW - Reddit API (FREE)
"""

# Search clients
from backend.integrations.exa_client import ExaSearchClient
from backend.integrations.serper_client import SerperClient
from backend.integrations.tavily_client import TavilyClient

# LLM clients
from backend.integrations.gemini_client import GeminiClient

# Content clients
from backend.integrations.jina_reader_client import JinaReaderClient
from backend.integrations.supadata_client import SupadataClient

__all__ = [
    "ExaSearchClient",
    "SerperClient",
    "TavilyClient",
    "GeminiClient",
    "JinaReaderClient",
    "SupadataClient",
]

