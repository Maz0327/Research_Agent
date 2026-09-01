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

from backend.lwm import (
    architecture,
    decisions,
    edit,
    factcheck,
    handoff,
    ledger,
    outline as outline_mod,
    packaging,
    production,
    research,
    writing,
)
from backend.lwm import episode as ep

# Stages where Maz is genuinely needed, in the D-V1-6 order. The ANGLE stage is
# NOT here: the system first lays the options out (internal work), and only the
# "options ready" state stops for him — he is never summoned to an empty page.
TOUCHPOINTS = {
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
        if rows.get("1 angle") and rows["1 angle"].status == "KILLED":
            return _stop(log, entry, "kill", "episode was killed at the angle decision", False)
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
            elif stage == "4b briefing":
                # The briefing is a research artifact and the handoff renders
                # it; if it exists, the stage is simply complete.
                if not (episode / "04b-briefing.md").exists():
                    raise RuntimeError("stage 4b pending but no briefing was rendered by the handoff")
                ledger.update_row(episode, "4b briefing", status="done", when=str(date.today()),
                                  gate="briefing ready: YES",
                                  notes="research output; the structure session is stage 4c")
                entry["did"] = "briefing ready"
            elif stage == "1 angle":
                row = rows.get("1 angle")
                if row and row.status.startswith("options ready"):
                    return _stop(log, entry, "touchpoint",
                                 "ANGLE — the story choice is yours: baseline, an alternative, "
                                 "your previous idea, or your own "
                                 "(`lwm decide angle --baseline` / `--alt N` / `--previous` / "
                                 "`--custom \"…\"`)", True)
                from backend.lwm import angle as angle_mod
                r = angle_mod.build(episode, client=hooks.get("angle_client"))
                entry["did"] = (f"angle options laid out: baseline + {len(r['alternatives'])} "
                                f"alternative(s)"
                                + ("; the system reads the familiar story as strongest"
                                   if r["baseline_is_strongest"] else ""))
                log.append(entry)
                return _stop(log, {"stage": stage, "macro": macro}, "touchpoint",
                             "ANGLE — the story choice is yours (01-angle-options.md)", True)
            elif stage == "1b packaging":
                row = rows.get("1b packaging")
                if row and row.status.startswith("concepts ready"):
                    return _stop(log, entry, "touchpoint",
                                 "PACKAGING — pick the title and the thumbnail concept "
                                 "(`lwm decide packaging --title … --thumbnail …`)", True)
                r = packaging.build(episode, client=hooks.get("packaging_client"))
                entry["did"] = (f"packaging: {len(r['titles'])} titles, "
                                f"{len(r['thumbnails'])} thumbnail concepts (written only)")
                log.append(entry)
                return _stop(log, {"stage": stage, "macro": macro}, "touchpoint",
                             "PACKAGING — the title and thumbnail are your pick "
                             "(01b-packaging.md)", True)
            elif stage == "2 feasibility + format":
                # D-V1-13: the default format is settled. It is recorded, not asked.
                ledger.update_row(episode, "2 feasibility + format", status="decided",
                                  when=str(date.today()), gate="KILL gate: pass",
                                  notes="default format (D-V1-13): Maz on camera + real archival / "
                                        "press / documents / interviews / images first; AI "
                                        "reconstruction only for genuine visual gaps")
                entry["did"] = "format recorded from the settled default (D-V1-13)"
            elif stage == "4c story architecture":
                row = rows.get("4c story architecture")
                status = row.status if row else ""
                if not (status.startswith("structure decided") or status.startswith("structure waived")):
                    return _stop(log, entry, "touchpoint",
                                 "STORY — read the Briefing and tell us how to tell it; "
                                 "`lwm decide B --notes \"…\"` or `--waive`", True)
                r = architecture.build(episode, client=hooks.get("architecture_client"))
                entry["did"] = (f"story architecture: {r['macro_shape']} "
                                f"({len(r['movements'])} movements)")
            elif stage == "5 outline":
                r = outline_mod.build(episode, client=hooks.get("writer_client"))
                check = outline_mod.adversarial_check(episode, client=hooks.get("judge_client"))
                cov = r["coverage_summary"]
                entry["did"] = (f"dense outline: {cov['SOLID']} SOLID / "
                                f"{cov['PRECISION-RISK']} PRECISION-RISK / {cov['THIN']} THIN; "
                                f"{len(check['findings'])} adversarial finding(s)")
                if r["thin_movements"]:
                    # THIN movements are an upstream information failure. Backfill
                    # exactly what is missing — never a full RA rerun (§7).
                    from backend.lwm import backfill as backfill_mod
                    filled = []
                    for m in r["movements"]:
                        if m["coverage"] != "THIN":
                            continue
                        got = backfill_mod.run(episode, int(m["n"]),
                                               m.get("missing_material") or [],
                                               client=hooks.get("judge_client"),
                                               search=hooks.get("search"),
                                               fetch=hooks.get("fetch"))
                        after = backfill_mod.reclassify(episode, int(m["n"]))
                        filled.append({**got, "coverage_after": after["coverage"]})
                    still_thin = [f["movement"] for f in filled if f["coverage_after"] == "THIN"]
                    entry["did"] += (f"; targeted backfill on {len(filled)} movement(s)"
                                     + (f", still THIN: {still_thin}" if still_thin else
                                        ", all resolved"))
                    if still_thin:
                        ledger.update_row(episode, "5 outline",
                                          status="done (THIN movements held)",
                                          notes=f"movements {still_thin} remain THIN after targeted "
                                                "backfill — they do not reach the writer; the "
                                                "research, not the writing, is what is missing")
                        return _stop(log, {"stage": stage, "macro": macro}, "contradiction",
                                     f"movements {still_thin} have no material behind them even "
                                     "after targeted backfill. More drafting cannot fix this — "
                                     "the story needs sources or the outline needs to stop "
                                     "promising what the research does not hold.", True)
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
                r = edit.edit_train(episode, client,
                                    reviewer_client=hooks.get("reviewer_client"))
                counts = " · ".join(f"{k} {v}" for k, v in (r["review_counts"] or {}).items())
                ledger.update_row(
                    episode, "8 edit",
                    status="done" if not r["tripwire"] else "done (tripwire: STOP WRITING)",
                    gate=f"cycles used: {r['cycles']}/{edit.EDIT_CYCLE_CAP}",
                    notes=f"reviewers: {counts or '—'}; lint {r['lint_flags']} flags; "
                          f"{r['applied']} pairs applied, {r['rejected']} rejected — 08-edit-log.md")
                entry["did"] = (f"review + edit train: {r['applied']} applied / {r['rejected']} "
                                f"rejected in {r['cycles']} cycle(s); reviewers {counts or '—'}; "
                                f"lint {r['lint_flags']} flags")
                if r["tripwire"]:
                    log.append(entry)
                    owners = " · ".join(x["owner"] for x in r["tripwire"]["routes"])
                    return _stop(log, {"stage": stage, "macro": macro}, "contradiction",
                                 f"TWO-CYCLE TRIPWIRE: {r['tripwire']['material_findings']} "
                                 f"material finding(s) survived {edit.EDIT_CYCLE_CAP} correction "
                                 f"cycles. Stop writing — the defect is upstream ({owners}). "
                                 "See outputs/tripwire.json.", True)
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
