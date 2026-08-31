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
from backend.pipeline.briefing_routing import below_the_line, qualifying_players

_BARE_ID = re.compile(r"\b(?:CLM|SRC|KP|TEN|GAP|STG|HOLE|QT|OBS|THEME)_\d+\b")

# An inline introduction is an appositive around the name: "Eric Uphill, the
# Middle Kingdom specialist, argued...", or "the Egyptologist Eric Uphill".
# An appositive after the name is a comma, a lower-case phrase that is not a
# conjunction, and a closing comma. Matching the SHAPE rather than a list of
# opening words is what lets "Timothy Akers, one of the Hawara researchers,"
# count — a valid introduction the old word list rejected because it did not
# begin with "a", "an", or "the".
_APPOSITIVE_AFTER = re.compile(
    r"^\s*,\s*(?!and\b|or\b|but\b|so\b)[a-z][\w'\u2019-]*(?:\s+[^,]{1,60})?,"
)
# A leading appositive: "the geologist who dated the Sphinx, Robert Schoch's".
# The trailing comma is optional because both "the scholar X" and "the scholar
# X," precede a name legitimately.
# How far past a name to look for its closing comma. Long enough for a full
# appositive clause; see _is_introduced.
_APPOSITIVE_WINDOW = 160

_APPOSITIVE_BEFORE = re.compile(
    r"(?:^|[.;:]\s|,\s|\(|\s)(?:the|a|an)\s+[\w'-]+(?:\s+[\w'-]+){0,6}\s*,?\s*$",
    re.I,
)

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


def check_player_cards(briefing, people=None) -> list[str]:
    """Names that recur across sections must have a card.

    Args:
        briefing: The assembled Briefing.
        people: Names confirmed to be people at build time. Without it the
            rule demands a Players card for "Historic Mysteries" and "Why
            Files" — a website and a section heading — because the action-verb
            test cannot tell a person from a thing that acts.

    Returns:
        One error per name that earned a card and did not get one.
    """
    sections = _sections_of(briefing)
    carded = {player.name.lower() for player in briefing.players}
    # Same function the pass uses, so the lint enforces the rule as applied:
    # 2+ sections, an actor rather than a place, aliases merged, capped.
    return [
        f"{name} recurs across sections but has no card in The Players"
        for name in qualifying_players(sections)
        if name.lower() not in carded and (people is None or name in people)
    ]


def _sections_of(briefing) -> dict[str, str]:
    """The prose of each section, as the player rules read it."""
    return {
        "read": " ".join([briefing.read.lede] + [p.text for p in briefing.read.paragraphs]),
        "record": " ".join(f"{e.what} {e.context or ''}" for e in briefing.record),
        "files": " ".join(f.body for f in briefing.files),
        "disputes": " ".join(
            f"{d.claim} {d.holders} {d.case_for.text} {d.case_against.text}"
            for d in briefing.disputes
        ),
        "anecdotes": " ".join(f"{a.text} {a.context or ''}" for a in briefing.anecdotes),
    }


def _is_introduced(text: str, position: int, name: str) -> bool:
    """Is this appearance of a name introduced where it stands?

    Args:
        text: The passage.
        position: Where the name starts.
        name: The name itself.

    Returns:
        True when an appositive sits immediately before or after the name.
    """
    # The window has to outrun the appositive itself. At 40 characters a long
    # gloss lost its closing comma to the truncation ("Walter Birkby, the
    # forensic anthropologist assisting |him,"), the pattern failed to match,
    # and the repair spliced a SECOND appositive onto a name that already had
    # one. Found live in the 2026-08-31 Packer briefing.
    after = text[position + len(name): position + len(name) + _APPOSITIVE_WINDOW]
    before = text[max(0, position - 80): position]
    return bool(_APPOSITIVE_AFTER.match(after) or _APPOSITIVE_BEFORE.search(before))


def check_inline_introductions(briefing, people=None) -> list[str]:
    """Names below the card cap must be introduced wherever they appear.

    The owner amendment to D-025 (2026-08-19) capped the cast at 14 and put
    everyone below the line on the one-off rule, so a reader never meets a name
    cold. This is the enforcement half of that amendment.

    Args:
        briefing: The assembled Briefing.
        people: Names confirmed to be people, from the build-time
            classification. None checks every ranked name, which over-fires on
            places and technologies — see `below_the_line`.

    Returns:
        One error per appearance that arrives without an introduction.
    """
    sections = _sections_of(briefing)
    findings = []

    for name in below_the_line(sections, people=people):
        for section, text in sections.items():
            # The FIRST occurrence in a section is where the reader meets the
            # name; once introduced there, later mentions in the same section
            # are not cold. Checking every occurrence instead demanded the same
            # gloss four times in one section, which reads worse than the
            # problem it fixes.
            match = re.search(re.escape(name), text or "")
            if match and not _is_introduced(text, match.start(), name):
                findings.append(
                    f"{name} appears in {section} with no card and no inline "
                    f"introduction; say who they are where the reader meets them"
                )
    return findings


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


def lint_briefing(briefing, people=None) -> BriefingLintResult:
    """Run the document-level checks over an assembled Briefing.

    Args:
        briefing: The assembled Briefing.
        people: Names confirmed to be people at build time. Passing them keeps
            the one-off rule off places, eras, and technologies.

    Returns:
        BriefingLintResult. `passes` is False only when there are errors.
    """
    return BriefingLintResult(
        errors=check_player_cards(briefing, people=people)
        + check_named_citations(briefing)
        + check_inline_introductions(briefing, people=people),
        advisories=check_staging_disclosure(briefing),
    )
