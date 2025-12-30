"""Source discovery and quality gate stages.

Dec 2025: Enhanced with Exa semantic search for better relevance filtering.
- Uses Exa (94.9% accuracy) for investigation/profile/controversy modes
- Falls back to Perplexity for breaking_news (speed priority)
- Adds semantic relevance scoring to filter irrelevant results
"""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import update_job
from .helpers import post_slack_message


def stage_3_source_shortlist(ctx: PipelineContext) -> None:
    """Generate source shortlist using semantic search (Exa) or Perplexity.

    Search strategy by mode:
    - breaking_news: Perplexity (speed priority, 358ms)
    - investigation/controversy: Exa semantic search (94.9% accuracy)
    - profile: Exa (entity-focused semantic search)
    - default: Perplexity with Exa fallback
    """
    logger.info(f"[{ctx.job_id}] Stage 3: Generating source shortlist")
    update_job(ctx.job_id, stage="source_discovery", progress_percent=25)
    post_slack_message(ctx, "Collecting sources...")

    try:
        if not ctx.angles:
            logger.warning(f"[{ctx.job_id}] No research angles available for source shortlist")
            ctx.add_warning("No research angles available - using topic as fallback")
            ctx.angles = ["general"]

        # Add niche query expansions if configured
        expanded_key_terms = list(ctx.key_terms)
        if ctx.niche_config:
            query_additions = ctx.niche_config.get("query_additions", [])
            if query_additions:
                # Expand queries with topic substitution
                for query in query_additions:
                    expanded = query.replace("{topic}", ctx.topic)
                    expanded_key_terms.append(expanded)
                logger.info(f"[{ctx.job_id}] Added {len(query_additions)} niche queries")

            # Add priority keywords
            priority_keywords = ctx.niche_config.get("priority_keywords", [])
            if priority_keywords:
                expanded_key_terms.extend(priority_keywords)

        # Determine search strategy based on mode
        mode = ctx.job_config.mode.value if ctx.job_config else "full"
        use_exa_primary = mode in ("investigation", "controversy", "profile")

        # Try Exa semantic search first for supported modes
        exa_sources = []
        if use_exa_primary:
            exa_sources = _search_with_exa(ctx, expanded_key_terms)

        # Fall back to Perplexity if Exa didn't return enough or for other modes
        if len(exa_sources) < 10:
            from backend.integrations.perplexity_client import source_shortlist
            result = source_shortlist(ctx.job_config, ctx.angles, expanded_key_terms)
            perplexity_sources = result.get("urls", []) or []
            ctx.set_output("source_shortlist_md", result.get("shortlist_md", ""))
            ctx.add_cost("perplexity_source_shortlist", 0.005)

            # Merge sources (Exa first for semantic relevance, then Perplexity)
            seen_urls = {s.url for s in exa_sources}
            for source in perplexity_sources:
                if source.url not in seen_urls:
                    exa_sources.append(source)
                    seen_urls.add(source.url)

            ctx.web_sources = exa_sources
            logger.info(f"[{ctx.job_id}] Combined sources: {len(exa_sources)} (Exa) + Perplexity fallback")
        else:
            ctx.web_sources = exa_sources
            ctx.set_output("source_shortlist_md", _generate_shortlist_md(exa_sources, "Exa Semantic Search"))
            logger.info(f"[{ctx.job_id}] Using Exa semantic search: {len(exa_sources)} sources")

        # For breaking_news mode, also search GDELT for recent news
        if ctx.job_config.mode.value in ("breaking_news", "BREAKING_NEWS"):
            _fetch_gdelt_sources(ctx)

        # Enforce budget cap
        if ctx.web_sources:
            max_urls = ctx.job_config.budgets.max_web_urls
            if len(ctx.web_sources) > max_urls:
                ctx.web_sources = ctx.web_sources[:max_urls]
                ctx.add_warning(f"Source shortlist capped to {max_urls} URLs")
            logger.info(f"[{ctx.job_id}] Generated source shortlist with {len(ctx.web_sources)} URLs")
        else:
            logger.warning(f"[{ctx.job_id}] No sources found in shortlist")
            ctx.add_warning("No sources found in shortlist")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Source shortlist generation failed: {e}")
        ctx.add_warning(f"Source shortlist generation failed: {str(e)}")
        ctx.set_output("source_shortlist_md", f"# Source Shortlist\n\n*Error: {str(e)}*")


