"""
Run mode: expand

Add new sources to research, producing:
- Doc 0 delta (new sources only, merged on display)
- Doc 1 append section (new findings only, merged on display)
- Doc 2 append section (new narrative section, merged on display)

Key behaviors:
- Doc 0 is APPEND-ONLY (delta contains only new sources)
- Doc 1/2 are APPEND-ONLY (new section added, originals untouched)
- New sources are extracted in isolation (RASS source isolation)
- LLM synthesizes ONLY what the new sources add (not full regeneration)
- Supports both user-provided URLs and grounded auto-search
"""

from typing import Any, Optional

from loguru import logger

from backend.models.run_models import Run, RunOutputs, RunStatus
from backend.pipeline.runs.modes.base import RunModeExecutor
from backend.pipeline.runs.storage import load_run_document, get_merged_doc_0


def run_expand(
    job_id: str,
    run: Run,
    user_id: str,
    artifacts_dict: dict[str, Any],
) -> tuple[RunOutputs, dict[str, Any]]:
    """
    Execute EXPAND run type.

    This mode:
    1. Loads parent run's documents
    2. Gets new sources (user-provided URLs or grounded search)
    3. Extracts new sources in isolation
    4. Creates delta Doc 0 (new sources only)
    5. Creates append sections for Doc 1/2 (new findings only)

    CRITICAL: Doc 1/2 are APPEND sections, NOT full regenerations.
    The existing analysis is never modified — only added to.

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

    executor.update_progress(5, "Loading parent documents")

    # Get parent run documents
    parent_run_id = run.parent_run_id
    if not parent_run_id:
        raise ValueError("expand requires a parent run")

    # Load parent Doc 0 path
    parent_doc_0_path = f"jobs/{job_id}/runs/{parent_run_id}/doc_0.json"
    parent_doc_0 = load_run_document(parent_doc_0_path)

    if not parent_doc_0:
        # Try legacy path
        parent_doc_0_path = artifacts_dict.get("doc_0_path")
        if parent_doc_0_path:
            parent_doc_0 = load_run_document(parent_doc_0_path)

    if not parent_doc_0:
        raise ValueError("Could not load parent Doc 0")

    # Load parent Doc 1 for context (needed for append synthesis)
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

    # Get existing source URLs to avoid duplicates
    existing_urls = set()
    for source in parent_doc_0.get("sources", []):
        url = source.get("url") or source.get("source_url")
        if url:
            existing_urls.add(url)

    logger.info(f"[{job_id}] Parent has {len(existing_urls)} existing sources")

    executor.update_progress(10, "Searching for new sources")

    # Get new sources from request or search
    new_source_urls = request.new_source_urls or []
    max_new = request.max_new_sources or 4
    search_mode = request.search_mode or "manual"

    # If no URLs provided and search_mode is auto, run grounded search
    if not new_source_urls and search_mode == "auto":
        from backend.pipeline.runs.search import grounded_search

        search_results = grounded_search(
            doc_0=parent_doc_0,
            user_prompt=request.user_prompt or "",
            existing_urls=existing_urls,
            max_results=max_new,
            executor=executor,
        )

        # Check if we need user review (trust_mode=False is default)
        if not request.trust_mode and search_results:
            # Store candidates in request for user review
            run.request.search_candidates = [
                {
                    "url": r["url"],
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "relevance_score": r.get("relevance_score", 0.0),
                }
                for r in search_results
            ]
            # Return early — run will be in AWAITING_REVIEW status
            # The worker will detect this and set the status accordingly
            outputs = RunOutputs(
                doc_0_is_delta=True,
                doc_0_parent_path=parent_doc_0_path,
                doc_1_is_append=True,
                doc_2_is_append=True,
                doc_1_parent_path=parent_doc_1_path,
                doc_2_parent_path=parent_doc_2_path,
            )
            metrics = executor.get_metrics()
            # Signal awaiting review by returning special marker
            metrics_dict = metrics.model_dump()
            metrics_dict["_awaiting_review"] = True
            return outputs, metrics_dict

        new_source_urls = [r["url"] for r in search_results]

    elif not new_source_urls:
        # Fallback: search using basic topic search
        new_source_urls = _search_for_sources(
            job_id=job_id,
            parent_doc_0=parent_doc_0,
            existing_urls=existing_urls,
            max_sources=max_new,
            user_prompt=request.user_prompt,
            executor=executor,
        )

    # Filter out duplicates
    new_source_urls = [
        url for url in new_source_urls
        if url not in existing_urls
    ][:max_new]

    if not new_source_urls:
        logger.warning(f"[{job_id}] No new sources found")
        # Create empty delta
        new_source_ids = []
        doc_0_delta = _create_empty_delta(run.run_id)
    else:
        executor.update_progress(30, f"Processing {len(new_source_urls)} new sources")

        # Process new sources
        new_source_ids, doc_0_delta = _process_new_sources(
            job_id=job_id,
            run=run,
            source_urls=new_source_urls,
            executor=executor,
        )

    executor.update_progress(70, "Synthesizing new findings (append-only)")

    # Synthesize ONLY new findings → append sections for Doc 1/2
    doc_1_section, doc_2_section = _synthesize_append_sections(
        job_id=job_id,
        run=run,
        doc_0_delta=doc_0_delta,
        parent_doc_1=parent_doc_1 or {},
        parent_doc_2=parent_doc_2 or {},
        user_prompt=request.user_prompt,
        executor=executor,
    )

    executor.update_progress(90, "Storing run outputs")

    # Store outputs with append metadata
    outputs = executor.store_outputs(
        doc_0=doc_0_delta,
        doc_1=doc_1_section,
        doc_2=doc_2_section,
        is_doc_0_delta=True,
        parent_doc_0_path=parent_doc_0_path,
        new_source_ids=new_source_ids,
    )

    # Set append metadata
    outputs.doc_1_is_append = True
    outputs.doc_2_is_append = True
    outputs.doc_1_parent_path = parent_doc_1_path
    outputs.doc_2_parent_path = parent_doc_2_path

    metrics = executor.get_metrics()

    logger.info(
        f"[{job_id}] Run {run.run_id} (expand) complete: "
        f"{len(new_source_ids)} new sources added, Doc 1/2 appended"
    )

    return outputs, metrics.model_dump()


def _synthesize_append_sections(
    job_id: str,
    run: Run,
    doc_0_delta: dict[str, Any],
    parent_doc_1: dict[str, Any],
    parent_doc_2: dict[str, Any],
    user_prompt: Optional[str],
    executor: RunModeExecutor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Synthesize ONLY new findings into append sections for Doc 1/2.

    CRITICAL: This does NOT regenerate the full Doc 1/2.
    It produces a NEW SECTION that gets appended to the existing documents.
    The existing analysis is never modified.

    The LLM receives:
    - New source extractions only
    - Existing Doc 1 themes/gaps (read-only context)
    - User prompt

    And produces:
    - Doc 1 section: New key points, themes, tensions, gaps
    - Doc 2 section: Narrative covering what new sources reveal
    """
    from backend.integrations.gemini_client import GeminiClient

    gemini = GeminiClient()

    # Get new extractions from delta
    new_extractions = doc_0_delta.get("semantic_extractions", [])
    new_sources = doc_0_delta.get("sources", [])

    if not new_extractions:
        # No extractions means no new findings
        empty_section_1 = _create_empty_doc1_section(run.run_id)
        empty_section_2 = _create_empty_doc2_section(run.run_id)
        return empty_section_1, empty_section_2

    # Collect new key points and claims
    new_key_points = []
    new_claims = []
    for ext in new_extractions:
        new_key_points.extend(ext.get("key_points", []))
        new_claims.extend(ext.get("claims", []))

    # Get existing themes for context (read-only)
    existing_themes = parent_doc_1.get("themes", parent_doc_1.get("directions", []))
    existing_gaps = parent_doc_1.get("gaps", parent_doc_1.get("research_gaps", []))
    existing_key_points = parent_doc_1.get("key_points", [])

    executor.update_progress(75, "Analyzing new findings against existing research")

    # Build the append synthesis prompt
    guidance = ""
    if user_prompt:
        guidance = f"\nUSER GUIDANCE: {user_prompt}\n"

    prompt = f"""You are analyzing NEW research sources that have been added to an existing body of research.

{guidance}

## EXISTING RESEARCH CONTEXT (READ-ONLY — do NOT repeat or modify)

Existing themes: {_format_themes(existing_themes[:5])}
Existing gaps: {_format_gaps(existing_gaps[:5])}
Existing key points count: {len(existing_key_points)}

## NEW SOURCE FINDINGS (analyze these)

New sources added: {len(new_sources)}
New key points ({len(new_key_points)} total):
{_format_key_points(new_key_points[:15])}

New claims ({len(new_claims)} total):
{_format_claims(new_claims[:10])}

## YOUR TASK

Analyze ONLY the new findings. Produce:
1. NEW key points from the new sources (do not duplicate existing ones)
2. NEW themes discovered (or note which existing themes are reinforced)
3. NEW tensions between new and existing findings
4. UPDATED gap assessment (which gaps are now addressed, any new gaps?)
5. Contradictions between new sources and existing research

Return JSON:
{{
  "new_key_points": [
    {{"key_point_id": "KP_new_1", "statement": "...", "source_ids": ["SRC_..."], "confidence": "HIGH|MEDIUM|LOW"}}
  ],
  "new_themes": [
    {{"theme_id": "THEME_new_1", "label": "...", "description": "...", "related_key_points": ["KP_new_1"]}}
  ],
  "reinforced_themes": [
    {{"existing_theme": "theme label or id", "new_evidence": "what the new sources add", "supporting_sources": ["SRC_..."]}}
  ],
  "new_tensions": [
    {{"tension_id": "TEN_new_1", "label": "...", "description": "...", "involved_points": ["KP_new_1", "KP_3"]}}
  ],
  "contradictions": [
    {{"description": "...", "existing_claim": "...", "new_evidence": "...", "sources": ["SRC_..."]}}
  ],
  "gap_updates": [
    {{"gap_description": "...", "status": "addressed|partially_addressed|new_gap", "explanation": "..."}}
  ],
  "summary": "2-3 sentence summary of what the new sources contribute"
}}

CRITICAL RULES:
- Only analyze the NEW sources. Do NOT re-analyze existing research.
- Reference existing themes/gaps by name for context, but do not modify them.
- Every claim must trace to a source_id from the new sources.
- If new sources contradict existing findings, flag it — do not resolve it.
"""

    try:
        response = gemini.generate_json(
            prompt=prompt,
            system_message="You analyze new research sources and identify what they ADD to an existing body of research. You never repeat or modify existing findings.",
        )
        executor.metrics.record_llm_call(tokens_in=3000, tokens_out=1500, cost=0.05)

        data = response.get("data", {})

        # Build Doc 1 append section
        doc_1_section = {
            "section_type": "expansion",
            "run_id": run.run_id,
            "run_type": "expand",
            "user_prompt": user_prompt or "",
            "new_source_count": len(new_sources),
            "new_key_points": data.get("new_key_points", []),
            "new_themes": data.get("new_themes", []),
            "reinforced_themes": data.get("reinforced_themes", []),
            "new_tensions": data.get("new_tensions", []),
            "contradictions": data.get("contradictions", []),
            "gap_updates": data.get("gap_updates", []),
            "summary": data.get("summary", ""),
        }

        # Build Doc 2 append section
        summary = data.get("summary", "New sources were analyzed.")
        new_theme_labels = [t.get("label", "") for t in data.get("new_themes", [])]
        contradiction_count = len(data.get("contradictions", []))

        narrative_parts = [summary]
        if new_theme_labels:
            narrative_parts.append(f"New themes identified: {', '.join(new_theme_labels)}.")
        if contradiction_count > 0:
            narrative_parts.append(f"{contradiction_count} contradiction(s) found with existing findings.")

        doc_2_section = {
            "section_type": "expansion",
            "run_id": run.run_id,
            "run_type": "expand",
            "heading": f"## Expansion: {user_prompt or 'Additional Sources'} (Run {run.run_id})",
            "narrative": " ".join(narrative_parts),
            "new_source_count": len(new_sources),
            "key_additions": [
                kp.get("statement", "")
                for kp in data.get("new_key_points", [])[:5]
            ],
            "themes_added": new_theme_labels,
            "contradictions_found": contradiction_count,
        }

        executor.metrics.record_extraction(
            key_points=len(data.get("new_key_points", [])),
            themes=len(data.get("new_themes", [])),
        )

        return doc_1_section, doc_2_section

    except Exception as e:
        logger.error(f"[{job_id}] Append synthesis failed: {e}")
        return (
            _create_empty_doc1_section(run.run_id, error=str(e)),
            _create_empty_doc2_section(run.run_id, error=str(e)),
        )


