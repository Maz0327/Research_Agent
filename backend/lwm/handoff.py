"""RA job → v4 episode: the ONE production handoff.

Replaces the scratchpad adapters that carried Packer across by hand. Given a
completed Research Agent job it verifies the outputs, registers the job in
the episode, writes 03-brief, renders the 04b briefing through the production
renderer, populates the mechanical half of the stage-4 registry, runs the one
fresh-family judgment pass, and updates the ledger — transactionally: files
land in a staging dir and move into place only when everything succeeded, so
a failure never leaves half-written stage state.

Doc 0 stays source truth. The briefing renderer is the same code the pipeline
uses everywhere; nothing is transformed twice.
"""

import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

from backend.lwm import ledger, manifest, registry
from backend.models.briefing import Briefing
from backend.pipeline.formatters.briefing_renderer import (
    render_briefing_html,
    render_briefing_markdown,
)

REQUIRED_DOCS = ("doc_0", "doc_1", "doc_2")


def load_job_docs(job_id: str, docs_dir: Path | None = None) -> dict:
    """The job's documents, from local files or the production store.

    `docs_dir` (files named doc_0.json …) takes precedence — it is how tests
    and offline work run. Otherwise the job's artifacts are fetched through
    the existing Supabase storage integration.
    """
    docs = {}
    if docs_dir:
        for name in REQUIRED_DOCS:
            p = Path(docs_dir) / f"{name}.json"
            if not p.exists():
                raise FileNotFoundError(f"handoff: {p} missing")
            docs[name] = json.loads(p.read_text())
    else:
        from backend.state import get_job
        job = get_job(job_id)
        if not job:
            raise ValueError(f"handoff: job {job_id} not found")
        if getattr(job, "status", "") != "completed":
            raise ValueError(f"handoff: job {job_id} is {getattr(job, 'status', '?')!r}, not completed")
        from backend.integrations.supabase_storage import SupabaseStorage
        store = SupabaseStorage()
        arts = job.artifacts.model_dump(exclude_none=True) if hasattr(job.artifacts, "model_dump") else (job.artifacts or {})
        paths = arts.get("doc_paths") or arts
        for name in REQUIRED_DOCS:
            path = paths.get(name)
            if not path:
                raise ValueError(f"handoff: job {job_id} has no {name} artifact")
            docs[name] = store.download_document(path)

    # Shape validation before anything is written.
    for name in REQUIRED_DOCS:
        payload = docs[name].get("data", docs[name])
        if not isinstance(payload, dict) or not payload:
            raise ValueError(f"handoff: {name} is empty or malformed")
        docs[name] = docs[name] if "data" in docs[name] else {"data": payload}
    Briefing.model_validate(docs["doc_2"]["data"])  # fail loudly on schema drift
    return {name: docs[name]["data"] for name in REQUIRED_DOCS} | {
        "doc_2_wrapper": docs["doc_2"]
    }


