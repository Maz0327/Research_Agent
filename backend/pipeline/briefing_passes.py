"""The Briefing generation passes (work order Section J, owner-approved).

Eight passes. The model writes content fields; code decides structure, pulls
inputs, checks coverage, computes chips, and assembles the document. The pass
layout is locked - it was approved on 2026-08-18 and is not to be redesigned.

Every pass here takes its inputs already narrowed by code. That is half the
grounding guarantee: a pass that only sees its own facts and the paragraphs
those facts came from has less room to wander than one handed the corpus.

Cost shape, for orientation: the Read is one large call; files, disputes,
blurbs, players, and contributions are small calls; the harvest (a separate
stage) is one call per source. Roughly 25-30 calls per job.
"""

from typing import Any, Optional

from loguru import logger

from backend.config import get_settings
from backend.models.briefing import (
    BLURBS_SCHEMA,
    CONTRIBUTIONS_SCHEMA,
    DISPUTE_SCHEMA,
    FILE_SCHEMA,
    PLAYERS_SCHEMA,
    READ_SCHEMA,
    SUBJECT_MAP_SCHEMA,
    Anecdote,
    DisputeSide,
    File,
    Player,
    Read,
    ReadParagraph,
    RecordEntry,
    _array_of,
    _object,
)
from backend.pipeline.briefing_routing import paragraphs_for_fact
from backend.pipeline.injection_guard import DATA_NOTICE, delimit
from backend.pipeline.prompts.briefing_prompts import (
    BLURB_ROLE,
    CONTRIBUTION_ROLE,
    DENSIFY_ROLE,
    DISPUTE_ROLE,
    FILE_ROLE,
    PLAYERS_ROLE,
    READ_EXAMPLES,
    READ_ROLE,
    SUBJECT_MAP_ROLE,
)
from backend.pipeline.text_similarity import statement_similarity

# The Read is one call over all raw text (owner decision: 20-source cap keeps
# it single-call). The budget is a TOTAL across the corpus, shared out evenly,
# rather than a fixed cut per source: a flat 40,000-character cap silently took
# 28% off the longest source in the Hawara corpus while the call as a whole sat
# nowhere near its context limit. Nothing is trimmed unless the corpus actually
# exceeds the total.
READ_TOTAL_CHARS = 700_000
READ_MIN_CHARS_PER_SOURCE = 20_000
READ_MAX_TOKENS = 24_000

SMALL_CALL_MAX_TOKENS = 4_000

# The subject map has to name every fact ID it places, so its output scales
# with the corpus: 480 facts overflowed a 4k ceiling on the labyrinth run.
SUBJECT_MAP_MAX_TOKENS = 16_000

# Facts per subject-map call. Beyond this the output runs long enough to risk
# truncation, so the map is built in batches and merged by code.
SUBJECT_MAP_BATCH = 150

# Entries per blurb call. Context notes are a few sentences each, so a long
# chronology needs several calls rather than one that truncates.
BLURB_BATCH = 20

# The Files section is a reader's map of the corpus, and a map with twenty
# regions is not a map (work order Section J: 4-8 subjects). Batching pushes
# the count up, so code caps it afterwards rather than asking harder.
MAX_FILE_SUBJECTS = 8


def read_budget(
    texts: dict[str, str],
    total: int = READ_TOTAL_CHARS,
    floor: int = READ_MIN_CHARS_PER_SOURCE,
) -> dict[str, int]:
    """Share the Read's character budget across the corpus.

    Under the total, every source is sent whole — which is the normal case and
    was NOT what the old fixed per-source cap did. Over it, the long sources
    give up characters first and every source keeps at least `floor`, so one
    enormous source cannot starve fifteen short ones.

    Args:
        texts: Source ID to full text.
        total: Characters the whole call may carry.
        floor: Characters every source keeps regardless.

    Returns:
        Source ID to how many characters to send.
    """
    if not texts:
        return {}

    lengths = {sid: len(text) for sid, text in texts.items()}
    if sum(lengths.values()) <= total:
        return lengths

    # Water-filling: raise a common ceiling until the budget is spent, so the
    # cut lands on the longest sources and never on the ones already short.
    allowed = dict.fromkeys(lengths, floor)
    spare = total - floor * len(lengths)
    for sid, length in sorted(lengths.items(), key=lambda kv: kv[1]):
        if spare <= 0:
            break
        want = min(length, floor + spare) - allowed[sid]
        if want > 0:
            allowed[sid] += want
            spare -= want
    return {sid: min(lengths[sid], allowed[sid]) for sid in lengths}


