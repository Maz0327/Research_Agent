"""MOVEMENT DRAFT PACKETS (§6, §7) — scoped context, not a dump and not a slice.

The verified defect this replaces: `writing.py` fed the drafter documents cut
at arbitrary character counts (`[:8000]`, `[:20000]`, `[:60000]`) and never
gave it Brief material at all. First-N-character truncation is exactly what the
context-engineering work found harmful — it keeps whatever happens to be at the
top of a file and silently drops the rest, including the wording constraints
that stop a claim drifting.

A Draft Packet is assembled from structure instead: the movement's own outline
entry, the exact registry rows that movement resolves, the exact Brief material
those rows come from, the chosen angle, the packaging promise, the relevant
architecture decisions, continuity from the previous movement, a small positive
writer cargo, and a few voice examples.

**The Freemasons lesson is the invariant:** fact + evidence status + allowed
wording + prohibited wording travel TOGETHER at every handoff. A packet that
carries a claim without its wording is a defect, and `missing_wording` reports
it rather than hiding it.
"""

import json
import re
from pathlib import Path

from backend.lwm import paths, registry

# Voice examples are exemplars, not a corpus dump: a handful of Maz's own
# lines does the job, and the rest is noise in a drafting prompt.
VOICE_EXAMPLES = 6


def _outline(episode: Path) -> dict:
    p = episode / "outputs" / "outline.json"
    if not p.exists():
        raise RuntimeError("no dense outline — draft packets are built from it")
    return json.loads(p.read_text())


def _voice_examples(n: int = VOICE_EXAMPLES) -> list[str]:
    """Tier-1 exemplars from the corpus — Maz's hands only, a few of them."""
    p = paths.pipeline_dir() / "MAZ-VOICE-CORPUS.md"
    if not p.exists():
        return []
    blocks = [b.strip() for b in re.split(r"\n(?=[->#])", p.read_text()) if b.strip()]
    quotes = [b for b in blocks if b.startswith(">")]
    return (quotes or blocks)[:n]


def _brief_material(episode: Path, rows: list[dict], movement: dict) -> list[str]:
    """The Brief's own statements behind this movement's rows.

    Selected by matching the registry claim against the research key points —
    the drafter has never received Brief material at all, which is how a
    movement ends up 'told' from an outline line and nothing else.
    """
    from backend.lwm import angle as _angle

    pack = _angle.evidence_pack(episode)
    wanted = {r["claim"].strip().lower() for r in rows}
    out = []
    for k in pack["key_points"]:
        s = (k["statement"] or "").strip()
        if s.lower() in wanted:
            out.append(f"[{k['id']}] {s}")
    # Tensions and disputes that touch this movement's material stay attached:
    # contested ground must never arrive at a drafter stripped of its dispute.
    tokens = set()
    for r in rows:
        tokens |= {w for w in re.findall(r"[A-Za-z']{4,}", r["claim"].lower())}
    for t in pack["tensions"]:
        d = t["description"] or ""
        if len(tokens & {w for w in re.findall(r"[A-Za-z']{4,}", d.lower())}) >= 4:
            out.append(f"[tension] {d}")
    for dsp in pack["disputes"]:
        c = dsp["claim"] or ""
        if len(tokens & {w for w in re.findall(r"[A-Za-z']{4,}", c.lower())}) >= 3:
            out.append(f"[dispute] {c} — {dsp['holders']}")
    for item in (movement.get("brief_references") or []):
        out.append(f"[outline reference] {item}")
    return out


def build(episode: Path, movement: int) -> dict:
    """The packet for one movement. Raises if the movement is THIN (§7)."""
    o = _outline(episode)
    m = next((x for x in o["movements"] if int(x.get("n", 0)) == movement), None)
    if m is None:
        raise KeyError(f"movement {movement} is not in the outline")
    if m["coverage"] == "THIN":
        raise ThinMovement(movement, m.get("missing_material") or [],
                           m.get("coverage_code_reason", ""))

    rows_by_n = {int(r["n"]): r for r in registry.read_table(episode)}
    rows = [rows_by_n[int(n)] for n in (m.get("registry_claim_ids") or [])
            if int(n) in rows_by_n]

    angle_path = episode / "outputs" / "angle-options.json"
    chosen = json.loads(angle_path.read_text()).get("chosen") if angle_path.exists() else None
    from backend.lwm import packaging as _packaging
    promise = _packaging.promise(episode)          # the CHOSEN promise when one exists
    packaging_title = (_packaging.selection(episode) or {}).get("title", "")
    arch_path = episode / "outputs" / "story-architecture.json"
    arch = json.loads(arch_path.read_text()) if arch_path.exists() else {}
    arch_movement = next((a for a in (arch.get("movements") or [])
                          if int(a.get("n", 0)) == movement), {})

    # Continuity: the previous movement's closing lines, so the seam holds.
    draft = episode / "07-draft.md"
    continuity = ""
    if draft.exists() and movement > 1:
        blocks = re.split(r"^## Movement (\d+)\s*$", draft.read_text(), flags=re.M)
        for i in range(1, len(blocks) - 1, 2):
            if int(blocks[i]) == movement - 1:
                tail = blocks[i + 1].strip().splitlines()
                continuity = "\n".join(tail[-6:])

    missing_wording = [int(r["n"]) for r in rows
                       if r["allowed"] in ("", "—") and r["status"] != "REPORTED"]

    packet = {
        "movement": movement,
        "coverage": m["coverage"],
        "precision_constraints": ([m["coverage_code_reason"]]
                                  if m["coverage"] == "PRECISION-RISK" else []),
        "angle": chosen,
        "packaging_promise": promise,
        "packaging_title": packaging_title,
        "architecture": {k: arch_movement.get(k) for k in
                         ("story_job", "audience_state_entering", "what_changes",
                          "scene_or_explanation", "evidence_placement", "setup_or_payoff",
                          "forward_pull") if arch_movement.get(k)},
        "outline": {k: m.get(k) for k in
                    ("story_job", "audience_state_entering", "what_changes", "events",
                     "names", "dates", "actions", "documents", "numbers", "quotes",
                     "contradictions", "setup_payoff_reveal", "forward_pull")
                    if m.get(k)},
        "facts": [{"row": int(r["n"]), "claim": r["claim"], "class": r["class"],
                   "status": r["status"], "source": r["source"], "load_bearing": r["lb"] == "y",
                   "allowed_wording": r["allowed"], "prohibited_wording": r["prohibited"],
                   "anchor": r["anchor"]}
                  for r in rows],
        "brief_material": _brief_material(episode, rows, m),
        "continuity_from_previous": continuity,
        "voice_examples": _voice_examples(),
        "missing_wording_rows": missing_wording,
    }
    (episode / "outputs" / "packets").mkdir(parents=True, exist_ok=True)
    (episode / "outputs" / "packets" / f"movement-{movement}.json").write_text(
        json.dumps(packet, indent=1, ensure_ascii=False))
    return packet