# ============================================================================
# Source processing helpers (reused from add_sources.py)
# ============================================================================

def _search_for_sources(
    job_id: str,
    parent_doc_0: dict[str, Any],
    existing_urls: set[str],
    max_sources: int,
    user_prompt: Optional[str],
    executor: RunModeExecutor,
) -> list[str]:
    """Search for new relevant sources (basic fallback, not grounded)."""
    topic = parent_doc_0.get("research_topic", "")
    if not topic:
        sources = parent_doc_0.get("sources", [])
        if sources:
            titles = [s.get("title", "") for s in sources[:3]]
            topic = " ".join(titles)

    if not topic:
        logger.warning(f"[{job_id}] No topic found for source search")
        return []

    logger.info(f"[{job_id}] Searching for sources on: {topic[:50]}...")

    try:
        from backend.integrations.tavily_client import TavilyClient

        tavily = TavilyClient()
        search_query = user_prompt if user_prompt else topic

        results = tavily.search(
            query=search_query,
            max_results=max_sources * 2,
        )

        new_urls = []
        for result in results.get("results", []):
            url = result.get("url")
            if url and url not in existing_urls:
                new_urls.append(url)
                if len(new_urls) >= max_sources:
                    break

        executor.metrics.record_llm_call(tokens_in=100, tokens_out=50, cost=0.01)
        return new_urls

    except Exception as e:
        logger.warning(f"[{job_id}] Source search failed: {e}")
        return []


