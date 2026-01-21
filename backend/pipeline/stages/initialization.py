"""Pipeline initialization and completion stages.

Updated: 2026-01-19 - Removed Slack usage.
"""
from typing import Optional
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import get_job, update_job
from backend.models.job_record import Artifacts
from backend.integrations.supabase_storage import get_storage_client


def stage_0_initialize(ctx: PipelineContext) -> None:
    """Initialize job and send start notification."""
    update_job(
        ctx.job_id,
        status="running",
        stage="initializing",
        progress_percent=0,
    )
    logger.info(f"[{ctx.job_id}] Job initialized: {ctx.topic}")


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


def _try_upload_exports_to_storage(ctx: PipelineContext) -> dict:
    """Upload exports 12-17 to Supabase Storage.

    Reads exports from ctx.outputs (populated by stage_9_drive_upload)
    and uploads each to Supabase under research/{job_id}/attachments/.

    Returns:
        Dict mapping export name to {storage_path, signed_url, present}
        Returns empty dict if storage unavailable or no exports found.
    """
    storage_client = get_storage_client()
    if not storage_client:
        logger.info(f"[{ctx.job_id}] Storage not configured, skipping export upload")
        return {}

    # Map ctx.outputs keys to filenames
    export_mapping = {
        "export_12_research_data": "12_RESEARCH_DATA.json",
        "export_13_citations": "13_CITATIONS.bib",
        "export_14_chapters": "14_CHAPTERS.json",
        "export_15_clips": "15_CLIPS.json",
        "export_16_social_kit": "16_SOCIAL_KIT.json",
        "export_17_research_brief": "17_RESEARCH_BRIEF.md",
    }

    results = {}
    for ctx_key, filename in export_mapping.items():
        content = ctx.outputs.get(ctx_key)
        if not content:
            results[filename] = {"present": False, "storage_path": None, "signed_url": None}
            continue

        try:
            upload_result = storage_client.upload_attachment(
                job_id=ctx.job_id,
                filename=filename,
                content=content,
                expires_in=3600,  # 1 hour
            )
            results[filename] = {
                "present": True,
                "storage_path": upload_result["storage_path"],
                "signed_url": upload_result["signed_url"],
            }
            logger.debug(f"[{ctx.job_id}] Uploaded export {filename}")
        except Exception as e:
            logger.warning(f"[{ctx.job_id}] Failed to upload export {filename}: {e}")
            ctx.add_warning(f"Export upload failed for {filename}: {str(e)}")
            results[filename] = {"present": False, "storage_path": None, "signed_url": None}

    uploaded_count = sum(1 for r in results.values() if r["present"])
    if uploaded_count > 0:
        logger.info(f"[{ctx.job_id}] Uploaded {uploaded_count}/{len(export_mapping)} exports to storage")

    return results


def _build_artifact_manifest(
    ctx: PipelineContext,
    storage_paths: dict,
    export_results: dict,
) -> dict:
    """Build the artifact_manifest structure.

    Args:
        ctx: Pipeline context
        storage_paths: Doc 0-3 storage paths from _try_upload_documents_to_storage
        export_results: Export results from _try_upload_exports_to_storage

    Returns:
        artifact_manifest dict as specified in Option B storage strategy
    """
    # Determine analysis modes present
    analysis_modes = set()
    if ctx.outputs.get("source_ledger"):
        ledger_data = ctx.outputs["source_ledger"]
        if isinstance(ledger_data, dict):
            for entry in ledger_data.get("entries", []):
                if isinstance(entry, dict) and entry.get("analysis_mode"):
                    analysis_modes.add(entry["analysis_mode"])

    # Determine overall confidence ceiling (lowest of all sources)
    confidence_map = {"low": 1, "medium": 2, "high": 3}
    overall_confidence = "high"
    if ctx.outputs.get("source_ledger"):
        ledger_data = ctx.outputs["source_ledger"]
        if isinstance(ledger_data, dict):
            for entry in ledger_data.get("entries", []):
                if isinstance(entry, dict):
                    ceiling = entry.get("confidence_ceiling", "high")
                    if confidence_map.get(ceiling, 3) < confidence_map.get(overall_confidence, 3):
                        overall_confidence = ceiling

    # Build manifest (handle None storage_paths)
    storage_paths = storage_paths or {}
    manifest = {
        "core_docs": {
            "20": {
                "present": bool(ctx.outputs.get("source_ledger_md") or storage_paths.get("doc_0_path")),
                "title": "Source Ledger",
            },
            "21": {
                "present": bool(ctx.outputs.get("jump_start_md") or storage_paths.get("doc_1_path")),
                "title": "Jump Start",
            },
            "22": {
                "present": bool(ctx.outputs.get("semantic_brief_md") or storage_paths.get("doc_2_path")),
                "title": "Semantic Brief",
            },
        },
        "attachments": {
            "producer_packet": {
                "present": bool(ctx.outputs.get("producer_packet")),
            },
            "exports": [
                {
                    "name": filename,
                    "present": info.get("present", False),
                    "signed_url": info.get("signed_url"),
                    "storage_path": info.get("storage_path"),
                }
                for filename, info in export_results.items()
            ] if export_results else [],
            "pdf": {
                "present": False,  # PDF is generated on-demand
                "signed_url": None,
                "storage_path": None,
            },
        },
        "warnings": ctx.warnings[:20] if ctx.warnings else [],
        "analysis_summary": {
            "analysis_modes_present": list(analysis_modes),
            "confidence_ceiling": overall_confidence,
        },
    }

    return manifest


