"""
Semantic Units - Core data structures for semantic extraction.

Based on: docs/authoritative/spec/Operational_Definitions.md

These units represent the extracted semantic structure from sources,
following the epistemic hierarchy defined in the Research Agent specs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConfidenceLevel(str, Enum):
    """Categorical confidence levels (never numeric)."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalysisMode(str, Enum):
    """How the source was analyzed based on content availability.

    Per INDEX.md Section "Six Analysis Modes":
    - Mode determines confidence ceiling
    - Mode determines quote permissions
    - Mode is set BEFORE extraction, not during
    """
    # Video sources
    TRANSCRIPT_GROUNDED = "transcript_grounded"  # Full transcript (Supadata/Whisper)
    CAPTION_GROUNDED = "caption_grounded"  # YouTube captions used
    VIDEO_ONLY = "video_only"  # No transcript available

    # Non-video sources (per RASS 4.2)
    TEXT_PROVIDED = "text_provided"  # User-pasted content
    OCR_EXTRACTED = "ocr_extracted"  # Screenshot with OCR
    ARTICLE_FETCHED = "article_fetched"  # Article URL with full text


# -----------------------------------------------------------------------------
# QUOTE (Operational Definitions §3)
# -----------------------------------------------------------------------------

@dataclass
class Quote:
    """
    Verbatim text from Source Data.

    Properties:
    - Exact text match (or near-exact with punctuation tolerance)
    - Associated with source_id and location anchor

    Rules:
    - Quotes do NOT imply truth or importance
    - Quotes exist only to support higher-level units
    """
    quote_id: str
    text: str
    source_id: str
    timestamp: Optional[str] = None  # MM:SS or HH:MM:SS format
    paragraph_index: Optional[int] = None
    approximate: bool = False  # True for caption_grounded mode

    # Verification fields (Phase 4)
    # Set by stage_semantic_validation after verifying against source text
    verification_status: Optional[str] = None  # verified | partial | unverified
    match_ratio: Optional[float] = None  # 0.0 to 1.0 similarity score
    _verification_warning: Optional[str] = None  # Warning message if unverified

    def to_dict(self) -> dict[str, Any]:
        result = {
            "quote_id": self.quote_id,
            "text": self.text,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "paragraph_index": self.paragraph_index,
            "approximate": self.approximate,
        }
        # Include verification fields if set
        if self.verification_status is not None:
            result["verification_status"] = self.verification_status
        if self.match_ratio is not None:
            result["match_ratio"] = self.match_ratio
        if self._verification_warning is not None:
            result["_verification_warning"] = self._verification_warning
        return result


# -----------------------------------------------------------------------------
# CLAIM (Operational Definitions §4)
# -----------------------------------------------------------------------------

@dataclass
class Claim:
    """
    Declarative statement made by a source that asserts something about reality.

    Examples:
    - "The event happened in 2019."
    - "We never received funding."

    What a Claim is NOT:
    - Opinions, interpretations, or general descriptions

    Rules:
    - Claims must originate from a source
    - Claims may be false, disputed, or unverifiable
    - Claims must reference at least one supporting Quote

    Exception for video_only mode:
    - Claims not required to have supporting Quotes
    - Must reference approximate timestamp ranges
    - Must be marked confidence: low
    """
    claim_id: str
    statement: str
    source_id: str
    supporting_quotes: list[str] = field(default_factory=list)  # Quote IDs
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp_range: Optional[str] = None  # For video_only mode: "~MM:SS - MM:SS"
    source_mode: Optional[AnalysisMode] = None  # Required for video_only

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "source_id": self.source_id,
            "supporting_quotes": self.supporting_quotes,
            "confidence": self.confidence.value,
            "timestamp_range": self.timestamp_range,
            "source_mode": self.source_mode.value if self.source_mode else None,
        }


# -----------------------------------------------------------------------------
# KEY POINT (Operational Definitions §5)
# -----------------------------------------------------------------------------

@dataclass
class KeyPoint:
    """
    Semantically meaningful assertion a researcher would extract.

    Properties:
    - Derived from one or more Claims and/or Quotes
    - Expressed in neutral language
    - Represents *what is being said*, not *what it means*

    What a Key Point is NOT:
    - A summary, quote, conclusion, or narrative beat

    Rules:
    - Each Key Point must reference one or more source_ids
    - Key Points may conflict with one another
    - Key Points may be incomplete
    """
    key_point_id: str
    statement: str
    source_ids: list[str] = field(default_factory=list)
    supporting_claims: list[str] = field(default_factory=list)  # Claim IDs
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_point_id": self.key_point_id,
            "statement": self.statement,
            "source_ids": self.source_ids,
            "supporting_claims": self.supporting_claims,
            "confidence": self.confidence.value,
        }


