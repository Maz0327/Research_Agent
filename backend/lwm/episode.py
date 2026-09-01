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


# What a caller does next, per earliest-incomplete stage. (macro, human text, maz_needed)
_NEXT = {
    "0 bootstrap": ("initialize the episode", False),
    "1 angle + packaging": ("TOUCHPOINT A — Maz: angle, title/thumbnail promise, kill gate", True),
    "2 feasibility + format": ("TOUCHPOINT A — Maz: format decision (archive census)", True),
    "3 brief": ("run research (`lwm continue` executes the Research Agent round)", False),
    "4 fact-check the brief": ("populate the registry from the RA job (`lwm continue`)", False),
    "4b briefing + structure session": ("TOUCHPOINT B — Maz reads the Briefing; structure session or waiver", True),
    "5 outline": ("build the outline from the structure decisions (`lwm continue`)", False),
    "6 grip gate A": ("internal grip advisory on the outline (`lwm continue`)", False),
    "7 draft": ("draft Movement 1 → TOUCHPOINT C (~700-word ear check)", False),
    "8 edit": ("internal edit train: delta-scan, TIC pairs, lint (`lwm continue`)", False),
    "9 grip gate B": ("internal grip advisory on full prose (`lwm continue`)", False),
    "9b pace edit": ("internal pace edit (`lwm continue`)", False),
    "10 ear loop + locks": ("TOUCHPOINT D prep — assemble the one candidate script", False),
    "10b script fact-check (D-SFC-1)": ("run the final script fact-check (`lwm check-script`)", False),
    "11 production package": ("generate the production package (`lwm package`)", False),
    "12 record + booth diff": ("Maz records; booth diff after", True),
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
                      ("outline", "05-outline.md"), ("draft", "07-draft.md"),
                      ("fact_check", "10b-fact-check.md"),
                      ("production_package", "11-production-package.md"),
                      ("manifest", "SOURCE-MANIFEST.json"), ("ledger", "STAGE-LEDGER.md")]:
        p = ep / name
        # Template stubs are tiny; only a real artifact counts as available.
        artifacts[key] = str(p) if p.exists() and p.stat().st_size > 1200 else None
    artifacts["ledger"] = str(ep / "STAGE-LEDGER.md")
    artifacts["manifest"] = str(manifest.manifest_path(ep)) if manifest.manifest_path(ep).exists() else None

    next_text, maz = _NEXT.get(stage, ("—", False)) if stage else ("published — stage 14 harvest is internal", False)
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
        "artifacts": artifacts,
        "blockers": blockers,
    }