class ThinMovement(RuntimeError):
    """A THIN movement never reaches the writer (§7). It gets backfilled."""

    def __init__(self, movement: int, missing: list[str], reason: str):
        self.movement = movement
        self.missing = missing
        self.reason = reason
        super().__init__(f"movement {movement} is THIN and must not be drafted: {reason}. "
                         f"Missing: {'; '.join(missing) or '(unnamed)'}")


def render_prompt(packet: dict, rules: str) -> str:
    """The drafter's cargo — everything scoped, nothing sliced.

    Positive writing cargo only (§8, D-V1-11): the writer gets story, evidence,
    structure and voice examples. The regex bank, the pathology inventory and
    the reviewer rule walls run AFTER drafting, not in the writer's head.
    """
    p = packet
    out = ["RULES (the writer's card, whole)", rules, ""]
    if p.get("angle"):
        out += ["THE STORY WE CHOSE TO TELL",
                f"- {p['angle'].get('central_story', '')}",
                f"- the question it answers: {p['angle'].get('driving_question', '')}",
                f"- what the viewer gets: {p['angle'].get('viewer_payoff', '')}", ""]
    if p.get("packaging_promise"):
        out += [f"THE PROMISE THIS VIDEO MADE ITS VIEWER: {p['packaging_promise']}"]
        if p.get("packaging_title"):
            out.append(f"(it goes out titled: {p['packaging_title']})")
        out.append("")
    if p.get("architecture"):
        out += ["THIS MOVEMENT'S JOB IN THE STRUCTURE"]
        out += [f"- {k.replace('_', ' ')}: {v}" for k, v in p["architecture"].items()]
        out.append("")
    o = p["outline"]
    out += [f"MOVEMENT {p['movement']} — WHAT HAPPENS"]
    for key in ("events", "actions"):
        out += [f"- {e}" for e in (o.get(key) or [])]
    for label, key in [("Names", "names"), ("Dates", "dates"), ("Documents", "documents"),
                       ("Numbers", "numbers"), ("Quotes you may use", "quotes")]:
        if o.get(key):
            out.append(f"{label}: " + " · ".join(str(x) for x in o[key]))
    if o.get("contradictions"):
        out += ["Contradictions and uncertainty that must survive the telling:"]
        out += [f"- {c}" for c in o["contradictions"]]
    if o.get("forward_pull"):
        out.append(f"Leave the listener wanting: {o['forward_pull']}")
    out.append("")

    out += ["THE FACTS, WITH THE WORDING THAT TRAVELS WITH THEM",
            "(say = the certainty you may claim · never = the overstatement)"]
    for f in p["facts"]:
        lb = " [LOAD-BEARING]" if f["load_bearing"] else ""
        out.append(f"- row {f['row']}{lb} ({f['status']}, {f['class'] or '—'}, src {f['source']}): "
                   f"{f['claim']}")
        out.append(f"    say: {f['allowed_wording'] or '—'}")
        out.append(f"    never: {f['prohibited_wording'] or '—'}")
        if f["anchor"] and f["anchor"] != "—":
            out.append(f"    the only comparison you may voice here: {f['anchor']}")
    out.append("")
    if p["brief_material"]:
        out += ["THE RESEARCH BEHIND THOSE FACTS"] + [f"- {b}" for b in p["brief_material"]] + [""]
    if p["precision_constraints"]:
        out += ["PRECISION RISK IN THIS MOVEMENT — exact wording is load-bearing:"]
        out += [f"- {c}" for c in p["precision_constraints"]] + [""]
    if p["continuity_from_previous"]:
        out += ["HOW THE PREVIOUS MOVEMENT ENDED (hold the seam)",
                p["continuity_from_previous"], ""]
    if p["voice_examples"]:
        out += ["HOW HE SOUNDS (a few of his own lines — imitate the ease, not the words)"]
        out += p["voice_examples"] + [""]
    out.append(f"Draft MOVEMENT {p['movement']} only. Tell it naturally.")
    return "\n".join(out)
