"""
Run mode: regenerate

Re-run synthesis with ALL sources, producing:
- Doc 0: Unchanged (inherits from parent)
- Doc 1: FULL REWRITE (replaces all previous Doc 1 content)
- Doc 2: FULL REWRITE (replaces all previous Doc 2 content)

This is the "nuclear option" — uses the complete merged Doc 0
(all sources from baseline + all expand deltas) and produces
entirely new Doc 1/2 from scratch.

Use case: When user wants fresh synthesis without adding sources.
"""

from typing import Any, Optional

from loguru import logger

from backend.models.run_models import Run, RunOutputs, ensure_runs_migrated
from backend.pipeline.runs.modes.base import RunModeExecutor
from backend.pipeline.runs.storage import load_run_document, get_merged_doc_0


def run_regenerate(
    job_id: str,
    run: Run,
    user_id: str,
    artifacts_dict: dict[str, Any],
) -> tuple[RunOutputs, dict[str, Any]]:
    """
    Execute regenerate run type.

    This mode:
    1. Loads the MERGED Doc 0 (all sources from all runs in the chain)
    2. Re-runs synthesis with optional user guidance
    3. Generates entirely new Doc 1/2 (NOT append — full replacement)

    CRITICAL: Doc 1/2 from this run are full replacements, NOT append sections.
    All previous Doc 1/2 content (including append sections) is superseded.

    Args:
        job_id: Job ID
        run: Run object with request parameters
        user_id: User who triggered the run
        artifacts_dict: Current job artifacts

    Returns:
        Tuple of (RunOutputs, metrics_dict)
    """
    executor = RunModeExecutor(job_id, run, user_id)
    request = run.request

    executor.update_progress(5, "Loading all sources (merged Doc 0)")

    # Get parent run documents
    parent_run_id = run.parent_run_id
    if not parent_run_id:
        raise ValueError("regenerate requires a parent run")

    # Try to get the MERGED Doc 0 (includes all expand deltas)
    # First, try using get_merged_doc_0 on the parent run
    all_runs = ensure_runs_migrated(
        type("Obj", (), {"runs": artifacts_dict.get("runs", []),
                         "doc_0_path": artifacts_dict.get("doc_0_path"),
                         "doc_1_path": artifacts_dict.get("doc_1_path"),
                         "doc_2_path": artifacts_dict.get("doc_2_path"),
                         "iterations": artifacts_dict.get("iterations", [])})(),
        user_id=user_id,
    )

    # Find parent run
    parent_run = None
    for r in all_runs:
        if r.run_id == parent_run_id:
            parent_run = r
            break

    merged_doc_0 = None
    doc_0_path_ref = None

    if parent_run:
        # Use merged Doc 0 from parent (includes all deltas up to parent)
        merged_doc_0 = get_merged_doc_0(parent_run)
        if parent_run.outputs and parent_run.outputs.doc_0_path:
            doc_0_path_ref = parent_run.outputs.doc_0_path

    if not merged_doc_0:
        # Fallback: try direct path
        parent_doc_0_path = f"jobs/{job_id}/runs/{parent_run_id}/doc_0.json"
        merged_doc_0 = load_run_document(parent_doc_0_path)
        doc_0_path_ref = parent_doc_0_path

    if not merged_doc_0:
        # Try legacy path
        legacy_path = artifacts_dict.get("doc_0_path")
        if legacy_path:
            merged_doc_0 = load_run_document(legacy_path)
            doc_0_path_ref = legacy_path

    if not merged_doc_0:
        raise ValueError("Could not load Doc 0 for regeneration")

    logger.info(f"[{job_id}] Regenerating synthesis for {len(merged_doc_0.get('sources', []))} sources (merged)")

    executor.update_progress(20, "Preparing for synthesis")

    # Get all extractions from merged Doc 0
    extractions = merged_doc_0.get("semantic_extractions", [])

    # Collect all key points and claims across all sources
    all_key_points = []
    all_claims = []
    for ext in extractions:
        all_key_points.extend(ext.get("key_points", []))
        all_claims.extend(ext.get("claims", []))

    executor.update_progress(40, "Regenerating synthesis")

    # Regenerate with optional guidance
    doc_1, doc_2 = _regenerate_with_guidance(
        job_id=job_id,
        run=run,
        key_points=all_key_points,
        claims=all_claims,
        user_prompt=request.user_prompt,
        executor=executor,
    )

    executor.update_progress(90, "Storing run outputs")

    # Store outputs - Doc 0 is NOT stored (inherited from parent)
    # Doc 1/2 are FULL REPLACEMENTS (not append sections)
    outputs = executor.store_outputs(
        doc_0=None,  # Inherit merged Doc 0
        doc_1=doc_1,
        doc_2=doc_2,
        is_doc_0_delta=False,
        parent_doc_0_path=doc_0_path_ref,
    )

    # Set doc_0_path to parent's for reference
    outputs.doc_0_path = doc_0_path_ref

    # Explicitly mark as NOT append (full replacement)
    outputs.doc_1_is_append = False
    outputs.doc_2_is_append = False

    metrics = executor.get_metrics()

    logger.info(f"[{job_id}] Run {run.run_id} (regenerate) complete")

    return outputs, metrics.model_dump()


