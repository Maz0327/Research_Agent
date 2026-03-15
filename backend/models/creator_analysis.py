"""Creator Analysis models — style profile output from analyzing a creator's videos.

Used by the creator analysis pipeline to produce a Creator Style Profile document.
The profile captures hook patterns, narrative structure, vocabulary fingerprint,
aesthetic keywords, and tone descriptors.

NOTE: CreatorStyleProfileSchema is used as Gemini response_schema.
      It MUST have NO default values (Gemini API rejects them).
"""

from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Gemini response_schema model — NO DEFAULTS ALLOWED
# =============================================================================


class HookPatternSchema(BaseModel):
    """A recurring hook pattern found in the creator's content."""
    hook_type: str  # "question", "stat", "story", "contradiction", "visual"
    example: str
    frequency: str  # "very_common", "common", "occasional"


class NarrativeStructureSchema(BaseModel):
    """Analysis of the creator's narrative structure."""
    primary_structure: str  # "heros_journey", "five_act", "problem_solution", "chronological", "mystery_reveal"
    structure_description: str
    pacing: str  # "fast", "medium", "deliberate"
    transition_style: str


class VocabularyFingerprintSchema(BaseModel):
    """Vocabulary patterns unique to the creator."""
    signature_phrases: list[str]
    filler_words: list[str]
    unique_expressions: list[str]
    tone_markers: list[str]


class AestheticProfileSchema(BaseModel):
    """Visual and audio aesthetic descriptors."""
    visual_style: str
    color_palette: str
    broll_style: str
    music_tone: str
    pacing_descriptors: list[str]
    typography_style: str


class ToneDescriptorSchema(BaseModel):
    """Tone analysis along multiple axes."""
    formality: str  # "very_formal" to "very_casual"
    humor_usage: str  # "none", "occasional", "frequent", "core_element"
    emotional_range: str
    authority_level: str  # "peer", "expert", "mentor", "entertainer"
    energy_level: str  # "calm", "moderate", "high", "intense"


class CreatorStyleProfileSchema(BaseModel):
    """Full creator style profile — Gemini response_schema.

    NO DEFAULT VALUES — Gemini rejects schemas with defaults.
    """
    creator_name: str
    channel_description: str
    content_niche: str
    hook_patterns: list[HookPatternSchema]
    narrative_structure: NarrativeStructureSchema
    vocabulary_fingerprint: VocabularyFingerprintSchema
    aesthetic_profile: AestheticProfileSchema
    tone_descriptors: ToneDescriptorSchema
    style_summary: str
    recommended_voice: str
    recommended_hook_style: str
    recommended_structure: str


# =============================================================================
# API request/response models (can have defaults)
# =============================================================================


class CreatorAnalysisRequest(BaseModel):
    """Request body for creating a creator analysis job."""
    creator_name: str = Field(..., min_length=1, max_length=200)
    video_urls: list[str] = Field(..., min_length=3, max_length=5)


class CreatorAnalysisResponse(BaseModel):
    """Response from creator analysis endpoint."""
    job_id: str
    status: str
    message: str


class CreatorStyleProfileResponse(BaseModel):
    """Full style profile response wrapping the schema output."""
    job_id: str
    creator_name: str
    profile: dict
    video_count: int
    status: str
