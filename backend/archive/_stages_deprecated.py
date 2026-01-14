"""
Extracted pipeline stages for run_research_job.

Each stage function takes a PipelineContext and modifies it in place.
This reduces the main orchestrator function from complexity 90 to ~5.
"""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import get_job, update_job


# =============================================================================
# Helper: Slack messaging
# =============================================================================

def post_slack_message(ctx: PipelineContext, message: str) -> None:
    """Post Slack message if payload is provided."""
    if ctx.slack_payload and ctx.slack_payload.get("response_url"):
        try:
            from backend.integrations.slack import post_slack_message as _post
            _post(ctx.slack_payload["response_url"], message)
        except Exception as e:
            logger.warning(f"[Slack] Failed to post message: {e}")


# =============================================================================
# Stage 0: Initialization
# =============================================================================

def stage_0_initialize(ctx: PipelineContext) -> None:
    """Initialize job and send start notification."""
    update_job(
        ctx.job_id,
        status="running",
        stage="initializing",
        progress_percent=0,
    )
    post_slack_message(ctx, f"✅ Started research job: `{ctx.job_id}`\nTopic: {ctx.topic}")


# =============================================================================
# Stage 1: Planning (OpenAI)
# =============================================================================

def stage_1_planning(ctx: PipelineContext) -> None:
    """Plan job using OpenAI to generate JobConfig."""
    from backend.integrations.openai_client import plan_job, generate_short_title
    from backend.models.job_config import JobConfig

    logger.info(f"[{ctx.job_id}] Stage 1: Planning job")
    update_job(ctx.job_id, stage="planning", progress_percent=5)

    try:
        if not ctx.topic or not ctx.topic.strip():
            raise ValueError("Topic cannot be empty")

        ctx.job_config = plan_job(ctx.topic)
        # Track OpenAI cost (estimate ~1K tokens for planning)
        ctx.add_cost("openai_planning", 0.002)

        if not isinstance(ctx.job_config, JobConfig):
            raise ValueError(f"plan_job returned invalid type: {type(ctx.job_config)}")

        config_dict = ctx.job_config.model_dump()
        if not config_dict or "topic" not in config_dict:
            raise ValueError("Invalid job_config structure: missing required fields")

        # Load niche overlay if specified
        if ctx.job_config.niche:
            try:
                from backend.pipeline.niche_loader import merge_mode_and_niche, is_valid_niche
                if is_valid_niche(ctx.job_config.niche):
                    ctx.niche_config = merge_mode_and_niche(
                        mode=ctx.job_config.mode.value,
                        niche=ctx.job_config.niche
                    )
                    logger.info(f"[{ctx.job_id}] Loaded niche overlay: {ctx.job_config.niche}")
                else:
                    ctx.add_warning(f"Unknown niche '{ctx.job_config.niche}', ignoring")
            except Exception as niche_error:
                logger.warning(f"[{ctx.job_id}] Failed to load niche: {niche_error}")
                ctx.add_warning(f"Niche loading failed: {str(niche_error)}")

        # Generate short title
        try:
            ctx.short_title = generate_short_title(ctx.topic)
            logger.info(f"[{ctx.job_id}] Generated title: '{ctx.short_title}'")
        except Exception as title_error:
            logger.warning(f"[{ctx.job_id}] Failed to generate title: {title_error}")
            ctx.short_title = " ".join(ctx.topic.split()[:6]).title()
            ctx.add_warning(f"Title generation failed, using fallback: {ctx.short_title}")

        # Save config and title
        job = get_job(ctx.job_id)
        if job:
            update_job(
                ctx.job_id,
                title=ctx.short_title,
                partial_outputs={"config_json": config_dict},
            )
        logger.info(f"[{ctx.job_id}] Planned job: {ctx.job_config.topic}, mode={ctx.job_config.mode}")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Planning failed: {e}")
        ctx.add_warning(f"Planning failed: {str(e)}, using default config")
        from backend.integrations.openai_client import _safe_default_config
        ctx.job_config = _safe_default_config(ctx.topic)


