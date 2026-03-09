"""Output Quality Enforcement — Code-level anti-generic validation.

R17: Anti-repetition, anti-hedge, source-grounding, circular-logic detection.
Runs on LLM-generated text to catch generic output BEFORE it reaches the user.

This module enforces quality via CODE, not prompt instructions alone.
The LLM is told the rules; this module verifies compliance.
"""

import re
from dataclasses import dataclass, field


# =============================================================================
# BANNED PHRASES — Generic AI filler that adds no value
# =============================================================================

HEDGE_PHRASES: list[str] = [
    "it's important to note",
    "it's worth noting",
    "it should be noted",
    "it is important to note",
    "it is worth noting",
    "it is worth mentioning",
    "interestingly enough",
    "interestingly",
    "notably",
    "it depends",
    "various factors",
    "a number of",
    "it's clear that",
    "it is clear that",
    "needless to say",
    "as we can see",
    "moving forward",
    "at the end of the day",
    "in today's world",
    "it goes without saying",
    "first and foremost",
    "last but not least",
    "in conclusion",
    "to summarize",
    "as previously mentioned",
    "it remains to be seen",
    "only time will tell",
    "the fact of the matter",
    "in terms of",
    "when it comes to",
    "plays a crucial role",
    "is a key factor",
    "is a game changer",
    "paradigm shift",
    "holistic approach",
    "leverage synergies",
    "deep dive into",
    "unpack this",
    "at its core",
    "the landscape of",
    "navigate the complexities",
    "shed light on",
    "raises important questions",
    "a nuanced understanding",
    "multifaceted",
    "myriad of",
    "a plethora of",
    "delve into",
    "delves into",
    "tapestry of",
    "rich tapestry",
    # Additional AI-generated filler
    "it's essential to",
    "it is essential to",
    "this highlights the importance",
    "underscores the need",
    "speaks to the broader",
    "serves as a reminder",
    "remains a critical",
    "cannot be overstated",
    "it bears mentioning",
    "one could argue",
    "it stands to reason",
    "the bottom line is",
    "in a nutshell",
    "by and large",
    "all things considered",
]

# Compiled regex patterns for efficient matching
_HEDGE_PATTERNS: list[re.Pattern] = [
    re.compile(re.escape(phrase), re.IGNORECASE) for phrase in HEDGE_PHRASES
]


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================


def detect_repetitive_sentence_starts(text: str) -> list[str]:
    """Detect when 2+ consecutive sentences start with the same word.

    Returns list of warning strings for each violation found.
    """
    if not text or not text.strip():
        return []

    # Split into sentences (handle common abbreviations)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    if len(sentences) < 2:
        return []

    warnings = []
    for i in range(1, len(sentences)):
        word_prev = sentences[i - 1].split()[0].lower().rstrip(".,;:") if sentences[i - 1].split() else ""
        word_curr = sentences[i].split()[0].lower().rstrip(".,;:") if sentences[i].split() else ""

        if word_prev and word_curr and word_prev == word_curr:
            # Skip common acceptable starters like "The"
            if word_prev not in ("the", "a", "an", "if", "when"):
                warnings.append(
                    f"Consecutive sentences start with '{word_curr}': "
                    f"'{sentences[i - 1][:50]}...' and '{sentences[i][:50]}...'"
                )

    return warnings


def detect_hedge_phrases(text: str) -> list[tuple[str, int]]:
    """Detect banned hedge/filler phrases in text.

    Returns list of (phrase, char_position) tuples for each match.
    """
    if not text:
        return []

    matches = []
    for pattern in _HEDGE_PATTERNS:
        for match in pattern.finditer(text):
            matches.append((match.group(), match.start()))

    # Sort by position
    matches.sort(key=lambda x: x[1])
    return matches