def run_handoff(episode: Path, job_id: str, docs_dir: Path | None = None,
                harvest: dict | None = None, judgment_client=None) -> dict:
    """The full handoff. Idempotent: rerunning regenerates the same artifacts.

    Refuses to run once the episode has moved past the briefing (outline or
    later complete) unless the caller passes a fresh look intentionally — a
    later stage building on a briefing that then changes is the drift this
    bridge exists to prevent.
    """
    rows = ledger.read_rows(episode)
    for later in ("5 outline", "6 grip gate A", "7 draft"):
        if rows.get(later) and rows[later].complete:
            raise RuntimeError(
                f"handoff refused: {episode.name} has completed {later!r}; "
                "regenerating the briefing under a written outline is drift, not idempotence"
            )

    docs = load_job_docs(job_id, docs_dir)
    doc_0, doc_1, doc_2 = docs["doc_0"], docs["doc_1"], docs["doc_2"]
    briefing = Briefing.model_validate(doc_2)

    stage = Path(tempfile.mkdtemp(prefix="lwm-handoff-", dir=episode))
    try:
        # 1. The research record: job identity + preserved docs, provenance intact.
        research = stage / "research"
        research.mkdir()
        for name, payload in [("doc_0", doc_0), ("doc_1", doc_1), ("doc_2", doc_2)]:
            (research / f"{name}.json").write_text(json.dumps({"data": payload}, indent=1, ensure_ascii=False))

        # 2. 03-brief: the stats header the pipeline expects, from the job itself.
        n_sources = len(doc_0.get("sources", []))
        meta = getattr(briefing, "meta", None)
        (stage / "03-brief.md").write_text(
            f"""<!--
artifact:  03-brief
version:   v1
upstream:  —
readiness: complete
unresolved:
-->

# RESEARCH → BRIEF

Research ran through the Research Agent, not by hand.

**Job** `{job_id}` · {n_sources} sources · quotes verified {getattr(meta, 'quote_verification_rate', '—') if meta else '—'}.

The readable output is `04b-briefing.md`. Source list and full texts live in the job's
Doc 0 (preserved at `research/doc_0.json`); the briefing's Source Trail resolves every
SRC id used in the text.
"""
        )

        # 3. 04b: the same renderer the pipeline uses. JSON travels with the episode.
        markdown = render_briefing_markdown(briefing)
        (stage / "04b-briefing.md").write_text(markdown)
        (stage / "04b-briefing.html").write_text(render_briefing_html(briefing))
        (stage / "04b-briefing.json").write_text(
            json.dumps({"data": doc_2, "markdown": markdown}, indent=1, ensure_ascii=False)
        )

        # 4. Stage 4 registry: mechanical columns from the job, judgment pass on top.
        reg = registry.build(doc_0, doc_1, harvest=harvest, judgment_client=judgment_client)
        (stage / "04-sources-registry.md").write_text(registry.render(reg, job_id))

        # Everything succeeded — move into place, then the ledger, last.
        # Directories MERGE rather than replace: the episode's research/ dir
        # already holds ra-job.json (the job identity the state machine runs
        # on), and replacing the dir once deleted it — which sent the next
        # `continue` back to stage 4 with no job to hand off.
        for f in stage.iterdir():
            dest = episode / f.name
            if f.is_dir():
                dest.mkdir(exist_ok=True)
                for inner in f.iterdir():
                    target = dest / inner.name
                    if target.exists():
                        target.unlink()
                    shutil.move(str(inner), target)
            else:
                shutil.move(str(f), dest)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    # Manifest ↔ RA source ids.
    src_map = {s.get("url", ""): s.get("source_id") for s in doc_0.get("sources", []) if s.get("url")}
    manifest.mark_ingested(episode, src_map)

    today = str(date.today())
    ledger.update_row(episode, "3 brief", status="done", when=today,
                      notes=f"Research Agent job {job_id}: {len(doc_0.get('sources', []))} sources. Handoff via lwm.")
    # Stage 4 COMPLETES only when the judgment pass ran; a mechanical-only
    # registry leaves the stage open (visibly) so nothing downstream builds on
    # judgment columns that were never filled.
    ledger.update_row(episode, "4 fact-check the brief",
                      status="done" if reg["judged"] else "mechanical only (judgment PENDING)",
                      when=today,
                      gate=f"judgment pass: {'run' if reg['judged'] else 'PENDING'}",
                      notes=f"{len(reg['rows'])} rows from RA provenance; "
                            f"{reg['flagged']} row(s) flagged MISSING-SOURCE by code validation.")
    ledger.update_row(episode, "4b briefing + structure session", status="briefing ready", when=today,
                      gate="briefing ready: YES (04b .md/.html/.json via lwm handoff)",
                      notes="structure session: PENDING (Maz touchpoint B)")

    return {"job_id": job_id, "registry_rows": len(reg["rows"]),
            "registry_flagged": reg["flagged"], "judged": reg["judged"],
            "briefing_words": len(markdown.split())}
