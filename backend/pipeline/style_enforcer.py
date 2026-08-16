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

# The vocabulary of research writing. These describe how the information was
# obtained, which the reader does not care about, and they are what makes a
# document read as an essay rather than as a person talking. Owner feedback at
# the P2 gate, 2026-08-15: "words like corpus, that doesn't make sense... more
# like a person telling a person, not a research essay".
RESEARCH_REGISTER: list[tuple[str, str]] = [
    (r"\bcorpus\b", "corpus"),
    (r"\bthe literature\b", "the literature"),
    (r"\bprimary (source|testimony|documentation)\b", "primary source/testimony"),
    # Bare "testimony" is deliberately NOT banned: on a court or inquiry topic
    # it is the subject matter, not the register. "primary testimony" above is
    # the research-writing form and stays an error.
    (r"\bposits\b", "posits"),
    (r"\barticulates\b", "articulates"),
    (r"\bconstitutes\b", "constitutes"),
    (r"\bunderscores\b", "underscores"),
    (r"\bcorroborat(e|es|ed|ing|ion)\b", "corroborates"),
    (r"\bwarrants further\b", "warrants further investigation"),
    (r"\blacks? primary\b", "lacks primary documentation"),
    (r"\bthis (paper|study|analysis) \b", "this paper/study/analysis"),
]

