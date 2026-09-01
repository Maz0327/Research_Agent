"""`lwm continue` — run internal work until the next Maz touchpoint.

Deterministic resume, no daemon: resolve the ONE pointer, read the ledger,
do what is internal, stop where the V1 touchpoint policy says Maz is needed —
and nowhere else. Never resumes by modification time; never asks Maz to
adjudicate lint or reviewer flags. Maz's answers come back through
`lwm decide`, which is the only way a touchpoint clears.
"""

from dataclasses import dataclass
from datetime import date

from loguru import logger

from backend.lwm import decisions, edit, factcheck, handoff, ledger, production, research, writing
from backend.lwm import episode as ep

TOUCHPOINTS = {
    "1 angle + packaging": "A — topic/angle/packaging (record with `lwm decide A …`)",
    "2 feasibility + format": "A — format decision (record with `lwm decide A …`)",
    "4b briefing + structure session": "B — read the Briefing; `lwm decide B --notes …` or `--waive`",
    "12 record + booth diff": "record (Maz at the mic)",
    "13 assemble + final review": "assemble/publish (Maz)",
}


@dataclass
class StopPoint:
    reason: str          # touchpoint | kill | contradiction | failure | done
    detail: str
    maz_needed: bool


def _stop(log, entry, reason, detail, maz):
    log.append({**entry, "stop": StopPoint(reason, detail, maz).__dict__})
    return log


