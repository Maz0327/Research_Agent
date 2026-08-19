"""The two mechanical gates on a generated Briefing.

They check opposite directions of the same trust question, and neither asks a
model anything.

**Coverage** (work order item 13) is the LOSS direction: everything the
harvest found should be somewhere in the document. The Files section is
lossless by definition, so a harvested fact the Briefing never says is a
reportable miss. There is no "omitted as unimportant" state, because that is
exactly the judgment a model must not be allowed to make about a researcher's
material.

**Grounding** (item 16a) is the INVENTION direction: every hard atom in the
document — numbers, dates, proper names, quoted strings — must appear in the
raw source text or in the harvest inventory. Unmatched means repair-or-strip,
never ship.

Honest limit, stated in the work order and worth repeating here: no mechanism
can PREVENT a model emitting off-corpus tokens. The guarantee is narrowed
inputs (each pass receives only its assigned facts and their raw paragraphs)
plus this deterministic post-check.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Optional

from backend.pipeline.text_similarity import content_tokens, statement_similarity

# A number, with thousands separators and decimals, optionally a percentage
_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?")

# A capitalized run, with the particles real names carry inside them:
# "Flinders Petrie", "Louis De Cordier", "Bank of England", "Merlin Burrows"
_NAME = re.compile(
    r"[A-Z][a-zA-Z'’-]+(?:\s+(?:of|the|de|del|van|von|al|bin)\s+[A-Z][a-zA-Z'’-]+|\s+[A-Z][a-zA-Z'’-]+)*"
)

# A single capitalized word that opens a sentence is usually just a sentence
# opening. Multi-word runs are still checked, and so is any single name that
# appears mid-sentence.
_SENTENCE_START = re.compile(r"(?:^|[.!?:;]\s+|\n\s*)$")

# Quoted strings, straight or curly. Capped in length because a "quotation"
# longer than this is almost always two quotes whose marks got paired wrong,
# not a citation anyone would check.
_QUOTE = re.compile(r'"([^"]{12,400})"|“([^”]{12,400})”')

# A span with sentence-ending punctuation in the middle of it is usually a
# mispaired quote rather than one long citation.
_LOOKS_MISPAIRED = re.compile(r"[.!?]\s+[A-Z]")

# Measured on the approved Hawara Briefing: below six words, quoted spans are
# titles and scare quotes, and checking them produced only false positives.
_MIN_QUOTE_WORDS = 6

# Markup that is never content
_TAG = re.compile(r"<[^>]+>")

# A quote this close to the corpus counts as present: transcripts drift on
# punctuation and filler, and a citation is not a byte comparison.
_QUOTE_MATCH_THRESHOLD = 0.85

# How close a harvested fact has to be to a passage to count as said
_FACT_MATCH_THRESHOLD = 0.55


@dataclass
class GateFinding:
    """One thing a gate objects to."""

    kind: str
    value: str
    where: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {"kind": self.kind, "value": self.value, "where": self.where, "detail": self.detail}


@dataclass
class GateReport:
    """The result of running one gate."""

    name: str
    checked: int = 0
    findings: list[GateFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict:
        return {
            "gate": self.name,
            "passed": self.passed,
            "checked": self.checked,
            "findings": [f.to_dict() for f in self.findings],
            "notes": self.notes,
        }

    def summary(self) -> str:
        """One line a human can read in a log."""
        verdict = "passed" if self.passed else f"FAILED with {len(self.findings)} finding(s)"
        return f"{self.name} gate {verdict} ({self.checked} checked)"


def normalize(text: str) -> str:
    """Fold text to the form both gates compare against.

    Args:
        text: Any text.

    Returns:
        Lowercased text with markup, curly quotes, and repeated whitespace
        normalized away.
    """
    text = _TAG.sub(" ", text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def numbers_in(text: str) -> set[str]:
    """Numeric atoms, with separators stripped so 1,200 == 1200."""
    return {m.group(0).replace(",", "").rstrip(".").lower() for m in _NUMBER.finditer(text or "")}


def names_in(text: str) -> set[str]:
    """Capitalized name TOKENS, checked one word at a time.

    Whole runs were measured against the approved Hawara Briefing and failed
    badly: 90 of 264 candidate runs did not appear verbatim in the corpus, all
    of them real names inside a possessive or a preposition ("Abbas of Egypt's
    NRIAG", "Brown's GPR"). Checking token by token drops that to near zero
    while still catching what matters - a person or place the corpus never
    mentions is a token that is absent.

    The honest limit: two real names combined into a false relationship pass,
    because every token exists. That is a claim error, not an atom error.

    Args:
        text: Prose to scan.

    Returns:
        Set of candidate name tokens, possessives stripped.
    """
    text = text or ""
    found = set()
    for match in _NAME.finditer(text):
        run = match.group(0).strip()
        run_is_single_word = " " not in run
        if run_is_single_word and _SENTENCE_START.search(text[: match.start()]):
            continue
        for token in run.split():
            # Possessives and contractions are grammar, not part of the name.
            token = re.sub(r"[’'][a-z]{1,2}$", "", token)
            # A hyphenated compound ("Roman-era", "SAR-scan") is grounded when
            # its parts are; the corpus rarely carries the compound itself.
            for part in token.replace("’", "'").strip("'-").split("-"):
                part = part.strip("'")
                if len(part) > 2 and part[:1].isupper():
                    found.add(part)
    return found


def quotes_in(text: str) -> set[str]:
    """Quoted passages long enough to be a citation, short enough to be one.

    Args:
        text: Prose to scan.

    Returns:
        Set of quoted passages worth verifying verbatim.
    """
    found = set()
    for match in _QUOTE.finditer(text or ""):
        quote = (match.group(1) or match.group(2) or "").strip()
        if not quote or _LOOKS_MISPAIRED.search(quote):
            continue
        # Below this length a quoted phrase is a title or a scare quote, not a
        # citation a reader would check against the source.
        if len(quote.split()) < _MIN_QUOTE_WORDS:
            continue
        found.add(quote)
    return found


def _quote_is_present(quote: str, corpus: str) -> bool:
    """Is this quoted passage in the corpus, allowing for transcript drift?"""
    needle = normalize(quote)
    if needle in corpus:
        return True

    # Fall back to token containment over a window of the corpus. Cheap and
    # good enough: a real quotation shares nearly all its words with its source.
    tokens = content_tokens(needle)
    if not tokens:
        return False
    present = sum(1 for token in tokens if token in corpus)
    return present / len(tokens) >= _QUOTE_MATCH_THRESHOLD


def briefing_prose(briefing) -> list[tuple[str, str]]:
    """Every piece of model-written prose in a Briefing, with its location.

    Args:
        briefing: A Briefing model.

    Returns:
        List of (where, text) pairs. Structural fields code produced (chips,
        IDs, dates placed by code) are deliberately not included: gates check
        what a model wrote.
    """
    prose: list[tuple[str, str]] = [("read.lede", briefing.read.lede)]
    for index, paragraph in enumerate(briefing.read.paragraphs):
        prose.append((f"read.paragraphs[{index}]", paragraph.text))
    for player in briefing.players:
        # The card's name is model-written too, so it is checked like any atom.
        prose.append(
            (f"players[{player.name}]", f"{player.name}, {player.role}. {player.body}")
        )
    for index, entry in enumerate(briefing.record):
        prose.append((f"record[{index}]", entry.what))
        if entry.context:
            prose.append((f"record[{index}].context", entry.context))
    for file in briefing.files:
        prose.append((f"files[{file.title}]", file.body))
    for index, dispute in enumerate(briefing.disputes):
        prose.append((f"disputes[{index}].claim", dispute.claim))
        prose.append((f"disputes[{index}].holders", dispute.holders))
        prose.append((f"disputes[{index}].for", dispute.case_for.text))
        prose.append((f"disputes[{index}].against", dispute.case_against.text))
    for index, anecdote in enumerate(briefing.anecdotes):
        prose.append((f"anecdotes[{index}]", anecdote.text))
        if anecdote.context:
            prose.append((f"anecdotes[{index}].context", anecdote.context))
    for index, gap in enumerate(briefing.info_gaps):
        prose.append((f"info_gaps[{index}]", f"{gap.question} {gap.why} {gap.go_get}"))
    for entry in briefing.source_trail:
        if entry.contribution:
            prose.append((f"source_trail[{entry.source_id}]", entry.contribution))
    return prose


def grounding_gate(
    briefing,
    raw_texts: Iterable[str],
    harvest_facts: Optional[Iterable[str]] = None,
) -> GateReport:
    """Check that every hard atom in the Briefing exists in the corpus.

    Args:
        briefing: The generated Briefing.
        raw_texts: Raw source texts (doc_0 `full_text` values).
        harvest_facts: Harvested fact statements, which are themselves derived
            from the raw text and carry its specifics in cleaner form.

    Returns:
        A GateReport. Findings are atoms the corpus does not contain.
    """
    corpus = normalize(" ".join(list(raw_texts) + list(harvest_facts or [])))
    corpus_numbers = numbers_in(corpus)
    report = GateReport(name="grounding")

    if not corpus.strip():
        report.notes.append("No raw text supplied; grounding could not be checked")
        return report

    for where, text in briefing_prose(briefing):
        for number in numbers_in(text):
            report.checked += 1
            if number not in corpus_numbers and number not in corpus:
                report.findings.append(
                    GateFinding("number", number, where, "not present in any source text")
                )
        for name in names_in(text):
            report.checked += 1
            if normalize(name) not in corpus:
                report.findings.append(
                    GateFinding("name", name, where, "not present in any source text")
                )
        for quote in quotes_in(text):
            report.checked += 1
            if not _quote_is_present(quote, corpus):
                report.findings.append(
                    GateFinding("quote", quote[:80], where, "not found in any source text")
                )

    return report


def coverage_gate(briefing, harvest_inventory: Iterable[dict]) -> GateReport:
    """Check that everything the harvest found is somewhere in the Briefing.

    A fact counts as said when a passage carries all of its distinctive atoms
    (its numbers and names), or when a passage restates it closely enough. The
    model is never asked whether it covered something.

    Args:
        briefing: The generated Briefing.
        harvest_inventory: Entries with `fact_id`, `source_id`, and `text`.

    Returns:
        A GateReport. Findings are harvested facts the document never says.
    """
    report = GateReport(name="coverage")
    passages = [text for _, text in briefing_prose(briefing)]
    if not passages:
        report.notes.append("Briefing carries no prose; nothing could be covered")

    document = normalize(" ".join(passages))
    document_numbers = numbers_in(document)

    for fact in harvest_inventory:
        text = fact.get("text", "")
        if not text.strip():
            continue
        report.checked += 1

        fact_numbers = numbers_in(text)
        fact_names = {normalize(n) for n in names_in(text)}
        atoms_present = (
            bool(fact_numbers or fact_names)
            and all(n in document_numbers or n in document for n in fact_numbers)
            and all(name in document for name in fact_names)
        )
        if atoms_present:
            continue

        if any(
            statement_similarity(text, passage) >= _FACT_MATCH_THRESHOLD
            for passage in passages
        ):
            continue

        report.findings.append(
            GateFinding(
                "uncovered_fact",
                text[:110],
                fact.get("fact_id", "unknown"),
                f"harvested from {fact.get('source_id', 'unknown')}, not said anywhere",
            )
        )

    return report
