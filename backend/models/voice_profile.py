"""Voice Profile data models.

Stores analyzed creator voice patterns for voice mimicry in script generation.
Generated from creator's video transcripts using LLM analysis.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SentenceRhythm(BaseModel):
    """Analysis of a creator's sentence rhythm patterns."""
    avg_sentence_length: int = Field(..., ge=1, description="Average sentence word count")
    length_variation: Literal["uniform", "varied", "highly_varied"] = "varied"
    fragment_frequency: Literal["none", "occasional", "frequent"] = "occasional"


class TransitionPattern(BaseModel):
    """A recurring transition phrase used by the creator."""
    from_context: str = Field(..., description="e.g. 'evidence to opinion'")
    phrase: str = Field(..., description="e.g. 'But here's the thing...'")
    frequency: str = Field(..., description="e.g. 'common', 'occasional'")


class EmphasisPatterns(BaseModel):
    """Analysis of how a creator emphasizes points."""
    repetition_style: str = Field("", description="How they repeat for emphasis")
    rhetorical_questions: bool = Field(False, description="Uses rhetorical questions?")
    pause_markers: list[str] = Field(
        default_factory=list,
        description="Pause markers like '...', 'right?'"
    )


class VoiceProfile(BaseModel):
    """A creator's analyzed voice profile for script mimicry.

    Generated from multiple video transcripts. Used to inject
    voice-specific instructions into the Script Writer prompt.
    """
    id: str = Field(..., description="UUID")
    user_id: str = Field(..., description="Owner user UUID")
    creator_name: str = Field(..., min_length=1, description="Name of the creator being analyzed")
    style_profile: dict = Field(
        default_factory=dict,
        description="CreatorStyleProfileSchema data from existing analysis"
    )
    sentence_rhythm: SentenceRhythm = Field(
        default_factory=lambda: SentenceRhythm(avg_sentence_length=12)
    )
    transition_patterns: list[TransitionPattern] = Field(default_factory=list)
    opening_patterns: list[str] = Field(default_factory=list)
    closing_patterns: list[str] = Field(default_factory=list)
    emphasis_patterns: EmphasisPatterns = Field(default_factory=EmphasisPatterns)
    source_video_urls: list[str] = Field(default_factory=list)
    source_video_count: int = Field(default=0, ge=0)

    def to_voice_instructions(self) -> str:
        """Generate voice mimicry instructions for the script prompt.

        Returns:
            Formatted instruction string for LLM prompt injection.
        """
        lines = [f"Mimic the voice of {self.creator_name}.", ""]

        # Sentence rhythm
        rhythm = self.sentence_rhythm
        lines.append(f"SENTENCE RHYTHM:")
        lines.append(f"- Average sentence length: ~{rhythm.avg_sentence_length} words")
        lines.append(f"- Length variation: {rhythm.length_variation}")
        lines.append(f"- Fragment frequency: {rhythm.fragment_frequency}")
        lines.append("")

        # Transitions
        if self.transition_patterns:
            lines.append("TRANSITION PATTERNS (use these):")
            for tp in self.transition_patterns[:8]:
                lines.append(f"- {tp.from_context}: \"{tp.phrase}\" ({tp.frequency})")
            lines.append("")

        # Opening patterns
        if self.opening_patterns:
            lines.append("OPENING PATTERNS (mimic these styles):")
            for op in self.opening_patterns[:5]:
                lines.append(f"- {op}")
            lines.append("")

        # Closing patterns
        if self.closing_patterns:
            lines.append("CLOSING PATTERNS (mimic these styles):")
            for cp in self.closing_patterns[:5]:
                lines.append(f"- {cp}")
            lines.append("")

        # Emphasis
        emp = self.emphasis_patterns
        lines.append("EMPHASIS STYLE:")
        if emp.repetition_style:
            lines.append(f"- Repetition: {emp.repetition_style}")
        lines.append(f"- Rhetorical questions: {'Yes' if emp.rhetorical_questions else 'No'}")
        if emp.pause_markers:
            lines.append(f"- Pause markers: {', '.join(emp.pause_markers)}")

        return "\n".join(lines)


class CreateVoiceProfileRequest(BaseModel):
    """Request body for POST /voice-profiles."""
    creator_name: str = Field(..., min_length=1)
    video_urls: list[str] = Field(..., min_length=1, max_length=10)
