"""
Grounded Search Pipeline - Three-layer filtered web search for iteration.

Unlike the baseline pipeline's search (which often drifts off-topic), this
search is GROUNDED in the existing Doc 0 content. By the time we're iterating,
we know exactly what the topic is because we have real, validated sources.

Three layers prevent topic drift:
1. Grounded Query Generation — LLM generates specific queries from Doc 0 context
2. Multi-Provider Search — Tavily/Serper/Brave with deduplication
3. Relevance Gate — Cheap LLM check filters irrelevant results

Example of drift prevention:
- Topic: "Barney the Dinosaur show fan theories"
- Doc 0 has sources from PBS fan theory sites
- Layer 1: Generates "Barney and Friends PBS children's show conspiracy theories"
  (not just "Barney theories" which would match How I Met Your Mother)
- Layer 3: Rejects "Barney Stinson fan theories" because Doc 0 context is about PBS show
"""

from typing import Any, Optional

from loguru import logger

from backend.pipeline.runs.modes.base import RunModeExecutor


def grounded_search(
    doc_0: dict[str, Any],
    user_prompt: str,
    existing_urls: set[str],
    max_results: int = 8,
    executor: Optional[RunModeExecutor] = None,
) -> list[dict[str, Any]]:
    """
    Three-layer filtered search grounded in existing Doc 0.

    Args:
        doc_0: Parent Doc 0 with sources and extractions
        user_prompt: User's search guidance (e.g., "find counterarguments")
        existing_urls: URLs to exclude (already in research)
        max_results: Maximum candidates to return
        executor: Optional metrics collector

    Returns:
        List of SearchCandidate dicts with url, title, snippet, relevance_score
    """
    # Extract topic context from Doc 0
    topic_context = _build_topic_context(doc_0)

    if not topic_context:
        logger.warning("Cannot perform grounded search: no topic context in Doc 0")
        return []

    # Layer 1: Generate grounded search queries
    if executor:
        executor.update_progress(12, "Generating search queries from existing research")

    queries = _generate_grounded_queries(
        topic_context=topic_context,
        user_prompt=user_prompt,
        executor=executor,
    )

    if not queries:
        logger.warning("No search queries generated")
        return []

    logger.info(f"Generated {len(queries)} grounded search queries")

    # Layer 2: Search across providers
    if executor:
        executor.update_progress(18, "Searching for relevant sources")

    raw_candidates = _multi_provider_search(
        queries=queries,
        existing_urls=existing_urls,
        max_per_query=max_results,
    )

    if not raw_candidates:
        logger.warning("No search results from any provider")
        return []

    logger.info(f"Found {len(raw_candidates)} raw candidates from search")

    # Layer 3: Relevance gate
    if executor:
        executor.update_progress(24, "Filtering for relevance")

    filtered = _relevance_gate(
        candidates=raw_candidates,
        topic_context=topic_context,
        user_prompt=user_prompt,
        executor=executor,
    )

    logger.info(f"Relevance gate: {len(filtered)}/{len(raw_candidates)} candidates passed")

    return filtered[:max_results]


def _build_topic_context(doc_0: dict[str, Any]) -> str:
    """
    Build a topic context string from Doc 0 for grounding.

    Uses source titles, the research topic, and key extractions
    to create a clear description of what this research is actually about.
    """
    parts = []

    # Research topic
    topic = doc_0.get("research_topic", "")
    if topic:
        parts.append(f"Research topic: {topic}")

    # Source titles (first 5)
    sources = doc_0.get("sources", [])
    titles = []
    for s in sources[:5]:
        title = s.get("title", "")
        if title and title != f"Source {s.get('source_id', '')}":
            titles.append(title)
    if titles:
        parts.append(f"Existing source titles: {'; '.join(titles)}")

    # Key points from extractions (first 5 most important)
    extractions = doc_0.get("semantic_extractions", [])
    key_statements = []
    for ext in extractions[:3]:
        for kp in ext.get("key_points", [])[:2]:
            statement = kp.get("statement", "")
            if statement:
                key_statements.append(statement)
    if key_statements:
        parts.append(f"Key findings so far: {'; '.join(key_statements[:5])}")

    return "\n".join(parts)


def _generate_grounded_queries(
    topic_context: str,
    user_prompt: str,
    executor: Optional[RunModeExecutor] = None,
) -> list[str]:
    """
    Layer 1: Generate specific search queries grounded in Doc 0 content.

    The LLM sees the actual research context and generates queries that
    are specific enough to avoid topic drift.
    """
    try:
        from backend.integrations.gemini_client import GeminiClient
        gemini = GeminiClient()
    except Exception as e:
        logger.warning(f"Gemini not available for query generation: {e}")
        # Fallback: use user_prompt directly
        return [user_prompt] if user_prompt else []

    prompt = f"""Generate 3-5 specific web search queries to find new sources for this research.

## EXISTING RESEARCH CONTEXT
{topic_context}

## WHAT THE USER WANTS TO FIND
{user_prompt or "Additional relevant sources"}

## RULES
- Each query must be HIGHLY SPECIFIC to this exact topic
- Include distinguishing keywords that prevent confusion with similar-sounding topics
- Use quotes around proper nouns or specific phrases when helpful
- Each query should approach from a slightly different angle
- Do NOT generate generic queries — they cause topic drift

Return JSON:
{{
  "queries": ["specific query 1", "specific query 2", "specific query 3"]
}}
"""

    try:
        response = gemini.generate_json(
            prompt=prompt,
            system_message="Generate precise, specific search queries for research expansion. Avoid generic queries.",
        )
        if executor:
            executor.metrics.record_llm_call(tokens_in=500, tokens_out=150, cost=0.005)

        data = response.get("data", {})
        queries = data.get("queries", [])

        # Validate: each query must be a non-empty string
        return [q for q in queries if isinstance(q, str) and len(q.strip()) > 5][:5]

    except Exception as e:
        logger.warning(f"Query generation failed: {e}")
        return [user_prompt] if user_prompt else []