def _manifest_line(source: dict) -> str:
    """One line describing a source, for the Read's manifest."""
    bits = [source.get("source_id", "SRC_?"), source.get("title") or "Untitled"]
    if source.get("source_type"):
        bits.append(f"({source['source_type']})")
    if source.get("creator"):
        bits.append(f"by {source['creator']}")
    if source.get("published"):
        bits.append(str(source["published"]))
    if source.get("duplicate_of"):
        bits.append(f"[republication of {source['duplicate_of']}]")
    if not (source.get("full_text") or "").strip():
        bits.append("[no text captured]")
    return " · ".join(str(b) for b in bits)


def run_read_pass(client: Any, topic: str, sources: list[dict]) -> Read:
    """Pass 1: write Section 1 from the raw source texts.

    Never from claim atoms. Extraction destroys each source's argumentative
    shape - concessions, who answers whom - and that shape is what makes the
    cast, the ranking, and the staged fights possible.

    Args:
        client: A structured-output client.
        topic: The job's topic, for orientation only.
        sources: Source dicts with `source_id`, `title`, `full_text`, and
            optionally `source_type`, `creator`, `published`, `duplicate_of`.

    Returns:
        The Read section.
    """
    settings = get_settings()
    manifest = "\n".join(_manifest_line(s) for s in sources)
    texts = {
        s.get("source_id") or f"SRC_{i}": (s.get("full_text") or "").strip()
        for i, s in enumerate(sources)
    }
    budget = read_budget({k: v for k, v in texts.items() if v})

    bodies = []
    for source in sources:
        source_id = source.get("source_id") or "SOURCE"
        text = texts.get(source_id, "")
        if not text:
            continue
        allowance = budget.get(source_id, len(text))
        if allowance < len(text):
            logger.warning(
                f"The Read: {source_id} trimmed to {allowance:,} of {len(text):,} "
                f"chars — the corpus exceeds the total budget"
            )
        bodies.append(
            f"===== {source_id} · {source.get('title') or 'Untitled'} =====\n"
            + delimit(text[:allowance], source_id, notice=False)
        )

    prompt = (
        f"TOPIC AS THE RESEARCHER TYPED IT: {topic}\n\n"
        f"SOURCE MANIFEST ({len(sources)} sources)\n{manifest}\n\n"
        f"{READ_EXAMPLES}\n\n"
        "Now write the read for the sources below. Same shape, same register.\n\n"
        f"{DATA_NOTICE}\n\n"
        + "\n\n".join(bodies)
    )

    data, _ = client.generate_structured(
        prompt=prompt,
        schema=READ_SCHEMA,
        system=READ_ROLE,
        max_tokens=READ_MAX_TOKENS,
    )

    read = _read_from(data)

    # One density pass (D-037). Measured on the Hawara fixture: +37% distinct
    # facts, source-talk down from 51% to 31% of the words, and a LOWER
    # invented-fact rate than the draft it improves. A second round adds facts
    # but drifts longer and lets source-talk creep back, so one is the setting.
    if not settings.read_densify:
        return read

    try:
        dense, _ = client.generate_structured(
            prompt=f"CURRENT DRAFT:\n{_flatten(read)}\n\n{DATA_NOTICE}\n\nSOURCES:\n"
            + "\n\n".join(bodies),
            schema=READ_SCHEMA,
            system=DENSIFY_ROLE,
            max_tokens=READ_MAX_TOKENS,
        )
    except Exception as exc:
        logger.warning(f"The Read: density pass failed ({exc}); keeping the draft")
        return read

    densified = _read_from(dense)
    if not densified.lede.strip() or not densified.paragraphs:
        logger.warning("The Read: density pass returned nothing; keeping the draft")
        return read
    return densified


