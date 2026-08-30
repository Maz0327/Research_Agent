"""End-to-end pipeline test on a fresh topic (films fixture, job 51c97825).

Stages: sources (from the stored doc_0) -> harvest -> Read (3-pass, production
run_read_pass) -> semantic advisory (production runner, sampled sentences).
Artifacts land in scratchpad/e2e_films/. Run stages individually:

    python scratchpad/e2e_films_run.py sources|harvest|read|advisory|report
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import get_settings  # noqa: E402
from backend.integrations.structured_client import get_structured_client  # noqa: E402
from backend.integrations.supabase_storage import get_storage_client  # noqa: E402
from backend.pipeline.semantic_advisory import source_sentence_units  # noqa: E402
from backend.pipeline.semantic_advisory_runner import (  # noqa: E402
    DashScopeEmbedder,
    SemanticAdvisoryRunner,
    StructuredSeatModel,
)
from backend.pipeline.stages.harvest_stage import build_inventory, harvest_source  # noqa: E402

JOB = "51c97825-4840-44e8-b93a-593688b31a07"
OUT = ROOT / "scratchpad" / "e2e_films"
OUT.mkdir(exist_ok=True)

MODE_CEILING = {"youtube": ("transcript_grounded", "HIGH"), "article": ("article_fetched", "HIGH")}


def stage_sources() -> None:
    """Pull the films sources (with full texts) from the stored doc_0."""
    client = get_storage_client()
    doc0 = client.download_document(f"{JOB}/doc_0.json")
    data = doc0["data"]
    sources = []
    for source in data["sources"]:
        text = (source.get("full_text") or "").strip()
        if not text:
            continue
        sources.append(
            {
                "source_id": source["source_id"],
                "source_type": source.get("source_type") or "article",
                "title": source.get("title") or source["source_id"],
                "full_text": text,
                "creator": source.get("creator"),
                "published": source.get("published"),
            }
        )
    payload = {"topic": data["topic"], "sources": sources}
    (OUT / "sources.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"sources: {len(sources)} with full text · total {sum(len(s['full_text']) for s in sources)} chars")
    print(f"topic: {data['topic']}")


def stage_harvest() -> None:
    """Harvest facts from every source with the configured harvest seat."""
    settings = get_settings()
    payload = json.loads((OUT / "sources.json").read_text())
    client = get_structured_client(settings.model_harvest)
    harvest: dict[str, list[str]] = {}
    total_cost = 0.0
    for source in payload["sources"]:
        mode, ceiling = MODE_CEILING.get(source["source_type"], ("article_fetched", "HIGH"))
        facts, cost = harvest_source(
            client,
            source["source_id"],
            source["title"],
            source["full_text"],
            mode=mode,
            ceiling=ceiling,
        )
        harvest[source["source_id"]] = facts
        total_cost += cost
        print(f"  {source['source_id']}: {len(facts)} facts (${cost:.3f})")
    (OUT / "harvest.json").write_text(json.dumps({"harvest": harvest}, ensure_ascii=False, indent=1))
    inventory = build_inventory(harvest)
    print(f"harvest: {len(inventory)} facts total · ${total_cost:.2f} · model {settings.model_harvest}")


def stage_read() -> None:
    """Write the Read with the production 3-pass flow."""
    settings = get_settings()
    payload = json.loads((OUT / "sources.json").read_text())
    model_id = settings.model_read or settings.model_distill
    client = get_structured_client(model_id)
    from backend.pipeline.briefing_passes import run_read_pass

    read = run_read_pass(client, payload["topic"], payload["sources"])
    data = {
        "lede": read.lede,
        "paragraphs": [{"label": p.label, "text": p.text} for p in read.paragraphs],
    }
    (OUT / "films_read.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    words = len(data["lede"].split()) + sum(len(p["text"].split()) for p in data["paragraphs"])
    print(f"read: {len(data['paragraphs'])} paragraphs · {words} words · model {model_id}")


def read_sentences(sample_every: int = 3) -> list[dict[str, str]]:
    """Split the Read into sentences and take a deterministic 1-in-N sample."""
    data = json.loads((OUT / "films_read.json").read_text())
    blocks = [("lede", data["lede"])] + [
        (f"p{i+1}", p["text"]) for i, p in enumerate(data["paragraphs"])
    ]
    sentences = []
    counter = 0
    for label, text in blocks:
        for unit in source_sentence_units(text):
            counter += 1
            sentences.append(
                {"sentence_id": f"F-S{counter:02d}", "sentence": unit["text"], "block": label}
            )
    sampled = [s for i, s in enumerate(sentences) if i % sample_every == 0]
    print(f"sentences: {len(sentences)} total · sampled {len(sampled)} (every {sample_every})")
    return sampled


def stage_advisory() -> None:
    """Run the semantic advisory on the sampled sentences."""
    payload = json.loads((OUT / "sources.json").read_text())
    harvest = json.loads((OUT / "harvest.json").read_text())["harvest"]
    inventory = build_inventory(harvest)
    sampled = read_sentences()
    runner = SemanticAdvisoryRunner(StructuredSeatModel("gpt-5.6-terra"), DashScopeEmbedder())
    report = runner.run(
        "films e2e (job 51c97825)",
        [{"sentence_id": s["sentence_id"], "sentence": s["sentence"]} for s in sampled],
        inventory,
        [{"source_id": s["source_id"], "full_text": s["full_text"]} for s in payload["sources"]],
    )
    (OUT / "advisory_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print("advisory counts:", report["advisory_counts"])
    print("evidence:", report["stats"])


def stage_report() -> None:
    """Print the flagged sentences with their advisories."""
    report = json.loads((OUT / "advisory_report.json").read_text())
    for sentence in report["sentences"]:
        status = sentence["advisory"]["deterministic_status"]
        if status in ("SEMANTIC_CONFLICT", "PARTIAL_WARNING", "UNVERIFIED"):
            print(f"\n[{status}] {sentence['sentence_id']}: {sentence['sentence'][:140]}")
            for cid in sentence["advisory"]["triggering_claim_ids"]:
                claim = next(c for c in sentence["claims"] if c["claim_id"] == cid)
                result = (
                    claim.get("direct_referee")
                    or claim.get("inference_referee")
                    or {"system_result": claim.get("corpus_check", {})}
                )["system_result"]
                print(f"    {cid}: {result.get('status') or result.get('conceptual_result')}"
                      f" — {str(result.get('reason') or result.get('system_reason'))[:120]}")


if __name__ == "__main__":
    {"sources": stage_sources, "harvest": stage_harvest, "read": stage_read,
     "advisory": stage_advisory, "report": stage_report}[sys.argv[1]]()