def detect_ungrounded_claims(text: str, source_ids: list[str]) -> list[str]:
    """Detect factual-sounding claims without source attribution nearby.

    Checks if statements containing specific numbers, dates, or proper nouns
    have a source reference (SRC_1, Source 1, etc.) within the same paragraph.

    Returns list of ungrounded claim descriptions.
    """
    if not text or not source_ids:
        return []

    # Split into paragraphs
    paragraphs = text.split("\n\n")
    ungrounded = []

    # Pattern for factual-sounding content (numbers, dates, percentages, proper nouns)
    factual_pattern = re.compile(
        r'(?:'
        r'\b\d{4}\b'                    # Years (2020, 1995, etc.)
        r'|\b\d+(?:\.\d+)?%'            # Percentages
        r'|\$\d+'                        # Dollar amounts
        r'|\b\d+(?:,\d{3})+\b'          # Large numbers with commas
        r'|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+'  # Dates
        r')',
        re.IGNORECASE,
    )

    # Build source reference patterns
    source_ref_patterns = []
    for sid in source_ids:
        # Match both "SRC_1" and "Source 1" formats
        source_ref_patterns.append(re.escape(sid))
        match = re.match(r"^([A-Z]+)_(\d+)$", sid)
        if match:
            prefix, number = match.groups()
            if prefix == "SRC":
                source_ref_patterns.append(rf"Source\s+{number}")

    source_pattern = re.compile("|".join(source_ref_patterns), re.IGNORECASE) if source_ref_patterns else None

    # Pattern for detecting hallucinated source IDs (SRC_N, Source N)
    all_src_refs_pattern = re.compile(r'\bSRC_(\d+)\b', re.IGNORECASE)
    source_ids_set = set(source_ids)

    for para in paragraphs:
        if not para.strip():
            continue

        # Anti-hallucination: Check for references to non-existent source IDs
        found_refs = all_src_refs_pattern.findall(para)
        for ref_num in found_refs:
            ref_id = f"SRC_{ref_num}"
            if ref_id not in source_ids_set:
                ungrounded.append(
                    f"Reference to non-existent source {ref_id}: "
                    f"'{para.strip()[:80]}...'"
                )

        # Check if paragraph has factual claims
        factual_matches = factual_pattern.findall(para)
        if not factual_matches:
            continue

        # Check if paragraph has source references
        has_source_ref = bool(source_pattern and source_pattern.search(para))

        if not has_source_ref and factual_matches:
            # Truncate paragraph for the warning
            para_preview = para.strip()[:80]
            ungrounded.append(
                f"Factual claim ({', '.join(factual_matches[:3])}) without source reference: "
                f"'{para_preview}...'"
            )

    return ungrounded


def detect_circular_logic(text: str) -> list[str]:
    """Detect when the same concept is restated 3+ times in different words.

    Uses word overlap heuristic (Jaccard similarity > 0.6 between sentences
    in the same paragraph) to detect circular reasoning.

    Returns list of suspected circular passages.
    """
    if not text:
        return []

    # Split into paragraphs, then sentences
    paragraphs = text.split("\n\n")
    warnings = []

    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', para.strip())
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]

        if len(sentences) < 3:
            continue

        # Compute pairwise Jaccard similarity
        def word_set(s: str) -> set[str]:
            # Remove common stop words for better signal
            stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                    "being", "have", "has", "had", "do", "does", "did", "will",
                    "would", "could", "should", "may", "might", "shall", "can",
                    "to", "of", "in", "for", "on", "with", "at", "by", "from",
                    "and", "or", "but", "not", "no", "this", "that", "it", "its"}
            words = set(re.findall(r'\b\w{3,}\b', s.lower()))
            return words - stop

        similar_groups = 0
        for i in range(len(sentences)):
            similar_to_i = 0
            words_i = word_set(sentences[i])
            if len(words_i) < 3:
                continue
            for j in range(len(sentences)):
                if i == j:
                    continue
                words_j = word_set(sentences[j])
                if len(words_j) < 3:
                    continue
                intersection = words_i & words_j
                union = words_i | words_j
                jaccard = len(intersection) / len(union) if union else 0
                if jaccard > 0.55:
                    similar_to_i += 1
            if similar_to_i >= 2:
                similar_groups += 1

        if similar_groups >= 1:
            para_preview = para.strip()[:100]
            warnings.append(
                f"Possible circular reasoning ({similar_groups} concepts restated): "
                f"'{para_preview}...'"
            )

    return warnings


# =============================================================================
# QUALITY REPORT
# =============================================================================


