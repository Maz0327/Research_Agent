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
