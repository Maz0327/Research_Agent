"""`lwm decide` — how Maz's four touchpoint decisions enter the state machine.

Decisions land in the artifacts that already exist — the STAGE-LEDGER and the
DECISION-LOG — never a new state store. Four touchpoints, no generic forms.
"""

from datetime import date
from pathlib import Path

from backend.lwm import ledger


def _log(episode: Path, title: str, body: str) -> None:
    p = episode / "DECISION-LOG.md"
    entry = f"\n## {date.today()} — {title}\n{body}\n"
    p.write_text((p.read_text() if p.exists() else "# DECISION LOG\n") + entry)


def decide_angle(episode: Path, choice: str = "", custom: str = "",
                 client=None, kill: bool = False, why: str = "") -> dict:
    """The ANGLE touchpoint (D-V1-7) — Maz picks the story, or kills the video.

    `choice` is "baseline", "alt-N", "previous", or "custom". A custom angle is
    assessed against the evidence and the verdict is RECORDED, never enforced:
    Maz overrides regardless, which is the point of the assessment existing.
    Nothing downstream runs until this row is chosen.
    """
    import json

    options_path = episode / "outputs" / "angle-options.json"
    if kill:
        ledger.update_row(episode, "1 angle", status="KILLED",
                          gate="KILL gate: KILLED", notes=f"Maz killed at the angle: {why or choice}")
        _log(episode, "ANGLE — KILLED", f"Reason: {why or 'not stated'}")
        return {"touchpoint": "angle", "killed": True}

    if not options_path.exists():
        raise RuntimeError("the angle options have not been laid out yet "
                           "(`lwm continue` builds outputs/angle-options.json)")
    options = json.loads(options_path.read_text())

    chosen: dict
    assessment = None
    c = (choice or ("custom" if custom else "")).strip().lower()
    if custom and c in ("", "custom"):
        from backend.lwm import angle as _angle
        assessment = _angle.assess_custom(episode, custom, client=client)
        chosen = {"kind": "custom", "name": "Maz's own angle", "central_story": custom}
    elif c == "baseline":
        chosen = dict(options["baseline"], kind="baseline")
    elif c == "previous":
        prev = options.get("previous_maz_idea") or ""
        if not prev:
            raise ValueError("there is no previous angle idea recorded for this episode")
        chosen = {"kind": "previous", "name": "Maz's previous idea", "central_story": prev}
    elif c.startswith("alt"):
        digits = "".join(ch for ch in c if ch.isdigit())
        n = int(digits) if digits else 0
        alts = options.get("alternatives") or []
        if not 1 <= n <= len(alts):
            raise ValueError(f"alternative {n or c!r} does not exist "
                             f"(there are {len(alts)})")
        chosen = dict(alts[n - 1], kind=f"alt-{n}")
    else:
        raise ValueError("choose --baseline, --alt N, --previous, or --custom \"…\"")

    options["chosen"] = chosen
    if assessment:
        options["custom_assessment"] = assessment
    options_path.write_text(json.dumps(options, indent=1, ensure_ascii=False))

    verdict_note = f" · evidence check: {assessment['verdict']} (advisory)" if assessment else ""
    ledger.update_row(episode, "1 angle", status="chosen", gate="KILL gate: pass",
                      notes=f"{chosen['kind']}: {chosen.get('name', '')}"
                            f" — {chosen.get('central_story', '')[:120]}{verdict_note}")
    body = [f"- choice: {chosen['kind']} — {chosen.get('name', '')}",
            f"- central story: {chosen.get('central_story', '')}"]
    if chosen.get("driving_question"):
        body.append(f"- driving question: {chosen['driving_question']}")
    if assessment:
        body += [f"- evidence check: **{assessment['verdict']}** — {assessment['why']}",
                 "- (advisory only; Maz's choice stands)"]
    _log(episode, "ANGLE CHOSEN", "\n".join(body))
    return {"touchpoint": "angle", "chosen": chosen, "assessment": assessment}


