"""Full chain with HARVESTED FACTS as the key-point layer."""
import json, re, sys, time
from dotenv import load_dotenv
load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")

from backend.models.semantic_units import ConfidenceLevel
from backend.pipeline.stages.distillation_stage import (
    build_corpus, confidence_ceiling_grade, distill_corpus, write_telling_layer,
)
from backend.pipeline.voice_repair import repair_voice
from backend.pipeline.formatters.briefing_formatter import render_briefing
from backend.pipeline.style_enforcer import lint_rendered_document

SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"
doc0 = json.load(open(f"{SCRATCH}/doc_0.json"))["data"]
doc2 = json.load(open(f"{SCRATCH}/doc_2.json"))["data"]
harvest = json.load(open(f"{SCRATCH}/harvest.json"))
sources = doc0["sources"]
titles = {s["source_id"]: s.get("title") for s in sources}

# Harvested facts become the key-point layer, one per fact, namespaced.
key_points = [
    {"key_point_id": f"F_{i}", "statement": fact, "source_ids": [sid], "confidence": "medium"}
    for sid, facts in harvest.items() for i, fact in enumerate(facts, 1)
]

def mine(text, cap=10):
    out=[]
    for sent in re.split(r"(?<=[.!?])\s+", text or ""):
        s=sent.strip()
        if not (40 < len(s) < 400): continue
        if re.search(r"\d", s) or len(re.findall(r"\b[A-Z][a-z]{3,}", s)) >= 3:
            out.append(s)
        if len(out) >= cap: break
    return out
specifics=[{"source_id": s["source_id"], "text": t} for s in sources for t in mine(s.get("full_text"))]

grade = confidence_ceiling_grade([ConfidenceLevel.HIGH]*len(sources), 0.0)
corpus = build_corpus(
    topic=doc0.get("topic") or "why modern films look the way they do",
    sources=sources, key_points=key_points,
    themes=doc2.get("themes",[]), tensions=doc2.get("tensions",[]),
    gaps=doc2.get("gaps",[]),
    semantic_core=(doc2.get("semantic_core") or {}).get("text"),
    verbatim_specifics=specifics,
)
known={s["source_id"] for s in sources}
print(f"corpus: {len(key_points)} facts in, {len(json.dumps(corpus)):,} chars")

t0=time.time()
graph, u1 = distill_corpus("fixture", corpus, grade, 0.0, known)
print(f"provenance: {len(graph.claims)} claims, {len(graph.story_goods)} story goods, {time.time()-t0:.0f}s")
full, u2 = write_telling_layer("fixture", graph, titles)
briefing = render_briefing(full, titles)
r = lint_rendered_document(briefing)
if not r.passes:
    full, stats = repair_voice("fixture", full)
    print("repair:", {k: stats[k] for k in ("offenders","applied","skipped")})
    briefing = render_briefing(full, titles)
    r = lint_rendered_document(briefing)

open(f"{SCRATCH}/BRIEFING-ENRICHED.md","w").write(briefing)
json.dump(full.model_dump(mode="json"), open(f"{SCRATCH}/fixture_graph_enriched.json","w"), indent=2)
cost=sum(x["cost"] for x in u1+u2)
print(f"final: {len(briefing):,} chars | lint {'PASS' if r.passes else 'FAIL '+str(r.errors[:1])} | ${cost:.2f}")

# density compare
old=open(f"{SCRATCH}/BRIEFING.md").read()
def density(t):
    w=len(t.split())
    return len(re.findall(r"\d[\d,.]*", t))/(w/1000), len(set(re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", t))), w
for name,t in (("OLD", old), ("ENRICHED", briefing)):
    n,e,w = density(t)
    print(f"{name}: {w} words | {n:.1f} numbers/1000w | {e} distinct named entities")
