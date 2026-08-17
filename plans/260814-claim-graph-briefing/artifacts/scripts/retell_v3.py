"""New format run: named attribution, no gestures, chorus cap, linked sources."""
import json, sys
from dotenv import load_dotenv
load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")
from backend.models.claim_graph import ClaimGraph
from backend.pipeline.stages.distillation_stage import write_telling_layer
from backend.pipeline.voice_repair import repair_voice
from backend.pipeline.formatters.briefing_formatter import render_briefing
from backend.pipeline.style_enforcer import lint_rendered_document

SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"
graph = ClaimGraph.model_validate(json.load(open(f"{SCRATCH}/fixture_graph_v2.json")))
doc0 = json.load(open(f"{SCRATCH}/doc_0.json"))["data"]
titles = {s["source_id"]: s.get("title") for s in doc0["sources"]}
urls = {s["source_id"]: s.get("url") for s in doc0["sources"] if s.get("url")}
bylines = [
    {"source": s.get("title"), "author": s.get("creator"), "type": s.get("source_type")}
    for s in doc0["sources"]
]

full, usages = write_telling_layer("fixture", graph, titles, source_bylines=bylines)
briefing = render_briefing(full, titles, urls)
r = lint_rendered_document(briefing)
rounds = 0
if not r.passes:
    print("pre-repair:", [e[:90] for e in r.errors])
    full, stats = repair_voice("fixture", full)
    print("repair:", {k: stats[k] for k in ("offenders", "applied", "skipped")})
    briefing = render_briefing(full, titles, urls)
    r = lint_rendered_document(briefing)

open(f"{SCRATCH}/BRIEFING-V3.md", "w").write(briefing)
json.dump(full.model_dump(mode="json"), open(f"{SCRATCH}/fixture_graph_v3.json", "w"), indent=2)
import re
print(f"final: {len(briefing):,} chars | lint {'PASS' if r.passes else 'FAIL '+str([e[:80] for e in r.errors])}")
print(f"cost ${sum(u['cost'] for u in usages):.2f}")
print("named-attribution check: 'Travis Holland' in brief:", "Travis Holland" in briefing,
      "| 'according to' count:", len(re.findall(r'according to', briefing, re.I)))