def decide_a(episode: Path, angle: str, packaging: str, format_: str,
             kill: bool = False) -> dict:
    """Pre-D-V1-6 touchpoint A. Kept so existing callers and tests keep working.

    Under the reordered flow the creative decision is `decide_angle`, taken
    AFTER research; packaging and format are their own stages. This records the
    same state across the rows that now carry it.
    """
    if kill:
        ledger.update_row(episode, "1 angle", status="KILLED",
                          gate="KILL gate: KILLED", notes=f"Maz killed at A: {angle or packaging}")
        _log(episode, "TOUCHPOINT A — KILLED", f"Reason: {angle or packaging or 'not stated'}")
        return {"touchpoint": "A", "killed": True}
    if not (angle and packaging and format_):
        raise ValueError("touchpoint A needs --angle, --packaging and --format (or --kill)")
    ledger.update_row(episode, "1 angle", status="chosen",
                      gate="KILL gate: pass", notes=f"angle: {angle}")
    ledger.update_row(episode, "1b packaging", status="done",
                      gate="packaging concepts: recorded by Maz", notes=f"packaging: {packaging}")
    ledger.update_row(episode, "2 feasibility + format", status="decided",
                      gate="KILL gate: pass", notes=f"MAZ: {format_}")
    _log(episode, "TOUCHPOINT A", f"- angle: {angle}\n- packaging: {packaging}\n- format: {format_}")
    return {"touchpoint": "A", "recorded": True}


def decide_b(episode: Path, notes: str = "", waive: bool = False) -> dict:
    """Touchpoint B (STORY): the structure session's decisions, or a waiver.

    Under D-V1-6 the Briefing is a research artifact that is already rendered
    by the time Maz gets here; what he decides at this touchpoint is how the
    story is TOLD. His decisions become the input to the Story Architecture
    pass, which the system then runs.
    """
    if not notes and not waive:
        raise ValueError("touchpoint B needs --notes (structure decisions) or --waive")
    ledger.update_row(episode, "4c story architecture",
                      status="structure waived" if waive else "structure decided",
                      gate="structure session: " + ("WAIVED" if waive else "held"),
                      notes=("structure session WAIVED by Maz — the architecture pass takes the "
                             "briefing's own strongest order" if waive else
                             "Maz's structure decisions in DECISION-LOG; architecture pass next"))
    _log(episode, "TOUCHPOINT B — STRUCTURE" + (" (WAIVED)" if waive else ""),
         notes or "Waived; the outline follows the briefing's own strongest order.")
    return {"touchpoint": "B", "waived": waive}


def decide_c(episode: Path, approve: bool = False, correction: str = "") -> dict:
    """Touchpoint C: the ~M1 ear check — approved, or ONE correction."""
    rows = ledger.read_rows(episode)
    row = rows.get("7 draft")
    if not row or "M1" not in row.status:
        raise RuntimeError("touchpoint C recorded but movement 1 is not at the ear "
                           f"(stage 7 status: {row.status if row else 'missing'!r})")
    if approve:
        ledger.update_row(episode, "7 draft", status="M1 approved",
                          notes="ear check passed (touchpoint C); drafting remaining movements")
        _log(episode, "TOUCHPOINT C — M1 APPROVED", "Ear check passed.")
        return {"touchpoint": "C", "approved": True}
    if not correction:
        raise ValueError("touchpoint C needs --approve or --correction \"…\"")
    if "redraft used" in row.notes:
        raise RuntimeError("the one-redraft cap is spent; C must approve or the episode "
                           "needs a named kill — a third M1 is the spiral the cap exists to stop")
    # The correction goes UPSTREAM into the dispatch cargo (doctrine: defects
    # are cargo defects), and M1 regenerates once.
    p = episode / "07-dispatch-notes.md"
    p.write_text((p.read_text() if p.exists() else "# Dispatch notes (cargo)\n")
                 + f"\n## Maz's ear correction ({date.today()})\n{correction}\n")
    ledger.update_row(episode, "7 draft", status="M1 correction issued",
                      notes="redraft used (cap 1); correction in 07-dispatch-notes.md")
    _log(episode, "TOUCHPOINT C — ONE CORRECTION", correction)
    return {"touchpoint": "C", "correction": correction}


