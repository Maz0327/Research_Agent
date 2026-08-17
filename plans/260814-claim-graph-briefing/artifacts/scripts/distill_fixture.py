"""P1 gate: distill the golden fixture job into a schema-valid Claim Graph.

Rebuilds the distillation input from the fixture's stored documents (doc_0
source ledger + doc_2 semantic brief), since the live PipelineContext for a
completed job no longer exists.
"""

import json
import sys
import time

from dotenv import load_dotenv

load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")

from backend.models.semantic_units import ConfidenceLevel
from backend.pipeline.stages.distillation_stage import (
    build_corpus,
    confidence_ceiling_grade,
    distill_corpus,
)

JOB_ID = "51c97825-4840-44e8-b93a-593688b31a07"
SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"

doc0 = json.load(open(f"{SCRATCH}/doc_0.json"))["data"]
doc2 = json.load(open(f"{SCRATCH}/doc_2.json"))["data"]

sources = doc0["sources"]
key_points = doc2["key_points"]

# Articles and transcript-backed videos both carry a HIGH ceiling. The fixture's
# quotes could not be verified against the transcripts, so verification is 0 and
# the ceiling drops one grade.
ceilings = [ConfidenceLevel.HIGH] * len(sources)
verification_rate = 0.0
max_grade = confidence_ceiling_grade(ceilings, verification_rate)

corpus = build_corpus(
    topic=doc0.get("topic") or "why modern films look the way they do",
    sources=sources,
    key_points=key_points,
    themes=doc2.get("themes", []),
    tensions=doc2.get("tensions", []),
    gaps=doc2.get("gaps", []),
    semantic_core=(doc2.get("semantic_core") or {}).get("text"),
)

print("=== corpus ===")
print(f"  sources:     {len(corpus['sources'])}")
print(f"  key points:  {len(corpus['key_points'])} "
      f"({len({k['ref'] for k in corpus['key_points']})} unique refs)")
print(f"  themes:      {len(corpus['themes'])}")
print(f"  tensions:    {len(corpus['tensions'])}")
print(f"  gaps:        {len(corpus['gaps'])}")
print(f"  ceiling:     grade {max_grade}")
print(f"  corpus size: {len(json.dumps(corpus)):,} chars")

known = {s["source_id"] for s in sources}

start = time.time()
graph, usages = distill_corpus(
    job_id=JOB_ID,
    corpus=corpus,
    max_confidence_grade=max_grade,
    verification_rate=verification_rate,
    known_source_ids=known,
)
elapsed = time.time() - start

print(f"\n=== graph (valid) in {elapsed:.0f}s ===")
print(f"  claims:      {len(graph.claims)}")
print(f"  story goods: {len(graph.story_goods)}")
print(f"  holes:       {len(graph.holes)}")
print(f"  attempts:    {len(usages)}  cost=${sum(u['cost'] for u in usages):.3f}")
print(f"  ledger check: {graph.validate_against_ledger(known) or 'clean'}")
print(f"  max grade used: {max(c.confidence.grade for c in graph.claims)} (ceiling {max_grade})")

out = f"{SCRATCH}/fixture_graph.json"
with open(out, "w") as f:
    json.dump(graph.model_dump(mode="json"), f, indent=2)
print("  wrote", out)

print("\n=== thesis ===")
print(" ", graph.thesis.text)
print(f"  confidence: {graph.thesis.confidence}")

print("\n=== spine ===")
for c in graph.claims_in_spine_order():
    holes = len(graph.holes_for(c.id))
    print(f"  {c.spine_order}. [{c.confidence.grade}/5 {c.evidence_status}] {c.title}")
    if holes:
        print(f"       holes: {holes}")