def _process_new_sources(
    job_id: str,
    run: Run,
    source_urls: list[str],
    executor: RunModeExecutor,
) -> tuple[list[str], dict[str, Any]]:
    """Process and extract new sources."""
    new_source_ids = []
    sources_data = []
    extractions = []

    for i, url in enumerate(source_urls):
        source_id = f"SRC_{run.run_id}_{i + 1}"
        new_source_ids.append(source_id)

        progress = 30 + int((i / len(source_urls)) * 35)
        executor.update_progress(progress, f"Processing: {url[:40]}...")

        try:
            source_data, extraction = _ingest_and_extract_source(
                job_id=job_id,
                source_id=source_id,
                url=url,
                executor=executor,
            )

            sources_data.append(source_data)
            if extraction:
                extractions.append(extraction)
                executor.metrics.record_extraction(
                    key_points=len(extraction.get("key_points", [])),
                    claims=len(extraction.get("claims", [])),
                )

            executor.metrics.record_source(is_new=True)

        except Exception as e:
            logger.warning(f"[{job_id}] Failed to process {url}: {e}")
            sources_data.append({
                "source_id": source_id,
                "url": url,
                "status": "failed",
                "error": str(e)[:200],
            })

    # Build delta Doc 0
    doc_0_delta = {
        "run_id": run.run_id,
        "run_type": "expand",
        "is_delta": True,
        "sources": sources_data,
        "source_manifest": [
            {"source_id": s["source_id"], "url": s.get("url", "")}
            for s in sources_data
        ],
        "source_count": len(sources_data),
        "ingested_count": sum(1 for s in sources_data if s.get("status") == "ingested"),
        "failed_count": sum(1 for s in sources_data if s.get("status") == "failed"),
        "semantic_extractions": extractions,
    }

    return new_source_ids, doc_0_delta