# -----------------------------------------------------------------------------
# THEME (Operational Definitions §6)
# -----------------------------------------------------------------------------

@dataclass
class Theme:
    """
    Recurring conceptual pattern spanning multiple Key Points.

    Properties:
    - Abstracted one level above Key Points
    - Describes *what ideas recur*, not what is concluded

    Examples:
    - "Inconsistent timelines"
    - "Financial opacity"

    Rules:
    - A Theme must contain ≥2 Key Points
    - Themes must NOT assert causality or resolve ambiguity
    - Themes may overlap
    """
    theme_id: str
    label: str
    description: str
    related_key_points: list[str] = field(default_factory=list)  # KeyPoint IDs

    # Phase 5: Multi-Source Attribution
    sources_supporting: list[str] = field(default_factory=list)  # source_ids that support this theme
    is_consensus: bool = False  # True if 2+ sources agree on this theme

    def to_dict(self) -> dict[str, Any]:
        result = {
            "theme_id": self.theme_id,
            "label": self.label,
            "description": self.description,
            "related_key_points": self.related_key_points,
        }
        # Include Phase 5 fields if populated
        if self.sources_supporting:
            result["sources_supporting"] = self.sources_supporting
            result["is_consensus"] = self.is_consensus
        return result


# -----------------------------------------------------------------------------
# TENSION (Operational Definitions §7)
# -----------------------------------------------------------------------------

@dataclass
class Tension:
    """
    When two or more Key Points cannot simultaneously be true without explanation.

    Examples:
    - Two sources give conflicting dates
    - A subject contradicts earlier statements
    - Data conflicts with testimony

    Rules:
    - Tensions must cite all involved Key Points
    - The system must NOT resolve tensions unless evidence exists
    - Tensions are surfaced, not adjudicated
    """
    tension_id: str
    description: str
    involved_key_points: list[str] = field(default_factory=list)  # KeyPoint IDs

    # Phase 5: Cross-Source Attribution
    sources_position_a: list[str] = field(default_factory=list)  # source_ids supporting one side
    sources_position_b: list[str] = field(default_factory=list)  # source_ids supporting the other
    is_cross_source: bool = False  # True if tension spans multiple sources

    def to_dict(self) -> dict[str, Any]:
        result = {
            "tension_id": self.tension_id,
            "description": self.description,
            "involved_key_points": self.involved_key_points,
        }
        # Include Phase 5 fields if populated
        if self.is_cross_source:
            result["sources_position_a"] = self.sources_position_a
            result["sources_position_b"] = self.sources_position_b
            result["is_cross_source"] = self.is_cross_source
        return result


# -----------------------------------------------------------------------------
# GAP (Operational Definitions §8)
# -----------------------------------------------------------------------------

@dataclass
class Gap:
    """
    Information a competent researcher would expect but is missing.

    Examples:
    - Missing response from a key party
    - No primary documentation for a major claim
    - No coverage of consequences or outcomes

    Rules:
    - Gaps are contextual, not absolute
    - Gaps must explain *why* the information is expected
    - Gaps drive the Jump-Start document
    """
    gap_id: str
    description: str
    why_expected: str
    related_themes: list[str] = field(default_factory=list)  # Theme IDs
    related_key_points: list[str] = field(default_factory=list)  # KeyPoint IDs
    suggested_research_direction: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "description": self.description,
            "why_expected": self.why_expected,
            "related_themes": self.related_themes,
            "related_key_points": self.related_key_points,
            "suggested_research_direction": self.suggested_research_direction,
        }


# -----------------------------------------------------------------------------
# APPROXIMATE OBSERVATION (for video_only mode)
# -----------------------------------------------------------------------------

@dataclass
class ApproximateObservation:
    """
    Semantic description of observed content in video_only mode.

    NOT a quote - this is a description of what was observed
    from visual/audio cues when no transcript is available.

    Rules:
    - Only used when analysis_mode = video_only
    - Must be marked approximate: true
    - Confidence ceiling is LOW
    - Never claim verbatim accuracy
    """
    observation_id: str
    observation: str
    source_id: str
    timestamp_range: str  # "~MM:SS - MM:SS"
    approximate: bool = True  # Always true
    observation_type: str = "observation"  # Always "observation"
    confidence: ConfidenceLevel = ConfidenceLevel.LOW  # Always LOW for video_only

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "observation": self.observation,
            "source_id": self.source_id,
            "timestamp_range": self.timestamp_range,
            "approximate": self.approximate,
            "type": self.observation_type,
            "confidence": self.confidence.value,
        }


