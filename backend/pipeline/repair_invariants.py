"""What a repair pass may never change.

Voice repair exists to fix how a document sounds. The danger is that it also
fixes what the document says: a rewritten sentence quietly loses a digit, a
tidied quotation stops being a quotation, a citation moves to the wrong claim.
That failure is invisible in review because the repaired text reads better.

So the facts are pinned. Quotes, numbers, dates, and citation IDs must survive
a repair byte for byte; anything else about the sentence may change (work order
H22). This complements the content-pipeline's fact-drift gate rather than
duplicating it: that one guards a script, this one guards the research
document it came from.
"""

import re
from dataclasses import dataclass, field

_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?")
_QUOTE = re.compile(r'"([^"]{8,400})"|“([^”]{8,400})”')
_ID = re.compile(r"\b(?:CLM|SRC|KP|TEN|GAP|STG|HOLE|QT|OBS|THEME)_\d+\b")
_DATE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\.?\s+\d{1,4}(?:,\s*\d{4})?\b|"
    r"\b\d{4}-\d{2}-\d{2}\b",
    re.I,
)


@dataclass
class InvariantReport:
    """What a repair changed that it was not allowed to change."""

    lost_numbers: list[str] = field(default_factory=list)
    lost_quotes: list[str] = field(default_factory=list)
    lost_dates: list[str] = field(default_factory=list)
    lost_ids: list[str] = field(default_factory=list)
    added_numbers: list[str] = field(default_factory=list)
    added_quotes: list[str] = field(default_factory=list)

    @property
    def holds(self) -> bool:
        """True when the repair touched voice only."""
        return not any(
            [
                self.lost_numbers,
                self.lost_quotes,
                self.lost_dates,
                self.lost_ids,
                self.added_numbers,
                self.added_quotes,
            ]
        )

    def to_dict(self) -> dict:
        return {
            "holds": self.holds,
            "lost_numbers": self.lost_numbers,
            "lost_quotes": self.lost_quotes,
            "lost_dates": self.lost_dates,
            "lost_ids": self.lost_ids,
            "added_numbers": self.added_numbers,
            "added_quotes": self.added_quotes,
        }

    def summary(self) -> str:
        """One line for a log or a warning."""
        if self.holds:
            return "repair invariants hold: no fact changed"
        parts = []
        for label, values in (
            ("numbers lost", self.lost_numbers),
            ("quotes lost", self.lost_quotes),
            ("dates lost", self.lost_dates),
            ("ids lost", self.lost_ids),
            ("numbers added", self.added_numbers),
            ("quotes added", self.added_quotes),
        ):
            if values:
                parts.append(f"{label}: {', '.join(v[:40] for v in values[:4])}")
        return "repair changed facts - " + "; ".join(parts)


def _numbers(text: str) -> list[str]:
    return [m.group(0).replace(",", "").rstrip(".") for m in _NUMBER.finditer(text or "")]


def _quotes(text: str) -> list[str]:
    return [
        (m.group(1) or m.group(2) or "").strip()
        for m in _QUOTE.finditer(text or "")
        if (m.group(1) or m.group(2))
    ]


def _dates(text: str) -> list[str]:
    return [m.group(0).strip() for m in _DATE.finditer(text or "")]


def _missing(before: list[str], after: list[str]) -> list[str]:
    """Items present before and not after, counting repeats."""
    remaining = list(after)
    lost = []
    for item in before:
        if item in remaining:
            remaining.remove(item)
        else:
            lost.append(item)
    return lost


def check_repair_invariants(before: str, after: str) -> InvariantReport:
    """Check that a repair changed voice and nothing else.

    Args:
        before: The text as it was.
        after: The text after the repair pass.

    Returns:
        An InvariantReport. `holds` is False when any fact moved.
    """
    report = InvariantReport()

    report.lost_numbers = _missing(_numbers(before), _numbers(after))
    report.added_numbers = _missing(_numbers(after), _numbers(before))
    report.lost_quotes = _missing(_quotes(before), _quotes(after))
    report.added_quotes = _missing(_quotes(after), _quotes(before))
    report.lost_dates = _missing(_dates(before), _dates(after))
    report.lost_ids = _missing(_ID.findall(before), _ID.findall(after))

    return report
