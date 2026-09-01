"""Stages 5–10: the writing path, connected — not replaced.

The v4 doctrine stays authoritative: cargo comes from the pipeline's own
files (RULES.md whole, registry rows, outline events, voice exemplars), the
drafter proposes and never gates, edits are logged, gates are advisory and
INTERNAL per the V1 touchpoint policy. This module assembles those dispatches
and runs them through the existing structured clients; it invents no new
doctrine and no new reviewers.

Model routing lives in `routing.py`: D-23's locked seats (deepseek-v4-pro
drafts, sonnet edits, kimi judges), env-overridable, and a missing credential
FAILS LOUDLY rather than substituting a different writer.
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
    for key, rel in [("briefing", "04b-briefing.md"), ("registry", "04-sources-registry.md"),
                     ("outline", "05-outline.md"), ("structure", "DECISION-LOG.md"),
                     ("dispatch_notes", "07-dispatch-notes.md")]:
        p = episode / rel
        cargo[key] = p.read_text() if p.exists() else ""
    return cargo


_TEXT_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}},
                "required": ["text"]}


def outline(episode: Path, client: Any = None) -> Path:
    """Stage 5: the outline, from the briefing + Maz's structure decisions."""
    if client is None:
        client, model = _client("writer")
    cargo = _cargo(episode)
    system = (
        "Build the episode outline. The structure decisions in the DECISION LOG are Maz's and are "
        "law. Stage the reveals as breadcrumbs the viewer assembles — never the narrator's "
        "conclusions; front-load the doors (D-25); carry reveal threads as rows: plant / silence "
        "/ payoff, staggered. Events reference registry rows by number; never write liftable "
        "narration prose into the outline."
    )
    prompt = (f"STRUCTURE DECISIONS\n{cargo['structure'][:8000]}\n\n"
              f"REGISTRY\n{cargo['registry'][:20000]}\n\nBRIEFING\n{cargo['briefing'][:60000]}")
    data, _ = client.generate_structured(prompt=prompt, schema=_TEXT_SCHEMA,
                                         system=system, max_tokens=16000)
    out = episode / "05-outline.md"
    out.write_text(data["text"])
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "outline.txt").write_text(data["text"])
    ledger.update_row(episode, "5 outline", status="done", notes="outline built via lwm from structure decisions")
    return out


def grip_gate(episode: Path, artifact: str, stage_key: str, clients: list | None = None) -> dict:
    """Stages 6/9: three blind readers, advisory, run ONCE per cycle.

    PASS and advisory FAIL are both COMPLETED gate executions — the gate ran,
    the result is on the record, nobody loops and nobody summons Maz. An
    advisory failure is input to the edit train, not a blocker. Gate B also
    writes the real grip map (held passages + drop-off points) that the pace
    edit consumes downstream.
    """
    text = (episode / artifact).read_text()
    schema = {"type": "object", "properties": {
        "gripped": {"type": "boolean"}, "drop_off_point": {"type": "string"},
        "held_best": {"type": "string"}, "note": {"type": "string"}},
        "required": ["gripped", "note"]}
    system = ("You are a cold reader. Read this once, at pace, as a viewer would. Answer only: "
              "did it keep you (gripped); where exactly did you check out if it lost you "
              "(drop_off_point, quote the line); which passage held you hardest (held_best, "
              "quote it verbatim); one sentence why. No craft advice.")
    if clients is None:
        client, _m = _client("reader")
        clients = [client] * 3
    verdicts = []
    for c in clients[:3]:
        try:
            data, _ = c.generate_structured(prompt=text[:60000], schema=schema,
                                            system=system, max_tokens=2000)
            verdicts.append(data)
        except Exception as e:
            verdicts.append({"gripped": None, "note": f"reader failed: {e}"})
    yes = sum(1 for v in verdicts if v.get("gripped") is True)
    passed = yes >= 2
    result = {"pass": passed, "yes": yes, "verdicts": verdicts}

    # A completed execution either way: "pass"/"done" both satisfy the ledger;
    # the verdict itself lives in the gate cell and the grip-map artifact.
    ledger.update_row(episode, stage_key,
                      status="pass" if passed else "done (advisory FAIL)",
                      gate=f"PASS/FAIL: {'PASS' if passed else 'FAIL'} ({yes}/3 gripped)",
                      notes="internal advisory (V1 policy); grip map in the gate artifact"
                            + ("" if passed else " — feeds the edit train, not Maz"))

    grip_file = episode / ("09-grip-gate-b.md" if stage_key.startswith("9") else "06-grip-gate-a.md")
    lines = [f"<!--\nartifact:  {grip_file.stem}\nversion:   v1 (lwm gate run)\n-->\n",
             f"# Grip map — {stage_key}\n",
             f"verdict: {'PASS' if passed else 'ADVISORY FAIL'} ({yes}/3 gripped)\n"]
    for i, v in enumerate(verdicts, 1):
        lines.append(f"- reader {i}: gripped={v.get('gripped')}")
        if v.get("held_best"):
            lines.append(f"  - held: “{v['held_best'][:160]}”")
        if v.get("drop_off_point"):
            lines.append(f"  - drop-off: “{v['drop_off_point'][:160]}”")
        lines.append(f"  - note: {v.get('note', '')[:160]}")
    grip_file.write_text("\n".join(lines) + "\n")
    return result


