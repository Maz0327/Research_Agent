"""The Research Briefing - the canonical human reading surface.

Format locked as Decision 025 (2026-08-18) after two-topic validation. The
canonical artifact is this JSON; HTML is rendered from it by deterministic
code, and Markdown or Drive exports are lossy secondary renders.

Nine sections, in order:

1. The Read - the argument told once, linear, written from RAW source text.
2. The Players - cast cards; a name in 2+ sections gets one.
3. The Places - the geography that matters to this story, split out of the
   cast; on the Packer run five of fourteen "players" were places, each with
   a biography.
4. The Record - dated chronology, every entry cited, each with context.
5. The Files - the lossless layer, facts merged by subject, coverage checked
   mechanically against the harvest inventory.
6. Disputed & Uncertain - holders, a code-computed status chip, both cases.
7. Details & Anecdotes - the texture bin, so small material cannot vanish.
8. Info Gaps - what the corpus lacks, phrased as go-get instructions.
9. Source Trail - each source's one unique contribution, linked to the vault.

The division of labour is the point (work order Section J): models write
content fields, code decides structure, counts, chips, coverage, and
rendering. Every field here is one or the other, and the docstrings say which.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BRIEFING_VERSION = "1"

# Chip vocabulary (D-025). The label is what a reader sees; the tone is what
# the renderer colours it with. Both are computed by code from provenance
# arithmetic - counts, not judgment.
ChipTone = Literal["solid", "contested", "network"]

CHIP_TONES: dict[str, ChipTone] = {
    "established": "solid",
    "documented": "solid",
    "contested": "contested",
    "single source": "network",
    "unverifiable": "network",
    "belief migration": "network",
    "single network on interpretation": "network",
}


class _Base(BaseModel):
    """Shared config: reject unknown fields so drift surfaces as a failure."""

    model_config = ConfigDict(extra="forbid")


class Chip(_Base):
    """An evidence-status badge. Code computes both fields; no model picks one."""

    label: str
    tone: ChipTone = "solid"

    @model_validator(mode="after")
    def _tone_matches_label(self) -> "Chip":
        expected = CHIP_TONES.get(self.label.lower())
        if expected is None:
            raise ValueError(
                f"chip label {self.label!r} is outside the D-025 vocabulary: "
                f"{sorted(CHIP_TONES)}"
            )
        object.__setattr__(self, "tone", expected)
        return self


class BriefingMeta(_Base):
    """The masthead strip. Every number is counted by code."""

    source_count: int
    independent_source_count: int
    raw_words: int
    quote_verification_rate: float | None = None
    confidence: str | None = None
    generated_on: str | None = None


class ReadParagraph(_Base):
    """One paragraph of Section 1. `label` is the bold lead-in, when it has one.

    Written by the Read pass (LLM) from raw source text.
    """

    label: str | None = None
    text: str


class Read(_Base):
    """Section 1. The only section built to be read top to bottom."""

    lede: str
    paragraphs: list[ReadParagraph] = Field(default_factory=list)


class Player(_Base):
    """Section 2 card. Code decides who qualifies; the model writes the card."""

    name: str
    role: str
    body: str
    source_ids: list[str] = Field(default_factory=list)


class Place(_Base):
    """Section 3 card. Code decides which qualifying names are places; the
    model writes the card, and only for places that matter to this story.

    Optional on the document: Briefings stored before the section existed
    validate with an empty list.
    """

    name: str
    line: str
    body: str
    source_ids: list[str] = Field(default_factory=list)


class RecordEntry(_Base):
    """Section 4 entry. Code places and sorts it; the model writes `context`."""

    when: str
    what: str
    source_ids: list[str] = Field(default_factory=list)
    context: str | None = None
    sort_key: float | None = None


class File(_Base):
    """Section 5 subject file. Code assigns the facts and computes the chips."""

    title: str
    chips: list[Chip] = Field(default_factory=list)
    body: str
    source_ids: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)


class DisputeSide(_Base):
    """One side of a dispute, written by the model from assigned evidence."""

    heading: str
    text: str
    source_ids: list[str] = Field(default_factory=list)


class Dispute(_Base):
    """Section 6 entry. Code selects the dispute and computes the chip."""

    claim: str
    holders: str
    chip: Chip
    case_for: DisputeSide
    case_against: DisputeSide


class Anecdote(_Base):
    """Section 7 item. Code selects it; the model writes the context blurb."""

    text: str
    source_ids: list[str] = Field(default_factory=list)
    context: str | None = None


class InfoGap(_Base):
    """Section 8 item. A pure code transform of the gap-analysis output."""

    question: str
    why: str
    go_get: str


class SourceTrailEntry(_Base):
    """Section 9 row. Everything but `contribution` is code."""

    source_id: str
    title: str
    kind: str | None = None
    year: str | None = None
    creator: str | None = None
    contribution: str | None = None
    vault_anchor: str | None = None
    duplicate_of: str | None = None
    accessible: bool = True
    note: str | None = None


class CorpusBalance(_Base):
    """Header advisory (work order I.24). Skew may be deliberate; never hidden."""

    domains: dict[str, int] = Field(default_factory=dict)
    date_range: str | None = None
    network_note: str | None = None
    stance_counts: dict[str, int] = Field(default_factory=dict)


class Addendum(_Base):
    """A dated update note (work order I.26/I.29b).

    Renders ABOVE the document rather than being folded into it: the owner
    reads the delta, not the whole Briefing again.
    """

    checked_on: str
    covers_since: str
    headline: str
    has_updates: bool = False
    new_items: list[dict] = Field(default_factory=list)
    changed_sections: list[str] = Field(default_factory=list)


class Briefing(_Base):
    """The whole document. Assembled by code from the generation passes."""

    briefing_version: str = BRIEFING_VERSION
    job_id: str
    topic: str
    meta: BriefingMeta
    read: Read
    players: list[Player] = Field(default_factory=list)
    places: list[Place] = Field(default_factory=list)
    record: list[RecordEntry] = Field(default_factory=list)
    files: list[File] = Field(default_factory=list)
    disputes: list[Dispute] = Field(default_factory=list)
    anecdotes: list[Anecdote] = Field(default_factory=list)
    info_gaps: list[InfoGap] = Field(default_factory=list)
    source_trail: list[SourceTrailEntry] = Field(default_factory=list)
    corpus_balance: CorpusBalance | None = None
    addendum: Addendum | None = None

    @model_validator(mode="after")
    def _read_is_present(self) -> "Briefing":
        """Section 1 is the document's spine; an empty one is a failed build."""
        if not self.read.lede.strip() or not self.read.paragraphs:
            raise ValueError("The Read is empty; the Briefing has no Section 1")
        return self

    @model_validator(mode="after")
    def _citations_resolve(self) -> "Briefing":
        """Every cited source ID must exist in the Source Trail."""
        known = {entry.source_id for entry in self.source_trail}
        if not known:
            return self

        cited: set[str] = set()
        for player in self.players:
            cited.update(player.source_ids)
        for place in self.places:
            cited.update(place.source_ids)
        for entry in self.record:
            cited.update(entry.source_ids)
        for file in self.files:
            cited.update(file.source_ids)
        for dispute in self.disputes:
            cited.update(dispute.case_for.source_ids)
            cited.update(dispute.case_against.source_ids)
        for anecdote in self.anecdotes:
            cited.update(anecdote.source_ids)

        unknown = sorted(cited - known)
        if unknown:
            raise ValueError(f"citations reference sources not in the trail: {unknown}")
        return self

    @model_validator(mode="after")
    def _duplicates_point_somewhere(self) -> "Briefing":
        """A source marked as a republication must name the source it copies."""
        known = {entry.source_id for entry in self.source_trail}
        for entry in self.source_trail:
            if entry.duplicate_of and entry.duplicate_of not in known:
                raise ValueError(
                    f"{entry.source_id} duplicates {entry.duplicate_of}, "
                    f"which is not in the trail"
                )
        return self