# =============================================================================
# Stage 2: Research Mapping (Perplexity)
# =============================================================================

def stage_2_research_mapping(ctx: PipelineContext) -> None:
    """Generate research map using Perplexity."""
    from backend.integrations.perplexity_client import research_map

    logger.info(f"[{ctx.job_id}] Stage 2: Generating research map")
    update_job(ctx.job_id, stage="research_mapping", progress_percent=15)

    try:
        result = research_map(ctx.job_config)
        ctx.set_output("research_map_md", result.get("research_map_md", ""))
        ctx.angles = result.get("angles", [])
        ctx.key_terms = result.get("key_terms", [])
        # Track Perplexity cost (~$0.005 per search)
        ctx.add_cost("perplexity_research_map", 0.005)
        logger.info(f"[{ctx.job_id}] Generated research map with {len(ctx.angles)} angles")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Research map generation failed: {e}")
        ctx.add_warning(f"Research map generation failed: {str(e)}")
        ctx.set_output("research_map_md", f"# Research Map\n\n*Error: {str(e)}*")


# =============================================================================
# Stage 3: Source Shortlist (Perplexity)
# =============================================================================

def stage_3_source_shortlist(ctx: PipelineContext) -> None:
    """Generate source shortlist using Perplexity and GDELT (for breaking_news)."""
    from backend.integrations.perplexity_client import source_shortlist

    logger.info(f"[{ctx.job_id}] Stage 3: Generating source shortlist")
    update_job(ctx.job_id, stage="source_discovery", progress_percent=25)
    post_slack_message(ctx, "📚 Collecting sources...")

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


# =============================================================================
# Stage 3.5: Quality Gate (Source Filtering)
# =============================================================================

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
            f"[{ctx.job_id}] Quality Gate: {original_count} → {len(approved_sources)} sources "
            f"(approved: {stats.get('approved_count', 0)}, "
            f"soft-rejected: {stats.get('soft_rejected_count', 0)}, "
            f"hard-rejected: {stats.get('rejected_count', 0)})"
        )

        # Track cost (Quality Gate is deterministic, no API cost)
        ctx.add_cost("quality_gate", 0.0)

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Quality Gate failed, continuing without filtering: {e}")
        ctx.add_warning(f"Quality Gate failed: {str(e)}")


# =============================================================================
# Stage 4: YouTube Enumeration
# =============================================================================

def stage_4_youtube_enumeration(ctx: PipelineContext) -> None:
    """Enumerate YouTube channel uploads."""
    from backend.integrations.youtube_client import enumerate_channel_uploads

    logger.info(f"[{ctx.job_id}] Stage 4: Enumerating YouTube uploads")
    update_job(ctx.job_id, stage="youtube_enumeration", progress_percent=35)

    try:
        if ctx.job_config.youtube.channels:
            result = enumerate_channel_uploads(ctx.job_config)
            ctx.youtube_videos = result.get("videos", [])
            ctx.set_output("youtube_index_md", result.get("youtube_index_md", ""))
            logger.info(f"[{ctx.job_id}] Enumerated {len(ctx.youtube_videos)} YouTube videos")
        else:
            ctx.set_output("youtube_index_md", "# YouTube Index\n\n*No channels specified*")
            logger.info(f"[{ctx.job_id}] No YouTube channels specified")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] YouTube enumeration failed: {e}")
        ctx.add_warning(f"YouTube enumeration failed: {str(e)}")
        ctx.set_output("youtube_index_md", f"# YouTube Index\n\n*Error: {str(e)}*")


# =============================================================================
# Stage 5: Transcript Fetching (Cloud-Compatible)
# =============================================================================

