"""Pydantic schema for Gemini response_schema (no defaults allowed).

Google's Gemini API requires response_schema models to have NO default values.
See: https://github.com/googleapis/python-genai/issues/699

This module provides schema classes specifically for Gemini JSON mode,
while semantic_units.py provides the runtime dataclasses with defaults.

Usage in generate_json():
    from backend.models.semantic_extraction_schema import SemanticExtractionSchema

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SemanticExtractionSchema,
    )
"""

from pydantic import BaseModel
from typing import Literal


class QuoteSchema(BaseModel):
    """Quote schema for Gemini - no defaults."""
    quote_id: str
    text: str
    source_id: str
    timestamp: str  # MM:SS or empty string
    approximate: bool


class ClaimSchema(BaseModel):
    """Claim schema for Gemini - no defaults."""
    claim_id: str
    statement: str
    source_id: str
    supporting_quotes: list[str]
    confidence: Literal["low", "medium", "high"]
    confidence_rationale: str  # Required: explanation for confidence level


class KeyPointSchema(BaseModel):
    """Key point schema for Gemini - no defaults."""
    key_point_id: str
    statement: str
    source_ids: list[str]
    supporting_claims: list[str]
    confidence: Literal["low", "medium", "high"]
    confidence_rationale: str  # Required: explanation for confidence level


class ThemeSchema(BaseModel):
    """Theme schema for Gemini - no defaults."""
    theme_id: str
    label: str
    description: str
    related_key_points: list[str]


class TensionSchema(BaseModel):
    """Tension schema for Gemini - no defaults."""
    tension_id: str
    description: str
    involved_key_points: list[str]


class ApproximateObservationSchema(BaseModel):
    """Observation schema for video_only mode - no defaults."""
    observation_id: str
    observation: str
    source_id: str
    timestamp_range: str


class SemanticExtractionSchema(BaseModel):
    """Complete extraction schema for Gemini response_schema.

    NO default values - Gemini API requirement.
    All fields required, empty arrays represented as [].
    """
    source_id: str
    analysis_mode: Literal[
        "transcript_grounded",
        "caption_grounded",
        "video_only",
        "text_provided",
        "ocr_extracted",
        "article_fetched"
    ]
    quotes: list[QuoteSchema]
    claims: list[ClaimSchema]
    key_points: list[KeyPointSchema]
    themes: list[ThemeSchema]
    tensions: list[TensionSchema]
    approximate_observations: list[ApproximateObservationSchema]
    analysis_limitations: list[str]
    reasoning_trace: list[str]  # Chain-of-thought reasoning steps for hallucination prevention
