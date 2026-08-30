"""Model-seat orchestration for the post-Read semantic advisory.

Wires the advisory model seats (decomposition, relevance, span localization,
referees, corpus relation) around the deterministic spine in
``backend.pipeline.semantic_advisory``. Ported from the validated v3
experiment (scratchpad/build_semantic_labeling_v3.py at 246fbaa) under
decisions D-SEM-5..7 / ADR-013.

Contract: the model seats ADVISE; every downstream decision — evidence
identity, dedup, corpus polarity routing, sentence advisories, the report —
is made by code in the spine. The output is a report; it never gates, blocks,
or edits a Read, and never touches writer inputs.

Model seats are injected (``AdvisoryModel`` / ``Embedder``) so tests run
without network access; production adapters at the bottom wrap the shared
structured client and the DashScope embeddings endpoint.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from backend.pipeline.semantic_advisory import (
    assemble_advisory_report,
    cosine,
    deduplicate_evidence,
    evidence_identity,
    full_source_candidate_regions,
    normalized,
    route_corpus_relations,
    source_sentence_units,
)

EMBEDDING_MODEL = "qwen3.7-text-embedding"
TOP_PER_ROUTE = 10
CORPUS_SEMANTIC_TOP = 20
CORPUS_LEXICAL_TOP = 10

CLAIM_TYPES = (
    "DIRECT_SOURCE_CLAIM",
    "SOURCE_GROUNDED_INFERENCE",
    "WRITER_ANALYSIS",
    "CORPUS_META",
)
RELEVANCE_LABELS = ("DIRECTLY_RELEVANT", "PARTIALLY_RELEVANT", "NOT_RELEVANT", "UNCLEAR")
DIRECT_RESULTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "CONFLICT", "INSUFFICIENT_EVIDENCE")
INFERENCE_RESULTS = (
    "REASONABLE_INFERENCE",
    "OVERSTATED_PARTIAL",
    "DOES_NOT_FOLLOW",
    "INSUFFICIENT_PREMISES",
)
MISMATCH_DIMENSIONS = (
    "actor",
    "action_relationship",
    "object",
    "polarity",
    "time_status",
    "quantity",
    "certainty_modality",
    "attribution",
)

NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")

ADVISORY_SYSTEM_PROMPT = (
    "You are an advisory semantic-verification judge. Preserve exact wording "
    "strength, attribution, polarity, modality, quantity, and time. Similarity "
    "is not correctness. UNVERIFIED is not FALSE. Return only the requested "
    "structured result."
)


def actor_mask(text: str) -> str:
    """Mask capitalized name spans so retrieval can match on the event shape."""
    return NAME_PATTERN.sub("[P]", text)


def schema_object(properties: dict[str, Any]) -> dict[str, Any]:
    """Return a strict object schema accepted by the shared structured client."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


DECOMPOSITION_SCHEMA = schema_object(
    {
        "claims": {
            "type": "array",
            "minItems": 1,
            "items": schema_object(
                {
                    "type": {"type": "string", "enum": list(CLAIM_TYPES)},
                    "text": {"type": "string"},
                    "derived_from_indices": {"type": "array", "items": {"type": "integer"}},
                    "reason": {"type": "string"},
                }
            ),
        }
    }
)

RELEVANCE_SCHEMA = schema_object(
    {
        "judgments": {
            "type": "array",
            "items": schema_object(
                {
                    "fact_id": {"type": "string"},
                    "label": {"type": "string", "enum": list(RELEVANCE_LABELS)},
                    "reason": {"type": "string"},
                }
            ),
        }
    }
)

LOCALIZATION_SCHEMA = schema_object(
    {
        "status": {"type": "string", "enum": ["SPAN_FOUND", "NO_SUPPORTING_SPAN_FOUND"]},
        "start_sentence_index": {"type": ["integer", "null"]},
        "end_sentence_index": {"type": ["integer", "null"]},
        "reason": {"type": "string"},
    }
)

