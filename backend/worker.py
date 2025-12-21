"""Celery worker configuration and task definitions."""
from datetime import datetime, timezone
from typing import Any, Optional

from celery import Celery
from loguru import logger

from backend.config import get_settings
from backend.integrations.google_drive_docs import create_research_packet
from backend.integrations.openai_client import plan_job, generate_short_title
from backend.integrations.perplexity_client import research_map, source_shortlist
from backend.integrations.transcripts import fetch_transcript, TranscriptStatus
from backend.integrations.web_capture import capture_web_content
from backend.integrations.youtube_client import enumerate_channel_uploads
from backend.models.job_config import JobConfig, DocumentaryMode, get_mode_config
from backend.pipeline.extraction import extract_claims
from backend.pipeline.validation import validate_claims
from backend.state import get_job, update_job
from backend.services.error_logger import log_exception

# NEW v2 API integrations
from backend.pipeline.search import unified_search
from backend.pipeline.content_extraction import extract_content_batch
from backend.pipeline.validation_v2 import validate_claims_v2

# New Phase 2 imports
from backend.pipeline.timeline import extract_timeline, generate_timeline_markdown
from backend.pipeline.entities import EntityExtractor, generate_entities_markdown
from backend.pipeline.angle_discovery import AngleDiscovery
from backend.pipeline.documentary_intelligence import DocumentaryIntelligence

# Reddit integration (optional)
try:
    from backend.integrations.reddit_client import RedditClient, extract_reddit_content
    REDDIT_AVAILABLE = True
except ImportError:
    logger.warning("Reddit client not available - install praw to enable Reddit integration")
    REDDIT_AVAILABLE = False

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "research_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Fix deprecation warning for Celery 5.3+/6.0 compatibility
    broker_connection_retry_on_startup=True,
    task_routes={
        "backend.worker.run_research_job": {"queue": "research"},
    },
    task_default_queue="research",
    task_default_exchange="research",
    task_default_routing_key="research",
)


def _post_slack_message(slack_payload: Optional[dict], message: str) -> None:
    """Helper to post Slack message if payload is provided."""
    if slack_payload and slack_payload.get("response_url"):
        try:
            from backend.integrations.slack import post_slack_message
            post_slack_message(slack_payload["response_url"], message)
        except Exception as e:
            # Log but don't fail the job if Slack notification fails
            logger.warning(f"[Slack] Failed to post message to {slack_payload.get('response_url')}: {e}")