def decide_d(episode: Path, approve: bool = False, corrections: str = "") -> dict:
    """Touchpoint D: the one final candidate — locked, or bounded corrections.

    A correction issued AFTER a lock (Maz's ruling on a material 10b finding
    routes here too — there is no fifth touchpoint) SUPERSEDES the lock: the
    old SHA stops being the approved script, its history is preserved in the
    lock record, stage 10 reopens, and the correction pass revises the
    candidate for a fresh D approval and a fresh 10b run.
    """
    import hashlib
    import json
    candidate = episode / "10-final-candidate.md"
    if not candidate.exists():
        raise RuntimeError("touchpoint D recorded but no final candidate exists "
                           "(stage 10 has not prepared 10-final-candidate.md)")
    out = episode / "outputs"
    meta_path = out / "final-script.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    if approve:
        text = candidate.read_text()
        sha = hashlib.sha256(text.encode()).hexdigest()[:12]
        out.mkdir(exist_ok=True)
        locked = out / "final-script-locked.md"
        locked.write_text(text)
        meta_path.write_text(json.dumps({
            "path": str(locked), "sha": sha, "approved": True,
            "locked_at": str(date.today()),
            "lineage": ["07-draft.md", "08-edit-log.md", "09-grip-gate-b.md",
                        "09b-pace-edit.md", "10-final-candidate.md"],
            # Every superseded lock stays on the record — provenance survives.
            "history": meta.get("history", []),
        }, indent=1))
        ledger.update_row(episode, "10 ear loop + locks", status="done",
                          gate=f"locks: script LOCKED {sha}",
                          notes="touchpoint D approved; canonical script = outputs/final-script-locked.md")
        _log(episode, "TOUCHPOINT D — SCRIPT LOCKED", f"sha {sha} · outputs/final-script-locked.md")
        return {"touchpoint": "D", "locked": True, "sha": sha}

    if not corrections:
        raise ValueError("touchpoint D needs --approve or --corrections \"…\"")

    if meta.get("approved"):
        # LOCK INVALIDATION: the old SHA is no longer the approved script.
        old_sha = meta.get("sha")
        meta["approved"] = False
        meta.setdefault("history", []).append({
            "sha": old_sha, "superseded_at": str(date.today()),
            "reason": f"D corrections after lock: {corrections[:200]}",
        })
        meta_path.write_text(json.dumps(meta, indent=1))
        # Downstream work built on the dead SHA reopens with it.
        for stage in ("10b script fact-check (D-SFC-1)", "11 production package"):
            ledger.update_row(episode, stage, status="", gate="—",
                              notes=f"reopened: lock {old_sha} superseded by D corrections")
        _log(episode, "LOCK SUPERSEDED", f"sha {old_sha} is no longer the approved script")

    # The correction is stored machine-readably so the stage-10 correction
    # pass applies exactly what Maz asked, not a paraphrase from a log.
    out.mkdir(exist_ok=True)
    dc_path = out / "d-corrections.json"
    dc = json.loads(dc_path.read_text()) if dc_path.exists() else {"corrections": []}
    dc["corrections"].append({"at": str(date.today()), "text": corrections, "applied": False})
    dc_path.write_text(json.dumps(dc, indent=1))

    ledger.update_row(episode, "10 ear loop + locks", status="corrections requested",
                      notes="correction stored in outputs/d-corrections.json; the correction "
                            "pass revises the candidate, then back to touchpoint D")
    _log(episode, "TOUCHPOINT D — CORRECTIONS", corrections)
    return {"touchpoint": "D", "corrections": corrections}


def locked_script(episode: Path) -> tuple[Path, str] | None:
    """The canonical locked script, when it exists: (path, sha)."""
    import json
    meta = episode / "outputs" / "final-script.json"
    if not meta.exists():
        return None
    data = json.loads(meta.read_text())
    p = Path(data["path"])
    return (p, data["sha"]) if p.exists() and data.get("approved") else None
