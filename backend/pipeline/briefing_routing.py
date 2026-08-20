"""Code decisions that happen before any Briefing prose is written.

Work order Section J puts the division of labour plainly: the model never
assembles the document, it fills content fields. Everything in this module is
the other half - what goes where, which names earn a card, what a status chip
says, and which raw paragraphs a writing pass is allowed to see.

Routing before writing also does the anti-hallucination work at the input end:
a pass that only receives its own facts and the paragraphs those facts came
from has less room to wander than one handed the whole corpus.
"""

import re
from collections.abc import Iterable
from typing import Any, Optional

from backend.models.briefing import Chip, chip
from backend.pipeline.text_similarity import content_tokens, statement_similarity

# Dates the way sources actually write them, most specific pattern first.
_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|"
    "november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
_DATE_PATTERNS = [
    # May 7 2026 / 7 May 2026 / May 2026
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}},?\s+(\d{{4}})\b", re.I),
    re.compile(rf"\b\d{{1,2}}\s+(?:{_MONTHS})\.?,?\s+(\d{{4}})\b", re.I),
    re.compile(rf"\b(?:{_MONTHS})\.?\s+(\d{{4}})\b", re.I),
    # 2007-09, 1843-1888
    re.compile(r"\b(\d{4})\s*[-–—]\s*\d{2,4}\b"),
    # c. 450 BC / 25 BC / 43 AD
    re.compile(r"\bc?\.?\s*(\d{1,4})\s*(?:BC|BCE)\b", re.I),
    re.compile(r"\b(\d{1,4})\s*(?:AD|CE)\b"),
    # bare four-digit year
    re.compile(r"\b(1\d{3}|20\d{2})\b"),
]

_BC = re.compile(r"\b(BC|BCE)\b", re.I)
_CENTURY = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+c(?:entury)?\b", re.I)

# A name mentioned in this many sections earns a card (D-025).
PLAYER_SECTION_THRESHOLD = 2

# A cast is a list of people you can hold in your head. The 2+-section rule
# alone returned 61 names on the labyrinth corpus, most of them places and
# aliases; after those are handled the rule stands, and this caps what is left.
MAX_PLAYER_CARDS = 14

# A player DOES something. Places, monuments, and eras recur constantly in a
# research corpus and belong in the prose, not in the cast, so a candidate has
# to be seen acting somewhere.
_ACTS = (
    "said|says|wrote|writes|found|founded|ran|runs|led|leads|funded|funds|"
    "published|publishes|claimed|claims|argued|argues|dismissed|dismisses|"
    "banned|bans|announced|announces|scanned|scans|excavated|excavates|"
    "reported|reports|told|tells|added|adds|released|releases|confirmed|"
    "confirms|refused|refuses|died|dies|organised|organized|produced|produces|"
    "drilled|drills|surveyed|surveys|concluded|concludes|described|describes|"
    "visited|visits|built|builds|granted|grants|threatened|threatens|"
    "interviewed|interviews|presented|presents|denied|denies|discovered|"
    "discovers|noted|notes|calls|called|believes|believed|suggests|suggested"
)
_ACTION_WINDOW = 30

# Capitalized function words that start a sentence and get swept into the run
# after them ("In the Joe Rogan Experience", "The Why Files")
_LEADING_NOISE = re.compile(
    r"^(?:In|On|At|By|From|To|For|With|After|Before|During|Since)\s+(?:the\s+|a\s+)?"
    r"|^(?:The|A|An)\s+(?=[A-Z])"
)

# Below this, two facts are about different things.
_SAME_SUBJECT = 0.55

# A chronology entry is a fact about something happening at a time, not any
# sentence that mentions a year. Measured on the labyrinth harvest: 152 facts
# carry a date, and 96 of them read as events; the rest are references,
# citations, and plans, which belong in the Files with their subject.
_IRREGULAR_PAST = (
    "found|wrote|began|built|took|went|came|led|ran|held|drew|sent|made|died|"
    "rose|fell|won|lost|saw|said|told|gave|got|kept|left|met|paid|put|read|sat|"
    "set|showed|spoke|stood|struck|taught|thought|threw|withdrew|was|were|had|did"
)
_PAST_TENSE = re.compile(rf"\b(\w+ed|{_IRREGULAR_PAST})\b", re.I)