def stage_5_transcripts(ctx: PipelineContext) -> None:
    """Fetch transcripts for YouTube videos.

    CLOUD-COMPATIBLE (Dec 2025):
    - Uses Supadata as primary (works on cloud IPs)
    - Whisper as fallback
    - youtube-transcript-api REMOVED (fails on Railway, AWS, GCP)
    """
    from backend.integrations.transcripts import fetch_transcript_v2, TranscriptStatus

    logger.info(f"[{ctx.job_id}] Stage 5: Fetching transcripts (via Supadata)")
    update_job(ctx.job_id, stage="transcript_fetching", progress_percent=45)

    total_minutes = 0
    max_minutes = ctx.job_config.budgets.max_transcription_minutes

    try:
        if ctx.job_config.youtube.fetch_transcripts and ctx.youtube_videos:
            for video in ctx.youtube_videos[:ctx.job_config.youtube.max_videos]:
                video_minutes = (video.duration_seconds or 0) / 60
                if total_minutes + video_minutes > max_minutes:
                    logger.info(f"[{ctx.job_id}] Transcription budget reached")
                    ctx.add_warning(f"Transcription budget ({max_minutes} min) reached")
                    break

                try:
                    # Use cloud-compatible fetch_transcript_v2 (Supadata → Whisper)
                    transcript = fetch_transcript_v2(video.url)
                    if transcript.status == TranscriptStatus.AVAILABLE:
                        ctx.transcripts.append(transcript)
                        total_minutes += video_minutes
                        logger.debug(f"[{ctx.job_id}] Transcript via {transcript.source}: {video.title}")
                    else:
                        ctx.add_warning(f"Transcript missing for video: {video.title}")
                except Exception as e:
                    logger.warning(f"[{ctx.job_id}] Failed to fetch transcript for {video.video_id}: {e}")
                    ctx.add_warning(f"Transcript fetch failed for {video.title}: {str(e)}")

            logger.info(f"[{ctx.job_id}] Fetched {len(ctx.transcripts)} transcripts")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Transcript fetching failed: {e}")
        ctx.add_warning(f"Transcript fetching failed: {str(e)}")


# =============================================================================
# Stage 6: Web Capture (v2 with Jina fallback)
# =============================================================================

def stage_6_web_capture(ctx: PipelineContext) -> None:
    """Capture web content using Jina → Trafilatura → Playwright fallback chain."""
    from backend.pipeline.content_extraction import extract_content_batch
    from backend.integrations.web_capture import capture_web_content
    from backend.models.source import SourceItem, SourceType

    logger.info(f"[{ctx.job_id}] Stage 6: Capturing web content (v2 with Jina)")
    update_job(ctx.job_id, stage="web_capture", progress_percent=55)

    if not ctx.web_sources:
        logger.info(f"[{ctx.job_id}] No web sources to capture")
        return

    try:
        # Try v2 extraction first
        try:
            logger.info(f"[{ctx.job_id}] Attempting v2 extraction (Jina/Trafilatura)...")
            urls = [s if isinstance(s, str) else s.url for s in ctx.web_sources]
            results = extract_content_batch(urls)

            captured = []
            jina_success = 0
            for result in results:
                if result.get("content") and len(result.get("content", "")) > 100:
                    source = SourceItem(
                        url=result["url"],
                        title=result.get("title", ""),
                        source_type=SourceType.WEB,
                        text=result["content"],
                        notes=f"Extracted via {result.get('api', 'unknown')}"
                    )
                    captured.append(source)
                    if result.get("api") == "jina":
                        jina_success += 1
                else:
                    source = SourceItem(
                        url=result["url"],
                        title="",
                        source_type=SourceType.WEB,
                        text="",
                        notes="Extraction failed - needs Playwright fallback"
                    )
                    captured.append(source)

            successful = sum(1 for s in captured if s.text)
            logger.info(f"[{ctx.job_id}] V2 extracted {successful}/{len(captured)} sources ({jina_success} via Jina)")

            # Playwright fallback for failed sources
            failed = [s for s in captured if not s.text]
            if failed:
                logger.info(f"[{ctx.job_id}] Trying Playwright fallback for {len(failed)} failed sources...")
                try:
                    pw_sources = capture_web_content([s.url for s in failed])
                    pw_dict = {s.url: s for s in pw_sources}
                    captured = [pw_dict.get(s.url, s) if not s.text else s for s in captured]
                    pw_success = sum(1 for s in pw_sources if s.text)
                    logger.info(f"[{ctx.job_id}] Playwright recovered {pw_success}/{len(failed)} sources")
                except Exception as pw_error:
                    logger.warning(f"[{ctx.job_id}] Playwright fallback failed: {pw_error}")
                    ctx.add_warning(f"Playwright fallback failed: {str(pw_error)}")

            ctx.web_sources = captured
            final_success = sum(1 for s in captured if s.text)
            logger.info(f"[{ctx.job_id}] Total captured: {final_success}/{len(captured)} web sources")

        except Exception as v2_error:
            logger.warning(f"[{ctx.job_id}] V2 extraction failed, falling back to Playwright only: {v2_error}")
            ctx.add_warning(f"V2 extraction failed, using Playwright: {str(v2_error)}")
            captured = capture_web_content(ctx.web_sources)
            successful = sum(1 for s in captured if s.text)
            logger.info(f"[{ctx.job_id}] Captured {successful}/{len(captured)} web sources (Playwright fallback)")
            ctx.web_sources = captured

        # Collect capture warnings
        for source in ctx.web_sources:
            if source.notes and "failed" in source.notes.lower():
                ctx.add_warning(f"Web capture failed for: {source.url[:50]}...")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Web capture failed: {e}")
        ctx.add_warning(f"Web capture failed: {str(e)}")