def _read_from(data: dict) -> Read:
    """Build a Read from a pass's raw response."""
    paragraphs = [
        ReadParagraph(label=(p.get("label") or None), text=p.get("text", "").strip())
        for p in data.get("paragraphs", [])
        if p.get("text", "").strip()
    ]
    return Read(lede=data.get("lede", "").strip(), paragraphs=paragraphs)


def _flatten(read: Read) -> str:
    """The Read as one block of prose, for a pass that rewrites it."""
    return " ".join([read.lede] + [p.text for p in read.paragraphs])


def run_subject_map_pass(
    client: Any, facts: list[dict]
) -> tuple[list[dict], list[str]]:
    """Pass 2: group the remaining facts into file subjects and an anecdote bin.

    Semantic grouping is the one thing code cannot do here - measured on this
    project, embeddings rank restatements rather than connections. Code has
    already routed dated facts to the Record and disputed facts to Disputes;
    this call sees only what is left, and code enforces no-orphan afterwards.

    Args:
        client: A structured-output client.
        facts: Harvest entries with `fact_id` and `text`.

    Returns:
        Tuple of (subjects, anecdote fact IDs). Each subject is a dict with
        `title` and `fact_ids`. Every input fact appears exactly once across
        the two: unassigned facts are put in their own "Everything else"
        subject rather than dropped.
    """
    if not facts:
        return [], []

    known = {f["fact_id"] for f in facts}
    seen: set[str] = set()
    subjects: list[dict] = []
    anecdotes: list[str] = []

    for start in range(0, len(facts), SUBJECT_MAP_BATCH):
        batch = facts[start: start + SUBJECT_MAP_BATCH]
        listing = "\n".join(f"{f['fact_id']}: {f['text']}" for f in batch)
        existing = (
            "\n\nSUBJECTS ALREADY OPEN (reuse a title exactly when a fact belongs "
            "to it):\n" + "\n".join(f"- {s['title']}" for s in subjects)
            if subjects
            else ""
        )
        data, _ = client.generate_structured(
            prompt=f"FACTS\n{listing}{existing}",
            schema=SUBJECT_MAP_SCHEMA,
            system=SUBJECT_MAP_ROLE,
            max_tokens=SUBJECT_MAP_MAX_TOKENS,
        )

        by_title = {s["title"].lower(): s for s in subjects}
        for subject in data.get("subjects", []):
            ids = [i for i in subject.get("fact_ids", []) if i in known and i not in seen]
            seen.update(ids)
            title = (subject.get("title") or "").strip()
            if not title or not ids:
                continue
            existing_subject = by_title.get(title.lower())
            if existing_subject:
                existing_subject["fact_ids"].extend(ids)
            else:
                subject_entry = {"title": title, "fact_ids": ids}
                subjects.append(subject_entry)
                by_title[title.lower()] = subject_entry

        for fact_id in data.get("anecdote_fact_ids", []):
            if fact_id in known and fact_id not in seen:
                anecdotes.append(fact_id)
                seen.add(fact_id)

    orphans = [i for i in known if i not in seen]
    if orphans:
        # No fact is lost because a model forgot it. The gate would catch this
        # later; putting them somewhere keeps the document honest either way.
        logger.warning(f"Subject map left {len(orphans)} fact(s) unassigned")
        subjects.append({"title": "Everything else", "fact_ids": sorted(orphans)})

    return cap_subjects(subjects), anecdotes


