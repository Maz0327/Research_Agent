"""Pipeline initialization and completion stages."""
from typing import Optional
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import get_job, update_job
from backend.models.job_record import Artifacts
from backend.integrations.supabase_storage import get_storage_client
from .helpers import post_slack_message


def stage_0_initialize(ctx: PipelineContext) -> None:
    """Initialize job and send start notification."""
    update_job(
        ctx.job_id,
        status="running",
        stage="initializing",
        progress_percent=0,
    )
    post_slack_message(ctx, f"Started research job: `{ctx.job_id}`\nTopic: {ctx.topic}")


def _try_upload_documents_to_storage(ctx: PipelineContext) -> Optional[dict]:
    """Try to upload documents to Supabase Storage.

    Returns:
        Dict with doc paths if successful, None if storage unavailable or failed.
    """
    storage_client = get_storage_client()
    if not storage_client:
        logger.info(f"[{ctx.job_id}] Storage not configured, using inline documents")
        return None

    paths = {}
    try:
        # Doc 0: Source Ledger
        if ctx.outputs.get("source_ledger"):
            doc_data = {
                "data": ctx.outputs["source_ledger"],
                "markdown": ctx.outputs.get("source_ledger_md"),
            }
            paths["doc_0_path"] = storage_client.upload_document(ctx.job_id, "doc_0", doc_data)

        # Doc 1: Jump-Start Directions
        if ctx.outputs.get("jump_start"):
            doc_data = {
                "data": ctx.outputs["jump_start"],
                "markdown": ctx.outputs.get("jump_start_md"),
            }
            paths["doc_1_path"] = storage_client.upload_document(ctx.job_id, "doc_1", doc_data)

        # Doc 2: Semantic Brief
        if ctx.outputs.get("semantic_brief"):
            doc_data = {
                "data": ctx.outputs["semantic_brief"],
                "markdown": ctx.outputs.get("semantic_brief_md"),
            }
            paths["doc_2_path"] = storage_client.upload_document(ctx.job_id, "doc_2", doc_data)

        # Doc 3: Producer Packet (if present)
        if ctx.outputs.get("producer_packet"):
            doc_data = {
                "data": ctx.outputs["producer_packet"],
                "markdown": ctx.outputs.get("producer_packet_md"),
            }
            paths["doc_3_path"] = storage_client.upload_document(ctx.job_id, "doc_3", doc_data)

        logger.info(f"[{ctx.job_id}] Uploaded {len(paths)} documents to storage")
        return paths

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Storage upload failed, falling back to inline: {e}")
        return None


def _build_inline_artifacts(ctx: PipelineContext) -> dict:
    """Build artifacts dict with inline document data (fallback/legacy)."""
    artifacts_dict = {}

    # Doc 0: Source Ledger
    if ctx.outputs.get("source_ledger"):
        artifacts_dict["source_ledger"] = {
            "data": ctx.outputs["source_ledger"],
            "markdown": ctx.outputs.get("source_ledger_md"),
        }

    # Doc 1: Jump-Start Directions
    if ctx.outputs.get("jump_start"):
        artifacts_dict["jump_start"] = {
            "data": ctx.outputs["jump_start"],
            "markdown": ctx.outputs.get("jump_start_md"),
        }

    # Doc 2: Semantic Brief
    if ctx.outputs.get("semantic_brief"):
        artifacts_dict["semantic_brief"] = {
            "data": ctx.outputs["semantic_brief"],
            "markdown": ctx.outputs.get("semantic_brief_md"),
        }

    # Include booster output if present
    if ctx.outputs.get("booster_output"):
        artifacts_dict["booster_output"] = ctx.outputs["booster_output"]
        artifacts_dict["booster_expansion_md"] = ctx.outputs.get("booster_expansion_md")

    # Include producer packet if present
    if ctx.outputs.get("producer_packet"):
        artifacts_dict["producer_packet"] = ctx.outputs["producer_packet"]
        artifacts_dict["producer_packet_md"] = ctx.outputs.get("producer_packet_md")

    return artifacts_dict


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

    # Try to upload documents to Supabase Storage (for lazy loading)
    storage_paths = _try_upload_documents_to_storage(ctx)

    if storage_paths:
        # New jobs: Prefer storage paths, but include small inline stubs so UI can render
        artifacts_dict = dict(storage_paths)

        # Build diagnostic stub markdown including warnings to aid troubleshooting
        warning_lines = []
        if ctx.warnings:
            top = ctx.warnings[:10]
            warning_lines = [f"- {w}" for w in top]
        stub_md_parts = [
            "# Document Available via Cloud Storage",
            "",
            "This document is stored in Supabase Storage and will be fetched on demand.",
            "",
            f"- Job ID: {ctx.job_id}",
            f"- Topic: {ctx.topic}",
            "- Storage: path present (inline JSON omitted to reduce payload)",
        ]
        if warning_lines:
            stub_md_parts.extend(["", "## Warnings (top)", *warning_lines])
        inline_stub_md = "\n".join(stub_md_parts)

        # For each stored document, add a minimal inline stub to ensure frontend can display
        if ctx.outputs.get("source_ledger") or storage_paths.get("doc_0_path"):
            artifacts_dict["source_ledger"] = {"data": {}, "markdown": inline_stub_md}
        if ctx.outputs.get("jump_start") or storage_paths.get("doc_1_path"):
            artifacts_dict["jump_start"] = {"data": {}, "markdown": inline_stub_md}
        if ctx.outputs.get("semantic_brief") or storage_paths.get("doc_2_path"):
            artifacts_dict["semantic_brief"] = {"data": {}, "markdown": inline_stub_md}

        # Still include booster/producer outputs in artifacts (small payload)
        if ctx.outputs.get("booster_output"):
            artifacts_dict["booster_output"] = ctx.outputs["booster_output"]
            artifacts_dict["booster_expansion_md"] = ctx.outputs.get("booster_expansion_md")
    else:
        # Fallback: Store inline data (existing behavior)
        artifacts_dict = _build_inline_artifacts(ctx)

    # Create Artifacts model (only include non-None values)
    artifacts = Artifacts(**{k: v for k, v in artifacts_dict.items() if v is not None})

    update_job(
        ctx.job_id,
        status="completed",
        stage="completed",
        progress_percent=100,
        partial_outputs=final_outputs,
        artifacts=artifacts,
        warnings_append=ctx.warnings,
    )

    # Build completion message
    if ctx.folder_url:
        message = (
            f"Research job `{ctx.job_id}` completed!\n\n"
            f"Drive folder: {ctx.folder_url}\n"
            f"Claims extracted: {len(ctx.claims)}\n"
            f"Sources: {len(ctx.web_sources)} web, {len(ctx.youtube_videos)} YouTube videos"
        )
        if ctx.warnings:
            message += f"\n{len(ctx.warnings)} warnings (see job details)"
    else:
        message = (
            f"Research job `{ctx.job_id}` completed!\n\n"
            f"Drive upload failed, but results are available via API\n"
            f"Claims extracted: {len(ctx.claims)}\n"
            f"Sources: {len(ctx.web_sources)} web, {len(ctx.youtube_videos)} YouTube videos"
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
