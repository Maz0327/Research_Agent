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


def decide_a(episode: Path, angle: str, packaging: str, format_: str,
             kill: bool = False) -> dict:
    """Touchpoint A: topic/angle/packaging + feasibility/format."""
    if kill:
        ledger.update_row(episode, "1 angle + packaging", status="KILLED",
                          gate="KILL gate: KILLED", notes=f"Maz killed at A: {angle or packaging}")
        _log(episode, "TOUCHPOINT A — KILLED", f"Reason: {angle or packaging or 'not stated'}")
        return {"touchpoint": "A", "killed": True}
    if not (angle and packaging and format_):
        raise ValueError("touchpoint A needs --angle, --packaging and --format (or --kill)")
    ledger.update_row(episode, "1 angle + packaging", status="decided",
                      gate="KILL gate: pass",
                      notes=f"angle: {angle} · packaging: {packaging}")
    ledger.update_row(episode, "2 feasibility + format", status="decided",
                      gate="KILL gate: pass", notes=f"MAZ: {format_}")
    _log(episode, "TOUCHPOINT A", f"- angle: {angle}\n- packaging: {packaging}\n- format: {format_}")
    return {"touchpoint": "A", "recorded": True}


def decide_b(episode: Path, notes: str = "", waive: bool = False) -> dict:
    """Touchpoint B: the structure session's decisions, or an explicit waiver."""
    if not notes and not waive:
        raise ValueError("touchpoint B needs --notes (structure decisions) or --waive")
    status = "waived" if waive else "done"
    ledger.update_row(episode, "4b briefing + structure session", status=status,
                      gate="briefing ready: YES",
                      notes=("structure session WAIVED by Maz — default path"
                             if waive else "structure session held; decisions in DECISION-LOG"))
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
    """Touchpoint D: the one final candidate — locked, or bounded corrections."""
    candidate = episode / "10-final-candidate.md"
    if not candidate.exists():
        raise RuntimeError("touchpoint D recorded but no final candidate exists "
                           "(stage 10 has not prepared 10-final-candidate.md)")
    if approve:
        import hashlib
        import json
        text = candidate.read_text()
        sha = hashlib.sha256(text.encode()).hexdigest()[:12]
        out = episode / "outputs"
        out.mkdir(exist_ok=True)
        locked = out / "final-script-locked.md"
        locked.write_text(text)
        (out / "final-script.json").write_text(json.dumps({
            "path": str(locked), "sha": sha, "approved": True,
            "locked_at": str(date.today()),
            "lineage": ["07-draft.md", "08-edit-log.md", "09-grip-gate-b.md",
                        "09b-pace-edit.md", "10-final-candidate.md"],
        }, indent=1))
        ledger.update_row(episode, "10 ear loop + locks", status="done",
                          gate=f"locks: script LOCKED {sha}",
                          notes="touchpoint D approved; canonical script = outputs/final-script-locked.md")
        _log(episode, "TOUCHPOINT D — SCRIPT LOCKED", f"sha {sha} · outputs/final-script-locked.md")
        return {"touchpoint": "D", "locked": True, "sha": sha}
    if not corrections:
        raise ValueError("touchpoint D needs --approve or --corrections \"…\"")
    ledger.update_row(episode, "10 ear loop + locks", status="corrections requested",
                      notes="bounded corrections in DECISION-LOG; one more candidate")
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