TIC_PATTERNS: list[tuple[str, str]] = [
    (r"—", "em-dash (use a comma, a full stop, or a new sentence)"),
    (r"\bdelve\b", "delve"),
    (r"\btapestry\b", "tapestry"),
    (r"\btestament\b", "testament"),
    (r"\bthe .{0,20}landscape\b", "landscape used as metaphor"),
    # The banned shape is the rhetorical "not just X, it's Y", where the comma
    # runs straight into "it's". An earlier, looser pattern also flagged
    # "not just a feeling, and it's the one place...", which is an ordinary
    # qualifier followed by a new clause and perfectly fine.
    (r"\bnot just .{1,60}?,['\"’]? (it'?s|it is)\b", "'not just X, it's Y' construction"),
    (r"\bnot just [^,.;]{1,60} but\b", "'not just X but Y' construction"),
    (r"\bas extracted\b", "'As extracted'"),
    (r"\bgoverning insight\b", "'Governing Insight'"),
    (r"\bsemantic\b", "'Semantic' (internal vocabulary)"),
    (r"\bit is worth noting\b", "'it is worth noting'"),
    (r"\ba recurring pattern\b", "'a recurring pattern'"),
    # Cross-references (Decision 024). The reader must never have to decode a
    # label or scroll to understand the sentence they are on. Owner stopped
    # reading at "Thread 4 sits underneath threads 2 and 3".
    (r"\bthreads? \d", "numbered thread reference"),
    (r"\bsections? \d", "numbered section reference"),
    (r"\b(see|mentioned|noted|discussed|described) (above|below|earlier|previously)\b",
     "cross-reference (say it again in place instead)"),
    (r"\bthe (previous|next|following|preceding) section\b",
     "cross-reference to another section"),
    (r"\bas (we|I) (said|mentioned|noted)\b", "cross-reference (re-say it in place)"),
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


# A sentence that OPENS with a source reference is narrating the bibliography
# instead of explaining the subject. Owner rejection, 2026-08-16: "the entire
# thing is 'one source says this, one source says that' — it needs to be
# written like a person is explaining it to me." A trailing aside ("...though
# that's one essay's argument") does not match this pattern and stays legal.
_SOURCE_OPENER = re.compile(
    r"(?:^|[.!?]\s+|\n)"
    r"(?:One|A|Another|A second|A third|A fourth|A different, |A separate |Two|"
    r"Three|Four|Both|Several|Multiple|Many|Most|Each|Neither|Every)"
    r"[a-z ,]{0,25}?"
    r"(?:sources?|essays?|articles?|videos?|essayists?|writers?|commentators?|"
    r"threads?|pieces?)\b",
    re.IGNORECASE,
)

# Consensus narration: prose about the fact THAT sources agree, rather than
# about what they actually say. Owner rejection, 2026-08-16: "the first 3
# paragraphs is just you telling me a lot of people came to the same
# conclusion... what you're not telling me is what the actual conclusion IS."
# Meta earns a trailing clause after content, not paragraphs of its own, so
# this is a density cap rather than a ban.
_CONSENSUS_NARRATION = re.compile(
    r"(?:independen(?:t|tly)|without (?:citing|referencing|talking to|reference to) "
    r"(?:each other|one another)|(?:came?|land(?:s|ed)?|arriv(?:e|es|ed)) (?:at|on|to) "
    r"the same|same (?:conclusion|complaint|observation|point|place|culprit|mechanism)"
    r"|across (?:all|every|the) (?:sources?|material)|all agree)",
    re.IGNORECASE,
)

# Neither raw phrase density (rejected doc 3.6/1000 vs approved 3.5/1000)
# nor pure-meta sentence density (2.1 vs 1.9) separates good from bad -
# measured on real documents, the ranges overlap. What separates them is
# POSITION. The owner-approved register allows a SHORT agreement sentence
# trailing a point that was already made ("Two essayists independently
# reject this."). What he rejected is agreement talk LEADING a paragraph, or
# stacked in runs. So a violation is a pure-meta sentence that either opens
# a paragraph or sits adjacent to another pure-meta sentence.
MAX_META_VIOLATIONS = 2

_META_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _is_pure_meta(sentence: str) -> bool:
    """A sentence about agreement that states none of the agreed content."""
    if not _CONSENSUS_NARRATION.search(sentence):
        return False
    has_content = bool(re.search(r"\d", sentence)) or bool(
        re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+", sentence)
    )
    return not has_content


def find_consensus_violations(text: str) -> list[str]:
    """Return pure-meta sentences that lead a paragraph or run in clusters.

    A single short pure-meta sentence trailing content is the approved
    register and is not returned.
    """
    violations: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph or paragraph.startswith("#"):
            continue
        sentences = [
            s.strip() for s in _META_SENTENCE_SPLIT.split(paragraph) if len(s.strip()) > 15
        ]
        flags = [_is_pure_meta(s) for s in sentences]
        for i, (sentence, is_meta) in enumerate(zip(sentences, flags)):
            if not is_meta:
                continue
            leads = i == 0
            clustered = (i > 0 and flags[i - 1]) or (i + 1 < len(flags) and flags[i + 1])
            if leads or clustered:
                violations.append(sentence)
    return violations


def check_consensus_narration(text: str) -> list[str]:
    """Flag documents that narrate agreement instead of content."""
    if len(text.split()) < 200:
        return []
    violations = find_consensus_violations(text)
    if len(violations) <= MAX_META_VIOLATIONS:
        return []
    return [
        f"Consensus-narration: {len(violations)} agreement-only sentences "
        f"leading paragraphs or stacked in runs (max {MAX_META_VIOLATIONS}). "
        f"e.g. '{violations[0][:80]}'. State what is actually said first; "
        f"agreement earns one short trailing sentence at most."
    ]


# Allowed sentence-initial source references per 1000 words. Calibrated
# against the failed fixture run (8.9 per 1000 — rejected) and the approved
# mockup (~2 per 1000). The occasional deliberate opener survives; using
# sourcing as the skeleton does not.
MAX_SOURCE_OPENERS_PER_1000_WORDS = 3.0


def check_source_narration(text: str) -> list[str]:
    """Flag documents that narrate their sourcing instead of their subject."""
    words = len(text.split())
    if words < 200:
        return []

    hits = _SOURCE_OPENER.findall(text)
    density = len(hits) / (words / 1000)
    if density <= MAX_SOURCE_OPENERS_PER_1000_WORDS:
        return []

    return [
        f"Source-narration: {len(hits)} sentences open with a source reference "
        f"({density:.1f} per 1000 words, max {MAX_SOURCE_OPENERS_PER_1000_WORDS:.0f}). "
        f"Explain the subject; flag sourcing as a short aside at the end of a "
        f"point instead."
    ]


def check_research_register(text: str) -> list[str]:
    """Flag research-essay vocabulary in a document meant to sound spoken."""
    violations = []
    for pattern, label in RESEARCH_REGISTER:
        hits = re.findall(pattern, text, re.IGNORECASE)
        if hits:
            violations.append(
                f"Research-essay word ({len(hits)}x): '{label}'. Say it the way "
                f"you would out loud instead."
            )
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
        errors=check_internal_ids(text)
        + check_tics(text)
        + check_research_register(text)
        + check_source_narration(text)
        + check_consensus_narration(text),
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