# Markers that a date is part of a citation rather than an event
_CITATION_MARKER = re.compile(r"\b(ISBN|DOI|vol\.|pp?\.|ed\.|edition|journal)\b", re.I)


def looks_like_an_event(text: str, date_written: str) -> bool:
    """Is this fact about something that happened, or does it just cite a year?

    Two things disqualify a date: no past-tense verb anywhere (a plan, a
    standing description), and a date sitting inside a citation - parenthesised
    or trailed by ISBN, volume, or page markers. Everything else is an event
    and belongs on the chronology.

    Args:
        text: The fact statement.
        date_written: The date as the fact writes it.

    Returns:
        True when the fact reads as a dated event.
    """
    if not _PAST_TENSE.search(text):
        return False

    first_word = date_written.lower().split()[0] if date_written else ""
    position = text.lower().find(first_word) if first_word else -1
    if position < 0:
        return True

    before = text[:position]
    after = text[position: position + 60]
    if before.count("(") > before.count(")") or before.count("[") > before.count("]"):
        return False
    return not _CITATION_MARKER.search(after)


def date_in(text: str) -> Optional[tuple[float, str]]:
    """Find the date a fact is about, if it has one.

    Args:
        text: A fact statement.

    Returns:
        Tuple of (sort key as a year, the date as written), or None when the
        fact carries no date. BC years sort negative.

    """
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        year = int(match.group(1))
        written = match.group(0).strip().rstrip(",")
        # "7000-5000 BC" matches the range pattern, which does not capture the
        # era, so look just past the match before deciding which way it sorts.
        tail = text[match.end(): match.end() + 8]
        if _BC.search(written) or _BC.search(tail):
            era = "" if _BC.search(written) else " BC"
            return -float(year), f"{written}{era}"
        return float(year), written

    century = _CENTURY.search(text)
    if century:
        number = int(century.group(1))
        written = century.group(0).strip()
        tail = text[century.end(): century.end() + 12]
        if _BC.search(tail):
            # 1st century BC is roughly 50 BC, 5th century BC roughly 450 BC:
            # a higher century number is further back.
            era = _BC.search(tail).group(0)
            return -(number * 100 - 50.0), f"{written} {era}"
        return (number - 1) * 100 + 50.0, written

    return None


def route_facts(
    inventory: Iterable[dict],
    dispute_claims: Iterable[str] = (),
) -> dict[str, list[dict]]:
    """Split the harvest into the sections code can decide by itself.

    Dated facts belong to the Record; facts that restate a known dispute
    belong to Disputes; everything else waits for the subject map.

    Args:
        inventory: Harvest entries with `fact_id`, `source_id`, `text`.
        dispute_claims: Claim sentences already identified as contested.

    Returns:
        Dict with `record`, `disputed`, and `remaining` lists. A fact appears
        in exactly one of them, so nothing is counted twice or lost.
    """
    claims = [c for c in dispute_claims if c and c.strip()]
    routed: dict[str, list[dict]] = {"record": [], "disputed": [], "remaining": []}

    for fact in inventory:
        text = fact.get("text", "")
        if not text.strip():
            continue

        dated = date_in(text)
        if dated and looks_like_an_event(text, dated[1]):
            entry = dict(fact)
            entry["sort_key"], entry["when"] = dated
            routed["record"].append(entry)
            continue

        if any(statement_similarity(text, claim) >= _SAME_SUBJECT for claim in claims):
            routed["disputed"].append(dict(fact))
            continue

        routed["remaining"].append(dict(fact))

    routed["record"].sort(key=lambda f: (f["sort_key"], f["fact_id"]))
    return routed


