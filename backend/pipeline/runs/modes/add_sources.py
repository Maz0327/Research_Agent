"""
Run mode: add_sources

Add new sources to research, producing:
- Doc 0 delta (new sources only, merged on display)
- Doc 1/2 regenerated with all sources

Key behaviors:
- Doc 0 is APPEND-ONLY (delta contains only new sources)
- New sources are extracted and added to synthesis
- Doc 1/2 reflect insights from ALL sources (parent + new)
"""

from typing import Any, Optional

from loguru import logger

from backend.models.run_models import Run, RunOutputs
from backend.pipeline.runs.modes.base import RunModeExecutor
from backend.pipeline.runs.storage import load_run_document, get_merged_doc_0


def run_add_sources(
    job_id: str,
    run: Run,
    user_id: str,
    artifacts_dict: dict[str, Any],
) -> tuple[RunOutputs, dict[str, Any]]:
    """
    Execute add_sources run type.

    This mode:
    1. Loads parent run's documents
    2. Searches for new sources based on request
    3. Extracts new sources
    4. Creates delta Doc 0 (new sources only)
    5. Regenerates Doc 1/2 with all sources

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
        raise ValueError("add_sources requires a parent run")

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

    # If no URLs provided, search for related sources
    if not new_source_urls:
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

    executor.update_progress(70, "Regenerating synthesis documents")

    # Regenerate Doc 1/2 with all sources
    doc_1, doc_2 = _regenerate_synthesis(
        job_id=job_id,
        run=run,
        parent_doc_0=parent_doc_0,
        doc_0_delta=doc_0_delta,
        artifacts_dict=artifacts_dict,
        executor=executor,
    )

    executor.update_progress(90, "Storing run outputs")

    # Store outputs
    outputs = executor.store_outputs(
        doc_0=doc_0_delta,
        doc_1=doc_1,
        doc_2=doc_2,
        is_doc_0_delta=True,
        parent_doc_0_path=parent_doc_0_path,
        new_source_ids=new_source_ids,
    )

    metrics = executor.get_metrics()

    logger.info(
        f"[{job_id}] Run {run.run_id} (add_sources) complete: "
        f"{len(new_source_ids)} new sources added"
    )

    return outputs, metrics.model_dump()


def _search_for_sources(
    job_id: str,
    parent_doc_0: dict[str, Any],
    existing_urls: set[str],
    max_sources: int,
    user_prompt: Optional[str],
    executor: RunModeExecutor,
) -> list[str]:
    """Search for new relevant sources."""
    # Extract topic from parent doc
    topic = parent_doc_0.get("research_topic", "")
    if not topic:
        # Try to infer from sources
        sources = parent_doc_0.get("sources", [])
        if sources:
            titles = [s.get("title", "") for s in sources[:3]]
            topic = " ".join(titles)

    if not topic:
        logger.warning(f"[{job_id}] No topic found for source search")
        return []

    logger.info(f"[{job_id}] Searching for sources on: {topic[:50]}...")

    # Use search integration if available
    try:
        from backend.integrations.tavily_client import TavilyClient

        tavily = TavilyClient()
        search_query = user_prompt if user_prompt else topic

        results = tavily.search(
            query=search_query,
            max_results=max_sources * 2,  # Get extra to filter
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
    from backend.pipeline.context import PipelineContext

    new_source_ids = []
    sources_data = []
    extractions = []

    for i, url in enumerate(source_urls):
        source_id = f"SRC_{run.run_id}_{i + 1}"
        new_source_ids.append(source_id)

        progress = 30 + int((i / len(source_urls)) * 35)
        executor.update_progress(progress, f"Processing: {url[:40]}...")

        try:
            # Ingest and extract source
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
            # Add failed source entry
            sources_data.append({
                "source_id": source_id,
                "url": url,
                "status": "failed",
                "error": str(e)[:200],
            })

    # Build delta Doc 0
    doc_0_delta = {
        "run_id": run.run_id,
        "run_type": "add_sources",
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
    # Determine source type
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
        # For YouTube videos, try to get transcript
        if source_type == "youtube":
            from backend.integrations.supadata import SupadataClient

            supadata = SupadataClient()
            transcript = supadata.get_transcript(url)

            if transcript:
                source_data["transcript"] = transcript[:10000]  # Truncate
                source_data["has_transcript"] = True

                # Extract from transcript
                extraction = _extract_from_content(
                    job_id=job_id,
                    source_id=source_id,
                    content=transcript,
                    source_type=source_type,
                    executor=executor,
                )

        # For web articles, fetch and extract
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
    """Extract semantic content from source text."""
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

        # Build extraction result
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


def _regenerate_synthesis(
    job_id: str,
    run: Run,
    parent_doc_0: dict[str, Any],
    doc_0_delta: dict[str, Any],
    artifacts_dict: dict[str, Any],
    executor: RunModeExecutor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Regenerate Doc 1 and Doc 2 with all sources."""
    from backend.integrations.gemini_client import GeminiClient

    gemini = GeminiClient()

    # Merge all sources for synthesis
    all_sources = parent_doc_0.get("sources", []) + doc_0_delta.get("sources", [])
    all_extractions = (
        parent_doc_0.get("semantic_extractions", []) +
        doc_0_delta.get("semantic_extractions", [])
    )

    # Collect all key points and claims
    all_key_points = []
    all_claims = []
    for ext in all_extractions:
        all_key_points.extend(ext.get("key_points", []))
        all_claims.extend(ext.get("claims", []))

    executor.update_progress(75, "Synthesizing themes and directions")

    # Generate synthesis
    synthesis_prompt = f"""
Analyze the following research findings and synthesize key themes and directions.

Key Points ({len(all_key_points)} total):
{_format_key_points(all_key_points[:20])}

Claims ({len(all_claims)} total):
{_format_claims(all_claims[:15])}

Provide:
1. Main themes across sources
2. Key tensions or contradictions
3. Research gaps needing attention
4. Jump-start directions for further research
"""

    try:
        response = gemini.generate_json(
            prompt=synthesis_prompt,
            system_message="Synthesize research findings into actionable directions.",
        )
        executor.metrics.record_llm_call(tokens_in=3000, tokens_out=1500, cost=0.05)

        data = response.get("data", {})

        # Build Doc 1 (Jump-Start Directions)
        doc_1 = {
            "run_id": run.run_id,
            "directions": data.get("directions", []),
            "research_gaps": data.get("gaps", []),
            "quick_start_priorities": data.get("priorities", []),
            "source_count": len(all_sources),
            "key_point_count": len(all_key_points),
        }

        # Build Doc 2 (Semantic Brief)
        doc_2 = {
            "run_id": run.run_id,
            "themes": data.get("themes", []),
            "tensions": data.get("tensions", []),
            "key_points_summary": all_key_points[:20],
            "claims_summary": all_claims[:15],
            "gaps": data.get("gaps", []),
            "confidence_summary": _compute_confidence_summary(all_key_points),
        }

        return doc_1, doc_2

    except Exception as e:
        logger.error(f"[{job_id}] Synthesis failed: {e}")
        # Return minimal docs on failure
        return (
            {"run_id": run.run_id, "directions": [], "error": str(e)},
            {"run_id": run.run_id, "themes": [], "error": str(e)},
        )


def _create_empty_delta(run_id: str) -> dict[str, Any]:
    """Create empty delta Doc 0 when no new sources found."""
    return {
        "run_id": run_id,
        "run_type": "add_sources",
        "is_delta": True,
        "sources": [],
        "source_manifest": [],
        "source_count": 0,
        "ingested_count": 0,
        "failed_count": 0,
        "semantic_extractions": [],
        "note": "No new sources found or added",
    }


def _format_key_points(key_points: list[dict]) -> str:
    """Format key points for prompt."""
    lines = []
    for kp in key_points:
        lines.append(f"- [{kp.get('confidence', 'MEDIUM')}] {kp.get('statement', '')}")
    return "\n".join(lines)


def _format_claims(claims: list[dict]) -> str:
    """Format claims for prompt."""
    lines = []
    for cl in claims:
        lines.append(f"- [{cl.get('confidence', 'MEDIUM')}] {cl.get('statement', '')}")
    return "\n".join(lines)


def _compute_confidence_summary(key_points: list[dict]) -> dict[str, int]:
    """Compute confidence distribution."""
    summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for kp in key_points:
        conf = kp.get("confidence", "MEDIUM").upper()
        if conf in summary:
            summary[conf] += 1
    return summary
