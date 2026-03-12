"""Creator Brief (Doc 3) data models.

The Creator Brief is the hero document — auto-generated after every successful pipeline run.
It distills Doc 2 (Semantic Brief) claims and Doc 0 (Source Ledger) data into a
production-ready creative brief for the creator.

Provenance chain (enforced):
  Every hook_option.claim_id → must exist in Doc 2
  Every core_fact.claim_id   → must exist in Doc 2
  Every core_fact.source_id  → must exist in Doc 0
  Every disputed_claim.claim_id → must exist in Doc 2 with matching framing
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class HookOption(BaseModel):
    """A hook option for the video. Two are always generated (A and B)."""
    hook_id: str = Field(..., description="HOOK_A or HOOK_B")
    text: str = Field(..., min_length=10, description="The hook text as it would be spoken")
    why_it_works: str = Field(..., description="Brief explanation of why this hook is compelling")
    claim_id: str = Field(..., description="The claim_id from Doc 2 this hook is derived from")
    source_id: str = Field(..., description="The source_id from Doc 0 of the primary source")


class Setup(BaseModel):
    """The setup section — core theme/thesis."""
    text: str = Field(..., min_length=20, description="The setup text explaining the core topic")
    supporting_claim_ids: list[str] = Field(
        default_factory=list,
        description="claim_ids from Doc 2 that ground this setup"
    )
    supporting_source_ids: list[str] = Field(
        default_factory=list,
        description="source_ids from Doc 0 that ground this setup"
    )


class Twist(BaseModel):
    """The twist/contrast moment — a contradiction or reversal."""
    text: str = Field(..., min_length=20, description="The twist text revealing the contradiction or surprise")
    claim_id: str = Field(..., description="claim_id from Doc 2 with framing=contradicts or disputed")
    source_id: str = Field(..., description="source_id from Doc 0")
    framing: Literal["contradicts", "disputed"] = Field(
        ..., description="Must match the claim's framing in Doc 2"
    )


class CoreFact(BaseModel):
    """A core fact — high-significance claim with plain-English phrasing."""
    fact_id: str = Field(..., description="FACT_1, FACT_2, ... FACT_5")
    statement: str = Field(..., description="The fact as extracted (may contain technical language)")
    say_it_like: str = Field(
        ...,
        description="Plain-English version of the fact — how to actually say it in a video"
    )
    significance: Literal["high", "medium", "low"] = Field(
        ..., description="Significance level from Doc 2 claim"
    )
    claim_id: str = Field(..., description="claim_id from Doc 2")
    source_id: str = Field(..., description="source_id from Doc 0")
    speaker: Optional[str] = Field(None, description="Who stated this fact, if attributed")


class Analogy(BaseModel):
    """An analogy to explain the core concept for a general audience."""
    text: str = Field(..., min_length=20, description="The analogy text")
    supporting_claim_ids: list[str] = Field(
        default_factory=list,
        description="claim_ids from Doc 2 that inspired this analogy"
    )


class PersonalStakes(BaseModel):
    """Why this matters to the viewer."""
    text: str = Field(..., min_length=20, description="The personal stakes text")
    supporting_claim_ids: list[str] = Field(
        default_factory=list,
        description="claim_ids from Doc 2 that support the stakes framing"
    )


class Cliffhanger(BaseModel):
    """An open question or speculative claim to end with."""
    text: str = Field(..., min_length=10, description="The cliffhanger text")
    claim_id: Optional[str] = Field(
        None, description="claim_id from Doc 2 with framing=speculative, if available"
    )
    framing: Literal["speculative", "open_question"] = Field(
        ..., description="Whether based on a speculative claim or an open question"
    )


class DescriptionSource(BaseModel):
    """A source formatted for the video description box."""
    source_id: str = Field(..., description="source_id from Doc 0")
    title: str = Field(..., description="Source title")
    url: Optional[str] = Field(None, description="Source URL, if available")
    creator: Optional[str] = Field(None, description="Creator/author of the source")


class DisputedClaim(BaseModel):
    """A claim flagged as disputed, speculative, or contradictory."""
    claim_id: str = Field(..., description="claim_id from Doc 2")
    statement: str = Field(..., description="The claim text")
    framing: Literal["disputed", "speculative", "contradicts", "hedged"] = Field(
        ..., description="Must match the claim's framing in Doc 2"
    )
    speaker: Optional[str] = Field(None, description="Who made this claim, if attributed")
    source_id: str = Field(..., description="source_id from Doc 0")


class CreatorBriefGuardrails(BaseModel):
    """Provenance acknowledgments — all must be True or the brief is invalid."""
    no_new_facts_ack: bool = Field(
        True, description="No facts introduced beyond Doc 0 content"
    )
    all_facts_reference_doc2: bool = Field(
        True, description="All claim_ids reference Doc 2"
    )
    all_facts_reference_doc0: bool = Field(
        True, description="All source_ids reference Doc 0"
    )


# ---------------------------------------------------------------------------
# Top-level Creator Brief document
# ---------------------------------------------------------------------------

class CreatorBriefDocument(BaseModel):
    """Creator Brief — Doc 3.

    The hero document. Auto-generated after every successful pipeline run.
    Distills Doc 2 claims and Doc 0 sources into a production-ready creative brief.

    Provenance requirements (validated by creator_brief_stage.py):
    - hook_options: exactly 2, each claim_id must exist in Doc 2
    - core_facts: 3–5 entries, each claim_id in Doc 2, each source_id in Doc 0
    - twist.claim_id must exist in Doc 2 with framing=contradicts or disputed
    - disputed_claims: all claim_ids must exist in Doc 2 with matching framing
    """
    document_type: Literal["creator_brief"] = "creator_brief"
    document_version: str = "1.0"
    job_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    topic: str = Field(..., description="The research topic")
    source_count: int = Field(..., ge=1, description="Number of sources in the job")

    hook_options: list[HookOption] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Exactly 2 hook options (A and B)"
    )
    setup: Setup
    twist: Optional[Twist] = Field(
        None,
        description="The twist/contradiction. May be absent if no contradicting claims found."
    )
    core_facts: list[CoreFact] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3–5 high-significance core facts"
    )
    analogy: Optional[Analogy] = Field(
        None,
        description="Analogy for general audience. May be absent if claims don't lend themselves to analogy."
    )
    personal_stakes: Optional[PersonalStakes] = Field(
        None,
        description="Why this matters to the viewer."
    )
    cliffhanger: Optional[Cliffhanger] = Field(
        None,
        description="Cliffhanger/open question. May be absent if no speculative claims."
    )
    description_sources: list[DescriptionSource] = Field(
        default_factory=list,
        description="Sources formatted for description box copy-paste"
    )
    disputed_claims: list[DisputedClaim] = Field(
        default_factory=list,
        description="All disputed/speculative claims explicitly flagged"
    )
    guardrails: CreatorBriefGuardrails = Field(
        default_factory=CreatorBriefGuardrails
    )

    @field_validator("hook_options")
    @classmethod
    def validate_hook_ids(cls, v: list[HookOption]) -> list[HookOption]:
        """Ensure hooks are labeled HOOK_A and HOOK_B."""
        ids = {h.hook_id for h in v}
        if ids != {"HOOK_A", "HOOK_B"}:
            raise ValueError("hook_options must contain exactly HOOK_A and HOOK_B")
        return v

    @field_validator("core_facts")
    @classmethod
    def validate_fact_ids(cls, v: list[CoreFact]) -> list[CoreFact]:
        """Ensure fact_ids are sequential (FACT_1 through FACT_N)."""
        expected = {f"FACT_{i}" for i in range(1, len(v) + 1)}
        actual = {f.fact_id for f in v}
        if actual != expected:
            raise ValueError(
                f"core_facts must have sequential IDs FACT_1..FACT_{len(v)}, got {sorted(actual)}"
            )
        return v

    @model_validator(mode="after")
    def validate_guardrails_are_true(self) -> "CreatorBriefDocument":
        """Guardrails must all be True — a brief with False guardrails is invalid."""
        g = self.guardrails
        if not g.no_new_facts_ack:
            raise ValueError("guardrails.no_new_facts_ack must be True")
        if not g.all_facts_reference_doc2:
            raise ValueError("guardrails.all_facts_reference_doc2 must be True")
        if not g.all_facts_reference_doc0:
            raise ValueError("guardrails.all_facts_reference_doc0 must be True")
        return self

    def all_claim_ids(self) -> set[str]:
        """Return all claim_ids referenced in this brief (for provenance validation)."""
        ids: set[str] = set()
        for h in self.hook_options:
            ids.add(h.claim_id)
        ids.update(self.setup.supporting_claim_ids)
        if self.twist:
            ids.add(self.twist.claim_id)
        for f in self.core_facts:
            ids.add(f.claim_id)
        if self.analogy:
            ids.update(self.analogy.supporting_claim_ids)
        if self.personal_stakes:
            ids.update(self.personal_stakes.supporting_claim_ids)
        if self.cliffhanger and self.cliffhanger.claim_id:
            ids.add(self.cliffhanger.claim_id)
        for d in self.disputed_claims:
            ids.add(d.claim_id)
        return ids

    def all_source_ids(self) -> set[str]:
        """Return all source_ids referenced in this brief (for provenance validation)."""
        ids: set[str] = set()
        for h in self.hook_options:
            ids.add(h.source_id)
        ids.update(self.setup.supporting_source_ids)
        if self.twist:
            ids.add(self.twist.source_id)
        for f in self.core_facts:
            ids.add(f.source_id)
        for s in self.description_sources:
            ids.add(s.source_id)
        for d in self.disputed_claims:
            ids.add(d.source_id)
        return ids


# ---------------------------------------------------------------------------
# Version metadata (used by version_manager.py in Phase 3)
# ---------------------------------------------------------------------------

class DocumentVersionMetadata(BaseModel):
    """Metadata stored alongside each document version.

    Stored at: research-jobs/{job_id}/doc_{N}/v{version}_meta.json
    """
    version: int = Field(..., ge=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    trigger: Literal[
        "initial_run",
        "deep_dive",
        "expand_sources",
        "deeper",
        "different_angle",
        "custom",
    ] = "initial_run"
    source_count: int = Field(..., ge=0)
    claim_count: int = Field(..., ge=0)
    diff_summary: str = Field(
        default="",
        description="Human-readable change summary, e.g. '+3 sources, +12 claims'"
    )