def cap_subjects(
    subjects: list[dict], maximum: int = MAX_FILE_SUBJECTS
) -> list[dict]:
    """Fold the smallest subjects into their nearest neighbour, keeping facts.

    Batching the map across a large corpus produces more subjects than the
    format wants. Merging is code's call and it is conservative: the smallest
    subject joins whichever surviving subject its title is closest to, and its
    facts move with it, so the merge changes where a fact is filed and never
    whether it is filed.

    Args:
        subjects: Subjects from the map pass, largest-first order not required.
        maximum: How many files the section may carry.

    Returns:
        At most `maximum` subjects, every fact still assigned.
    """
    if len(subjects) <= maximum:
        return subjects

    ordered = sorted(subjects, key=lambda s: -len(s["fact_ids"]))
    # Copy what survives: callers keep their own list, and a merge that
    # mutated the input would double-count facts for anyone measuring after.
    kept = [{"title": s["title"], "fact_ids": list(s["fact_ids"])} for s in ordered[:maximum]]
    overflow = ordered[maximum:]

    for subject in overflow:
        scored = [
            (statement_similarity(subject["title"], candidate["title"]), index)
            for index, candidate in enumerate(kept)
        ]
        _, best = max(scored) if scored else (0.0, 0)
        kept[best]["fact_ids"].extend(subject["fact_ids"])
        logger.info(
            f"Subject '{subject['title']}' folded into '{kept[best]['title']}' "
            f"({len(subject['fact_ids'])} facts)"
        )

    return kept


def _fact_context(fact_texts: list[str], raw_by_source: dict[str, str], fact_sources: list[str]) -> str:
    """Assemble the raw paragraphs a writing pass is allowed to see."""
    chunks: list[str] = []
    for text, source_id in zip(fact_texts, fact_sources, strict=False):
        for paragraph in paragraphs_for_fact(text, raw_by_source.get(source_id, "")):
            if paragraph not in chunks:
                chunks.append(paragraph)
    return "\n\n".join(chunks)


def run_file_pass(
    client: Any,
    title: str,
    facts: list[dict],
    raw_by_source: dict[str, str],
) -> File:
    """Pass 3: write one subject file from its assigned facts.

    Args:
        client: A structured-output client.
        title: The subject title from the map pass.
        facts: The facts assigned to this subject.
        raw_by_source: Source ID to that source's raw text.

    Returns:
        The File section, with its assigned fact and source IDs recorded so the
        coverage gate can check it.
    """
    listing = "\n".join(f"- {f['text']}" for f in facts)
    context = _fact_context(
        [f["text"] for f in facts], raw_by_source, [f.get("source_id", "") for f in facts]
    )

    prompt = (
        f"SUBJECT: {title}\n\nFACTS TO WRITE (every one must appear)\n{listing}"
        + (
            "\n\nRAW SOURCE PARAGRAPHS THESE CAME FROM\n"
            + delimit(context, f"{title}-context")
            if context
            else ""
        )
    )
    data, _ = client.generate_structured(
        prompt=prompt,
        schema=FILE_SCHEMA,
        system=FILE_ROLE,
        max_tokens=SMALL_CALL_MAX_TOKENS,
    )

    source_ids: list[str] = []
    for fact in facts:
        source_id = fact.get("source_id")
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)

    return File(
        title=(data.get("title") or title).strip(),
        body=data.get("body", "").strip(),
        source_ids=source_ids,
        fact_ids=[f["fact_id"] for f in facts],
    )


def repair_file_coverage(
    client: Any, file: File, missing: list[dict], raw_by_source: dict[str, str]
) -> File:
    """Append the facts a file left out. One round, append-only.

    Re-emitting a document to edit it drops content - proven three ways on this
    project - so the repair adds a paragraph rather than rewriting the file.

    Args:
        client: A structured-output client.
        file: The file that missed facts.
        missing: The facts the coverage check found missing.
        raw_by_source: Source ID to that source's raw text.

    Returns:
        The file with an appended paragraph covering the misses.
    """
    if not missing:
        return file

    listing = "\n".join(f"- {f['text']}" for f in missing)
    context = _fact_context(
        [f["text"] for f in missing],
        raw_by_source,
        [f.get("source_id", "") for f in missing],
    )
    prompt = (
        f"SUBJECT: {file.title}\n\n"
        "These facts belong in this file and are not in it yet. Write ONE "
        "additional paragraph that says them. Do not restate what is already "
        f"written.\n\nALREADY WRITTEN\n{file.body}\n\nMISSING FACTS\n{listing}"
        + (f"\n\nRAW SOURCE PARAGRAPHS\n{context}" if context else "")
    )

    data, _ = client.generate_structured(
        prompt=prompt,
        schema=FILE_SCHEMA,
        system=FILE_ROLE,
        max_tokens=SMALL_CALL_MAX_TOKENS,
    )
    addition = data.get("body", "").strip()
    if addition:
        file.body = f"{file.body}\n\n{addition}"
    return file


