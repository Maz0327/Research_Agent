"""Build the post-write D-038 semantic-verification v3 experiment.

This is scratchpad tooling only. It preserves the writer's full-input contract:
the frozen Read already exists before any verification work begins. Terra makes
advisory proposals; code owns IDs, retrieval, offsets, dedup, aggregation, and
artifact validation. No result edits the Read or gates research material.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings  # noqa: E402
from backend.integrations.structured_client import (  # noqa: E402
    get_structured_client,
    provider_for,
)
from backend.pipeline.briefing_routing import paragraphs_for_fact  # noqa: E402
from backend.pipeline.stages.harvest_stage import build_inventory  # noqa: E402
from backend.pipeline.text_similarity import content_tokens  # noqa: E402
from scratchpad.build_semantic_labeling_current_read import (  # noqa: E402
    actor_mask,
    cosine,
    embed_texts,
    read_json,
    read_source_vault,
    selected_sentences,
    stable_hash,
)

DEFAULT_READ = ROOT / "scratchpad/current_d038_read.json"
DEFAULT_HARVEST = ROOT / "scratchpad/current_harvest.json"
DEFAULT_SOURCE_VAULT = (
    ROOT
    / "plans/260814-claim-graph-briefing/artifacts/hawara-run/hawara-vault.html"
)
DEFAULT_FACT_CACHE = ROOT / "scratchpad/fact_embeddings_current_read.json.gz"
DEFAULT_V3_CACHE = ROOT / "scratchpad/semantic_labeling_v3_cache.json.gz"
DEFAULT_JSON = ROOT / "scratchpad/semantic_labeling_v3.json"
DEFAULT_HTML = ROOT / "scratchpad/semantic_labeling_v3.html"

EMBEDDING_MODEL = "qwen3.7-text-embedding"
TOP_PER_ROUTE = 10
LOCALIZATION_SEMANTIC_TOP = 10
LOCALIZATION_LEXICAL_TOP = 5
LOCALIZATION_REGION_RADIUS = 2
CORPUS_SEMANTIC_TOP = 20
CORPUS_LEXICAL_TOP = 10
CURRENT_READ_IDENTIFIER = (
    "D-038 accepted Hawara Read · hawara-rerun · Briefing v1 · 2026-08-22"
)
CLAIM_TYPES = (
    "DIRECT_SOURCE_CLAIM",
    "SOURCE_GROUNDED_INFERENCE",
    "WRITER_ANALYSIS",
    "CORPUS_META",
)
RELEVANCE_LABELS = (
    "DIRECTLY_RELEVANT",
    "PARTIALLY_RELEVANT",
    "NOT_RELEVANT",
    "UNCLEAR",
)
DIRECT_RESULTS = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONFLICT",
    "INSUFFICIENT_EVIDENCE",
)
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


def schema_object(properties: dict[str, Any]) -> dict[str, Any]:
    """Return a strict object schema accepted by the shared client."""
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
                    "derived_from_indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
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
        "status": {
            "type": "string",
            "enum": ["SPAN_FOUND", "NO_SUPPORTING_SPAN_FOUND"],
        },
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
                        "enum": [
                            "SUPPORTS",
                            "PARTIAL",
                            "CONFLICT",
                            "IRRELEVANT",
                            "UNCLEAR",
                        ],
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
        "reason": {"type": "string"},
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
    }
)

CORPUS_COUNTEREXAMPLE_SCHEMA = schema_object(
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


def normalized(text: str) -> str:
    return " ".join(text.split())


class V3Cache:
    """Separate resumable cache for v3 query vectors and Terra proposals."""

    def __init__(
        self,
        path: Path,
        *,
        read_sha256: str,
        inventory_sha256: str,
        judge_model: str,
        judge_provider: str,
    ) -> None:
        self.path = path
        expected = {
            "schema_version": 1,
            "read_sha256": read_sha256,
            "inventory_sha256": inventory_sha256,
            "embedding_model": EMBEDDING_MODEL,
            "judge_model": judge_model,
            "judge_provider": judge_provider,
        }
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                payload = json.load(handle)
            actual = payload.get("metadata", {})
            mismatches = {
                key: (actual.get(key), value)
                for key, value in expected.items()
                if actual.get(key) != value
            }
            if mismatches:
                raise RuntimeError(f"Incompatible v3 cache metadata: {mismatches}")
            self.payload = payload
        else:
            self.payload = {
                "metadata": {**expected, "created_at": datetime.now(UTC).isoformat()},
                "query_embeddings": {},
                "model_calls": {},
            }
        self.payload.setdefault("source_unit_embeddings", {})
        self.used_query_keys: set[str] = set()
        self.used_source_unit_keys: set[str] = set()
        self.used_model_keys: set[str] = set()

    @property
    def query_embeddings(self) -> dict[str, Any]:
        return self.payload["query_embeddings"]

    @property
    def model_calls(self) -> dict[str, Any]:
        return self.payload["model_calls"]

    @property
    def source_unit_embeddings(self) -> dict[str, Any]:
        return self.payload["source_unit_embeddings"]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
            json.dump(self.payload, handle, ensure_ascii=False, separators=(",", ":"))
        temporary.replace(self.path)

    def prune_unused(self) -> None:
        """Keep only entries referenced by the final deterministic build."""
        self.payload["query_embeddings"] = {
            key: value
            for key, value in self.query_embeddings.items()
            if key in self.used_query_keys
        }
        self.payload["source_unit_embeddings"] = {
            key: value
            for key, value in self.source_unit_embeddings.items()
            if key in self.used_source_unit_keys
        }
        self.payload["model_calls"] = {
            key: value
            for key, value in self.model_calls.items()
            if key in self.used_model_keys
        }


class TerraAdvisor:
    """Cached access to the configured Terra judge seat only."""

    def __init__(self, cache: V3Cache, model: str) -> None:
        self.cache = cache
        self.model = model
        self.provider = provider_for(model)
        if model != "gpt-5.6-terra" or self.provider != "openai":
            raise RuntimeError(
                f"This experiment requires gpt-5.6-terra through openai; got "
                f"{model!r} through {self.provider!r}"
            )
        self.client = get_structured_client(model)
        self.calls_reused = 0
        self.calls_created = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def call(
        self,
        stage: str,
        prompt: str,
        schema: dict[str, Any],
        *,
        max_tokens: int = 8_000,
    ) -> dict[str, Any]:
        key = stable_hash(
            {"stage": stage, "prompt": prompt, "schema": schema, "model": self.model}
        )
        self.cache.used_model_keys.add(key)
        cached = self.cache.model_calls.get(key)
        if cached is not None:
            self.calls_reused += 1
            return cached["result"]
        result, usage = self.client.generate_structured(
            prompt=prompt,
            schema=schema,
            system=(
                "You are an advisory semantic-verification judge. Preserve exact "
                "wording strength, attribution, polarity, modality, quantity, and "
                "time. Similarity is not correctness. UNVERIFIED is not FALSE. "
                "Return only the requested structured result."
            ),
            max_tokens=max_tokens,
        )
        self.cache.model_calls[key] = {
            "stage": stage,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "schema_sha256": stable_hash(schema),
            "model": self.model,
            "provider": self.provider,
            "usage": usage,
            "result": result,
        }
        self.calls_created += 1
        self.input_tokens += usage.get("input_tokens", 0) or 0
        self.output_tokens += usage.get("output_tokens", 0) or 0
        self.cache.save()
        return result


def load_fact_embeddings(
    path: Path,
    inventory: list[dict[str, Any]],
) -> tuple[list[list[float]], str, int]:
    signature = [
        [fact["fact_id"], fact["source_id"], fact["text"]] for fact in inventory
    ]
    inventory_sha = stable_hash(signature)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        cache = json.load(handle)
    metadata = cache.get("metadata", {})
    embeddings = cache.get("fact_embeddings", [])
    if metadata.get("embedding_model") != EMBEDDING_MODEL:
        raise RuntimeError("Existing fact cache uses the wrong embedding model")
    if metadata.get("inventory_sha256") != inventory_sha:
        raise RuntimeError("Existing fact cache inventory hash is incompatible")
    if metadata.get("fact_count") != len(inventory) or len(embeddings) != len(inventory):
        raise RuntimeError("Existing fact cache does not contain all 1,270 facts")
    dimensions = metadata.get("dimensions") or (len(embeddings[0]) if embeddings else 0)
    if not embeddings or any(len(vector) != dimensions for vector in embeddings):
        raise RuntimeError("Existing fact cache has inconsistent vector dimensions")
    return embeddings, inventory_sha, dimensions


def ensure_query_embeddings(
    cache: V3Cache,
    queries: dict[str, str],
) -> tuple[dict[str, list[float]], int]:
    resolved: dict[str, list[float]] = {}
    missing: list[tuple[str, str]] = []
    for key, text in queries.items():
        cache.used_query_keys.add(key)
        text_sha = hashlib.sha256(text.encode()).hexdigest()
        cached = cache.query_embeddings.get(key)
        if cached and cached.get("text_sha256") == text_sha:
            resolved[key] = cached["embedding"]
        else:
            missing.append((key, text))
    if missing:
        vectors = embed_texts([text for _, text in missing])
        for (key, text), vector in zip(missing, vectors, strict=True):
            cache.query_embeddings[key] = {
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "embedding": vector,
            }
            resolved[key] = vector
        cache.save()
    return resolved, len(missing)


def ensure_source_unit_embeddings(
    cache: V3Cache,
    source_units: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[list[float]]], int]:
    """Resolve one Qwen vector for every deterministic unit in every source."""
    resolved: dict[str, list[list[float]]] = {}
    missing: list[tuple[str, str, str, int]] = []
    for source_id, units in source_units.items():
        resolved[source_id] = [[] for _ in units]
        for unit in units:
            sentence_index = unit["sentence_index"]
            key = f"{source_id}:{sentence_index}"
            text = unit["text"]
            text_sha = hashlib.sha256(text.encode()).hexdigest()
            cache.used_source_unit_keys.add(key)
            cached = cache.source_unit_embeddings.get(key)
            if cached and cached.get("text_sha256") == text_sha:
                resolved[source_id][sentence_index] = cached["embedding"]
            else:
                missing.append((key, text, source_id, sentence_index))
    if missing:
        vectors = embed_texts([text for _, text, _, _ in missing])
        for (key, text, source_id, sentence_index), vector in zip(
            missing, vectors, strict=True
        ):
            cache.source_unit_embeddings[key] = {
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "embedding": vector,
            }
            resolved[source_id][sentence_index] = vector
        cache.save()
    if any(not vector for vectors in resolved.values() for vector in vectors):
        raise RuntimeError("Full-source embedding cache left an unresolved source unit")
    return resolved, len(missing)


def propose_decomposition(
    advisor: TerraAdvisor,
    sentence: dict[str, Any],
) -> list[dict[str, Any]]:
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
    result = advisor.call("stage_1_decomposition", prompt, DECOMPOSITION_SCHEMA)
    proposals = result.get("claims")
    if not isinstance(proposals, list) or not proposals:
        raise RuntimeError(f"Terra returned no claims for {sentence['sentence_id']}")
    claims: list[dict[str, Any]] = []
    for index, proposal in enumerate(proposals, 1):
        claim_type = proposal.get("type")
        text = normalized(proposal.get("text") or "")
        links = proposal.get("derived_from_indices")
        if claim_type not in CLAIM_TYPES or not text or not isinstance(links, list):
            raise RuntimeError(
                f"Invalid decomposition proposal for {sentence['sentence_id']}: {proposal}"
            )
        if claim_type == "SOURCE_GROUNDED_INFERENCE":
            if not links or any(
                not isinstance(link, int) or link < 1 or link > len(proposals)
                for link in links
            ):
                raise RuntimeError(
                    f"Inference has invalid premise links in {sentence['sentence_id']}"
                )
        elif links:
            raise RuntimeError(
                f"Non-inference has premise links in {sentence['sentence_id']}"
            )
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


def retrieve_candidates(
    direct_claims: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    fact_embeddings: list[list[float]],
    cache: V3Cache,
    source_titles: dict[str, str],
) -> tuple[int, dict[str, int]]:
    queries: dict[str, str] = {}
    route_texts: dict[str, tuple[str, str | None]] = {}
    for claim in direct_claims:
        exact = claim["text"]
        masked = actor_mask(exact)
        exact_key = f"{claim['claim_id']}:exact"
        queries[exact_key] = exact
        masked_key: str | None = None
        if masked != exact:
            masked_key = f"{claim['claim_id']}:actor_masked"
            queries[masked_key] = masked
        route_texts[claim["claim_id"]] = (exact_key, masked_key)
    query_vectors, created = ensure_query_embeddings(cache, queries)

    stats = {"direct_claims": len(direct_claims), "query_routes": len(queries)}
    for claim in direct_claims:
        exact_key, masked_key = route_texts[claim["claim_id"]]
        exact_vector = query_vectors[exact_key]
        masked_vector = query_vectors.get(masked_key) if masked_key else None
        exact_scores = [cosine(exact_vector, vector) for vector in fact_embeddings]
        masked_scores = (
            [cosine(masked_vector, vector) for vector in fact_embeddings]
            if masked_vector is not None
            else []
        )
        exact_order = sorted(
            range(len(inventory)),
            key=lambda i: (-exact_scores[i], inventory[i]["fact_id"]),
        )
        masked_order = (
            sorted(
                range(len(inventory)),
                key=lambda i: (-masked_scores[i], inventory[i]["fact_id"]),
            )
            if masked_scores
            else []
        )
        exact_top = exact_order[:TOP_PER_ROUTE]
        masked_top = masked_order[:TOP_PER_ROUTE]
        exact_ranks = {fact_index: rank for rank, fact_index in enumerate(exact_top, 1)}
        masked_ranks = {
            fact_index: rank for rank, fact_index in enumerate(masked_top, 1)
        }
        union = sorted(
            set(exact_top) | set(masked_top),
            key=lambda i: (
                -max(exact_scores[i], masked_scores[i] if masked_scores else -2.0),
                inventory[i]["fact_id"],
            ),
        )
        candidates: list[dict[str, Any]] = []
        for union_rank, fact_index in enumerate(union, 1):
            fact = inventory[fact_index]
            exact_rank = exact_ranks.get(fact_index)
            masked_rank = masked_ranks.get(fact_index)
            if exact_rank and masked_rank:
                retrieved_by = "both"
            elif exact_rank:
                retrieved_by = "exact"
            else:
                retrieved_by = "actor_masked"
            masked_score = masked_scores[fact_index] if masked_scores else None
            candidates.append(
                {
                    "fact_id": fact["fact_id"],
                    "source_id": fact["source_id"],
                    "source_title": source_titles[fact["source_id"]],
                    "fact_text": fact["text"],
                    "exact_query_score": round(exact_scores[fact_index], 6),
                    "actor_masked_query_score": (
                        round(masked_score, 6) if masked_score is not None else None
                    ),
                    "rank_exact": exact_rank,
                    "rank_actor_masked": masked_rank,
                    "retrieved_by": retrieved_by,
                    "best_embedding_score": round(
                        max(
                            exact_scores[fact_index],
                            masked_score if masked_score is not None else -2.0,
                        ),
                        6,
                    ),
                    "union_rank": union_rank,
                    "system_relevance": None,
                    "owner_relevance": None,
                    "evidence_proposal": None,
                    "owner_evidence_localization": None,
                }
            )
        claim["retrieval"] = {
            "exact_query": claim["text"],
            "actor_masked_query": (
                actor_mask(claim["text"]) if masked_key is not None else None
            ),
            "top_per_route": TOP_PER_ROUTE,
            "similarity_threshold": None,
            "deduplication": "exact FACT_ID only",
            "candidates": candidates,
            "owner_missing_fact_or_evidence": False,
        }
    return created, stats


def propose_relevance(advisor: TerraAdvisor, claim: dict[str, Any]) -> None:
    candidates = claim["retrieval"]["candidates"]
    facts = "\n".join(
        f"{candidate['fact_id']}: {candidate['fact_text']}"
        for candidate in candidates
    )
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
    result = advisor.call("stage_3_relevance", prompt, RELEVANCE_SCHEMA)
    judgments = result.get("judgments")
    expected = {candidate["fact_id"] for candidate in candidates}
    if not isinstance(judgments, list) or {
        judgment.get("fact_id") for judgment in judgments
    } != expected or len(judgments) != len(expected):
        raise RuntimeError(f"Incomplete relevance response for {claim['claim_id']}")
    by_id = {judgment["fact_id"]: judgment for judgment in judgments}
    for candidate in candidates:
        judgment = by_id[candidate["fact_id"]]
        if judgment.get("label") not in RELEVANCE_LABELS:
            raise RuntimeError(f"Invalid relevance label for {candidate['fact_id']}")
        candidate["system_relevance"] = {
            "label": judgment["label"],
            "reason": judgment.get("reason") or "",
            "model": advisor.model,
            "provider": advisor.provider,
        }


def source_sentence_units(text: str) -> list[dict[str, Any]]:
    """Split raw source text deterministically while preserving exact offsets."""
    units: list[dict[str, Any]] = []

    def append_segment(segment_start: int, segment_end: int) -> None:
        """Append a sentence, or bounded transcript units when punctuation is absent."""
        segment = text[segment_start:segment_end]
        word_matches = list(re.finditer(r"\S+", segment))
        chunks = (
            [word_matches[offset : offset + 60] for offset in range(0, len(word_matches), 60)]
            if len(word_matches) > 120
            else [word_matches]
        )
        for chunk in chunks:
            if not chunk:
                continue
            chunk_start = segment_start + chunk[0].start()
            chunk_end = segment_start + chunk[-1].end()
            units.append(
                {
                    "sentence_index": len(units),
                    "start_char": chunk_start,
                    "end_char": chunk_end,
                    "text": text[chunk_start:chunk_end],
                    "unit_kind": (
                        "bounded_transcript_unit"
                        if len(word_matches) > 120
                        else "source_sentence"
                    ),
                }
            )

    start = 0
    length = len(text)
    while start < length:
        while start < length and text[start].isspace():
            start += 1
        if start >= length:
            break
        end = start
        boundary = length
        while end < length:
            char = text[end]
            if char in ".!?":
                probe = end + 1
                while probe < length and text[probe] in "\"'’”)]":
                    probe += 1
                if probe >= length or text[probe].isspace():
                    boundary = probe
                    break
            if char == "\n" and end + 1 < length and text[end + 1] == "\n":
                boundary = end
                break
            end += 1
        raw_end = boundary
        while raw_end > start and text[raw_end - 1].isspace():
            raw_end -= 1
        if raw_end > start:
            append_segment(start, raw_end)
        start = max(boundary, start + 1)
    return units


def legacy_candidate_region_indices(
    fact_text: str,
    source_text: str,
    units: list[dict[str, Any]],
) -> set[int]:
    """Reproduce the old route only to measure whether it would miss evidence."""
    windows = paragraphs_for_fact(fact_text, source_text, window=2)
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for window in windows:
        position = source_text.find(window, cursor)
        if position < 0:
            position = source_text.find(window)
        if position >= 0:
            offsets.append((position, position + len(window)))
            cursor = position + len(window)
    if offsets:
        region_start = min(start for start, _ in offsets)
        region_end = max(end for _, end in offsets)
        matched = [
            unit
            for unit in units
            if unit["end_char"] > region_start and unit["start_char"] < region_end
        ]
    else:
        fact_tokens = content_tokens(fact_text)
        best = max(
            range(len(units)),
            key=lambda index: len(fact_tokens & content_tokens(units[index]["text"])),
        )
        matched = units[max(0, best - 2) : best + 3]
    if not matched:
        raise RuntimeError("Source routing produced no mappable sentence units")
    first = matched[0]["sentence_index"]
    last = matched[-1]["sentence_index"]
    expanded = units[max(0, first - 2) : min(len(units), last + 3)]
    if len(expanded) > 18:
        fact_tokens = content_tokens(fact_text)
        best_local = max(
            range(len(expanded)),
            key=lambda index: len(
                fact_tokens & content_tokens(expanded[index]["text"])
            ),
        )
        expanded = expanded[max(0, best_local - 8) : best_local + 10]
    return {unit["sentence_index"] for unit in expanded}


def full_source_candidate_regions(
    fact_text: str,
    fact_vector: list[float],
    units: list[dict[str, Any]],
    unit_vectors: list[list[float]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, int], set[int], set[int]]:
    """Search every source unit, then form compact regions for Terra review."""
    if len(units) != len(unit_vectors) or not units:
        raise RuntimeError("Full-source search received mismatched source units/vectors")
    semantic_scores = [cosine(fact_vector, vector) for vector in unit_vectors]
    semantic_order = sorted(
        range(len(units)), key=lambda index: (-semantic_scores[index], index)
    )
    semantic_rank = {
        index: rank for rank, index in enumerate(semantic_order, start=1)
    }
    fact_tokens = content_tokens(fact_text)
    lexical_scores = [
        len(fact_tokens & content_tokens(unit["text"])) / max(1, len(fact_tokens))
        for unit in units
    ]
    lexical_order = sorted(
        (index for index, score in enumerate(lexical_scores) if score > 0),
        key=lambda index: (-lexical_scores[index], index),
    )
    semantic_anchors = semantic_order[:LOCALIZATION_SEMANTIC_TOP]
    lexical_anchors = lexical_order[:LOCALIZATION_LEXICAL_TOP]
    lexical_rank = {
        index: rank for rank, index in enumerate(lexical_order, start=1)
    }

    regions: dict[tuple[int, int], dict[str, Any]] = {}
    for route, anchors in (
        ("semantic", semantic_anchors),
        ("lexical", lexical_anchors),
    ):
        for anchor in anchors:
            start = max(0, anchor - LOCALIZATION_REGION_RADIUS)
            end = min(len(units) - 1, anchor + LOCALIZATION_REGION_RADIUS)
            key = (start, end)
            region = regions.setdefault(
                key,
                {
                    "start_sentence_index": start,
                    "end_sentence_index": end,
                    "semantic_anchor_ranks": [],
                    "lexical_anchor_ranks": [],
                    "best_embedding_score": None,
                    "retrieved_by": [],
                },
            )
            if route not in region["retrieved_by"]:
                region["retrieved_by"].append(route)
            if route == "semantic":
                region["semantic_anchor_ranks"].append(semantic_rank[anchor])
            else:
                region["lexical_anchor_ranks"].append(lexical_rank[anchor])
            score = semantic_scores[anchor]
            current = region["best_embedding_score"]
            if current is None or score > current:
                region["best_embedding_score"] = score

    ordered_regions = sorted(
        regions.values(),
        key=lambda region: (
            min(region["semantic_anchor_ranks"], default=10**9),
            min(region["lexical_anchor_ranks"], default=10**9),
            region["start_sentence_index"],
        ),
    )
    for number, region in enumerate(ordered_regions, start=1):
        region["region_id"] = f"R{number:02d}"
        region["semantic_anchor_ranks"].sort()
        region["lexical_anchor_ranks"].sort()
        region["retrieved_by"] = (
            "both" if len(region["retrieved_by"]) == 2 else region["retrieved_by"][0]
        )
        region["best_embedding_score"] = round(
            float(region["best_embedding_score"]), 6
        )

    presented_indices = sorted(
        {
            index
            for region in ordered_regions
            for index in range(
                region["start_sentence_index"],
                region["end_sentence_index"] + 1,
            )
        }
    )
    presented_units = [units[index] for index in presented_indices]
    semantic_presented = {
        index
        for anchor in semantic_anchors
        for index in range(
            max(0, anchor - LOCALIZATION_REGION_RADIUS),
            min(len(units), anchor + LOCALIZATION_REGION_RADIUS + 1),
        )
    }
    lexical_presented = {
        index
        for anchor in lexical_anchors
        for index in range(
            max(0, anchor - LOCALIZATION_REGION_RADIUS),
            min(len(units), anchor + LOCALIZATION_REGION_RADIUS + 1),
        )
    }
    return (
        presented_units,
        ordered_regions,
        semantic_rank,
        semantic_presented,
        lexical_presented,
    )


def propose_localization(
    advisor: TerraAdvisor,
    claim: dict[str, Any],
    candidate: dict[str, Any],
    source_text: str,
    units: list[dict[str, Any]],
    fact_vector: list[float],
    unit_vectors: list[list[float]],
) -> None:
    (
        region,
        candidate_regions,
        semantic_rank,
        semantic_presented,
        lexical_presented,
    ) = full_source_candidate_regions(
        candidate["fact_text"], fact_vector, units, unit_vectors
    )
    legacy_indices = legacy_candidate_region_indices(
        candidate["fact_text"], source_text, units
    )
    by_all_index = {unit["sentence_index"]: unit for unit in units}
    rendered_regions: list[str] = []
    for candidate_region in candidate_regions:
        start = candidate_region["start_sentence_index"]
        end = candidate_region["end_sentence_index"]
        numbered = "\n".join(
            f"[{index}] {by_all_index[index]['text']}"
            for index in range(start, end + 1)
        )
        rendered_regions.append(
            f"{candidate_region['region_id']} "
            f"(retrieved by {candidate_region['retrieved_by']}; similarity rank is "
            "routing metadata only):\n"
            f"{numbered}"
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
{chr(10).join(rendered_regions)}"""
    result = advisor.call("stage_4_full_source_localization", prompt, LOCALIZATION_SCHEMA)
    region_indices = {unit["sentence_index"] for unit in region}

    def boundaries_are_invalid(proposal: dict[str, Any]) -> bool:
        proposed_start = proposal.get("start_sentence_index")
        proposed_end = proposal.get("end_sentence_index")
        if proposal.get("status") != "SPAN_FOUND":
            return False
        return (
            not isinstance(proposed_start, int)
            or not isinstance(proposed_end, int)
            or proposed_start not in region_indices
            or proposed_end not in region_indices
            or proposed_end < proposed_start
            or proposed_end - proposed_start > 2
            or any(
                index not in region_indices
                for index in range(proposed_start, proposed_end + 1)
            )
        )

    for retry_number in (1, 2):
        if not boundaries_are_invalid(result):
            break
        proposed_start = result.get("start_sentence_index")
        proposed_end = result.get("end_sentence_index")
        retry_prompt = f"""{prompt}

Your previous proposal selected sentence indices {proposed_start} through
{proposed_end}, which violates the required contiguous 1-3 sentence limit or
does not map to the supplied region. Correct the proposal. SPAN_FOUND is valid
only when end_sentence_index - start_sentence_index is 0, 1, or 2. Otherwise,
return NO_SUPPORTING_SPAN_FOUND with null indices. Do not ask code to truncate
or invent a span."""
        result = advisor.call(
            f"stage_4_full_source_localization_boundary_retry_{retry_number}",
            retry_prompt,
            LOCALIZATION_SCHEMA,
        )
    status = result.get("status")
    search_metadata: dict[str, Any] = {
        "search_scope": "entire_known_source",
        "full_source_units_searched": len(units),
        "full_source_candidate_windows_searched": len(units),
        "semantic_top_requested": LOCALIZATION_SEMANTIC_TOP,
        "lexical_top_requested": LOCALIZATION_LEXICAL_TOP,
        "similarity_threshold": None,
        "candidate_regions_considered": candidate_regions,
        "winning_semantic_rank": None,
        "lexical_search_helped": False,
        "old_routing_location_would_have_missed_final_evidence": None,
    }
    if status == "NO_SUPPORTING_SPAN_FOUND":
        if result.get("start_sentence_index") is not None or result.get(
            "end_sentence_index"
        ) is not None:
            raise RuntimeError(
                f"Localization returned indices with no span for {candidate['fact_id']}"
            )
        candidate["evidence_proposal"] = {
            "status": "NO_SUPPORTING_SPAN_FOUND",
            "routing_method": "full_source_semantic_search_with_lexical_union",
            "search_metadata": search_metadata,
            "candidate_region_sentences": region,
            "system_reason": result.get("reason") or "",
            "model": advisor.model,
            "provider": advisor.provider,
        }
        return
    if status != "SPAN_FOUND":
        raise RuntimeError(f"Invalid localization status for {candidate['fact_id']}")
    start_index = result.get("start_sentence_index")
    end_index = result.get("end_sentence_index")
    by_index = {unit["sentence_index"]: unit for unit in region}
    if (
        not isinstance(start_index, int)
        or not isinstance(end_index, int)
        or start_index not in by_index
        or end_index not in by_index
        or end_index < start_index
        or end_index - start_index > 2
        or any(index not in by_index for index in range(start_index, end_index + 1))
    ):
        raise RuntimeError(
            f"Invalid localization boundaries for {candidate['fact_id']}: "
            f"{start_index}-{end_index}"
        )
    start_char = by_index[start_index]["start_char"]
    end_char = by_index[end_index]["end_char"]
    exact_text = source_text[start_char:end_char]
    context_before = units[start_index - 1]["text"] if start_index > 0 else None
    context_after = (
        units[end_index + 1]["text"] if end_index + 1 < len(units) else None
    )
    selected_indices = set(range(start_index, end_index + 1))
    search_metadata["winning_semantic_rank"] = min(
        semantic_rank[index] for index in selected_indices
    )
    search_metadata["lexical_search_helped"] = bool(
        selected_indices & lexical_presented
        and not selected_indices & semantic_presented
    )
    search_metadata["old_routing_location_would_have_missed_final_evidence"] = (
        not selected_indices <= legacy_indices
    )
    candidate["evidence_proposal"] = {
        "status": "SPAN_FOUND",
        "routing_method": "full_source_semantic_search_with_lexical_union",
        "search_metadata": search_metadata,
        "source_id": candidate["source_id"],
        "exact_raw_text": exact_text,
        "start_char": start_char,
        "end_char": end_char,
        "start_sentence_index": start_index,
        "end_sentence_index": end_index,
        "word_count": len(exact_text.split()),
        "source_sentence_count": end_index - start_index + 1,
        "supporting_fact_ids": [candidate["fact_id"]],
        "context_before": context_before,
        "context_after": context_after,
        "candidate_region_sentences": region,
        "system_reason": result.get("reason") or "",
        "model": advisor.model,
        "provider": advisor.provider,
    }