def paragraphs_for_fact(fact_text: str, raw_text: str, window: int = 2) -> list[str]:
    """Pull the raw paragraphs a fact most likely came from.

    A writing pass gets these instead of the whole corpus, which is the
    narrowing half of the grounding guarantee: the pass can only draw on the
    text its own facts came from.

    Args:
        fact_text: The harvested fact.
        raw_text: One source's full text.
        window: How many best-matching paragraphs to return.

    Returns:
        The best-matching paragraphs, in document order.
    """
    if not fact_text.strip() or not raw_text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\r\n\r\n", raw_text) if p.strip()]
    if not paragraphs:
        return []

    tokens = content_tokens(fact_text)
    if not tokens:
        return []

    scored = []
    for index, paragraph in enumerate(paragraphs):
        shared = tokens & content_tokens(paragraph)
        if shared:
            scored.append((len(shared) / len(tokens), index, paragraph))

    scored.sort(key=lambda row: (-row[0], row[1]))
    best = sorted(scored[:window], key=lambda row: row[1])
    return [paragraph for _, _, paragraph in best]


def name_candidates(text: str) -> set[str]:
    """Names worth considering for a Players card.

    Args:
        text: Prose from any section.

    Returns:
        Set of multi-word capitalized runs, which is what a person or an
        organization looks like in a sentence.
    """
    from backend.pipeline.briefing_gates import _NAME

    found = set()
    for match in _NAME.finditer(text or ""):
        candidate = re.sub(r"[’'][a-z]{1,2}$", "", match.group(0).strip())
        candidate = _LEADING_NOISE.sub("", candidate).strip()
        if " " in candidate and len(candidate) > 5:
            found.add(candidate)
    return found


def names_by_section(sections: dict[str, str]) -> dict[str, set[str]]:
    """Count where each name appears, so code can apply the 2+-section rule.

    Args:
        sections: Map of section name to that section's full prose.

    Returns:
        Map of name to the set of sections it appears in.
    """
    appearances: dict[str, set[str]] = {}
    for section, text in sections.items():
        for name in name_candidates(text):
            appearances.setdefault(name, set()).add(section)
    return appearances


def merge_aliases(appearances: dict[str, set[str]]) -> dict[str, dict]:
    """Fold shorter forms of a name into the fullest form of it.

    "De Cordier" and "Louis De Cordier" are one person; "Ministry of Tourism"
    and "Egypt's Ministry of Tourism" are one body. Matching on token
    containment catches both without a name database.

    Args:
        appearances: Map of name to the sections it appears in.

    Returns:
        Map of canonical name to `{"sections": set, "aliases": set}`. Aliases
        are kept because the ranking counts every form a name appears under.
    """
    names = sorted(appearances, key=lambda n: (-len(n.split()), n))
    merged: dict[str, dict] = {}

    for name in names:
        tokens = {t.lower().strip(".,") for t in name.split()}
        target = None
        for canonical in merged:
            canonical_tokens = {t.lower().strip(".,") for t in canonical.split()}
            if tokens <= canonical_tokens or canonical_tokens <= tokens:
                target = canonical
                break
        if target:
            merged[target]["sections"] |= appearances[name]
            merged[target]["aliases"].add(name)
        else:
            merged[name] = {"sections": set(appearances[name]), "aliases": {name}}

    return merged


def mention_count(aliases: Iterable[str], text: str) -> int:
    """How many times a name appears, counting every form of it.

    Args:
        aliases: All forms the name appears under.
        text: All the document's prose.

    Returns:
        Total mentions.
    """
    lowered = (text or "").lower()
    return sum(lowered.count(alias.lower()) for alias in aliases)


def acts_somewhere(name: str, text: str) -> bool:
    """Is this name shown doing something, or is it just a place that recurs?

    Args:
        name: Candidate name.
        text: All the document's prose.

    Returns:
        True when the name is followed closely by an action verb.
    """
    pattern = re.compile(
        rf"{re.escape(name)}[^.!?]{{0,{_ACTION_WINDOW}}}?\b(?:{_ACTS})\b", re.I
    )
    return bool(pattern.search(text))


