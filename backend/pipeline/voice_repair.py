"""Voice repair - fix lint-offending sentences with pairs applied by code.

Prompting alone does not converge on the voice laws: across repeated
distillation runs the same document ranged from 3.3 to 7.1 source-openers per
thousand words, and banned vocabulary kept reappearing in ones and twos. The
repair pass closes that gap mechanically.

The law here is the owner's own (TIC-PASS doctrine): a model NEVER re-emits a
document to edit it. It proposes old->new pairs for the offending sentences
only; code applies them, verifies each pair landed, and re-lints. Re-emission
drops content, leaks editor notes, and logs changes it did not make - proven
three ways on 2026-08-15.
"""

import re
from typing import Callable, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from backend.models.claim_graph import ClaimGraph
from backend.pipeline.style_enforcer import (
    RESEARCH_REGISTER,
    TIC_PATTERNS,
    _SOURCE_OPENER,
    find_consensus_violations,
)

# One repair round only. If the document still fails after that, it ships
# with warnings rather than looping cost into a document nobody approved.
MAX_REPAIR_ROUNDS = 1

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class VoiceEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old: str
    new: str


class VoiceEdits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edits: list[VoiceEdit] = Field(default_factory=list)


REPAIR_SYSTEM = """You fix single sentences that broke a house voice rule. You return each sentence rewritten, keeping every fact intact.

Rules for every rewrite:
- Keep ALL facts, names and numbers. Change only the framing.
- Sentences must not OPEN with a source reference ("One source says", "Both
  essays", "A separate article"). Say the fact first; if the speaker matters,
  they trail the fact: "..., and one of the essayists admits that outright."
- A sentence flagged as narrating agreement without content must be rewritten
  to lead with WHAT is claimed, with the agreement as a short trailing clause,
  or deleted outright (see the deletion rule below).
- No research-essay words: corpus, posits, corroborates, testimony,
  articulates, underscores.
- No em-dashes. No "not just X, it's Y". No internal IDs.
- Plain spoken English, the way a person explains something to a friend.

Return the rewrites as edits. `old` must be the sentence EXACTLY as given,
byte for byte. `new` is your rewrite. One special case: when a flagged
sentence carries no information worth keeping (pure agreement-talk with no
facts in it), DELETE it by returning `new` as an empty string. Deleting a
contentless sentence is better than rewording it. Never merge sentences and
never add new ones."""


def _offending_sentences(text: str) -> list[tuple[str, str]]:
    """Find sentences in one prose field that break a voice law.

    Returns (sentence, reason) pairs. Only patterns that are hard lint errors
    are collected; advisories are not repaired.
    """
    found: list[tuple[str, str]] = []
    for sentence in _SENTENCE_SPLIT.split(text):
        stripped = sentence.strip()
        if len(stripped) < 15:
            continue
        if _SOURCE_OPENER.match(stripped) or _SOURCE_OPENER.search(f". {stripped}"):
            found.append((stripped, "opens with a source reference"))
            continue

        for pattern, label in RESEARCH_REGISTER + TIC_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                found.append((stripped, f"contains banned pattern: {label}"))
                break
    return found


def _prose_fields(graph: ClaimGraph) -> list[tuple[str, Callable[[str], None]]]:
    """Every prose field the Briefing renders from, with a setter for each."""
    fields: list[tuple[str, Callable[[str], None]]] = []

    def make_setter(obj: object, attr: str) -> Callable[[str], None]:
        return lambda value: setattr(obj, attr, value)

    fields.append((graph.thesis.text, make_setter(graph.thesis, "text")))
    for section in graph.sections:
        fields.append((section.title, make_setter(section, "title")))
        fields.append((section.body, make_setter(section, "body")))
    for noticing in graph.noticings:
        fields.append((noticing.text, make_setter(noticing, "text")))
    if graph.landscape:
        fields.append(
            (graph.landscape.everyone_does, make_setter(graph.landscape, "everyone_does"))
        )
        fields.append(
            (graph.landscape.nobody_has, make_setter(graph.landscape, "nobody_has"))
        )
    for claim in graph.claims:
        # Titles feed the out-loud closer; bodies of claims are not rendered
        # in Shape B but stay clean for the other projections.
        fields.append((claim.title, make_setter(claim, "title")))
    for hole in graph.holes:
        fields.append((hole.missing, make_setter(hole, "missing")))
        fields.append((hole.hurts_because, make_setter(hole, "hurts_because")))
        if hole.how_to_fill:
            fields.append((hole.how_to_fill, make_setter(hole, "how_to_fill")))
    return fields


