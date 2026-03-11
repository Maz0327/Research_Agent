"""
Run mode: refine

Re-analyze existing sources from a new angle/perspective, producing:
- Doc 0: Unchanged (inherits from parent)
- Doc 1 append section (new analysis perspective)
- Doc 2 append section (new narrative section)

Key behaviors:
- NO new sources are added — same corpus as parent
- Doc 1/2 are APPEND-ONLY (new perspective section, originals untouched)
- User prompt drives the angle: counterarguments, economic lens, weaknesses, etc.
- user_prompt is REQUIRED for REFINE runs

Use cases:
- "What are the counterarguments to the main findings?"
- "Analyze from an economic perspective"
- "What are the weaknesses in the evidence?"
- "Summarize for a technical audience"
"""

from typing import Any, Optional

from loguru import logger

from backend.models.run_models import Run, RunOutputs
from backend.pipeline.runs.modes.base import RunModeExecutor
from backend.pipeline.runs.storage import load_run_document, get_merged_doc_0


def run_refine(
    job_id: str,
    run: Run,
    user_id: str,
    artifacts_dict: dict[str, Any],
) -> tuple[RunOutputs, dict[str, Any]]:
    """
    Execute REFINE run type.

    This mode:
    1. Loads parent run's Doc 0 (all sources + extractions)
    2. Loads parent Doc 1 (existing analysis)
    3. Calls LLM with existing corpus + new perspective prompt
    4. Produces Doc 1/2 append sections (new analysis, not replacement)

    CRITICAL: Doc 1/2 are APPEND sections, NOT full regenerations.
    The existing analysis is never modified — only new perspective added.

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

    if not request.user_prompt:
        raise ValueError("REFINE runs require a user_prompt describing the analysis angle")

    executor.update_progress(5, "Loading parent documents")

    # Get parent run documents
    parent_run_id = run.parent_run_id
    if not parent_run_id:
        raise ValueError("refine requires a parent run")

    # Load parent Doc 0 (need the full merged version for all extractions)
    parent_doc_0_path = f"jobs/{job_id}/runs/{parent_run_id}/doc_0.json"
    parent_doc_0 = load_run_document(parent_doc_0_path)

    if not parent_doc_0:
        parent_doc_0_path = artifacts_dict.get("doc_0_path")
        if parent_doc_0_path:
            parent_doc_0 = load_run_document(parent_doc_0_path)

    if not parent_doc_0:
        raise ValueError("Could not load parent Doc 0")

    # Load parent Doc 1 for context
    parent_doc_1_path = f"jobs/{job_id}/runs/{parent_run_id}/doc_1.json"
    parent_doc_1 = load_run_document(parent_doc_1_path)
    if not parent_doc_1:
        parent_doc_1_path = artifacts_dict.get("doc_1_path")
        if parent_doc_1_path:
            parent_doc_1 = load_run_document(parent_doc_1_path)

    # Load parent Doc 2 for context
    parent_doc_2_path = f"jobs/{job_id}/runs/{parent_run_id}/doc_2.json"
    parent_doc_2 = load_run_document(parent_doc_2_path)
    if not parent_doc_2:
        parent_doc_2_path = artifacts_dict.get("doc_2_path")
        if parent_doc_2_path:
            parent_doc_2 = load_run_document(parent_doc_2_path)

    logger.info(
        f"[{job_id}] Refining with {len(parent_doc_0.get('sources', []))} sources, "
        f"perspective: {request.user_prompt[:50]}..."
    )

    executor.update_progress(20, "Analyzing existing corpus from new perspective")

    # Get all extractions from parent
    extractions = parent_doc_0.get("semantic_extractions", [])

    # Collect all key points and claims
    all_key_points = []
    all_claims = []
    for ext in extractions:
        all_key_points.extend(ext.get("key_points", []))
        all_claims.extend(ext.get("claims", []))

    executor.update_progress(40, "Synthesizing new perspective")

    # Synthesize new perspective
    doc_1_section, doc_2_section = _synthesize_refine_sections(
        job_id=job_id,
        run=run,
        key_points=all_key_points,
        claims=all_claims,
        parent_doc_1=parent_doc_1 or {},
        user_prompt=request.user_prompt,
        executor=executor,
    )

    executor.update_progress(90, "Storing run outputs")

    # Store outputs — Doc 0 is NOT stored (inherited from parent)
    outputs = executor.store_outputs(
        doc_0=None,
        doc_1=doc_1_section,
        doc_2=doc_2_section,
        is_doc_0_delta=False,
        parent_doc_0_path=parent_doc_0_path,
    )

    # Set Doc 0 path to parent's for reference
    outputs.doc_0_path = parent_doc_0_path

    # Set append metadata
    outputs.doc_1_is_append = True
    outputs.doc_2_is_append = True
    outputs.doc_1_parent_path = parent_doc_1_path
    outputs.doc_2_parent_path = parent_doc_2_path

    metrics = executor.get_metrics()

    logger.info(f"[{job_id}] Run {run.run_id} (refine) complete: perspective='{request.user_prompt[:40]}...'")

    return outputs, metrics.model_dump()


def _synthesize_refine_sections(
    job_id: str,
    run: Run,
    key_points: list[dict],
    claims: list[dict],
    parent_doc_1: dict[str, Any],
    user_prompt: str,
    executor: RunModeExecutor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Re-analyze existing corpus from a new perspective.

    Produces append-only sections for Doc 1/2.
    Does NOT repeat or modify existing analysis.
    """
    from backend.integrations.gemini_client import GeminiClient

    gemini = GeminiClient()

    # Get existing analysis for context
    existing_themes = parent_doc_1.get("themes", parent_doc_1.get("directions", []))
    existing_gaps = parent_doc_1.get("gaps", parent_doc_1.get("research_gaps", []))

    prompt = f"""You are re-analyzing an existing research corpus from a NEW PERSPECTIVE.

## USER'S REQUESTED PERSPECTIVE
{user_prompt}

## EXISTING ANALYSIS (READ-ONLY — do NOT repeat any of this)

Existing themes: {_format_list(existing_themes, 5)}
Existing gaps: {_format_list(existing_gaps, 5)}

## SOURCE CORPUS (same sources, analyze from new angle)

Key Points ({len(key_points)} total):
{_format_key_points(key_points[:20])}

Claims ({len(claims)} total):
{_format_claims(claims[:15])}

## YOUR TASK

Analyze the SAME source material from the perspective: "{user_prompt}"

Produce ONLY NEW insights that come from looking at the data through this lens.
Do NOT repeat anything from the existing analysis.

Return JSON:
{{
  "perspective_label": "2-4 word label for this perspective",
  "new_insights": [
    {{"insight_id": "INS_1", "statement": "...", "supporting_evidence": ["KP_..."], "confidence": "HIGH|MEDIUM|LOW"}}
  ],
  "new_themes": [
    {{"theme_id": "THEME_refine_1", "label": "...", "description": "...", "related_key_points": ["KP_..."]}}
  ],
  "reframed_findings": [
    {{"original_finding": "existing KP or theme reference", "reframing": "how this looks from new perspective"}}
  ],
  "new_tensions": [
    {{"tension_id": "TEN_refine_1", "label": "...", "description": "...", "involved_points": ["KP_..."]}}
  ],
  "new_gaps": [
    {{"description": "gaps visible only from this perspective"}}
  ],
  "summary": "2-3 sentences on what this perspective reveals"
}}

CRITICAL RULES:
- Produce NEW observations, not repetitions of existing analysis
- Every insight must trace to key points from the source corpus
- This is a DIFFERENT LENS on the SAME data — not new data
- If the perspective reveals contradictions, flag them but don't resolve
"""

    executor.update_progress(60, "Running LLM analysis")

    try:
        response = gemini.generate_json(
            prompt=prompt,
            system_message="You re-analyze research findings from alternative perspectives, producing new insights without repeating existing analysis.",
        )
        executor.metrics.record_llm_call(tokens_in=3500, tokens_out=2000, cost=0.06)

        data = response.get("data", {})

        perspective_label = data.get("perspective_label", user_prompt[:30])

        # Build Doc 1 append section
        doc_1_section = {
            "section_type": "refinement",
            "run_id": run.run_id,
            "run_type": "refine",
            "user_prompt": user_prompt,
            "perspective_label": perspective_label,
            "new_insights": data.get("new_insights", []),
            "new_themes": data.get("new_themes", []),
            "reframed_findings": data.get("reframed_findings", []),
            "new_tensions": data.get("new_tensions", []),
            "new_gaps": data.get("new_gaps", []),
            "summary": data.get("summary", ""),
        }

        # Build Doc 2 append section
        summary = data.get("summary", "Research was re-analyzed from a new perspective.")
        insight_count = len(data.get("new_insights", []))
        new_theme_labels = [t.get("label", "") for t in data.get("new_themes", [])]

        doc_2_section = {
            "section_type": "refinement",
            "run_id": run.run_id,
            "run_type": "refine",
            "heading": f"## Refinement: {perspective_label} (Run {run.run_id})",
            "narrative": summary,
            "perspective": user_prompt,
            "insight_count": insight_count,
            "themes_added": new_theme_labels,
            "key_insights": [
                ins.get("statement", "")
                for ins in data.get("new_insights", [])[:5]
            ],
        }

        executor.metrics.record_extraction(
            themes=len(data.get("new_themes", [])),
        )

        return doc_1_section, doc_2_section

    except Exception as e:
        logger.error(f"[{job_id}] Refine synthesis failed: {e}")
        return (
            {
                "section_type": "refinement",
                "run_id": run.run_id,
                "run_type": "refine",
                "user_prompt": user_prompt,
                "new_insights": [],
                "new_themes": [],
                "summary": "",
                "error": str(e),
            },
            {
                "section_type": "refinement",
                "run_id": run.run_id,
                "run_type": "refine",
                "heading": f"## Refinement (Run {run.run_id})",
                "narrative": "Refinement analysis failed.",
                "error": str(e),
            },
        )


def _format_key_points(key_points: list[dict]) -> str:
    """Format key points for prompt."""
    lines = []
    for kp in key_points:
        kp_id = kp.get("key_point_id", "")
        statement = kp.get("statement", "")
        conf = kp.get("confidence", "MEDIUM")
        sources = ", ".join(kp.get("source_ids", []))
        lines.append(f"- [{kp_id}] [{conf}] {statement} (sources: {sources})")
    return "\n".join(lines) if lines else "(none)"


def _format_claims(claims: list[dict]) -> str:
    """Format claims for prompt."""
    lines = []
    for cl in claims:
        conf = cl.get("confidence", "MEDIUM")
        lines.append(f"- [{conf}] {cl.get('statement', '')}")
    return "\n".join(lines) if lines else "(none)"


def _format_list(items: list, max_items: int = 5) -> str:
    """Format a list of items (themes, gaps, etc.) for context."""
    lines = []
    for item in items[:max_items]:
        if isinstance(item, dict):
            label = item.get("label", item.get("description", item.get("theme", "")))
            lines.append(f"- {label}")
        elif isinstance(item, str):
            lines.append(f"- {item}")
    return "\n".join(lines) if lines else "(none)"
