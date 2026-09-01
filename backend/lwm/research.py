"""Run the Research Agent for an episode — the maintained invocation path.

Wraps the existing production worker (`run_research_job`) and the existing
iterate machinery (`grounded_search` + expand) so a normal run executes its
research cycles without anyone hand-ferrying gap results between stages.
No research logic lives here; doctrine (full-source preservation, provenance,
gap analysis, over-gather-before-distill, Doc 0 authority) is untouched.
"""

import json
from pathlib import Path

from loguru import logger

from backend.lwm import manifest

# Bounded by design: one base round + at most this many gap-driven expansions.
# Matches how Packer actually ran (round 1 + one gap round). Not endless.
MAX_GAP_ROUNDS = 1
# A gap round only fires when gap analysis produced at least this many gaps.
MIN_GAPS_TO_EXPAND = 2


def build_job_config(episode: Path, topic: str) -> dict:
    """The mixed-input config the worker expects, from the manifest."""
    pending = manifest.pending_for_research(episode)
    n = sum(len(pending[k]) for k in ("video_urls", "article_urls", "text_inputs", "screenshots"))
    if n == 0 and not topic:
        raise ValueError("nothing to research: no pending sources and no topic")
    return {
        "topic": topic,
        "job_type": "mixed_input",
        "input_mode": "mixed",
        "video_urls": pending["video_urls"],
        "article_urls": pending["article_urls"],
        "text_inputs": pending["text_inputs"],
        "screenshots": [{"filename": Path(p).name, "path": p} for p in pending["screenshots"]],
        "source_count": n,
        "duplicates_removed": 0,
    }


def run_round(episode: Path, topic: str) -> dict:
    """One base research round through the production worker."""
    from backend.state import create_job
    from backend.worker import run_research_job

    config = build_job_config(episode, topic)
    job = create_job(config_json=config)
    logger.info(f"lwm research: job {job.job_id} — {config['source_count']} sources")
    result = run_research_job(job.job_id, topic)
    _record_job(episode, job.job_id, result)
    return {"job_id": job.job_id, **{k: result.get(k) for k in ("status", "claims_count", "sources_count", "warnings_count")}}


def run_gap_rounds(episode: Path, topic: str, rounds: int = MAX_GAP_ROUNDS) -> list[dict]:
    """The gap loop, automated the way Packer's manual round 2 actually worked.

    Round N completes → its Doc 1 names the gaps → `grounded_search` (existing
    machinery: query generation from Doc 0 context, multi-provider search,
    relevance gate) finds sources answering them → they join the manifest as
    role="discovered" → one more full round runs over everything. Nobody
    hand-ferries gap output into a new job config any more.

    Bounded: at most `rounds` extra rounds (default 1, matching the proven
    Packer shape), and a round that finds too few gaps or no accepted
    candidates ends the loop — the existing relevance gate is the
    diminishing-returns rule.
    """
    from backend.lwm.handoff import load_job_docs
    from backend.pipeline.runs.search import grounded_search

    results = []
    for i in range(rounds):
        job_id = current_job_id(episode)
        docs = load_job_docs(job_id)
        doc_0, doc_1 = docs["doc_0"], docs["doc_1"]
        gaps = (doc_1.get("gaps") or []) + (doc_1.get("research_directions") or [])
        if len(gaps) < MIN_GAPS_TO_EXPAND:
            logger.info(f"lwm gap loop: {len(gaps)} gaps — below threshold, stopping")
            break
        prompt = "Fill these specific gaps in the research:\n" + "\n".join(
            f"- {g.get('label') or g.get('description') or g}" if isinstance(g, dict) else f"- {g}"
            for g in gaps[:10]
        )
        existing = {s.get("url", "") for s in doc_0.get("sources", []) if s.get("url")}
        candidates = grounded_search(doc_0, prompt, existing_urls=existing, max_results=8)
        if not candidates:
            logger.info("lwm gap loop: no accepted candidates — stopping")
            break
        added = []
        for c in candidates:
            entry = manifest.add_source(episode, c["url"], role="discovered", offline=True)
            if not entry.get("duplicate"):
                added.append(c["url"])
        if not added:
            break
        logger.info(f"lwm gap loop round {i + 1}: re-running with {len(added)} new sources")
        result = run_round(episode, topic)
        results.append({"round": i + 1, "added": added, "job_id": result["job_id"]})
    return results


def _record_job(episode: Path, job_id: str, result: dict) -> None:
    p = episode / "research" / "ra-job.json"
    p.parent.mkdir(exist_ok=True)
    history = json.loads(p.read_text()) if p.exists() else {"jobs": []}
    history["jobs"].append({"job_id": job_id, "status": result.get("status"),
                            "claims": result.get("claims_count"),
                            "sources": result.get("sources_count")})
    history["current"] = job_id
    p.write_text(json.dumps(history, indent=1) + "\n")


def current_job_id(episode: Path) -> str | None:
    p = episode / "research" / "ra-job.json"
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("current")