def _ingest_and_extract_source(
    job_id: str,
    source_id: str,
    url: str,
    executor: RunModeExecutor,
) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
    """Ingest and extract a single source."""
    from backend.utils.url_utils import classify_url

    source_type = classify_url(url)

    source_data = {
        "source_id": source_id,
        "url": url,
        "source_type": source_type,
        "status": "ingested",
        "title": f"Source {source_id}",
    }

    extraction = None

    try:
        if source_type == "youtube":
            from backend.integrations.supadata import SupadataClient

            supadata = SupadataClient()
            transcript = supadata.get_transcript(url)

            if transcript:
                source_data["transcript"] = transcript[:10000]
                source_data["has_transcript"] = True

                extraction = _extract_from_content(
                    job_id=job_id,
                    source_id=source_id,
                    content=transcript,
                    source_type=source_type,
                    executor=executor,
                )

        elif source_type in ("article", "web"):
            from backend.integrations.tavily_client import TavilyClient

            tavily = TavilyClient()
            content = tavily.extract_content(url)

            if content:
                source_data["content"] = content[:10000]
                source_data["title"] = content.get("title", source_data["title"])

                extraction = _extract_from_content(
                    job_id=job_id,
                    source_id=source_id,
                    content=content.get("text", ""),
                    source_type=source_type,
                    executor=executor,
                )

    except Exception as e:
        logger.warning(f"[{job_id}] Extraction failed for {source_id}: {e}")
        source_data["extraction_error"] = str(e)[:200]

    return source_data, extraction


