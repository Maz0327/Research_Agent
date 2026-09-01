"""Stages 5–10: the writing path, connected — not replaced.

The v4 doctrine stays authoritative: cargo comes from the pipeline's own
files (RULES.md whole, registry rows, outline events, voice exemplars), the
drafter proposes and never gates, edits are logged, gates are advisory and
INTERNAL per the V1 touchpoint policy. This module assembles those dispatches
and runs them through the existing structured clients; it invents no new
doctrine and no new reviewers.

Model routing lives in `routing.py`: the locked seats, env-overridable, and a
missing credential FAILS LOUDLY rather than substituting a different writer.

Packer readiness patch (2026-09-01): the outline moved to `outline.py` (dense,
coverage-classified) and the drafter's cargo moved to `packet.py` (movement-
scoped Draft Packets). The arbitrary `[:8000]` / `[:20000]` / `[:60000]`
truncation that used to live here is gone, and the drafter now receives Brief
material, which it never did.
"""

import re
from pathlib import Path
from typing import Any

from backend.lwm import ledger, paths


def _client(seat: str):
    from backend.lwm.routing import seat_client
    return seat_client(seat)


def _cargo(episode: Path) -> dict:
    """The dispatch cargo, from the pipeline's own files."""
    pipe = paths.pipeline_dir()
    cargo = {}
    for key, rel in [("rules", "RULES.md"), ("voice", "MAZ-VOICE-CORPUS.md")]:
        p = pipe / rel
        cargo[key] = p.read_text() if p.exists() else ""
    # Only what a drafting dispatch actually uses. Story material reaches the
    # writer through its movement's Draft Packet (packet.py), scoped — never as
    # a whole document truncated to a character count.
    for key, rel in [("structure", "DECISION-LOG.md"),
                     ("dispatch_notes", "07-dispatch-notes.md")]:
        p = episode / rel
        cargo[key] = p.read_text() if p.exists() else ""
    return cargo


_TEXT_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}},
                "required": ["text"]}


def outline(episode: Path, client: Any = None) -> Path:
    """Stage 5 — delegated to the dense outline builder (§5).

    Kept as the stable entry point; the coverage-classified outline, the
    registry cross-check and the adversarial pre-draft check live in
    `outline.py`.
    """
    from backend.lwm import outline as _outline
    _outline.build(episode, client=client)
    return episode / "05-outline.md"


# The richer gate question sets (§15, §16). Gate A interrogates the OUTLINE —
# do I know what ride I am on, is anything buried, does the ending pay the
# angle. Gate B interrogates the PROSE — where did you drift, what held you,
# did anything feel invented, did it sound spoken or written.
GATE_A_QUESTIONS = [
    "Do you know what ride you are on, early?",
    "What promise are you given, and where is it paid?",
    "Where does it stop changing?",
    "Which movement would you skip?",
    "Is strong information buried where it does no work?",
    "Is anything withheld artificially rather than legitimately?",
    "Does the ending satisfy the story it set up?",
]
GATE_B_QUESTIONS = [
    "Where did you drift?",
    "What held you hardest?",
    "Was it mystery, or was it fog?",
    "Did you understand the mechanism of what happened?",
    "Did you trust the narrator?",
    "Did anything feel invented?",
    "Did it sound like a person talking, or like writing?",
    "What was overexplained?",
    "What was underexplained?",
    "Did the ending pay the opening promise?",
]

# Where a gate-A failure is routed (§15). QA never summons Maz for these; the
# routing decides which upstream stage owns the fix.
GATE_A_ROUTES = {
    "evidence": "targeted research (backfill the movement — never a full RA rerun)",
    "structure": "story architecture (04c) — the shape is wrong, not the words",
    "local": "the outline (05) — this movement's material or order",
}