def _fetch_gdelt_sources(ctx: PipelineContext) -> None:
    """Fetch GDELT news sources for breaking_news mode."""
    try:
        from backend.integrations.gdelt_client import search_news_gdelt
        from backend.models.source import SourceItem, SourceType

        logger.info(f"[{ctx.job_id}] Fetching GDELT news for breaking_news mode")

        # Search GDELT with short timespan for recency
        gdelt_articles = search_news_gdelt(
            query=ctx.topic,
            timespan="24h",
            max_records=20
        )

        # Convert GDELT results to SourceItems
        gdelt_sources = []
        for article in gdelt_articles:
            if article.get("url"):
                source = SourceItem(
                    url=article["url"],
                    title=article.get("title", ""),
                    source_type=SourceType.NEWS,
                    text="",  # Will be filled in web capture
                    published_at=article.get("published_date"),
                    notes=f"GDELT: {article.get('source', 'unknown')}"
                )
                gdelt_sources.append(source)

        if gdelt_sources:
            ctx.web_sources.extend(gdelt_sources)
            logger.info(f"[{ctx.job_id}] Added {len(gdelt_sources)} GDELT news sources")

            # Append to shortlist markdown
            gdelt_md = "\n\n## GDELT News Sources\n\n"
            for src in gdelt_sources[:10]:
                gdelt_md += f"- [{src.title or 'Untitled'}]({src.url})\n"
            current_md = ctx.outputs.get("source_shortlist_md", "")
            ctx.set_output("source_shortlist_md", current_md + gdelt_md)

    except Exception as gdelt_error:
        logger.warning(f"[{ctx.job_id}] GDELT search failed: {gdelt_error}")
        ctx.add_warning(f"GDELT news search failed: {str(gdelt_error)}")


def _search_with_exa(ctx: PipelineContext, key_terms: list[str]) -> list:
    """Search using Exa semantic search for high-accuracy results.

    Returns SourceItem list with semantic relevance scores.
    Falls back gracefully if Exa is not configured.
    """
    from backend.models.source import SourceItem, SourceType
    from backend.config import get_settings

    settings = get_settings()
    if not settings.exa_api_key:
        logger.debug(f"[{ctx.job_id}] Exa API key not configured, skipping semantic search")
        return []

    try:
        from backend.integrations.exa_client import ExaSearchClient

        client = ExaSearchClient()
        sources = []

        # Build semantic search query from topic and key terms
        search_query = f"{ctx.topic}"
        if key_terms:
            search_query += f" {' '.join(key_terms[:5])}"

        logger.info(f"[{ctx.job_id}] Exa semantic search: {search_query[:80]}...")

        # Get results with semantic scoring
        result = client.search(
            query=search_query,
            num_results=30,
            use_autoprompt=True,  # Let Exa optimize the query
        )

        # Convert to SourceItems with relevance scores
        for item in result.get("results", []):
            source = SourceItem(
                url=item.get("url", ""),
                title=item.get("title", ""),
                source_type=SourceType.WEB,
                text="",  # Will be filled in web capture
                notes=f"Exa score: {item.get('score', 0):.3f}",
            )
            sources.append(source)

        # Track Exa cost (~$0.001 per search)
        ctx.add_cost("exa_semantic_search", result.get("cost", 0.001))
        logger.info(f"[{ctx.job_id}] Exa returned {len(sources)} semantically relevant sources")

        return sources

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Exa search failed: {e}")
        ctx.add_warning(f"Exa semantic search failed: {str(e)}")
        return []