@celery_app.task(name="backend.worker.run_research_job")
def run_research_job(
    job_id: str,
    topic: str,
    slack_payload: Optional[dict] = None,
) -> dict:
    """
    Research job task that runs through all stages of the research pipeline.
    
    Stages:
    1. Plan job (OpenAI)
    2. Perplexity research_map
    3. Perplexity source_shortlist
    4. YouTube enumerate
    5. Transcripts fetch
    6. Web capture
    7. Extraction (quote bank + claims ledger)
    8. Validation (evidence table + missing angles)
    9. Write Drive docs
    10. Slack completion message
    
    Args:
        job_id: Unique identifier for the research job
        topic: Research topic string (from Slack or API)
        slack_payload: Optional Slack payload for posting updates
        
    Returns:
        Dictionary with research results including Drive folder URL
    """
    logger.info(f"Starting research job {job_id} for topic: {topic}")
    
    # Initialize outputs
    outputs = {}
    warnings = []
    
    try:
        # Stage 0: Initialization
        update_job(
            job_id,
            status="running",
            stage="initializing",
            progress_percent=0,
        )
        _post_slack_message(slack_payload, f"✅ Started research job: `{job_id}`\nTopic: {topic}")
        
        # Stage 1: Plan job (OpenAI)
        logger.info(f"[{job_id}] Stage 1: Planning job")
        update_job(
            job_id,
            stage="planning",
            progress_percent=5,
        )
        
        try:
            # Validate topic before planning
            if not topic or not topic.strip():
                raise ValueError("Topic cannot be empty")
            
            job_config = plan_job(topic)
            
            # Validate job_config structure
            if not isinstance(job_config, JobConfig):
                raise ValueError(f"plan_job returned invalid type: {type(job_config)}")
            
            config_dict = job_config.model_dump()
            if not config_dict or "topic" not in config_dict:
                raise ValueError("Invalid job_config structure: missing required fields")
            
            # Generate short title for the job
            try:
                short_title = generate_short_title(topic)
                logger.info(f"[{job_id}] Generated title: '{short_title}'")
            except Exception as title_error:
                logger.warning(f"[{job_id}] Failed to generate title: {title_error}")
                # Fallback to first 6 words
                short_title = " ".join(topic.split()[:6]).title()
                warnings.append(f"Title generation failed, using fallback: {short_title}")

            # Save config and title to job
            job = get_job(job_id)
            if job:
                update_job(
                    job_id,
                    title=short_title,
                    partial_outputs={"config_json": config_dict},
                )
            logger.info(f"[{job_id}] Planned job: {job_config.topic}, mode={job_config.mode}")
        except Exception as e:
            logger.warning(f"[{job_id}] Planning failed: {e}")
            warnings.append(f"Planning failed: {str(e)}, using default config")
            # Use default config
            from backend.integrations.openai_client import _safe_default_config
            job_config = _safe_default_config(topic)
        
        # Stage 2: Perplexity research_map
        logger.info(f"[{job_id}] Stage 2: Generating research map")
        update_job(
            job_id,
            stage="research_mapping",
            progress_percent=15,
        )
        
        try:
            research_map_result = research_map(job_config)
            outputs["research_map_md"] = research_map_result.get("research_map_md", "")
            angles = research_map_result.get("angles", [])
            key_terms = research_map_result.get("key_terms", [])
            logger.info(f"[{job_id}] Generated research map with {len(angles)} angles")
        except Exception as e:
            logger.warning(f"[{job_id}] Research map generation failed: {e}")
            warnings.append(f"Research map generation failed: {str(e)}")
            outputs["research_map_md"] = f"# Research Map\n\n*Error: {str(e)}*"
            angles = []
            key_terms = []
        
        # Stage 3: Perplexity source_shortlist
        logger.info(f"[{job_id}] Stage 3: Generating source shortlist")
        update_job(
            job_id,
            stage="source_discovery",
            progress_percent=25,
        )
        _post_slack_message(slack_payload, "📚 Collecting sources...")
        
        try:
            if not angles:
                logger.warning(f"[{job_id}] No research angles available for source shortlist")
                warnings.append("No research angles available - using topic as fallback")
                angles = ["general"]
            
            shortlist_result = source_shortlist(job_config, angles, key_terms)
            web_sources = shortlist_result.get("urls", []) or []
            outputs["source_shortlist_md"] = shortlist_result.get("shortlist_md", "")
            
            # Enforce budget cap
            if web_sources:
                max_urls = job_config.budgets.max_web_urls
                if len(web_sources) > max_urls:
                    web_sources = web_sources[:max_urls]
                    warnings.append(f"Source shortlist capped to {max_urls} URLs")
                logger.info(f"[{job_id}] Generated source shortlist with {len(web_sources)} URLs")
            else:
                logger.warning(f"[{job_id}] No sources found in shortlist")
                warnings.append("No sources found in shortlist")
        except Exception as e:
            logger.warning(f"[{job_id}] Source shortlist generation failed: {e}")
            warnings.append(f"Source shortlist generation failed: {str(e)}")
            web_sources = []
            outputs["source_shortlist_md"] = f"# Source Shortlist\n\n*Error: {str(e)}*"
        
        # Stage 4: YouTube enumerate
        logger.info(f"[{job_id}] Stage 4: Enumerating YouTube uploads")
        update_job(
            job_id,
            stage="youtube_enumeration",
            progress_percent=35,
        )
        
        youtube_videos = []
        try:
            if job_config.youtube.channels:
                youtube_result = enumerate_channel_uploads(job_config)
                youtube_videos = youtube_result.get("videos", [])
                outputs["youtube_index_md"] = youtube_result.get("youtube_index_md", "")
                logger.info(f"[{job_id}] Enumerated {len(youtube_videos)} YouTube videos")
            else:
                outputs["youtube_index_md"] = "# YouTube Index\n\n*No channels specified*"
                logger.info(f"[{job_id}] No YouTube channels specified")
        except Exception as e:
            logger.warning(f"[{job_id}] YouTube enumeration failed: {e}")
            warnings.append(f"YouTube enumeration failed: {str(e)}")
            youtube_videos = []
            outputs["youtube_index_md"] = f"# YouTube Index\n\n*Error: {str(e)}*"
        
        # Stage 5: Transcripts fetch
        logger.info(f"[{job_id}] Stage 5: Fetching transcripts")
        update_job(
            job_id,
            stage="transcript_fetching",
            progress_percent=45,
        )
        
        transcripts = []
        total_transcription_minutes = 0
        max_transcription_minutes = job_config.budgets.max_transcription_minutes
        
        try:
            if job_config.youtube.fetch_transcripts and youtube_videos:
                for video in youtube_videos[:job_config.youtube.max_videos]:
                    # Check budget
                    video_minutes = (video.duration_seconds or 0) / 60
                    if total_transcription_minutes + video_minutes > max_transcription_minutes:
                        logger.info(f"[{job_id}] Transcription budget reached, skipping remaining videos")
                        warnings.append(f"Transcription budget ({max_transcription_minutes} min) reached")
                        break
                    
                    try:
                        transcript = fetch_transcript(video.url)
                        if transcript.status == TranscriptStatus.AVAILABLE:
                            transcripts.append(transcript)
                            total_transcription_minutes += video_minutes
                            logger.debug(f"[{job_id}] Fetched transcript for {video.video_id}")
                        else:
                            warnings.append(f"Transcript missing for video: {video.title}")
                    except Exception as e:
                        logger.warning(f"[{job_id}] Failed to fetch transcript for {video.video_id}: {e}")
                        warnings.append(f"Transcript fetch failed for {video.title}: {str(e)}")
                
                logger.info(f"[{job_id}] Fetched {len(transcripts)} transcripts")
        except Exception as e:
            logger.warning(f"[{job_id}] Transcript fetching failed: {e}")
            warnings.append(f"Transcript fetching failed: {str(e)}")
            transcripts = []
        
        # Stage 6: Web capture (v2 with Jina → Trafilatura → Playwright fallback)
        logger.info(f"[{job_id}] Stage 6: Capturing web content (v2 with Jina)")
        update_job(
            job_id,
            stage="web_capture",
            progress_percent=55,
        )

        try:
            if web_sources:
                # Try v2 extraction first (Jina → Trafilatura → Playwright)
                try:
                    logger.info(f"[{job_id}] Attempting v2 extraction (Jina/Trafilatura)...")
                    from backend.models.source import SourceItem

                    # Extract URLs from web_sources
                    urls_to_extract = [s if isinstance(s, str) else s.url for s in web_sources]

                    # Use v2 batch extraction
                    extraction_results = extract_content_batch(urls_to_extract)

                    # Convert results to SourceItem objects
                    from backend.models.source import SourceType
                    captured_sources = []
                    jina_success = 0
                    for result in extraction_results:
                        if result.get("content") and len(result.get("content", "")) > 100:
                            source = SourceItem(
                                url=result["url"],
                                title=result.get("title", ""),
                                source_type=SourceType.WEB,  # Added required field
                                text=result["content"],
                                notes=f"Extracted via {result.get('api', 'unknown')}"
                            )
                            captured_sources.append(source)
                            if result.get("api") == "jina":
                                jina_success += 1
                        else:
                            # Failed extraction - mark for Playwright fallback
                            source = SourceItem(
                                url=result["url"],
                                title="",
                                source_type=SourceType.WEB,  # Added required field
                                text="",
                                notes="Extraction failed - needs Playwright fallback"
                            )
                            captured_sources.append(source)

                    successful_captures = sum(1 for s in captured_sources if s.text)
                    logger.info(f"[{job_id}] V2 extracted {successful_captures}/{len(captured_sources)} sources ({jina_success} via Jina)")

                    # For sources that failed v2, try Playwright as fallback
                    failed_sources = [s for s in captured_sources if not s.text]
                    if failed_sources:
                        logger.info(f"[{job_id}] Trying Playwright fallback for {len(failed_sources)} failed sources...")
                        try:
                            playwright_sources = capture_web_content([s.url for s in failed_sources])
                            # Replace failed sources with Playwright results
                            playwright_dict = {s.url: s for s in playwright_sources}
                            captured_sources = [
                                playwright_dict.get(s.url, s) if not s.text else s
                                for s in captured_sources
                            ]
                            playwright_success = sum(1 for s in playwright_sources if s.text)
                            logger.info(f"[{job_id}] Playwright recovered {playwright_success}/{len(failed_sources)} sources")
                        except Exception as pw_error:
                            logger.warning(f"[{job_id}] Playwright fallback failed: {pw_error}")
                            warnings.append(f"Playwright fallback failed: {str(pw_error)}")

                    web_sources = captured_sources
                    final_success = sum(1 for s in captured_sources if s.text)
                    logger.info(f"[{job_id}] Total captured: {final_success}/{len(captured_sources)} web sources")

                except Exception as v2_error:
                    logger.warning(f"[{job_id}] V2 extraction failed, falling back to Playwright only: {v2_error}")
                    warnings.append(f"V2 extraction failed, using Playwright: {str(v2_error)}")

                    # Fallback: Use old Playwright-only capture
                    captured_sources = capture_web_content(web_sources)
                    successful_captures = sum(1 for s in captured_sources if s.text)
                    logger.info(f"[{job_id}] Captured {successful_captures}/{len(captured_sources)} web sources (Playwright fallback)")
                    web_sources = captured_sources

                # Collect any capture warnings
                for source in web_sources:
                    if source.notes and "failed" in source.notes.lower():
                        warnings.append(f"Web capture failed for: {source.url[:50]}...")
            else:
                logger.info(f"[{job_id}] No web sources to capture")
        except Exception as e:
            logger.warning(f"[{job_id}] Web capture failed: {e}")
            warnings.append(f"Web capture failed: {str(e)}")
            # Continue with uncaptured sources

        # NEW Stage 6.5: Reddit Collection
        logger.info(f"[{job_id}] Stage 6.5: Reddit collection")
        update_job(job_id, stage="reddit_collection", progress_percent=58)

        reddit_posts = []
        try:
            if REDDIT_AVAILABLE:
                reddit_client = RedditClient()
                reddit_posts = reddit_client.search_multiple_subreddits(
                    query=topic,
                    limit_per_sub=5  # 5 posts per subreddit
                )

                # Store Reddit posts
                if reddit_posts:
                    # Convert to markdown for processing
                    reddit_md = extract_reddit_content(reddit_posts)
                    outputs["reddit_discussions_md"] = reddit_md

                    # Add Reddit content as sources for claim extraction
                    reddit_source = {
                        "url": "reddit.com/search",
                        "title": "Reddit Discussions",
                        "source_type": "reddit",
                        "text": reddit_md
                    }
                    # Add as a source for later processing
                    from backend.models.source import SourceItem, SourceType
                    reddit_source_item = SourceItem(
                        url="https://reddit.com/search",
                        title="Reddit Discussions",
                        source_type=SourceType.REDDIT,  # Added required field
                        text=reddit_md,
                        notes="Aggregated Reddit discussions"
                    )
                    web_sources.append(reddit_source_item)

                    logger.info(f"[{job_id}] Collected {len(reddit_posts)} Reddit posts")
                else:
                    outputs["reddit_discussions_md"] = "# Reddit Discussions\n\nNo relevant Reddit posts found."
            else:
                logger.info(f"[{job_id}] Reddit integration not available")
                outputs["reddit_discussions_md"] = "# Reddit Discussions\n\n*Reddit integration not installed*"
        except Exception as e:
            logger.warning(f"[{job_id}] Reddit collection failed: {e}")
            warnings.append(f"Reddit collection failed: {str(e)}")
            outputs["reddit_discussions_md"] = f"# Reddit Discussions\n\n*Error: {str(e)}*"

        # Stage 7: Extraction (quote bank + claims ledger)
        logger.info(f"[{job_id}] Stage 7: Extracting claims")
        update_job(
            job_id,
            stage="claim_extraction",
            progress_percent=65,
        )
        _post_slack_message(slack_payload, "🔍 Extracting claims...")
        
        claims = []
        try:
            if transcripts or any(s.text for s in web_sources):
                claims, quote_bank_md, claims_ledger_md = extract_claims(transcripts, web_sources)
                outputs["quote_bank_md"] = quote_bank_md
                outputs["claims_ledger_md"] = claims_ledger_md
                logger.info(f"[{job_id}] Extracted {len(claims)} claims")
            else:
                outputs["quote_bank_md"] = "# Quote Bank\n\n*No content available for extraction*"
                outputs["claims_ledger_md"] = "# Claims Ledger\n\n*No content available for extraction*"
                logger.info(f"[{job_id}] No content available for extraction")
        except Exception as e:
            logger.warning(f"[{job_id}] Claim extraction failed: {e}")
            warnings.append(f"Claim extraction failed: {str(e)}")
            outputs["quote_bank_md"] = f"# Quote Bank\n\n*Error: {str(e)}*"
            outputs["claims_ledger_md"] = f"# Claims Ledger\n\n*Error: {str(e)}*"
            claims = []

        # NEW Stage 7.5: Timeline Extraction
        logger.info(f"[{job_id}] Stage 7.5: Timeline extraction")
        update_job(job_id, stage="timeline_extraction", progress_percent=68)

        timeline_events = []
        try:
            timeline_events = extract_timeline(transcripts, web_sources, claims)

            # Store timeline
            if timeline_events:
                timeline_data = [event.model_dump() for event in timeline_events]
                update_job(job_id, partial_outputs={"timeline_events": timeline_data})

                # Generate timeline markdown
                timeline_md = generate_timeline_markdown(timeline_events)
                outputs["timeline_md"] = timeline_md

                logger.info(f"[{job_id}] Extracted {len(timeline_events)} timeline events")
            else:
                outputs["timeline_md"] = "# Timeline\n\nNo timeline events extracted."
        except Exception as e:
            logger.warning(f"[{job_id}] Timeline extraction failed: {e}")
            warnings.append(f"Timeline extraction failed: {str(e)}")
            outputs["timeline_md"] = f"# Timeline\n\n*Error: {str(e)}*"

        # NEW Stage 7.6: Entity Extraction
        logger.info(f"[{job_id}] Stage 7.6: Entity extraction")
        update_job(job_id, stage="entity_extraction", progress_percent=70)

        entities = {}
        try:
            extractor = EntityExtractor()
            entities = extractor.extract_entities(transcripts, web_sources, claims)

            # Store entities
            if entities:
                update_job(job_id, partial_outputs={"entities": entities})

                # Generate entities markdown
                entities_md = generate_entities_markdown(entities)
                outputs["entities_md"] = entities_md

                total_entities = sum(len(entities.get(cat, [])) for cat in entities)
                logger.info(f"[{job_id}] Extracted {total_entities} entities")
            else:
                outputs["entities_md"] = "# Entities\n\nNo entities extracted."
        except Exception as e:
            logger.warning(f"[{job_id}] Entity extraction failed: {e}")
            warnings.append(f"Entity extraction failed: {str(e)}")
            outputs["entities_md"] = f"# Entities\n\n*Error: {str(e)}*"

        # Stage 8: Validation (evidence table + missing angles)
        logger.info(f"[{job_id}] Stage 8: Validating claims (v2 multi-stage)")
        update_job(
            job_id,
            stage="claim_validation",
            progress_percent=75,
        )

        evidence_records = []
        try:
            if claims:
                # Use v2 multi-stage validator (ClaimBuster → Google FC → Perplexity)
                max_perplexity = job_config.budgets.max_claims_to_validate if hasattr(job_config.budgets, 'max_claims_to_validate') else 10
                evidence_records, cost_breakdown = validate_claims_v2(
                    claims,
                    topic,
                    max_perplexity_calls=max_perplexity
                )

                # Generate output markdown (use old format for compatibility)
                # NOTE: This reuses the formatting logic from the old validate_claims
                # We just pass the evidence_records through the formatter
                try:
                    _, evidence_table_md, missing_angles_md = validate_claims(claims, job_config)
                    outputs["evidence_table_md"] = evidence_table_md
                    outputs["missing_angles_md"] = missing_angles_md
                except:
                    # Fallback: Generate simple table if old formatter fails
                    outputs["evidence_table_md"] = _generate_evidence_table_md(evidence_records)
                    outputs["missing_angles_md"] = "# Missing Angles\n\n*Analysis not available*"

                logger.info(f"[{job_id}] Validated {len(evidence_records)} claims (cost: ${cost_breakdown.get('total', 0):.2f})")
            else:
                outputs["evidence_table_md"] = "# Evidence Table\n\n*No claims to validate*"
                outputs["missing_angles_md"] = "# Missing Angles\n\n*No claims available for analysis*"
        except Exception as e:
            logger.warning(f"[{job_id}] Claim validation v2 failed, falling back to v1: {e}")
            warnings.append(f"Claim validation v2 failed, using v1: {str(e)}")

            # Fallback to old validation
            try:
                evidence_records, evidence_table_md, missing_angles_md = validate_claims(claims, job_config)
                outputs["evidence_table_md"] = evidence_table_md
                outputs["missing_angles_md"] = missing_angles_md
                logger.info(f"[{job_id}] Validated {len(evidence_records)} claims (v1 fallback)")
            except Exception as e2:
                logger.error(f"[{job_id}] Both v2 and v1 validation failed: {e2}")
                outputs["evidence_table_md"] = f"# Evidence Table\n\n*Error: {str(e2)}*"
                outputs["missing_angles_md"] = f"# Missing Angles\n\n*Error: {str(e2)}*"

        # NEW Stage 8.5: Angle Discovery
        logger.info(f"[{job_id}] Stage 8.5: Angle discovery")
        update_job(job_id, stage="angle_discovery", progress_percent=78)

        discovered_angles = {}
        try:
            angle_discovery = AngleDiscovery()
            discovered_angles = angle_discovery.discover_angles(
                topic=topic,
                research_data={
                    "timeline": [e.model_dump() for e in timeline_events] if timeline_events else [],
                    "entities": entities,
                    "claims": claims,
                    "sources": web_sources + transcripts
                }
            )

            # Store discovered angles
            if discovered_angles:
                update_job(job_id, partial_outputs={
                    "discovered_angles": discovered_angles.get("discovered_angles", []),
                    "coverage_analysis": discovered_angles.get("coverage_map", {})
                })

                outputs["discovered_angles"] = discovered_angles
                angle_count = len(discovered_angles.get("discovered_angles", []))
                logger.info(f"[{job_id}] Discovered {angle_count} unique angles")
            else:
                logger.info(f"[{job_id}] No unique angles discovered")
        except Exception as e:
            logger.warning(f"[{job_id}] Angle discovery failed: {e}")
            warnings.append(f"Angle discovery failed: {str(e)}")

        # NEW Stage 8.6: Documentary Intelligence Analysis
        logger.info(f"[{job_id}] Stage 8.6: Documentary intelligence analysis")
        update_job(job_id, stage="documentary_analysis", progress_percent=82)

        documentary_analysis = {}
        try:
            doc_intel = DocumentaryIntelligence()

            # Determine documentary type from job config
            job = get_job(job_id)
            pipeline_mode = job.pipeline if hasattr(job, 'pipeline') else "investigation"

            # Include discovered angles in documentary analysis
            documentary_analysis = doc_intel.analyze(
                research_data={
                    "timeline": [e.model_dump() for e in timeline_events] if timeline_events else [],
                    "entities": entities,
                    "claims": claims,
                    "sources": web_sources + transcripts,
                    "validation": evidence_records,
                    "discovered_angles": discovered_angles
                },
                doc_type=pipeline_mode
            )

            if documentary_analysis:
                outputs["documentary_analysis"] = documentary_analysis
                logger.info(f"[{job_id}] Documentary analysis complete")
        except Exception as e:
            logger.warning(f"[{job_id}] Documentary analysis failed: {e}")
            warnings.append(f"Documentary analysis failed: {str(e)}")

        # Stage 9: Write Drive docs
        logger.info(f"[{job_id}] Stage 9: Writing Drive docs")
        update_job(
            job_id,
            stage="drive_upload",
            progress_percent=85,
        )
        _post_slack_message(slack_payload, "📝 Writing docs...")
        
        folder_url = None
        doc_urls = {}
        
        try:
            # Prepare document contents
            doc_contents = {
                "00_MASTER_INDEX": _generate_master_index(job_config, outputs),
                "01_RESEARCH_MAP": outputs.get("research_map_md", ""),
                "02_SOURCE_SHORTLIST": outputs.get("source_shortlist_md", ""),
                "03_YOUTUBE_INDEX": outputs.get("youtube_index_md", ""),
                "04_TRANSCRIPTS": _generate_transcripts_md(transcripts),
                "05_WEB_EXTRACTS": _generate_web_extracts_md(web_sources),
                "06_QUOTE_BANK": outputs.get("quote_bank_md", ""),
                "07_CLAIMS_LEDGER": outputs.get("claims_ledger_md", ""),
                "08_EVIDENCE_TABLE": outputs.get("evidence_table_md", ""),
                "09_MISSING_ANGLES": outputs.get("missing_angles_md", ""),
            }
            
            folder_name = job_config.output.drive_folder_name or f"Research: {job_config.topic}"

            # Get user info from job for Drive sharing
            job = get_job(job_id)
            user_email = None
            user_id_for_drive = None
            if job and job.config_json:
                user_email = job.config_json.get("user_email")
                user_id_for_drive = job.config_json.get("user_id")

            drive_result = create_research_packet(
                folder_name,
                doc_contents,
                user_email=user_email,
                user_id=user_id_for_drive,
            )
            folder_url = drive_result["folder_url"]
            doc_urls = drive_result["doc_urls"]
            
            # Update job with artifacts
            # Convert doc_urls dict to list for storage
            doc_url_list = list(doc_urls.values()) if doc_urls else []
            update_job(
                job_id,
                partial_artifacts={
                    "drive_folder_url": folder_url,
                    "doc_urls": doc_url_list,
                },
            )
            
            logger.info(f"[{job_id}] Created Drive folder: {folder_url}")
        except Exception as e:
            logger.warning(f"[{job_id}] Drive upload failed: {e}")
            warnings.append(f"Drive upload failed: {str(e)}")
            # Job still completes, just without Drive folder
        
        # Stage 10: Completion
        logger.info(f"[{job_id}] Stage 10: Completing job")
        update_job(
            job_id,
            status="completed",
            stage="completed",
            progress_percent=100,
            partial_outputs=outputs,
            warnings_append=warnings,
        )
        
        # Post completion message to Slack
        if folder_url:
            completion_message = (
                f"✅ Research job `{job_id}` completed!\n\n"
                f"📁 Drive folder: {folder_url}\n"
                f"📊 Claims extracted: {len(claims)}\n"
                f"📚 Sources: {len(web_sources)} web, {len(youtube_videos)} YouTube videos"
            )
            if warnings:
                completion_message += f"\n⚠️ {len(warnings)} warnings (see job details)"
        else:
            completion_message = (
                f"✅ Research job `{job_id}` completed!\n\n"
                f"⚠️ Drive upload failed, but results are available via API\n"
                f"📊 Claims extracted: {len(claims)}\n"
                f"📚 Sources: {len(web_sources)} web, {len(youtube_videos)} YouTube videos"
            )
        
        _post_slack_message(slack_payload, completion_message)
        
        result = {
            "job_id": job_id,
            "status": "completed",
            "folder_url": folder_url,
            "doc_urls": doc_urls,
            "claims_count": len(claims),
            "sources_count": len(web_sources),
            "youtube_videos_count": len(youtube_videos),
            "warnings_count": len(warnings),
        }
        
        logger.info(f"Research job {job_id} completed successfully")
        return result
        
    except Exception as e:
        logger.exception(f"Fatal error in research job {job_id}: {e}")

        # Log error to database for admin tracking
        job = get_job(job_id)
        user_id = None
        user_email = None
        current_stage = "unknown"
        if job:
            user_id = job.user_id
            user_email = job.config_json.get("user_email")
            current_stage = job.stage or "unknown"

        log_exception(
            exception=e,
            job_id=job_id,
            user_id=user_id,
            user_email=user_email,
            stage=current_stage,
        )

        # Update job status to failed
        update_job(
            job_id,
            status="failed",
            stage="error",
            progress_percent=0,
            warnings_append=warnings + [f"Fatal error: {str(e)}"],
        )

        # Post error message to Slack
        _post_slack_message(
            slack_payload,
            f"❌ Research job `{job_id}` failed: {str(e)}",
        )

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


