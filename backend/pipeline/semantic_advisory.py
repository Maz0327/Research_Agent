"""Post-Read semantic advisory — the deterministic spine of the v3 checker.

Ported from the validated v3 experiment (scratchpad/build_semantic_labeling_v3.py
at 246fbaa) under decisions D-SEM-5/6/7: the deterministic lanes are the trusted
spine; model outputs are ADVISORY inputs carried as flags; **nothing here gates,
blocks, or edits a Read** — this module only assembles a report.

Doctrine preserved:
- code decides, a model advises, a model never gates;
- similarity finds suspects; it never convicts;
- unverified does not mean false; a failed search is a search state, not a verdict;
- one evidence span = one confirmation (same source + same span never counts twice);
- a passage that CONFIRMS a negative corpus claim is never a counterexample to it;
- single-call model judgments are noisy (D-SEM-6): referee statuses arriving here
  are advisory and are surfaced with that caveat, never hardened into truth.

The model-call orchestration (decomposition, relevance, span pick, referees,
corpus relation) lives with the caller; this module consumes their outputs and
performs every downstream decision deterministically.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from typing import Any

# Tuning constants proven in the v3 experiment (kept for reproducibility).
LOCALIZATION_SEMANTIC_TOP = 10
LOCALIZATION_LEXICAL_TOP = 5
LOCALIZATION_REGION_RADIUS = 2

SENTENCE_ADVISORIES = [
    "SEMANTIC_CONFLICT",
    "PARTIAL_WARNING",
    "UNVERIFIED",
    "NOTHING_FOUND_AGAINST",
    "NO_SEMANTIC_ISSUE_FOUND",
    "NO_SOURCE_VERIFICATION_REQUIRED",
]

CORPUS_RELATIONS = {"CONTRADICTS_CLAIM", "SUPPORTS_CLAIM", "UNRELATED"}

ADVISORY_RULE = "code_aggregation_v3_corpus_conceptual_nothing_found_tier"

REFEREE_NOISE_CAVEAT = (
    "Referee statuses are single-call model judgments and are empirically noisy "
    "(D-SEM-6); treat them as advisory flags, not verdicts."
)


def normalized(text: str) -> str:
    """Collapse all whitespace so span text compares stably."""
    return " ".join(text.split())


def stable_hash(value: Any) -> str:
    """Deterministic sha256 of any JSON-serializable value."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def cosine(left: list[float], right: list[float]) -> float:
    """Cosine similarity; 0.0 when either vector is empty or zero."""
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def source_sentence_units(text: str) -> list[dict[str, Any]]:
    """Split raw source text deterministically while preserving exact offsets.

    Sentences end at ./!/? followed by whitespace (closing quotes/brackets
    absorbed) or at blank lines. Punctuation-free stretches longer than 120
    words become bounded 60-word transcript units so transcripts stay
    searchable. Offsets always slice the original text exactly.
    """
    units: list[dict[str, Any]] = []

    def append_segment(segment_start: int, segment_end: int) -> None:
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


