"""Build a labelled faithfulness set from a corpus, without asking anyone.

A judge contest needs ground truth, and hand-labelling is slow, small, and
disputable. Ground truth can instead be constructed: a fact harvested from a
source is supported by that source, and a fact altered in a specific way is
not. The alteration is the label.

The four corruptions are the failure modes a judge is actually for, so a judge
that scores well here is good at the job rather than good at spotting nonsense:

- **figure**: the same sentence with a different number.
- **attribution**: the same action credited to a different real name from the
  same corpus.
- **negation**: the claim turned into its opposite.
- **addition**: a specific detail the source never gives, welded onto a real fact.

Word-salad fabrications are deliberately not used. They are trivially
detectable and would flatter every judge.
"""

import random
import re
from typing import Optional

_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")
_NAME = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b")

_NEGATIONS = [
    (re.compile(r"\bwas\b"), "was never"),
    (re.compile(r"\bwere\b"), "were never"),
    (re.compile(r"\bfound\b"), "failed to find"),
    (re.compile(r"\breported\b"), "declined to report"),
    (re.compile(r"\bconfirmed\b"), "contradicted"),
    (re.compile(r"\bshowed\b"), "showed no sign of"),
    (re.compile(r"\bhas\b"), "has never"),
]

_ADDITIONS = [
    " The report was peer reviewed in Nature the following year.",
    " The finding was independently replicated by two other teams.",
    " The full data set has been public since 2011.",
    " A second survey the next season reached the same conclusion.",
    " The team published the raw scans alongside the paper.",
]

CORRUPTIONS = ("figure", "attribution", "negation", "addition")


def _swap_figure(text: str, rng: random.Random) -> Optional[str]:
    """Change a number to a different plausible one."""
    numbers = list(_NUMBER.finditer(text))
    if not numbers:
        return None
    match = rng.choice(numbers)
    original = match.group(0)
    digits = original.replace(",", "")
    try:
        value = int(digits)
    except ValueError:
        return None
    changed = value * rng.choice([2, 3, 4]) + rng.choice([1, 7, 11])
    return text[: match.start()] + f"{changed:,}" + text[match.end():]


def _swap_attribution(text: str, rng: random.Random, other_names: list[str]) -> Optional[str]:
    """Credit the same action to a different real name from the corpus."""
    names = [m.group(0) for m in _NAME.finditer(text)]
    candidates = [n for n in other_names if n not in names]
    if not names or not candidates:
        return None
    return text.replace(names[0], rng.choice(candidates), 1)


def _negate(text: str, rng: random.Random) -> Optional[str]:
    """Turn the claim into its opposite."""
    for pattern, replacement in _NEGATIONS:
        if pattern.search(text):
            return pattern.sub(replacement, text, count=1)
    return None


def _add_detail(text: str, rng: random.Random) -> Optional[str]:
    """Weld a specific, checkable, absent detail onto a real fact."""
    return text.rstrip(". ") + "." + rng.choice(_ADDITIONS)


def names_in_corpus(facts: list[str], minimum: int = 2) -> list[str]:
    """Names that appear often enough to be swappable attribution targets.

    Args:
        facts: Fact statements from the corpus.
        minimum: How many facts a name must appear in.

    Returns:
        Sorted list of names.
    """
    counts: dict[str, int] = {}
    for fact in facts:
        for match in _NAME.finditer(fact):
            counts[match.group(0)] = counts.get(match.group(0), 0) + 1
    return sorted(name for name, count in counts.items() if count >= minimum)


def build_faithfulness_set(
    facts: list[dict],
    size: int = 40,
    seed: int = 17,
) -> list[dict]:
    """Build a balanced labelled set: half supported, half corrupted.

    Args:
        facts: Harvest entries with `fact_id`, `source_id`, and `text`.
        size: Total items. Half are supported, half corrupted.
        seed: Fixed so the set is identical for every judge and every rerun.

    Returns:
        Items with `item_id`, `source_id`, `statement`, `label`
        ("supported" or "unsupported"), `corruption`, and `original`.
    """
    rng = random.Random(seed)
    usable = [f for f in facts if len(f.get("text", "").split()) >= 8]
    rng.shuffle(usable)
    names = names_in_corpus([f["text"] for f in usable])

    half = size // 2
    items: list[dict] = []

    for fact in usable[:half]:
        items.append(
            {
                "item_id": f"F{len(items) + 1}",
                "source_id": fact["source_id"],
                "statement": fact["text"],
                "label": "supported",
                "corruption": None,
                "original": fact["text"],
            }
        )

    makers = {
        "figure": lambda t: _swap_figure(t, rng),
        "attribution": lambda t: _swap_attribution(t, rng, names),
        "negation": lambda t: _negate(t, rng),
        "addition": lambda t: _add_detail(t, rng),
    }

    # Each corruption needs a fact it can actually be applied to - a figure
    # swap needs a number, an attribution swap needs a name - so the search is
    # per corruption rather than a single walk down the list. Without this a
    # small corpus produces a lopsided set, which would quietly turn the
    # contest into a different measurement.
    pool = usable[half:]
    wanted = [CORRUPTIONS[i % len(CORRUPTIONS)] for i in range(half)]
    used: set[str] = set()

    for kind in wanted:
        for fact in pool:
            if fact["fact_id"] in used:
                continue
            corrupted = makers[kind](fact["text"])
            if corrupted and corrupted != fact["text"]:
                used.add(fact["fact_id"])
                items.append(
                    {
                        "item_id": f"F{len(items) + 1}",
                        "source_id": fact["source_id"],
                        "statement": corrupted,
                        "label": "unsupported",
                        "corruption": kind,
                        "original": fact["text"],
                    }
                )
                break

    # A corruption can fail to find a fact it applies to - a figure swap needs
    # a number - so top up with whatever does apply rather than shipping a
    # lopsided set, which would change what the contest measures.
    for fact in pool:
        if len(items) >= size:
            break
        if fact["fact_id"] in used:
            continue
        for kind in CORRUPTIONS:
            corrupted = makers[kind](fact["text"])
            if corrupted and corrupted != fact["text"]:
                used.add(fact["fact_id"])
                items.append(
                    {
                        "item_id": f"F{len(items) + 1}",
                        "source_id": fact["source_id"],
                        "statement": corrupted,
                        "label": "unsupported",
                        "corruption": kind,
                        "original": fact["text"],
                    }
                )
                break

    rng.shuffle(items)
    return items


def cohens_kappa(truth: list[str], predicted: list[str]) -> float:
    """Agreement above chance, which is the only agreement worth reporting.

    Raw agreement flatters a judge by roughly 38 points on a balanced set
    (arXiv 2606.19544), because guessing one label constantly scores 50%.

    Args:
        truth: Ground-truth labels.
        predicted: A judge's labels, same order.

    Returns:
        Cohen's kappa, -1.0 to 1.0.
    """
    if not truth or len(truth) != len(predicted):
        return 0.0

    n = len(truth)
    observed = sum(1 for t, p in zip(truth, predicted, strict=False) if t == p) / n

    labels = set(truth) | set(predicted)
    expected = sum(
        (truth.count(label) / n) * (predicted.count(label) / n) for label in labels
    )
    if expected >= 1.0:
        return 0.0
    return (observed - expected) / (1 - expected)