def _generate_master_index(job_config: JobConfig, outputs: dict) -> str:
    """
    Generate master index document markdown.
    
    Args:
        job_config: Job configuration
        outputs: Dictionary of output markdown strings
        
    Returns:
        Master index markdown string
    """
    lines = [
        "# Master Index",
        "",
        f"**Topic:** {job_config.topic}",
        f"**Mode:** {job_config.mode.value}",
        "",
        "## Documents",
        "",
        "- [01 Research Map](#01-research-map)",
        "- [02 Source Shortlist](#02-source-shortlist)",
        "- [03 YouTube Index](#03-youtube-index)",
        "- [04 Transcripts](#04-transcripts)",
        "- [05 Web Extracts](#05-web-extracts)",
        "- [06 Quote Bank](#06-quote-bank)",
        "- [07 Claims Ledger](#07-claims-ledger)",
        "- [08 Evidence Table](#08-evidence-table)",
        "- [09 Missing Angles](#09-missing-angles)",
        "",
    ]
    return "\n".join(lines)


def _generate_transcripts_md(transcripts: list) -> str:
    """
    Generate transcripts markdown document.
    
    Args:
        transcripts: List of TranscriptItem objects
        
    Returns:
        Transcripts markdown string
    """
    if not transcripts:
        return "# Transcripts\n\n*No transcripts available.*"
    
    lines = ["# Transcripts", ""]
    for transcript in transcripts:
        lines.append(f"## {transcript.video_id}")
        lines.append(f"**URL:** {transcript.video_url}")
        lines.append(f"**Status:** {transcript.status.value}")
        if transcript.text:
            lines.append(f"\n{transcript.text}\n")
        else:
            lines.append(f"*{transcript.error_message or 'Transcript not available'}*\n")
        lines.append("---\n")
    
    return "\n".join(lines)