def full_source_candidate_regions(
    fact_tokens: set[str],
    fact_vector: list[float],
    units: list[dict[str, Any]],
    unit_vectors: list[list[float]],
    unit_token_sets: list[set[str]] | None = None,
    *,
    semantic_top: int = LOCALIZATION_SEMANTIC_TOP,
    lexical_top: int = LOCALIZATION_LEXICAL_TOP,
    radius: int = LOCALIZATION_REGION_RADIUS,
) -> list[dict[str, Any]]:
    """Search every unit of the known source; return ranked compact regions.

    Broad-by-default per the locked v3 decision: the whole known source is
    scored semantically, a lexical union adds recall, and compact regions
    (anchor ± radius) are returned for a model to pick the minimal span from.
    Scores are routing metadata only, never correctness judgments.
    """
    if len(units) != len(unit_vectors) or not units:
        raise ValueError("full-source search received mismatched source units/vectors")
    semantic_scores = [cosine(fact_vector, vector) for vector in unit_vectors]
    semantic_order = sorted(range(len(units)), key=lambda i: (-semantic_scores[i], i))
    semantic_rank = {i: rank for rank, i in enumerate(semantic_order, start=1)}
    if unit_token_sets is None:
        unit_token_sets = [set(unit["text"].lower().split()) for unit in units]
    lexical_scores = [
        len(fact_tokens & tokens) / max(1, len(fact_tokens)) for tokens in unit_token_sets
    ]
    lexical_order = sorted(
        (i for i, score in enumerate(lexical_scores) if score > 0),
        key=lambda i: (-lexical_scores[i], i),
    )
    lexical_rank = {i: rank for rank, i in enumerate(lexical_order, start=1)}

    regions: dict[tuple[int, int], dict[str, Any]] = {}
    for route, anchors in (("semantic", semantic_order[:semantic_top]), ("lexical", lexical_order[:lexical_top])):
        for anchor in anchors:
            start = max(0, anchor - radius)
            end = min(len(units) - 1, anchor + radius)
            region = regions.setdefault(
                (start, end),
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
            if region["best_embedding_score"] is None or score > region["best_embedding_score"]:
                region["best_embedding_score"] = score

    ordered = sorted(
        regions.values(),
        key=lambda region: (
            min(region["semantic_anchor_ranks"], default=10**9),
            min(region["lexical_anchor_ranks"], default=10**9),
            region["start_sentence_index"],
        ),
    )
    for number, region in enumerate(ordered, start=1):
        region["region_id"] = f"R{number:02d}"
        region["semantic_anchor_ranks"].sort()
        region["lexical_anchor_ranks"].sort()
        region["retrieved_by"] = "both" if len(region["retrieved_by"]) == 2 else region["retrieved_by"][0]
        region["best_embedding_score"] = round(float(region["best_embedding_score"]), 6)
    return ordered


def evidence_identity(proposal: dict[str, Any]) -> str:
    """Stable identity for an exact source span: source + offsets + text."""
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
    """Collapse located spans into unique evidence objects.

    Same source + same exact span (or a contained span for the exact same fact
    text under the same claim) = ONE evidence object. Different sources are
    never merged, however similar the wording — cross-source agreement is
    corroboration, not duplication.
    """
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
                and normalized(pa["exact_raw_text"]) == normalized(pb["exact_raw_text"])
            )
            contained = (
                a["claim_id"] == b["claim_id"]
                and normalized(a["fact_text"]) == normalized(b["fact_text"])
                and (
                    (pa["start_char"] <= pb["start_char"] and pa["end_char"] >= pb["end_char"])
                    or (pb["start_char"] <= pa["start_char"] and pb["end_char"] >= pa["end_char"])
                )
            )
            if same_span or contained:
                union(left, right)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(occurrences)):
        groups[find(index)].append(index)

    evidence_objects: list[dict[str, Any]] = []
    for member_indices in sorted(groups.values(), key=min):
        canonical_index = min(
            member_indices,
            key=lambda i: (
                len(occurrences[i]["proposal"]["exact_raw_text"].split()),
                occurrences[i]["proposal"]["end_char"] - occurrences[i]["proposal"]["start_char"],
                occurrences[i]["occurrence_id"],
            ),
        )
        canonical = occurrences[canonical_index]["proposal"]
        evidence_objects.append(
            {
                "evidence_id": evidence_identity(canonical),
                "source_id": canonical["source_id"],
                "exact_raw_text": canonical["exact_raw_text"],
                "start_char": canonical["start_char"],
                "end_char": canonical["end_char"],
                "supporting_fact_ids": sorted({occurrences[i]["fact_id"] for i in member_indices}),
                "routed_claim_ids": sorted({occurrences[i]["claim_id"] for i in member_indices}),
                "occurrence_ids": sorted(occurrences[i]["occurrence_id"] for i in member_indices),
            }
        )
    stats = {
        "raw_localized_evidence_occurrences": len(occurrences),
        "unique_evidence_ids": len(evidence_objects),
        "duplicates_eliminated": len(occurrences) - len(evidence_objects),
    }
    return evidence_objects, stats


def route_corpus_relations(
    candidate_windows: list[dict[str, Any]],
    relations_by_id: dict[str, str],
) -> dict[str, Any]:
    """Directional corpus routing: only CONTRADICTS_CLAIM is a counterexample.

    A passage supporting a negative corpus claim (relation SUPPORTS_CLAIM) is
    confirming evidence and must never be escalated as a conflict — the S09
    lesson. No result means "nothing found", never "absence proven".
    """
    counterexamples: list[dict[str, Any]] = []
    confirming: list[dict[str, Any]] = []
    for window in candidate_windows:
        relation = relations_by_id.get(window["candidate_id"])
        if relation not in CORPUS_RELATIONS:
            raise ValueError(f"invalid corpus relation {relation!r} for {window['candidate_id']}")
        window = dict(window, model_relation=relation)
        if relation == "CONTRADICTS_CLAIM":
            counterexamples.append(window)
        elif relation == "SUPPORTS_CLAIM":
            confirming.append(window)
    conceptual = "POSSIBLE_COUNTEREXAMPLE_FOUND" if counterexamples else "NOTHING_FOUND"
    return {
        "conceptual_result": conceptual,
        "counterexamples": counterexamples,
        "confirming_passages": confirming,
        "nothing_found_is_proof_of_absence": False,
    }


