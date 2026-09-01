"""STORY ARCHITECTURE (D-V1-9, D-V1-10) — how the chosen story gets told.

ANGLE decided *what* story. This decides *how*: macro shape and narrative
construction. It is a separate pass from writing, because the load-bearing
craft conclusion from the old work is that a writer forced to reason about
arcs and payoff mechanics *while* producing prose does neither well — and the
cleverness belongs in the structure, not in the sentences.

Boundary, enforced here and checked by code: architecture makes STRUCTURAL
decisions. It never dictates sentence-level prose, jokes, vocabulary or
rhythm, and it never writes a line a drafter could lift. The library it draws
on (`pipeline/STORY-ARCHITECTURE-LIBRARY.md`) is a menu of techniques, not a
set of mandates; the retired universal doctrines stay retired.
"""

import json
import re
from pathlib import Path
from typing import Any

from backend.lwm import ledger, paths

STAGE = "4c story architecture"

# Macro shapes are TOOLS, not templates (D-V1-9). No shape is mandatory and
# none is the house style.
MACRO_SHAPES = ("chronological", "investigation", "contradiction", "mystery", "character",
                "dual timeline", "escalation", "misconception/reversal", "hybrid")

_MOVEMENT = {
    "type": "object",
    "properties": {
        "n": {"type": "integer"},
        "story_job": {"type": "string"},
        "audience_state_entering": {"type": "string"},
        "what_changes": {"type": "string"},
        "material": {"type": "array", "items": {"type": "string"}},
        "scene_or_explanation": {"type": "string"},
        "evidence_placement": {"type": "string"},
        "setup_or_payoff": {"type": "string"},
        "forward_pull": {"type": "string"},
    },
    "required": ["n", "story_job", "what_changes"],
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "macro_shape": {"type": "string"},
        "why_this_shape": {"type": "string"},
        "audience_belief_entering": {"type": "string"},
        "what_changes_that_belief": {"type": "string"},
        "information_order_rationale": {"type": "string"},
        "movements": {"type": "array", "items": _MOVEMENT},
        "legitimate_withholding": {"type": "string"},
        "human_stakes": {"type": "string"},
        "ending": {"type": "string"},
        "unresolved_uncertainty": {"type": "string"},
        "compressed_vs_full_scene": {"type": "string"},
        "techniques_used": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["macro_shape", "why_this_shape", "audience_belief_entering",
                 "what_changes_that_belief", "movements", "ending"],
}

_ROLE = """You decide the ARCHITECTURE of a documentary video whose story is already chosen.

You decide STRUCTURE ONLY: macro shape, what the audience believes coming in and what changes it,
the order information is released, where evidence lands, what earns a full scene and what is
compressed, where something is legitimately withheld, forward pull between sections, human stakes,
the ending, and what stays unresolved.

You must NOT write narration, prose, jokes, phrasings, vocabulary or rhythm. Never write a
sentence a drafter could lift into the script. Describe what happens and what it does to the
viewer, in plain working language.

The macro shapes available are TOOLS, not templates: chronological · investigation · contradiction
· mystery · character · dual timeline · escalation · misconception/reversal · hybrid. Choose the
one this story actually wants and say why. There is no house shape.

The technique library offered to you is a MENU. Use what serves this story; ignore the rest.
Explicitly retired as universal law and not to be applied by default: Story Circle, the
destabilization ladder, "every beat must be bigger", mandatory biggest-reveal-last, narrative debt
ledgers, payoff percentages, giant reveal formulas.

The creator's own structure decisions, where present, are LAW. Build around them."""


def _library() -> str:
    p = paths.pipeline_dir() / "STORY-ARCHITECTURE-LIBRARY.md"
    return p.read_text() if p.exists() else ""


def _structure_decisions(episode: Path) -> str:
    """Maz's own structure decisions from the DECISION LOG, if he held the session."""
    p = episode / "DECISION-LOG.md"
    if not p.exists():
        return ""
    blocks = re.split(r"\n## ", p.read_text())
    hits = [b for b in blocks if b.startswith(tuple("0123456789")) and "TOUCHPOINT B" in b]
    return hits[-1] if hits else ""


_LIFTABLE = re.compile(r"[“\"]([^”\"]{80,})[”\"]")


def liftable_prose(arch: dict) -> list[str]:
    """Quoted runs long enough to be lifted into a draft. The pilot proved
    outline prose leaks into drafts; the same applies here."""
    found = []
    for match in _LIFTABLE.finditer(json.dumps(arch, ensure_ascii=False)):
        text = match.group(1)
        if len(text.split()) >= 12:
            found.append(text[:120])
    return found


