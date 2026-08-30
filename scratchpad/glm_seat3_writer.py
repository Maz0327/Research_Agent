"""Seat 3 — WRITER: glm-5.3-flash vs gpt-5.6-luna, 3 reads each, films sources."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scratchpad.glm_bakeoff_lib import glm_client, atom_grounding, density
from backend.integrations.structured_client import get_structured_client
from backend.pipeline.briefing_passes import run_read_pass

payload = json.load(open(ROOT / "scratchpad/e2e_films/sources.json"))
corpus = " ".join(s["full_text"] for s in payload["sources"])

def score(lede, paragraphs, secs, model, run):
    text = lede + " " + " ".join(p["text"] for p in paragraphs)
    words = len(text.split())
    total, missing, miss = atom_grounding([text], corpus)
    dens = density(text)
    row = {"words": words, "facts_delivered": dens, "per_100w": round(dens / words * 100, 1),
           "atoms": total, "ungrounded": missing, "pct": round(missing / total * 100, 1) if total else 0.0,
           "secs": round(secs, 0), "missing_sample": miss[:4]}
    print(f"{model} run{run}: {words}w · {dens} facts ({row['per_100w']}/100w) · "
          f"{missing}/{total} ungrounded ({row['pct']}%) · {secs:.0f}s")
    return row

out = {"gpt-5.6-luna": [], "glm-5.3-flash": []}
# luna run 1 = tonight's production Read, rescored with the same ruler
fr = json.load(open(ROOT / "scratchpad/e2e_films/films_read.json"))
out["gpt-5.6-luna"].append(score(fr["lede"], fr["paragraphs"], 0, "gpt-5.6-luna", "1(prod)"))

for model, client_f, runs in (("gpt-5.6-luna", lambda: get_structured_client("gpt-5.6-luna"), 2),
                              ("glm-5.3-flash", glm_client, 3)):
    for run in range(runs):
        t0 = time.time()
        read = run_read_pass(client_f(), payload["topic"], payload["sources"])
        paragraphs = [{"text": p.text} for p in read.paragraphs]
        out[model].append(score(read.lede, paragraphs, time.time() - t0, model, run + 2 if model == "gpt-5.6-luna" else run + 1))
json.dump(out, open(ROOT / "scratchpad/glm_seat3_results.json", "w"), indent=1)