def run_dispute_pass(
    client: Any,
    claim: str,
    holders: str,
    evidence_for: list[str],
    evidence_against: list[str],
    source_ids_for: list[str],
    source_ids_against: list[str],
) -> tuple[DisputeSide, DisputeSide]:
    """Pass 4: write both sides of one dispute code already selected.

    Args:
        client: A structured-output client.
        claim: The disputed claim, as code stated it.
        holders: Who holds each position, as code assembled it.
        evidence_for: Fact statements supporting the claim.
        evidence_against: Fact statements against it.
        source_ids_for: Sources behind the supporting evidence.
        source_ids_against: Sources behind the opposing evidence.

    Returns:
        Tuple of (case for, case against).
    """
    prompt = (
        f"DISPUTED CLAIM: {claim}\nHOLDERS: {holders}\n\n"
        "EVIDENCE FOR\n" + "\n".join(f"- {e}" for e in evidence_for or ["(none supplied)"])
        + "\n\nEVIDENCE AGAINST\n"
        + "\n".join(f"- {e}" for e in evidence_against or ["(none supplied)"])
    )
    data, _ = client.generate_structured(
        prompt=prompt,
        schema=DISPUTE_SCHEMA,
        system=DISPUTE_ROLE,
        max_tokens=SMALL_CALL_MAX_TOKENS,
    )

    return (
        DisputeSide(
            heading=(data.get("for_heading") or "The case for").strip(),
            text=data.get("for_text", "").strip(),
            source_ids=list(source_ids_for),
        ),
        DisputeSide(
            heading=(data.get("against_heading") or "The case against").strip(),
            text=data.get("against_text", "").strip(),
            source_ids=list(source_ids_against),
        ),
    )


def run_blurb_pass(
    client: Any,
    items: list[str],
    context_by_index: Optional[dict[int, str]] = None,
    role: str = BLURB_ROLE,
) -> dict[int, str]:
    """Pass 5 and 7a: write context notes for entries code already placed.

    Entries are addressed by index so a model cannot move, merge, or invent one.

    Args:
        client: A structured-output client.
        items: The entries, in order.
        context_by_index: Extra material per entry, if any.
        role: The system prompt to use.

    Returns:
        Map of index to context note. Indexes outside the input are dropped.
    """
    if not items:
        return {}

    blurbs: dict[int, str] = {}
    for start in range(0, len(items), BLURB_BATCH):
        batch = list(enumerate(items))[start: start + BLURB_BATCH]
        lines = []
        for index, item in batch:
            extra = (context_by_index or {}).get(index, "")
            lines.append(f"[{index}] {item}" + (f"\n    material: {extra}" if extra else ""))

        data, _ = client.generate_structured(
            prompt="ENTRIES\n" + "\n".join(lines),
            schema=BLURBS_SCHEMA,
            system=role,
            max_tokens=SMALL_CALL_MAX_TOKENS,
        )

        for blurb in data.get("blurbs", []):
            index = blurb.get("index")
            text = (blurb.get("context") or "").strip()
            if isinstance(index, int) and 0 <= index < len(items) and text:
                blurbs[index] = text
    return blurbs


def run_players_pass(
    client: Any, names: list[str], material_by_name: dict[str, list[str]]
) -> list[Player]:
    """Pass 6: write cards for the names code decided qualify.

    Args:
        client: A structured-output client.
        names: Names that appear in 2+ sections.
        material_by_name: Facts mentioning each name.

    Returns:
        Cards for the qualifying names, in the order code supplied them. Cards
        for names that were not asked for are discarded.
    """
    if not names:
        return []

    blocks = []
    for name in names:
        material = material_by_name.get(name, [])
        blocks.append(f"{name}\n" + "\n".join(f"  - {m}" for m in material))

    data, _ = client.generate_structured(
        prompt="NAMES AND THEIR MATERIAL\n\n" + "\n\n".join(blocks),
        schema=PLAYERS_SCHEMA,
        system=PLAYERS_ROLE,
        max_tokens=SMALL_CALL_MAX_TOKENS,
    )

    wanted = {name.lower(): name for name in names}
    cards: dict[str, Player] = {}
    for player in data.get("players", []):
        written = (player.get("name") or "").strip()
        canonical = wanted.get(written.lower())
        if not canonical or canonical in cards:
            continue
        cards[canonical] = Player(
            name=canonical,
            role=(player.get("role") or "").strip(),
            body=(player.get("body") or "").strip(),
        )
    return [cards[name] for name in names if name in cards]


