"""Lint that only makes sense on a whole Briefing.

The text-level lint (style_enforcer) sees one passage at a time. Three of
D-025's rules are about the document as a whole, so they live here (work order
item 15):

- **Players threshold.** A name that appears in two or more sections gets a
  card. Otherwise a reader meets someone for the third time still not knowing
  who they are.
- **Named citations in prose.** Sources are named the way a person names them
  ("Johanna's video adds"); bare IDs belong in the trailing tag, which the
  renderer writes from `source_ids`. An ID inside a sentence is a leak.
- **Staging disclosure.** When a source dramatizes a fact rather than
  reporting it, the document says so and says where the underlying fact lives.

Errors here block a render. Advisories report and let it through.
"""

import re
from dataclasses import dataclass, field

from backend.pipeline.briefing_gates import briefing_prose
from backend.pipeline.briefing_routing import PLAYER_SECTION_THRESHOLD, names_by_section

_BARE_ID = re.compile(r"\b(?:CLM|SRC|KP|TEN|GAP|STG|HOLE|QT|OBS|THEME)_\d+\b")

# Words that mark a source performing a fact rather than reporting it
_STAGING_WORDS = re.compile(
    r"\b(re-?enact\w*|dramatiz\w*|dramatis\w*|stages? (?:this|it|the)|"
    r"staged|recreation|recreated|acted out|voiced over|illustrat\w+ scene)\b",
    re.I,
)

# Phrases that satisfy the disclosure once staging is present
_DISCLOSURE_WORDS = re.compile(
    r"\b(the underlying|the fact itself|as (?:told|reported) (?:by|in)|"
    r"the record for this|documented in|comes from|sourced (?:to|from)|"
    r"originates (?:with|in))\b",
    re.I,
)


@dataclass
class BriefingLintResult:
    """Findings from the document-level checks."""

    errors: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)

    @property
    def passes(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "passes": self.passes,
            "errors": self.errors,
            "advisories": self.advisories,
        }


def check_player_cards(briefing) -> list[str]:
    """Names that recur across sections must have a card.

    Args:
        briefing: The assembled Briefing.

    Returns:
        One error per name that earned a card and did not get one.
    """
    sections = {
        "read": " ".join([briefing.read.lede] + [p.text for p in briefing.read.paragraphs]),
        "record": " ".join(f"{e.what} {e.context or ''}" for e in briefing.record),
        "files": " ".join(f.body for f in briefing.files),
        "disputes": " ".join(
            f"{d.claim} {d.holders} {d.case_for.text} {d.case_against.text}"
            for d in briefing.disputes
        ),
        "anecdotes": " ".join(f"{a.text} {a.context or ''}" for a in briefing.anecdotes),
    }
    carded = {player.name.lower() for player in briefing.players}
    appearances = names_by_section(sections)

    return [
        f"{name} appears in {len(where)} sections ({', '.join(sorted(where))}) "
        f"but has no card in The Players"
        for name, where in sorted(appearances.items())
        if len(where) >= PLAYER_SECTION_THRESHOLD and name.lower() not in carded
    ]


def check_named_citations(briefing) -> list[str]:
    """Bare source IDs must not appear inside prose.

    Args:
        briefing: The assembled Briefing.

    Returns:
        One error per prose field carrying a bare ID.
    """
    findings = []
    for where, text in briefing_prose(briefing):
        leaked = sorted(set(_BARE_ID.findall(text or "")))
        if leaked:
            findings.append(
                f"{where} names sources by ID in the prose ({', '.join(leaked)}); "
                f"name them the way a person would and leave IDs to the citation tag"
            )
    return findings


def check_staging_disclosure(briefing) -> list[str]:
    """Where a source performs a fact, the document must say where the fact lives.

    Args:
        briefing: The assembled Briefing.

    Returns:
        One advisory per passage that describes staging without disclosure.
    """
    findings = []
    for where, text in briefing_prose(briefing):
        if _STAGING_WORDS.search(text or "") and not _DISCLOSURE_WORDS.search(text or ""):
            findings.append(
                f"{where} describes a source performing a fact without saying where "
                f"the underlying fact lives"
            )
    return findings


def lint_briefing(briefing) -> BriefingLintResult:
    """Run the document-level checks over an assembled Briefing.

    Args:
        briefing: The assembled Briefing.

    Returns:
        BriefingLintResult. `passes` is False only when there are errors.
    """
    return BriefingLintResult(
        errors=check_player_cards(briefing) + check_named_citations(briefing),
        advisories=check_staging_disclosure(briefing),
    )
