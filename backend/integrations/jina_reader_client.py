"""Jina AI Reader - fast content extraction to LLM-ready markdown."""
import os
import re
from typing import Dict, List, Optional
import httpx
from loguru import logger

from backend.utils.error_handling import sanitize_error_message
from backend.utils.rate_limiter import with_rate_limit


# Sites that need special handling (JS rendering, consent walls, etc.)
_REDDIT_PATTERN = re.compile(r"(reddit\.com|redd\.it)", re.IGNORECASE)


def _is_reddit_url(url: str) -> bool:
    """Check if URL is a Reddit URL."""
    return bool(_REDDIT_PATTERN.search(url))


def _convert_to_old_reddit(url: str) -> str:
    """Convert www.reddit.com URLs to old.reddit.com for better extraction.

    old.reddit.com serves static HTML without JS rendering requirements,
    which yields much better content extraction via Jina Reader.
    """
    return re.sub(
        r"https?://(www\.)?reddit\.com",
        "https://old.reddit.com",
        url,
    )


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
        """Initialize Jina client using Settings for API key."""
        from backend.config import get_settings
        settings = get_settings()
        # API key is optional - improves rate limits
        self.api_key = settings.jina_api_key
        self.timeout = 30.0
        self.cost_per_extraction = 0.0  # Free tier

    @with_rate_limit("jina")
    def extract(
        self,
        url: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Extract content from URL as markdown.

        Automatically applies site-specific optimizations for Reddit
        and other anti-bot sites (e.g., old.reddit.com conversion,
        cache-busting, wait-for-selector).

        Args:
            url: Target URL to extract content from
            extra_headers: Optional additional Jina headers (X-No-Cache, etc.)

        Returns:
            Dict with markdown content and metadata
        """
        try:
            # Site-specific URL transformations
            fetch_url = url
            if _is_reddit_url(url):
                fetch_url = _convert_to_old_reddit(url)
                logger.info(f"Jina: Reddit URL → old.reddit.com: {fetch_url[:60]}")

            logger.info(f"Jina extracting: {fetch_url[:60]}...")

            # Construct Jina Reader URL
            jina_url = f"{self.BASE_URL}{fetch_url}"

            headers = {
                "Accept": "text/markdown",
                "X-Return-Format": "markdown",
                "X-No-Cache": "true",  # Always bypass cache for fresh content
            }

            # Site-specific headers
            if _is_reddit_url(url):
                # old.reddit.com renders as static HTML, but add timeout
                # to ensure full page load
                headers["X-Timeout"] = "20"

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Merge any caller-provided headers
            if extra_headers:
                headers.update(extra_headers)

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(jina_url, headers=headers)
                response.raise_for_status()

            markdown_content = response.text

            logger.info(
                f"Jina extracted {len(markdown_content)} chars from "
                f"{fetch_url[:40]}..."
            )

            return {
                "url": url,  # Return original URL, not transformed
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
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Jina extraction failed for {url}: {sanitized}")
            return {"url": url, "content": "", "error": sanitized}

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
                sanitized = sanitize_error_message(e, include_type=False)
                return {"url": url, "content": "", "error": sanitized}

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
