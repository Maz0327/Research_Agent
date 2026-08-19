"""Deterministic text-similarity primitives.

Three pipeline decisions used to be made by a model, or not made at all:
whether two sources are the same syndicated article, whether two key points
say the same thing, and whether two theme statements are restatements. Those
are matching problems, and code answers them reproducibly. Models write
content; code decides identity.

Measured on the films corpus (2026-08-16): 8-word shingle overlap put SRC_7
and SRC_8 at 89% - a syndicated duplicate that had been silently inflating
corroboration counts. Embeddings were tried on the same corpus and rejected:
they rank restatements, not connections.
"""

import re
from collections.abc import Iterable

# Words carrying no discriminating power when comparing two statements
_STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those of in on at to for from by with
    about into over after before between out against during without within along across
    is are was were be been being am do does did doing have has had having will would can
    could should may might must shall it its it's as not no nor so such there their them
    they he she his her him we us our you your i me my
    """.split()  # noqa: SIM905 - a readable word list, not a literal to maintain by hand
)


_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
_NUMBER_PATTERN = re.compile(r"\b\d[\d,.]*\b")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens.

    Args:
        text: Any text.

    Returns:
        List of tokens in order, punctuation dropped.
    """
    return _TOKEN_PATTERN.findall(text.lower())


def content_tokens(text: str) -> set[str]:
    """Tokens that carry meaning, with stopwords removed.

    Args:
        text: Any text.

    Returns:
        Set of content tokens.
    """
    return {t for t in tokenize(text) if t not in _STOPWORDS and len(t) > 1}


def numbers_in(text: str) -> set[str]:
    """Numeric tokens in a text, normalized.

    Numbers are the sharpest discriminator between two similar-sounding
    statements: "1,200 workers" and "12,000 workers" share every other word.

    Args:
        text: Any text.

    Returns:
        Set of normalized number strings (commas stripped, trailing dots removed).
    """
    return {m.replace(",", "").rstrip(".") for m in _NUMBER_PATTERN.findall(text)}


def shingles(text: str, size: int = 8) -> set[str]:
    """Overlapping word n-grams, the unit of duplicate detection.

    Args:
        text: Any text.
        size: Words per shingle. 8 is the measured setting for catching
            syndicated copies without matching shared boilerplate.

    Returns:
        Set of shingles. Empty when the text is shorter than one shingle.
    """
    tokens = tokenize(text)
    if len(tokens) < size:
        return set()
    return {" ".join(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def shingle_overlap(text_a: str, text_b: str, size: int = 8) -> float:
    """How much of the shorter text appears verbatim in the longer one.

    Containment, not Jaccard: a syndicated copy is often trimmed or has a
    different intro, which Jaccard punishes and containment does not.

    Args:
        text_a: First text.
        text_b: Second text.
        size: Words per shingle.

    Returns:
        0.0 to 1.0. Returns 0.0 when either text is too short to shingle.
    """
    a = shingles(text_a, size)
    b = shingles(text_b, size)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def statement_similarity(text_a: str, text_b: str) -> float:
    """How much of the shorter statement's meaning appears in the longer one.

    Containment over content words, not Jaccard. Two sources rarely make the
    same point at the same length, and Jaccard reads that length difference as
    disagreement: on the films corpus the genuine SRC_7/SRC_8 match scored 0.47
    by Jaccard and 0.69 by containment. Sentence-length text is too short to
    shingle, so the duplicate detector's instrument does not apply here.

    Args:
        text_a: First statement.
        text_b: Second statement.

    Returns:
        0.0 to 1.0. Returns 0.0 when either statement has no content words.
    """
    a = content_tokens(text_a)
    b = content_tokens(text_b)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


# Below this many content words, containment matches on almost anything
_MIN_COMPARABLE_TOKENS = 4

# Calibrated on the films corpus (689 cross-source pairs, 2026-08-19): median
# containment 0.045, only three pairs at or above 0.50 and all of them the
# known SRC_7/SRC_8 syndication. 0.60 keeps the true match and drops the one
# false pair that sat at 0.50.
SAME_STATEMENT_THRESHOLD = 0.60


def says_the_same_thing(
    text_a: str,
    text_b: str,
    threshold: float = SAME_STATEMENT_THRESHOLD,
) -> bool:
    """Decide whether two statements assert the same thing.

    Conservative by design: a false match invents corroboration, and a
    fabricated "two sources agree" is a worse failure than reporting a
    corroborated fact as single-source. Any number in one statement must appear
    in the other, so "1,200 chambers" never corroborates "12,000 chambers".

    Honest limit: two sources making the same point in genuinely different
    words score below any safe threshold, so paraphrase-level agreement is
    under-counted on purpose. The Files and Disputed sections put near-matches
    in front of a reader rather than resolving them here.

    Args:
        text_a: First statement.
        text_b: Second statement.
        threshold: Minimum content-word containment.

    Returns:
        True when the two statements assert the same thing.
    """
    if (
        len(content_tokens(text_a)) < _MIN_COMPARABLE_TOKENS
        or len(content_tokens(text_b)) < _MIN_COMPARABLE_TOKENS
    ):
        return False

    numbers_a = numbers_in(text_a)
    numbers_b = numbers_in(text_b)
    if numbers_a and numbers_b and not (numbers_a & numbers_b):
        return False
    if bool(numbers_a) != bool(numbers_b):
        # One cites a figure and the other does not: they are not the same claim.
        return False

    return statement_similarity(text_a, text_b) >= threshold


def group_matching(
    items: Iterable[tuple[str, str]],
    threshold: float = SAME_STATEMENT_THRESHOLD,
) -> dict[str, str]:
    """Group statements that say the same thing.

    Single-link clustering by `says_the_same_thing`. Groups are labelled by the
    id of their first member, so grouping is stable for a given input order.

    Args:
        items: Pairs of (id, statement).
        threshold: Passed through to `says_the_same_thing`.

    Returns:
        Dict mapping every id to its group id.
    """
    group_of: dict[str, str] = {}
    members: dict[str, list[tuple[str, str]]] = {}

    for item_id, statement in items:
        for group_id, group_members in members.items():
            if any(
                says_the_same_thing(statement, other, threshold)
                for _, other in group_members
            ):
                group_of[item_id] = group_id
                group_members.append((item_id, statement))
                break
        else:
            group_of[item_id] = item_id
            members[item_id] = [(item_id, statement)]

    return group_of
