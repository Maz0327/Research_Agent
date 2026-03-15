"""Brainstorm models — request/response schemas for the brainstorm pre-stage.

The brainstorm endpoint generates creative angles, vocabulary, and source
strategies BEFORE research begins. Inspired by the "burden of proof on AI"
principle — open-ended "what angles should we explore?" prompting.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ─── LLM Output Schema (no defaults — Gemini requirement) ────────────────────

class StoryArc(BaseModel):
    """Five-act narrative structure for a brainstorm angle."""
    hook: str
    conflict: str
    build: str
    resolution: str
    cta: str


class BrainstormAngleLLM(BaseModel):
    """Single angle suggestion from Gemini (no defaults)."""
    title: str
    description: str
    hook_preview: str
    story_arc: StoryArc
    content_type: str
    estimated_depth: str


class BrainstormLLMOutput(BaseModel):
    """Full Gemini output schema for brainstorm (no defaults)."""
    angles: list[BrainstormAngleLLM]
    vocabulary: list[str]
    key_questions: list[str]
    aesthetic_keywords: list[str]
    suggested_search_queries: list[str]


# ─── API Request/Response ────────────────────────────────────────────────────

class BrainstormRequest(BaseModel):
    """Request body for POST /jobs/brainstorm."""
    topic: str = Field(..., min_length=3, max_length=2000)
    audience_hint: Optional[str] = Field(None, max_length=100)
    style_guide_id: Optional[str] = None


class BrainstormAngle(BaseModel):
    """Angle in the brainstorm response (with IDs added server-side)."""
    angle_id: str
    title: str
    description: str
    hook_preview: str
    story_arc: StoryArc
    content_type: str
    estimated_depth: str


class BrainstormResponse(BaseModel):
    """Response body for POST /jobs/brainstorm."""
    angles: list[BrainstormAngle] = Field(default_factory=list)
    vocabulary: list[str] = Field(default_factory=list)
    key_questions: list[str] = Field(default_factory=list)
    aesthetic_keywords: list[str] = Field(default_factory=list)
    suggested_search_queries: list[str] = Field(default_factory=list)
    cost: float = 0.0
