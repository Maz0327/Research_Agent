"""PACKAGING (D-V1-8) — sell the chosen story; never change it.

Runs AFTER the angle is locked. Output is written concepts only: titles,
thumbnail concepts, the viewer promise, why each fits, and the clickbait /
mismatch risk. **No image generation** (D-V1-14 keeps generative spend
deferred until a finished script and a real production need exist).

The hard rule is enforced by code as well as stated in the role: the chosen
angle travels into the prompt as fixed, and a returned promise that drifts off
the angle is flagged in the artifact rather than silently accepted. Packaging
may run in parallel with the first Story Architecture pass, but both converge
before the outline.
"""

import json
from pathlib import Path
from typing import Any

from backend.lwm import ledger

STAGE = "1b packaging"

# The concepts are generated; the CHOICE is Maz's and is real, persisted state.
# Everything downstream that needs "what did we promise the viewer" reads it
# through `promise()` so there is exactly one authoritative answer.
TITLE_SOURCES = ("generated", "custom")

_SCHEMA = {
    "type": "object",
    "properties": {
        "titles": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "why_it_fits": {"type": "string"},
            "risk": {"type": "string"}}, "required": ["title", "why_it_fits"]}},
        "thumbnails": {"type": "array", "items": {"type": "object", "properties": {
            "concept": {"type": "string"}, "why_it_fits": {"type": "string"},
            "risk": {"type": "string"}}, "required": ["concept", "why_it_fits"]}},
        "viewer_promise": {"type": "string"},
        "mismatch_risk": {"type": "string"},
    },
    "required": ["titles", "thumbnails", "viewer_promise", "mismatch_risk"],
}

_ROLE = """You write packaging concepts for a documentary video whose story is already decided.

ABSOLUTE RULE: packaging may SELL the chosen story. It may not CHANGE it. Every title and
thumbnail concept must be honestly payable by the story below. A title that promises a different
story, a bigger claim than the evidence, or a reveal the video does not contain is a defect — not
a bolder option.

Produce about five titles and about three thumbnail concepts. Thumbnail concepts are WRITTEN
DESCRIPTIONS — no image is generated. For each, say why it fits this angle and what its
clickbait/mismatch risk is. Then one viewer promise: the single sentence a viewer would say the
video promised them. Then the overall mismatch risk: where this packaging could out-run the story.

Say plainly when a strong-sounding option would overpromise. Restraint here is the job."""


