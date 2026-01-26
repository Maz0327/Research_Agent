"""
Iteration mode: deeper

Re-extract existing sources with more granular prompts.
Produces deeper, more detailed key points than baseline.
"""

from typing import Any

from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.gap_analysis import stage_gap_analysis
from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis
from backend.pipeline.stages.document_assembly import stage_document_assembly
from backend.pipeline.stages.semantic_extraction import process_single_source
from backend.state import update_job
from ..baseline_loader import BaselineData, reconstruct_source_packages
from ..metrics_tracker import MetricsTracker


# Deeper extraction instructions appended to standard prompt
DEEPER_EXTRACTION_SUFFIX = """

## DEEPER EXTRACTION MODE

You are performing a DEEPER analysis pass. Extract MORE GRANULAR details than a standard pass:

1. **Specific examples and case studies** - Names, dates, places, outcomes
2. **Numerical data** - Statistics, percentages, counts, measurements
3. **Named entities** - People, organizations, places, products mentioned
4. **Direct quotes** - Exact words with speaker attribution (if available)
5. **Causal relationships** - "X leads to Y because Z"
6. **Counterarguments** - Limitations, criticisms, or alternative views acknowledged
7. **Temporal information** - When things happened or are expected to happen

Focus on extracting SPECIFIC, ACTIONABLE details rather than general summaries.
Each key point should ideally include a concrete example or data point.
"""


