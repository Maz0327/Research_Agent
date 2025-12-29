"""Source discovery and quality gate stages."""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import update_job
from .helpers import post_slack_message


def stage_3_source_shortlist(ctx: PipelineContext) -> None:
    """Generate source shortlist using Perplexity and GDELT (for breaking_news)."""
    from backend.integrations.perplexity_client import source_shortlist

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

        result = source_shortlist(ctx.job_config, ctx.angles, expanded_key_terms)
        ctx.web_sources = result.get("urls", []) or []
        ctx.set_output("source_shortlist_md", result.get("shortlist_md", ""))
        # Track Perplexity cost (~$0.005 per search)
        ctx.add_cost("perplexity_source_shortlist", 0.005)

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