def rank_players(sections: dict[str, str]) -> list[dict]:
    """Rank every name that meets the card threshold, deterministically.

    The order is fixed by owner amendment to D-025 (2026-08-19): distinct
    sections first, total mentions as the tie-break, then the name itself so
    the result never depends on dict order or on how the prose was chunked.

    Two things happen before the ranking, for the result to be a cast rather
    than an index: aliases of one name count once, and a name that never acts
    is a place, not a player.

    Args:
        sections: Map of section name to that section's full prose.

    Returns:
        List of `{"name", "sections", "mentions", "aliases"}`, best first.
    """
    merged = merge_aliases(names_by_section(sections))
    everything = " ".join(sections.values())

    ranked = [
        {
            "name": name,
            "sections": len(entry["sections"]),
            "mentions": mention_count(entry["aliases"], everything),
            "aliases": sorted(entry["aliases"]),
        }
        for name, entry in merged.items()
        if len(entry["sections"]) >= PLAYER_SECTION_THRESHOLD
        and acts_somewhere(name, everything)
    ]
    ranked.sort(key=lambda row: (-row["sections"], -row["mentions"], row["name"]))
    return ranked


def qualifying_players(
    sections: dict[str, str], maximum: int = MAX_PLAYER_CARDS
) -> list[str]:
    """Names that earn a card: the top of the ranking, capped.

    Args:
        sections: Map of section name to that section's full prose.
        maximum: How many cards the section may carry.

    Returns:
        Qualifying names, best first.
    """
    return [row["name"] for row in rank_players(sections)[:maximum]]


def below_the_line(
    sections: dict[str, str], maximum: int = MAX_PLAYER_CARDS
) -> list[str]:
    """Names that met the threshold but fell below the cap.

    These follow the one-off rule instead: introduced inline wherever they
    appear, so a reader never meets a name cold (owner amendment, 2026-08-19).

    Args:
        sections: Map of section name to that section's full prose.
        maximum: How many cards the section may carry.

    Returns:
        The names below the line, in ranking order.
    """
    return [row["name"] for row in rank_players(sections)[maximum:]]


def evidence_chip(
    source_ids: Iterable[str],
    duplicate_of: Optional[dict] = None,
    contested: bool = False,
    belief_migration: bool = False,
    verifiable: bool = True,
) -> Chip:
    """Compute a status chip from provenance arithmetic.

    Counts, not judgment (D-025). Syndicated copies collapse into their
    canonical source first, so four printings of one wire story never read as
    four sources.

    Args:
        source_ids: Sources supporting the claim.
        duplicate_of: Map of duplicate source ID to canonical source ID.
        contested: True when the corpus carries a case against it.
        belief_migration: True when the claim is a relocated belief rather than
            a finding.
        verifiable: False when nothing in the corpus could settle it.

    Returns:
        The chip a reader sees.
    """
    canonical = {(duplicate_of or {}).get(s, s) for s in source_ids if s}

    if belief_migration:
        return chip("belief migration")
    if not verifiable:
        return chip("unverifiable")
    if contested:
        return chip("contested")
    if len(canonical) <= 1:
        return chip("single source")
    return chip("established")


# Synthesis text often cites the key points it refers to ("the consensus
# (KP_2) against the scan data (KP_3)"). Internal IDs never render in a
# document body, so they are stripped before the text becomes a claim.
_INTERNAL_ID = re.compile(r"\s*\((?:[A-Z]{2,6}_\d+(?:\s*[,;]\s*)?)+\)|\b[A-Z]{2,6}_\d+\b")


def _strip_internal_ids(text: str) -> str:
    """Remove internal unit IDs from text destined for the page."""
    return re.sub(r"\s{2,}", " ", _INTERNAL_ID.sub("", text or "")).strip()


def _dedupe_claims(claims: list[dict]) -> list[dict]:
    """Drop disputes that restate one already selected."""
    kept: list[dict] = []
    for candidate in claims:
        if any(
            statement_similarity(candidate["claim"], existing["claim"]) >= _SAME_SUBJECT
            for existing in kept
        ):
            continue
        kept.append(candidate)
    return kept