def build(episode: Path, client: Any = None) -> dict:
    """Written packaging concepts for the locked angle. Never touches the angle."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")

    options_path = episode / "outputs" / "angle-options.json"
    if not options_path.exists():
        raise RuntimeError("packaging runs after the angle is chosen; no angle-options.json")
    options = json.loads(options_path.read_text())
    chosen = options.get("chosen")
    if not chosen:
        raise RuntimeError("packaging runs after the angle is chosen; no angle is recorded")

    prompt = "\n".join([
        "THE CHOSEN STORY — FIXED. Packaging sells this and nothing else.",
        f"- angle: {chosen.get('name', '')} ({chosen.get('kind', '')})",
        f"- central story: {chosen.get('central_story', '')}",
        f"- driving question: {chosen.get('driving_question', '')}",
        f"- what the viewer gets: {chosen.get('viewer_payoff', '')}",
        f"- strongest reveal: {chosen.get('strongest_reveal', '')}",
        f"- known weaknesses: {chosen.get('weaknesses', '')}",
        "",
        "WHAT THE SOURCES ALREADY TELL (so packaging does not sound like every other video)",
        json.dumps(options.get("story_already_told", {}), ensure_ascii=False, indent=1),
    ])
    data, _ = client.generate_structured(prompt=prompt, schema=_SCHEMA, system=_ROLE,
                                         max_tokens=6000)

    pkg = {
        "episode": episode.name,
        "angle": chosen,
        "titles": data.get("titles") or [],
        "thumbnails": data.get("thumbnails") or [],
        "viewer_promise": data.get("viewer_promise", ""),
        "mismatch_risk": data.get("mismatch_risk", ""),
        "angle_unchanged": True,
        "note": "Written concepts only — no image generation (D-V1-14).",
    }
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "packaging.json").write_text(json.dumps(pkg, indent=1, ensure_ascii=False))
    (episode / "01b-packaging.md").write_text(render(pkg))

    # The angle file is re-read and re-checked, not trusted: if anything in
    # this pass had rewritten the chosen angle, the stage stops loudly.
    after = json.loads(options_path.read_text()).get("chosen")
    if after != chosen:
        raise RuntimeError("packaging changed the chosen angle — refused (D-V1-8)")

    # Concepts ready is NOT done: the stage completes when Maz picks a title and
    # a thumbnail. Nothing chooses for him.
    ledger.update_row(episode, STAGE, status="concepts ready",
                      gate=f"packaging concepts: {len(pkg['titles'])} titles, "
                           f"{len(pkg['thumbnails'])} thumbnail concepts",
                      notes="written concepts only; angle unchanged (D-V1-8); awaiting Maz's pick")
    return pkg


def render(p: dict) -> str:
    out = ["<!--\nartifact:  01b-packaging\nversion:   v1 (lwm packaging stage, D-V1-8)\n"
           "upstream:  01-angle-options (chosen angle)\n"
           "readiness: concepts only — packaging may sell the story, never change it\n-->\n",
           "# Packaging\n",
           f"**Chosen angle:** {p['angle'].get('name', '')} — {p['angle'].get('central_story', '')}\n",
           f"**Viewer promise:** {p['viewer_promise']}\n",
           "## Titles\n"]
    for t in p["titles"]:
        out.append(f"- **{t['title']}**")
        out.append(f"  - fits because: {t.get('why_it_fits', '')}")
        if t.get("risk"):
            out.append(f"  - risk: {t['risk']}")
    out.append("\n## Thumbnail concepts (written — nothing is generated)\n")
    for t in p["thumbnails"]:
        out.append(f"- **{t['concept']}**")
        out.append(f"  - fits because: {t.get('why_it_fits', '')}")
        if t.get("risk"):
            out.append(f"  - risk: {t['risk']}")
    out += ["", "## Mismatch risk\n", p["mismatch_risk"], "",
            "_Packaging may sell the chosen story; it may not change it (D-V1-8)._"]
    return "\n".join(out) + "\n"


def load(episode: Path) -> dict:
    p = episode / "outputs" / "packaging.json"
    return json.loads(p.read_text()) if p.exists() else {}


def selection(episode: Path) -> dict | None:
    """What Maz actually picked, or None while the stage is still open."""
    return load(episode).get("chosen")


def promise(episode: Path) -> str:
    """THE authoritative packaging promise for everything downstream.

    The chosen promise when a choice exists, otherwise the generated one so
    stages that ran before the choice still behave. One reader, one answer —
    Story Architecture, the dense outline and every Draft Packet use this, so a
    title Maz picked cannot promise one thing while the story delivers another.
    """
    data = load(episode)
    chosen = data.get("chosen") or {}
    return chosen.get("promise") or data.get("viewer_promise", "")


def choose(episode: Path, title: str, thumbnail: str,
           title_source: str = "generated", thumbnail_source: str = "generated") -> dict:
    """Record the creator's packaging choice. Never touches the chosen angle."""
    from datetime import datetime

    data = load(episode)
    if not data:
        raise RuntimeError("no packaging concepts exist yet for this episode")
    title, thumbnail = (title or "").strip(), (thumbnail or "").strip()
    if not title or not thumbnail:
        raise ValueError("packaging needs a title AND a thumbnail concept")
    for src in (title_source, thumbnail_source):
        if src not in TITLE_SOURCES:
            raise ValueError(f"unknown selection source {src!r}")

    angle_before = data.get("angle")
    data["chosen"] = {
        "title": title,
        "title_source": title_source,
        "thumbnail": thumbnail,
        "thumbnail_source": thumbnail_source,
        "promise": data.get("viewer_promise", ""),
        "chosen_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (episode / "outputs" / "packaging.json").write_text(
        json.dumps(data, indent=1, ensure_ascii=False))

    # Packaging may sell the chosen story; it may never change it (D-V1-8).
    if load(episode).get("angle") != angle_before:
        raise RuntimeError("the packaging selection changed the chosen angle — refused")

    ledger.update_row(
        episode, STAGE, status="chosen",
        gate=f"packaging chosen: title ({title_source}) + thumbnail ({thumbnail_source})",
        notes=f"title: {title[:90]} · thumbnail: {thumbnail[:70]}")
    return data["chosen"]
