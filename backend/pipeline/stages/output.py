"""Drive upload and output generation stage."""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.pipeline.formats import ExportManager
from backend.state import get_job, update_job
from .helpers import post_slack_message


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
    post_slack_message(ctx, "Writing docs...")

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

        # Generate new format exports
        try:
            export_manager = ExportManager()
            research_data = export_manager.gather_research_data(ctx)

            # Add structured exports
            doc_contents["12_RESEARCH_DATA.json"] = export_manager.to_json(research_data)
            doc_contents["13_CITATIONS.bib"] = export_manager.to_bibtex(research_data)
            doc_contents["14_CHAPTERS.json"] = export_manager.to_chapters(research_data)
            doc_contents["15_CLIPS.json"] = export_manager.to_clips(research_data)
            doc_contents["16_SOCIAL_KIT.json"] = export_manager.to_social(research_data)
            doc_contents["17_RESEARCH_BRIEF.md"] = export_manager.to_brief(research_data)

            logger.info(f"[{ctx.job_id}] Generated 6 new export formats")
        except Exception as e:
            logger.warning(f"[{ctx.job_id}] Export generation failed: {e}")
            ctx.add_warning(f"Export generation failed: {str(e)}")

        # Generate folder name with optional interpretation prefix
        base_name = ctx.job_config.output.drive_folder_name or ctx.short_title or ctx.job_config.topic
        # Clean the name for folder use (replace spaces, limit length)
        clean_name = base_name.replace(" ", "_")[:50]

        if ctx.interpretation_index is not None:
            # Multiple interpretations: prefix with number
            folder_name = f"{ctx.interpretation_index}_{clean_name}"
        else:
            folder_name = clean_name

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
