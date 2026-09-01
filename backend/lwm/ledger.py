"""Read and update STAGE-LEDGER.md — the only detailed state authority.

The ledger is a markdown table maintained by humans and agents alike, so this
module edits rows in place and never regenerates the file: prose notes above
and below the table survive every update. A gate result that isn't written
here didn't happen.

ORDER (D-V1-6, 2026-09-01): research precedes the angle. The creator flow is
INPUT → RESEARCH → BRIEF → ANGLE → PACKAGING → STORY → SCRIPT → FINAL CHECK →
PRODUCTION. The stage KEYS below keep their historical numbers on purpose —
renaming fourteen identifiers across three repositories is churn this project
has paid for before, and the creator UI never shows a stage ID. The ORDER of
this list, not the number inside a key, is what the machine runs on. Old keys
that were split or merged resolve through ALIASES so every existing ledger,
test and script keeps working.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Ledger stage keys, in PIPELINE ORDER, with the macro state each belongs to.
# Mirrors pipeline/STATE-MAP.md — change both together.
STAGES: list[tuple[str, str]] = [
    ("0 bootstrap", "INPUT"),
    ("3 brief", "RESEARCH"),
    ("4 fact-check the brief", "BRIEF"),
    ("4b briefing", "BRIEF"),
    ("1 angle", "ANGLE"),
    ("1b packaging", "PACKAGING"),
    ("2 feasibility + format", "PACKAGING"),
    ("4c story architecture", "STORY"),
    ("5 outline", "STORY"),
    ("6 grip gate A", "STORY"),
    ("7 draft", "SCRIPT"),
    ("8 edit", "SCRIPT"),
    ("9 grip gate B", "SCRIPT"),
    ("9b pace edit", "SCRIPT"),
    ("10 ear loop + locks", "SCRIPT"),
    ("10b script fact-check (D-SFC-1)", "FINAL CHECK"),
    ("11 production package", "PRODUCTION"),
    ("12 record + booth diff", "RECORDED"),
    ("13 assemble + final review", "PUBLISHED"),
    # 14 harvest is post-publish internal work: excluded from projection.
]

# The creator-facing journey, in order. PUBLISHED is the terminal projection.
MACRO_STATES = ["INPUT", "RESEARCH", "BRIEF", "ANGLE", "PACKAGING", "STORY",
                "SCRIPT", "FINAL CHECK", "PRODUCTION", "RECORDED", "PUBLISHED"]

# Pre-patch stage keys → the canonical key that now carries their state.
# "1 angle + packaging" carried angle AND packaging; under D-V1-8 those are
# separate stages, and the old key resolves to the angle row (where the
# creative decision lives). Two old keys may map to one new row; that is
# intended — the migration carries the strongest recorded status across.
ALIASES: dict[str, str] = {
    "1 angle + packaging": "1 angle",
    "4b briefing + structure session": "4b briefing",
}

# A row counts as complete when its status starts with one of these.
COMPLETE = ("done", "decided", "pass", "published", "recorded", "complete", "waived",
            "locked", "chosen")


@dataclass
class Row:
    stage: str
    status: str
    date: str
    gate: str
    notes: str

    @property
    def complete(self) -> bool:
        return self.status.strip().lower().startswith(COMPLETE)


def canonical(stage: str) -> str:
    """The canonical key for a stage name, resolving pre-patch aliases."""
    return ALIASES.get(stage, stage)


def _ledger_path(episode: Path) -> Path:
    return episode / "STAGE-LEDGER.md"


def read_rows(episode: Path) -> dict[str, Row]:
    """Rows by canonical key, plus every alias pointing at the same Row.

    Callers written before the D-V1-6 reorder keep working unchanged: they ask
    for the key they know and get the row that now holds that state.
    """
    rows: dict[str, Row] = {}
    for line in _ledger_path(episode).read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] in ("stage", "---"):
            continue
        rows[cells[0]] = Row(*cells[:5])
    for old, new in ALIASES.items():
        if new in rows and old not in rows:
            rows[old] = rows[new]
        elif old in rows and new not in rows:
            rows[new] = rows[old]
    return rows


def update_row(episode: Path, stage: str, status: str | None = None,
               gate: str | None = None, notes: str | None = None,
               when: str | None = None) -> None:
    """Rewrite one row's cells, leaving the rest of the file untouched."""
    p = _ledger_path(episode)
    wanted = {stage, canonical(stage)}
    out = []
    hit = False
    for line in p.read_text().splitlines(keepends=True):
        if line.startswith("|") and not hit:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 5 and cells[0] in wanted:
                if status is not None:
                    cells[1] = status
                cells[2] = when or (cells[2] if status is None else str(date.today()))
                if gate is not None:
                    cells[3] = gate
                if notes is not None:
                    cells[4] = notes
                line = "| " + " | ".join(cells) + " |\n"
                hit = True
        out.append(line)
    if not hit:
        raise KeyError(f"ledger row not found: {stage!r} in {p}")
    p.write_text("".join(out))