def _generate_shortlist_md(sources: list, source_name: str = "Search") -> str:
    """Generate markdown for source shortlist."""
    md = f"# Source Shortlist\n\n**Source:** {source_name}\n\n"
    for i, source in enumerate(sources[:30], 1):
        title = getattr(source, 'title', '') or source.url[:50]
        url = getattr(source, 'url', str(source))
        notes = getattr(source, 'notes', '')
        md += f"{i}. [{title}]({url})"
        if notes:
            md += f" - {notes}"
        md += "\n"
    return md


def stage_3_5_quality_gate(ctx: PipelineContext) -> None:
    """Apply Quality Gate to filter and score discovered sources."""
    from backend.pipeline.quality_gate import run_quality_gate

    logger.info(f"[{ctx.job_id}] Stage 3.5: Applying Quality Gate")
    update_job(ctx.job_id, stage="quality_gate", progress_percent=30)

    if not ctx.web_sources:
        logger.info(f"[{ctx.job_id}] No sources to filter")
        return

    try:
        # Convert sources to dicts for quality gate
        source_dicts = []
        for source in ctx.web_sources:
            if isinstance(source, dict):
                source_dicts.append(source)
            elif hasattr(source, 'url'):
                source_dicts.append({
                    'url': source.url,
                    'title': getattr(source, 'title', ''),
                    'snippet': getattr(source, 'text', ''),
                    'source_type': getattr(source, 'source_type', 'web'),
                })
            else:
                source_dicts.append({'url': str(source)})

        # Get mode from job config
        mode = ctx.job_config.mode.value if ctx.job_config else "full"
        niche = ctx.job_config.niche if ctx.job_config else None

        # Run Quality Gate with key terms for BM25 scoring
        result = run_quality_gate(
            sources=source_dicts,
            mode=mode,
            niche=niche,
            query_terms=ctx.key_terms if ctx.key_terms else None,
        )

        # Store stats
        ctx.quality_gate_stats = result.get("stats", {})

        # Convert approved sources back to SourceItems
        from backend.models.source import SourceItem, SourceType

        approved_sources = []
        for src in result.get("approved", []):
            source_type_str = src.get("source_type", "web")
            try:
                source_type = SourceType(source_type_str)
            except ValueError:
                source_type = SourceType.WEB

            approved_sources.append(SourceItem(
                url=src["url"],
                title=src.get("title", ""),
                source_type=source_type,
                text=src.get("snippet", ""),
                notes=f"QG score: {src.get('final_score', 0):.2f}"
            ))

        # Replace web_sources with filtered list
        original_count = len(ctx.web_sources)
        ctx.web_sources = approved_sources

        # Add soft-rejected as reference links in outputs
        soft_rejected = result.get("soft_rejected", [])
        if soft_rejected:
            ref_links = "\n\n## Reference Links (Not Extracted)\n\n"
            for src in soft_rejected[:10]:
                ref_links += f"- [{src.get('title', src['url'][:50])}]({src['url']})\n"
            current_shortlist = ctx.outputs.get("source_shortlist_md", "")
            ctx.set_output("source_shortlist_md", current_shortlist + ref_links)

        stats = ctx.quality_gate_stats
        logger.info(
            f"[{ctx.job_id}] Quality Gate: {original_count} -> {len(approved_sources)} sources "
            f"(approved: {stats.get('approved_count', 0)}, "
            f"soft-rejected: {stats.get('soft_rejected_count', 0)}, "
            f"hard-rejected: {stats.get('rejected_count', 0)})"
        )

        # Track cost (Quality Gate is deterministic, no API cost)
        ctx.add_cost("quality_gate", 0.0)

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Quality Gate failed, continuing without filtering: {e}")
        ctx.add_warning(f"Quality Gate failed: {str(e)}")