def stage_10_completion(ctx: PipelineContext) -> dict:
    """Mark job complete and build artifact manifest.

    Updated: 2026-01-19 - Now builds artifact_manifest with Option B storage strategy.
    Core docs (20-22) stored in artifacts, exports uploaded to Supabase Storage.
    """
    logger.info(f"[{ctx.job_id}] Stage 10: Completing job")

    # Get cost summary for final output
    cost_summary = ctx.get_cost_summary()

    # Add cost and quality gate stats to outputs
    final_outputs = dict(ctx.outputs)
    if cost_summary:
        final_outputs["cost_summary"] = cost_summary
    if ctx.quality_gate_stats:
        final_outputs["quality_gate_stats"] = ctx.quality_gate_stats

    # Try to upload documents (Doc 0-3) to Supabase Storage
    storage_paths = _try_upload_documents_to_storage(ctx)

    # Upload exports 12-17 to Supabase Storage
    export_results = _try_upload_exports_to_storage(ctx)

    # Build artifact manifest (STEP 3)
    artifact_manifest = _build_artifact_manifest(ctx, storage_paths, export_results)

    if storage_paths:
        # New jobs: Prefer storage paths, but include small inline stubs so UI can render
        artifacts_dict = dict(storage_paths)

        # Build diagnostic stub markdown
        warning_lines = [f"- {w}" for w in ctx.warnings[:10]] if ctx.warnings else []
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

    # Add artifact_manifest to artifacts
    artifacts_dict["artifact_manifest"] = artifact_manifest

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

    # --- Build doc_paths from artifacts_dict (already computed above) ---
    doc_paths = {}
    for k in ("doc_0", "doc_1", "doc_2", "doc_3"):
        path_key = f"{k}_path"
        if path_key in artifacts_dict:
            doc_paths[k] = artifacts_dict[path_key]

    # --- Counts (robust + schema-aligned) ---
    semantic_extractions = getattr(ctx, "semantic_extractions", None) or []
    source_identity_packages = getattr(ctx, "source_identity_packages", None) or []
    warnings = getattr(ctx, "warnings", None) or []

    claims_count = sum(len(getattr(e, "claims", []) or []) for e in semantic_extractions)
    sources_count = len(source_identity_packages)
    warnings_count = len(warnings)

    youtube_videos_count = sum(
        1 for p in source_identity_packages
        if (getattr(p, "source_type", None) == "youtube") or (getattr(p, "kind", None) == "youtube")
    )

    # --- Return payload ---
    result = {
        "job_id": str(ctx.job_id),
        "status": "completed",

        # Path prefix (NOT a URL)
        "folder_url": f"documents/{ctx.job_id}" if doc_paths else None,

        # Paths (NOT URLs)
        "doc_paths": doc_paths,

        # Backward compatibility: keep old key but make it paths too
        "doc_urls": doc_paths,

        # Backward-compat counters
        "claims_count": claims_count,
        "sources_count": sources_count,
        "youtube_videos_count": youtube_videos_count,
        "warnings_count": warnings_count,

        # Schema-aligned aliases
        "total_claims": claims_count,
        "total_sources": sources_count,
        "source_count": sources_count,
        "warning_count": warnings_count,
    }

    logger.info(f"Research job {ctx.job_id} completed successfully (cost: ${cost_summary.get('total_cost', 0):.4f})")
    return result
