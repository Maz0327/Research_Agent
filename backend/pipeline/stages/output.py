"""Export generation stage.

Updated: 2026-01-19 - Drive upload completely removed.
Exports are generated and stored in ctx.outputs for Supabase upload
during stage_10_completion.

NOTE: stage_9_drive_upload is NO LONGER used. The function is
kept as a no-op for backward compatibility but does nothing.
"""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.pipeline.formats import ExportManager
from backend.state import update_job


def stage_9_drive_upload(ctx: PipelineContext) -> None:
    """DEPRECATED: Drive upload removed (2026-01-19).

    This function now only generates exports to ctx.outputs.
    No Drive upload occurs. Documents are stored in artifacts
    and exports go to Supabase Storage during stage_10_completion.
    """
    logger.info(f"[{ctx.job_id}] Generating exports (Drive upload disabled)")
    update_job(ctx.job_id, stage="generating_exports", progress_percent=85)

    # Generate exports 12-17 and store in ctx.outputs for Supabase upload
    try:
        generate_exports_to_context(ctx)
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Export generation failed: {e}")
        ctx.add_warning(f"Export generation failed: {str(e)}")


def generate_exports_to_context(ctx: PipelineContext) -> None:
    """Generate exports 12-17 and store in ctx.outputs.

    These will be uploaded to Supabase Storage in stage_10_completion.
    Stored as ctx.outputs["export_12_research_data"], etc.
    """
    export_manager = ExportManager()
    research_data = export_manager.gather_research_data(ctx)

    # Generate each export and store in ctx.outputs
    exports_generated = []

    try:
        ctx.outputs["export_12_research_data"] = export_manager.to_json(research_data)
        exports_generated.append("12_RESEARCH_DATA.json")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Failed to generate 12_RESEARCH_DATA: {e}")
        ctx.add_warning(f"Export 12_RESEARCH_DATA failed: {str(e)}")

    try:
        ctx.outputs["export_13_citations"] = export_manager.to_bibtex(research_data)
        exports_generated.append("13_CITATIONS.bib")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Failed to generate 13_CITATIONS: {e}")
        ctx.add_warning(f"Export 13_CITATIONS failed: {str(e)}")

    try:
        ctx.outputs["export_14_chapters"] = export_manager.to_chapters(research_data)
        exports_generated.append("14_CHAPTERS.json")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Failed to generate 14_CHAPTERS: {e}")
        ctx.add_warning(f"Export 14_CHAPTERS failed: {str(e)}")

    try:
        ctx.outputs["export_15_clips"] = export_manager.to_clips(research_data)
        exports_generated.append("15_CLIPS.json")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Failed to generate 15_CLIPS: {e}")
        ctx.add_warning(f"Export 15_CLIPS failed: {str(e)}")

    try:
        ctx.outputs["export_16_social_kit"] = export_manager.to_social(research_data)
        exports_generated.append("16_SOCIAL_KIT.json")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Failed to generate 16_SOCIAL_KIT: {e}")
        ctx.add_warning(f"Export 16_SOCIAL_KIT failed: {str(e)}")

    try:
        ctx.outputs["export_17_research_brief"] = export_manager.to_brief(research_data)
        exports_generated.append("17_RESEARCH_BRIEF.md")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Failed to generate 17_RESEARCH_BRIEF: {e}")
        ctx.add_warning(f"Export 17_RESEARCH_BRIEF failed: {str(e)}")

    if exports_generated:
        logger.info(f"[{ctx.job_id}] Generated {len(exports_generated)} exports: {exports_generated}")