def grip_gate(episode: Path, artifact: str, stage_key: str, clients: list | None = None) -> dict:
    """Stages 6/9: three blind readers, advisory, run ONCE per cycle.

    PASS and advisory FAIL are both COMPLETED gate executions — the gate ran,
    the result is on the record, nobody loops and nobody summons Maz. An
    advisory failure is input to the edit train, not a blocker. Gate B also
    writes the real grip map (held passages + drop-off points) that the pace
    edit consumes downstream.

    The question sets are the richer ones the readiness patch restored, and a
    gate-A failure carries its own routing: evidence problems go to targeted
    research, structural problems to the architecture, local problems to the
    outline.
    """
    gate_a = stage_key.startswith("6")
    questions = GATE_A_QUESTIONS if gate_a else GATE_B_QUESTIONS
    text = (episode / artifact).read_text()
    props = {
        "gripped": {"type": "boolean"}, "drop_off_point": {"type": "string"},
        "held_best": {"type": "string"}, "note": {"type": "string"},
        "answers": {"type": "array", "items": {"type": "object", "properties": {
            "question": {"type": "string"}, "answer": {"type": "string"}},
            "required": ["question", "answer"]}},
    }
    if gate_a:
        props["route"] = {"type": "string", "enum": list(GATE_A_ROUTES)}
        props["buried_information"] = {"type": "string"}
    else:
        props["felt_invented"] = {"type": "string"}
        props["spoken_or_written"] = {"type": "string"}
    schema = {"type": "object", "properties": props, "required": ["gripped", "note", "answers"]}
    system = ("You are a cold reader. Read this once, at pace, as a viewer would. You are not a "
              "critic and you give no craft advice — you report your own experience. Answer every "
              "question you are given, in your own words, quoting the exact line where a question "
              "asks where something happened. Then: did it keep you (gripped); where exactly did "
              "you check out (drop_off_point, quote the line); which passage held you hardest "
              "(held_best, quote it verbatim); one sentence why."
              + (" If it lost you, say whether the problem was the EVIDENCE (there was nothing "
                 "there), the STRUCTURE (wrong shape or order) or LOCAL (this one section) — "
                 "route: evidence | structure | local."
                 if gate_a else
                 " Say plainly whether anything felt invented, and whether it sounded like a "
                 "person talking or like writing."))
    prompt = text + "\n\n---\nANSWER THESE, ONE BY ONE:\n" + "\n".join(f"- {q}" for q in questions)
    if clients is None:
        client, _m = _client("reader")
        clients = [client] * 3
    verdicts = []
    for c in clients[:3]:
        try:
            data, _ = c.generate_structured(prompt=prompt, schema=schema,
                                            system=system, max_tokens=4000)
            verdicts.append(data)
        except Exception as e:
            verdicts.append({"gripped": None, "note": f"reader failed: {e}"})
    yes = sum(1 for v in verdicts if v.get("gripped") is True)
    passed = yes >= 2
    routes = [v.get("route") for v in verdicts if v.get("route") in GATE_A_ROUTES]
    result = {"pass": passed, "yes": yes, "verdicts": verdicts, "questions": questions,
              "routes": routes}

    # A completed execution either way: "pass"/"done" both satisfy the ledger;
    # the verdict itself lives in the gate cell and the grip-map artifact.
    ledger.update_row(episode, stage_key,
                      status="pass" if passed else "done (advisory FAIL)",
                      gate=f"PASS/FAIL: {'PASS' if passed else 'FAIL'} ({yes}/3 gripped)",
                      notes="internal advisory (V1 policy); grip map in the gate artifact"
                            + ("" if passed else " — feeds the edit train, not Maz")
                            + (f"; routed: {', '.join(sorted(set(routes)))}" if routes else ""))

    grip_file = episode / ("09-grip-gate-b.md" if stage_key.startswith("9") else "06-grip-gate-a.md")
    lines = [f"<!--\nartifact:  {grip_file.stem}\nversion:   v2 (richer question set)\n-->\n",
             f"# Grip map — {stage_key}\n",
             f"verdict: {'PASS' if passed else 'ADVISORY FAIL'} ({yes}/3 gripped)\n",
             "Questions asked:\n"] + [f"- {q}" for q in questions] + [""]
    for i, v in enumerate(verdicts, 1):
        lines.append(f"- reader {i}: gripped={v.get('gripped')}")
        if v.get("held_best"):
            lines.append(f"  - held: \u201c{v['held_best'][:160]}\u201d")
        if v.get("drop_off_point"):
            lines.append(f"  - drop-off: \u201c{v['drop_off_point'][:160]}\u201d")
        for extra in ("buried_information", "felt_invented", "spoken_or_written"):
            if v.get(extra):
                lines.append(f"  - {extra.replace('_', ' ')}: {v[extra][:200]}")
        if v.get("route"):
            lines.append(f"  - routes to: {v['route']} → {GATE_A_ROUTES[v['route']]}")
        for a in (v.get("answers") or []):
            lines.append(f"  - Q: {a.get('question', '')}")
            lines.append(f"    A: {a.get('answer', '')}")
        lines.append(f"  - note: {v.get('note', '')[:200]}")
    grip_file.write_text("\n".join(lines) + "\n")
    return result