def run_contribution_pass(
    client: Any, sources: list[dict], facts_by_source: dict[str, list[str]]
) -> dict[str, str]:
    """Pass 7c: one line per source saying what only it contributes.

    Args:
        client: A structured-output client.
        sources: Source dicts with `source_id`, `title`, `source_type`.
        facts_by_source: Facts harvested from each source.

    Returns:
        Map of source ID to its contribution line.
    """
    if not sources:
        return {}

    blocks = []
    for source in sources:
        source_id = source.get("source_id", "")
        facts = facts_by_source.get(source_id, [])[:12]
        blocks.append(
            f"{source_id} · {source.get('title') or 'Untitled'} "
            f"({source.get('source_type') or 'source'})\n"
            + "\n".join(f"  - {f}" for f in facts)
        )

    data, _ = client.generate_structured(
        prompt="SOURCES\n\n" + "\n\n".join(blocks),
        schema=CONTRIBUTIONS_SCHEMA,
        system=CONTRIBUTION_ROLE,
        max_tokens=SMALL_CALL_MAX_TOKENS,
    )

    known = {s.get("source_id") for s in sources}
    return {
        c["source_id"]: c.get("contribution", "").strip()
        for c in data.get("contributions", [])
        if c.get("source_id") in known and c.get("contribution", "").strip()
    }


def build_record_entries(
    dated_facts: list[dict], blurbs: Optional[dict[int, str]] = None
) -> list[RecordEntry]:
    """Pass 5, code half: the chronology skeleton.

    Code extracts, sorts, and places the entries; the model only writes the
    context notes, and a note whose date does not match its entry is dropped.

    Args:
        dated_facts: Routed facts carrying `when` and `sort_key`.
        blurbs: Context notes by entry index.

    Returns:
        The Record section.
    """
    entries: list[RecordEntry] = []
    for index, fact in enumerate(dated_facts):
        entries.append(
            RecordEntry(
                when=fact["when"],
                what=fact["text"],
                source_ids=[fact["source_id"]] if fact.get("source_id") else [],
                context=(blurbs or {}).get(index),
                sort_key=fact.get("sort_key"),
            )
        )
    return entries


def build_anecdotes(
    facts: list[dict], blurbs: Optional[dict[int, str]] = None
) -> list[Anecdote]:
    """Pass 7a, code half: the texture bin.

    Args:
        facts: Facts the subject map put in the anecdotes bin.
        blurbs: Context notes by index.

    Returns:
        The Details & Anecdotes section.
    """
    return [
        Anecdote(
            text=fact["text"],
            source_ids=[fact["source_id"]] if fact.get("source_id") else [],
            context=(blurbs or {}).get(index),
        )
        for index, fact in enumerate(facts)
    ]


# =============================================================================
# Person classification + inline-introduction repair (§J pass 8's repair round)
# =============================================================================

# NOTE: `_array_of` already wraps its argument with `_object`. Passing an
# already-built object here double-wraps it, and the model then echoes the
# schema's own scaffolding back as data — which reads as "no names are people"
# and silently suppressed 25 real lint findings before it was caught.
PEOPLE_SCHEMA: dict = _object(
    {
        "people": _array_of(
            {
                "name": {"type": "string"},
                "is_person": {"type": "boolean"},
            }
        )
    }
)

