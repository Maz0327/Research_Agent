"""Style guide models for personal creator style preferences.

Style guides shape brainstorm suggestions, Creator Brief tone, hooks,
and narrative structure. Three default templates provided:
- deep_dive_explainer: Educational/explainer (Kurzgesagt, MKBHD)
- investigative_storyteller: Investigation/documentary (Coffeezilla)
- casual_conversationalist: Personality-driven (Emma Chamberlain, MrBeast)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TemplateBase(str, Enum):
    """Pre-built style guide templates."""
    DEEP_DIVE_EXPLAINER = "deep_dive_explainer"
    INVESTIGATIVE_STORYTELLER = "investigative_storyteller"
    CASUAL_CONVERSATIONALIST = "casual_conversationalist"
    CUSTOM = "custom"


class StyleGuideOverrides(BaseModel):
    """User overrides on top of a template base."""
    voice: Optional[str] = None
    audience: Optional[str] = None
    vocabulary_use: Optional[list[str]] = None
    vocabulary_avoid: Optional[list[str]] = None
    structure: Optional[str] = None
    hook_style: Optional[str] = None
    inspirations: Optional[list[str]] = None


class SectionPreference(BaseModel):
    """Per-section display preferences for Doc 3."""
    section_key: str
    enabled: bool = True
    order: int = 0


class StyleGuide(BaseModel):
    """Full style guide record from Supabase."""
    id: str
    user_id: str
    name: str
    template_base: TemplateBase
    overrides: StyleGuideOverrides = Field(default_factory=StyleGuideOverrides)
    section_preferences: list[SectionPreference] = Field(default_factory=list)
    is_default: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class StyleGuideCreate(BaseModel):
    """Request body for creating a new style guide."""
    name: str = Field(..., min_length=1, max_length=100)
    template_base: TemplateBase
    overrides: StyleGuideOverrides = Field(default_factory=StyleGuideOverrides)
    section_preferences: list[SectionPreference] = Field(default_factory=list)
    is_default: bool = False


class StyleGuideUpdate(BaseModel):
    """Request body for updating a style guide. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    template_base: Optional[TemplateBase] = None
    overrides: Optional[StyleGuideOverrides] = None
    section_preferences: Optional[list[SectionPreference]] = None
    is_default: Optional[bool] = None


class StyleGuideResponse(BaseModel):
    """API response shape for a style guide."""
    id: str
    name: str
    template_base: str
    overrides: dict[str, Any] = Field(default_factory=dict)
    section_preferences: list[dict[str, Any]] = Field(default_factory=list)
    is_default: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_style_guide(cls, sg: StyleGuide) -> "StyleGuideResponse":
        """Convert a StyleGuide model to API response."""
        return cls(
            id=sg.id,
            name=sg.name,
            template_base=sg.template_base.value,
            overrides=sg.overrides.model_dump(exclude_none=True),
            section_preferences=[sp.model_dump() for sp in sg.section_preferences],
            is_default=sg.is_default,
            created_at=sg.created_at,
            updated_at=sg.updated_at,
        )


# =============================================================================
# Default Templates (static data — no DB needed)
# =============================================================================

DEFAULT_TEMPLATES: dict[str, dict[str, Any]] = {
    "deep_dive_explainer": {
        "name": "Deep Dive Explainer",
        "description": "Educational/explainer style. Confident, clear, curious.",
        "creator_references": "Kurzgesagt, Wendover, MKBHD, Ali Abdaal, Veritasium",
        "voice": "Confident, clear, curious. 'Let me show you what I found' — shared discovery, not lecture.",
        "audience": "Curious generalists (18-45) who want to understand a topic in 10-25 min.",
        "vocabulary_use": [
            "Here's why that matters",
            "The short version is...",
            "Think of it like...",
            "What most people miss is...",
        ],
        "vocabulary_avoid": [
            "Interestingly",
            "It's important to note",
            "One could argue",
            "stakeholders",
            "paradigm",
            "furthermore",
            "moreover",
        ],
        "structure": "Setup (frame the question) → Context → Core mechanism → Implications (so what?) → Open thread",
        "hook_style": "Question-driven or counterintuitive fact. Opens with specific detail that creates information gap.",
        "example_tone": "The FTC fined the company $150 million — the largest penalty in the agency's history for a data privacy case. But the fine wasn't what changed the industry; it was the three-sentence clause buried in the settlement.",
    },
    "investigative_storyteller": {
        "name": "Investigative Storyteller",
        "description": "Direct, urgent, evidence-forward. Every claim backed by something specific.",
        "creator_references": "Coffeezilla, Philip DeFranco, SomeOrdinaryGamers",
        "voice": "Direct, urgent, evidence-forward. Controlled intensity — facts are dramatic enough without hype.",
        "audience": "Engaged, slightly skeptical viewers (20-40) who value receipts over opinions.",
        "vocabulary_use": [
            "Here's what we know",
            "The documents show...",
            "They said X. The records say Y.",
        ],
        "vocabulary_avoid": [
            "Allegedly",
            "Some people say",
            "It's complicated",
            "Shocking",
            "insane",
            "mind-blowing",
            "I think",
        ],
        "structure": "Cold open (single damning detail) → Surface story → Evidence trail (chronological) → The pattern → What happens next",
        "hook_style": "Contradiction or reveal. Juxtaposes official claim against contradicting evidence.",
        "example_tone": "On March 3rd, the CEO told investors the product was 'fully tested and safe.' Internal emails from February 28th show the engineering team flagged three unresolved safety failures.",
    },
    "casual_conversationalist": {
        "name": "Casual Conversationalist",
        "description": "Warm, opinionated, conversational. Smart friend texting you about something they found.",
        "creator_references": "Emma Chamberlain, MrBeast narration, podcast hosts",
        "voice": "Warm, opinionated, conversational. Short sentences. Fragments fine. Energy over precision.",
        "audience": "Gen Z and younger millennials (16-30) on phones, often multitasking.",
        "vocabulary_use": [
            "Okay so",
            "So basically",
            "Wait, it gets worse",
            "The thing is...",
            "This is the part nobody talks about",
        ],
        "vocabulary_avoid": [
            "However",
            "Nevertheless",
            "Thus",
            "Research indicates",
            "In conclusion",
            "Utilize",
        ],
        "structure": "The take (lead with opinion) → Context (just enough) → The receipts → Hot take (prediction) → Closer (question to audience)",
        "hook_style": "Reaction-first or hot take. Opens with emotional response that makes viewers want to know why.",
        "example_tone": "So this company just got caught charging customers for a subscription they never signed up for — and we're not talking about like 50 people. Try 2.4 million accounts.",
    },
}
