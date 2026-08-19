"""Statistical style signals, and a single score to trend them with.

Phrase lists catch the tics we already know about. They cannot see the tell
that has no vocabulary: sentences that are all the same length. Enumerate-and-
march writing - the essay that walks through point one, point two, point three
in identical sentence shapes - is invisible to a phrase matcher and obvious to
a variance measure.

Everything here is advisory. The score exists to answer questions the lint
cannot: did this repair round actually improve anything, and is this writer
model better than that one. Never a gate by itself (work order H20).
"""

import re
import statistics
from dataclasses import dataclass, field

# Transitions a person uses occasionally and a model uses structurally
_TRANSITIONS = (
    "however",
    "moreover",
    "furthermore",
    "additionally",
    "consequently",
    "therefore",
    "thus",
    "in addition",
    "in contrast",
    "on the other hand",
    "that said",
    "as a result",
    "importantly",
    "notably",
    "ultimately",
    "crucially",
)

_PASSIVE = re.compile(
    r"\b(is|are|was|were|been|being)\s+(\w+ed|known|shown|seen|found|made|given|taken)\b",
    re.I,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-zA-Z'’-]+")

# Human prose in this register runs a standard deviation of roughly 6-12 words
# per sentence. Below 4 the rhythm is mechanical.
LOW_VARIANCE = 4.0

# Type-token ratio over the first 1000 words; below this the vocabulary is
# recycling itself.
LOW_DIVERSITY = 0.38

# Transitions per 1000 words. A person writing at pace uses a handful.
HIGH_TRANSITION_DENSITY = 12.0

# Passive constructions per 1000 words.
HIGH_PASSIVE_RATE = 15.0


@dataclass
class StyleStats:
    """Measured properties of a document's prose."""

    words: int = 0
    sentences: int = 0
    mean_sentence_words: float = 0.0
    sentence_length_stdev: float = 0.0
    lexical_diversity: float = 0.0
    passive_per_1000: float = 0.0
    transitions_per_1000: float = 0.0
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "words": self.words,
            "sentences": self.sentences,
            "mean_sentence_words": round(self.mean_sentence_words, 2),
            "sentence_length_stdev": round(self.sentence_length_stdev, 2),
            "lexical_diversity": round(self.lexical_diversity, 3),
            "passive_per_1000": round(self.passive_per_1000, 2),
            "transitions_per_1000": round(self.transitions_per_1000, 2),
            "findings": self.findings,
        }


def measure_style(text: str) -> StyleStats:
    """Measure the statistical signals a phrase list cannot see.

    Args:
        text: Document prose.

    Returns:
        StyleStats, with advisory findings for anything outside the human range.
    """
    stats = StyleStats()
    if not text or not text.strip():
        return stats

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    lengths = [len(_WORD.findall(s)) for s in sentences]
    lengths = [n for n in lengths if n]
    words = _WORD.findall(text.lower())

    stats.words = len(words)
    stats.sentences = len(lengths)
    if not words or not lengths:
        return stats

    stats.mean_sentence_words = statistics.fmean(lengths)
    stats.sentence_length_stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    sample = words[:1000]
    stats.lexical_diversity = len(set(sample)) / len(sample)

    per_1000 = 1000 / len(words)
    stats.passive_per_1000 = len(_PASSIVE.findall(text)) * per_1000
    lowered = text.lower()
    stats.transitions_per_1000 = (
        sum(lowered.count(t) for t in _TRANSITIONS) * per_1000
    )

    if stats.sentences >= 8 and stats.sentence_length_stdev < LOW_VARIANCE:
        stats.findings.append(
            f"sentence length barely varies (stdev {stats.sentence_length_stdev:.1f} "
            f"words): the march of identical shapes"
        )
    if stats.words >= 200 and stats.lexical_diversity < LOW_DIVERSITY:
        stats.findings.append(
            f"vocabulary is recycling itself (type-token {stats.lexical_diversity:.2f})"
        )
    if stats.transitions_per_1000 > HIGH_TRANSITION_DENSITY:
        stats.findings.append(
            f"transitions are doing the structure's job "
            f"({stats.transitions_per_1000:.0f} per 1000 words)"
        )
    if stats.passive_per_1000 > HIGH_PASSIVE_RATE:
        stats.findings.append(
            f"passive voice is the default ({stats.passive_per_1000:.0f} per 1000 words)"
        )

    return stats


def slop_score(
    text: str,
    lint_errors: int = 0,
    lint_advisories: int = 0,
    stats: "StyleStats | None" = None,
) -> int:
    """Score how much a document reads as machine-written, 0 to 100.

    Higher is worse. The number has no meaning on its own; it exists to be
    compared - the same document before and after a repair round, or two
    writer models over the same brief. Never a gate (work order H20).

    Args:
        text: Document prose.
        lint_errors: Hard lint errors already found.
        lint_advisories: Advisory lint findings already found.
        stats: Pre-computed stats, if the caller has them.

    Returns:
        0-100, where 0 is a document with no measured tells.
    """
    if not text or not text.strip():
        return 0

    stats = stats or measure_style(text)
    per_1000 = 1000 / max(stats.words, 1)

    score = 0.0
    # Hard lint errors are the strongest signal we have.
    score += min(40.0, lint_errors * per_1000 * 8)
    score += min(10.0, lint_advisories * per_1000 * 3)

    if stats.sentences >= 8:
        shortfall = max(0.0, LOW_VARIANCE + 2 - stats.sentence_length_stdev)
        score += min(20.0, shortfall * 4)

    if stats.words >= 200:
        shortfall = max(0.0, LOW_DIVERSITY + 0.05 - stats.lexical_diversity)
        score += min(15.0, shortfall * 200)

    score += min(10.0, max(0.0, stats.transitions_per_1000 - 6) * 1.2)
    score += min(5.0, max(0.0, stats.passive_per_1000 - 10) * 0.4)

    return int(round(min(100.0, score)))
