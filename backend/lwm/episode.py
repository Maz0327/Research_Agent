"""Episode lifecycle: create from _TEMPLATE, resolve, report status.

State never lives here — it lives in the episode's STAGE-LEDGER.md and
SOURCE-MANIFEST.json; this module derives and reports.
"""

import re
import shutil
from datetime import date
from pathlib import Path

from backend.lwm import ledger, manifest, paths

# Episode numbers >= this are reserved for scoped tests (99-hawara-grip-test).
_RESERVED_FROM = 90


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "-".join(s.split("-")[:5]) or "untitled"


def next_number() -> int:
    highest = 0
    for d in paths.episodes_dir().iterdir():
        m = re.match(r"^(\d+)-", d.name)
        if m and int(m.group(1)) < _RESERVED_FROM:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def create(idea: str, sources: list[str] | None = None, offline: bool = False) -> dict:
    """One operation: template copy, slug, manifest, pointer, ledger. No hand-editing.

    `idea` may be a topic, a sentence, or empty when the episode is
    sources-only ("there may be a video here").
    """
    sources = sources or []
    if not idea and not sources:
        raise ValueError("an episode needs an idea, at least one source, or both")

    title_seed = idea or "untitled sources-first episode"
    slug = f"{next_number():02d}-{_slugify(title_seed)}"
    dest = paths.episode_dir(slug)
    if dest.exists():
        raise FileExistsError(f"episode already exists: {dest} — refusing to overwrite")

    shutil.copytree(paths.template_dir(), dest)

    # 00-candidate carries the idea verbatim; sources-only episodes say so.
    (dest / "00-candidate.md").write_text(
        f"# Candidate\n\n**Idea (verbatim):** {idea or '(none — sources-first: “there may be a video here”)'}\n\n"
        f"Created {date.today()} via `lwm new`.\n"
    )

    entries = []
    for raw in sources:
        entries.append(manifest.add_source(dest, raw, role="seed", offline=offline))
    if not manifest.manifest_path(dest).exists():
        manifest.save(dest, manifest.load(dest))

    ledger.update_row(dest, "0 bootstrap", status="done", gate="—",
                      notes="created via lwm new; manifest initialized")
    paths.set_active_episode(slug)

    return {"slug": slug, "path": str(dest), "sources": entries,
            "next_action": status(slug)["next_action"]}


def resolve(slug: str | None = None) -> Path:
    """The active episode, from the ONE pointer. Never guessed from mtimes."""
    slug = slug or paths.read_active_episode()
    if not slug:
        raise FileNotFoundError("no active episode: pipeline/ACTIVE-EPISODE.txt is missing or empty")
    d = paths.episode_dir(slug)
    if not d.exists():
        raise FileNotFoundError(f"ACTIVE-EPISODE points at {slug!r} but {d} does not exist")
    return d


# What a caller does next, per earliest-incomplete stage. (human text, maz_needed)
# Order is the D-V1-6 creator flow: research precedes the angle.
_NEXT = {
    "0 bootstrap": ("initialize the episode", False),
    "3 brief": ("run research (`lwm continue` executes the Research Agent round)", False),
    "4 fact-check the brief": ("populate the registry from the RA job (`lwm continue`)", False),
    "4b briefing": ("render the Briefing from the research (`lwm continue`)", False),
    "1 angle": ("TOUCHPOINT ANGLE — Maz chooses the story: baseline, an alternative, "
                "his previous idea, or his own (`lwm decide angle …`)", True),
    "1b packaging": ("build packaging concepts for the chosen angle (`lwm continue`)", False),
    "12 record + booth diff": ("Maz records, then marks it recorded (`lwm decide recorded`)", True),
    "2 feasibility + format": ("format is the settled default (D-V1-13) — `lwm continue` records it", False),
    "4c story architecture": ("TOUCHPOINT STORY — Maz reads the Briefing; structure session "
                              "or explicit waiver (`lwm decide B …`)", True),
    "5 outline": ("build the dense, coverage-classified outline (`lwm continue`)", False),
    "6 grip gate A": ("internal grip advisory on the outline (`lwm continue`)", False),
    "7 draft": ("draft/advance movements — `lwm continue`; TOUCHPOINT C clears via `lwm decide C`", False),
    "8 edit": ("internal review + edit train: reviewers, lint, constructive editor (`lwm continue`)", False),
    "9 grip gate B": ("internal grip advisory on full prose (`lwm continue`)", False),
    "9b pace edit": ("internal pace edit (`lwm continue`)", False),
    "10 ear loop + locks": ("prepare the ONE final candidate; TOUCHPOINT D clears via `lwm decide D`", False),
    "10b script fact-check (D-SFC-1)": ("fact-check the LOCKED script (`lwm continue` / `lwm check-script`)", False),
    "11 production package": ("generate the production package (`lwm package`)", False),
    "13 assemble + final review": ("assemble per PRODUCTION-ASSEMBLY-PIPELINE; publish", True),
}


