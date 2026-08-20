"""Corpus balance — the advisory header block (work order I.24).

A Briefing can be entirely accurate and still be built on a lopsided corpus:
six videos from one creator, or a decade-old date spread on a live dig, or
sixteen sources that all trace back to one press release. None of that is
wrong, and the owner may well have chosen it on purpose. The rule is only that
it is never *invisible*.

Everything here is advisory. Nothing gates, nothing is stripped, nothing fails.
The block states what the corpus is made of and lets the reader judge.

Division of labour follows the work order: the spreads and the network overlap
are code (they are counting problems and a model would only add error), and
the per-source stance label is one small LLM call, because "is this source
arguing for the claim, against it, or reporting it" is a reading judgement.
"""
from collections import Counter
from collections.abc import Iterable
from typing import Any, Optional
from urllib.parse import urlparse

from loguru import logger

from backend.models.briefing import CorpusBalance

# A stance vocabulary the reader can act on. Deliberately four words: a longer
# scale invites the model to split hairs it cannot actually see from a title
# and a skim summary.
STANCES = ("believer", "skeptic", "neutral", "institutional")

STANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "stances": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "stance": {"type": "string", "enum": list(STANCES)},
                },
                "required": ["source_id", "stance"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["stances"],
    "additionalProperties": False,
}

STANCE_ROLE = """You are labelling the STANCE of each source in a research corpus.

You are not judging whether a source is right, and you are not summarizing it.
You are answering one question per source: what posture does it take toward the
topic's contested claim?

  believer       - argues the extraordinary claim is true, or presents it as
                   established without qualification
  skeptic        - argues against the claim, or exists mainly to debunk it
  neutral        - reports the dispute without taking a side
  institutional  - speaks as the official body, agency, ministry, university, or
                   journal with formal authority over the subject matter

Judge only from the title and summary you are given. If a source does not
clearly fit, label it `neutral` — that is the honest answer, not a failure.
An institutional source that also argues a side is still `institutional`;
who is speaking outranks what they conclude.

Return one entry for every source_id you are given, and no others.
"""


# One outlet spelled two ways is one outlet. Kept deliberately short: a general
# "same company" map would start making editorial-independence calls that this
# block has no business making, so it holds only pure aliases of one property.
HOST_ALIASES = {
    "youtu.be": "youtube.com",
    "m.youtube.com": "youtube.com",
    "m.wikipedia.org": "wikipedia.org",
}


def domain_of(url: Optional[str]) -> str:
    """Reduce a URL to a comparable host, dropping `www.`, the port, and aliases.

    Args:
        url: A source URL, possibly empty or malformed.

    Returns:
        The bare host, or an empty string when there is nothing to parse.
    """
    if not url:
        return ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return HOST_ALIASES.get(host, host)


def domain_spread(sources: Iterable[dict]) -> dict[str, int]:
    """Count sources per host.

    Args:
        sources: Source ledger entries.

    Returns:
        Host to source count, hosts with no URL omitted.
    """
    counts = Counter(domain_of(s.get("url")) for s in sources)
    counts.pop("", None)
    return dict(counts)


def _year_of(published: Any) -> Optional[int]:
    """Pull a four-digit year off a stored publication date."""
    text = str(published or "").strip()
    if len(text) < 4 or not text[:4].isdigit():
        return None
    year = int(text[:4])
    # A ledger date outside this window is a parse artifact, not a publication.
    return year if 1400 <= year <= 2200 else None


def date_spread(sources: Iterable[dict]) -> Optional[str]:
    """Describe the corpus's publication window in one human phrase.

    Args:
        sources: Source ledger entries.

    Returns:
        A phrase like "2019-2025, 3 undated", or None when nothing is dated.
    """
    sources = list(sources)
    years = [y for y in (_year_of(s.get("published")) for s in sources) if y]
    undated = len(sources) - len(years)
    if not years:
        return f"none dated ({undated} sources)" if sources else None

    span = str(min(years)) if min(years) == max(years) else f"{min(years)}-{max(years)}"
    return f"{span}, {undated} undated" if undated else span


def _creator_of(source: dict) -> str:
    """Normalize the byline, treating the stored string "None" as absent."""
    creator = str(source.get("creator") or "").strip()
    return "" if creator.lower() in ("", "none", "unknown") else creator


def shared_bylines(sources: Iterable[dict]) -> dict[str, int]:
    """Count sources per byline, keeping only bylines that appear more than once.

    Args:
        sources: Source ledger entries.

    Returns:
        Byline to source count, for bylines carrying 2+ sources.
    """
    counts = Counter(c for c in (_creator_of(s) for s in sources) if c)
    return {name: n for name, n in counts.items() if n > 1}


