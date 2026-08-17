"""P2 gate: render the fixture's Claim Graph as the Briefing and lint it."""
import json
import sys

sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")

from backend.models.claim_graph import ClaimGraph
from backend.pipeline.formatters.briefing_formatter import render_briefing
from backend.pipeline.style_enforcer import lint_rendered_document

SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"

graph = ClaimGraph.model_validate(json.load(open(f"{SCRATCH}/fixture_graph.json")))
doc0 = json.load(open(f"{SCRATCH}/doc_0.json"))["data"]
titles = {s["source_id"]: s.get("title") for s in doc0["sources"]}

briefing = render_briefing(graph, titles)

out = f"{SCRATCH}/BRIEFING.md"
with open(out, "w") as f:
    f.write(briefing)

result = lint_rendered_document(briefing)
passes, violations = result.passes, result.all_findings

print(f"rendered: {len(briefing):,} chars, {len(briefing.split())} words, "
      f"{len(briefing.splitlines())} lines")
print(f"tic-lint: {'PASS' if passes else 'FAIL'}")
for v in violations:
    print("   -", v)

# Length comparison against the documents this replaces.
for n, label in ((1, "Jump-Start"), (2, "Semantic Brief")):
    md = json.load(open(f"{SCRATCH}/doc_{n}.json")).get("markdown") or ""
    print(f"  old {label}: {len(md):,} chars")
print(f"  new Briefing: {len(briefing):,} chars")
print("wrote", out)