def evidence_identity(proposal: dict[str, Any]) -> str:
    identity = {
        "source_id": proposal["source_id"],
        "start_char": proposal["start_char"],
        "end_char": proposal["end_char"],
        "normalized_text": normalized(proposal["exact_raw_text"]),
    }
    return "E_" + stable_hash(identity)[:16]


def deduplicate_evidence(
    direct_claims: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for claim in direct_claims:
        for candidate in claim["retrieval"]["candidates"]:
            proposal = candidate.get("evidence_proposal")
            if not proposal or proposal.get("status") != "SPAN_FOUND":
                continue
            occurrences.append(
                {
                    "occurrence_id": f"OCC_{len(occurrences) + 1:03d}",
                    "claim_id": claim["claim_id"],
                    "fact_id": candidate["fact_id"],
                    "fact_text": candidate["fact_text"],
                    "candidate": candidate,
                    "proposal": proposal,
                }
            )

    parent = list(range(len(occurrences)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    merge_reasons: dict[tuple[int, int], str] = {}
    for left in range(len(occurrences)):
        a = occurrences[left]
        for right in range(left + 1, len(occurrences)):
            b = occurrences[right]
            pa, pb = a["proposal"], b["proposal"]
            if pa["source_id"] != pb["source_id"]:
                continue
            same_span = (
                pa["start_char"] == pb["start_char"]
                and pa["end_char"] == pb["end_char"]
                and normalized(pa["exact_raw_text"])
                == normalized(pb["exact_raw_text"])
            )
            contained = (
                a["claim_id"] == b["claim_id"]
                and normalized(a["fact_text"]) == normalized(b["fact_text"])
                and (
                    (
                        pa["start_char"] <= pb["start_char"]
                        and pa["end_char"] >= pb["end_char"]
                    )
                    or (
                        pb["start_char"] <= pa["start_char"]
                        and pb["end_char"] >= pa["end_char"]
                    )
                )
            )
            if same_span or contained:
                union(left, right)
                merge_reasons[(left, right)] = (
                    "exact_same_source_span"
                    if same_span
                    else "contained_span_for_exact_duplicate_fact_text"
                )

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(occurrences)):
        groups[find(index)].append(index)

    evidence_objects: list[dict[str, Any]] = []
    for member_indices in groups.values():
        canonical_index = min(
            member_indices,
            key=lambda index: (
                occurrences[index]["proposal"]["word_count"],
                occurrences[index]["proposal"]["end_char"]
                - occurrences[index]["proposal"]["start_char"],
                occurrences[index]["occurrence_id"],
            ),
        )
        canonical = occurrences[canonical_index]["proposal"]
        evidence_id = evidence_identity(canonical)
        fact_ids = sorted({occurrences[index]["fact_id"] for index in member_indices})
        claim_ids = sorted({occurrences[index]["claim_id"] for index in member_indices})
        reasons = sorted(
            {
                reason
                for (left, right), reason in merge_reasons.items()
                if left in member_indices and right in member_indices
            }
        )
        evidence = {
            "evidence_id": evidence_id,
            "source_id": canonical["source_id"],
            "exact_raw_text": canonical["exact_raw_text"],
            "start_char": canonical["start_char"],
            "end_char": canonical["end_char"],
            "start_sentence_index": canonical["start_sentence_index"],
            "end_sentence_index": canonical["end_sentence_index"],
            "word_count": canonical["word_count"],
            "source_sentence_count": canonical["source_sentence_count"],
            "supporting_fact_ids": fact_ids,
            "routed_claim_ids": claim_ids,
            "occurrence_ids": [
                occurrences[index]["occurrence_id"] for index in member_indices
            ],
            "context_before": canonical["context_before"],
            "context_after": canonical["context_after"],
            "system_grouping": {
                "occurrence_count": len(member_indices),
                "merge_reasons": reasons,
            },
            "owner_grouping": None,
        }
        evidence_objects.append(evidence)
        for index in member_indices:
            occurrences[index]["candidate"]["evidence_proposal"][
                "evidence_id"
            ] = evidence_id
            occurrences[index]["candidate"]["evidence_proposal"][
                "occurrence_id"
            ] = occurrences[index]["occurrence_id"]
    evidence_objects.sort(key=lambda item: item["evidence_id"])
    stats = {
        "candidate_fact_occurrences": sum(
            len(claim["retrieval"]["candidates"]) for claim in direct_claims
        ),
        "unique_retrieved_fact_ids": len(
            {
                candidate["fact_id"]
                for claim in direct_claims
                for candidate in claim["retrieval"]["candidates"]
            }
        ),
        "raw_localized_evidence_occurrences": len(occurrences),
        "unique_evidence_ids": len(evidence_objects),
        "duplicates_eliminated": len(occurrences) - len(evidence_objects),
    }
    return evidence_objects, stats


def propose_direct_referee(
    advisor: TerraAdvisor,
    claim: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> None:
    evidence_ids = sorted(
        {
            candidate["evidence_proposal"]["evidence_id"]
            for candidate in claim["retrieval"]["candidates"]
            if candidate.get("evidence_proposal")
            and candidate["evidence_proposal"].get("status") == "SPAN_FOUND"
        }
    )
    evidence = [evidence_by_id[evidence_id] for evidence_id in evidence_ids]
    if not evidence:
        claim["direct_referee"] = {
            "system_result": {
                "status": "INSUFFICIENT_EVIDENCE",
                "mismatch_dimensions": [],
                "conflicting_evidence": False,
                "evidence_assessments": [],
                "reason": "No localized supporting span survived routing and localization.",
                "generation_mode": "deterministic_no_evidence",
            },
            "owner_result": None,
            "owner_flags": [],
            "owner_notes": "",
        }
        return
    rendered = "\n\n".join(
        f"Evidence {item['evidence_id']} ({item['source_id']}):\n{item['exact_raw_text']}"
        for item in evidence
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
    result = advisor.call("stage_6_direct_referee", prompt, DIRECT_REFEREE_SCHEMA)
    if result.get("status") not in DIRECT_RESULTS:
        raise RuntimeError(f"Invalid direct referee result for {claim['claim_id']}")
    assessments = result.get("evidence_assessments")
    if not isinstance(assessments, list) or {
        item.get("evidence_id") for item in assessments
    } != set(evidence_ids) or len(assessments) != len(evidence_ids):
        raise RuntimeError(
            f"Incomplete evidence assessments for {claim['claim_id']}"
        )
    dimensions = result.get("mismatch_dimensions")
    if not isinstance(dimensions, list) or any(
        dimension not in MISMATCH_DIMENSIONS for dimension in dimensions
    ):
        raise RuntimeError(f"Invalid mismatch dimensions for {claim['claim_id']}")
    claim["direct_referee"] = {
        "system_result": {
            "status": result["status"],
            "mismatch_dimensions": dimensions,
            "conflicting_evidence": bool(result.get("conflicting_evidence")),
            "evidence_assessments": assessments,
            "reason": result.get("reason") or "",
            "generation_mode": "terra_advisory",
            "model": advisor.model,
            "provider": advisor.provider,
        },
        "owner_result": None,
        "owner_flags": [],
        "owner_notes": "",
    }


def propose_inference_referee(
    advisor: TerraAdvisor,
    inference: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> None:
    premise_ids = inference["derived_from_claim_ids"]
    premises = [claims_by_id.get(claim_id) for claim_id in premise_ids]
    valid = [premise for premise in premises if premise is not None]
    if len(valid) != len(premise_ids):
        inference["inference_referee"] = {
            "system_result": {
                "status": "INSUFFICIENT_PREMISES",
                "reason": "One or more proposed premise links do not resolve.",
                "premise_assessments": [],
                "generation_mode": "deterministic_missing_premise_link",
            },
            "owner_result": None,
            "owner_derived_from_claim_ids": list(premise_ids),
            "owner_notes": "",
        }
        return
    premise_blocks: list[str] = []
    for premise in valid:
        referee = premise.get("direct_referee", {}).get("system_result", {})
        evidence_ids = sorted(
            {
                candidate["evidence_proposal"]["evidence_id"]
                for candidate in premise.get("retrieval", {}).get("candidates", [])
                if candidate.get("evidence_proposal")
                and candidate["evidence_proposal"].get("status") == "SPAN_FOUND"
            }
        )
        evidence_text = "\n".join(
            f"  {evidence_id}: {evidence_by_id[evidence_id]['exact_raw_text']}"
            for evidence_id in evidence_ids
        )
        premise_blocks.append(
            f"Premise {premise['claim_id']}: {premise['text']}\n"
            f"Direct result: {referee.get('status', 'NOT_DIRECT')}\n{evidence_text}"
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

{chr(10).join(premise_blocks)}"""
    result = advisor.call(
        "stage_7_inference_referee", prompt, INFERENCE_REFEREE_SCHEMA
    )
    if result.get("status") not in INFERENCE_RESULTS:
        raise RuntimeError(
            f"Invalid inference result for {inference['claim_id']}"
        )
    assessments = result.get("premise_assessments")
    if not isinstance(assessments, list) or {
        item.get("claim_id") for item in assessments
    } != set(premise_ids) or len(assessments) != len(premise_ids):
        raise RuntimeError(
            f"Incomplete premise assessments for {inference['claim_id']}"
        )
    inference["inference_referee"] = {
        "system_result": {
            "status": result["status"],
            "reason": result.get("reason") or "",
            "premise_assessments": assessments,
            "generation_mode": "terra_advisory",
            "model": advisor.model,
            "provider": advisor.provider,
        },
        "owner_result": None,
        "owner_derived_from_claim_ids": list(premise_ids),
        "owner_notes": "",
    }


def positive_counterexample_proposition(claim_text: str) -> str:
    """Construct the positive proposition that a negative corpus claim denies."""
    if claim_text == "The pile contains no response from Hawass to the Mataha allegations.":
        return "Hawass responded to the Mataha allegations in the supplied research."
    if claim_text == "The official reports are linked rather than substantively reproduced.":
        return "The supplied research substantively reproduces the official reports."
    match = re.fullmatch(r"No supplied source identifies (.+)\.", claim_text)
    if match:
        return f"A supplied source identifies {match.group(1)}."
    raise RuntimeError(f"No safe positive-proposition rule for corpus claim: {claim_text}")


def check_corpus_claim(
    claim: dict[str, Any],
    sources: list[dict[str, Any]],
    source_units: dict[str, list[dict[str, Any]]],
    source_unit_vectors: dict[str, list[list[float]]],
    cache: V3Cache,
    advisor: TerraAdvisor,
) -> None:
    proposition = positive_counterexample_proposition(claim["text"])
    query_key = f"{claim['claim_id']}:corpus_positive_proposition"
    query_vectors, _ = ensure_query_embeddings(cache, {query_key: proposition})
    query_vector = query_vectors[query_key]
    flattened: list[dict[str, Any]] = []
    for source in sources:
        source_id = source["source_id"]
        units = source_units[source_id]
        vectors = source_unit_vectors[source_id]
        for unit, vector in zip(units, vectors, strict=True):
            flattened.append(
                {
                    "source_id": source_id,
                    "unit": unit,
                    "vector": vector,
                }
            )
    semantic_scores = [cosine(query_vector, item["vector"]) for item in flattened]
    semantic_order = sorted(
        range(len(flattened)), key=lambda index: (-semantic_scores[index], index)
    )
    semantic_rank = {
        index: rank for rank, index in enumerate(semantic_order, start=1)
    }
    query_tokens = content_tokens(proposition)
    lexical_scores = [
        len(query_tokens & content_tokens(item["unit"]["text"]))
        / max(1, len(query_tokens))
        for item in flattened
    ]
    lexical_order = sorted(
        (index for index, score in enumerate(lexical_scores) if score > 0),
        key=lambda index: (-lexical_scores[index], index),
    )
    lexical_rank = {
        index: rank for rank, index in enumerate(lexical_order, start=1)
    }
    anchors: list[tuple[str, int]] = [
        ("semantic", index) for index in semantic_order[:CORPUS_SEMANTIC_TOP]
    ] + [("lexical", index) for index in lexical_order[:CORPUS_LEXICAL_TOP]]
    source_by_id = {source["source_id"]: source for source in sources}
    regions: dict[tuple[str, int, int], dict[str, Any]] = {}
    for route, flat_index in anchors:
        item = flattened[flat_index]
        source_id = item["source_id"]
        unit_index = item["unit"]["sentence_index"]
        units = source_units[source_id]
        start_index = max(0, unit_index - 1)
        end_index = min(len(units) - 1, unit_index + 1)
        key = (source_id, start_index, end_index)
        region = regions.setdefault(
            key,
            {
                "source_id": source_id,
                "start_sentence_index": start_index,
                "end_sentence_index": end_index,
                "semantic_anchor_ranks": [],
                "lexical_anchor_ranks": [],
                "retrieved_routes": [],
                "best_embedding_score": None,
            },
        )
        if route not in region["retrieved_routes"]:
            region["retrieved_routes"].append(route)
        if route == "semantic":
            region["semantic_anchor_ranks"].append(semantic_rank[flat_index])
        else:
            region["lexical_anchor_ranks"].append(lexical_rank[flat_index])
        score = semantic_scores[flat_index]
        current_score = region["best_embedding_score"]
        if current_score is None or score > current_score:
            region["best_embedding_score"] = score

    candidate_windows = sorted(
        regions.values(),
        key=lambda region: (
            min(region["semantic_anchor_ranks"], default=10**9),
            min(region["lexical_anchor_ranks"], default=10**9),
            region["source_id"],
            region["start_sentence_index"],
        ),
    )
    for number, region in enumerate(candidate_windows, start=1):
        source_id = region["source_id"]
        units = source_units[source_id]
        start_index = region["start_sentence_index"]
        end_index = region["end_sentence_index"]
        start_char = units[start_index]["start_char"]
        end_char = units[end_index]["end_char"]
        exact_text = source_by_id[source_id]["full_text"][start_char:end_char]
        routes = region.pop("retrieved_routes")
        region.update(
            {
                "candidate_id": f"CW_{number:02d}",
                "exact_raw_text": exact_text,
                "start_char": start_char,
                "end_char": end_char,
                "word_count": len(exact_text.split()),
                "source_sentence_count": end_index - start_index + 1,
                "semantic_anchor_ranks": sorted(region["semantic_anchor_ranks"]),
                "lexical_anchor_ranks": sorted(region["lexical_anchor_ranks"]),
                "retrieved_by": (
                    "both"
                    if len(routes) == 2
                    else routes[0]
                ),
                "best_embedding_score": round(
                    float(region["best_embedding_score"]), 6
                ),
            }
        )
    if not candidate_windows:
        claim["corpus_check"] = {
            "system_result": "CORPUS_CHECK_INCOMPLETE",
            "conceptual_result": "CHECK_INCOMPLETE",
            "method": "full_corpus_semantic_counterexample_search",
            "positive_proposition": proposition,
            "sources_checked": len(sources),
            "full_corpus_windows_searched": len(flattened),
            "candidate_windows": [],
            "counterexamples": [],
            "nothing_found_is_proof_of_absence": False,
            "owner_result": None,
            "owner_notes": "",
        }
        return
    rendered = "\n\n".join(
        f"{window['candidate_id']} ({window['source_id']}, sentences "
        f"{window['start_sentence_index']}-{window['end_sentence_index']}):\n"
        f"{window['exact_raw_text']}"
        for window in candidate_windows
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
    result = advisor.call(
        "stage_7_corpus_counterexample_review",
        prompt,
        CORPUS_COUNTEREXAMPLE_SCHEMA,
    )
    assessments = result.get("candidate_assessments")
    expected_ids = {window["candidate_id"] for window in candidate_windows}
    if (
        not isinstance(assessments, list)
        or {item.get("candidate_id") for item in assessments} != expected_ids
        or len(assessments) != len(expected_ids)
    ):
        raise RuntimeError(f"Incomplete corpus review for {claim['claim_id']}")
    assessment_by_id = {item["candidate_id"]: item for item in assessments}
    allowed_relations = {"CONTRADICTS_CLAIM", "SUPPORTS_CLAIM", "UNRELATED"}
    counterexamples: list[dict[str, Any]] = []
    confirming_passages: list[dict[str, Any]] = []
    for window in candidate_windows:
        assessment = assessment_by_id[window["candidate_id"]]
        relation = assessment.get("relation")
        if relation not in allowed_relations:
            raise RuntimeError(
                f"Invalid corpus relation {relation!r} for {claim['claim_id']}"
            )
        window["model_relation"] = relation
        window["model_reason"] = assessment.get("reason") or ""
        if relation == "CONTRADICTS_CLAIM":
            counterexamples.append(window)
        elif relation == "SUPPORTS_CLAIM":
            confirming_passages.append(window)
    conceptual_result = (
        "POSSIBLE_COUNTEREXAMPLE_FOUND" if counterexamples else "NOTHING_FOUND"
    )
    status = (
        "COUNTEREXAMPLE_FOUND"
        if counterexamples
        else "CORPUS_CHECK_INCOMPLETE"
    )
    claim["corpus_check"] = {
        "system_result": status,
        "conceptual_result": conceptual_result,
        "method": "full_corpus_semantic_counterexample_search",
        "positive_proposition": proposition,
        "sources_checked": len(sources),
        "full_corpus_windows_searched": len(flattened),
        "semantic_top_requested": CORPUS_SEMANTIC_TOP,
        "lexical_top_requested": CORPUS_LEXICAL_TOP,
        "similarity_threshold": None,
        "candidate_windows": candidate_windows,
        "counterexamples": counterexamples,
        "confirming_passages": confirming_passages,
        "winning_semantic_rank": min(
            (
                min(window["semantic_anchor_ranks"], default=10**9)
                for window in counterexamples
            ),
            default=None,
        ),
        "lexical_search_helped": any(
            window["retrieved_by"] == "lexical" for window in counterexamples
        ),
        "nothing_found_is_proof_of_absence": False,
        "system_reason": result.get("reason") or "",
        "model": advisor.model,
        "provider": advisor.provider,
        "owner_result": None,
        "owner_notes": "",
    }


def deterministic_advisory(claims: list[dict[str, Any]]) -> dict[str, Any]:
    direct = [claim for claim in claims if claim["type"] == "DIRECT_SOURCE_CLAIM"]
    inferences = [
        claim for claim in claims if claim["type"] == "SOURCE_GROUNDED_INFERENCE"
    ]
    corpus = [claim for claim in claims if claim["type"] == "CORPUS_META"]
    direct_status = {
        claim["claim_id"]: claim["direct_referee"]["system_result"]["status"]
        for claim in direct
    }
    inference_status = {
        claim["claim_id"]: claim["inference_referee"]["system_result"]["status"]
        for claim in inferences
    }
    corpus_status = {
        claim["claim_id"]: claim["corpus_check"]["conceptual_result"]
        for claim in corpus
    }

    triggers = [
        claim_id for claim_id, status in direct_status.items() if status == "CONFLICT"
    ] + [
        claim_id
        for claim_id, status in inference_status.items()
        if status == "DOES_NOT_FOLLOW"
    ] + [
        claim_id
        for claim_id, status in corpus_status.items()
        if status == "POSSIBLE_COUNTEREXAMPLE_FOUND"
    ]
    if triggers:
        status = "SEMANTIC_CONFLICT"
    else:
        triggers = [
            claim_id
            for claim_id, result in direct_status.items()
            if result == "PARTIALLY_SUPPORTED"
        ] + [
            claim_id
            for claim_id, result in inference_status.items()
            if result == "OVERSTATED_PARTIAL"
        ]
        if triggers:
            status = "PARTIAL_WARNING"
        else:
            triggers = [
                claim_id
                for claim_id, result in direct_status.items()
                if result == "INSUFFICIENT_EVIDENCE"
            ] + [
                claim_id
                for claim_id, result in inference_status.items()
                if result == "INSUFFICIENT_PREMISES"
            ] + [
                claim_id
                for claim_id, result in corpus_status.items()
                if result == "CHECK_INCOMPLETE"
            ]
            if triggers:
                status = "UNVERIFIED"
            elif any(result == "NOTHING_FOUND" for result in corpus_status.values()):
                status = "NOTHING_FOUND_AGAINST"
                triggers = [
                    claim_id
                    for claim_id, result in corpus_status.items()
                    if result == "NOTHING_FOUND"
                ]
            elif not direct and not inferences and not corpus:
                status = "NO_SOURCE_VERIFICATION_REQUIRED"
                triggers = [
                    claim["claim_id"]
                    for claim in claims
                    if claim["type"] == "WRITER_ANALYSIS"
                ]
            else:
                status = "NO_SEMANTIC_ISSUE_FOUND"
                triggers = []
    return {
        "deterministic_status": status,
        "triggering_claim_ids": sorted(set(triggers)),
        "rule": "code_aggregation_v3_corpus_conceptual_nothing_found_tier",
        "owner_result": None,
        "owner_notes": "",
    }


def build_experiment(
    read_data: dict[str, Any],
    harvest_payload: dict[str, Any],
    sources: list[dict[str, Any]],
    fact_embeddings: list[list[float]],
    inventory: list[dict[str, Any]],
    cache: V3Cache,
    advisor: TerraAdvisor,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    sentences = selected_sentences(read_data)
    source_by_id = {source["source_id"]: source for source in sources}
    source_titles = {
        source["source_id"]: source.get("title") or "Untitled source"
        for source in sources
    }
    source_units = {
        source["source_id"]: source_sentence_units(source["full_text"])
        for source in sources
    }
    source_unit_vectors, new_source_unit_embeddings = ensure_source_unit_embeddings(
        cache, source_units
    )
    fact_vector_by_id = {
        fact["fact_id"]: vector
        for fact, vector in zip(inventory, fact_embeddings, strict=True)
    }

    cards: list[dict[str, Any]] = []
    all_direct: list[dict[str, Any]] = []
    for sentence in sentences:
        claims = propose_decomposition(advisor, sentence)
        for claim in claims:
            if claim["type"] == "DIRECT_SOURCE_CLAIM":
                all_direct.append(claim)
        cards.append(
            {
                **sentence,
                "system_decomposition": {
                    "claims": claims,
                    "model": advisor.model,
                    "provider": advisor.provider,
                },
                "owner_decomposition": None,
                "owner_notes": "",
            }
        )

    new_query_embeddings, retrieval_stats = retrieve_candidates(
        all_direct,
        inventory,
        fact_embeddings,
        cache,
        source_titles,
    )
    for claim in all_direct:
        propose_relevance(advisor, claim)
        for candidate in claim["retrieval"]["candidates"]:
            label = candidate["system_relevance"]["label"]
            if label not in {"DIRECTLY_RELEVANT", "PARTIALLY_RELEVANT"}:
                continue
            source = source_by_id[candidate["source_id"]]
            propose_localization(
                advisor,
                claim,
                candidate,
                source["full_text"],
                source_units[candidate["source_id"]],
                fact_vector_by_id[candidate["fact_id"]],
                source_unit_vectors[candidate["source_id"]],
            )

    evidence_objects, dedup_stats = deduplicate_evidence(all_direct)
    evidence_by_id = {
        evidence["evidence_id"]: evidence for evidence in evidence_objects
    }
    for claim in all_direct:
        propose_direct_referee(advisor, claim, evidence_by_id)

    for card in cards:
        claims = card["system_decomposition"]["claims"]
        claims_by_id = {claim["claim_id"]: claim for claim in claims}
        for claim in claims:
            if claim["type"] == "SOURCE_GROUNDED_INFERENCE":
                propose_inference_referee(
                    advisor, claim, claims_by_id, evidence_by_id
                )
            elif claim["type"] == "WRITER_ANALYSIS":
                claim["analysis_result"] = "NO_SOURCE_VERIFICATION_REQUIRED"
            elif claim["type"] == "CORPUS_META":
                check_corpus_claim(
                    claim,
                    sources,
                    source_units,
                    source_unit_vectors,
                    cache,
                    advisor,
                )
        card["sentence_advisory"] = deterministic_advisory(claims)

    localized_lengths = [
        evidence["word_count"] for evidence in evidence_objects
    ]
    sentence_counts = [
        evidence["source_sentence_count"] for evidence in evidence_objects
    ]
    generation_stats = {
        **retrieval_stats,
        **dedup_stats,
        "new_query_embeddings": new_query_embeddings,
        "new_source_unit_embeddings": new_source_unit_embeddings,
        "full_source_unit_inventory": sum(len(units) for units in source_units.values()),
        "retrieval_candidate_occurrences": sum(
            len(claim["retrieval"]["candidates"]) for claim in all_direct
        ),
        "relevant_candidate_occurrences": sum(
            1
            for claim in all_direct
            for candidate in claim["retrieval"]["candidates"]
            if candidate["system_relevance"]["label"]
            in {"DIRECTLY_RELEVANT", "PARTIALLY_RELEVANT"}
        ),
        "no_supporting_span_found": sum(
            1
            for claim in all_direct
            for candidate in claim["retrieval"]["candidates"]
            if (candidate.get("evidence_proposal") or {}).get("status")
            == "NO_SUPPORTING_SPAN_FOUND"
        ),
        "localizations_where_lexical_search_helped": sum(
            1
            for claim in all_direct
            for candidate in claim["retrieval"]["candidates"]
            if (candidate.get("evidence_proposal") or {}).get("search_metadata", {}).get(
                "lexical_search_helped"
            )
        ),
        "localized_evidence_old_route_would_have_missed": sum(
            1
            for claim in all_direct
            for candidate in claim["retrieval"]["candidates"]
            if (candidate.get("evidence_proposal") or {}).get("search_metadata", {}).get(
                "old_routing_location_would_have_missed_final_evidence"
            )
        ),
        "corpus_claim_conceptual_results": dict(
            sorted(
                {
                    result: sum(
                        1
                        for card in cards
                        for claim in card["system_decomposition"]["claims"]
                        if claim["type"] == "CORPUS_META"
                        and claim["corpus_check"]["conceptual_result"] == result
                    )
                    for result in (
                        "POSSIBLE_COUNTEREXAMPLE_FOUND",
                        "NOTHING_FOUND",
                        "CHECK_INCOMPLETE",
                    )
                }.items()
            )
        ),
        "evidence_words": {
            "mean": round(statistics.mean(localized_lengths), 2)
            if localized_lengths
            else 0,
            "median": round(statistics.median(localized_lengths), 2)
            if localized_lengths
            else 0,
            "min": min(localized_lengths, default=0),
            "max": max(localized_lengths, default=0),
        },
        "evidence_sentence_counts": {
            "mean": round(statistics.mean(sentence_counts), 2)
            if sentence_counts
            else 0,
            "median": round(statistics.median(sentence_counts), 2)
            if sentence_counts
            else 0,
            "min": min(sentence_counts, default=0),
            "max": max(sentence_counts, default=0),
        },
        "claim_type_counts": dict(
            sorted(
                {
                    claim_type: sum(
                        1
                        for card in cards
                        for claim in card["system_decomposition"]["claims"]
                        if claim["type"] == claim_type
                    )
                    for claim_type in CLAIM_TYPES
                }.items()
            )
        ),
        "harvest_payload_sha256": stable_hash(harvest_payload["harvest"]),
    }
    return cards, evidence_objects, generation_stats


def html_document(dataset: dict[str, Any]) -> str:
    embedded = (
        json.dumps(dataset, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return HTML_TEMPLATE.replace("__EMBEDDED_DATA__", embedded)


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>D-038 semantic labeling v3</title>
<style>
:root{--paper:#eef1f3;--card:#fff;--ink:#172027;--muted:#61707b;--rule:#d5dde2;--accent:#8a5200;--soft:#fff2dc;--ok:#215d47;--oksoft:#e4f3ed;--warn:#8a5200;--bad:#8d2d2d;--src:#f6f8f9}
@media(prefers-color-scheme:dark){:root{--paper:#0e1519;--card:#172027;--ink:#e8eef1;--muted:#9aabb5;--rule:#31404a;--accent:#efad51;--soft:#2b2115;--ok:#8cc9ae;--oksoft:#162a22;--warn:#efad51;--bad:#f08f8f;--src:#11191e}}
*{box-sizing:border-box}body{margin:0;padding:0 18px 70px;overflow-x:hidden;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,system-ui,sans-serif}.wrap{max-width:980px;margin:auto}.wrap,.card,.panel,.row>*{min-width:0}header{padding:38px 0 18px}h1{font:500 clamp(28px,5vw,40px)/1.15 Georgia,serif;margin:0 0 10px}.lede{color:var(--muted);max-width:78ch}.bar{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--paper) 94%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--rule);padding:10px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.progress{font:12px ui-monospace,monospace}.spacer{flex:1}.card{margin-top:22px;background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:clamp(18px,4vw,28px)}.position,.eyebrow{font:12px ui-monospace,monospace;color:var(--accent)}.sentence{font:22px/1.5 Georgia,serif}.sentence,.meta,.fact,.raw{overflow-wrap:anywhere}.stages{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin:20px 0}.stage{padding:9px 4px;font-size:11px}.stage.done{border-color:var(--ok);background:var(--oksoft)}.stage.active{outline:2px solid var(--accent)}button,select,input,textarea{font:inherit;color:var(--ink)}button{cursor:pointer;border:1px solid var(--rule);border-radius:8px;padding:10px 13px;background:transparent;font-weight:650}button:hover{border-color:var(--accent);background:var(--soft)}button[aria-pressed=true]{border-color:var(--accent);background:var(--soft)}textarea,input,select{width:100%;border:1px solid var(--rule);border-radius:7px;padding:9px;background:var(--card)}textarea{min-height:78px;resize:vertical}.panel h2{font:600 21px Georgia,serif}.panel h3{margin:22px 0 7px}.system{background:var(--src);border:1px solid var(--rule);border-radius:9px;padding:14px;margin:10px 0}.claim,.candidate,.evidence{border-top:1px solid var(--rule);padding:15px 0}.meta{font:11px ui-monospace,monospace;color:var(--muted)}.fact{font-weight:600}.raw{white-space:pre-wrap;border-left:3px solid var(--rule);padding-left:12px;color:var(--muted)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.tri{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.choices{display:flex;gap:7px;flex-wrap:wrap}.choices button{font-size:12px}.row{display:grid;grid-template-columns:180px 1fr auto;gap:8px;align-items:start;margin:8px 0}.nav{display:flex;justify-content:space-between;gap:10px;margin-top:20px}.nav div{display:flex;gap:8px}.notice{padding:11px;border-radius:8px;background:var(--soft);color:var(--warn)}.status{font-weight:700}.complete{color:var(--ok)}.incomplete{color:var(--warn)}.danger{color:var(--bad)}[hidden]{display:none!important}
@media(max-width:720px){.stages{grid-template-columns:repeat(4,1fr)}.grid,.tri,.row{grid-template-columns:1fr}.bar .spacer{display:none}.bar{align-items:stretch}.bar button{flex:1}.nav{flex-direction:column}.nav div{display:grid;grid-template-columns:1fr 1fr}.nav button{width:100%}}
</style>
</head>
<body><main class="wrap">
<header><h1>Semantic labeling v3</h1><p class="lede">Post-write verification of the same 15 D-038 sentences. Work stage by stage. System proposals stay separate from your corrections. Similarity finds candidates; evidence decides support; UNVERIFIED never means FALSE.</p><div class="meta" id="version"></div></header>
<div class="bar"><span class="progress"><b id="sentenceProgress"></b> · <span id="completionProgress"></span></span><span class="spacer"></span><button id="reset">Reset v3 labels</button><button id="export">Export labeled JSON</button></div>
<article class="card" id="card" tabindex="-1"><div class="position" id="position"></div><p class="sentence" id="sentence"></p><div class="stages" id="stages"></div><section class="panel" id="panel"></section><label><span class="eyebrow">OWNER NOTES FOR THIS SENTENCE</span><textarea id="notes"></textarea></label><nav class="nav"><div><button id="prevSentence">Previous sentence</button><button id="nextSentence">Next sentence</button></div><div><button id="prevStage">Previous stage</button><button id="nextStage">Next stage</button></div></nav></article>
</main>
<script>
const DATA=__EMBEDDED_DATA__;
const FRIENDLY_LABELS={
DIRECT_SOURCE_CLAIM:"Source-based fact",SOURCE_GROUNDED_INFERENCE:"Conclusion drawn from the research",WRITER_ANALYSIS:"Writer's analysis",CORPUS_META:"Claim about the research itself",
DIRECTLY_RELEVANT:"Clearly relevant",PARTIALLY_RELEVANT:"Somewhat relevant",NOT_RELEVANT:"Not relevant",UNCLEAR:"Not sure",
SUPPORTED:"Supported",PARTIALLY_SUPPORTED:"Partly supported",CONFLICT:"Evidence says something different",INSUFFICIENT_EVIDENCE:"Not enough evidence",
REASONABLE_INFERENCE:"Conclusion makes sense",OVERSTATED_PARTIAL:"Conclusion goes too far",DOES_NOT_FOLLOW:"Conclusion doesn't follow",INSUFFICIENT_PREMISES:"Not enough information to judge",
NO_SUPPORTING_SPAN_FOUND:"Couldn't find the source passage",POSSIBLE_COUNTEREXAMPLE_FOUND:"Possible counterexample found",NOTHING_FOUND:"Nothing found — absence not proven",CHECK_INCOMPLETE:"Check incomplete",
CORPUS_CLAIM_VERIFIED:"No counterexample found — absence not proven",COUNTEREXAMPLE_FOUND:"Possible counterexample found",CORPUS_CHECK_INCOMPLETE:"Not proven — needs review",
SEMANTIC_CONFLICT:"Semantic problem found",PARTIAL_WARNING:"Partial-support warning",UNVERIFIED:"Not verified",NOTHING_FOUND_AGAINST:"Nothing found against this — absence not proven",NO_SEMANTIC_ISSUE_FOUND:"No semantic issue found",NO_SOURCE_VERIFICATION_REQUIRED:"No source verification required",
SUFFICIENT:"Sufficient",TOO_BROAD:"Too broad",MISSING_NEEDED_CONTEXT:"Missing needed context",DOES_NOT_SUPPORT_FACT:"Doesn't support the fact",CORRECTLY_GROUPED:"Correctly grouped",SHOULD_BE_SEPARATE:"Should be separate",MISSING_DUPLICATE:"Missing duplicate",
ACCEPT:"Accept",WRONG_BOUNDARY:"Wrong boundary",WRONG_TYPE:"Wrong type",MISSING_CLAIM:"Missing claim",SHOULD_BE_ONE_CLAIM:"Should be one claim",CORRECT_PREMISE:"Correct premise",WRONG_PREMISE:"Wrong premise",MISSING_PREMISE:"Missing premise",FALSE_CONFLICT:"False conflict",MISSED_CONFLICT:"Missed conflict"
};
function friendly(value){const text=String(value??"");return FRIENDLY_LABELS[value]||(/^[A-Z0-9_]+$/.test(text)?text.replaceAll("_"," ").toLowerCase().replace(/^./,c=>c.toUpperCase()):text)}
const STORAGE_KEY="semantic-labeling-v3:2:"+DATA.metadata.artifact_sha256;
const STAGE_NAMES=["Decompose","Retrieve","Relevance","Localize","Dedup","Direct referee","Inference / corpus","Advisory"];
const byId=id=>document.getElementById(id);
let currentSentence=0,currentStage=0,state={};
try{state=JSON.parse(localStorage.getItem(STORAGE_KEY)||"{}")||{}}catch(_){state={}}
const clone=value=>JSON.parse(JSON.stringify(value));
const el=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node};
function systemClaims(item){return item.system_decomposition.claims}
function defaultSentenceState(item){return {decomposition_review:null,owner_decomposition:clone(systemClaims(item)),premise_link_judgments:{},direct_claims:{},evidence_grouping:{},direct_referees:{},inference_referees:{},corpus_checks:{},sentence_advisory:null,notes:""}}
function answer(item){if(!state[item.sentence_id])state[item.sentence_id]=defaultSentenceState(item);return state[item.sentence_id]}
function save(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}catch(_){}}
function directClaims(item){return systemClaims(item).filter(c=>c.type==="DIRECT_SOURCE_CLAIM")}
function inferenceClaims(item){return systemClaims(item).filter(c=>c.type==="SOURCE_GROUNDED_INFERENCE")}
function corpusClaims(item){return systemClaims(item).filter(c=>c.type==="CORPUS_META")}
function relevantCandidates(claim){return claim.retrieval.candidates.filter(c=>["DIRECTLY_RELEVANT","PARTIALLY_RELEVANT"].includes(c.system_relevance.label))}
function selectField(options,value,onchange){const select=el("select");const empty=el("option",null,"Choose…");empty.value="";select.append(empty);options.forEach(option=>{const node=el("option",null,friendly(option));node.value=option;node.selected=option===value;select.append(node)});select.addEventListener("change",()=>onchange(select.value||null));return select}
function choiceButtons(options,value,onchange){const box=el("div","choices");options.forEach(option=>{const button=el("button",null,friendly(option));button.type="button";button.setAttribute("aria-pressed",String(value===option));button.addEventListener("click",()=>onchange(option));box.append(button)});return box}
function ensureClaimState(a,claim){if(!a.direct_claims[claim.claim_id])a.direct_claims[claim.claim_id]={missing_fact_or_evidence:false,candidates:{}};return a.direct_claims[claim.claim_id]}
function ensureCandidateState(a,claim,candidate){const cs=ensureClaimState(a,claim);if(!cs.candidates[candidate.fact_id])cs.candidates[candidate.fact_id]={owner_relevance:null,owner_evidence_localization:null,owner_start_sentence_index:null,owner_end_sentence_index:null};return cs.candidates[candidate.fact_id]}
function stageComplete(item,a,index){if(index===0){if(!a.decomposition_review||!a.owner_decomposition.length)return false;return inferenceClaims(item).every(c=>!!a.premise_link_judgments[c.claim_id])}if(index===1)return true;if(index===2)return directClaims(item).every(c=>c.retrieval.candidates.every(f=>!!ensureCandidateState(a,c,f).owner_relevance));if(index===3)return directClaims(item).every(c=>relevantCandidates(c).every(f=>!!ensureCandidateState(a,c,f).owner_evidence_localization));if(index===4)return DATA.evidence_objects.filter(e=>e.routed_claim_ids.some(id=>systemClaims(item).some(c=>c.claim_id===id))).every(e=>!!a.evidence_grouping[e.evidence_id]);if(index===5)return directClaims(item).every(c=>!!a.direct_referees[c.claim_id]?.owner_result);if(index===6)return inferenceClaims(item).every(c=>!!a.inference_referees[c.claim_id]?.owner_result)&&corpusClaims(item).every(c=>!!a.corpus_checks[c.claim_id]);if(index===7)return !!a.sentence_advisory;return false}
function sentenceComplete(item){const a=answer(item);return STAGE_NAMES.every((_,i)=>stageComplete(item,a,i))}
function heading(title,help){const h=el("h2",null,title);const p=el("p","lede",help);return [h,p]}
function systemBox(label,value){const box=el("div","system");box.append(el("div","eyebrow",label),el("div","status",friendly(value)));return box}
function renderStage1(panel,item,a){panel.append(...heading("Stage 1 · Claim decomposition","Review Terra’s proposal, then correct a separate owner copy. Keep qualifiers and inference premise links."));panel.append(systemBox("SYSTEM MODEL",item.system_decomposition.provider+" · "+item.system_decomposition.model));systemClaims(item).forEach(c=>{const box=el("div","claim");box.append(el("div","meta",c.claim_id+" · "+friendly(c.type)),el("div",null,c.text));if(c.derived_from_claim_ids.length)box.append(el("div","meta","Premises: "+c.derived_from_claim_ids.join(", ")));panel.append(box)});panel.append(el("h3",null,"Overall proposal judgment"),choiceButtons(["ACCEPT","WRONG_BOUNDARY","WRONG_TYPE","MISSING_CLAIM","SHOULD_BE_ONE_CLAIM"],a.decomposition_review,v=>{a.decomposition_review=v;save();render()}),el("h3",null,"Owner-corrected claims"));a.owner_decomposition.forEach((c,index)=>{const row=el("div","row");const type=selectField([...DATA.metadata.allowed_claim_types],c.type,v=>{c.type=v;save()});const text=el("textarea");text.value=c.text;text.addEventListener("input",()=>{c.text=text.value;save()});const del=el("button",null,"Delete");del.type="button";del.addEventListener("click",()=>{a.owner_decomposition.splice(index,1);save();render()});row.append(type,text,del);panel.append(row);if(c.type==="SOURCE_GROUNDED_INFERENCE"){const label=el("label");label.append(el("div","eyebrow","EDIT PREMISE CLAIM IDS (comma-separated)"));const input=el("input");input.value=(c.derived_from_claim_ids||[]).join(", ");input.addEventListener("input",()=>{c.derived_from_claim_ids=input.value.split(",").map(x=>x.trim()).filter(Boolean);save()});label.append(input);panel.append(label)}});const add=el("button",null,"Add missing claim");add.type="button";add.addEventListener("click",()=>{a.owner_decomposition.push({claim_id:item.sentence_id+":OWNER_"+(a.owner_decomposition.length+1),type:"DIRECT_SOURCE_CLAIM",text:"",derived_from_claim_ids:[]});save();render()});panel.append(add);if(inferenceClaims(item).length)panel.append(el("h3",null,"Inference-link judgments"));inferenceClaims(item).forEach(c=>{const box=el("div","claim");box.append(el("div","meta",c.claim_id+" · "+c.derived_from_claim_ids.join(", ")),choiceButtons(["CORRECT_PREMISE","WRONG_PREMISE","MISSING_PREMISE"],a.premise_link_judgments[c.claim_id],v=>{a.premise_link_judgments[c.claim_id]=v;save();render()}));panel.append(box)})}
function renderStage2(panel,item){panel.append(...heading("Stage 2 · Broad retrieval","Code retrieved top 10 exact plus top 10 actor-masked per source-based fact, then deduplicated only exact fact ID. Scores measure retrieval, never truth."));directClaims(item).forEach(c=>{panel.append(systemBox(c.claim_id,c.text));const counts={exact:0,actor_masked:0,both:0};c.retrieval.candidates.forEach(f=>counts[f.retrieved_by]++);panel.append(el("p","meta",`${c.retrieval.candidates.length} union candidates · exact ${counts.exact} · masked ${counts.actor_masked} · both ${counts.both} · no floor`))});if(!directClaims(item).length)panel.append(el("p","notice","No source-based fact was proposed, so retrieval is not exercised for this sentence."))}
function renderStage3(panel,item,a){panel.append(...heading("Stage 3 · Claim ↔ fact relevance","Judge relevance without seeing raw passages. Contradictions are relevant. Support is a different question."));directClaims(item).forEach(c=>{const cs=ensureClaimState(a,c);panel.append(systemBox(c.claim_id,c.text));const missing=el("label","notice");const check=el("input");check.type="checkbox";check.style.width="auto";check.checked=cs.missing_fact_or_evidence;check.addEventListener("change",()=>{cs.missing_fact_or_evidence=check.checked;save()});missing.append(check,document.createTextNode(" MISSING THE FACT/EVIDENCE I NEED"));panel.append(missing);c.retrieval.candidates.forEach(f=>{const fs=ensureCandidateState(a,c,f),box=el("div","candidate");box.append(el("div","meta",`#${f.union_rank} · ${f.fact_id} · ${f.source_id} · ${f.retrieved_by} · best ${f.best_embedding_score.toFixed(3)}`),el("div","fact",f.fact_text),systemBox("SYSTEM RELEVANCE",f.system_relevance.label),selectField([...DATA.metadata.allowed_relevance_labels],fs.owner_relevance,v=>{fs.owner_relevance=v;save();render()}));panel.append(box)})});if(!directClaims(item).length)panel.append(el("p","notice","Not exercised: no direct claims."))}
function renderStage4(panel,item,a){panel.append(...heading("Stage 4 · Precise evidence localization","For relevant candidates, judge the smallest proposed raw span. The whole known source was searched; a miss does not mean the fact is false."));let shown=0;directClaims(item).forEach(c=>relevantCandidates(c).forEach(f=>{shown++;const fs=ensureCandidateState(a,c,f),box=el("div","evidence");box.append(el("div","meta",`${c.claim_id} · ${f.fact_id} · ${f.source_id}`),el("div","fact",f.fact_text));const p=f.evidence_proposal;if(p.status==="SPAN_FOUND"){box.append(el("div","raw",p.exact_raw_text),el("div","meta",`${p.word_count} words · ${p.source_sentence_count} sentence(s) · chars ${p.start_char}-${p.end_char} · semantic rank ${p.search_metadata.winning_semantic_rank}`))}else box.append(el("p","notice",friendly("NO_SUPPORTING_SPAN_FOUND")+": "+p.system_reason));box.append(selectField([...DATA.metadata.allowed_localization_labels],fs.owner_evidence_localization,v=>{fs.owner_evidence_localization=v;save();render()}));if(p.status==="SPAN_FOUND"){const grid=el("div","grid");["start","end"].forEach(which=>{const label=el("label");label.append(el("div","eyebrow","OWNER "+which.toUpperCase()+" SENTENCE INDEX"));const input=el("input");input.type="number";input.value=fs["owner_"+which+"_sentence_index"]??p[which+"_sentence_index"];input.addEventListener("input",()=>{fs["owner_"+which+"_sentence_index"]=input.value===""?null:Number(input.value);save()});label.append(input);grid.append(label)});box.append(grid)}panel.append(box)}));if(!shown)panel.append(el("p","notice","Not exercised: no candidates survived the relevance review."))}
function sentenceEvidence(item){const ids=new Set(systemClaims(item).map(c=>c.claim_id));return DATA.evidence_objects.filter(e=>e.routed_claim_ids.some(id=>ids.has(id)))}
function renderStage5(panel,item,a){panel.append(...heading("Stage 5 · Evidence identity / dedup","A fact is not evidence. Review code’s exact source/span grouping. Different sources are never merged."));const evidence=sentenceEvidence(item);evidence.forEach(e=>{const box=el("div","evidence");box.append(el("div","meta",`${e.evidence_id} · ${e.source_id} · ${e.occurrence_ids.length} occurrence(s)`),el("div","raw",e.exact_raw_text),el("div","meta","Facts: "+e.supporting_fact_ids.join(", ")),selectField([...DATA.metadata.allowed_grouping_labels],a.evidence_grouping[e.evidence_id],v=>{a.evidence_grouping[e.evidence_id]=v;save();render()}));panel.append(box)});if(!evidence.length)panel.append(el("p","notice","Not exercised: no localized evidence objects for this sentence."))}
function renderStage6(panel,item,a){panel.append(...heading("Stage 6 · Direct claim referee","Compare each source-based fact to localized evidence. Not enough evidence does not mean false; disagreement remains visible."));directClaims(item).forEach(c=>{const sys=c.direct_referee.system_result,box=el("div","claim");box.append(el("div","meta",c.claim_id),el("div","fact",c.text),systemBox("SYSTEM RESULT",sys.status),el("p",null,sys.reason));if(sys.mismatch_dimensions?.length)box.append(el("div","meta","Mismatch dimensions: "+sys.mismatch_dimensions.map(friendly).join(", ")));if(sys.conflicting_evidence)box.append(el("p","notice","Conflicting evidence preserved"));const current=a.direct_referees[c.claim_id]||{owner_result:null,flags:[],notes:""};a.direct_referees[c.claim_id]=current;box.append(selectField([...DATA.metadata.allowed_direct_results],current.owner_result,v=>{current.owner_result=v;save();render()}),choiceButtons(["FALSE_CONFLICT","MISSED_CONFLICT"],current.flags[0]||null,v=>{current.flags=[v];save();render()}));const notes=el("textarea");notes.placeholder="Optional correction notes";notes.value=current.notes;notes.addEventListener("input",()=>{current.notes=notes.value;save()});box.append(notes);panel.append(box)});if(!directClaims(item).length)panel.append(el("p","notice","Not exercised: no source-based facts."))}
function renderStage7(panel,item,a){panel.append(...heading("Stage 7 · Conclusions and research-content checks","Judge whether each conclusion was earned from its premises. Claims about the research use a full-corpus counterexample search; finding nothing never proves absence."));inferenceClaims(item).forEach(c=>{const sys=c.inference_referee.system_result,box=el("div","claim");box.append(el("div","meta",c.claim_id+" · premises "+c.derived_from_claim_ids.join(", ")),el("div","fact",c.text),systemBox("SYSTEM CONCLUSION RESULT",sys.status),el("p",null,sys.reason));const current=a.inference_referees[c.claim_id]||{owner_result:null,derived_from_claim_ids:clone(c.derived_from_claim_ids),notes:""};a.inference_referees[c.claim_id]=current;box.append(selectField([...DATA.metadata.allowed_inference_results],current.owner_result,v=>{current.owner_result=v;save();render()}));const label=el("label");label.append(el("div","eyebrow","OWNER PREMISE LINKS"));const input=el("input");input.value=current.derived_from_claim_ids.join(", ");input.addEventListener("input",()=>{current.derived_from_claim_ids=input.value.split(",").map(x=>x.trim()).filter(Boolean);save()});label.append(input);box.append(label);panel.append(box)});corpusClaims(item).forEach(c=>{const sys=c.corpus_check,box=el("div","claim");box.append(el("div","meta",c.claim_id+" · "+sys.sources_checked+" sources searched"),el("div","fact",c.text),systemBox("SYSTEM RESEARCH-CONTENT RESULT",sys.conceptual_result),el("p","meta","Searched for: "+sys.positive_proposition));if(sys.counterexamples.length){box.append(el("p","notice","Possible counterexamples for owner inspection:"));sys.counterexamples.forEach(x=>{const evidence=el("div","evidence");evidence.append(el("div","meta",x.source_id+" · sentences "+x.start_sentence_index+"-"+x.end_sentence_index+" · semantic rank "+(x.semantic_anchor_ranks[0]??"outside semantic top")),el("div","raw",x.exact_raw_text),el("p",null,x.model_reason));box.append(evidence)})}else box.append(el("p","notice","Nothing was found in the reviewed candidates. This does not prove the research lacks it."));box.append(selectField([...DATA.metadata.allowed_corpus_results],a.corpus_checks[c.claim_id],v=>{a.corpus_checks[c.claim_id]=v;save();render()}));panel.append(box)});if(!inferenceClaims(item).length&&!corpusClaims(item).length)panel.append(el("p","notice","Not exercised: no conclusion drawn from research or claim about the research itself."))}
function renderStage8(panel,item,a){panel.append(...heading("Stage 8 · Deterministic sentence advisory","Code combines claim-unit proposals. No extra model makes a whole-sentence verdict, and nothing edits the Read."));const sys=item.sentence_advisory;panel.append(systemBox("CODE ADVISORY",sys.deterministic_status),el("p","meta","Triggering claims: "+(sys.triggering_claim_ids.join(", ")||"none")),el("h3",null,"Owner sentence advisory"),selectField([...DATA.metadata.allowed_sentence_advisories],a.sentence_advisory,v=>{a.sentence_advisory=v;save();render()}))}
const renderers=[renderStage1,renderStage2,renderStage3,renderStage4,renderStage5,renderStage6,renderStage7,renderStage8];
function render(focus=false){const item=DATA.sentences[currentSentence],a=answer(item);byId("version").textContent=DATA.metadata.current_read_identifier+" · "+DATA.metadata.judge.provider+"/"+DATA.metadata.judge.model;byId("sentenceProgress").textContent=(currentSentence+1)+" / "+DATA.sentences.length;const complete=DATA.sentences.filter(sentenceComplete).length;byId("completionProgress").textContent=complete+" sentences complete";byId("position").textContent=item.sentence_id+" · "+item.paragraph_label+" · paragraph "+item.paragraph_index+", sentence "+item.sentence_index_in_paragraph;byId("sentence").textContent=item.sentence;const stages=byId("stages");stages.replaceChildren();STAGE_NAMES.forEach((name,index)=>{const button=el("button","stage "+(stageComplete(item,a,index)?"done ":"")+(currentStage===index?"active":""),(index+1)+". "+name);button.type="button";button.addEventListener("click",()=>{currentStage=index;render()});stages.append(button)});const panel=byId("panel");panel.replaceChildren();renderers[currentStage](panel,item,a);byId("notes").value=a.notes;byId("prevSentence").disabled=currentSentence===0;byId("nextSentence").disabled=currentSentence===DATA.sentences.length-1;byId("prevStage").disabled=currentStage===0;byId("nextStage").disabled=currentStage===STAGE_NAMES.length-1;if(focus){byId("card").focus();scrollTo({top:0,behavior:"smooth"})}}
byId("notes").addEventListener("input",()=>{const item=DATA.sentences[currentSentence];answer(item).notes=byId("notes").value;save()});byId("prevSentence").addEventListener("click",()=>{if(currentSentence>0){currentSentence--;currentStage=0;render(true)}});byId("nextSentence").addEventListener("click",()=>{if(currentSentence<DATA.sentences.length-1){currentSentence++;currentStage=0;render(true)}});byId("prevStage").addEventListener("click",()=>{if(currentStage>0){currentStage--;render(true)}});byId("nextStage").addEventListener("click",()=>{if(currentStage<STAGE_NAMES.length-1){currentStage++;render(true)}});byId("reset").addEventListener("click",()=>{if(confirm("Reset all v3 owner labels?")){state={};localStorage.removeItem(STORAGE_KEY);render()}});byId("export").addEventListener("click",()=>{const payload=clone(DATA);payload.owner_labels_exported_at=new Date().toISOString();payload.owner_labels=DATA.sentences.map(item=>({sentence_id:item.sentence_id,...answer(item),stage_completion:STAGE_NAMES.map((name,index)=>({stage:index+1,name,complete:stageComplete(item,answer(item),index)}))}));const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}),url=URL.createObjectURL(blob),link=el("a");link.href=url;link.download="semantic_labeling_v3_labeled.json";document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)});render();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read", type=Path, default=DEFAULT_READ)
    parser.add_argument("--harvest", type=Path, default=DEFAULT_HARVEST)
    parser.add_argument("--source-vault", type=Path, default=DEFAULT_SOURCE_VAULT)
    parser.add_argument("--fact-cache", type=Path, default=DEFAULT_FACT_CACHE)
    parser.add_argument("--v3-cache", type=Path, default=DEFAULT_V3_CACHE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()

    read_data = read_json(args.read)
    harvest_payload = read_json(args.harvest)
    sources = read_source_vault(args.source_vault)
    if not isinstance(harvest_payload, dict) or "harvest" not in harvest_payload:
        raise RuntimeError("Frozen replay harvest is missing")
    harvest = harvest_payload["harvest"]
    inventory = build_inventory(harvest)
    if len(inventory) != 1270:
        raise RuntimeError(f"Expected frozen replay harvest of 1,270 facts; got {len(inventory)}")
    if len(sources) != 16 or sum(len(s["full_text"].split()) for s in sources) != 42263:
        raise RuntimeError("Frozen 16-source / 42,263-word source vault differs")
    samples = selected_sentences(read_data)
    if len(samples) != 15:
        raise RuntimeError("Frozen v2 sample no longer contains exactly 15 sentences")
    read_sha = stable_hash(read_data["read"])
    if read_sha != "ea8dfd6c18edb27d7f7dc85e5da6e9e193b528c8e16876c6481c585d00029b0e":
        raise RuntimeError("Frozen D-038 Read SHA differs")

    fact_embeddings, inventory_sha, dimensions = load_fact_embeddings(
        args.fact_cache, inventory
    )
    settings = get_settings()
    judge_model = settings.model_judge
    judge_provider = provider_for(judge_model)
    cache = V3Cache(
        args.v3_cache,
        read_sha256=read_sha,
        inventory_sha256=inventory_sha,
        judge_model=judge_model,
        judge_provider=judge_provider,
    )
    advisor = TerraAdvisor(cache, judge_model)
    cards, evidence_objects, generation_stats = build_experiment(
        read_data,
        harvest_payload,
        sources,
        fact_embeddings,
        inventory,
        cache,
        advisor,
    )
    source_vault_sha = stable_hash(
        [
            {key: source[key] for key in ("source_id", "title", "url", "full_text")}
            for source in sources
        ]
    )
    metadata: dict[str, Any] = {
        "schema_version": 3,
        "task": "post_write_semantic_verification_owner_labeling_v3",
        "architecture_order": [
            "research",
            "full_rich_research_packet",
            "writer",
            "finished_read",
            "semantic_verification",
        ],
        "code_decides_model_advises_model_never_gates": True,
        "verification_can_modify_writer_inputs": False,
        "verification_can_rewrite_read": False,
        "current_read_identifier": CURRENT_READ_IDENTIFIER,
        "decision": "D-038",
        "job_id": "hawara-rerun",
        "briefing_version": "1",
        "read_generated_on": "2026-08-22",
        "read_sha256": read_sha,
        "read_word_count": 1816,
        "read_paragraph_count": 9,
        "selected_sentence_count": 15,
        "selected_sentence_sha256": stable_hash(samples),
        "harvest": {
            "replayed_scratchpad_fact_count": 1270,
            "replayed_harvest_sha256": stable_hash(harvest),
            "accepted_live_d038_fact_count": 1253,
            "accepted_live_and_replay_are_identical": False,
        },
        "source_vault": {
            "source_count": 16,
            "word_count": 42263,
            "sha256": source_vault_sha,
        },
        "embedding": {
            "provider": "dashscope",
            "model": EMBEDDING_MODEL,
            "fact_cache": args.fact_cache.name,
            "fact_cache_reused": True,
            "fact_inventory_sha256": inventory_sha,
            "dimensions": dimensions,
            "v3_query_cache": args.v3_cache.name,
            "source_unit_embeddings_cached_in_v3_cache": True,
        },
        "judge": {
            "provider": judge_provider,
            "model": judge_model,
            "advisory_stages": [1, 3, 4, 6, 7],
            "calls_created_this_run": advisor.calls_created,
            "calls_reused_this_run": advisor.calls_reused,
            "input_tokens_created_this_run": advisor.input_tokens,
            "output_tokens_created_this_run": advisor.output_tokens,
        },
        "retrieval": {
            "claim_types_retrieved": ["DIRECT_SOURCE_CLAIM"],
            "routes": ["exact", "actor_masked_where_changed"],
            "top_per_route_before_union": TOP_PER_ROUTE,
            "similarity_threshold": None,
            "fact_deduplication": "exact FACT_ID only",
            "force_source_diversity": False,
            "similarity_is_correctness_verdict": False,
        },
        "localization": {
            "search_scope": "entire known source",
            "semantic_model": EMBEDDING_MODEL,
            "semantic_top_regions": LOCALIZATION_SEMANTIC_TOP,
            "lexical_top_regions_union": LOCALIZATION_LEXICAL_TOP,
            "similarity_threshold": None,
            "terra_selects_smallest_contiguous_sentence_count": [1, 3],
            "no_supporting_span_found_is_truth_verdict": False,
            "legacy_routing_used_only_for_miss_measurement": True,
        },
        "corpus_check": {
            "method": "full_corpus_semantic_counterexample_search",
            "semantic_model": EMBEDDING_MODEL,
            "semantic_top_regions": CORPUS_SEMANTIC_TOP,
            "lexical_top_regions_union": CORPUS_LEXICAL_TOP,
            "nothing_found_proves_absence": False,
            "conceptual_results": [
                "POSSIBLE_COUNTEREXAMPLE_FOUND",
                "NOTHING_FOUND",
                "CHECK_INCOMPLETE",
            ],
        },
        "evidence_identity": {
            "fields": [
                "source_id",
                "start_char",
                "end_char",
                "normalized_evidence_text",
            ],
            "cross_source_deduplication": False,
            "independent_event_identity_deferred": True,
        },
        "allowed_claim_types": list(CLAIM_TYPES),
        "allowed_relevance_labels": list(RELEVANCE_LABELS),
        "allowed_localization_labels": [
            "SUFFICIENT",
            "TOO_BROAD",
            "MISSING_NEEDED_CONTEXT",
            "DOES_NOT_SUPPORT_FACT",
            "UNCLEAR",
        ],
        "allowed_grouping_labels": [
            "CORRECTLY_GROUPED",
            "SHOULD_BE_SEPARATE",
            "MISSING_DUPLICATE",
        ],
        "allowed_direct_results": list(DIRECT_RESULTS),
        "allowed_inference_results": list(INFERENCE_RESULTS),
        "allowed_corpus_results": [
            "CORPUS_CLAIM_VERIFIED",
            "COUNTEREXAMPLE_FOUND",
            "CORPUS_CHECK_INCOMPLETE",
        ],
        "allowed_sentence_advisories": [
            "SEMANTIC_CONFLICT",
            "PARTIAL_WARNING",
            "UNVERIFIED",
            "NOTHING_FOUND_AGAINST",
            "NO_SEMANTIC_ISSUE_FOUND",
            "NO_SOURCE_VERIFICATION_REQUIRED",
        ],
        "generation_statistics": generation_stats,
        "built_at": datetime.now(UTC).isoformat(),
    }
    metadata["artifact_sha256"] = stable_hash(
        {
            "sentences": cards,
            "evidence_objects": evidence_objects,
            "read_sha256": read_sha,
            "inventory_sha256": inventory_sha,
            "judge_model": judge_model,
        }
    )
    dataset = {
        "metadata": metadata,
        "sentences": cards,
        "evidence_objects": evidence_objects,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.html_output.write_text(html_document(dataset), encoding="utf-8")
    cache.prune_unused()
    cache.save()
    print(
        json.dumps(
            {
                "read_sha256": read_sha,
                "sentences": len(cards),
                "facts": len(inventory),
                "judge": f"{judge_provider}/{judge_model}",
                "direct_claims": generation_stats["direct_claims"],
                "retrieval_candidate_occurrences": generation_stats[
                    "retrieval_candidate_occurrences"
                ],
                "localized_occurrences": generation_stats[
                    "raw_localized_evidence_occurrences"
                ],
                "unique_evidence_ids": generation_stats["unique_evidence_ids"],
                "cache": str(args.v3_cache),
                "json": str(args.json_output),
                "html": str(args.html_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