def step(slug: str | None = None, max_steps: int = 12, **hooks) -> list[dict]:
    """Advance the active episode until a stop condition. Returns the log.

    `hooks` lets tests inject clients/search/fetch; production resolves seats
    through routing.py (locked models, loud failures).
    """
    episode = ep.resolve(slug)
    log: list[dict] = []

    for _ in range(max_steps):
        macro, stage = ledger.macro_state(episode)
        entry = {"stage": stage, "macro": macro}
        rows = ledger.read_rows(episode)

        if not stage:
            return _stop(log, entry, "done", "episode is PUBLISHED", False)
        if rows.get("1 angle + packaging") and rows["1 angle + packaging"].status == "KILLED":
            return _stop(log, entry, "kill", "episode was killed at touchpoint A", False)
        if stage in TOUCHPOINTS:
            return _stop(log, entry, "touchpoint", f"Maz touchpoint {TOUCHPOINTS[stage]}", True)

        try:
            if stage == "3 brief":
                topic = ep.status(episode.name)["topic"]
                result = research.run_round(episode, topic)
                if result.get("status") != "completed":
                    raise RuntimeError(f"research job {result.get('job_id')} did not complete: {result}")
                gap_rounds = research.run_gap_rounds(episode, topic)
                # The round succeeded — the ledger advances HERE, so a second
                # `continue` never reruns research because nothing recorded it.
                final_job = research.current_job_id(episode)
                ledger.update_row(episode, "3 brief", status="done", when=str(date.today()),
                                  notes=f"RA job {final_job}: {result.get('sources_count')} sources, "
                                        f"{result.get('claims_count')} claims; "
                                        f"{len(gap_rounds)} gap round(s) via lwm")
                entry["did"] = f"research complete — job {final_job}, {len(gap_rounds)} gap round(s)"
            elif stage == "4 fact-check the brief":
                job_id = research.current_job_id(episode)
                if not job_id:
                    raise RuntimeError("stage 4 pending but no RA job recorded in research/ra-job.json")
                judgment = hooks.get("judgment_client")
                if judgment is None:
                    # The fresh-family pass is part of stage 4's contract; the
                    # judge seat resolves through the locked routing and fails
                    # loudly if unreachable — never silently skipped.
                    from backend.lwm.routing import seat_client
                    judgment, _m = seat_client("judge")
                result = handoff.run_handoff(episode, job_id,
                                             docs_dir=hooks.get("docs_dir"),
                                             harvest=hooks.get("harvest"),
                                             judgment_client=judgment)
                entry["did"] = f"handoff: {result['registry_rows']} registry rows, briefing rendered"
            elif stage == "5 outline":
                writing.outline(episode, client=hooks.get("writer_client"))
                entry["did"] = "outline built"
            elif stage == "6 grip gate A":
                r = writing.grip_gate(episode, "05-outline.md", "6 grip gate A",
                                      clients=hooks.get("reader_clients"))
                entry["did"] = f"gate A internal: {r['yes']}/3 gripped ({'PASS' if r['pass'] else 'advisory FAIL'})"
            elif stage == "7 draft":
                row = rows.get("7 draft")
                status = row.status if row else ""
                if status.startswith("M1 drafted"):
                    return _stop(log, entry, "touchpoint",
                                 "C — Maz hears ~Movement 1; `lwm decide C --approve` or `--correction …`", True)
                if status.startswith("M1 correction issued"):
                    writing.redraft_m1(episode, client=hooks.get("writer_client"))
                    entry["did"] = "M1 regenerated from amended cargo (cap 1) — back to the ear"
                    log.append(entry)
                    return _stop(log, {"stage": stage, "macro": macro}, "touchpoint",
                                 "C — Maz hears the corrected Movement 1", True)
                if status.startswith("M1 approved"):
                    writing.draft_remaining(episode, client=hooks.get("writer_client"))
                    entry["did"] = "remaining movements drafted"
                else:
                    writing.draft_movement(episode, 1, client=hooks.get("writer_client"))
                    entry["did"] = "movement 1 drafted"
                    log.append(entry)
                    return _stop(log, {"stage": stage, "macro": macro}, "touchpoint",
                                 "C — Maz hears ~Movement 1; `lwm decide C --approve` or `--correction …`", True)
            elif stage == "8 edit":
                client = hooks.get("editor_client")
                if client is None:
                    client, _m = writing._client("editor")
                r = edit.edit_train(episode, client)
                ledger.update_row(episode, "8 edit", status="done",
                                  gate=f"cycles used: {r['cycles']}",
                                  notes=f"{r['applied']} pairs applied, {r['rejected']} rejected — 08-edit-log.md")
                entry["did"] = f"edit train: {r['applied']} applied / {r['rejected']} rejected in {r['cycles']} cycle(s)"
            elif stage == "9 grip gate B":
                r = writing.grip_gate(episode, "07-draft.md", "9 grip gate B",
                                      clients=hooks.get("reader_clients"))
                entry["did"] = f"gate B internal: {r['yes']}/3 gripped; grip map written"
            elif stage == "9b pace edit":
                client = hooks.get("editor_client")
                if client is None:
                    client, _m = writing._client("editor")
                r = edit.pace_edit(episode, client)
                ledger.update_row(episode, "9b pace edit", status="done",
                                  gate=f"words before → after: {r['words']}",
                                  notes=r.get("note", f"{r['applied']} cuts applied; held passages protected"))
                entry["did"] = f"pace edit: {r['words']}"
            elif stage == "10 ear loop + locks":
                row = rows.get("10 ear loop + locks")
                if row and row.status.startswith("corrections requested"):
                    # Maz's D correction is APPLIED, not just recorded: the
                    # editor seat proposes pairs against the current candidate,
                    # code applies them, and the revised candidate goes back to
                    # D. Never silently re-locked.
                    client = hooks.get("editor_client")
                    if client is None:
                        client, _m = writing._client("editor")
                    r = edit.d_correction_pass(episode, client)
                    entry["did"] = (f"D correction applied to the candidate "
                                    f"({r['applied']} pair(s); changed={r['changed']})")
                    log.append(entry)
                    return _stop(log, {"stage": stage, "macro": macro}, "touchpoint",
                                 "D — REVISED candidate ready; `lwm decide D --approve` "
                                 "or `--corrections …`", True)
                if row and row.status.startswith("candidate ready"):
                    return _stop(log, entry, "touchpoint",
                                 "D — ONE final candidate at 10-final-candidate.md; "
                                 "`lwm decide D --approve` or `--corrections …`", True)
                # Prepare the one candidate from the completed back-half.
                text = (episode / "07-draft.md").read_text()
                (episode / "10-final-candidate.md").write_text(text)
                ledger.update_row(episode, "10 ear loop + locks", status="candidate ready",
                                  notes="one candidate prepared from the edit/gate/pace train (touchpoint D)")
                entry["did"] = "final candidate prepared"
                log.append(entry)
                return _stop(log, {"stage": stage, "macro": macro}, "touchpoint",
                             "D — ONE final candidate; `lwm decide D --approve` or `--corrections …`", True)
            elif stage == "10b script fact-check (D-SFC-1)":
                locked = decisions.locked_script(episode)
                if not locked:
                    raise RuntimeError("10b requires the LOCKED script (touchpoint D approval); none exists")
                script_path, sha = locked
                row = rows.get(stage)
                if row and row.status.startswith("material findings") and sha in row.notes:
                    # The check already ran against THIS sha and found material
                    # blockers. Re-running it changes nothing — the way forward
                    # is Maz's ruling through the D correction path. No loop.
                    return _stop(log, entry, "contradiction",
                                 "Final Check found material blockers on the current locked "
                                 "script — resolve via `lwm decide D --corrections …` "
                                 "(10b-fact-check.md has the findings)", True)
                client = hooks.get("judge_client")
                if client is None:
                    from backend.config import get_settings
                    from backend.integrations.structured_client import get_structured_client
                    client = get_structured_client(get_settings().model_judge)
                report = factcheck.run(script_path, episode, client,
                                       search=hooks.get("search"), fetch=hooks.get("fetch"),
                                       lb_claims=factcheck.load_bearing_claims(episode))
                ledger.update_row(episode, stage,
                                  status="done" if not report["blocks_recording"] else "material findings",
                                  gate="verdicts: " + " · ".join(f"{k} {v}" for k, v in report["counts"].items()),
                                  notes=(f"checked locked script {sha}; "
                                         + ("nothing material blocks recording" if not report["blocks_recording"]
                                            else f"{report['material_findings']} material blocker(s) → Maz ruling")))
                entry["did"] = f"fact-check on locked {sha}: {report['claims_checked']} claims"
                if report["blocks_recording"]:
                    log.append(entry)
                    return _stop(log, {"stage": stage, "macro": macro}, "contradiction",
                                 f"{report['material_findings']} material blocker(s) need Maz's ruling "
                                 "(10b-fact-check.md)", True)
            elif stage == "11 production package":
                locked = decisions.locked_script(episode)
                if not locked:
                    raise RuntimeError("stage 11 requires the LOCKED script; none exists")
                production.build(episode, locked[0])
                entry["did"] = f"production package from locked {locked[1]}"
            else:
                return _stop(log, entry, "failure", f"no internal runner for stage {stage!r}", False)
        except Exception as e:
            logger.exception(f"lwm continue: stage {stage!r} failed")
            return _stop(log, entry, "failure", f"{stage}: {e}", False)
        log.append(entry)
    return log
