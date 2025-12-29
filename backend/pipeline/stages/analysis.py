"""Validation, angle discovery, and documentary intelligence stages."""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import get_job, update_job


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