# =============================================================================
# Stage 6.5: Reddit Collection
# =============================================================================

def stage_6_5_reddit(ctx: PipelineContext) -> None:
    """Collect Reddit discussions."""
    logger.info(f"[{ctx.job_id}] Stage 6.5: Reddit collection")
    update_job(ctx.job_id, stage="reddit_collection", progress_percent=58)

    try:
        from backend.integrations.reddit_client import RedditClient, extract_reddit_content
        from backend.models.source import SourceItem, SourceType

        reddit_client = RedditClient()
        ctx.reddit_posts = reddit_client.search_multiple_subreddits(
            query=ctx.topic,
            limit_per_sub=5
        )

        if ctx.reddit_posts:
            reddit_md = extract_reddit_content(ctx.reddit_posts)
            ctx.set_output("reddit_discussions_md", reddit_md)

            reddit_source = SourceItem(
                url="https://reddit.com/search",
                title="Reddit Discussions",
                source_type=SourceType.REDDIT,
                text=reddit_md,
                notes="Aggregated Reddit discussions"
            )
            ctx.web_sources.append(reddit_source)
            logger.info(f"[{ctx.job_id}] Collected {len(ctx.reddit_posts)} Reddit posts")
        else:
            ctx.set_output("reddit_discussions_md", "# Reddit Discussions\n\nNo relevant Reddit posts found.")

    except ImportError:
        logger.info(f"[{ctx.job_id}] Reddit integration not available")
        ctx.set_output("reddit_discussions_md", "# Reddit Discussions\n\n*Reddit integration not installed*")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Reddit collection failed: {e}")
        ctx.add_warning(f"Reddit collection failed: {str(e)}")
        ctx.set_output("reddit_discussions_md", f"# Reddit Discussions\n\n*Error: {str(e)}*")


# =============================================================================
# Stage 7: Claim Extraction
# =============================================================================

