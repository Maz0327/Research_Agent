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
from typing import Any

from loguru import logger

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
    # the 1950s / early 1900s / mid-1800s. Without this a decade is invisible:
    # "1950s" has no word boundary before the "s", so the bare-year pattern
    # skips it and the next number in the sentence wins. That filed "In the
    # 1950s, a rusted 1862 Colt was found" under 1862, putting a discovery
    # between Packer's birth and his enlistment, and it dropped decade-only
    # events out of the Record entirely.
    re.compile(r"\b(?:(?:early|mid|late)[-\s]+)?((?:1\d{2}|20\d)0)s\b", re.I),
    # bare four-digit year
    re.compile(r"\b(1\d{3}|20\d{2})\b"),
]

_BC = re.compile(r"\b(BC|BCE)\b", re.I)
_CENTURY = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)\s+c(?:entury)?\b", re.I  # codespell:ignore
)

# A name mentioned in this many sections earns a card (D-025).
PLAYER_SECTION_THRESHOLD = 2

# A cast is a list of people you can hold in your head. The 2+-section rule
# alone returned 61 names on the labyrinth corpus, most of them places and
# aliases; after those are handled the rule stands, and this caps what is left.
MAX_PLAYER_CARDS = 14

# The Places section is capped the way the cast is, and smaller: a reader
# holds fewer locations than actors, and on the Packer corpus the five places
# that had been posing as players were already a full geography for one story.
MAX_PLACE_CARDS = 8

# How many words a fuller form of a name may add before it stops being the
# same entity. See merge_aliases.
_ALIAS_MAX_EXTRA_WORDS = 2

