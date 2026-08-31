"""Driver: production semantic advisory over the Packer r3 Read.

Phase A: harvest the r3 sources with the production harvest stage (cached).
Phase B: run SemanticAdvisoryRunner with the production adapters.
Scratchpad only; no production code touched.
"""
import json, sys, time, threading
from pathlib import Path

sys.path.insert(0, "/Users/mazbot/Research_Agent-v3work")

from backend.config import get_settings
from backend.integrations.structured_client import get_structured_client
from backend.pipeline.stages.harvest_stage import harvest_source, build_inventory
from backend.pipeline.semantic_advisory import source_sentence_units
from backend.pipeline.semantic_advisory_runner import (
    SemanticAdvisoryRunner, StructuredSeatModel, DashScopeEmbedder,
)

BASE = "/Users/mazbot/Research_Agent-v3work/scratchpad/e2e_films"
HARVEST_CACHE = f"{BASE}/packer_r3_harvest.json"
REPORT_PATH = f"{BASE}/packer_semantic_report.json"

settings = get_settings()
d0 = json.load(open(f"{BASE}/packer_r3_doc_0.json"))["data"]
sources = [
    {"source_id": s["source_id"], "full_text": s["full_text"], "title": s.get("title") or s["source_id"]}
    for s in d0["sources"]
    if s.get("full_text")
]
print(f"sources: {len(sources)}", flush=True)

# ---- Phase A: harvest (cached) ----
try:
    harvest = json.load(open(HARVEST_CACHE))["harvest"]
    print("harvest loaded from cache", flush=True)
except FileNotFoundError:
    client = get_structured_client(settings.model_harvest)
    harvest, total_cost = {}, 0.0
    for s in sources:
        facts, cost = harvest_source(
            client, s["source_id"], s["title"], s["full_text"],
        )
        harvest[s["source_id"]] = facts
        total_cost += cost
        print(f"harvested {s['source_id']}: {len(facts)} facts (${cost:.4f})", flush=True)
    json.dump(
        {"model": settings.model_harvest, "cost": total_cost, "harvest": harvest},
        open(HARVEST_CACHE, "w"), indent=1,
    )
    print(f"harvest total cost ${total_cost:.4f}", flush=True)

inventory = build_inventory(harvest)
inventory = [{"fact_id": f["fact_id"], "source_id": f["source_id"], "text": f["text"]} for f in inventory]
print(f"inventory: {len(inventory)} facts", flush=True)

# ---- Read sentences (1-in-2 sample; 82 total > 40) ----
d2 = json.load(open(f"{BASE}/packer_r3_doc_2.json"))["data"]
read = d2["read"]
blocks = [("LEDE", read["lede"])] + [
    (f"P{i+1}", p["text"]) for i, p in enumerate(read["paragraphs"])
]
all_sentences = []
for block_id, text in blocks:
    for u in source_sentence_units(text):
        all_sentences.append(
            {"sentence_id": f"{block_id}:S{u['sentence_index']+1:02d}", "sentence": u["text"]}
        )
# A dozen varied sentences answers 'does the checker find real problems'.
# The full 41 can run later off the warm cache if the dozen looks right.
SAMPLE = int(__import__('os').environ.get('SEM_SAMPLE', '12'))
step = max(1, len(all_sentences) // SAMPLE)
sampled = all_sentences[::step][:SAMPLE]
print(f"sentences: {len(all_sentences)} total, running {len(sampled)} (every {step}th)", flush=True)

# ---- Phase B: advisory ----
class LoggingSeat(StructuredSeatModel):
    def __init__(self, model_id):
        super().__init__(model_id)
        self.calls = 0
        self.lock = threading.Lock()
    def generate(self, stage, prompt, schema):
        with self.lock:
            self.calls += 1
            n = self.calls
        t0 = time.time()
        out = super().generate(stage, prompt, schema)
        print(f"call {n} [{stage}] {time.time()-t0:.1f}s", flush=True)
        return out

model = LoggingSeat(settings.model_judge)
runner = SemanticAdvisoryRunner(
    model,
    DashScopeEmbedder(cache_path=Path(BASE) / "embedding_cache.json.gz"),
)
t0 = time.time()
report = runner.run("packer_r3_read", sampled, inventory, sources)
report["run_meta"] = {
    "job_id": d2.get("job_id"),
    "seat_model": settings.model_judge,
    "harvest_model": settings.model_harvest,
    "sentences_total": len(all_sentences),
    "sentences_run": len(sampled),
    "sampling": "1-in-2 (every other sentence, order preserved)",
    "model_calls": model.calls,
    "wall_seconds": round(time.time() - t0, 1),
}
json.dump(report, open(REPORT_PATH, "w"), indent=1)
print(f"DONE: {model.calls} calls, {time.time()-t0:.0f}s -> {REPORT_PATH}", flush=True)