PEOPLE_ROLE = """You are sorting names out of a research document into people and
not-people.

A PERSON is a human being — a researcher, an author, an official, a witness, an
ancient writer. Anything else is not: places, lakes, regions, historical
periods, institutions, technologies, instruments, companies, podcasts, books,
papers, and video titles are all NOT people.

Judge the name itself. If you genuinely cannot tell, answer false — the cost of
a wrong "true" is a document that stops to explain who Synthetic Aperture Radar
is, and the cost of a wrong "false" is only that a minor name goes unglossed.

Return one entry for every name you are given, and no others."""

INTRO_SCHEMA: dict = _object(
    {
        "introductions": _array_of(
            {
                "name": {"type": "string"},
                "introduction": {"type": "string"},
            }
        )
    }
)

INTRO_ROLE = """You write the four-or-five-word gloss that tells a reader who
someone is, at the moment they first meet the name.

Write ONLY the gloss, not the name and not a sentence. It will be inserted
directly after the name, between commas:

  name: Robert Schoch
  introduction: the geologist who redated the Sphinx

  name: Pomponius Mela
  introduction: a Roman geographer writing in the first century

Rules that matter:
- Do NOT repeat what the sentence already says. If the passage reads "Graham
  Hancock published Fingerprints of the Gods", the gloss "the author of
  Fingerprints of the Gods" tells the reader nothing they are not about to
  read. Say the thing the sentence leaves out — what they do, or who they are
  to this story.
- Ground it in the passage you are given. If the passage does not say who they
  are, write what it does establish about them, and nothing more.
- No adjectives of praise or dismissal. "the geologist who redated the Sphinx",
  never "the controversial geologist".
- Lower case at the start UNLESS the first word is a proper noun, and keep the
  capitals on every name inside the gloss: "the scholar who read Herodotus and
  Strabo", never "herodotus and strabo".
- No full stop at the end.
- Under eight words.

If the passage gives you nothing at all to say about them, return an empty
string for that name. An empty answer is better than an invented credential."""


def classify_people(names: list[str], client: Any, topic: str = "") -> set[str]:
    """Decide which of these names are people.

    One call for the whole list: the judgement is comparative and the answers
    are steadier when the model sees the field at once.

    Args:
        names: Candidate names from the ranking.
        client: A structured client.
        topic: The job topic, for context.

    Returns:
        The subset that are people. On failure, returns every name — the
        one-off rule then over-fires as it did before, which is the safe
        direction: a spurious lint error is noise, a missing one is a reader
        meeting a name cold.
    """
    if not names:
        return set()

    try:
        data, _usage = client.generate_structured(
            prompt=(f"TOPIC: {topic}\n\n" if topic else "")
            + "NAMES:\n"
            + "\n".join(f"- {name}" for name in names),
            schema=PEOPLE_SCHEMA,
            system=PEOPLE_ROLE,
            max_tokens=2_000,
        )
    except Exception as exc:
        logger.warning(f"Person classification failed ({exc}); keeping every name")
        return set(names)

    known = set(names)
    return {
        entry["name"]
        for entry in (data.get("people") or [])
        if entry.get("is_person") and entry.get("name") in known
    }


def write_introductions(
    needed: dict[str, str], client: Any, topic: str = ""
) -> dict[str, str]:
    """Write one inline gloss per name, from the passage it appears in.

    Args:
        needed: Name to the passage where the reader first meets them.
        client: A structured client.
        topic: The job topic, for context.

    Returns:
        Name to gloss. Names the model could say nothing about are omitted
        rather than given an invented credential.
    """
    if not needed:
        return {}

    payload = "\n\n".join(
        f"name: {name}\npassage: {passage[:600]}" for name, passage in needed.items()
    )
    try:
        data, _usage = client.generate_structured(
            prompt=(f"TOPIC: {topic}\n\n" if topic else "") + payload,
            schema=INTRO_SCHEMA,
            system=INTRO_ROLE,
            max_tokens=2_000,
        )
    except Exception as exc:
        logger.warning(f"Introduction pass failed ({exc}); no repairs written")
        return {}

    return {
        entry["name"]: entry["introduction"].strip().rstrip(".")
        for entry in (data.get("introductions") or [])
        if entry.get("name") in needed and (entry.get("introduction") or "").strip()
    }
