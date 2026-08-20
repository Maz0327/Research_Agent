"""Harvest recall audit (work order I.25).

Coverage gate 13 asks whether the Briefing used the harvest inventory. It
cannot ask whether the *inventory* used the source, because the inventory is
the only record of what the source contained — one model's word, trusted
completely, with nothing behind it. That is the single point of trust this
module closes.

The method is a spot check, not a proof: code samples raw paragraphs, a model
re-extracts facts from that sample and nothing else, and code measures how many
of those facts the harvest already holds. A high rate is evidence the harvest
read the whole source. A low rate is evidence it summarized.

The sample is stratified by *position* on purpose. The failure this is built to
catch is the one D-029 documented from the other side: a model handed a long
source returns a roughly fixed number of items whatever it is handed, which
means the back of a long document goes missing while the front looks perfect.
An unstratified sample would average that away; thirds make it visible.
"""
import random
import re
from typing import Any, Optional

from loguru import logger

from backend.config import get_settings
from backend.pipeline.injection_guard import delimit
from backend.pipeline.text_similarity import content_tokens, statement_similarity

# Recall asks "did the harvest capture this at all", which is a looser question
# than `says_the_same_thing` answers. That matcher refuses paraphrase by design
# — it guards against inventing corroboration — and using it here would report
# genuine captures as misses. This threshold is calibrated instead: see
# `calibrate_matcher`, which measures where real matches and unrelated facts
# actually separate on a given corpus.
RECALL_THRESHOLD = 0.45

# Below this a "fact" is too short to match on anything but chance.
MIN_FACT_TOKENS = 4

# A transcript arrives as one unbroken blob, so paragraph splitting has to fall
# back to sentence grouping or the sample would be a single chunk. Measured on
# the Hawara fixture 2026-08-20: Supadata transcripts carry NO punctuation and
# NO newlines at all — SRC_2 is 4,019 words with zero full stops — so sentence
# grouping fails too and a fixed word window is the only splitter left.
_SENTENCES_PER_BLOCK = 4
_MIN_BLOCK_WORDS = 25
_WORDS_PER_BLOCK = 80

AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["facts"],
    "additionalProperties": False,
}

AUDIT_ROLE = """You extract the concrete content of a text as dense, self-contained fact statements.

Each fact is ONE sentence that survives being read alone. Preserve every
specific: numbers with what they measure, names of people, places and works and
what they did, dates, events in order, causal claims as the text makes them.

NEVER write meta-statements ("the passage argues", "the author discusses").
Write the content itself.

Extract every fact the passage contains. This is a short excerpt, so the count
is small — do not pad it, and do not compress it either.

Skip filler, greetings, sponsor reads, and asides about the speaker's own life
or other episodes. These are the same exclusions the harvest works under, and
this measurement is only meaningful if both passes are asked for the same thing:
a fact the harvest was told to skip is not a fact the harvest missed.

EMPTY OUTPUT PERMISSION
Return an empty list if the passage carries no facts. Never invent content to
fill it. Sparse and accurate beats dense and fabricated.

SOURCE ISOLATION
This passage is the only thing you know about. Do not add anything you know
from elsewhere, and do not refer to other sources."""


