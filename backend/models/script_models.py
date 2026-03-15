"""Script Writer (Doc 5) data models.

The Script is a spoken-word video script with tone/length controls.
It distills Doc 2 (Semantic Brief) claims and Doc 0 (Source Ledger) data
into a structured video script with full provenance.

Provenance chain (enforced):
  Every section.claim_ids → must exist in Doc 2
  Every section.source_ids → must exist in Doc 0
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ScriptHook(BaseModel):
    """Opening hook for the script."""
    text: str = Field(..., min_length=10, description="The hook text as it would be spoken")
    hook_type: str = Field(..., description="Type of hook: question, statistic, story, provocative")
    claim_id: str = Field(..., description="claim_id from Doc 2")
    source_id: str = Field(..., description="source_id from Doc 0")


class ScriptSection(BaseModel):
    """A section of the video script with spoken text and stage directions."""
    section_id: str = Field(..., description="SCRIPT_SEC_1, SCRIPT_SEC_2, ...")
    beat_label: str = Field(..., description="Story arc beat label")
    spoken_text: str = Field(..., min_length=20, description="The actual spoken script text")
    stage_direction: Optional[str] = Field(None, description="Visual/b-roll notes in italics")
    duration_estimate: str = Field(..., description="e.g. '~90 seconds'")
    claim_ids: list[str] = Field(
        default_factory=list,
        description="claim_ids from Doc 2 referenced in this section"
    )
    source_ids: list[str] = Field(
        default_factory=list,
        description="source_ids from Doc 0 referenced in this section"
    )


class ScriptOutro(BaseModel):
    """Outro/closing section of the script."""
    text: str = Field(..., min_length=10, description="Closing spoken text")
    call_to_action: Optional[str] = Field(None, description="Optional CTA")


class ScriptGuardrails(BaseModel):
    """Provenance acknowledgments — all must be True."""
    no_new_facts_ack: bool = Field(True, description="No facts introduced beyond Doc 0 content")
    all_facts_reference_doc2: bool = Field(True, description="All claim_ids reference Doc 2")
    all_facts_reference_doc0: bool = Field(True, description="All source_ids reference Doc 0")


class ScriptDocument(BaseModel):
    """Script — Doc 5.

    A spoken-word video script with tone and length controls.
    Every claim traces to Doc 2 and every source to Doc 0.
    """
    document_type: Literal["script"] = "script"
    job_id: str
    generated_at: str = Field(..., description="ISO datetime string")
    topic: str = Field(..., description="The research topic")
    source_count: int = Field(..., ge=1)
    tone: Literal["serious", "casual", "energetic", "conversational"] = "conversational"
    target_length: Literal["short", "medium", "long"] = "medium"
    story_arc: str = Field(..., description="Story arc used for structure")
    title: str = Field(..., min_length=5, description="Script title")
    hook: ScriptHook
    sections: list[ScriptSection] = Field(
        ...,
        min_length=3,
        max_length=18,
        description="3-18 script sections"
    )
    outro: ScriptOutro
    total_word_count: int = Field(..., ge=0)
    estimated_duration: str = Field(..., description="e.g. '8 minutes'")
    description_sources: list[dict] = Field(
        default_factory=list,
        description="Sources for attribution (DescriptionSource dicts)"
    )
    guardrails: ScriptGuardrails = Field(default_factory=ScriptGuardrails)

    @field_validator("sections")
    @classmethod
    def validate_section_ids(cls, v: list[ScriptSection]) -> list[ScriptSection]:
        """Ensure section_ids are sequential SCRIPT_SEC_1..SCRIPT_SEC_N."""
        expected = {f"SCRIPT_SEC_{i}" for i in range(1, len(v) + 1)}
        actual = {s.section_id for s in v}
        if actual != expected:
            raise ValueError(
                f"sections must have sequential IDs SCRIPT_SEC_1..SCRIPT_SEC_{len(v)}, got {sorted(actual)}"
            )
        return v

    def all_claim_ids(self) -> set[str]:
        """Return all claim_ids referenced in this script."""
        ids: set[str] = {self.hook.claim_id}
        for s in self.sections:
            ids.update(s.claim_ids)
        return ids

    def all_source_ids(self) -> set[str]:
        """Return all source_ids referenced in this script."""
        ids: set[str] = {self.hook.source_id}
        for s in self.sections:
            ids.update(s.source_ids)
        for ds in self.description_sources:
            if ds.get("source_id"):
                ids.add(ds["source_id"])
        return ids


class GenerateScriptRequest(BaseModel):
    """Request body for POST /jobs/{job_id}/script."""
    tone: Literal["serious", "casual", "energetic", "conversational"] = "conversational"
    target_length: Literal["short", "medium", "long"] = "medium"
    story_arc: Optional[str] = None
    style_guide_id: Optional[str] = None
    voice_profile_id: Optional[str] = None