def build(episode: Path, client: Any = None) -> dict:
    """The architecture pass. Structure only; no prose; no writing."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")

    options_path = episode / "outputs" / "angle-options.json"
    if not options_path.exists():
        raise RuntimeError("story architecture runs after the angle is chosen")
    options = json.loads(options_path.read_text())
    chosen = options.get("chosen")
    if not chosen:
        raise RuntimeError("story architecture runs after the angle is chosen")

    pkg_path = episode / "outputs" / "packaging.json"
    promise = json.loads(pkg_path.read_text()).get("viewer_promise", "") if pkg_path.exists() else ""

    from backend.lwm import angle as _angle
    pack = _angle.evidence_pack(episode)
    decisions_text = _structure_decisions(episode)

    prompt = "\n".join([
        "THE CHOSEN STORY (fixed)",
        json.dumps(chosen, ensure_ascii=False, indent=1),
        "",
        f"THE PACKAGING PROMISE THE STRUCTURE MUST PAY: {promise or '(packaging not run yet)'}",
        "",
        "THE CREATOR'S OWN STRUCTURE DECISIONS — LAW WHERE PRESENT",
        decisions_text or "(none recorded — he waived the session; use the material's own strongest order)",
        "",
        "TECHNIQUE LIBRARY (a menu, not mandates)",
        _library(),
        "",
        f"MATERIAL — KEY POINTS ({len(pack['key_points'])})",
        *[f"- [{k['id']}] {k['statement']}" for k in pack["key_points"]],
        "",
        "DISAGREEMENTS AND CONTESTED GROUND",
        *[f"- {t['description']}" for t in pack["tensions"]],
        *[f"- {d['claim']} — {d['holders']}" for d in pack["disputes"]],
        "",
        "WHAT THE RESEARCH COULD NOT ESTABLISH (candidates for honest unresolved endings)",
        *[f"- {g}" for g in pack["gaps"]],
    ])
    data, _ = client.generate_structured(prompt=prompt, schema=_SCHEMA, system=_ROLE,
                                         max_tokens=10000)

    shape = (data.get("macro_shape") or "").strip().lower()
    arch = {
        "episode": episode.name,
        "angle": chosen,
        "packaging_promise": promise,
        "structure_session": "held" if decisions_text else "waived",
        "macro_shape": data.get("macro_shape", ""),
        "macro_shape_known": shape in MACRO_SHAPES,
        "why_this_shape": data.get("why_this_shape", ""),
        "audience_belief_entering": data.get("audience_belief_entering", ""),
        "what_changes_that_belief": data.get("what_changes_that_belief", ""),
        "information_order_rationale": data.get("information_order_rationale", ""),
        "movements": data.get("movements") or [],
        "legitimate_withholding": data.get("legitimate_withholding", ""),
        "human_stakes": data.get("human_stakes", ""),
        "ending": data.get("ending", ""),
        "unresolved_uncertainty": data.get("unresolved_uncertainty", ""),
        "compressed_vs_full_scene": data.get("compressed_vs_full_scene", ""),
        "techniques_used": data.get("techniques_used") or [],
    }
    arch["liftable_prose"] = liftable_prose(arch)

    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "story-architecture.json").write_text(
        json.dumps(arch, indent=1, ensure_ascii=False))
    (episode / "04c-story-architecture.md").write_text(render(arch))
    ledger.update_row(episode, STAGE, status="done",
                      gate=f"architecture recorded: {arch['macro_shape'] or '—'} "
                           f"({len(arch['movements'])} movements)",
                      notes="structure decisions only — no prose"
                            + ("" if not arch["liftable_prose"]
                               else f"; {len(arch['liftable_prose'])} liftable passage(s) flagged"))
    return arch


def render(a: dict) -> str:
    out = ["<!--\nartifact:  04c-story-architecture\nversion:   v1 (lwm architecture pass, D-V1-9)\n"
           "upstream:  01-angle-options (chosen) · 01b-packaging · 04b-briefing\n"
           "readiness: structure decisions only — never prose, never narration\n-->\n",
           "# Story architecture\n",
           f"**Story:** {a['angle'].get('central_story', '')}\n",
           f"**Macro shape:** {a['macro_shape']}"
           + ("" if a["macro_shape_known"] else " _(not one of the library's shapes — read it carefully)_"),
           f"\n{a['why_this_shape']}\n",
           f"**Structure session:** {a['structure_session']}\n",
           "## What changes for the viewer\n",
           f"- **Believes coming in:** {a['audience_belief_entering']}",
           f"- **What changes it:** {a['what_changes_that_belief']}",
           f"- **Why this information order:** {a['information_order_rationale']}\n",
           "## Movements\n"]
    for m in a["movements"]:
        out.append(f"### Movement {m.get('n', '?')} — {m.get('story_job', '')}")
        for label, key in [("Audience state entering", "audience_state_entering"),
                           ("What changes", "what_changes"),
                           ("Scene or explanation", "scene_or_explanation"),
                           ("Evidence placement", "evidence_placement"),
                           ("Setup / payoff", "setup_or_payoff"),
                           ("Forward pull into the next", "forward_pull")]:
            if m.get(key):
                out.append(f"- **{label}:** {m[key]}")
        if m.get("material"):
            out.append("- **Material it owns:** " + "; ".join(m["material"]))
        out.append("")
    out += ["## Across the whole thing\n",
            f"- **Legitimate withholding:** {a['legitimate_withholding']}",
            f"- **Human stakes:** {a['human_stakes']}",
            f"- **Full scene vs compressed:** {a['compressed_vs_full_scene']}",
            f"- **Ending:** {a['ending']}",
            f"- **What stays unresolved:** {a['unresolved_uncertainty']}",
            "",
            "**Techniques chosen:** " + (", ".join(a["techniques_used"]) or "—"),
            ""]
    if a["liftable_prose"]:
        out += ["> ⚠️ This architecture contains quoted passages long enough to be lifted into a "
                "draft. Architecture is structure, not narration — treat these as accidents:",
                *[f"> - “{q}…”" for q in a["liftable_prose"]], ""]
    return "\n".join(out)