def stage_7_extraction(ctx: PipelineContext) -> None:
    """Extract claims from transcripts and web sources."""
    from backend.pipeline.extraction import extract_claims

    logger.info(f"[{ctx.job_id}] Stage 7: Extracting claims")
    update_job(ctx.job_id, stage="claim_extraction", progress_percent=65)
    post_slack_message(ctx, "🔍 Extracting claims...")

    try:
        if ctx.transcripts or any(s.text for s in ctx.web_sources):
            ctx.claims, quote_bank_md, claims_ledger_md = extract_claims(ctx.transcripts, ctx.web_sources)
            ctx.set_output("quote_bank_md", quote_bank_md)
            ctx.set_output("claims_ledger_md", claims_ledger_md)
            # Track OpenAI cost (estimate ~2K tokens for extraction)
            ctx.add_cost("openai_claim_extraction", 0.003)
            logger.info(f"[{ctx.job_id}] Extracted {len(ctx.claims)} claims")
        else:
            ctx.set_output("quote_bank_md", "# Quote Bank\n\n*No content available for extraction*")
            ctx.set_output("claims_ledger_md", "# Claims Ledger\n\n*No content available for extraction*")
            logger.info(f"[{ctx.job_id}] No content available for extraction")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Claim extraction failed: {e}")
        ctx.add_warning(f"Claim extraction failed: {str(e)}")
        ctx.set_output("quote_bank_md", f"# Quote Bank\n\n*Error: {str(e)}*")
        ctx.set_output("claims_ledger_md", f"# Claims Ledger\n\n*Error: {str(e)}*")


# =============================================================================
# Stage 7.5: Timeline Extraction
# =============================================================================

def stage_7_5_timeline(ctx: PipelineContext) -> None:
    """Extract timeline events."""
    from backend.pipeline.timeline import extract_timeline, generate_timeline_markdown

    logger.info(f"[{ctx.job_id}] Stage 7.5: Timeline extraction")
    update_job(ctx.job_id, stage="timeline_extraction", progress_percent=68)

    try:
        ctx.timeline_events = extract_timeline(ctx.transcripts, ctx.web_sources, ctx.claims)

        if ctx.timeline_events:
            timeline_data = [event.model_dump() for event in ctx.timeline_events]
            update_job(ctx.job_id, partial_outputs={"timeline_events": timeline_data})
            ctx.set_output("timeline_md", generate_timeline_markdown(ctx.timeline_events))
            logger.info(f"[{ctx.job_id}] Extracted {len(ctx.timeline_events)} timeline events")
        else:
            ctx.set_output("timeline_md", "# Timeline\n\nNo timeline events extracted.")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Timeline extraction failed: {e}")
        ctx.add_warning(f"Timeline extraction failed: {str(e)}")
        ctx.set_output("timeline_md", f"# Timeline\n\n*Error: {str(e)}*")


# =============================================================================
# Stage 7.6: Entity Extraction
# =============================================================================

def stage_7_6_entities(ctx: PipelineContext) -> None:
    """Extract entities (people, organizations, locations)."""
    from backend.pipeline.entities import EntityExtractor, generate_entities_markdown

    logger.info(f"[{ctx.job_id}] Stage 7.6: Entity extraction")
    update_job(ctx.job_id, stage="entity_extraction", progress_percent=70)

    try:
        extractor = EntityExtractor()
        ctx.entities = extractor.extract_entities(ctx.transcripts, ctx.web_sources, ctx.claims)

        if ctx.entities:
            update_job(ctx.job_id, partial_outputs={"entities": ctx.entities})
            ctx.set_output("entities_md", generate_entities_markdown(ctx.entities))
            total = sum(len(ctx.entities.get(cat, [])) for cat in ctx.entities)
            logger.info(f"[{ctx.job_id}] Extracted {total} entities")
        else:
            ctx.set_output("entities_md", "# Entities\n\nNo entities extracted.")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Entity extraction failed: {e}")
        ctx.add_warning(f"Entity extraction failed: {str(e)}")
        ctx.set_output("entities_md", f"# Entities\n\n*Error: {str(e)}*")


# =============================================================================
# Stage 8: Claim Validation
# =============================================================================

