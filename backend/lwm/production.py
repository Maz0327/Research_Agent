"""Stage 11 — the production package, from the locked script and the registry.

Deterministic: everything here derives from artifacts that already exist
(script, registry, manifest), the ammo-cards way — claims ledger sorted by
confidence, per-beat cue cards carrying load-bearing facts and their anchors,
an asset checklist where the intake manifest's user-supplied material appears
as available assets and everything else is an explicit TODO rather than a
failure. Missing assets never block the package.

Readiness patch §18 — beat-level asset intelligence restored. Every beat now
carries its visual need classified REAL / FACE / AI-GAP under the REAL-FIRST
rule: if a thing can be shown with real footage, documents, images, interviews
or press, real material comes first. AI reconstruction is for genuine visual
gaps only — what no camera could have captured, or historical depictions that
do not exist. Nothing here generates anything: no Higgsfield calls, no AI video
spend, no Resolve assembly (D-V1-14). It writes the shopping list.
"""

import json
import re
from datetime import date
from pathlib import Path

from backend.lwm import ledger, manifest


def _beats(script: str) -> list[dict]:
    """Split the script into beats: movement/heading blocks, else paragraph runs."""
    parts = re.split(r"\n(?=#{1,3} )", script)
    if len(parts) > 1:
        beats = []
        for part in parts:
            lines = part.strip().splitlines()
            if not lines:
                continue
            title = lines[0].lstrip("# ").strip() if lines[0].startswith("#") else f"Beat {len(beats)+1}"
            beats.append({"title": title, "text": "\n".join(lines[1:]).strip() or lines[0]})
        return beats
    paras = [p.strip() for p in script.split("\n\n") if p.strip()]
    return [{"title": f"Beat {i+1}", "text": "\n".join(paras[i*4:(i+1)*4])}
            for i in range((len(paras) + 3) // 4)]


def _registry_rows(episode: Path) -> list[dict]:
    p = episode / "04-sources-registry.md"
    rows = []
    if not p.exists():
        return rows
    for line in p.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) == 9 and cells[0] not in ("#", "---"):
            rows.append(dict(zip(
                ("n", "claim", "class", "status", "source", "lb", "allowed", "prohibited", "anchor"),
                cells, strict=True)))
    return rows


def _overlap(a: str, b: str) -> int:
    from backend.pipeline.text_similarity import content_tokens
    return len(content_tokens(a) & content_tokens(b))


# What kind of coverage a beat needs. REAL-FIRST is the rule, not a preference.
VISUAL_CLASSES = ("REAL", "FACE", "AI-GAP")

# A beat whose material predates photography, or is an interior/imagined
# moment, is the honest AI-GAP case. Everything else starts as REAL.
_NO_CAMERA = re.compile(
    r"\b(1[0-8]\d{2}|thought|imagin|dream|inside his head|what he saw|"
    r"must have (?:felt|seen|thought))\b", re.I)
_DOCUMENTARY = re.compile(
    r"\b(document|letter|report|transcript|record|affidavit|ledger|map|"
    r"newspaper|headline|photograph|photo|court|trial|testimony|census|"
    r"telegram|diary|deposition|verdict|indictment)\b", re.I)
_PERSON_TO_CAMERA = re.compile(
    r"\b(i |i'm|i've|my |we |let me|here'?s what|look,|honestly|so —|"
    r"the thing is)\b", re.I)


def classify_visual(beat_text: str, claims: list[dict], sources: list[dict]) -> dict:
    """REAL / FACE / AI-GAP for one beat, REAL-FIRST.

    Deterministic and conservative: a beat is only AI-GAP when the material
    plainly could not have been photographed and no real asset covers it. When
    in doubt it is REAL, because the rule is to look for real material first
    and the cost of a wrong REAL is a search, while the cost of a wrong AI-GAP
    is generated footage nobody needed.
    """
    documentary = bool(_DOCUMENTARY.search(beat_text)) or any(
        _DOCUMENTARY.search(c.get("claim", "")) for c in claims)
    no_camera = bool(_NO_CAMERA.search(beat_text)) and not documentary
    narrator = bool(_PERSON_TO_CAMERA.search(beat_text))

    if documentary:
        cls, why = "REAL", "documents/records named here — show the real thing"
    elif no_camera:
        cls, why = ("AI-GAP",
                    "nothing here could have been photographed; reconstruction is the honest "
                    "option, and only for this")
    elif narrator:
        cls, why = "FACE", "narrator-led beat — Maz on camera carries it"
    else:
        cls, why = "REAL", "REAL-FIRST: archival/press/stills before anything is generated"

    searches = []
    for c in claims[:4]:
        claim = c.get("claim", "")
        if claim:
            searches.append(claim[:110])
    return {"class": cls, "why": why, "search_tasks": searches}


def build(episode: Path, script_path: Path) -> dict:
    script = script_path.read_text()
    rows = _registry_rows(episode)
    beats = _beats(script)
    data = manifest.load(episode)

    # Claims that actually appear in the script, by beat.
    for beat in beats:
        matched = sorted(rows, key=lambda r: -_overlap(r["claim"], beat["text"]))
        beat["claims"] = [r for r in matched if _overlap(r["claim"], beat["text"]) >= 4][:6]

    lb_rows = [r for r in rows if r.get("lb") == "y"]
    assets_available = [
        {"id": s["id"], "type": s["type"], "title": s.get("title"),
         "ref": s.get("canonical") or s.get("preserved_path"),
         "note": "user-supplied — candidate footage/reference" if s["type"] in ("youtube", "image", "file") else "reference"}
        for s in data["sources"]
    ]

    fc = episode / "10b-fact-check.json"
    fact_check = json.loads(fc.read_text()) if fc.exists() else None

    beat_packets = []
    for b in beats:
        visual = classify_visual(b["text"], b["claims"], data["sources"])
        anchor_claim = b["claims"][0]["claim"] if b["claims"] else ""
        candidates = [a for a in assets_available if a["type"] in ("youtube", "image", "file")]
        beat_packets.append({
            "title": b["title"],
            "cue_card": {
                "load_bearing": [{"claim": r["claim"], "allowed": r["allowed"],
                                  "prohibited": r["prohibited"], "anchor": r["anchor"],
                                  "source": r["source"]}
                                 for r in b["claims"] if r.get("lb") == "y"],
                "anchors": [r["anchor"] for r in b["claims"]
                            if r.get("anchor") and r["anchor"] != "—"],
            },
            "visual": {
                "class": visual["class"],
                "need": visual["why"],
                "real_first": visual["class"] != "AI-GAP",
                "supplied_assets": [a["id"] for a in candidates],
                "video_segment": next((a["ref"] for a in candidates if a["type"] == "youtube"), None),
                "image_or_document_candidate": (
                    "the documents named in this beat — source page, scan or press image"
                    if visual["class"] == "REAL" and _DOCUMENTARY.search(b["text"]) else None),
                "archival_candidate": ("period photography / newsreel / press for this beat"
                                       if visual["class"] == "REAL" else None),
                "search_tasks": visual["search_tasks"],
                "licence_note": "check rights before use — none cleared automatically",
                "factual_anchor": anchor_claim,
            },
            # Kept for compatibility with anything reading the v1 shape.
            "visual_needs": [f"{visual['class']} — {visual['why']}"],
            "matched_assets": [a["id"] for a in assets_available
                               if a["type"] in ("youtube", "image")],
        })

    package = {
        "script": {"path": str(script_path), "words": len(script.split()),
                   "sha": __import__("hashlib").sha256(script.encode()).hexdigest()[:12]},
        "beats": beat_packets,
        "claims_ledger": rows,
        "load_bearing": lb_rows,
        "assets": {"available": assets_available,
                   "missing": sorted({t for b in beat_packets for t in b["visual"]["search_tasks"]}),
                   "rule": "REAL-FIRST — real footage/documents/images/interviews/press before "
                           "any reconstruction; AI only for genuine visual gaps"},
        "visual_summary": {c: sum(1 for b in beat_packets if b["visual"]["class"] == c)
                           for c in VISUAL_CLASSES},
        "generation": "NONE — no image/video generation, no AI spend, no assembly (D-V1-14)",
        "fact_check": ({"counts": fact_check["counts"],
                        "material_findings": fact_check["material_findings"]}
                       if fact_check else "not run"),
        "assembly": "governed by content-pipeline/PRODUCTION-ASSEMBLY-PIPELINE.md",
        "generated": str(date.today()),
    }

    (episode / "editing").mkdir(exist_ok=True)
    (episode / "editing" / "production-package.json").write_text(
        json.dumps(package, indent=1, ensure_ascii=False))
    (episode / "11-production-package.md").write_text(_render_md(package))
    v = package["visual_summary"]
    ledger.update_row(episode, "11 production package", status="done",
                      notes=f"generated by lwm from {script_path.name} "
                            f"({package['script']['sha']}); {len(beats)} beats, "
                            f"{len(lb_rows)} load-bearing claims; visuals "
                            f"{v['REAL']} REAL / {v['FACE']} FACE / {v['AI-GAP']} AI-GAP")
    return package


def _render_md(pkg: dict) -> str:
    v = pkg["visual_summary"]
    out = [
        "<!--\nartifact:  11-production-package\nversion:   v2 (generated by lwm)\nreadiness: complete\n-->\n",
        "# Production package\n",
        f"Script: `{pkg['script']['path']}` · {pkg['script']['words']} words · version `{pkg['script']['sha']}`",
        f"Fact-check: {pkg['fact_check'] if isinstance(pkg['fact_check'], str) else 'run — ' + json.dumps(pkg['fact_check']['counts'])}",
        f"Assembly: {pkg['assembly']}",
        f"Generation: {pkg['generation']}",
        f"\nVisuals: **{v['REAL']} REAL · {v['FACE']} FACE · {v['AI-GAP']} AI-GAP** — {pkg['assets']['rule']}\n",
        "## Cue / ammo cards — at the mic\n",
    ]
    for b in pkg["beats"]:
        vis = b["visual"]
        out.append(f"### {b['title']}   [{vis['class']}]")
        for c in b["cue_card"]["load_bearing"]:
            out.append(f"- **LB** {c['claim']}\n  - say: {c['allowed'] or '—'} · never: {c['prohibited'] or '—'}"
                       f"\n  - anchor: {c['anchor']} · source: {c['source']}")
        if b["cue_card"]["anchors"]:
            out.append(f"- anchors in play: {' · '.join(b['cue_card']['anchors'])}")
        out.append(f"- **visual need:** {vis['need']}")
        if vis["factual_anchor"]:
            out.append(f"- factual anchor: {vis['factual_anchor']}")
        if vis["video_segment"]:
            out.append(f"- supplied video: {vis['video_segment']}")
        if vis["image_or_document_candidate"]:
            out.append(f"- document/image candidate: {vis['image_or_document_candidate']}")
        if vis["archival_candidate"]:
            out.append(f"- archival candidate: {vis['archival_candidate']}")
        if vis["supplied_assets"]:
            out.append(f"- supplied assets in play: {', '.join(vis['supplied_assets'])}")
        for task in vis["search_tasks"]:
            out.append(f"- ⬜ find: {task}")
        out.append(f"- rights: {vis['licence_note']}")
        out.append("")
    out.append("## Asset inventory\n")
    for a in pkg["assets"]["available"]:
        out.append(f"- [{a['id']}] {a['type']}: {a['title'] or a['ref']} — {a['note']}")
    if not pkg["assets"]["available"]:
        out.append("- (none supplied — everything below is a sourcing task)")
    out.append("\n### Still to find\n")
    for m in pkg["assets"]["missing"]:
        out.append(f"- ⬜ {m}")
    out.append(f"\n## Claims ledger — {len(pkg['claims_ledger'])} rows, {len(pkg['load_bearing'])} load-bearing\n")
    out.append("Full table in `04-sources-registry.md`; machine copy in `editing/production-package.json`.")
    return "\n".join(out) + "\n"