def repair_voice(
    job_id: str,
    graph: ClaimGraph,
    model: Optional[str] = None,
) -> tuple[ClaimGraph, dict]:
    """Repair voice-law violations in the graph's prose fields, in place.

    Collects every offending sentence across the fields the Briefing renders
    from, asks the model for old->new pairs, and applies them in code. A pair
    whose `old` is not found verbatim is skipped and counted - never fuzzily
    matched, never re-asked.

    Args:
        job_id: For logging.
        graph: The full graph (telling layer included). Mutated in place.
        model: Override for the repair call's model.

    Returns:
        Tuple of (graph, stats dict with counts and usage).
    """
    from backend.integrations.anthropic_client import get_anthropic_client

    offenders: list[tuple[str, str]] = []
    for text, _ in _prose_fields(graph):
        offenders.extend(_offending_sentences(text))
        for sentence in find_consensus_violations(text):
            offenders.append(
                (sentence,
                 "agreement-only sentence leading a paragraph or stacked in a "
                 "run; state the content instead, or delete it")
            )

    # De-duplicate while keeping order; the same stock sentence can appear
    # in more than one field.
    seen: set[str] = set()
    unique = [(s, r) for s, r in offenders if not (s in seen or seen.add(s))]

    stats = {"offenders": len(unique), "applied": 0, "skipped": 0, "cost": 0.0}
    if not unique:
        return graph, stats

    logger.info(f"[{job_id}] Voice repair: {len(unique)} offending sentences")

    listing = "\n\n".join(
        f"SENTENCE: {sentence}\nPROBLEM: {reason}" for sentence, reason in unique
    )
    schema = VoiceEdits.model_json_schema()
    schema["additionalProperties"] = False
    for definition in schema.get("$defs", {}).values():
        definition["additionalProperties"] = False
        definition["required"] = list(definition.get("properties", {}))
    schema["required"] = list(schema.get("properties", {}))

    client = get_anthropic_client(model=model)
    data, usage = client.generate_structured(
        prompt=f"Fix these sentences.\n\n{listing}",
        schema=schema,
        system=REPAIR_SYSTEM,
        max_tokens=8_000,
        model=model,
    )
    stats["cost"] = usage.get("cost", 0.0)

    edits = VoiceEdits.model_validate(data).edits
    fields = _prose_fields(graph)

    for edit in edits:
        is_deletion = not edit.new.strip()
        if edit.old == edit.new:
            stats["skipped"] += 1
            continue
        # The cure must not be a new disease. (A deletion cannot offend.)
        if not is_deletion and _offending_sentences(edit.new):
            stats["skipped"] += 1
            logger.warning(f"[{job_id}] Repair rewrite still offends; skipped")
            continue

        applied = False
        for text, setter in fields:
            if edit.old in text:
                updated = text.replace(edit.old, edit.new if not is_deletion else "")
                if is_deletion:
                    updated = re.sub(r"[ \t]{2,}", " ", updated).strip()
                setter(updated)
                applied = True
                break
        if applied:
            stats["applied"] += 1
            # Refresh views after a mutation so later pairs see current text.
            fields = _prose_fields(graph)
        else:
            stats["skipped"] += 1
            logger.warning(
                f"[{job_id}] Repair pair not found verbatim; skipped: "
                f"{edit.old[:60]!r}"
            )

    logger.info(
        f"[{job_id}] Voice repair applied {stats['applied']}/{len(edits)} pairs "
        f"(${stats['cost']:.3f})"
    )
    return graph, stats