# Function words never appear inside a proper name, only in phrases that
# contain one. See merge_aliases.
_PHRASE_WORDS = frozenset({
    "of", "the", "a", "an", "and", "or", "in", "on", "at", "for", "with",
    "from", "to", "by", "about",
})

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
# after them ("In the Joe Rogan Experience", "The Why Files").
#
# The adverbs and common nouns matter as much as the prepositions: measured on
# the Hawara Briefing, "Researchers Corrado Malanga" ranked as its own person
# distinct from "Corrado Malanga", and "Then Robert Schoch" split a two-section
# name into two one-section names so neither reached the card threshold. A name
# that splits this way is invisible to every rule that counts sections.
_LEADING_NOISE = re.compile(
    r"^(?:In|On|At|By|From|To|For|With|After|Before|During|Since)\s+(?:the\s+|a\s+)?"
    r"|^(?:The|A|An)\s+(?=[A-Z])"
    r"|^(?:Then|Later|Meanwhile|However|Today|Yesterday|Instead|Meanwhile|"
    r"Researcher|Researchers|Author|Authors|Egyptologist|Egyptologists|"
    r"Archaeologist|Archaeologists|Geologist|Geologists|Professor|Journalist|"
    r"Historian|Historians|Scientist|Scientists|Engineer|Engineers)\s+(?=[A-Z])"
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


def date_in(text: str) -> tuple[float, str] | None:
    """Find the date a fact is about, if it has one.

    Args:
        text: A fact statement.

    Returns:
        Tuple of (sort key as a year, the date as written), or None when the
        fact carries no date. BC years sort negative.

    """
    # The date a sentence is about is normally the first one it names. Taking
    # the leftmost match rather than the first pattern that hits keeps "In 1874
    # the party set out; the gun surfaced in the 1950s" at 1874, while still
    # reading the decade when the decade comes first.
    found = [
        (match.start(), index, match)
        for index, pattern in enumerate(_DATE_PATTERNS)
        if (match := pattern.search(text))
    ]
    if found:
        _, _, match = min(found, key=lambda row: (row[0], row[1]))
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

    # Supadata transcripts carry no blank lines at all - SRC_2 of the Hawara
    # fixture is 4,019 words with zero newlines - so splitting on paragraph
    # breaks returned the WHOLE source as one "paragraph". The File pass and
    # the dispute pass both read through here, so the narrowing half of the
    # grounding guarantee was not holding for a third of that corpus.
    # `blocks_of` is the proven fallback chain: paragraphs, then sentence
    # groups, then fixed word windows.
    from backend.pipeline.harvest_audit import blocks_of

    paragraphs = blocks_of(raw_text)
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


def _strip_sentence_case(candidate: str, lowercase_words: set[str]) -> str:
    """Drop leading words that are capitalised only because a sentence began.

    A hand-written stop list never finishes: the Packer run produced "When
    David Bailey", "Only Bell" and "Reaching Ouray", none of which the list
    knew. The corpus answers it instead — a word that appears lowercase
    somewhere in the same prose is a normal word, and a real given name
    essentially never does.

    Args:
        candidate: A capitalised run from the text.
        lowercase_words: Every word seen lowercase anywhere in the prose.

    Returns:
        The candidate with leading ordinary words removed.
    """
    tokens = candidate.split()
    while len(tokens) > 1 and tokens[0].lower().strip(".,'\u2019") in lowercase_words:
        tokens = tokens[1:]
    return " ".join(tokens)


def name_candidates(text: str) -> set[str]:
    """Names worth considering for a Players card.

    Args:
        text: Prose from any section.

    Returns:
        Set of multi-word capitalized runs, which is what a person or an
        organization looks like in a sentence.
    """
    from backend.pipeline.briefing_gates import _NAME

    text = text or ""
    lowercase_words = {word.lower() for word in re.findall(r"\b[a-z]{2,}\b", text)}

    found = set()
    for match in _NAME.finditer(text):
        candidate = re.sub(r"[’'][a-z]{1,2}$", "", match.group(0).strip())
        candidate = _LEADING_NOISE.sub("", candidate).strip()
        # Only where a sentence actually began: mid-sentence a capital is
        # the writer's choice. Stripping regardless turned "New York Times"
        # into "York Times", because "new" is also an ordinary word.
        before = text[max(0, match.start() - 2) : match.start()]
        if not before.strip() or before.rstrip().endswith((".", "!", "?", ":", ";")):
            candidate = _strip_sentence_case(candidate, lowercase_words)
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


def merge_aliases(
    appearances: dict[str, set[str]],
    lowercase_words: set[str] | None = None,
) -> dict[str, dict]:
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
    # Longest form first — by tokens, then by characters, so the fullest form
    # is always the canonical one even when a truncated variant has the same
    # token count ("Denver Po" and "Denver Post" are both two tokens).
    names = sorted(appearances, key=lambda n: (-len(n.split()), -len(n), n))
    merged: dict[str, dict] = {}

    def normalise(value: str) -> set[str]:
        return {
            token.lower().strip(".,").removesuffix("’s").removesuffix("'s")
            for token in value.split()
        }

    for name in names:
        tokens = normalise(name)
        target = None
        for canonical in merged:
            canonical_tokens = normalise(canonical)
            # A fuller form of a name adds a word or two — a first name, a
            # middle name, a title. It does not add five. Without this,
            # "Alferd Packer" folded into "Alferd Packer's High Protein
            # Gourmet Cookbook" and the subject of the briefing vanished from
            # his own cast list (2026-08-31).
            if abs(len(canonical.split()) - len(name.split())) > _ALIAS_MAX_EXTRA_WORDS:
                continue
            # A fuller name adds more name-words; a title embeds a name in a
            # phrase, and the giveaway is grammatical. "Alferd Packer" folded
            # into "The Legend of Alfred Packer" and the subject of the
            # briefing left his own cast list. Testing for function words
            # catches that without rejecting "Los Pinos Indian Agency", whose
            # extra words are ordinary nouns but part of the name.
            if (tokens ^ canonical_tokens) & _PHRASE_WORDS:
                continue
            # Token containment catches shorter word-boundary forms. The
            # prefix check catches truncation artifacts, which end mid-word
            # and so share no last token with the full form: on the Packer run
            # the name extractor cut "Los Piños Indian Agency" at the "ñ" and
            # both "Los Pi" and the full agency name got a card.
            if (
                tokens <= canonical_tokens
                or canonical_tokens <= tokens
                or canonical.lower().startswith(name.lower())
            ):
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
    everything = " ".join(sections.values())
    lowercase_words = {w.lower() for w in re.findall(r"\b[a-z]{2,}\b", everything)}
    merged = merge_aliases(names_by_section(sections), lowercase_words)

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


def split_cast(
    names: list[str],
    kinds: dict[str, str] | None,
    max_places: int = MAX_PLACE_CARDS,
) -> tuple[list[str], list[str]]:
    """Split the qualifying names into Players and Places, by classification.

    Players keeps people AND organisations — the Denver Post and the Colorado
    Supreme Court act in a story the way a person does. Places gets geographic
    locations only. The split exists because the 2+-section rule counts a
    river as readily as a reporter: on the Packer run five of fourteen
    "players" were places, each handed a biography.

    Args:
        names: Qualifying names, best first.
        kinds: Name-to-kind map from `classify_name_kinds`, or None when the
            classification failed. None keeps every name a player, the
            pre-split behaviour and the safe direction; so does a name the
            classifier did not answer for.
        max_places: Ceiling on the Places section.

    Returns:
        Tuple of (player names, place names), each in ranking order.
    """
    if kinds is None:
        return list(names), []
    players = [name for name in names if kinds.get(name) != "place"]
    places = [name for name in names if kinds.get(name) == "place"][:max_places]
    return players, places


def below_the_line(
    sections: dict[str, str],
    maximum: int = MAX_PLAYER_CARDS,
    people: set[str] | None = None,
) -> list[str]:
    """Names that met the threshold but fell below the cap.

    These follow the one-off rule instead: introduced inline wherever they
    appear, so a reader never meets a name cold (owner amendment, 2026-08-19).

    The `people` filter exists because the action-verb test cannot tell a
    person from a thing that acts — radar detects, a kingdom builds, a lake is
    described. On the Hawara fixture that put "Middle Kingdom", "Lake Moeris",
    and "Synthetic Aperture Radar" on the one-off list, where the rule's own
    error text ("say who they are") reads as nonsense. Whether a name is a
    person is a reading judgement, so it is decided once at build time and
    handed in here; this function stays arithmetic.

    Args:
        sections: Map of section name to that section's full prose.
        maximum: How many cards the section may carry.
        people: Names confirmed to be people. None applies no filter, which is
            the old behaviour and is right when no classification was run.

    Returns:
        The names below the line, in ranking order.
    """
    ranked = [row["name"] for row in rank_players(sections)[maximum:]]
    if people is None:
        return ranked
    return [name for name in ranked if name in people]


def evidence_chip(
    source_ids: Iterable[str],
    duplicate_of: dict | None = None,
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


# Scraped bylines that name no one: a Wikipedia footer widget, a CMS field.
_NOT_A_BYLINE = re.compile(
    r"^(authority control|authority control databases|admin|editor|staff|"
    r"unknown|n/?a|none|wikipedia contributors)\b",
    re.I,
)
# "Alfred Packer - Wikipedia", "Cannibal Correspondence - True West Magazine"
_TITLE_PUBLISHER = re.compile(r"\s+[-–—|]\s+([^-–—|]{2,40})$")


def source_display_name(source: dict) -> str:
    """What to call a source on the page.

    A reader knows publications, not bylines and not scraped CMS fields. The
    first live briefing attributed a side of a dispute to "Authority control
    databases", which is the name of a footer widget on a Wikipedia page.

    Args:
        source: A source dict with `title` and optional `creator`.

    Returns:
        A name to print, or "" when nothing usable is there.
    """
    title = (source.get("title") or "").strip()
    creator = (source.get("creator") or "").strip()

    publisher = _TITLE_PUBLISHER.search(title)
    if publisher:
        return publisher.group(1).strip()
    if creator and not _NOT_A_BYLINE.match(creator):
        # "KAREN TIMMONS" is a byline shouted by a CMS, not emphasis.
        if creator.isupper():
            creator = creator.title()
        # "Author Gulliford; Andrew" — a CMS label, then a surname-first byline.
        creator = re.sub(r"^(?:author|by|written by)\s+", "", creator, flags=re.I)
        return creator.split(";")[0].strip()
    return title


def _who(source_ids: Iterable[str], source_names: dict[str, str]) -> str:
    """Name the sources behind a side, in words a reader knows.

    Never an internal ID. "SRC_1" is a fact about the pipeline, and the page
    is about Packer; the IDs also used to be echoed into prose by the model
    that was shown them, and then flagged by the grounding gate as ungrounded
    names, which cost sixteen amputated sentences on the first live briefing.
    """
    named = [
        (source_names.get(sid) or "").strip()
        for sid in sorted(set(source_ids))
    ]
    named = [name for name in named if name]
    if not named:
        return ""
    if len(named) == 1:
        return named[0]
    if len(named) == 2:
        return f"{named[0]} and {named[1]}"
    return f"{', '.join(named[:-1])} and {named[-1]}"


# How an extractor writes a disagreement down. The opposition lives in the
# description — "self-defense versus coroner reports of identical trauma" —
# not in the key points it cites, which routinely state one side twice.
_VERSUS = re.compile(r"\s+(?:versus|vs\.?)\s+|,\s+(?:yet|whereas|while)\s+", re.I)

# "Criminal Conviction vs. Forensic Evidence: Packer served…" — a label, then
# the actual sentence. The label is a heading, not one of the two sides.
_TENSION_LABEL = re.compile(r"^[^.:]{0,70}:\s+")


def split_tension(description: str) -> tuple[str, str]:
    """Split a tension into the two positions it sets against each other.

    Returns `("", "")` when the description states no opposition, which is the
    honest answer: taking two cited key points and assuming the second opposes
    the first staged the undisputed core story of the first live briefing as a
    fight, and a reader asked afterwards found that none of the eight pairs
    disagreed at all.
    """
    def halve(text: str) -> tuple[str, str]:
        halves = _VERSUS.split(text.strip(), maxsplit=1)
        if len(halves) != 2:
            return "", ""
        left, right = (half.strip(" .") for half in halves)
        return (left, right) if left and right else ("", "")

    # "Criminal Conviction vs. Forensic Evidence: Packer served seventeen years,
    # yet bullet lead suggests…" — the heading names the fight and the sentence
    # states it. The sentence is the better pair, so it is tried first.
    text = description.strip()
    head, colon, body = text.partition(":")
    if colon and len(head) <= 90:
        sides = halve(body)
        if sides != ("", ""):
            return sides
    return halve(text)


def select_disputes(
    claim_graph: Any | None = None,
    tensions: Iterable[Any] = (),
    inventory: Iterable[dict] = (),
    key_points: dict | None = None,
    max_disputes: int = 8,
    source_names: dict[str, str] | None = None,
    opposition_check: Any = None,
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
                "holders": "",  # written below, once both sides are known
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
        # The two sides come from the description, which is where the extractor
        # actually wrote the disagreement down.
        statement_for, statement_against = split_tension(description)
        claim = statement_for or description

        candidates.append(
            {
                "claim": claim,
                "holders": "",  # written below, once both sides are known
                "statement_for": statement_for,
                "statement_against": statement_against,
                "source_ids_for": sorted(set(sources)),
                "source_ids_against": [],
                "verifiable": True,
            }
        )

    names = source_names or {}
    disputes = []

    for dispute in _dedupe_claims(candidates):
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

        # A claim nobody argues with is not disputed, and a section called
        # "Disputed & Uncertain" is the wrong place to read about it. Staging
        # it anyway produced the worst prose in the first live briefing: the
        # writer, handed "(none supplied)" as the other side, wrote a truthful
        # paragraph about having been given nothing — a page about the
        # pipeline's inputs instead of a page about the story.
        if not dispute["statement_against"] or not dispute["evidence_against"]:
            continue

        # Each side is credited to the sources of the evidence actually behind
        # it. Crediting the "for" side with every source the tension cited put
        # the opposing source on both sides of its own argument.
        for side in ("for", "against"):
            behind = sorted(
                {
                    fact["source_id"]
                    for fact in facts
                    if fact["text"] in dispute[f"evidence_{side}"]
                }
            )
            if behind:
                dispute[f"source_ids_{side}"] = behind
        # A source carrying both sides is not two camps; it is one account that
        # argues with itself, which is worth saying but not as a line-up.
        supporting = set(dispute["source_ids_for"])
        opposing = set(dispute["source_ids_against"])
        for_side = _who(supporting - opposing, names)
        against_side = _who(opposing - supporting, names)
        if for_side and against_side:
            dispute["holders"] = f"Held by {for_side}; disputed by {against_side}."
        elif for_side:
            dispute["holders"] = f"Held by {for_side}."
        elif against_side:
            dispute["holders"] = f"Disputed by {against_side}."
        else:
            both = _who(supporting & opposing, names)
            dispute["holders"] = (
                f"{both} carries both sides of this." if both else ""
            )

        disputes.append(dispute)
        if len(disputes) == max_disputes:
            break

    # Last: do the two sides actually disagree? Lexical similarity cannot tell
    # opposition from restatement — "not" is a stopword, so a sentence and its
    # negation score 0.86 — so a reader is asked, and code applies the answer.
    # Without this the tension path staged the undisputed core story of the
    # briefing as a fight, having only assumed its two key points opposed.
    if opposition_check is not None and disputes:
        opposed = opposition_check(
            [(d["statement_for"], d["statement_against"]) for d in disputes]
        )
        kept = [d for index, d in enumerate(disputes) if index in opposed]
        for index, dispute in enumerate(disputes):
            if index not in opposed:
                logger.info(
                    f"Dispute dropped, sides do not disagree: {dispute['claim'][:70]}"
                )
        disputes = kept

    return disputes


_YEAR_IN_TEXT = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")

# Two years this close together, in restatements of one event, are two
# readings of the same number rather than two different moments.
_COMPETING_YEARS = 10

# How alike two sentences must read, once their numbers are removed, to count
# as the same event told twice.
SAME_EVENT_FLOOR = 0.62


def _without_digits(text: str) -> str:
    return _YEAR_IN_TEXT.sub(" ", text)


_ANY_NUMBER = re.compile(r"\b(\d{1,4})\b")


def _outvoted(facts: list[dict], pattern: re.Pattern, support: dict) -> set[str]:
    """Numbers in these facts that a better-supported near neighbour beats.

    Two numbers only compete when no single fact uses both: "eight years for
    each of the five victims" is one sentence about two different quantities,
    not two readings of one. Two readings of one number look like 1907 against
    1909, or an age of 65 against 69 — never side by side, always close, and
    one of them carried by far fewer sources.
    """
    per_fact = [set(pattern.findall(fact.get("text") or "")) for fact in facts]
    everything = set().union(*per_fact) if per_fact else set()
    together = {
        frozenset((a, b))
        for found in per_fact
        for a in found
        for b in found
        if a != b
    }

    def backing(value: str) -> int:
        return len(support.get(value, ()))

    return {
        value
        for value in everything
        for rival in everything
        if value != rival
        and frozenset((value, rival)) not in together
        and abs(int(value) - int(rival)) <= _COMPETING_YEARS
        and backing(rival) >= 2
        and backing(rival) >= 2 * backing(value)
    }


def collapse_same_event(dated_facts: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collapse restatements of one event, and settle years they disagree on.

    The Record placed every dated fact verbatim and never compared neighbours,
    so the first live briefing opened with four consecutive "Packer was born"
    entries, two of which gave different death years — 1907 and 1909 — sitting
    side by side as though nobody had noticed. Seven sources said 1907; the one
    saying 1909 contradicted itself elsewhere. That is not a disagreement a
    reader should have to arbitrate mid-page; it is arithmetic.

    So: facts about the same year that read alike once their numbers are
    stripped are one event. Within that group, years close enough to be
    readings of the same number are compared, and the reading fewer sources
    support loses. What survives is the fullest remaining telling.

    Args:
        dated_facts: Routed facts carrying `text`, `source_id`, `sort_key`.

    Returns:
        `(kept, dropped)` — the facts to render, in their original order, and
        the ones collapsed away, each with a `dropped_because` note.
    """
    support: dict[str, set] = {}
    for fact in dated_facts:
        for year in _YEAR_IN_TEXT.findall(fact.get("text") or ""):
            support.setdefault(year, set()).add(fact.get("source_id"))

    number_support: dict[str, set] = {}
    for fact in dated_facts:
        for value in _ANY_NUMBER.findall(fact.get("text") or ""):
            number_support.setdefault(value, set()).add(fact.get("source_id"))

    def backing(year: str) -> int:
        return len(support.get(year, ()))

    order = {id(fact): index for index, fact in enumerate(dated_facts)}
    buckets: dict[Any, list[dict]] = {}
    for fact in dated_facts:
        buckets.setdefault(fact.get("sort_key"), []).append(fact)

    kept: list[dict] = []
    dropped: list[dict] = []

    for sort_key, bucket in buckets.items():
        # Every fact here is anchored to the same year, so a second year one of
        # them names is a further detail about the same subject — a death year
        # beside a birth year. Two such years close together are two readings
        # of one number, and the reading fewer sources support is an error, not
        # a disagreement for the reader to arbitrate. The margin has to be
        # clear: outvoted means beaten at least two to one.
        secondary = {
            year
            for fact in bucket
            for year in _YEAR_IN_TEXT.findall(fact.get("text") or "")
            if float(year) != sort_key
        }
        outvoted = _outvoted(bucket, _YEAR_IN_TEXT, support) & secondary

        survivors = []
        for fact in bucket:
            losing = set(_YEAR_IN_TEXT.findall(fact["text"])) & outvoted
            if losing:
                winner = min(
                    (y for y in secondary - outvoted
                     if any(abs(int(y) - int(bad)) <= _COMPETING_YEARS for bad in losing)),
                    key=lambda y: -backing(y),
                    default="",
                )
                dropped.append({
                    **fact,
                    "dropped_because": (
                        f"gives {', '.join(sorted(losing))} where "
                        f"{backing(winner)} sources give {winner}"
                        if winner else f"outvoted year {', '.join(sorted(losing))}"
                    ),
                })
            else:
                survivors.append(fact)
        if not survivors:  # never empty a year on arithmetic alone
            survivors, dropped = bucket, [
                d for d in dropped
                if d.get("fact_id") not in {f.get("fact_id") for f in bucket}
            ]

        # What is left may still tell one event several times over.
        clusters: list[list[dict]] = []
        for fact in survivors:
            stripped = _without_digits(fact.get("text") or "")
            for cluster in clusters:
                head = _without_digits(cluster[0].get("text") or "")
                if statement_similarity(stripped, head) >= SAME_EVENT_FLOOR:
                    cluster.append(fact)
                    break
            else:
                clusters.append([fact])

        for cluster in clusters:
            # Before printing the fullest telling, drop the tellings that lose
            # on a number. Length alone once chose a death entry giving Packer's
            # age as 69 over three sources giving 65, purely because that
            # sentence ran longer.
            beaten = _outvoted(cluster, _ANY_NUMBER, number_support)
            standing = [
                fact
                for fact in cluster
                if not (set(_ANY_NUMBER.findall(fact["text"])) & beaten)
            ] or cluster
            for fact in cluster:
                if fact not in standing:
                    losing = sorted(set(_ANY_NUMBER.findall(fact["text"])) & beaten)
                    dropped.append(
                        {**fact, "dropped_because": f"outvoted on {', '.join(losing)}"}
                    )

            best = max(standing, key=lambda f: len(f.get("text") or ""))
            kept.append(best)
            for fact in standing:
                if fact is not best:
                    dropped.append(
                        {**fact, "dropped_because": "restates the same event"}
                    )

    kept.sort(key=lambda fact: order[id(fact)])
    return kept, dropped


# A harvested fact sometimes carries the extractor's framing rather than the
# thing itself — "the text says his reputation lives on". The briefing is about
# Packer, not about the documents Packer is in, so the framing comes off.
_SOURCE_VOICE = [
    (re.compile(r"^(?:the (?:text|document|source|article)|it) (?:says|states|notes|reports) that ", re.I), ""),
    (re.compile(r"^(?:the (?:text|document|source|article)|it) (?:says|states|notes|reports) ", re.I), ""),
    (re.compile(r",? and the (?:text|document|source|article) (?:says|states|notes|reports) that ", re.I), ", and "),
    (re.compile(r",? and the (?:text|document|source|article) (?:says|states|notes|reports) ", re.I), ", and "),
    (re.compile(r"^according to the (?:text|document|source|article),\s*", re.I), ""),
]


def strip_source_voice(text: str) -> str:
    """Remove a fact's reference to the document it came from.

    Args:
        text: A harvested fact statement.

    Returns:
        The statement, said about the world rather than about the corpus.
    """
    cleaned = text
    for pattern, replacement in _SOURCE_VOICE:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = cleaned.strip()
    if cleaned and cleaned[0].islower() and not text.startswith(cleaned[0]):
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or text