@dataclass
class OutputQualityReport:
    """Results of output quality validation."""
    warnings: list[str] = field(default_factory=list)
    hedge_phrases_found: list[tuple[str, int]] = field(default_factory=list)
    repetitive_starts: list[str] = field(default_factory=list)
    ungrounded_claims: list[str] = field(default_factory=list)
    circular_passages: list[str] = field(default_factory=list)

    @property
    def hedge_count(self) -> int:
        return len(self.hedge_phrases_found)

    @property
    def ungrounded_count(self) -> int:
        return len(self.ungrounded_claims)

    @property
    def repetition_count(self) -> int:
        return len(self.repetitive_starts)

    @property
    def circular_count(self) -> int:
        return len(self.circular_passages)

    @property
    def total_issues(self) -> int:
        return self.hedge_count + self.ungrounded_count + self.repetition_count + self.circular_count

    @property
    def overall_quality_score(self) -> int:
        """Score from 0-100. Starts at 100, deducts for each issue type."""
        score = 100
        score -= self.hedge_count * 5          # -5 per hedge phrase
        score -= self.ungrounded_count * 10    # -10 per ungrounded claim
        score -= self.repetition_count * 8     # -8 per repetitive start
        score -= self.circular_count * 15      # -15 per circular passage
        return max(0, min(100, score))

    def to_dict(self) -> dict:
        return {
            "hedge_count": self.hedge_count,
            "ungrounded_count": self.ungrounded_count,
            "repetition_count": self.repetition_count,
            "circular_count": self.circular_count,
            "total_issues": self.total_issues,
            "overall_quality_score": self.overall_quality_score,
            "warnings": self.warnings,
        }


# =============================================================================
# MAIN VALIDATION FUNCTIONS
# =============================================================================


class OutputQualityError(Exception):
    """Raised when output quality fails strict validation."""
    def __init__(self, report: OutputQualityReport):
        self.report = report
        super().__init__(
            f"Output quality score {report.overall_quality_score}/100 "
            f"({report.total_issues} issues found)"
        )


def validate_output_quality(
    text: str,
    source_ids: list[str] | None = None,
) -> OutputQualityReport:
    """Run all quality checks on text and return report.

    Args:
        text: The LLM-generated text to validate.
        source_ids: List of valid source IDs for grounding checks.

    Returns:
        OutputQualityReport with all findings.
    """
    if not text:
        return OutputQualityReport()

    source_ids = source_ids or []

    report = OutputQualityReport()

    # Check 1: Repetitive sentence starts
    report.repetitive_starts = detect_repetitive_sentence_starts(text)
    if report.repetitive_starts:
        report.warnings.extend(
            f"[REPETITION] {w}" for w in report.repetitive_starts
        )

    # Check 2: Hedge phrases
    report.hedge_phrases_found = detect_hedge_phrases(text)
    if report.hedge_phrases_found:
        phrases = [p for p, _ in report.hedge_phrases_found]
        report.warnings.append(
            f"[HEDGE] Found {len(phrases)} hedge/filler phrases: {', '.join(set(phrases))}"
        )

    # Check 3: Ungrounded claims (only if source_ids provided)
    if source_ids:
        report.ungrounded_claims = detect_ungrounded_claims(text, source_ids)
        if report.ungrounded_claims:
            report.warnings.extend(
                f"[UNGROUNDED] {w}" for w in report.ungrounded_claims
            )

    # Check 4: Circular logic
    report.circular_passages = detect_circular_logic(text)
    if report.circular_passages:
        report.warnings.extend(
            f"[CIRCULAR] {w}" for w in report.circular_passages
        )

    return report


def enforce_output_quality(
    text: str,
    source_ids: list[str] | None = None,
    strict: bool = False,
    min_score: int = 30,
) -> tuple[str, list[str]]:
    """Validate output quality and optionally enforce minimum score.

    Args:
        text: The LLM-generated text to validate.
        source_ids: List of valid source IDs for grounding checks.
        strict: If True, raises OutputQualityError for critical violations.
        min_score: Minimum acceptable quality score (only enforced if strict=True).

    Returns:
        Tuple of (original_text, list_of_warnings).

    Raises:
        OutputQualityError: If strict=True and quality score < min_score.
    """
    report = validate_output_quality(text, source_ids)

    if strict and report.overall_quality_score < min_score:
        raise OutputQualityError(report)

    return text, report.warnings