DIRECT_REFEREE_SCHEMA = schema_object(
    {
        "status": {"type": "string", "enum": list(DIRECT_RESULTS)},
        "mismatch_dimensions": {
            "type": "array",
            "items": {"type": "string", "enum": list(MISMATCH_DIMENSIONS)},
        },
        "conflicting_evidence": {"type": "boolean"},
        "evidence_assessments": {
            "type": "array",
            "items": schema_object(
                {
                    "evidence_id": {"type": "string"},
                    "relation": {
                        "type": "string",
                        "enum": ["SUPPORTS", "PARTIAL", "CONFLICT", "IRRELEVANT", "UNCLEAR"],
                    },
                    "reason": {"type": "string"},
                }
            ),
        },
        "reason": {"type": "string"},
    }
)

INFERENCE_REFEREE_SCHEMA = schema_object(
    {
        "status": {"type": "string", "enum": list(INFERENCE_RESULTS)},
        "premise_assessments": {
            "type": "array",
            "items": schema_object(
                {
                    "claim_id": {"type": "string"},
                    "established": {"type": "boolean"},
                    "reason": {"type": "string"},
                }
            ),
        },
        "reason": {"type": "string"},
    }
)

CORPUS_RELATION_SCHEMA = schema_object(
    {
        "candidate_assessments": {
            "type": "array",
            "items": schema_object(
                {
                    "candidate_id": {"type": "string"},
                    "relation": {"type": "string"},
                    "reason": {"type": "string"},
                }
            ),
        },
        "reason": {"type": "string"},
    }
)