def draft_movement(episode: Path, movement: int, client: Any = None) -> Path:
    """Stage 7: one movement, free telling, from real dispatch cargo."""
    model = "?"
    if client is None:
        client, model = _client("writer")
    cargo = _cargo(episode)
    system = (
        "You draft narration for a story-driven documentary video — a person telling a story, at "
        "the mic, to one listener. FREE TELLING: tell it in order as it grips you; the outline's "
        "movement events are your material, registry allowed-wording governs certainty, and only "
        "a registry anchor may voice a comparison. Reactions and asides are PROPOSALS marked "
        "[MAZ?]. Never announce thread duties; never write about the documents; write speech."
    )
    prompt = (f"RULES (whole card)\n{cargo['rules']}\n\nVOICE EXEMPLARS\n{cargo['voice'][:6000]}\n\n"
              + (f"DISPATCH NOTES (Maz's corrections — law)\n{cargo['dispatch_notes']}\n\n"
                 if cargo.get('dispatch_notes') else "")
              + f"OUTLINE\n{cargo['outline'][:20000]}\n\nREGISTRY\n{cargo['registry'][:20000]}\n\n"
              f"Draft MOVEMENT {movement} only.")
    data, _ = client.generate_structured(prompt=prompt, schema=_TEXT_SCHEMA,
                                         system=system, max_tokens=16000)
    out = episode / "07-draft.md"
    # Template stubs must not survive, but a real short draft must: the test
    # is whether the file already carries a movement, not how big it is.
    existing = out.read_text() if out.exists() and "## Movement" in out.read_text() else ""
    out.write_text((existing.rstrip() + "\n\n" if existing else "")
                   + f"## Movement {movement}\n\n{data['text'].strip()}\n")
    ledger.update_row(episode, "7 draft", status=f"M{movement} drafted",
                      notes=f"movement {movement} via lwm dispatch (writer seat: {model}); "
                            "ear check per touchpoint C" if movement == 1 else f"through movement {movement}")
    return out


def lint(episode: Path) -> str:
    """The existing tier-1 lint, unchanged, on the current draft."""
    import subprocess
    draft = episode / "07-draft.md"
    mjs = paths.pipeline_dir() / "lint" / "regression-tier1.mjs"
    if not (draft.exists() and mjs.exists()):
        return "lint skipped: draft or lint script missing"
    proc = subprocess.run(["node", str(mjs), str(draft)], capture_output=True, text=True, timeout=120)
    return proc.stdout[-2000:] or proc.stderr[-2000:]


def movement_count(episode: Path) -> int:
    """How many movements the outline plans; a story defaults to three."""
    outline_text = (episode / "05-outline.md").read_text() if (episode / "05-outline.md").exists() else ""
    numbers = [int(m) for m in re.findall(r"movement\s+(\d)", outline_text, re.I)]
    return max(numbers) if numbers else 3


def draft_remaining(episode: Path, client: Any = None) -> Path:
    """After touchpoint C approval: the remaining planned movements, automatically."""
    total = movement_count(episode)
    draft = episode / "07-draft.md"
    done = {int(m) for m in re.findall(r"^## Movement (\d)", draft.read_text(), re.M)} if draft.exists() else set()
    for movement in range(1, total + 1):
        if movement not in done:
            draft_movement(episode, movement, client=client)
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
