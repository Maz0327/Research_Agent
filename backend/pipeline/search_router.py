"""Search Router: Mode-based API routing for optimal search results.

Research-validated stack (Dec 2025):
- breaking_news: Perplexity for speed (358ms avg)
- investigation/controversy: Exa + Perplexity for depth (94.9% accuracy)
- profile: Exa semantic search for entity focus
- Fallback chain: Exa → Perplexity → Serper → Tavily
"""
from typing import Any, Optional

from loguru import logger

from backend.config import get_settings


# Search API priorities by mode
MODE_SEARCH_CONFIG = {
    "breaking_news": {
        "primary": "perplexity",  # Speed priority
        "secondary": None,
        "fallback": ["serper", "tavily"],
        "reason": "Speed is critical for breaking news (358ms vs 800ms+)",
    },
    "investigation": {
        "primary": "exa",  # Accuracy priority
        "secondary": "perplexity",  # Combine for depth
        "fallback": ["serper", "tavily"],
        "reason": "Investigation requires 94.9% semantic accuracy from Exa",
    },
    "controversy": {
        "primary": "exa",  # Multiple perspectives need semantic understanding
        "secondary": "perplexity",
        "fallback": ["serper", "tavily"],
        "reason": "Controversy requires finding opposing viewpoints semantically",
    },
    "profile": {
        "primary": "exa",  # Entity-focused semantic search
        "secondary": None,
        "fallback": ["perplexity", "serper", "tavily"],
        "reason": "Profile mode benefits from Exa's entity understanding",
    },
}

DEFAULT_CONFIG = {
    "primary": "perplexity",
    "secondary": None,
    "fallback": ["serper", "tavily"],
    "reason": "Default fallback",
}


async def search_with_routing(
    query: str,
    mode: str = "investigation",
    num_results: int = 20,
    include_domains: Optional[list[str]] = None,
    exclude_domains: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Search using mode-appropriate APIs with automatic fallback.

    Args:
        query: Search query
        mode: Pipeline mode (breaking_news, investigation, profile, controversy)
        num_results: Number of results to return
        include_domains: Domains to include (passed to Exa)
        exclude_domains: Domains to exclude (passed to Exa)

    Returns:
        Dict with results, api_used, and cost estimate
    """
    config = MODE_SEARCH_CONFIG.get(mode.lower(), DEFAULT_CONFIG)
    settings = get_settings()

    logger.info(f"Search routing: mode={mode}, primary={config['primary']}, query={query[:50]}...")

    results = []
    apis_used = []
    total_cost = 0.0

    # Try primary API
    primary_result = await _try_search_api(
        config["primary"],
        query,
        num_results,
        include_domains,
        exclude_domains,
    )
    if primary_result:
        results.extend(primary_result["results"])
        apis_used.append(config["primary"])
        total_cost += primary_result.get("cost", 0)

    # Try secondary API if configured
    if config["secondary"] and len(results) < num_results:
        secondary_result = await _try_search_api(
            config["secondary"],
            query,
            num_results - len(results),
            include_domains,
            exclude_domains,
        )
        if secondary_result:
            results.extend(secondary_result["results"])
            apis_used.append(config["secondary"])
            total_cost += secondary_result.get("cost", 0)

    # Try fallback chain if still insufficient results
    if len(results) < num_results // 2:  # Less than half requested
        for fallback_api in config["fallback"]:
            if fallback_api in apis_used:
                continue

            fallback_result = await _try_search_api(
                fallback_api,
                query,
                num_results - len(results),
            )
            if fallback_result:
                results.extend(fallback_result["results"])
                apis_used.append(fallback_api)
                total_cost += fallback_result.get("cost", 0)

            if len(results) >= num_results // 2:
                break

    # Deduplicate results by URL
    seen_urls = set()
    unique_results = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    logger.info(f"Search routing complete: {len(unique_results)} results from {apis_used}")

    return {
        "results": unique_results[:num_results],
        "apis_used": apis_used,
        "cost": total_cost,
        "mode": mode,
    }


async def _try_search_api(
    api_name: str,
    query: str,
    num_results: int,
    include_domains: Optional[list[str]] = None,
    exclude_domains: Optional[list[str]] = None,
) -> Optional[dict]:
    """Try a specific search API, return None on failure."""
    settings = get_settings()

    try:
        if api_name == "exa":
            if not settings.exa_api_key:
                logger.debug("Exa API key not configured, skipping")
                return None

            from backend.integrations.exa_client import ExaSearchClient
            client = ExaSearchClient()
            result = client.search(
                query,
                num_results=num_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            )
            return result

        elif api_name == "perplexity":
            if not settings.perplexity_api_key:
                logger.debug("Perplexity API key not configured, skipping")
                return None

            from backend.integrations.perplexity_client import search_perplexity
            results = search_perplexity(query, max_results=num_results)
            return {
                "results": results,
                "cost": 0.001 * num_results,  # Rough estimate
            }

        elif api_name == "serper":
            if not settings.serper_api_key:
                logger.debug("Serper API key not configured, skipping")
                return None

            from backend.integrations.serper_client import SerperClient
            client = SerperClient()
            result = await client.search(query, num_results=num_results)
            return result

        elif api_name == "tavily":
            if not settings.tavily_api_key:
                logger.debug("Tavily API key not configured, skipping")
                return None

            from backend.integrations.tavily_client import search_tavily
            results = search_tavily(query, max_results=num_results)
            return {
                "results": results,
                "cost": 0.001 * num_results,  # Rough estimate
            }

        else:
            logger.warning(f"Unknown search API: {api_name}")
            return None

    except Exception as e:
        logger.warning(f"Search API {api_name} failed: {e}")
        return None


def get_search_explanation(mode: str) -> str:
    """Get explanation of search routing for a mode."""
    config = MODE_SEARCH_CONFIG.get(mode.lower(), DEFAULT_CONFIG)
    return config.get("reason", "Default search routing")
