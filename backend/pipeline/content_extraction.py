"""Unified content extraction with Jina Reader."""
from typing import List, Dict, Any
from loguru import logger

from backend.integrations.jina_reader_client import (
    JinaReaderClient
)

# Keep Trafilatura as fallback
try:
    from trafilatura import fetch_url, extract as trafilatura_extract
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("Trafilatura not available for fallback")


class UnifiedExtractor:
    """
    Unified content extraction with Jina + Trafilatura fallback.

    Use Jina Reader FIRST. It's faster and returns clean markdown.
    Only fall back to Trafilatura if Jina fails.

    DO NOT use Playwright unless both fail.
    """

    def __init__(self):
        """Initialize extractor."""
        self.jina = JinaReaderClient()

    def extract(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL.

        Args:
            url: Target URL

        Returns:
            Dict with content and metadata
        """
        # Tier 1: Try Jina Reader
        try:
            result = self.jina.extract(url)
            if result.get("content") and len(result["content"]) > 100:
                return result
        except Exception as e:
            logger.warning(f"Jina extraction failed for {url}: {e}")

        # Tier 2: Try Trafilatura (local, no API)
        if TRAFILATURA_AVAILABLE:
            try:
                logger.info(f"Falling back to Trafilatura for {url}")
                downloaded = fetch_url(url)
                if downloaded:
                    text = trafilatura_extract(downloaded)
                    if text:
                        return {
                            "url": url,
                            "content": text,
                            "content_type": "text",
                            "api": "trafilatura",
                            "cost": 0,
                        }
            except Exception as e:
                logger.warning(f"Trafilatura failed for {url}: {e}")

        # Return empty if all fail
        logger.error(f"All extraction methods failed for {url}")
        return {
            "url": url,
            "content": "",
            "error": "All extraction methods failed",
        }

    def extract_batch(self, urls: List[str]) -> List[Dict]:
        """
        Extract content from multiple URLs.

        Uses Jina batch extraction for efficiency.
        """
        results = []

        # Try batch with Jina first
        try:
            jina_results = self.jina.extract_batch(urls)
            for result in jina_results:
                if result.get("content") and len(result.get("content", "")) > 100:
                    results.append(result)
                else:
                    # Try Trafilatura for failed ones
                    fallback = self.extract(result["url"])
                    results.append(fallback)
            return results
        except Exception as e:
            logger.warning(f"Batch extraction failed: {e}")

        # Fallback: Extract one by one
        for url in urls:
            results.append(self.extract(url))

        return results


def extract_content(url: str) -> str:
    """
    Extract content from URL.

    Use this in the pipeline. Returns markdown/text string.
    """
    extractor = UnifiedExtractor()
    result = extractor.extract(url)
    return result.get("content", "")


def extract_content_batch(urls: List[str]) -> List[Dict]:
    """Extract content from multiple URLs."""
    extractor = UnifiedExtractor()
    return extractor.extract_batch(urls)