def stage_8_validation(ctx: PipelineContext) -> None:
    """Validate claims using multi-stage validation."""
    from backend.pipeline.validation_v2 import validate_claims_v2
    from backend.pipeline.validation import validate_claims

    logger.info(f"[{ctx.job_id}] Stage 8: Validating claims (v2 multi-stage)")
    update_job(ctx.job_id, stage="claim_validation", progress_percent=75)

    if not ctx.claims:
        ctx.set_output("evidence_table_md", "# Evidence Table\n\n*No claims to validate*")
        ctx.set_output("missing_angles_md", "# Missing Angles\n\n*No claims available for analysis*")
        return

    try:
        max_perplexity = getattr(ctx.job_config.budgets, 'max_claims_to_validate', 10)
        ctx.evidence_records, cost_breakdown = validate_claims_v2(
            ctx.claims,
            ctx.topic,
            max_perplexity_calls=max_perplexity
        )
        # Track validation costs from v2 breakdown
        if cost_breakdown:
            ctx.add_cost("perplexity_validation", cost_breakdown.get("perplexity", 0))
            ctx.add_cost("openai_validation", cost_breakdown.get("openai", 0))

        try:
            _, evidence_table_md, missing_angles_md = validate_claims(ctx.claims, ctx.job_config)
            ctx.set_output("evidence_table_md", evidence_table_md)
            ctx.set_output("missing_angles_md", missing_angles_md)
        except Exception:
            from backend.worker import _generate_evidence_table_md
            ctx.set_output("evidence_table_md", _generate_evidence_table_md(ctx.evidence_records))
            ctx.set_output("missing_angles_md", "# Missing Angles\n\n*Analysis not available*")

        logger.info(f"[{ctx.job_id}] Validated {len(ctx.evidence_records)} claims (cost: ${cost_breakdown.get('total', 0):.2f})")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Claim validation v2 failed, falling back to v1: {e}")
        ctx.add_warning(f"Claim validation v2 failed, using v1: {str(e)}")

        try:
            ctx.evidence_records, evidence_table_md, missing_angles_md = validate_claims(ctx.claims, ctx.job_config)
            ctx.set_output("evidence_table_md", evidence_table_md)
            ctx.set_output("missing_angles_md", missing_angles_md)
            logger.info(f"[{ctx.job_id}] Validated {len(ctx.evidence_records)} claims (v1 fallback)")
        except Exception as e2:
            logger.error(f"[{ctx.job_id}] Both v2 and v1 validation failed: {e2}")
            ctx.set_output("evidence_table_md", f"# Evidence Table\n\n*Error: {str(e2)}*")
            ctx.set_output("missing_angles_md", f"# Missing Angles\n\n*Error: {str(e2)}*")


# =============================================================================
# Stage 8.5: Angle Discovery
# =============================================================================

def stage_8_5_angle_discovery(ctx: PipelineContext) -> None:
    """Discover unique angles from research data."""
    from backend.pipeline.angle_discovery import AngleDiscovery

    logger.info(f"[{ctx.job_id}] Stage 8.5: Angle discovery")
    update_job(ctx.job_id, stage="angle_discovery", progress_percent=78)

    try:
        angle_discovery = AngleDiscovery()
        ctx.discovered_angles = angle_discovery.discover_angles(
            topic=ctx.topic,
            research_data={
                "timeline": [e.model_dump() for e in ctx.timeline_events] if ctx.timeline_events else [],
                "entities": ctx.entities,
                "claims": ctx.claims,
                "sources": ctx.web_sources + ctx.transcripts
            }
        )

        if ctx.discovered_angles:
            update_job(ctx.job_id, partial_outputs={
                "discovered_angles": ctx.discovered_angles.get("discovered_angles", []),
                "coverage_analysis": ctx.discovered_angles.get("coverage_map", {})
            })
            ctx.outputs["discovered_angles"] = ctx.discovered_angles
            angle_count = len(ctx.discovered_angles.get("discovered_angles", []))
            logger.info(f"[{ctx.job_id}] Discovered {angle_count} unique angles")
        else:
            logger.info(f"[{ctx.job_id}] No unique angles discovered")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Angle discovery failed: {e}")
        ctx.add_warning(f"Angle discovery failed: {str(e)}")


