"""YouTube enumeration and transcript fetching stages.

Dec 2025: Enhanced with topic-based search when no channels specified.
- If channels are specified: enumerate channel uploads
- If no channels: search YouTube by topic (auto-discovery)
"""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import update_job


def stage_4_youtube_enumeration(ctx: PipelineContext) -> None:
    """Enumerate YouTube videos - from channels or by topic search.

    Dec 2025: Now supports auto-discovery via YouTube search when no
    channels are specified. This ensures YouTube content is always
    discovered based on the research topic.
    """
    from backend.integrations.youtube_client import (
        enumerate_channel_uploads,
        search_youtube_videos,
    )

    logger.info(f"[{ctx.job_id}] Stage 4: YouTube video discovery")
    update_job(ctx.job_id, stage="youtube_enumeration", progress_percent=35)

    try:
        if ctx.job_config.youtube.channels:
            # Channel enumeration mode (original behavior)
            logger.info(f"[{ctx.job_id}] Using channel enumeration for {len(ctx.job_config.youtube.channels)} channels")
            result = enumerate_channel_uploads(ctx.job_config)
            ctx.youtube_videos = result.get("videos", [])
            ctx.set_output("youtube_index_md", result.get("youtube_index_md", ""))
            logger.info(f"[{ctx.job_id}] Enumerated {len(ctx.youtube_videos)} videos from channels")
        else:
            # Topic search mode (new auto-discovery)
            logger.info(f"[{ctx.job_id}] No channels specified, searching YouTube by topic")
            max_videos = ctx.job_config.youtube.max_videos
            result = search_youtube_videos(
                query=ctx.topic,
                max_results=max_videos,
                exclude_shorts=ctx.job_config.youtube.exclude_shorts,
            )
            ctx.youtube_videos = result.get("videos", [])
            ctx.set_output("youtube_index_md", result.get("youtube_index_md", ""))
            logger.info(f"[{ctx.job_id}] Found {len(ctx.youtube_videos)} videos via topic search")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] YouTube discovery failed: {e}")
        ctx.add_warning(f"YouTube discovery failed: {str(e)}")
        ctx.set_output("youtube_index_md", f"# YouTube Index\n\n*Error: {str(e)}*")


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
                    # Use cloud-compatible fetch_transcript_v2 (Supadata -> Whisper)
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
