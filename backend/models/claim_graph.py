"""Claim Graph - the canonical distillation of a research job.

One distillation stage produces this graph; every downstream document is a
projection of it (selection + ordering + voice). Projections may not introduce
facts - they select claims and re-voice them, citing claim IDs.

Based on: plans/260814-claim-graph-briefing/spec.md Section 2
Owner approval for the document-structure change: DECISIONS.md Decision 023

Two schema constraints are load-bearing and must not be "tidied" away:

1. The FULL schema ships in V1, including the optional ``market_context``.
   The Strategist Brief (V2) needs it populated from day one so that V2 is
   purely additive. Removing it would silently break that plan.

2. Claude structured outputs reject recursive schemas, numeric bounds and
   string-length bounds. Bounds are therefore declared here for client-side
   pydantic validation and stripped from the wire schema by
   ``api_json_schema()``. Prefer ``Literal``/enum over numeric ranges where a
   field has a small fixed domain, since enums survive the strip.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GRAPH_VERSION = "1"

# Claim-count bounds. The spec targets ~12-15 claims; the validator accepts
# 8-18 so a thin or unusually rich corpus is not failed for being honest.
MIN_CLAIMS = 8
MAX_CLAIMS = 18

ConfidenceGrade = Literal[1, 2, 3, 4, 5]
Severity = Literal[1, 2, 3, 4, 5]
EvidenceStatus = Literal["all_sources", "multi_source", "one_source", "conflicted"]
ThesisConfidence = Literal["solid", "usable", "thin"]
SourceRole = Literal["backbone", "confirmation", "color", "lead"]
StoryGoodType = Literal["scene", "character", "number", "moment", "quote"]


class _Base(BaseModel):
    """Shared config: reject unknown fields so drift surfaces as a failure."""

    model_config = ConfigDict(extra="forbid")


class MarketContext(_Base):
    """Strategist-lens context (spec Section 2, 2026-08-14 addition).

    Populated only when the sources support it. Outside knowledge must be
    flagged as context and never presented as evidence from the input - the
    same law as Truth Lab's Market rung.
    """

    who_else_serves_this: Optional[str] = None
    supply_vs_demand: Optional[str] = None
    based_on: list[str] = Field(default_factory=list)


class EvidenceRef(_Base):
    """A pointer from a claim back into the source ledger."""

    source_id: str
    quote_ref: Optional[str] = None
    timestamp: Optional[str] = None


class Confidence(_Base):
    grade: ConfidenceGrade
    reason: str


class Claim(_Base):
    """One claim on the argument spine, with its receipts attached.

    Multiple key points restating the same thing are EVIDENCE for one claim,
    not separate claims.
    """

    id: str
    title: str
    what_sources_say: str
    pushback: Optional[str] = None
    my_read: Optional[str] = None
    say_it_like: str
    confidence: Confidence
    evidence_status: EvidenceStatus
    evidence: list[EvidenceRef] = Field(default_factory=list)
    story_goods: list[str] = Field(default_factory=list)
    spine_order: int
    tags: list[str] = Field(default_factory=list)
    market_context: Optional[MarketContext] = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v.startswith("CLM_"):
            raise ValueError(f"claim id must start with 'CLM_': {v}")
        return v


class StoryGood(_Base):
    """Concrete, visualizable texture for the script layer (spec Section 2.1).

    Story goods must quote or tightly paraphrase the ledger. No invented detail.
    """

    id: str
    type: StoryGoodType
    text: str
    source_id: str
    claim_ids: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v.startswith("STG_"):
            raise ValueError(f"story good id must start with 'STG_': {v}")
        return v


class Hole(_Base):
    """Missing evidence, attached where it would sit. Gaps are not a section."""

    id: str
    attached_to: str  # a claim id, or the literal "thesis"
    missing: str
    hurts_because: str
    severity: Severity
    how_to_fill: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v.startswith("HOLE_"):
            raise ValueError(f"hole id must start with 'HOLE_': {v}")
        return v


class Thesis(_Base):
    text: str
    confidence: ThesisConfidence
    based_on: list[str] = Field(default_factory=list)


class Ground(_Base):
    """The 'if someone challenges you' seed."""

    claim_id: str
    why: str


class RankedSource(_Base):
    source_id: str
    role: SourceRole
    note: Optional[str] = None


class ClaimGraph(_Base):
    """The canonical graph. Every document derives from this."""

    graph_version: str = GRAPH_VERSION
    job_id: str
    topic: str
    thesis: Thesis
    claims: list[Claim] = Field(default_factory=list)
    story_goods: list[StoryGood] = Field(default_factory=list)
    holes: list[Hole] = Field(default_factory=list)
    weakest_ground: Optional[Ground] = None
    strongest_ground: Optional[Ground] = None
    sources_ranked: list[RankedSource] = Field(default_factory=list)
    market_context: Optional[MarketContext] = None

    # -- structural invariants -------------------------------------------------

    @model_validator(mode="after")
    def _check_claim_count(self) -> "ClaimGraph":
        if not MIN_CLAIMS <= len(self.claims) <= MAX_CLAIMS:
            raise ValueError(
                f"claim count {len(self.claims)} outside {MIN_CLAIMS}-{MAX_CLAIMS}"
            )
        return self

    @model_validator(mode="after")
    def _check_unique_ids(self) -> "ClaimGraph":
        for label, ids in (
            ("claim", [c.id for c in self.claims]),
            ("story good", [s.id for s in self.story_goods]),
            ("hole", [h.id for h in self.holes]),
        ):
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"duplicate {label} ids: {sorted(dupes)}")
        return self

    @model_validator(mode="after")
    def _check_refs_resolve(self) -> "ClaimGraph":
        claim_ids = {c.id for c in self.claims}
        story_ids = {s.id for s in self.story_goods}

        for claim in self.claims:
            for ref in claim.story_goods:
                if ref not in story_ids:
                    raise ValueError(f"{claim.id} references unknown story good {ref}")

        # No orphan story goods: each must be reachable from at least one claim.
        for story in self.story_goods:
            if not story.claim_ids:
                raise ValueError(f"orphan story good {story.id}: no claim_ids")
            for ref in story.claim_ids:
                if ref not in claim_ids:
                    raise ValueError(f"{story.id} references unknown claim {ref}")

        # Every hole attaches to a real claim, or to the thesis.
        for hole in self.holes:
            if hole.attached_to != "thesis" and hole.attached_to not in claim_ids:
                raise ValueError(
                    f"{hole.id} attached to unknown claim {hole.attached_to}"
                )

        for label, ground in (
            ("weakest_ground", self.weakest_ground),
            ("strongest_ground", self.strongest_ground),
        ):
            if ground and ground.claim_id not in claim_ids:
                raise ValueError(f"{label} references unknown claim {ground.claim_id}")

        for ref in self.thesis.based_on:
            if ref not in claim_ids:
                raise ValueError(f"thesis based_on references unknown claim {ref}")

        return self

    @model_validator(mode="after")
    def _check_spine(self) -> "ClaimGraph":
        orders = sorted(c.spine_order for c in self.claims)
        if len(set(orders)) != len(orders):
            raise ValueError(f"duplicate spine_order values: {orders}")
        return self

    # -- ledger-dependent invariant -------------------------------------------

    def validate_against_ledger(self, known_source_ids: set[str]) -> list[str]:
        """Check every evidence ref resolves to a real source.

        Kept separate from the pydantic validators because it needs the source
        ledger, which the model itself does not carry.

        Args:
            known_source_ids: source_ids present in the job's source ledger.

        Returns:
            List of human-readable problems. Empty means the graph is clean.
        """
        problems: list[str] = []

        for claim in self.claims:
            if not claim.evidence:
                problems.append(f"{claim.id} has no evidence")
            for ref in claim.evidence:
                if ref.source_id not in known_source_ids:
                    problems.append(
                        f"{claim.id} cites unknown source {ref.source_id}"
                    )

        for story in self.story_goods:
            if story.source_id not in known_source_ids:
                problems.append(f"{story.id} cites unknown source {story.source_id}")

        for ranked in self.sources_ranked:
            if ranked.source_id not in known_source_ids:
                problems.append(
                    f"sources_ranked cites unknown source {ranked.source_id}"
                )

        return problems

    def claims_in_spine_order(self) -> list[Claim]:
        return sorted(self.claims, key=lambda c: c.spine_order)

    def holes_for(self, claim_id: str) -> list[Hole]:
        return [h for h in self.holes if h.attached_to == claim_id]


# -----------------------------------------------------------------------------
# Wire schema
# -----------------------------------------------------------------------------

# Keywords Claude structured outputs reject. Bounds stay on the pydantic models
# for client-side validation and are stripped here.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "format",
        "default",
    }
)


# Optional string fields. On the wire these are plain (non-nullable) strings
# and an empty string means "absent"; normalize_wire_payload turns "" back into
# None before validation. See _collapse_scalar_nullable for why.
OPTIONAL_STRING_FIELDS = frozenset(
    {
        "pushback",
        "my_read",
        "quote_ref",
        "timestamp",
        "how_to_fill",
        "note",
        "who_else_serves_this",
        "supply_vs_demand",
    }
)

def _collapse_nullable(node: dict) -> dict:
    """Rewrite ``anyOf [T, null]`` as bare ``T``.

    Nullable unions are the single most expensive construct in the compiled
    grammar, and this was measured against the API rather than guessed: 40
    plain string properties compile fine, 20 nullable ones are rejected, and
    this schema compiles only at zero nullable branches. Optionality therefore
    cannot be expressed as nullability on the wire at all.

    It is preserved instead by convention, which normalize_wire_payload
    reverses: optional strings arrive as "" and become None, and a
    market_context whose fields are all empty becomes None. Everything the
    model must always supply is simply required.
    """
    branches = node.get("anyOf")
    if not isinstance(branches, list) or len(branches) != 2:
        return node

    non_null = [b for b in branches if b.get("type") != "null"]
    has_null = any(b.get("type") == "null" for b in branches)
    if not has_null or len(non_null) != 1:
        return node

    collapsed = {k: v for k, v in node.items() if k != "anyOf"}
    collapsed.update(non_null[0])
    return collapsed


def _is_blank_market_context(value: Any) -> bool:
    """True when a market_context object carries no actual content."""
    if not isinstance(value, dict):
        return False
    return not any(
        str(value.get(field) or "").strip()
        for field in ("who_else_serves_this", "supply_vs_demand")
    )


def normalize_wire_payload(node: Any) -> Any:
    """Turn the wire form back into the model's form.

    The wire schema has no nullable branches (see _collapse_nullable), so
    absence is encoded as emptiness. This reverses that, keeping "no pushback"
    and "no judgment offered" distinguishable from a field the model filled in.
    """
    if isinstance(node, list):
        return [normalize_wire_payload(n) for n in node]
    if not isinstance(node, dict):
        return node

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in OPTIONAL_STRING_FIELDS and isinstance(value, str) and not value.strip():
            out[key] = None
        elif key == "market_context" and _is_blank_market_context(value):
            out[key] = None
        else:
            out[key] = normalize_wire_payload(value)
    return out


def _sanitize(node: Any) -> Any:
    """Strip unsupported keywords, force additionalProperties, require all keys.

    Marking every property required is not pedantry. Structured outputs compile
    the schema into a grammar, and an object with optional properties forces
    that grammar to accept every subset of its keys. Across this many nested
    objects the combinations multiply until the API rejects the request with
    "the compiled grammar is too large" - which is exactly what happened on the
    first fixture run.

    Requiring every key makes the grammar a single fixed shape. Optionality is
    preserved by nullability instead: fields that may be absent are already
    ``anyOf [T, null]``, so the model emits null rather than omitting the key,
    and pydantic still accepts a missing key from any other producer.
    """
    if isinstance(node, list):
        return [_sanitize(n) for n in node]
    if not isinstance(node, dict):
        return node

    out = {k: _sanitize(v) for k, v in node.items() if k not in _UNSUPPORTED_SCHEMA_KEYS}
    out = _collapse_nullable(out)
    if out.get("type") == "object" or "properties" in out:
        out["additionalProperties"] = False
        if "properties" in out:
            out["required"] = list(out["properties"].keys())
    return out


def api_json_schema() -> dict:
    """JSON Schema for the distillation call's structured output.

    Pydantic emits ``$defs`` + ``$ref``, which structured outputs support.
    Recursion is not present in this schema and must not be introduced.
    """
    return _sanitize(ClaimGraph.model_json_schema())