def macro_state(episode: Path) -> tuple[str, str]:
    """Project the ledger onto the creator flow's macro states.

    Returns (macro_state, earliest_incomplete_stage). An episode whose stage
    13 is complete is PUBLISHED regardless of anything later — stage 14 never
    regresses it.
    """
    rows = read_rows(episode)
    for stage, macro in STAGES:
        row = rows.get(stage)
        if row is None or not row.complete:
            return macro, stage
    return "PUBLISHED", ""


# Stage 14 is post-publish internal work: it lives in the table but never in
# the projection, so the migration carries it explicitly.
_TABLE_TAIL = ("14 harvest", "")

# Gate-cell hints for rows the migration has to create from nothing. They are
# prompts for whoever fills the row, not state.
_GATE_HINT = {
    "1 angle": "KILL gate:",
    "1b packaging": "packaging concepts:",
    "2 feasibility + format": "KILL gate:",
    "4b briefing": "briefing ready:",
    "4c story architecture": "architecture recorded:",
    "5 outline": "coverage: SOLID/PRECISION-RISK/THIN",
    "6 grip gate A": "PASS/FAIL:",
    "8 edit": "cycles used:",
    "9 grip gate B": "PASS/FAIL:",
    "9b pace edit": "words before → after:",
    "10 ear loop + locks": "locks:",
    "10b script fact-check (D-SFC-1)": "verdicts:",
    "12 record + booth diff": "errors found:",
}


def rewrite_table(episode: Path) -> dict:
    """Migrate a ledger onto the D-V1-6 stage set and order, losing no state.

    Rows keep their status/date/gate/notes; renamed rows are carried across by
    ALIASES; rows the new flow adds appear empty. Prose above and below the
    table survives. Idempotent — running it on a migrated ledger is a no-op.
    """
    p = _ledger_path(episode)
    text = p.read_text()
    old = read_rows(episode)

    ordered = [s for s, _ in STAGES] + [_TABLE_TAIL[0]]
    seen: set[str] = set()
    new_lines = ["| stage | status | date | gate result | notes |",
                 "|---|---|---|---|---|"]
    carried, created = 0, 0
    for stage in ordered:
        row = old.get(stage)
        if row is not None and row.stage in seen:
            row = None  # two old keys collapsed onto one row: keep the first
        if row is not None:
            seen.add(row.stage)
            carried += 1
            cells = [stage, row.status, row.date, row.gate, row.notes]
        else:
            created += 1
            cells = [stage, "", "", _GATE_HINT.get(stage, "—"), ""]
        new_lines.append("| " + " | ".join(cells) + " |")

    lines = text.splitlines(keepends=True)
    first = next((i for i, ln in enumerate(lines) if ln.startswith("|")), None)
    if first is None:
        raise ValueError(f"{p} has no ledger table")
    last = first
    while last < len(lines) and lines[last].startswith("|"):
        last += 1
    p.write_text("".join(lines[:first]) + "\n".join(new_lines) + "\n" + "".join(lines[last:]))
    return {"episode": episode.name, "carried": carried, "created": created}