def _generate_web_extracts_md(web_sources: list) -> str:
    """
    Generate web extracts markdown document.

    Args:
        web_sources: List of SourceItem objects with captured content

    Returns:
        Web extracts markdown string
    """
    if not web_sources:
        return "# Web Extracts\n\n*No web sources available.*"

    lines = ["# Web Extracts", ""]
    for source in web_sources:
        lines.append(f"## {source.title}")
        lines.append(f"**URL:** {source.url}")
        lines.append(f"**Type:** {source.source_type.value}")
        if source.published_at:
            lines.append(f"**Published:** {source.published_at}")
        if source.text:
            lines.append(f"\n{source.text[:2000]}...")  # Limit extract length
        else:
            lines.append("*Content not available*")
        if source.notes:
            lines.append(f"\n*Note: {source.notes}*")
        lines.append("\n---\n")

    return "\n".join(lines)


def _generate_evidence_table_md(evidence_records: list) -> str:
    """
    Generate evidence table markdown document.

    Args:
        evidence_records: List of EvidenceRecord objects

    Returns:
        Evidence table markdown string
    """
    if not evidence_records:
        return "# Evidence Table\n\n*No evidence records available.*"

    lines = [
        "# Evidence Table",
        "",
        "| Claim ID | Status | Evidence For | Evidence Against | Notes |",
        "|----------|--------|--------------|------------------|-------|",
    ]

    for record in evidence_records:
        claim_id = record.claim_id if hasattr(record, 'claim_id') else str(record.get('claim_id', 'N/A'))
        status = record.status.value if hasattr(record, 'status') else str(record.get('status', 'Unproven'))

        # Format evidence for
        evidence_for = []
        for_list = record.evidence_for if hasattr(record, 'evidence_for') else record.get('evidence_for', [])
        for citation in for_list:
            url = citation.url if hasattr(citation, 'url') else citation.get('url', '')
            if url:
                evidence_for.append(f"[Link]({url})")
        evidence_for_str = ", ".join(evidence_for) if evidence_for else "-"

        # Format evidence against
        evidence_against = []
        against_list = record.evidence_against if hasattr(record, 'evidence_against') else record.get('evidence_against', [])
        for citation in against_list:
            url = citation.url if hasattr(citation, 'url') else citation.get('url', '')
            if url:
                evidence_against.append(f"[Link]({url})")
        evidence_against_str = ", ".join(evidence_against) if evidence_against else "-"

        # Format notes (truncate and escape pipes)
        notes = record.notes if hasattr(record, 'notes') else record.get('notes', '')
        notes_str = (notes or "-")[:100].replace("|", "\\|").replace("\n", " ")

        lines.append(f"| {claim_id} | {status} | {evidence_for_str} | {evidence_against_str} | {notes_str} |")

    lines.append("")
    lines.append(f"**Total claims validated:** {len(evidence_records)}")

    # Summary statistics
    verified = sum(1 for r in evidence_records if (r.status.value if hasattr(r, 'status') else r.get('status', '')) == 'Verified')
    debunked = sum(1 for r in evidence_records if (r.status.value if hasattr(r, 'status') else r.get('status', '')) == 'Debunked')
    unproven = sum(1 for r in evidence_records if (r.status.value if hasattr(r, 'status') else r.get('status', '')) == 'Unproven')

    lines.append(f"- Verified: {verified}")
    lines.append(f"- Debunked: {debunked}")
    lines.append(f"- Unproven: {unproven}")

    return "\n".join(lines)


