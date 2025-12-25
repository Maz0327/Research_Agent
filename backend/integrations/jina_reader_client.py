"""Jina AI Reader - fast content extraction to LLM-ready markdown."""
import os
from typing import Dict, List
import httpx
from loguru import logger


class JinaReaderClient:
    """
    Jina AI Reader for URL content extraction.

    This REPLACES Playwright scraping.
    - 2-3 seconds per page (vs 10-30s for Playwright)
    - Returns clean markdown
    - Handles JavaScript rendering
    - FREE with rate limits
    """

    BASE_URL = "https://r.jina.ai/"

    def __init__(self):
        """Initialize Jina client."""
        # API key is optional - improves rate limits
        self.api_key = os.getenv("JINA_AI_READER_API_KEY") or os.getenv("JINA_API_KEY")
        self.timeout = 30.0
        self.cost_per_extraction = 0.0  # Free tier

    def extract(self, url: str) -> Dict[str, str]:
        """
        Extract content from URL as markdown.

        Args:
            url: Target URL to extract content from

        Returns:
            Dict with markdown content and metadata
        """
        try:
            logger.info(f"Jina extracting: {url[:50]}...")

            # Construct Jina Reader URL
            jina_url = f"{self.BASE_URL}{url}"

            headers = {
                "Accept": "text/markdown",
                "X-Return-Format": "markdown",
            }

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(jina_url, headers=headers)
                response.raise_for_status()

            markdown_content = response.text

            logger.info(f"Jina extracted {len(markdown_content)} chars from {url[:30]}...")

            return {
                "url": url,
                "content": markdown_content,
                "content_type": "markdown",
                "char_count": len(markdown_content),
                "api": "jina",
                "cost": self.cost_per_extraction,
            }

        except httpx.TimeoutException:
            logger.warning(f"Jina timeout for {url}")
            return {"url": url, "content": "", "error": "timeout"}
        except Exception as e:
            logger.error(f"Jina extraction failed for {url}: {e}")
            return {"url": url, "content": "", "error": str(e)}

    def extract_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> List[Dict[str, str]]:
        """
        Extract content from multiple URLs.

        Use this for batch extraction. More efficient than individual calls.
        """
        import asyncio

        async def extract_async(url: str) -> Dict:
            """Async extraction helper."""
            try:
                jina_url = f"{self.BASE_URL}{url}"
                headers = {"Accept": "text/markdown"}

                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(jina_url, headers=headers)
                    response.raise_for_status()

                return {
                    "url": url,
                    "content": response.text,
                    "content_type": "markdown",
                }
            except Exception as e:
                return {"url": url, "content": "", "error": str(e)}

        async def extract_all():
            """Extract all URLs with concurrency limit."""
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_extract(url):
                async with semaphore:
                    return await extract_async(url)

            tasks = [limited_extract(url) for url in urls]
            return await asyncio.gather(*tasks)

        logger.info(f"Jina batch extracting {len(urls)} URLs...")
        results = asyncio.run(extract_all())
        logger.info(f"Jina batch complete: {len([r for r in results if r.get('content')])} successful")

        return results


def extract_with_jina(url: str) -> str:
    """
    Convenience function - extract URL content as markdown.

    Use this in the pipeline. Returns markdown string.
    """
    client = JinaReaderClient()
    result = client.extract(url)
    return result.get("content", "")


def extract_batch_with_jina(urls: List[str]) -> List[Dict]:
    """Convenience function for batch extraction."""
    client = JinaReaderClient()
    return client.extract_batch(urls)
