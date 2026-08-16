"""Style enforcement for human-readable research output.

Runs after LLM generates text, before text enters document assembly.
Returns violations list. Empty list = text passes.

No external dependencies required. textstat is optional for readability scoring.
"""

import re
from dataclasses import dataclass, field

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


# -----------------------------------------------------------------------------
# Tic-lint for rendered documents (EXECUTION-PLAN P2.3)
#
# These are the tells that make a document read as machine output. They are
# enforceable, not aspirational: a rendered document that trips one of these
# fails its render test rather than shipping.
# -----------------------------------------------------------------------------

# Internal IDs must never appear in a document body. Rendering uses source
# names and plain evidence-status language instead.
_INTERNAL_ID_PATTERN = re.compile(r"\b(CLM|SRC|KP|TEN|GAP|STG|HOLE|QT|OBS|THEME)_\d+\b")

TIC_PATTERNS: list[tuple[str, str]] = [
    (r"—", "em-dash (use a comma, a full stop, or a new sentence)"),
    (r"\bdelve\b", "delve"),
    (r"\btapestry\b", "tapestry"),
    (r"\btestament\b", "testament"),
    (r"\bthe .{0,20}landscape\b", "landscape used as metaphor"),
    (r"\bnot just .{1,60}?,? (it'?s|but)\b", "'not just X, it's Y' construction"),
    (r"\bas extracted\b", "'As extracted'"),
    (r"\bgoverning insight\b", "'Governing Insight'"),
    (r"\bsemantic\b", "'Semantic' (internal vocabulary)"),
    (r"\bit is worth noting\b", "'it is worth noting'"),
    (r"\ba recurring pattern\b", "'a recurring pattern'"),
]

# Rule-of-three adjective stacks used for rhythm. Deliberately narrow: three
# comma-separated single words immediately before a noun. A genuine
# enumeration of multi-word items is not this and must not be flagged.
_RULE_OF_THREE_PATTERN = re.compile(
    r"\b([a-z]{3,}), ([a-z]{3,}),? and ([a-z]{3,})\b(?= [a-z]+)",
    re.IGNORECASE,
)


def check_internal_ids(text: str) -> list[str]:
    """Flag internal IDs leaking into rendered prose."""
    found = sorted({f"{prefix}_" for prefix in _INTERNAL_ID_PATTERN.findall(text)})
    if not found:
        return []
    return [f"Internal ID in document body: {', '.join(found)}"]


def check_tics(text: str) -> list[str]:
    """Flag the banned constructions from the voice laws."""
    violations = []
    for pattern, label in TIC_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Voice law violation: {label}")
    return violations


def check_rule_of_three(text: str) -> list[str]:
    """Flag three-word adjective stacks used for rhythm."""
    matches = _RULE_OF_THREE_PATTERN.findall(text)
    if not matches:
        return []
    sample = ", ".join(" ".join(m) for m in matches[:2])
    return [f"Rule-of-three stack ({len(matches)}): {sample}"]


@dataclass
class LintResult:
    """Outcome of the tic-lint.

    Errors and advisories are separated because they carry different
    certainty. An em-dash or a leaked ID is unambiguous and blocks the render.
    Rule-of-three detection cannot tell an adjective stack from an honest
    enumeration without a part-of-speech tagger, so it reports rather than
    blocks. Failing a document over "workload, deadlines, and creative
    constraints" would train everyone to ignore the lint.
    """

    errors: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)

    @property
    def passes(self) -> bool:
        return not self.errors

    @property
    def all_findings(self) -> list[str]:
        return self.errors + [f"advisory: {a}" for a in self.advisories]


def lint_rendered_document(text: str) -> LintResult:
    """Run the tic-lint over a rendered document.

    This is the gate for anything a human reads. Separate from enforce_style,
    which runs on LLM output mid-pipeline and whose sentence-length and
    passive-voice checks are advisory by nature.

    Args:
        text: The rendered markdown document.

    Returns:
        LintResult. ``passes`` is False only when there are hard errors.
    """
    result = LintResult(
        errors=check_internal_ids(text) + check_tics(text),
        advisories=check_rule_of_three(text),
    )

    if result.errors:
        logger.warning(f"Tic-lint: {len(result.errors)} errors in rendered document")
    if result.advisories:
        logger.info(f"Tic-lint: {len(result.advisories)} advisories")

    return result


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