def _extract_from_content(
    job_id: str,
    source_id: str,
    content: str,
    source_type: str,
    executor: RunModeExecutor,
) -> dict[str, Any]:
    """Extract semantic content from source text (source-isolated)."""
    from backend.integrations.gemini_client import GeminiClient

    if not content or len(content) < 50:
        return {"source_id": source_id, "key_points": [], "claims": []}

    gemini = GeminiClient()

    prompt = f"""
Analyze this {source_type} content and extract key semantic information.

Content:
{content[:8000]}

Extract:
1. Key points (main insights, findings, arguments)
2. Claims (factual assertions that could be verified)

Return JSON with:
- key_points: list of {{statement, confidence: "HIGH"/"MEDIUM"/"LOW"}}
- claims: list of {{statement, confidence: "HIGH"/"MEDIUM"/"LOW"}}
"""

    try:
        response = gemini.generate_json(
            prompt=prompt,
            system_message="Extract semantic content from research sources.",
        )
        executor.metrics.record_llm_call(tokens_in=2000, tokens_out=500, cost=0.02)

        data = response.get("data", {})

        key_points = []
        for i, kp in enumerate(data.get("key_points", [])[:10]):
            key_points.append({
                "key_point_id": f"KP_{source_id}_{i + 1}",
                "statement": kp.get("statement", ""),
                "source_ids": [source_id],
                "confidence": kp.get("confidence", "MEDIUM"),
            })

        claims = []
        for i, cl in enumerate(data.get("claims", [])[:10]):
            claims.append({
                "claim_id": f"CLM_{source_id}_{i + 1}",
                "statement": cl.get("statement", ""),
                "source_ids": [source_id],
                "confidence": cl.get("confidence", "MEDIUM"),
            })

        return {
            "source_id": source_id,
            "key_points": key_points,
            "claims": claims,
        }

    except Exception as e:
        logger.warning(f"[{job_id}] LLM extraction failed: {e}")
        return {"source_id": source_id, "key_points": [], "claims": []}


# ============================================================================
# Helper functions
# ============================================================================

def _create_empty_delta(run_id: str) -> dict[str, Any]:
    """Create empty delta Doc 0 when no new sources found."""
    return {
        "run_id": run_id,
        "run_type": "expand",
        "is_delta": True,
        "sources": [],
        "source_manifest": [],
        "source_count": 0,
        "ingested_count": 0,
        "failed_count": 0,
        "semantic_extractions": [],
        "note": "No new sources found or added",
    }


def _create_empty_doc1_section(run_id: str, error: str = "") -> dict[str, Any]:
    """Create empty Doc 1 append section."""
    section = {
        "section_type": "expansion",
        "run_id": run_id,
        "run_type": "expand",
        "new_key_points": [],
        "new_themes": [],
        "reinforced_themes": [],
        "new_tensions": [],
        "contradictions": [],
        "gap_updates": [],
        "summary": "No new findings from expansion.",
    }
    if error:
        section["error"] = error
    return section


def _create_empty_doc2_section(run_id: str, error: str = "") -> dict[str, Any]:
    """Create empty Doc 2 append section."""
    section = {
        "section_type": "expansion",
        "run_id": run_id,
        "run_type": "expand",
        "heading": f"## Expansion (Run {run_id})",
        "narrative": "No new findings were produced from this expansion.",
        "new_source_count": 0,
        "key_additions": [],
    }
    if error:
        section["error"] = error
    return section


def _format_key_points(key_points: list[dict]) -> str:
    """Format key points for prompt."""
    lines = []
    for kp in key_points:
        lines.append(f"- [{kp.get('confidence', 'MEDIUM')}] {kp.get('statement', '')} (source: {', '.join(kp.get('source_ids', []))})")
    return "\n".join(lines) if lines else "(none)"


def _format_claims(claims: list[dict]) -> str:
    """Format claims for prompt."""
    lines = []
    for cl in claims:
        lines.append(f"- [{cl.get('confidence', 'MEDIUM')}] {cl.get('statement', '')}")
    return "\n".join(lines) if lines else "(none)"


def _format_themes(themes: list) -> str:
    """Format existing themes for context."""
    lines = []
    for t in themes:
        if isinstance(t, dict):
            label = t.get("label", t.get("theme", ""))
            desc = t.get("description", "")[:80]
            lines.append(f"- {label}: {desc}")
        elif isinstance(t, str):
            lines.append(f"- {t}")
    return "\n".join(lines) if lines else "(none)"


def _format_gaps(gaps: list) -> str:
    """Format existing gaps for context."""
    lines = []
    for g in gaps:
        if isinstance(g, dict):
            label = g.get("label", g.get("description", "")[:60])
            lines.append(f"- {label}")
        elif isinstance(g, str):
            lines.append(f"- {g}")
    return "\n".join(lines) if lines else "(none)"