# =============================================================================
# Stage 8.6: Documentary Intelligence
# =============================================================================

def stage_8_6_documentary_intelligence(ctx: PipelineContext) -> None:
    """Analyze research data for documentary production and generate dual output."""
    from backend.pipeline.documentary_intelligence import DocumentaryIntelligence
    from backend.pipeline.dual_output import format_dual_output

    logger.info(f"[{ctx.job_id}] Stage 8.6: Documentary intelligence analysis")
    update_job(ctx.job_id, stage="documentary_analysis", progress_percent=82)

    try:
        doc_intel = DocumentaryIntelligence()
        job = get_job(ctx.job_id)
        pipeline_mode = job.pipeline if hasattr(job, 'pipeline') else "investigation"

        research_data = {
            "timeline": [e.model_dump() for e in ctx.timeline_events] if ctx.timeline_events else [],
            "entities": ctx.entities,
            "claims": ctx.claims,
            "sources": ctx.web_sources + ctx.transcripts,
            "validation": ctx.evidence_records,
            "discovered_angles": ctx.discovered_angles
        }

        ctx.documentary_analysis = doc_intel.analyze(
            research_data=research_data,
            doc_type=pipeline_mode
        )

        if ctx.documentary_analysis:
            ctx.outputs["documentary_analysis"] = ctx.documentary_analysis
            logger.info(f"[{ctx.job_id}] Documentary analysis complete")

            # Generate dual output: NotebookLM packet + Documentary blueprint
            try:
                dual_output = format_dual_output(
                    research_data=research_data,
                    documentary_analysis=ctx.documentary_analysis,
                    title=ctx.short_title or ctx.topic,
                )
                ctx.set_output("notebooklm_packet_md", dual_output["notebooklm_md"])
                ctx.set_output("documentary_blueprint_md", dual_output["documentary_md"])
                logger.info(f"[{ctx.job_id}] Generated dual output (NotebookLM + Documentary)")
            except Exception as dual_error:
                logger.warning(f"[{ctx.job_id}] Dual output generation failed: {dual_error}")
                ctx.add_warning(f"Dual output generation failed: {str(dual_error)}")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Documentary analysis failed: {e}")
        ctx.add_warning(f"Documentary analysis failed: {str(e)}")


# =============================================================================
# Stage 9: Drive Upload
# =============================================================================