class AdvisoryModel(Protocol):
    """A structured advisory model seat. Implementations must be side-effect free."""

    def generate(self, stage: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a dict conforming to ``schema`` for the given stage prompt."""
        ...


class Embedder(Protocol):
    """Batch text embedder returning one vector per input text."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors, one per text, in order."""
        ...


NEGATIVE_CORPUS_PATTERNS: tuple[tuple[re.Pattern[str], Callable[[re.Match[str]], str]], ...] = (
    (
        re.compile(r"^No supplied source (identifies|mentions|describes|contains) (.+?)\.?$"),
        lambda m: f"A supplied source {m.group(1)} {m.group(2)}.",
    ),
    (
        re.compile(r"^(?:The (?:pile|corpus|research|sources?) )contains? no (.+?)\.?$"),
        lambda m: f"The supplied research contains {m.group(1)}.",
    ),
    (
        re.compile(r"^None of the (?:supplied )?(?:sources?|research) (.+?)\.?$"),
        lambda m: f"At least one supplied source {m.group(1)}.",
    ),
)


def positive_proposition(claim_text: str) -> str | None:
    """Build the positive proposition a negative corpus claim denies.

    Pattern-based and deliberately conservative: an unrecognized claim shape
    returns None, and the corpus check reports CHECK_INCOMPLETE rather than
    guessing — honesty over coverage.
    """
    text = normalized(claim_text)
    for pattern, build in NEGATIVE_CORPUS_PATTERNS:
        match = pattern.match(text)
        if match:
            return build(match)
    return None


class SemanticAdvisoryRunner:
    """Runs the full post-Read semantic advisory over injected model seats."""

    def __init__(
        self,
        model: AdvisoryModel,
        embedder: Embedder,
        *,
        top_per_route: int = TOP_PER_ROUTE,
    ) -> None:
        self.model = model
        self.embedder = embedder
        self.top_per_route = top_per_route
        self._embedding_memo: dict[str, list[float]] = {}

    # ---- embeddings -----------------------------------------------------

    def _embed(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in self._embedding_memo]
        if missing:
            vectors = self.embedder.embed(missing)
            if len(vectors) != len(missing):
                raise RuntimeError("embedder returned wrong vector count")
            self._embedding_memo.update(zip(missing, vectors, strict=True))
        return [self._embedding_memo[t] for t in texts]

    # ---- stage 1: decomposition ----------------------------------------

    def decompose(self, sentence: dict[str, Any]) -> list[dict[str, Any]]:
        """Propose claim units for one Read sentence (model advises; code validates)."""
        prompt = f"""Decompose this finished Read sentence into the smallest meaningful,
independently verifiable claim units. Do not split mechanically at every
conjunction. Split only when propositions have independent truth conditions.

Allowed types only:
- DIRECT_SOURCE_CLAIM: directly reportable from source material
- SOURCE_GROUNDED_INFERENCE: a conclusion derived from other claim units
- WRITER_ANALYSIS: interpretation, synthesis, judgment, or analytical point
- CORPUS_META: a claim about what the supplied corpus contains or omits

Preserve actor, action, object, polarity, attribution, certainty/modality,
quantity, and time/status. Never strengthen the sentence. Attribution belongs
inside the claim. For each SOURCE_GROUNDED_INFERENCE, derived_from_indices must
contain the 1-based indices of its premise claim units. Other types must use an
empty list.

Sentence ID: {sentence['sentence_id']}
Sentence: {sentence['sentence']}"""
        result = self.model.generate("stage_1_decomposition", prompt, DECOMPOSITION_SCHEMA)
        proposals = result.get("claims")
        if not isinstance(proposals, list) or not proposals:
            raise RuntimeError(f"no claims proposed for {sentence['sentence_id']}")
        claims: list[dict[str, Any]] = []
        for index, proposal in enumerate(proposals, 1):
            claim_type = proposal.get("type")
            text = normalized(proposal.get("text") or "")
            links = proposal.get("derived_from_indices")
            if claim_type not in CLAIM_TYPES or not text or not isinstance(links, list):
                raise RuntimeError(f"invalid decomposition for {sentence['sentence_id']}")
            if claim_type == "SOURCE_GROUNDED_INFERENCE":
                if not links or any(
                    not isinstance(link, int) or link < 1 or link > len(proposals)
                    for link in links
                ):
                    raise RuntimeError(f"invalid premise links in {sentence['sentence_id']}")
            elif links:
                raise RuntimeError(f"non-inference has premise links in {sentence['sentence_id']}")
            claims.append(
                {
                    "claim_id": f"{sentence['sentence_id']}:C{index:02d}",
                    "type": claim_type,
                    "text": text,
                    "derived_from_claim_ids": [],
                    "system_reason": proposal.get("reason") or "",
                }
            )
        for index, proposal in enumerate(proposals):
            claims[index]["derived_from_claim_ids"] = [
                claims[premise_index - 1]["claim_id"]
                for premise_index in proposal["derived_from_indices"]
            ]
        return claims

    # ---- stage 2: broad retrieval --------------------------------------

    def retrieve(
        self,
        claim: dict[str, Any],
        inventory: list[dict[str, Any]],
        fact_vectors: list[list[float]],
    ) -> None:
        """High-recall candidate retrieval: exact + actor-masked query union."""
        exact = claim["text"]
        masked = actor_mask(exact)
        queries = [exact] + ([masked] if masked != exact else [])
        vectors = self._embed(queries)
        exact_vector = vectors[0]
        masked_vector = vectors[1] if len(vectors) > 1 else None
        exact_scores = [cosine(exact_vector, v) for v in fact_vectors]
        masked_scores = (
            [cosine(masked_vector, v) for v in fact_vectors] if masked_vector else []
        )
        exact_order = sorted(
            range(len(inventory)), key=lambda i: (-exact_scores[i], inventory[i]["fact_id"])
        )
        masked_order = (
            sorted(range(len(inventory)), key=lambda i: (-masked_scores[i], inventory[i]["fact_id"]))
            if masked_scores
            else []
        )
        exact_top = exact_order[: self.top_per_route]
        masked_top = masked_order[: self.top_per_route]
        exact_ranks = {i: rank for rank, i in enumerate(exact_top, 1)}
        masked_ranks = {i: rank for rank, i in enumerate(masked_top, 1)}
        union = sorted(
            set(exact_top) | set(masked_top),
            key=lambda i: (
                -max(exact_scores[i], masked_scores[i] if masked_scores else -2.0),
                inventory[i]["fact_id"],
            ),
        )
        candidates = []
        for union_rank, i in enumerate(union, 1):
            fact = inventory[i]
            retrieved_by = (
                "both"
                if i in exact_ranks and i in masked_ranks
                else ("exact" if i in exact_ranks else "actor_masked")
            )
            candidates.append(
                {
                    "fact_id": fact["fact_id"],
                    "source_id": fact["source_id"],
                    "fact_text": fact["text"],
                    "rank_exact": exact_ranks.get(i),
                    "rank_actor_masked": masked_ranks.get(i),
                    "retrieved_by": retrieved_by,
                    "best_embedding_score": round(
                        max(exact_scores[i], masked_scores[i] if masked_scores else -2.0), 6
                    ),
                    "union_rank": union_rank,
                    "system_relevance": None,
                    "evidence_proposal": None,
                }
            )
        claim["retrieval"] = {
            "exact_query": exact,
            "actor_masked_query": masked if masked != exact else None,
            "top_per_route": self.top_per_route,
            "similarity_threshold": None,
            "deduplication": "exact FACT_ID only",
            "candidates": candidates,
        }

    # ---- stage 3: relevance --------------------------------------------

    def judge_relevance(self, claim: dict[str, Any]) -> None:
        """Model advises relevance per candidate; contradictions are relevant."""
        candidates = claim["retrieval"]["candidates"]
        if not candidates:
            return
        facts = "\n".join(f"{c['fact_id']}: {c['fact_text']}" for c in candidates)
        prompt = f"""Judge claim-to-fact RELEVANCE only. Do not judge whether the
harvested fact is accurately sourced and do not judge whether it supports or
contradicts the claim. A contradiction is directly relevant.

Question: Assuming this harvested fact is accurately sourced, does it
materially help evaluate this specific claim?

Labels: DIRECTLY_RELEVANT, PARTIALLY_RELEVANT, NOT_RELEVANT, UNCLEAR.
Compare actor, action/relationship, object, event/location, time/status,
quantity, polarity, certainty, and attribution. Return every fact exactly once.

Claim ID: {claim['claim_id']}
Claim: {claim['text']}

Candidates:
{facts}"""
        result = self.model.generate("stage_3_relevance", prompt, RELEVANCE_SCHEMA)
        judgments = result.get("judgments")
        expected = {c["fact_id"] for c in candidates}
        if (
            not isinstance(judgments, list)
            or {j.get("fact_id") for j in judgments} != expected
            or len(judgments) != len(expected)
        ):
            raise RuntimeError(f"incomplete relevance response for {claim['claim_id']}")
        by_id = {j["fact_id"]: j for j in judgments}
        for candidate in candidates:
            judgment = by_id[candidate["fact_id"]]
            if judgment.get("label") not in RELEVANCE_LABELS:
                raise RuntimeError(f"invalid relevance label for {candidate['fact_id']}")
            candidate["system_relevance"] = {
                "label": judgment["label"],
                "reason": judgment.get("reason") or "",
            }

    # ---- stage 4: full-source localization ------------------------------

    def localize(
        self,
        claim: dict[str, Any],
        candidate: dict[str, Any],
        source_text: str,
        units: list[dict[str, Any]],
        unit_vectors: list[list[float]],
    ) -> None:
        """Search the ENTIRE known source, then the model picks the minimal span."""
        fact_vector = self._embed([candidate["fact_text"]])[0]
        fact_tokens = set(candidate["fact_text"].lower().split())
        regions = full_source_candidate_regions(fact_tokens, fact_vector, units, unit_vectors)
        by_index = {u["sentence_index"]: u for u in units}
        region_indices = {
            i
            for r in regions
            for i in range(r["start_sentence_index"], r["end_sentence_index"] + 1)
        }
        rendered = []
        for region in regions:
            numbered = "\n".join(
                f"[{i}] {by_index[i]['text']}"
                for i in range(region["start_sentence_index"], region["end_sentence_index"] + 1)
            )
            rendered.append(
                f"{region['region_id']} (retrieved by {region['retrieved_by']}; similarity "
                f"rank is routing metadata only):\n{numbered}"
            )
        prompt = f"""Find the smallest contiguous 1-3 sentence raw-source span that
is sufficient to establish the harvested fact. The harvested fact is only a
routing aid. Code semantically searched every deterministic sentence unit in
the known source and also unioned lexical candidates for recall. Similarity and
lexical overlap are not correctness judgments. Select exact sentence indices
from one supplied candidate region. Expand
only for coreference, negation, attribution, certainty, time/status, or meaning
that depends on an adjacent sentence. If none of the regions establishes the
fact, return NO_SUPPORTING_SPAN_FOUND with null indices. Do not fabricate.

Read claim (context only): {claim['text']}
Harvested fact: {candidate['fact_text']}
Source ID: {candidate['source_id']}

Full-source candidate regions ({len(units)} source units searched):
{chr(10).join(rendered)}"""
        result = self.model.generate("stage_4_localization", prompt, LOCALIZATION_SCHEMA)

        def invalid(proposal: dict[str, Any]) -> bool:
            start = proposal.get("start_sentence_index")
            end = proposal.get("end_sentence_index")
            if proposal.get("status") != "SPAN_FOUND":
                return False
            return (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start not in region_indices
                or end not in region_indices
                or end < start
                or end - start > 2
            )

        if invalid(result):
            result = self.model.generate(
                "stage_4_localization_boundary_retry",
                prompt
                + "\n\nYour previous answer had invalid boundaries. Select start and end "
                "sentence indices from ONE candidate region, spanning at most 3 sentences, "
                "or return NO_SUPPORTING_SPAN_FOUND with null indices.",
                LOCALIZATION_SCHEMA,
            )
        if invalid(result):
            result = {"status": "NO_SUPPORTING_SPAN_FOUND", "reason": "invalid boundaries twice"}
        if result.get("status") == "NO_SUPPORTING_SPAN_FOUND":
            candidate["evidence_proposal"] = {
                "status": "NO_SUPPORTING_SPAN_FOUND",
                "search_scope": "entire_known_source",
                "full_source_units_searched": len(units),
                "system_reason": result.get("reason") or "",
            }
            return
        start_index, end_index = result["start_sentence_index"], result["end_sentence_index"]
        start_char = units[start_index]["start_char"]
        end_char = units[end_index]["end_char"]
        exact_text = source_text[start_char:end_char]
        proposal = {
            "status": "SPAN_FOUND",
            "search_scope": "entire_known_source",
            "full_source_units_searched": len(units),
            "source_id": candidate["source_id"],
            "exact_raw_text": exact_text,
            "start_char": start_char,
            "end_char": end_char,
            "start_sentence_index": start_index,
            "end_sentence_index": end_index,
            "source_sentence_count": end_index - start_index + 1,
            "word_count": len(exact_text.split()),
            "system_reason": result.get("reason") or "",
        }
        proposal["evidence_id"] = evidence_identity(proposal)
        candidate["evidence_proposal"] = proposal

    # ---- stages 6/7: referees ------------------------------------------

    def referee_direct(self, claim: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> None:
        """Advisory verdict on a direct claim vs its localized evidence."""
        evidence_ids = sorted(
            {
                c["evidence_proposal"]["evidence_id"]
                for c in claim["retrieval"]["candidates"]
                if c.get("evidence_proposal") and c["evidence_proposal"].get("status") == "SPAN_FOUND"
            }
        )
        if not evidence_ids:
            claim["direct_referee"] = {
                "system_result": {
                    "status": "INSUFFICIENT_EVIDENCE",
                    "mismatch_dimensions": [],
                    "conflicting_evidence": False,
                    "evidence_assessments": [],
                    "reason": "No localized supporting span survived routing and localization.",
                    "generation_mode": "deterministic_no_evidence",
                }
            }
            return
        rendered = "\n\n".join(
            f"Evidence {eid} ({evidence_by_id[eid]['source_id']}):\n{evidence_by_id[eid]['exact_raw_text']}"
            for eid in evidence_ids
        )
        prompt = f"""Compare this DIRECT_SOURCE_CLAIM against the localized raw
evidence. The evidence is authoritative; harvested facts were only routing
aids. Choose SUPPORTED, PARTIALLY_SUPPORTED, CONFLICT, or
INSUFFICIENT_EVIDENCE. INSUFFICIENT_EVIDENCE does not mean false. Preserve
disagreement between evidence objects; never majority-vote or pick a winner.
Assess actor, action/relationship, object, polarity, time/status, quantity,
certainty/modality, and attribution. If the claim itself attributes a statement,
analysis, or opinion to a source ("X says", "the analysis suggests"), judge whether
the evidence establishes that attribution: an accurately attributed statement is
SUPPORTED even though the underlying assertion is the source's own view. Reserve
PARTIALLY_SUPPORTED for claims where a material part of what the claim asserts is
not established — never for the mere presence of attributed or analytical content.
Return every evidence ID exactly once.

Claim ID: {claim['claim_id']}
Claim: {claim['text']}

{rendered}"""
        result = self.model.generate("stage_6_direct_referee", prompt, DIRECT_REFEREE_SCHEMA)
        if result.get("status") not in DIRECT_RESULTS:
            raise RuntimeError(f"invalid direct referee result for {claim['claim_id']}")
        assessments = result.get("evidence_assessments")
        if not isinstance(assessments, list) or {
            a.get("evidence_id") for a in assessments
        } != set(evidence_ids):
            raise RuntimeError(f"incomplete evidence assessments for {claim['claim_id']}")
        claim["direct_referee"] = {"system_result": {**result, "generation_mode": "advisory_model"}}

    def referee_inference(
        self, inference: dict[str, Any], claims_by_id: dict[str, dict[str, Any]]
    ) -> None:
        """Advisory verdict on whether a conclusion is earned from its premises."""
        premise_ids = inference["derived_from_claim_ids"]
        premises = [claims_by_id.get(cid) for cid in premise_ids]
        if any(p is None for p in premises):
            inference["inference_referee"] = {
                "system_result": {
                    "status": "INSUFFICIENT_PREMISES",
                    "reason": "One or more proposed premise links do not resolve.",
                    "premise_assessments": [],
                    "generation_mode": "deterministic_missing_premise_link",
                }
            }
            return
        blocks = []
        for premise in premises:
            referee = premise.get("direct_referee", {}).get("system_result", {})
            blocks.append(
                f"Premise {premise['claim_id']}: {premise['text']}\n"
                f"Direct result: {referee.get('status', 'NOT_DIRECT')}"
            )
        prompt = f"""Evaluate a SOURCE_GROUNDED_INFERENCE through its linked
premises, not by searching for source language that literally states the
conclusion. First determine whether each required premise is established.
Then ask whether the conclusion reasonably follows without adding a material
unsupported leap. A conclusion that follows plainly from established premises is
REASONABLE_INFERENCE even when it adds judgment or restates their consequence
("so they are not independent"). Choose OVERSTATED_PARTIAL only when the conclusion
asserts materially MORE than the premises establish — not because the conclusion is
an inference rather than a stated fact. Choose REASONABLE_INFERENCE, OVERSTATED_PARTIAL,
DOES_NOT_FOLLOW, or INSUFFICIENT_PREMISES. Return every premise claim ID once.

Inference ID: {inference['claim_id']}
Conclusion: {inference['text']}

{chr(10).join(blocks)}"""
        result = self.model.generate("stage_7_inference_referee", prompt, INFERENCE_REFEREE_SCHEMA)
        if result.get("status") not in INFERENCE_RESULTS:
            raise RuntimeError(f"invalid inference result for {inference['claim_id']}")
        assessments = result.get("premise_assessments")
        if not isinstance(assessments, list) or {
            a.get("claim_id") for a in assessments
        } != set(premise_ids):
            raise RuntimeError(f"incomplete premise assessments for {inference['claim_id']}")
        inference["inference_referee"] = {
            "system_result": {**result, "generation_mode": "advisory_model"}
        }

    # ---- corpus lane ----------------------------------------------------

    def check_corpus_claim(
        self,
        claim: dict[str, Any],
        sources: list[dict[str, Any]],
        source_units: dict[str, list[dict[str, Any]]],
        source_unit_vectors: dict[str, list[list[float]]],
    ) -> None:
        """Directional full-corpus counterexample search for a negative claim."""
        proposition = positive_proposition(claim["text"])
        if proposition is None:
            claim["corpus_check"] = {
                "conceptual_result": "CHECK_INCOMPLETE",
                "positive_proposition": None,
                "counterexamples": [],
                "confirming_passages": [],
                "nothing_found_is_proof_of_absence": False,
                "system_reason": "no safe positive-proposition rule for this claim shape",
            }
            return
        query_vector = self._embed([proposition])[0]
        flattened = [
            {"source_id": s["source_id"], "unit": u, "vector": v}
            for s in sources
            for u, v in zip(
                source_units[s["source_id"]], source_unit_vectors[s["source_id"]], strict=True
            )
        ]
        scores = [cosine(query_vector, item["vector"]) for item in flattened]
        order = sorted(range(len(flattened)), key=lambda i: (-scores[i], i))
        query_tokens = set(proposition.lower().split())
        lexical_scores = [
            len(query_tokens & set(item["unit"]["text"].lower().split()))
            / max(1, len(query_tokens))
            for item in flattened
        ]
        lexical_order = sorted(
            (i for i, s in enumerate(lexical_scores) if s > 0),
            key=lambda i: (-lexical_scores[i], i),
        )
        anchors = order[:CORPUS_SEMANTIC_TOP] + lexical_order[:CORPUS_LEXICAL_TOP]
        source_texts = {s["source_id"]: s["full_text"] for s in sources}
        windows: dict[tuple[str, int, int], dict[str, Any]] = {}
        for flat_index in anchors:
            item = flattened[flat_index]
            source_id = item["source_id"]
            units = source_units[source_id]
            index = item["unit"]["sentence_index"]
            start, end = max(0, index - 1), min(len(units) - 1, index + 1)
            key = (source_id, start, end)
            if key not in windows:
                start_char = units[start]["start_char"]
                end_char = units[end]["end_char"]
                windows[key] = {
                    "candidate_id": f"CW_{len(windows) + 1:02d}",
                    "source_id": source_id,
                    "start_sentence_index": start,
                    "end_sentence_index": end,
                    "start_char": start_char,
                    "end_char": end_char,
                    "exact_raw_text": source_texts[source_id][start_char:end_char],
                }
        candidate_windows = list(windows.values())
        if not candidate_windows:
            claim["corpus_check"] = {
                "conceptual_result": "CHECK_INCOMPLETE",
                "positive_proposition": proposition,
                "counterexamples": [],
                "confirming_passages": [],
                "nothing_found_is_proof_of_absence": False,
                "system_reason": "no candidate windows retrieved",
            }
            return
        rendered = "\n\n".join(
            f"{w['candidate_id']} ({w['source_id']}, sentences "
            f"{w['start_sentence_index']}-{w['end_sentence_index']}):\n{w['exact_raw_text']}"
            for w in candidate_windows
        )
        prompt = f"""Review candidate passages against a claim about what the
supplied research corpus does or does not contain. Code semantically searched
every deterministic source window and unioned lexical candidates. Similarity and
lexical overlap are routing aids, not truth judgments.

Corpus claim: {claim['text']}
Positive proposition that would counter the claim: {proposition}

For every candidate, classify its relation to the CORPUS CLAIM with exactly one of:
CONTRADICTS_CLAIM — the passage shows the positive proposition is true, i.e. it is
evidence AGAINST the corpus claim;
SUPPORTS_CLAIM — the passage is consistent with or confirms the corpus claim
(for a negative claim, a passage that itself lacks or defers the denied content
supports the claim, it does not contradict it);
UNRELATED — the passage does not materially bear on the claim either way.
Direction matters: never classify a passage that confirms the corpus claim as a
counterexample. Do not treat failure to find a candidate as proof of absence.
Return every candidate ID exactly once.

Candidate windows:
{rendered}"""
        result = self.model.generate("stage_7_corpus_relation", prompt, CORPUS_RELATION_SCHEMA)
        assessments = result.get("candidate_assessments")
        expected = {w["candidate_id"] for w in candidate_windows}
        if (
            not isinstance(assessments, list)
            or {a.get("candidate_id") for a in assessments} != expected
        ):
            raise RuntimeError(f"incomplete corpus review for {claim['claim_id']}")
        relations = {a["candidate_id"]: a.get("relation") for a in assessments}
        routed = route_corpus_relations(candidate_windows, relations)
        claim["corpus_check"] = {
            **routed,
            "positive_proposition": proposition,
            "sources_checked": len(sources),
            "full_corpus_windows_searched": len(flattened),
        }

    # ---- full run -------------------------------------------------------

    def run(
        self,
        read_identifier: str,
        read_sentences: list[dict[str, Any]],
        inventory: list[dict[str, Any]],
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run the complete advisory over a finished Read. Returns the report.

        ``read_sentences``: [{sentence_id, sentence}]; ``inventory``:
        harvested facts [{fact_id, source_id, text}]; ``sources``:
        [{source_id, full_text}]. The writer's inputs are never touched;
        the Read is never edited; the report never gates.
        """
        fact_vectors = self._embed([f["text"] for f in inventory])
        source_units = {s["source_id"]: source_sentence_units(s["full_text"]) for s in sources}
        source_unit_vectors = {
            sid: self._embed([u["text"] for u in units]) for sid, units in source_units.items()
        }
        source_texts = {s["source_id"]: s["full_text"] for s in sources}

        sentences_out = []
        all_direct: list[dict[str, Any]] = []
        for sentence in read_sentences:
            claims = self.decompose(sentence)
            for claim in claims:
                if claim["type"] == "DIRECT_SOURCE_CLAIM":
                    self.retrieve(claim, inventory, fact_vectors)
                    self.judge_relevance(claim)
                    for candidate in claim["retrieval"]["candidates"]:
                        label = (candidate.get("system_relevance") or {}).get("label")
                        if label in ("DIRECTLY_RELEVANT", "PARTIALLY_RELEVANT"):
                            sid = candidate["source_id"]
                            self.localize(
                                claim,
                                candidate,
                                source_texts[sid],
                                source_units[sid],
                                source_unit_vectors[sid],
                            )
                    all_direct.append(claim)
            sentences_out.append(
                {"sentence_id": sentence["sentence_id"], "sentence": sentence["sentence"], "claims": claims}
            )

        evidence_objects, dedup_stats = deduplicate_evidence(all_direct)
        evidence_by_id = {e["evidence_id"]: e for e in evidence_objects}

        for sentence in sentences_out:
            claims_by_id = {c["claim_id"]: c for c in sentence["claims"]}
            for claim in sentence["claims"]:
                if claim["type"] == "DIRECT_SOURCE_CLAIM":
                    self.referee_direct(claim, evidence_by_id)
            for claim in sentence["claims"]:
                if claim["type"] == "SOURCE_GROUNDED_INFERENCE":
                    self.referee_inference(claim, claims_by_id)
                elif claim["type"] == "WRITER_ANALYSIS":
                    claim["analysis_result"] = "NO_SOURCE_VERIFICATION_REQUIRED"
                elif claim["type"] == "CORPUS_META":
                    self.check_corpus_claim(claim, sources, source_units, source_unit_vectors)

        report = assemble_advisory_report(read_identifier, sentences_out)
        report["evidence_objects"] = evidence_objects
        report["stats"] = dedup_stats
        return report


# ---- production adapters -------------------------------------------------


class StructuredSeatModel:
    """Production AdvisoryModel over the shared structured client."""

    def __init__(self, model_id: str) -> None:
        from backend.integrations.structured_client import get_structured_client

        self.model_id = model_id
        self._client = get_structured_client(model_id)

    def generate(self, stage: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """One structured advisory call; stage is for logging/cost attribution."""
        result, _usage = self._client.generate_structured(
            prompt=prompt,
            schema=schema,
            system=ADVISORY_SYSTEM_PROMPT,
            max_tokens=8_000,
        )
        return result

    def __repr__(self) -> str:  # pragma: no cover
        return f"StructuredSeatModel({self.model_id!r})"


class DashScopeEmbedder:
    """Production Embedder over the DashScope OpenAI-compatible endpoint."""

    def __init__(self, model: str = EMBEDDING_MODEL, batch_size: int = 10) -> None:
        from backend.config import get_settings

        settings = get_settings()
        if not settings.dashscope_api_key:
            raise RuntimeError("QWEN_API_KEY is required for semantic advisory embeddings")
        self._key = settings.dashscope_api_key
        self._endpoint = settings.dashscope_base_url.rstrip("/") + "/embeddings"
        self.model = model
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in order, batched, with bounded retries."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            payload = json.dumps({"model": self.model, "input": batch}).encode()
            last_error: Exception | None = None
            for attempt in range(1, 6):
                request = urllib.request.Request(
                    self._endpoint,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self._key}",
                        "Content-Type": "application/json",
                    },
                )
                try:
                    with urllib.request.urlopen(request, timeout=120) as response:
                        data = json.loads(response.read().decode())
                    items = sorted(data["data"], key=lambda item: item["index"])
                    vectors.extend(item["embedding"] for item in items)
                    last_error = None
                    break
                except Exception as error:  # noqa: BLE001 — retry then surface
                    last_error = error
                    time.sleep(min(2**attempt, 20))
            if last_error is not None:
                raise RuntimeError(f"embedding batch failed after retries: {last_error}")
        return vectors
