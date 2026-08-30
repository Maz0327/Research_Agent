"""Seat 2 — GAP ANALYSIS: glm-5.3-flash vs gpt-5.4-mini, 3 runs each, packer inputs."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scratchpad.glm_bakeoff_lib import glm_client, atom_grounding
from backend.integrations.structured_client import get_structured_client
from backend.pipeline.prompts.semantic_synthesis_prompt import build_gap_identification_prompt

d1 = json.load(open(ROOT / "scratchpad/e2e_films/packer3_doc_1.json"))["data"]
d0 = json.load(open(ROOT / "scratchpad/e2e_films/packer3_doc_0.json"))["data"]
corpus = " ".join((s.get("full_text") or "") for s in d0["sources"])
manifest = [{"source_id": s["source_id"], "type": s.get("source_type"), "title": s.get("title"), "status": "ingested"} for s in d0["sources"]]
themes = d1.get("themes", []) or []
prompt = build_gap_identification_prompt(
    scope_lock=d1.get("scope_lock") or d0["topic"],
    source_manifest=manifest, key_points=d1["key_points"], themes=themes, tensions=d1.get("tensions", []))
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["gaps"],
          "properties": {"gaps": {"type": "array", "items": {"type": "object", "additionalProperties": False,
              "required": ["gap_description"], "properties": {
                  "gap_description": {"type": "string"}, "gap_type": {"type": "string"},
                  "suggested_direction": {"type": "string"}}}}}}
clients = {"glm-5.3-flash": glm_client(), "gpt-5.4-mini": get_structured_client("gpt-5.4-mini")}
out = {}
for model, client in clients.items():
    out[model] = []
    for run in range(3):
        t0 = time.time()
        result, _ = client.generate_structured(prompt=prompt, schema=SCHEMA,
            system="You identify research gaps. Ground every statement in the supplied material only.", max_tokens=16000)
        gaps = result.get("gaps", [])
        texts = [(g.get("gap_description") or "") + " " + (g.get("suggested_direction") or "") for g in gaps]
        total, missing, miss = atom_grounding(texts, corpus)
        pct = round(missing / total * 100, 1) if total else 0.0
        words = sum(len(t.split()) for t in texts)
        out[model].append({"gaps": len(gaps), "atoms": total, "ungrounded": missing, "pct": pct,
                           "words": words, "secs": round(time.time() - t0, 1), "missing_sample": miss[:4]})
        print(f"{model} run{run+1}: {len(gaps)} gaps · {missing}/{total} atoms ungrounded ({pct}%) · {words}w · {out[model][-1]['secs']}s")
json.dump(out, open(ROOT / "scratchpad/glm_seat2_results.json", "w"), indent=1)