def _regenerate_with_guidance(
    job_id: str,
    run: Run,
    key_points: list[dict],
    claims: list[dict],
    user_prompt: Optional[str],
    executor: RunModeExecutor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Regenerate synthesis with optional user guidance."""
    from backend.integrations.gemini_client import GeminiClient

    gemini = GeminiClient()

    # Build guidance section
    guidance = ""
    if user_prompt:
        guidance = f"""
USER GUIDANCE:
{user_prompt}

Consider this guidance when synthesizing themes and directions.
"""

    synthesis_prompt = f"""
Analyze the following research findings and synthesize key themes and directions.

{guidance}

Key Points ({len(key_points)} total):
{_format_items(key_points[:25], "statement")}

Claims ({len(claims)} total):
{_format_items(claims[:20], "statement")}

Provide a comprehensive synthesis including:
1. Main themes across sources (with supporting evidence)
2. Key tensions or contradictions found
3. Research gaps that need attention
4. Prioritized directions for further research
5. Quick-start recommendations
"""

    executor.update_progress(60, "Running LLM synthesis")

    try:
        response = gemini.generate_json(
            prompt=synthesis_prompt,
            system_message="Synthesize research findings into actionable insights.",
        )
        executor.metrics.record_llm_call(tokens_in=3500, tokens_out=2000, cost=0.06)

        data = response.get("data", {})

        # Build Doc 1 (Jump-Start Directions)
        doc_1 = {
            "run_id": run.run_id,
            "run_type": "regenerate",
            "directions": data.get("directions", []),
            "research_gaps": data.get("gaps", []),
            "quick_start_priorities": data.get("priorities", data.get("quick_start", [])),
            "key_point_count": len(key_points),
            "claim_count": len(claims),
            "user_guidance_applied": bool(user_prompt),
        }

        # Build Doc 2 (Semantic Brief)
        doc_2 = {
            "run_id": run.run_id,
            "run_type": "regenerate",
            "themes": data.get("themes", []),
            "tensions": data.get("tensions", []),
            "key_points_summary": key_points[:25],
            "claims_summary": claims[:20],
            "gaps": data.get("gaps", []),
            "confidence_summary": _compute_confidence_summary(key_points),
            "synthesis_notes": data.get("notes", ""),
        }

        executor.metrics.record_extraction(
            themes=len(doc_2.get("themes", [])),
        )

        return doc_1, doc_2

    except Exception as e:
        logger.error(f"[{job_id}] Regenerate synthesis failed: {e}")
        return (
            {"run_id": run.run_id, "directions": [], "error": str(e)},
            {"run_id": run.run_id, "themes": [], "error": str(e)},
        )


def _format_items(items: list[dict], key: str) -> str:
    """Format items for prompt."""
    lines = []
    for item in items:
        conf = item.get("confidence", "MEDIUM")
        text = item.get(key, "")
        lines.append(f"- [{conf}] {text}")
    return "\n".join(lines)


def _compute_confidence_summary(key_points: list[dict]) -> dict[str, int]:
    """Compute confidence distribution."""
    summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for kp in key_points:
        conf = str(kp.get("confidence", "MEDIUM")).upper()
        if conf in summary:
            summary[conf] += 1
    return summary