def status(slug: str | None = None) -> dict:
    """The Phase 2 contract's status payload. Everything derived, nothing stored."""
    ep = resolve(slug)
    macro, stage = ledger.macro_state(ep)
    rows = ledger.read_rows(ep)
    data = manifest.load(ep)

    idea = ""
    cand = ep / "00-candidate.md"
    if cand.exists():
        m = re.search(r"\*\*Idea \(verbatim\):\*\* (.+)", cand.read_text())
        idea = m.group(1) if m else ""

    artifacts = {}
    for key, name in [("briefing", "04b-briefing.md"), ("briefing_html", "04b-briefing.html"),
                      ("angle_options", "01-angle-options.md"),
                      ("angle_options_json", "outputs/angle-options.json"),
                      ("packaging", "01b-packaging.md"),
                      ("packaging_json", "outputs/packaging.json"),
                      ("architecture", "04c-story-architecture.md"),
                      ("architecture_json", "outputs/story-architecture.json"),
                      ("outline_json", "outputs/outline.json"),
                      ("tripwire", "outputs/tripwire.json"),
                      ("production_json", "editing/production-package.json"),
                      ("outline", "05-outline.md"), ("draft", "07-draft.md"),
                      ("review_findings", "08-review-findings.md"),
                      ("lint_findings", "outputs/lint-findings.json"),
                      ("final_candidate", "10-final-candidate.md"),
                      ("fact_check", "10b-fact-check.md"),
                      ("fact_check_json", "10b-fact-check.json"),
                      ("correction_log", "10-correction-pass.md"),
                      ("production_package", "11-production-package.md"),
                      ("manifest", "SOURCE-MANIFEST.json"), ("ledger", "STAGE-LEDGER.md")]:
        p = ep / name
        # Keys whose file exists as a tiny stub in _TEMPLATE need a size floor
        # so the stub never masquerades as a real artifact; everything else
        # (fact-check json, manifests, correction logs) is real by existence.
        stubby = key in ("briefing", "briefing_html", "outline", "draft", "production_package")
        floor = 1200 if stubby else 1
        artifacts[key] = str(p) if p.exists() and p.stat().st_size >= floor else None
    artifacts["ledger"] = str(ep / "STAGE-LEDGER.md")
    artifacts["manifest"] = str(manifest.manifest_path(ep)) if manifest.manifest_path(ep).exists() else None

    next_text, maz = _NEXT.get(stage, ("—", False)) if stage else ("published", False)

    # A named kill is a terminal state of its own (STATE-MAP), but the stage
    # projection cannot express it: the row is simply never complete, so the
    # episode would otherwise read as "still at the angle, press Continue"
    # forever. Report it so a UI can stop offering to carry on.
    killed_row = next((r for r in rows.values() if r.status.strip().upper() == "KILLED"), None)
    killed = ({"stage": killed_row.stage, "when": killed_row.date, "why": killed_row.notes}
              if killed_row else None)

    # Waiting-on-Maz states inside internal stages: C (M1 at the ear) and D
    # (candidate ready) flip maz_needed live, from the ledger, not from a map.
    row = rows.get(stage) if stage else None
    # ANGLE and STORY are creator decisions, but the system lays the options
    # out FIRST. Until the options exist the move is the system's, not Maz's —
    # he is never summoned to an empty page.
    if stage == "1 angle":
        if row and row.status.startswith("options ready"):
            next_text, maz = ("TOUCHPOINT ANGLE — choose the story: baseline, an alternative, "
                              "your previous idea, or your own"), True
        else:
            next_text, maz = "the system can lay out the angle options (`lwm continue`)", False
    if stage == "1b packaging":
        if row and row.status.startswith("concepts ready"):
            next_text, maz = ("TOUCHPOINT PACKAGING — pick the title and thumbnail concept "
                              "(`lwm decide packaging …`)"), True
        else:
            next_text, maz = "the system can work up titles and thumbnail concepts (`lwm continue`)", False
    if stage == "4c story architecture" and row and (
            row.status.startswith("structure decided") or row.status.startswith("structure waived")):
        next_text, maz = "the system can build the story architecture (`lwm continue`)", False
    if stage == "7 draft" and row and row.status.startswith("M1 drafted"):
        next_text, maz = "TOUCHPOINT C — Maz hears Movement 1; `lwm decide C --approve` / `--correction`", True
    if stage == "10 ear loop + locks" and row and row.status.startswith("candidate ready"):
        next_text, maz = "TOUCHPOINT D — approve the final candidate; `lwm decide D --approve` / `--corrections`", True
    if stage == "10 ear loop + locks" and row and row.status.startswith("corrections requested"):
        next_text, maz = "the system applies your correction to the candidate (`lwm continue`)", False
    if stage == "10b script fact-check (D-SFC-1)" and row and row.status.startswith("material findings"):
        next_text, maz = "FINAL CHECK — needs your decision; correct via touchpoint D", True

    # How many sources the RESEARCH found, distinct from how many the creator
    # supplied. Packer supplied none and its research found eleven; a UI that
    # shows only the intake count reads as "this episode has no sources", which
    # is false and alarming. Derived from the job record already on disk — no
    # model call, no research touched.
    research_sources = None
    job_file = ep / "research" / "ra-job.json"
    if job_file.exists():
        try:
            import json as _json
            jobs = _json.loads(job_file.read_text())
            current = jobs.get("current")
            for job in jobs.get("jobs", []):
                if job.get("job_id") == current and job.get("sources"):
                    research_sources = job["sources"]
        except Exception:
            research_sources = None

    # A kill wins over every per-stage next action computed above: there is
    # nothing to continue.
    if killed:
        next_text, maz = "this video was killed", False

    from backend.lwm import decisions as _dec
    locked = _dec.locked_script(ep)
    blockers = [f"{s['id']}: {'; '.join(s['errors'])}" for s in data["sources"] if s.get("errors")]

    return {
        "episode": ep.name,
        "active": paths.read_active_episode() == ep.name,
        "topic": idea,
        "macro_state": macro if stage else "PUBLISHED",
        "detailed_stage": stage or "complete",
        "detailed_stage_status": (rows.get(stage).status if stage and rows.get(stage) else ""),
        "next_action": next_text,
        "maz_needed": maz,
        "sources": [
            {k: s.get(k) for k in ("id", "type", "title", "canonical", "role",
                                    "ingestion_status", "transcript_status",
                                    "ra_source_id", "errors", "preserved_path")}
            for s in data["sources"]
        ],
        "research_sources": research_sources,
        "killed": killed,
        "artifacts": artifacts,
        "final_script": ({"path": str(locked[0]), "sha": locked[1], "locked": True}
                         if locked else None),
        "blockers": blockers,
    }


def list_all() -> list[dict]:
    """Every episode's creator-facing state, derived from its own ledger.

    Read-only; tolerant of scoped/legacy episodes whose ledgers are partial —
    a row it cannot project honestly reports what it can and marks itself.
    """
    active = paths.read_active_episode()
    rows = []
    for d in sorted(paths.episodes_dir().iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        try:
            s = status(d.name)
            rows.append({k: s[k] for k in ("episode", "topic", "macro_state",
                                            "detailed_stage", "next_action",
                                            "maz_needed", "research_sources", "killed")} | {
                "active": d.name == active,
                "sources": len(s["sources"]),
            })
        except Exception as e:
            rows.append({"episode": d.name, "topic": "", "macro_state": "UNKNOWN",
                         "detailed_stage": "", "next_action": f"unreadable: {e}",
                         "maz_needed": False, "research_sources": None, "killed": None,
                         "active": d.name == active, "sources": 0})
    # Active first, then by number.
    rows.sort(key=lambda r: (not r["active"], r["episode"]))
    return rows