def network_note(
    sources: Iterable[dict],
    duplicate_groups: Optional[list[list[str]]] = None,
) -> Optional[str]:
    """State the corpus's concentration in one sentence, or say nothing.

    This is the "one crew" catch mechanized: a corpus can look like sixteen
    independent sources and be four, because one host carries most of them, one
    byline wrote several, or the duplicate detector already found republications.

    Args:
        sources: Source ledger entries.
        duplicate_groups: Syndication groups from `find_duplicate_sources`.

    Returns:
        A sentence naming every concentration found, or None when the corpus is
        genuinely spread out.
    """
    sources = list(sources)
    if not sources:
        return None

    notes: list[str] = []

    domains = domain_spread(sources)
    if domains:
        host, n = max(domains.items(), key=lambda kv: kv[1])
        # Half the corpus on one host is the point at which "independent
        # sources" stops describing what the reader is looking at.
        if n > 1 and n * 2 >= len(sources):
            notes.append(f"{n} of {len(sources)} sources are from {host}")

    bylines = shared_bylines(sources)
    if bylines:
        notes.append(
            "shared bylines: "
            + ", ".join(f"{name} ({n})" for name, n in sorted(bylines.items()))
        )

    republished = sum(len(g) - 1 for g in (duplicate_groups or []) if len(g) > 1)
    if republished:
        notes.append(f"{republished} republished copies detected")

    return "; ".join(notes) if notes else None


def stance_counts(labels: Iterable[dict]) -> dict[str, int]:
    """Tally stance labels, ignoring anything outside the vocabulary.

    Args:
        labels: Entries carrying a `stance` key.

    Returns:
        Stance to count, in vocabulary order, zero-count stances omitted.
    """
    counts = Counter(
        str(item.get("stance", "")).lower()
        for item in labels
        if str(item.get("stance", "")).lower() in STANCES
    )
    return {stance: counts[stance] for stance in STANCES if counts[stance]}


def _stance_payload(sources: list[dict]) -> str:
    """Render the sources the labeller sees: identity, title, summary only."""
    lines = []
    for source in sources:
        summary = str(source.get("skim_summary") or "").strip()[:400]
        lines.append(
            f"{source.get('source_id', '?')} | {source.get('title', '(untitled)')}"
            + (f"\n  {summary}" if summary else "")
        )
    return "\n".join(lines)


def label_stances(sources: list[dict], client: Any, topic: str = "") -> list[dict]:
    """Ask the model for one stance label per source.

    A single call for the whole corpus: stance is a comparative judgement, and
    the labels are more consistent when the model sees the field at once.

    Args:
        sources: Source ledger entries.
        client: A structured client exposing `generate_structured`.
        topic: The job topic, for context on what the sides are.

    Returns:
        Stance entries. Empty when the corpus is empty or the call fails —
        this block is advisory and must never take a Briefing down with it.
    """
    if not sources:
        return []

    prompt = (
        (f"TOPIC: {topic}\n\n" if topic else "")
        + "SOURCES:\n"
        + _stance_payload(sources)
    )
    try:
        data, _usage = client.generate_structured(
            prompt=prompt,
            schema=STANCE_SCHEMA,
            system=STANCE_ROLE,
            max_tokens=4_000,
        )
    except Exception as exc:  # advisory block: degrade, never fail the build
        logger.warning(f"Corpus balance: stance labelling failed ({exc}); omitting stances")
        return []

    known = {s.get("source_id") for s in sources}
    return [
        entry
        for entry in (data.get("stances") or [])
        if entry.get("source_id") in known
    ]


def build_corpus_balance(
    sources: list[dict],
    client: Any = None,
    topic: str = "",
    duplicate_groups: Optional[list[list[str]]] = None,
) -> Optional[CorpusBalance]:
    """Assemble the header advisory.

    Args:
        sources: Source ledger entries.
        client: Structured client for the stance call; omit to skip stances.
        topic: The job topic, passed to the stance call for context.
        duplicate_groups: Syndication groups from `find_duplicate_sources`.

    Returns:
        The block, or None when there are no sources to describe.
    """
    if not sources:
        return None

    labels = label_stances(sources, client, topic) if client is not None else []
    return CorpusBalance(
        domains=domain_spread(sources),
        date_range=date_spread(sources),
        network_note=network_note(sources, duplicate_groups),
        stance_counts=stance_counts(labels),
    )