def draft_movement(episode: Path, movement: int, client: Any = None) -> Path:
    """Stage 7: one movement, FREE TELLING, from its own Draft Packet.

    §8 / D-V1-11 — the first prose pass stays free. The writer receives story,
    evidence, structure, relevant context, a small positive cargo and a few
    voice examples, and is asked to tell it. It does NOT receive the regex
    bank, the pathology inventory, mechanical style counters or a wall of
    reviewer rules; those run AFTER drafting, where they belong.

    Raises `packet.ThinMovement` if the movement is THIN — a movement with no
    material behind it must be backfilled, never written (§7).
    """
    from backend.lwm import packet as _packet

    model = "?"
    if client is None:
        client, model = _client("writer")
    pk = _packet.build(episode, movement)          # raises ThinMovement
    cargo = _cargo(episode)
    prompt = _packet.render_prompt(pk, cargo["rules"])
    if cargo.get("dispatch_notes"):
        prompt = (f"THE CREATOR'S CORRECTION — LAW\n{cargo['dispatch_notes']}\n\n" + prompt)

    system = (
        "You draft narration for a story-driven documentary video — a person telling a story, at "
        "the mic, to one listener. Tell it naturally, in the order that grips you. The material "
        "you are given is what you have; the wording that travels with each fact governs how "
        "certain you may sound, and only a listed anchor may voice a comparison. Reactions and "
        "asides are PROPOSALS marked [MAZ?]. Never write about the documents; write speech."
    )
    data, _ = client.generate_structured(prompt=prompt, schema=_TEXT_SCHEMA,
                                         system=system, max_tokens=16000)
    out = episode / "07-draft.md"
    # Template stubs must not survive, but a real short draft must: the test
    # is whether the file already carries a movement, not how big it is.
    existing = out.read_text() if out.exists() and "## Movement" in out.read_text() else ""
    out.write_text((existing.rstrip() + "\n\n" if existing else "")
                   + f"## Movement {movement}\n\n{data['text'].strip()}\n")
    note = (f"movement {movement} via draft packet (writer seat: {model}; coverage "
            f"{pk['coverage']}); ear check per touchpoint C" if movement == 1
            else f"through movement {movement} (coverage {pk['coverage']})")
    ledger.update_row(episode, "7 draft", status=f"M{movement} drafted", notes=note)
    return out


def lint(episode: Path) -> dict:
    """The existing tier-1 lint, unchanged, on the current draft.

    Structured output (§12): the detector already speaks `--json`, and its
    findings are preserved whole rather than squeezed through a truncated
    stdout tail. The detector itself is untouched — it is a large body of
    researched work and flags only.
    """
    from backend.lwm import edit as _edit
    return _edit.run_lint(episode / "07-draft.md")


def movement_count(episode: Path) -> int:
    """How many movements the outline plans; a story defaults to three."""
    import json
    j = episode / "outputs" / "outline.json"
    if j.exists():
        movements = json.loads(j.read_text()).get("movements") or []
        if movements:
            return max(int(m.get("n", 0)) for m in movements)
    outline_text = (episode / "05-outline.md").read_text() if (episode / "05-outline.md").exists() else ""
    numbers = [int(m) for m in re.findall(r"movement\s+(\d+)", outline_text, re.I)]
    return max(numbers) if numbers else 3


def draft_remaining(episode: Path, client: Any = None) -> Path:
    """After touchpoint C approval: the remaining planned movements, automatically."""
    from backend.lwm import packet as _packet

    total = movement_count(episode)
    draft = episode / "07-draft.md"
    done = {int(m) for m in re.findall(r"^## Movement (\d+)", draft.read_text(), re.M)} if draft.exists() else set()
    thin = []
    for movement in range(1, total + 1):
        if movement in done:
            continue
        try:
            draft_movement(episode, movement, client=client)
        except _packet.ThinMovement as e:
            # A THIN movement is an upstream information failure, not a writing
            # failure (§7). It is held out of the draft, named, and backfilled.
            thin.append({"movement": movement, "missing": e.missing, "reason": e.reason})
    if thin:
        ledger.update_row(
            episode, "7 draft", status="held: THIN movement(s)",
            notes="movements " + ", ".join(str(t["movement"]) for t in thin)
                  + " were not drafted — no material behind them; targeted backfill first "
                    "(`lwm backfill`). This is an upstream failure, not a writing failure.")
        return draft
    ledger.update_row(episode, "7 draft", status="done",
                      notes=f"all {total} movements drafted (M1 approved at touchpoint C)")
    return draft


def redraft_m1(episode: Path, client: Any = None) -> Path:
    """Apply Maz's one C correction: regenerate M1 from the amended cargo (cap 1)."""
    draft = episode / "07-draft.md"
    if draft.exists():
        draft.unlink()
    out = draft_movement(episode, 1, client=client)
    ledger.update_row(episode, "7 draft", status="M1 drafted",
                      notes="redraft used (cap 1) — correction applied upstream via dispatch notes; back to the ear")
    return out