def blocks_of(text: str, min_words: int = _MIN_BLOCK_WORDS) -> list[str]:
    """Split a source into sampleable blocks.

    Prefers real paragraphs; falls back to grouped sentences for transcripts,
    which carry no paragraph breaks at all.

    Args:
        text: The source's raw text.
        min_words: Blocks shorter than this are dropped as unsampleable.

    Returns:
        Blocks in document order.
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    long_enough = [p for p in paragraphs if len(p.split()) >= min_words]
    if len(long_enough) >= 3:
        return long_enough

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    blocks = [
        " ".join(sentences[i : i + _SENTENCES_PER_BLOCK])
        for i in range(0, len(sentences), _SENTENCES_PER_BLOCK)
    ]
    usable = [b for b in blocks if len(b.split()) >= min_words]
    if len(usable) >= 3:
        return usable

    words = text.split()
    windows = [
        " ".join(words[i : i + _WORDS_PER_BLOCK])
        for i in range(0, len(words), _WORDS_PER_BLOCK)
    ]
    return [w for w in windows if len(w.split()) >= min_words]


def stratified_sample(
    text: str,
    per_source: int = 3,
    seed: int = 0,
) -> list[tuple[str, str]]:
    """Take blocks spread across the front, middle, and back of a source.

    Args:
        text: The source's raw text.
        per_source: How many blocks to take, spread across the thirds.
        seed: Seed for the pick within each third, so a re-run reproduces.

    Returns:
        List of (position, block), position being "front", "middle", or "back".
    """
    blocks = blocks_of(text)
    if not blocks:
        return []

    rng = random.Random(seed)
    third = max(1, len(blocks) // 3)
    bands = [
        ("front", blocks[:third]),
        ("middle", blocks[third : third * 2] or blocks[:third]),
        ("back", blocks[third * 2 :] or blocks[-third:]),
    ]

    picked: list[tuple[str, str]] = []
    for index in range(per_source):
        position, band = bands[index % 3]
        if band:
            picked.append((position, rng.choice(band)))
    return picked


def best_match(fact: str, inventory_texts: list[str]) -> float:
    """Score a fact against the closest thing the inventory holds.

    Args:
        fact: A fact re-extracted from a sampled block.
        inventory_texts: Every harvested fact for the same source.

    Returns:
        The best similarity found, 0.0 when there is nothing to compare.
    """
    if not inventory_texts or len(content_tokens(fact)) < MIN_FACT_TOKENS:
        return 0.0
    return max(statement_similarity(fact, held) for held in inventory_texts)


def score_sample(sampled_facts: list[str], inventory_texts: list[str]) -> list[dict]:
    """Score every re-extracted fact against the inventory.

    Scores are kept for hits as well as misses. A recall number is only worth
    as much as the threshold under it, and the threshold is only arguable if
    the distribution it cuts is on the page.

    Args:
        sampled_facts: Facts re-extracted from sampled blocks.
        inventory_texts: Harvested facts for the same source.

    Returns:
        One entry per scorable fact, carrying the fact and its best score.
    """
    return [
        {"fact": fact, "best_score": round(best_match(fact, inventory_texts), 3)}
        for fact in sampled_facts
        if len(content_tokens(fact)) >= MIN_FACT_TOKENS
    ]


def recall_of(
    sampled_facts: list[str],
    inventory_texts: list[str],
    threshold: float = RECALL_THRESHOLD,
) -> tuple[float, list[dict]]:
    """Measure how much of a re-extracted sample the harvest already holds.

    Args:
        sampled_facts: Facts re-extracted from sampled blocks.
        inventory_texts: Harvested facts for the same source.
        threshold: Similarity at which a fact counts as captured.

    Returns:
        Tuple of (recall rate, misses). Each miss carries the fact and the best
        score it managed, so a borderline threshold is arguable from the data
        rather than from the number alone.
    """
    scored = score_sample(sampled_facts, inventory_texts)
    if not scored:
        return 1.0, []

    misses = [entry for entry in scored if entry["best_score"] < threshold]
    return (len(scored) - len(misses)) / len(scored), misses


def calibrate_matcher(inventory_texts: list[str], sample: int = 60) -> dict:
    """Measure where matched and unmatched facts actually separate.

    Scores each fact against the inventory with itself removed (the honest
    "would we find this if the harvest had phrased it differently" case), and
    against a rotation of the inventory (the unrelated case). A threshold is
    only defensible when those two distributions do not overlap at it.

    Args:
        inventory_texts: Harvested facts.
        sample: How many facts to score.

    Returns:
        Dict of the two score distributions and the threshold in use.
    """
    facts = inventory_texts[:sample]
    if len(facts) < 4:
        return {}

    self_scores = []
    unrelated_scores = []
    for index, fact in enumerate(facts):
        others = facts[:index] + facts[index + 1 :]
        self_scores.append(statement_similarity(fact, fact))
        unrelated_scores.append(best_match(fact, others))

    return {
        "identical_min": round(min(self_scores), 3),
        "unrelated_max": round(max(unrelated_scores), 3),
        "unrelated_mean": round(sum(unrelated_scores) / len(unrelated_scores), 3),
        "threshold": RECALL_THRESHOLD,
        "separated": min(self_scores) >= RECALL_THRESHOLD > max(unrelated_scores),
    }


def _reextract(client: Any, source_id: str, position: str, block: str) -> list[str]:
    """Re-extract facts from one sampled block; never fails the audit."""
    try:
        data, _usage = client.generate_structured(
            prompt=f"PASSAGE ({position} of source {source_id}):\n\n"
            + delimit(block, source_id),
            schema=AUDIT_SCHEMA,
            system=AUDIT_ROLE,
            max_tokens=2_000,
        )
    except Exception as exc:
        logger.warning(f"Harvest audit: re-extraction failed on {source_id} ({exc})")
        return []
    return [f.strip() for f in (data.get("facts") or []) if f and f.strip()]


def truncated_sources(sources: list[dict], max_chars: Optional[int] = None) -> list[dict]:
    """Find sources the harvest never saw the end of.

    This is not a recall miss and must not be reported as one: text past the
    harvest's character cap was never sent to a model at all. A source that
    scores badly here has a cause that no prompt change will fix.

    Args:
        sources: Ledger entries carrying `source_id` and `full_text`.
        max_chars: The harvest cap; defaults to the configured value.

    Returns:
        One entry per truncated source, with how much went unread.
    """
    cap = max_chars if max_chars is not None else get_settings().harvest_max_chars
    cut = []
    for source in sources:
        length = len(source.get("full_text") or "")
        if length > cap:
            cut.append(
                {
                    "source_id": source.get("source_id", ""),
                    "chars": length,
                    "unread_chars": length - cap,
                    "unread_share": round((length - cap) / length, 3),
                }
            )
    return cut


def audit_harvest_recall(
    sources: list[dict],
    inventory: list[dict],
    client: Any,
    per_source: int = 3,
    max_sources: Optional[int] = None,
    seed: int = 0,
) -> dict:
    """Spot-check how much of each source the harvest actually captured.

    Args:
        sources: Ledger entries carrying `source_id` and `full_text`.
        inventory: Harvest inventory entries carrying `source_id` and `text`.
        client: A structured client for the re-extraction calls.
        per_source: Blocks sampled per source, spread across the thirds.
        max_sources: Audit only this many sources; None audits all of them.
        seed: Sampling seed, so a re-run reproduces the same blocks.

    Returns:
        A report: overall recall, recall by position, per-source rows, and every
        miss with the score it managed.
    """
    by_source: dict[str, list[str]] = {}
    for fact in inventory:
        by_source.setdefault(fact.get("source_id", ""), []).append(fact.get("text", ""))

    audited = [s for s in sources if (s.get("full_text") or "").strip()]
    if max_sources is not None:
        audited = audited[:max_sources]

    rows: list[dict] = []
    all_misses: list[dict] = []
    all_scores: list[float] = []
    by_position: dict[str, list[int]] = {"front": [0, 0], "middle": [0, 0], "back": [0, 0]}

    for source in audited:
        source_id = source.get("source_id", "")
        held = by_source.get(source_id, [])
        sampled = stratified_sample(source.get("full_text") or "", per_source, seed)

        source_hits = source_total = 0
        source_positions: dict[str, list[int]] = {
            "front": [0, 0],
            "middle": [0, 0],
            "back": [0, 0],
        }
        for position, block in sampled:
            facts = _reextract(client, source_id, position, block)
            scored = score_sample(facts, held)
            all_scores.extend(entry["best_score"] for entry in scored)
            misses = [e for e in scored if e["best_score"] < RECALL_THRESHOLD]
            scorable = len(scored)
            hits = scorable - len(misses)

            source_hits += hits
            source_total += scorable
            source_positions[position][0] += hits
            source_positions[position][1] += scorable
            by_position[position][0] += hits
            by_position[position][1] += scorable
            for miss in misses:
                all_misses.append({**miss, "source_id": source_id, "position": position})

        rows.append(
            {
                "source_id": source_id,
                "sampled_facts": source_total,
                "captured": source_hits,
                "recall": round(source_hits / source_total, 3) if source_total else None,
                "inventory_size": len(held),
                "by_position": {
                    position: round(hits / total, 3) if total else None
                    for position, (hits, total) in source_positions.items()
                },
            }
        )

    total_hits = sum(r["captured"] for r in rows)
    total_facts = sum(r["sampled_facts"] for r in rows)

    # Pooled rates weight by fact count, so one dense article can carry the
    # whole number and hide a source that was barely read. Measured on the
    # Hawara fixture: adding two text articles moved pooled back-of-source
    # recall from 0.55 to 0.82 while the thin sources were unchanged. The
    # macro average gives every source one vote, which is the question being
    # asked here — did the harvest read each source, not the corpus on average.
    scored_rows = [r for r in rows if r["recall"] is not None]
    macro = (
        round(sum(r["recall"] for r in scored_rows) / len(scored_rows), 3)
        if scored_rows
        else None
    )

    return {
        "overall_recall": round(total_hits / total_facts, 3) if total_facts else None,
        "macro_recall": macro,
        "weakest_sources": [
            {"source_id": r["source_id"], "recall": r["recall"]}
            for r in sorted(scored_rows, key=lambda r: r["recall"])[:3]
        ],
        "sampled_facts": total_facts,
        "by_position": {
            position: round(hits / total, 3) if total else None
            for position, (hits, total) in by_position.items()
        },
        "by_position_macro": _macro_by_position(rows),
        "sources": rows,
        "misses": all_misses,
        "threshold": RECALL_THRESHOLD,
        "score_distribution": _distribution(all_scores),
        "truncated_sources": truncated_sources(audited),
    }


def _macro_by_position(rows: list[dict]) -> dict:
    """Average each position across sources, one vote per source."""
    out = {}
    for position in ("front", "middle", "back"):
        rates = [
            r["by_position"][position]
            for r in rows
            if r.get("by_position", {}).get(position) is not None
        ]
        out[position] = round(sum(rates) / len(rates), 3) if rates else None
    return out


def _distribution(scores: list[float]) -> dict:
    """Bucket the scores so the threshold's cut point is visible, not asserted."""
    if not scores:
        return {}
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for score in scores:
        index = min(int(score * 5), 4)
        buckets[list(buckets)[index]] += 1
    ordered = sorted(scores)
    return {
        "buckets": buckets,
        "median": round(ordered[len(ordered) // 2], 3),
        "n": len(scores),
    }