def _multi_provider_search(
    queries: list[str],
    existing_urls: set[str],
    max_per_query: int = 8,
) -> list[dict[str, Any]]:
    """
    Layer 2: Search across multiple providers with deduplication.

    Tries Tavily first (best quality), then Serper, then Brave.
    Deduplicates results across queries and against existing URLs.
    """
    seen_urls: set[str] = set(existing_urls)
    candidates: list[dict[str, Any]] = []

    for query in queries:
        results = _search_single_provider(query, max_per_query)

        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                candidates.append(result)

    return candidates


def _search_single_provider(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search a single query across available providers."""
    # Try Tavily first
    try:
        from backend.integrations.tavily_client import TavilyClient

        tavily = TavilyClient()
        results = tavily.search(query=query, max_results=max_results)

        return [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("content", r.get("snippet", ""))[:200],
                "provider": "tavily",
            }
            for r in results.get("results", [])
            if r.get("url")
        ]
    except Exception as e:
        logger.debug(f"Tavily search failed, trying alternatives: {e}")

    # Try Serper
    try:
        from backend.integrations.serper_client import SerperClient

        serper = SerperClient()
        results = serper.search(query=query, num_results=max_results)

        return [
            {
                "url": r.get("link", ""),
                "title": r.get("title", ""),
                "snippet": r.get("snippet", "")[:200],
                "provider": "serper",
            }
            for r in results.get("organic", [])
            if r.get("link")
        ]
    except Exception as e:
        logger.debug(f"Serper search failed, trying Brave: {e}")

    # Try Brave
    try:
        from backend.integrations.brave_client import BraveSearchClient

        brave = BraveSearchClient()
        results = brave.search(query=query, count=max_results)

        return [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("description", "")[:200],
                "provider": "brave",
            }
            for r in results.get("web", {}).get("results", [])
            if r.get("url")
        ]
    except Exception as e:
        logger.warning(f"All search providers failed for query: {query[:50]}: {e}")
        return []


def _relevance_gate(
    candidates: list[dict[str, Any]],
    topic_context: str,
    user_prompt: str,
    executor: Optional[RunModeExecutor] = None,
) -> list[dict[str, Any]]:
    """
    Layer 3: Cheap LLM check to filter irrelevant results.

    Single batch call that checks each candidate against the Doc 0 context.
    This catches drift that keyword search misses (e.g., "Barney" disambiguation).
    """
    if not candidates:
        return []

    try:
        from backend.integrations.gemini_client import GeminiClient
        gemini = GeminiClient()
    except Exception as e:
        logger.warning(f"Gemini not available for relevance gate: {e}")
        # Without the gate, return all candidates (risky but functional)
        for c in candidates:
            c["relevance_score"] = 0.5
        return candidates

    # Build candidate list for batch check
    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(
            f"[{i}] Title: {c.get('title', 'N/A')}\n"
            f"    URL: {c.get('url', '')}\n"
            f"    Snippet: {c.get('snippet', 'N/A')[:150]}"
        )

    prompt = f"""Rate the relevance of each search result to this specific research topic.

## RESEARCH CONTEXT (what we're studying)
{topic_context}

## SEARCH INTENT
{user_prompt or "Finding additional relevant sources"}

## SEARCH RESULTS TO EVALUATE

{chr(10).join(candidate_lines)}

## TASK

For each result, determine if it is about the SAME SPECIFIC TOPIC as the research context.

Be STRICT: similar keywords ≠ same topic. For example:
- "Barney the dinosaur theories" ≠ "Barney Stinson theories"
- "Apple fruit nutrition" ≠ "Apple Inc stock analysis"
- "Python snake habitats" ≠ "Python programming tutorials"

Return JSON:
{{
  "ratings": [
    {{"index": 0, "relevant": true, "confidence": 0.9, "reason": "directly about same topic"}},
    {{"index": 1, "relevant": false, "confidence": 0.8, "reason": "different topic despite similar keywords"}}
  ]
}}
"""

    try:
        response = gemini.generate_json(
            prompt=prompt,
            system_message="Filter search results for topic relevance. Be strict — reject anything not about the exact same topic.",
        )
        if executor:
            executor.metrics.record_llm_call(tokens_in=1000, tokens_out=400, cost=0.01)

        data = response.get("data", {})
        ratings = data.get("ratings", [])

        # Build index → rating map
        rating_map: dict[int, dict] = {}
        for r in ratings:
            idx = r.get("index")
            if idx is not None:
                rating_map[int(idx)] = r

        # Filter candidates
        filtered = []
        for i, candidate in enumerate(candidates):
            rating = rating_map.get(i, {})
            is_relevant = rating.get("relevant", False)
            confidence = rating.get("confidence", 0.0)

            if is_relevant and confidence >= 0.7:
                candidate["relevance_score"] = confidence
                candidate["relevance_reason"] = rating.get("reason", "")
                filtered.append(candidate)

        return filtered

    except Exception as e:
        logger.warning(f"Relevance gate failed: {e}")
        # Fallback: return all with low confidence
        for c in candidates:
            c["relevance_score"] = 0.3
        return candidates
