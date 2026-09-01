"""`lwm continue` — run internal work until the next Maz touchpoint.

Deterministic resume, no daemon: resolve the ONE pointer, read the ledger,
do what is internal, stop where the V1 touchpoint policy says Maz is needed —
and nowhere else. Never resumes by modification time; never asks Maz to
adjudicate lint or reviewer flags.
"""

from dataclasses import dataclass

from loguru import logger

from backend.lwm import episode as ep
from backend.lwm import factcheck, handoff, ledger, production, research, writing

TOUCHPOINTS = {
    "1 angle + packaging": "A — topic/angle/packaging (kill gate is Maz's)",
    "2 feasibility + format": "A — format decision",
    "4b briefing + structure session": "B — read the Briefing; structure session or waiver",
    "12 record + booth diff": "record",
    "13 assemble + final review": "assemble/publish",
}


@dataclass
class StopPoint:
    reason: str          # touchpoint | kill | contradiction | failure | done
    detail: str
    maz_needed: bool


def step(slug: str | None = None, max_steps: int = 6, **hooks) -> list[dict]:
    """Advance the active episode until a stop condition. Returns the log.

    `hooks` lets tests inject clients/search/fetch; production uses defaults.
    """
    episode = ep.resolve(slug)
    log: list[dict] = []

    for _ in range(max_steps):
        macro, stage = ledger.macro_state(episode)
        entry = {"stage": stage, "macro": macro}

        if not stage:
            log.append({**entry, "stop": StopPoint("done", "episode is PUBLISHED", False).__dict__})
            break
        if stage in TOUCHPOINTS:
            log.append({**entry, "stop": StopPoint(
                "touchpoint", f"Maz touchpoint {TOUCHPOINTS[stage]}", True).__dict__})
            break

        rows = ledger.read_rows(episode)
        try:
            if stage == "3 brief":
                status = ep.status(episode.name)
                topic = status["topic"]
                result = research.run_round(episode, topic)
                if result.get("status") != "completed":
                    raise RuntimeError(f"research job {result.get('job_id')} did not complete: {result}")
                research.run_gap_rounds(episode, topic)
                entry["did"] = f"research round(s) complete — job {result['job_id']}"
            elif stage == "4 fact-check the brief":
                job_id = research.current_job_id(episode)
                if not job_id:
                    raise RuntimeError("stage 4 pending but no RA job recorded in research/ra-job.json")
                result = handoff.run_handoff(episode, job_id,
                                             docs_dir=hooks.get("docs_dir"),
                                             judgment_client=hooks.get("judgment_client"))
                entry["did"] = f"handoff: {result['registry_rows']} registry rows, briefing rendered"
            elif stage == "5 outline":
                writing.outline(episode, client=hooks.get("writer_client"))
                entry["did"] = "outline built"
            elif stage == "6 grip gate A":
                r = writing.grip_gate(episode, "05-outline.md", "6 grip gate A",
                                      clients=hooks.get("reader_clients"))
                entry["did"] = f"gate A internal: {r['yes']}/3 gripped"
            elif stage == "7 draft":
                row = rows.get("7 draft")
                if row and row.status.startswith("M1 drafted"):
                    # Movement 1 exists and awaits the ear — touchpoint C.
                    log.append({**entry, "stop": StopPoint(
                        "touchpoint", "C — Maz hears ~Movement 1 (700 words), once", True).__dict__})
                    break
                writing.draft_movement(episode, 1, client=hooks.get("writer_client"))
                entry["did"] = "movement 1 drafted — stopping for the ear"
                log.append(entry)
                log.append({"stage": stage, "macro": macro, "stop": StopPoint(
                    "touchpoint", "C — Maz hears ~Movement 1 (700 words), once", True).__dict__})
                return log
            elif stage in ("8 edit", "9 grip gate B", "9b pace edit", "10 ear loop + locks"):
                # Internal train: lint/edit log now; the full TIC/edit dispatch chain
                # runs inside the writing session per RUNBOOK — here we run what is
                # code (lint) and record. Gates advisory.
                if stage == "9 grip gate B":
                    r = writing.grip_gate(episode, "07-draft.md", "9 grip gate B",
                                          clients=hooks.get("reader_clients"))
                    entry["did"] = f"gate B internal: {r['yes']}/3 gripped"
                else:
                    note = writing.lint(episode)
                    ledger.update_row(episode, stage, status="done",
                                      notes=f"internal via lwm continue; lint tail: {note[:120]}")
                    entry["did"] = f"{stage} internal pass recorded"
            elif stage == "10b script fact-check (D-SFC-1)":
                script = episode / "07-draft.md"
                client = hooks.get("judge_client")
                if client is None:
                    from backend.config import get_settings
                    from backend.integrations.structured_client import get_structured_client
                    client = get_structured_client(get_settings().model_judge)
                report = factcheck.run(script, episode, client,
                                       search=hooks.get("search"), fetch=hooks.get("fetch"))
                ledger.update_row(episode, stage,
                                  status="done" if not report["blocks_recording"] else "material findings",
                                  gate="verdicts: " + " · ".join(f"{k} {v}" for k, v in report["counts"].items()),
                                  notes=("nothing material blocks recording" if not report["blocks_recording"]
                                         else f"{report['material_findings']} material finding(s) → Maz ruling"))
                entry["did"] = f"fact-check: {report['claims_checked']} claims"
                if report["blocks_recording"]:
                    log.append(entry)
                    log.append({"stage": stage, "macro": macro, "stop": StopPoint(
                        "contradiction", f"{report['material_findings']} material finding(s) need Maz's ruling", True).__dict__})
                    return log
            elif stage == "11 production package":
                production.build(episode, episode / "07-draft.md")
                entry["did"] = "production package generated"
            else:
                log.append({**entry, "stop": StopPoint(
                    "failure", f"no internal runner for stage {stage!r}", False).__dict__})
                break
        except Exception as e:
            logger.exception(f"lwm continue: stage {stage!r} failed")
            log.append({**entry, "stop": StopPoint("failure", f"{stage}: {e}", False).__dict__})
            break
        log.append(entry)
    return log
