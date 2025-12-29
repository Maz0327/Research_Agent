"""Web content capture and Reddit collection stages."""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import update_job


def stage_6_web_capture(ctx: PipelineContext) -> None:
    """Capture web content using Jina -> Trafilatura -> Playwright fallback chain."""
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