def deterministic_advisory(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-claim advisory results into one sentence-level advisory.

    Ladder (first match wins): SEMANTIC_CONFLICT (direct CONFLICT, inference
    DOES_NOT_FOLLOW, corpus counterexample) > PARTIAL_WARNING (partial support,
    overstated inference) > UNVERIFIED (insufficient evidence/premises, corpus
    check incomplete) > NOTHING_FOUND_AGAINST (negative corpus claims searched
    clean) > NO_SEMANTIC_ISSUE_FOUND > NO_SOURCE_VERIFICATION_REQUIRED (pure
    analysis). Pure code; no model re-judges the sentence.
    """
    direct = [c for c in claims if c["type"] == "DIRECT_SOURCE_CLAIM"]
    inferences = [c for c in claims if c["type"] == "SOURCE_GROUNDED_INFERENCE"]
    corpus = [c for c in claims if c["type"] == "CORPUS_META"]
    direct_status = {c["claim_id"]: c["direct_referee"]["system_result"]["status"] for c in direct}
    inference_status = {
        c["claim_id"]: c["inference_referee"]["system_result"]["status"] for c in inferences
    }
    corpus_status = {c["claim_id"]: c["corpus_check"]["conceptual_result"] for c in corpus}

    triggers = (
        [cid for cid, s in direct_status.items() if s == "CONFLICT"]
        + [cid for cid, s in inference_status.items() if s == "DOES_NOT_FOLLOW"]
        + [cid for cid, s in corpus_status.items() if s == "POSSIBLE_COUNTEREXAMPLE_FOUND"]
    )
    if triggers:
        status = "SEMANTIC_CONFLICT"
    else:
        triggers = [cid for cid, s in direct_status.items() if s == "PARTIALLY_SUPPORTED"] + [
            cid for cid, s in inference_status.items() if s == "OVERSTATED_PARTIAL"
        ]
        if triggers:
            status = "PARTIAL_WARNING"
        else:
            triggers = (
                [cid for cid, s in direct_status.items() if s == "INSUFFICIENT_EVIDENCE"]
                + [cid for cid, s in inference_status.items() if s == "INSUFFICIENT_PREMISES"]
                + [cid for cid, s in corpus_status.items() if s == "CHECK_INCOMPLETE"]
            )
            if triggers:
                status = "UNVERIFIED"
            elif any(s == "NOTHING_FOUND" for s in corpus_status.values()):
                status = "NOTHING_FOUND_AGAINST"
                triggers = [cid for cid, s in corpus_status.items() if s == "NOTHING_FOUND"]
            elif not direct and not inferences and not corpus:
                status = "NO_SOURCE_VERIFICATION_REQUIRED"
                triggers = [c["claim_id"] for c in claims if c["type"] == "WRITER_ANALYSIS"]
            else:
                status = "NO_SEMANTIC_ISSUE_FOUND"
                triggers = []
    return {
        "deterministic_status": status,
        "triggering_claim_ids": sorted(set(triggers)),
        "rule": ADVISORY_RULE,
    }


def assemble_advisory_report(
    read_identifier: str,
    sentences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the final post-Read advisory report. Report only — never gates.

    Each sentence dict must carry `sentence_id`, `sentence` and `claims`
    (with advisory model results attached by the caller). Every sentence
    advisory is computed here, deterministically.
    """
    report_sentences = []
    for sentence in sentences:
        advisory = deterministic_advisory(sentence["claims"])
        report_sentences.append(
            {
                "sentence_id": sentence["sentence_id"],
                "sentence": sentence["sentence"],
                "advisory": advisory,
                "claims": sentence["claims"],
            }
        )
    counts: dict[str, int] = defaultdict(int)
    for item in report_sentences:
        counts[item["advisory"]["deterministic_status"]] += 1
    return {
        "kind": "semantic_advisory_report",
        "read_identifier": read_identifier,
        "doctrine": {
            "gates_output": False,
            "modifies_writer_inputs": False,
            "modifies_read": False,
            "referee_noise_caveat": REFEREE_NOISE_CAVEAT,
        },
        "advisory_counts": dict(sorted(counts.items())),
        "sentences": report_sentences,
        "report_sha256": stable_hash([s["sentence_id"] for s in report_sentences]),
    }