def stage_9_drive_upload(ctx: PipelineContext) -> None:
    """Upload research packet to Google Drive."""
    from backend.integrations.google_drive_docs import create_research_packet
    from backend.pipeline.document_helpers import (
        generate_master_index,
        generate_transcripts_md,
        generate_web_extracts_md,
    )

    logger.info(f"[{ctx.job_id}] Stage 9: Writing Drive docs")
    update_job(ctx.job_id, stage="drive_upload", progress_percent=85)
    post_slack_message(ctx, "📝 Writing docs...")

    try:
        doc_contents = {
            "00_MASTER_INDEX": generate_master_index(ctx.job_config, ctx.outputs),
            "01_RESEARCH_MAP": ctx.outputs.get("research_map_md", ""),
            "02_SOURCE_SHORTLIST": ctx.outputs.get("source_shortlist_md", ""),
            "03_YOUTUBE_INDEX": ctx.outputs.get("youtube_index_md", ""),
            "04_TRANSCRIPTS": generate_transcripts_md(ctx.transcripts),
            "05_WEB_EXTRACTS": generate_web_extracts_md(ctx.web_sources),
            "06_QUOTE_BANK": ctx.outputs.get("quote_bank_md", ""),
            "07_CLAIMS_LEDGER": ctx.outputs.get("claims_ledger_md", ""),
            "08_EVIDENCE_TABLE": ctx.outputs.get("evidence_table_md", ""),
            "09_MISSING_ANGLES": ctx.outputs.get("missing_angles_md", ""),
        }

        # Add dual output documents if available
        if ctx.outputs.get("notebooklm_packet_md"):
            doc_contents["10_NOTEBOOKLM_PACKET"] = ctx.outputs["notebooklm_packet_md"]
        if ctx.outputs.get("documentary_blueprint_md"):
            doc_contents["11_DOCUMENTARY_BLUEPRINT"] = ctx.outputs["documentary_blueprint_md"]

        folder_name = ctx.job_config.output.drive_folder_name or f"Research: {ctx.job_config.topic}"

        job = get_job(ctx.job_id)
        user_email = None
        user_id = None
        if job and job.config_json:
            user_email = job.config_json.get("user_email")
            user_id = job.config_json.get("user_id")

        drive_result = create_research_packet(
            folder_name,
            doc_contents,
            user_email=user_email,
            user_id=user_id,
        )
        ctx.folder_url = drive_result["folder_url"]
        ctx.doc_urls = drive_result["doc_urls"]

        doc_url_list = list(ctx.doc_urls.values()) if ctx.doc_urls else []
        update_job(
            ctx.job_id,
            partial_artifacts={
                "drive_folder_url": ctx.folder_url,
                "doc_urls": doc_url_list,
            },
        )

        logger.info(f"[{ctx.job_id}] Created Drive folder: {ctx.folder_url}")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Drive upload failed: {e}")
        ctx.add_warning(f"Drive upload failed: {str(e)}")


# =============================================================================
# Stage 10: Completion
# =============================================================================

def stage_10_completion(ctx: PipelineContext) -> dict:
    """Mark job complete and send notifications."""
    logger.info(f"[{ctx.job_id}] Stage 10: Completing job")

    # Get cost summary for final output
    cost_summary = ctx.get_cost_summary()

    # Add cost and quality gate stats to outputs
    final_outputs = dict(ctx.outputs)
    if cost_summary:
        final_outputs["cost_summary"] = cost_summary
    if ctx.quality_gate_stats:
        final_outputs["quality_gate_stats"] = ctx.quality_gate_stats

    update_job(
        ctx.job_id,
        status="completed",
        stage="completed",
        progress_percent=100,
        partial_outputs=final_outputs,
        warnings_append=ctx.warnings,
    )

    # Build completion message
    if ctx.folder_url:
        message = (
            f"✅ Research job `{ctx.job_id}` completed!\n\n"
            f"📁 Drive folder: {ctx.folder_url}\n"
            f"📊 Claims extracted: {len(ctx.claims)}\n"
            f"📚 Sources: {len(ctx.web_sources)} web, {len(ctx.youtube_videos)} YouTube videos"
        )
        if ctx.warnings:
            message += f"\n⚠️ {len(ctx.warnings)} warnings (see job details)"
    else:
        message = (
            f"✅ Research job `{ctx.job_id}` completed!\n\n"
            f"⚠️ Drive upload failed, but results are available via API\n"
            f"📊 Claims extracted: {len(ctx.claims)}\n"
            f"📚 Sources: {len(ctx.web_sources)} web, {len(ctx.youtube_videos)} YouTube videos"
        )

    post_slack_message(ctx, message)

    result = {
        "job_id": ctx.job_id,
        "status": "completed",
        "folder_url": ctx.folder_url,
        "doc_urls": ctx.doc_urls,
        "claims_count": len(ctx.claims),
        "sources_count": len(ctx.web_sources),
        "youtube_videos_count": len(ctx.youtube_videos),
        "warnings_count": len(ctx.warnings),
        "cost_summary": cost_summary,
        "quality_gate_stats": ctx.quality_gate_stats,
    }

    logger.info(f"Research job {ctx.job_id} completed successfully (cost: ${cost_summary.get('total_cost', 0):.4f})")
    return result
