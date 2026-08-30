"""Seat 1 — HARVEST: glm-5.3-flash vs gpt-5.4-mini, same-day paired, D-034 substrate."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scratchpad.glm_bakeoff_lib import glm_client, atom_grounding
from backend.integrations.structured_client import get_structured_client
from backend.pipeline.stages.harvest_stage import harvest_source
from scratchpad.build_semantic_labeling_current_read import read_source_vault

sources = {s["source_id"]: s for s in read_source_vault(ROOT / "plans/260814-claim-graph-briefing/artifacts/hawara-run/hawara-vault.html")}
TRIO = ["SRC_8", "SRC_1", "SRC_16"]
clients = {"glm-5.3-flash": glm_client(), "gpt-5.4-mini": get_structured_client("gpt-5.4-mini")}
out = {}
for model, client in clients.items():
    out[model] = {}
    for sid in TRIO:
        s = sources[sid]; words = len(s["full_text"].split())
        t0 = time.time()
        facts, cost = harvest_source(client, sid, s.get("title") or sid, s["full_text"], mode="article_fetched", ceiling="HIGH")
        dt = time.time() - t0
        total, missing, miss_atoms = atom_grounding(facts, s["full_text"])
        out[model][sid] = {"facts": len(facts), "per_1k": round(len(facts) / words * 1000, 1),
                           "atoms": total, "ungrounded": missing,
                           "ungrounded_pct": round(missing / total * 100, 1) if total else 0.0,
                           "secs": round(dt, 1), "sample_missing": miss_atoms[:4]}
        print(f"{model} {sid}: {len(facts)} facts ({out[model][sid]['per_1k']}/1k) · "
              f"{missing}/{total} atoms ungrounded ({out[model][sid]['ungrounded_pct']}%) · {dt:.0f}s")
json.dump(out, open(ROOT / "scratchpad/glm_seat1_results.json", "w"), indent=1)