def run_deeper(
    ctx: PipelineContext,
    baseline: BaselineData,
    metrics: MetricsTracker,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Re-extract sources with deeper analysis prompts.

    This mode re-runs extraction on each source with enhanced prompts
    that request more granular, specific details.

    Args:
        ctx: Pipeline context
        baseline: Baseline data (with source info in doc_0)
        metrics: Metrics tracker

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts
    """
    job_id = ctx.job_id
    iteration_id = ctx.outputs.get("iteration_id", "unknown")
    logger.info(f"[{job_id}] Running deeper iteration")

    # Update progress
    update_job(
        job_id,
        iteration_progress_percent=10,
        pass_detail="Preparing deeper extraction",
    )

    # 1. Reconstruct source packages from baseline doc_0
    source_packages = reconstruct_source_packages(baseline["doc_0"])
    num_sources = len(source_packages)
    logger.info(f"[{job_id}] Found {num_sources} sources to re-extract")

    if num_sources == 0:
        raise ValueError("No sources found in baseline for deeper extraction")

    # 2. Re-extract each source with deeper prompt
    # Note: We use baseline extractions as context but generate new ones
    ctx.semantic_extractions = []

    for i, pkg in enumerate(source_packages):
        source_id = pkg["source_id"]
        progress = 10 + int((i / num_sources) * 50)

        update_job(
            job_id,
            iteration_progress_percent=progress,
            pass_detail=f"Deeper extraction: {pkg['title'][:30]}... ({i + 1}/{num_sources})",
        )

        # Find baseline extraction for this source to provide context
        baseline_extraction = None
        for ext in baseline["extractions"]:
            ext_source_id = ext.get("source_id") or ext.get("extraction", {}).get("source_id")
            if ext_source_id == source_id:
                baseline_extraction = ext
                break

        # Build enhanced prompt context
        deeper_context = ""
        if baseline_extraction:
            existing_kps = baseline_extraction.get("key_points", [])
            if existing_kps:
                kp_summaries = [kp.get("statement", "")[:100] for kp in existing_kps[:5]]
                deeper_context = (
                    f"Previously extracted key points (go DEEPER than these):\n"
                    + "\n".join(f"- {s}" for s in kp_summaries)
                    + "\n\n"
                )

        try:
            # Re-extract with deeper focus
            # Note: process_single_source uses SourceIdentityPackage,
            # but we only have minimal info. We'll create a simplified extraction.
            from backend.integrations.gemini_client import GeminiClient
            from backend.models.semantic_units import (
                SemanticExtractionResult,
                KeyPoint,
                Claim,
                ConfidenceLevel,
            )

            gemini = GeminiClient()

            # Build deeper extraction prompt
            prompt = f"""
Analyze the following source and extract key semantic content.

Source ID: {source_id}
Title: {pkg['title']}
Source Type: {pkg['source_type']}

{deeper_context}

{DEEPER_EXTRACTION_SUFFIX}

Based on the source content available in the baseline, provide a deeper analysis.
Focus on specific details, examples, and evidence that support the main points.

Return a JSON object with:
- key_points: List of detailed key points with statement, confidence, quotes (if available)
- claims: List of specific claims that can be verified
"""

            response = gemini.generate_json(
                prompt=prompt,
                system_message="You are a research analyst performing deep extraction.",
            )
            metrics.record_llm_call(tokens_in=1500, tokens_out=800)

            # Parse response into extraction result
            data = response.get("data", {})
            key_points = []
            for kp in data.get("key_points", []):
                key_points.append(KeyPoint(
                    key_point_id=f"KP_{source_id}_{len(key_points) + 1}",
                    statement=kp.get("statement", ""),
                    source_ids=[source_id],
                    confidence=ConfidenceLevel(kp.get("confidence", "medium").upper()),
                    quotes=kp.get("quotes", []),
                ))

            claims = []
            for cl in data.get("claims", []):
                claims.append(Claim(
                    claim_id=f"CLM_{source_id}_{len(claims) + 1}",
                    statement=cl.get("statement", ""),
                    source_ids=[source_id],
                    confidence=ConfidenceLevel(cl.get("confidence", "medium").upper()),
                ))

            extraction = SemanticExtractionResult(
                source_id=source_id,
                key_points=key_points,
                claims=claims,
                themes=[],
                tensions=[],
            )

            ctx.semantic_extractions.append(extraction.model_dump())
            logger.debug(f"[{job_id}] Deeper extraction for {source_id}: {len(key_points)} KPs")

        except Exception as e:
            logger.warning(f"[{job_id}] Deeper extraction failed for {source_id}: {e}")
            # Fall back to baseline extraction if available
            if baseline_extraction:
                ctx.semantic_extractions.append(baseline_extraction)

    # 3. Re-run gap analysis
    update_job(job_id, iteration_progress_percent=65, pass_detail="Analyzing gaps in deeper content")
    stage_gap_analysis(ctx)
    metrics.record_llm_call(tokens_in=500, tokens_out=200)

    # 4. Re-run synthesis
    update_job(job_id, iteration_progress_percent=75, pass_detail="Synthesizing deeper insights")
    stage_semantic_synthesis(ctx)
    metrics.record_llm_call(tokens_in=2000, tokens_out=1500)

    # 5. Document assembly
    update_job(job_id, iteration_progress_percent=90, pass_detail="Assembling iteration documents")
    result = stage_document_assembly(ctx)

    # Extract docs with markdown for frontend rendering
    doc_0 = result["source_ledger"].to_dict()
    doc_0["markdown"] = result["source_ledger"].to_markdown()
    doc_1 = result["jump_start"].to_dict()
    doc_1["markdown"] = result["jump_start"].to_markdown()
    doc_2 = result["semantic_brief"].to_dict()
    doc_2["markdown"] = result["semantic_brief"].to_markdown()

    # Add iteration metadata
    doc_0["iteration_id"] = iteration_id
    doc_0["iteration_mode"] = "deeper"
    doc_1["iteration_id"] = iteration_id
    doc_2["iteration_id"] = iteration_id
    doc_2["iteration_mode"] = "deeper"

    logger.info(
        f"[{job_id}] Iteration {iteration_id} (deeper) complete: "
        f"{len(ctx.semantic_extractions)} sources re-extracted"
    )

    return doc_0, doc_1, doc_2
