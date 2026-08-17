"""Run the telling pass on the existing fixture provenance graph, render, lint."""
import json, sys, time
from dotenv import load_dotenv
load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")

from backend.models.claim_graph import ClaimGraph
from backend.pipeline.stages.distillation_stage import write_telling_layer
from backend.pipeline.formatters.briefing_formatter import render_briefing
from backend.pipeline.style_enforcer import lint_rendered_document

SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"
graph = ClaimGraph.model_validate(json.load(open(f"{SCRATCH}/fixture_graph.json")))
doc0 = json.load(open(f"{SCRATCH}/doc_0.json"))["data"]
titles = {s["source_id"]: s.get("title") for s in doc0["sources"]}

t0 = time.time()
full, usages = write_telling_layer("51c97825-4840-44e8-b93a-593688b31a07", graph, titles)
print(f"telling pass: {len(full.sections)} sections "
      f"({sum(1 for s in full.sections if s.is_connection)} connections), "
      f"{len(full.noticings)} noticings, {time.time()-t0:.0f}s, "
      f"${sum(u['cost'] for u in usages):.3f}, attempts={len(usages)}")

json.dump(full.model_dump(mode="json"), open(f"{SCRATCH}/fixture_graph_full.json","w"), indent=2)

briefing = render_briefing(full, titles)
open(f"{SCRATCH}/BRIEFING.md","w").write(briefing)
result = lint_rendered_document(briefing)
print(f"rendered: {len(briefing):,} chars, {len(briefing.split())} words")
print(f"lint: {'PASS' if result.passes else 'FAIL'}")
for e in result.errors: print("  ERROR:", e)
for a in result.advisories: print("  advisory:", a)
print("\nsection titles:")
for s in full.sections:
    print(f"  {'[CONNECTION] ' if s.is_connection else ''}{s.title}")