# =============================================================================
# Transcript Extraction Task
# =============================================================================

@celery_app.task(name="backend.worker.run_transcript_job")
def run_transcript_job(job_id: str) -> dict:
    """
    Celery task for async transcript extraction.

    Processes large batches of YouTube videos (>5) in the background.
    Updates job progress as each video is processed.

    Args:
        job_id: Unique identifier for the transcript job

    Returns:
        Dict with job_id, status, and doc_url
    """
    from datetime import datetime
    from backend.services.transcript_service import (
        extract_single_transcript,
        format_transcripts_for_doc,
    )
    from backend.integrations.google_drive_docs import create_transcript_doc
    from backend.models.job_record import Artifacts

    logger.info(f"[{job_id}] Starting transcript extraction job")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    video_urls = job.config_json.get("video_urls", [])
    use_whisper = job.config_json.get("use_whisper_fallback", True)
    doc_title = job.config_json.get("doc_title")
    preferred_languages = job.config_json.get("preferred_languages", ["en"])

    total = len(video_urls)
    logger.info(f"[{job_id}] Processing {total} videos")

    # Update status to running
    update_job(job_id, status="running", stage="extracting_transcripts", progress_percent=5)

    transcripts = []
    warnings = []

    # Process each video
    for i, url in enumerate(video_urls):
        # Update progress (5% start, 85% for extraction, 10% for doc generation)
        progress = 5 + int(((i + 1) / total) * 80)

        try:
            result = extract_single_transcript(
                url,
                use_whisper=use_whisper,
                preferred_languages=preferred_languages,
            )
            transcripts.append(result)

            if result.status != "available":
                warnings.append(f"Transcript unavailable for {url}: {result.error_message}")

            logger.info(f"[{job_id}] Processed {i + 1}/{total}: {result.status}")

        except Exception as e:
            logger.error(f"[{job_id}] Error processing {url}: {e}")
            warnings.append(f"Error processing {url}: {str(e)}")
            from backend.models.transcript_job import TranscriptResultItem
            from backend.integrations.transcripts import _extract_video_id
            transcripts.append(TranscriptResultItem(
                video_id=_extract_video_id(url) or "",
                video_url=url,
                status="error",
                source="failed",
                error_message=str(e),
            ))

        # Update job progress
        update_job(
            job_id,
            progress_percent=progress,
            config_json={**job.config_json, "transcripts_completed": i + 1},
        )

    # Stage: Generate Google Doc
    logger.info(f"[{job_id}] Generating Google Doc")
    update_job(job_id, stage="generating_document", progress_percent=90)

    try:
        if not doc_title:
            doc_title = f"YouTube Transcripts - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        content = format_transcripts_for_doc(transcripts)

        # Get user info from job for Drive sharing
        user_email = None
        user_id_for_drive = None
        if job and job.config_json:
            user_email = job.config_json.get("user_email")
            user_id_for_drive = job.config_json.get("user_id")

        drive_result = create_transcript_doc(
            doc_title,
            content,
            user_email=user_email,
            user_id=user_id_for_drive,
        )

        # Update job with success
        artifacts = Artifacts(
            drive_folder_url=drive_result["folder_url"],
            doc_urls=[drive_result["doc_url"]],
        )

        update_job(
            job_id,
            status="completed",
            progress_percent=100,
            stage="completed",
            artifacts=artifacts,
            warnings=warnings,
        )

        logger.info(f"[{job_id}] Transcript job completed: {drive_result['doc_url']}")

        return {
            "job_id": job_id,
            "status": "completed",
            "doc_url": drive_result["doc_url"],
            "folder_url": drive_result["folder_url"],
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Failed to create Google Doc: {e}")
        warnings.append(f"Failed to create Google Doc: {str(e)}")

        update_job(
            job_id,
            status="failed",
            warnings=warnings,
        )

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }
