"""Claim, timeline, and entity extraction stages."""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import update_job
from .helpers import post_slack_message


def stage_7_extraction(ctx: PipelineContext) -> None:
    """Extract claims from transcripts and web sources."""
    from backend.pipeline.extraction import extract_claims

    logger.info(f"[{ctx.job_id}] Stage 7: Extracting claims")
    update_job(ctx.job_id, stage="claim_extraction", progress_percent=65)
    post_slack_message(ctx, "Extracting claims...")

    try:
        if ctx.transcripts or any(s.text for s in ctx.web_sources):
            ctx.claims, quote_bank_md, claims_ledger_md = extract_claims(ctx.transcripts, ctx.web_sources)
            # Heuristic fallback if LLM extraction produced too few claims
            if not ctx.claims or len(ctx.claims) < 3:
                try:
                    from backend.pipeline.extraction import _extract_claim_candidates
                    fallback_sentences = []
                    # Harvest sentences from transcripts (primary content source)
                    for transcript in (ctx.transcripts or []):
                        if getattr(transcript, 'text', None):
                            candidates = _extract_claim_candidates(transcript.text)
                            fallback_sentences.extend([c['text'] for c in candidates[:5]])
                    # Harvest sentences from captured web content
                    for src in (ctx.web_sources or []):
                        if getattr(src, 'text', None):
                            candidates = _extract_claim_candidates(src.text)
                            fallback_sentences.extend([c['text'] for c in candidates[:5]])
                    # Deduplicate and build minimal claims
                    unique = []
                    seen = set()
                    for sent in fallback_sentences:
                        key = sent.strip().lower()
                        if key not in seen:
                            seen.add(key)
                            unique.append(sent)
                    from backend.models.claim import Claim, ClaimType
                    import uuid as _uuid
                    # Create up to 10 heuristic claims (increased from 5)
                    heuristics = [
                        Claim(
                            claim_id=f"claim_{_uuid.uuid4().hex[:8]}",
                            canonical_claim=s,
                            verbatim_quote=s,
                            citations=[],
                            claim_type=ClaimType.FACTUAL,
                            entities=[],
                            confidence=0.4,
                        ) for s in unique[:10]
                    ]
                    if heuristics:
                        ctx.claims = (ctx.claims or []) + heuristics
                        quote_bank_md = (quote_bank_md or "# Quote Bank\n\n") + "\n".join(f"> {s}" for s in unique[:10])
                        claims_ledger_md = (claims_ledger_md or "# Claims Ledger\n\n") + "\n".join(f"- {s}" for s in unique[:10])
                        logger.info(f"[{ctx.job_id}] Added {len(heuristics)} heuristic claims as fallback")
                        ctx.add_warning(f"Used heuristic fallback: {len(heuristics)} claims (LLM extracted {len(ctx.claims) - len(heuristics)})")
                except Exception as fb_err:
                    logger.debug(f"[{ctx.job_id}] Heuristic fallback failed: {fb_err}")

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
