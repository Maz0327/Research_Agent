"""Read and update STAGE-LEDGER.md — the only detailed state authority.

The ledger is a markdown table maintained by humans and agents alike, so this
module edits rows in place and never regenerates the file: prose notes above
and below the table survive every update. A gate result that isn't written
here didn't happen.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Ledger stage keys, in pipeline order, with the STATE-MAP macro state each
# belongs to. Mirrors pipeline/STATE-MAP.md — change both together.
STAGES: list[tuple[str, str]] = [
    ("0 bootstrap", "TOPIC"),
    ("1 angle + packaging", "TOPIC"),
    ("2 feasibility + format", "TOPIC"),
    ("3 brief", "RESEARCH"),
    ("4 fact-check the brief", "RESEARCH"),
    ("4b briefing + structure session", "STORY"),
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

# A row counts as complete when its status starts with one of these.
COMPLETE = ("done", "decided", "pass", "published", "recorded", "complete", "waived")


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


def _ledger_path(episode: Path) -> Path:
    return episode / "STAGE-LEDGER.md"


def read_rows(episode: Path) -> dict[str, Row]:
    rows: dict[str, Row] = {}
    for line in _ledger_path(episode).read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] in ("stage", "---"):
            continue
        rows[cells[0]] = Row(*cells[:5])
    return rows


def update_row(episode: Path, stage: str, status: str | None = None,
               gate: str | None = None, notes: str | None = None,
               when: str | None = None) -> None:
    """Rewrite one row's cells, leaving the rest of the file untouched."""
    p = _ledger_path(episode)
    out = []
    hit = False
    for line in p.read_text().splitlines(keepends=True):
        if line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 5 and cells[0] == stage:
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
    """Project the ledger onto STATE-MAP's macro states.

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