# -----------------------------------------------------------------------------
# SPECULATIVE OBSERVATION (Operational Definitions §10)
# -----------------------------------------------------------------------------

@dataclass
class SpeculativeObservation:
    """
    Inference that goes beyond what source data directly supports.

    Examples:
    - "This may indicate an attempt to obscure responsibility."
    - "One possible motive is financial pressure."

    Rules:
    - Must be explicitly labeled as speculative
    - Must never appear in Doc 0
    - Optional in Doc 2
    - Never presented as truth
    """
    text: str
    based_on: list[str] = field(default_factory=list)  # KeyPoint IDs
    label: str = "speculative"  # Always "speculative"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "based_on": self.based_on,
            "label": self.label,
        }


# -----------------------------------------------------------------------------
# SEMANTIC EXTRACTION RESULT (aggregates all units from one source)
# -----------------------------------------------------------------------------

@dataclass
class SemanticExtractionResult:
    """
    Complete semantic extraction output for a single source.

    Contains all extracted semantic units from one source,
    along with metadata about how the extraction was performed.
    """
    source_id: str
    analysis_mode: AnalysisMode

    # Extracted units
    quotes: list[Quote] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    key_points: list[KeyPoint] = field(default_factory=list)
    themes: list[Theme] = field(default_factory=list)
    tensions: list[Tension] = field(default_factory=list)

    # For video_only mode
    approximate_observations: list[ApproximateObservation] = field(default_factory=list)

    # Metadata
    analysis_limitations: list[str] = field(default_factory=list)
    transcript_source: Optional[str] = None  # "supadata", "whisper", "youtube_captions", "none"
    parse_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "analysis_mode": self.analysis_mode.value,
            "quotes": [q.to_dict() for q in self.quotes],
            "claims": [c.to_dict() for c in self.claims],
            "key_points": [kp.to_dict() for kp in self.key_points],
            "themes": [t.to_dict() for t in self.themes],
            "tensions": [t.to_dict() for t in self.tensions],
            "approximate_observations": [ao.to_dict() for ao in self.approximate_observations],
            "analysis_limitations": self.analysis_limitations,
            "transcript_source": self.transcript_source,
            "parse_error": self.parse_error,
        }

    @property
    def confidence_ceiling(self) -> ConfidenceLevel:
        """Return max allowed confidence based on analysis mode.

        NOTE: This mapping mirrors backend.pipeline.mode_selector.CONFIDENCE_CEILINGS.
        Cannot import from mode_selector to avoid circular import.
        Keep in sync with mode_selector (single source of truth for pipeline).

        Per INDEX.md "Six Analysis Modes":
        - transcript_grounded, article_fetched: HIGH
        - caption_grounded, text_provided, ocr_extracted: MEDIUM
        - video_only: LOW
        """
        # Mirrors mode_selector.CONFIDENCE_CEILINGS - keep in sync
        ceilings = {
            # Video sources
            AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
            AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
            AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
            # Non-video sources
            AnalysisMode.TEXT_PROVIDED: ConfidenceLevel.MEDIUM,
            AnalysisMode.OCR_EXTRACTED: ConfidenceLevel.MEDIUM,
            AnalysisMode.ARTICLE_FETCHED: ConfidenceLevel.HIGH,
        }
        return ceilings.get(self.analysis_mode, ConfidenceLevel.LOW)

    def enforce_confidence_ceiling(self) -> list[str]:
        """
        Downgrade confidence levels that exceed mode ceiling.
        Returns list of warnings for each downgrade.
        """
        warnings = []
        ceiling = self.confidence_ceiling
        ceiling_order = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
        ceiling_idx = ceiling_order.index(ceiling)

        for claim in self.claims:
            claim_idx = ceiling_order.index(claim.confidence)
            if claim_idx > ceiling_idx:
                warnings.append(
                    f"Confidence auto-downgraded from {claim.confidence.value} "
                    f"to {ceiling.value} for claim {claim.claim_id}"
                )
                claim.confidence = ceiling

        for kp in self.key_points:
            kp_idx = ceiling_order.index(kp.confidence)
            if kp_idx > ceiling_idx:
                warnings.append(
                    f"Confidence auto-downgraded from {kp.confidence.value} "
                    f"to {ceiling.value} for key_point {kp.key_point_id}"
                )
                kp.confidence = ceiling

        return warnings