def chip(label: str) -> Chip:
    """Build a chip, with its tone resolved from the vocabulary.

    Args:
        label: One of the D-025 chip labels.

    Returns:
        A Chip whose tone matches its label.

    Raises:
        ValueError: If the label is outside the vocabulary.
    """
    return Chip(label=label)


# ---------------------------------------------------------------------------
# Wire schemas for the generation passes.
#
# These are what actually reach the API, and they are deliberately small and
# flat. The measured grammar ceiling applies (claim_graph._collapse_nullable):
# ZERO nullable branches, `additionalProperties: false`, every property
# required. Absence is encoded as an empty string, never as null.
#
# The full Briefing schema above is never sent anywhere: code assembles the
# document from these pass outputs (work order Section J, pass 8).
# ---------------------------------------------------------------------------


def _object(properties: dict) -> dict:
    """Wrap properties as a strict object schema with everything required.

    Args:
        properties: JSON Schema property definitions.

    Returns:
        An object schema the structured-outputs grammar accepts.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def _array_of(item_properties: dict) -> dict:
    """An array whose items are strict objects.

    Args:
        item_properties: JSON Schema property definitions for one item.

    Returns:
        An array schema.
    """
    return {"type": "array", "items": _object(item_properties)}


_STRING = {"type": "string"}
_STRINGS = {"type": "array", "items": {"type": "string"}}
_INTEGER = {"type": "integer"}


# Pass 1: The Read. Input is raw source text; output is plain prose.
READ_SCHEMA = _object(
    {
        "lede": _STRING,
        "paragraphs": _array_of({"label": _STRING, "text": _STRING}),
    }
)

# Pass 2: Subject map. The one grouping job code cannot do (measured:
# embeddings rank restatements, not connections).
SUBJECT_MAP_SCHEMA = _object(
    {
        "subjects": _array_of({"title": _STRING, "fact_ids": _STRINGS}),
        "anecdote_fact_ids": _STRINGS,
    }
)

# Pass 3: one file, written from its assigned facts and their raw paragraphs.
FILE_SCHEMA = _object({"title": _STRING, "body": _STRING})

# Pass 4: one dispute's two cases. Code selected the dispute and computed the chip.
DISPUTE_SCHEMA = _object(
    {
        "for_heading": _STRING,
        "for_text": _STRING,
        "against_heading": _STRING,
        "against_text": _STRING,
    }
)

# Pass 5: context blurbs for dated entries, addressed by position so the model
# cannot invent or move a date.
BLURBS_SCHEMA = _object(
    {"blurbs": _array_of({"index": _INTEGER, "context": _STRING})}
)

# Pass 6: cards for the names code decided qualify.
PLAYERS_SCHEMA = _object(
    {"players": _array_of({"name": _STRING, "role": _STRING, "body": _STRING})}
)

# Pass 6b: cards for the qualifying names code classified as places. The model
# may return fewer cards than names it was given: whether a place matters to
# this story is a reading judgement, so the backdrop rule lives in the prompt.
PLACES_SCHEMA = _object(
    {"places": _array_of({"name": _STRING, "line": _STRING, "body": _STRING})}
)

# Pass 7: one line per source, saying what only that source contributes.
CONTRIBUTIONS_SCHEMA = _object(
    {"contributions": _array_of({"source_id": _STRING, "contribution": _STRING})}
)