def select_disputes(
    claim_graph: Optional[Any] = None,
    tensions: Iterable[Any] = (),
    inventory: Iterable[dict] = (),
    key_points: Optional[dict] = None,
    max_disputes: int = 8,
) -> list[dict]:
    """Choose the disputes, by code, from what the pipeline already found.

    Two sources feed it: a claim's `pushback` in the claim graph, which is
    where tension lives by design, and the extraction stage's tensions.
    Restatements are dropped so the same fight is not staged twice.

    The model is never asked what is disputed. It is only asked to write the
    two cases for a dispute code has already selected and evidenced.

    Args:
        claim_graph: A validated ClaimGraph, when distillation produced one.
        tensions: Tension objects from extraction.
        inventory: Harvest entries, used to attach concrete evidence.
        key_points: Map of key-point ID to its dict, so a tension can be
            stated as the concrete assertion its key points make rather than
            as the analytic sentence a synthesis model wrote about it. IDs are
            source-qualified since work order B6; a corpus extracted before
            that fix has colliding IDs and falls back to the description.
        max_disputes: Ceiling on how many disputes the section carries.

    Returns:
        Dispute specs ready for the dispute pass.
    """
    facts = [f for f in inventory if f.get("text")]
    candidates: list[dict] = []

    for claim in getattr(claim_graph, "claims", []) or []:
        pushback = getattr(claim, "pushback", None)
        if not pushback:
            continue
        sources = [e.source_id for e in getattr(claim, "evidence", []) or []]
        candidates.append(
            {
                "claim": getattr(claim, "title", "") or "",
                "holders": f"For: {', '.join(sorted(set(sources))) or 'the sources'}. "
                f"Against: the pushback in the same corpus.",
                "statement_for": getattr(claim, "what_sources_say", "") or "",
                "statement_against": pushback,
                "source_ids_for": sorted(set(sources)),
                "source_ids_against": [],
                "verifiable": getattr(getattr(claim, "confidence", None), "grade", 3) > 1,
            }
        )

    lookup = key_points or {}
    for tension in tensions or []:
        description = _strip_internal_ids(getattr(tension, "description", "") or "")
        if not description.strip():
            continue

        involved = [
            lookup[kp_id]
            for kp_id in (getattr(tension, "involved_key_points", []) or [])
            if kp_id in lookup
        ]
        sources = list(getattr(tension, "source_ids", []) or [])
        for point in involved:
            sources.extend(point.get("source_ids", []) or [])

        # A dispute reads as the thing being disputed, not as a sentence about
        # there being a disagreement. The key points carry the concrete
        # assertion; the description is the fallback when they do not resolve.
        if len(involved) >= 2:
            claim = involved[0].get("statement", description)
            statement_for = involved[0].get("statement", description)
            statement_against = involved[1].get("statement", "")
        elif involved:
            claim = involved[0].get("statement", description)
            statement_for = claim
            statement_against = ""
        else:
            claim = description
            statement_for = description
            statement_against = ""

        candidates.append(
            {
                "claim": claim,
                "holders": f"Held across: {', '.join(sorted(set(sources))) or 'the corpus'}.",
                "statement_for": statement_for,
                "statement_against": statement_against,
                "source_ids_for": sorted(set(sources)),
                "source_ids_against": [],
                "verifiable": True,
            }
        )

    disputes = _dedupe_claims(candidates)[:max_disputes]

    for dispute in disputes:
        dispute["evidence_for"] = [
            fact["text"]
            for fact in facts
            if statement_similarity(fact["text"], dispute["statement_for"]) >= 0.30
        ][:8]
        dispute["evidence_against"] = [
            fact["text"]
            for fact in facts
            if dispute["statement_against"]
            and statement_similarity(fact["text"], dispute["statement_against"]) >= 0.30
        ][:8]
        dispute["source_ids_against"] = sorted(
            {
                fact["source_id"]
                for fact in facts
                if fact["text"] in dispute["evidence_against"]
            }
        )
    return disputes
