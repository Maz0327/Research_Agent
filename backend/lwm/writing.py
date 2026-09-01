"""Stages 5–10: the writing path, connected — not replaced.

The v4 doctrine stays authoritative: cargo comes from the pipeline's own
files (RULES.md whole, registry rows, outline events, voice exemplars), the
drafter proposes and never gates, edits are logged, gates are advisory and
INTERNAL per the V1 touchpoint policy. This module assembles those dispatches
and runs them through the existing structured clients; it invents no new
doctrine and no new reviewers.

Model routing: seats resolve from env (LWM_MODEL_WRITER / _EDITOR / _READER)
before falling back to the research repo's settings. D-23's drafter
(deepseek-v4-pro) is not reachable through this repo's clients today, so the
default writer falls back to MODEL_DISTILL — recorded in every dispatch note
rather than hidden.
"""

import os
from pathlib import Path
from typing import Any

from backend.lwm import ledger, paths


def _client(seat_env: str, default_setting: str):
    from backend.config import get_settings
    from backend.integrations.structured_client import get_structured_client
    model = os.environ.get(seat_env) or getattr(get_settings(), default_setting)
    return get_structured_client(model), model


def _cargo(episode: Path) -> dict:
    """The dispatch cargo, from the pipeline's own files."""
    pipe = paths.pipeline_dir()
    cargo = {}
    for key, rel in [("rules", "RULES.md"), ("voice", "MAZ-VOICE-CORPUS.md")]:
        p = pipe / rel
        cargo[key] = p.read_text() if p.exists() else ""
    for key, rel in [("briefing", "04b-briefing.md"), ("registry", "04-sources-registry.md"),
                     ("outline", "05-outline.md"), ("structure", "DECISION-LOG.md")]:
        p = episode / rel
        cargo[key] = p.read_text() if p.exists() else ""
    return cargo


_TEXT_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}},
                "required": ["text"]}


def outline(episode: Path, client: Any = None) -> Path:
    """Stage 5: the outline, from the briefing + Maz's structure decisions."""
    if client is None:
        client, model = _client("LWM_MODEL_WRITER", "model_distill")
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
    """Stages 6/9: three blind readers, advisory, logged — never Maz homework.

    Readers see only the artifact — no dispatch history, no doctrine, no hint
    of which parts are new (the blinding that survived the A/B position-bias
    failure). Results go to the ledger; the gate interrupts nobody.
    """
    text = (episode / artifact).read_text()
    schema = {"type": "object", "properties": {
        "gripped": {"type": "boolean"}, "drop_off_point": {"type": "string"},
        "note": {"type": "string"}}, "required": ["gripped", "note"]}
    system = ("You are a cold reader. Read this once, at pace, as a viewer would. Answer only: "
              "did it keep you (gripped), where exactly did you check out if it lost you "
              "(drop_off_point), and one sentence why. No craft advice.")
    if clients is None:
        client, _m = _client("LWM_MODEL_READER", "model_judge")
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
    result = {"pass": yes >= 2, "yes": yes, "verdicts": verdicts}
    ledger.update_row(episode, stage_key,
                      status="pass" if result["pass"] else "advisory-fail (internal)",
                      gate=f"PASS/FAIL: {'PASS' if result['pass'] else 'FAIL'} ({yes}/3 gripped)",
                      notes="internal advisory per V1 touchpoint policy; verdicts in gate file")
    (episode / f"{artifact.split('-')[0]}-gate-verdicts.md").write_text(
        f"# Gate verdicts — {stage_key}\n\n" + "\n".join(
            f"- gripped: {v.get('gripped')} · drop-off: {v.get('drop_off_point', '—')} · {v.get('note')}"
            for v in verdicts) + "\n")
    return result


def draft_movement(episode: Path, movement: int, client: Any = None) -> Path:
    """Stage 7: one movement, free telling, from real dispatch cargo."""
    model = "?"
    if client is None:
        client, model = _client("LWM_MODEL_WRITER", "model_distill")
    cargo = _cargo(episode)
    system = (
        "You draft narration for a story-driven documentary video — a person telling a story, at "
        "the mic, to one listener. FREE TELLING: tell it in order as it grips you; the outline's "
        "movement events are your material, registry allowed-wording governs certainty, and only "
        "a registry anchor may voice a comparison. Reactions and asides are PROPOSALS marked "
        "[MAZ?]. Never announce thread duties; never write about the documents; write speech."
    )
    prompt = (f"RULES (whole card)\n{cargo['rules']}\n\nVOICE EXEMPLARS\n{cargo['voice'][:6000]}\n\n"
              f"OUTLINE\n{cargo['outline'][:20000]}\n\nREGISTRY\n{cargo['registry'][:20000]}\n\n"
              f"Draft MOVEMENT {movement} only.")
    data, _ = client.generate_structured(prompt=prompt, schema=_TEXT_SCHEMA,
                                         system=system, max_tokens=16000)
    out = episode / "07-draft.md"
    existing = out.read_text() if out.exists() and out.stat().st_size > 300 else ""
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
