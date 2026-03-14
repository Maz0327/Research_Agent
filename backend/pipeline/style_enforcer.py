"""Style enforcement for human-readable research output.

Runs after LLM generates text, before text enters document assembly.
Returns violations list. Empty list = text passes.

No external dependencies required. textstat is optional for readability scoring.
"""

import re

from loguru import logger


# Banned phrases — academic/robotic patterns that should never appear
BANNED_PATTERNS: list[tuple[str, str]] = [
    (r"\brecurring pattern (identified|observed|noted)\b", "recurring pattern identified"),
    (r"\bthe source (outlines|argues|posits|suggests|presents)\b", "the source outlines/argues"),
    (r"\b(an|the) (analysis|exploration|examination) of\b", "an analysis/exploration of"),
    (r"\bis (argued|said|perceived|presented) (to|as)\b", "is argued/said to"),
    (r"\bcorpus\b", "corpus"),
    (r"\bcinematic output\b", "cinematic output"),
    (r"\bfurthermore\b", "furthermore"),
    (r"\badditionally\b", "additionally"),
    (r"\bin contrast\b", "in contrast"),
    (r"\bmoreover\b", "moreover"),
    (r"\bthe aforementioned\b", "the aforementioned"),
    (r"\bparadigm\b", "paradigm"),
    (r"\bpraxis\b", "praxis"),
    (r"\bphenomenology\b", "phenomenology"),
    (r"\bhaptic visuality\b", "haptic visuality"),
    (r"\bthis topic centers on\b", "this topic centers on"),
    (r"\bit could be argued\b", "it could be argued"),
    (r"\bconsequently\b", "consequently"),
]

# Maximum words per sentence before flagging
MAX_SENTENCE_WORDS = 35

# Maximum passive voice instances before flagging
MAX_PASSIVE_VOICE = 5

# Passive voice detection pattern: auxiliary + past participle
_PASSIVE_PATTERN = re.compile(
    r"\b(is|are|was|were|been|being)\s+(\w+ed|known|shown|seen|found|made|given|taken)\b",
    re.IGNORECASE,
)


def check_banned_phrases(text: str) -> list[str]:
    """Check for banned academic phrases.

    Args:
        text: Text to check.

    Returns:
        List of violation descriptions. Empty if clean.
    """
    violations = []
    for pattern, label in BANNED_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            violations.append(f"Banned phrase detected: '{label}'")
    return violations


def check_sentence_lengths(text: str) -> list[str]:
    """Check for sentences over MAX_SENTENCE_WORDS words.

    Uses simple period/question/exclamation split. No spaCy needed.

    Args:
        text: Text to check.

    Returns:
        List of violation descriptions. Empty if clean.
    """
    violations = []
    # Split on sentence-ending punctuation followed by space or end
    sentences = re.split(r'[.!?]+(?:\s|$)', text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        words = sent.split()
        if len(words) > MAX_SENTENCE_WORDS:
            preview = " ".join(words[:10]) + "..."
            violations.append(
                f"Sentence too long ({len(words)} words, max {MAX_SENTENCE_WORDS}): '{preview}'"
            )
    return violations


def check_passive_voice_simple(text: str) -> list[str]:
    """Simple regex-based passive voice detection.

    Only flags if pervasive (more than MAX_PASSIVE_VOICE instances).

    Args:
        text: Text to check.

    Returns:
        List with single violation if pervasive, empty otherwise.
    """
    matches = _PASSIVE_PATTERN.findall(text)
    if len(matches) > MAX_PASSIVE_VOICE:
        return [f"Excessive passive voice ({len(matches)} instances, max {MAX_PASSIVE_VOICE})"]
    return []


def check_readability(text: str) -> str | None:
    """Check Flesch-Kincaid grade level. Target: grade 12 or below.

    Uses textstat if installed, otherwise skips silently.

    Args:
        text: Text to check.

    Returns:
        Violation string if grade too high, None if passes or textstat unavailable.
    """
    try:
        import textstat
        grade = textstat.flesch_kincaid_grade(text)
        if grade > 14:
            return f"Reading level too high: grade {grade:.1f} (target: ≤12)"
    except ImportError:
        pass  # textstat not installed — skip check
    except Exception:
        pass  # Any other error — skip gracefully
    return None


def enforce_style(text: str) -> tuple[bool, list[str]]:
    """Run all style checks on text.

    Args:
        text: Text to validate.

    Returns:
        Tuple of (passes, violations). passes=True if no violations found.
    """
    if not text or len(text.strip()) < 50:
        return True, []  # Too short to meaningfully check

    violations: list[str] = []
    violations += check_banned_phrases(text)
    violations += check_sentence_lengths(text)
    violations += check_passive_voice_simple(text)

    readability = check_readability(text)
    if readability:
        violations.append(readability)

    passes = len(violations) == 0

    if not passes:
        logger.debug(f"Style enforcement: {len(violations)} violations found")

    return passes, violations
