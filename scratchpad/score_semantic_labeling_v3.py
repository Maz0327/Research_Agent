"""Score a completed owner-exported semantic-labeling v3 artifact by stage."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "count": numerator,
        "total": denominator,
        "rate": round(numerator / denominator, 4) if denominator else None,
    }


def mean_median(values: list[int]) -> dict[str, int | float | None]:
    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 2) if values else None,
        "median": round(statistics.median(values), 2) if values else None,
    }


def direct_claims(sentence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in sentence["system_decomposition"]["claims"]
        if claim["type"] == "DIRECT_SOURCE_CLAIM"
    ]


def inference_claims(sentence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in sentence["system_decomposition"]["claims"]
        if claim["type"] == "SOURCE_GROUNDED_INFERENCE"
    ]


def corpus_claims(sentence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in sentence["system_decomposition"]["claims"]
        if claim["type"] == "CORPUS_META"
    ]


def relevant(label: str) -> bool:
    return label in {"DIRECTLY_RELEVANT", "PARTIALLY_RELEVANT"}


def confusion_accuracy(pairs: Iterable[tuple[str, str]]) -> dict[str, Any]:
    materialized = list(pairs)
    return ratio(sum(system == owner for system, owner in materialized), len(materialized))


def require_completed_export(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if payload.get("metadata", {}).get("schema_version") != 3:
        raise SystemExit("Input is not a semantic-labeling v3 export")
    labels = payload.get("owner_labels")
    if not isinstance(labels, list) or len(labels) != 15:
        raise SystemExit("Export must contain owner_labels for all 15 sentences")
    by_id = {label.get("sentence_id"): label for label in labels}
    expected_ids = {sentence["sentence_id"] for sentence in payload["sentences"]}
    if set(by_id) != expected_ids:
        raise SystemExit("Owner-label sentence IDs do not match the artifact")
    incomplete = [
        (label["sentence_id"], stage["stage"])
        for label in labels
        for stage in label.get("stage_completion", [])
        if not stage.get("complete")
    ]
    if any(len(label.get("stage_completion", [])) != 8 for label in labels) or incomplete:
        raise SystemExit(f"Owner export is incomplete: {incomplete[:12]}")
    return by_id


def score(payload: dict[str, Any]) -> dict[str, Any]:
    owner_by_sentence = require_completed_export(payload)
    sentences = payload["sentences"]

    boundary_correct = boundary_total = type_correct = type_total = 0
    missing_claims = over_split_claims = 0
    missing_claim_flags = over_split_flags = 0
    premise_correct = premise_total = 0
    for sentence in sentences:
        owner = owner_by_sentence[sentence["sentence_id"]]
        system_claims = sentence["system_decomposition"]["claims"]
        gold_claims = owner["owner_decomposition"]
        system_by_id = {claim["claim_id"]: claim for claim in system_claims}
        gold_by_id = {claim["claim_id"]: claim for claim in gold_claims}
        boundary_total += max(len(system_claims), len(gold_claims))
        boundary_correct += sum(
            claim_id in gold_by_id
            and " ".join(system["text"].split())
            == " ".join(gold_by_id[claim_id]["text"].split())
            for claim_id, system in system_by_id.items()
        )
        common = set(system_by_id) & set(gold_by_id)
        type_total += len(common)
        type_correct += sum(
            system_by_id[claim_id]["type"] == gold_by_id[claim_id]["type"]
            for claim_id in common
        )
        missing_claims += max(0, len(gold_claims) - len(system_claims))
        over_split_claims += max(0, len(system_claims) - len(gold_claims))
        missing_claim_flags += owner["decomposition_review"] == "MISSING_CLAIM"
        over_split_flags += owner["decomposition_review"] == "SHOULD_BE_ONE_CLAIM"
        for claim in inference_claims(sentence):
            premise_total += 1
            gold = gold_by_id.get(claim["claim_id"])
            judged_correct = owner["premise_link_judgments"].get(claim["claim_id"])
            premise_correct += bool(
                gold
                and gold.get("derived_from_claim_ids") == claim["derived_from_claim_ids"]
                and judged_correct == "CORRECT_PREMISE"
            )

    retrieval_claims = []
    relevance_pairs: list[tuple[str, str]] = []
    owner_relevance_counts: Counter[str] = Counter()
    gold_candidates = 0
    gold_at = {1: 0, 3: 0, 5: 0, 10: 0}
    actor_mask_gold = actor_mask_rescue_claims = claims_with_gold = 0
    missing_evidence_claims = 0
    localization_labels: list[str] = []
    localization_words: list[int] = []
    localization_sentence_counts: list[int] = []
    for sentence in sentences:
        owner = owner_by_sentence[sentence["sentence_id"]]
        for claim in direct_claims(sentence):
            retrieval_claims.append(claim)
            claim_owner = owner["direct_claims"][claim["claim_id"]]
            missing_evidence_claims += bool(claim_owner["missing_fact_or_evidence"])
            claim_gold = []
            exact_route_has_gold = False
            masked_only_has_gold = False
            for candidate in claim["retrieval"]["candidates"]:
                candidate_owner = claim_owner["candidates"][candidate["fact_id"]]
                owner_label = candidate_owner["owner_relevance"]
                system_label = candidate["system_relevance"]["label"]
                relevance_pairs.append((system_label, owner_label))
                owner_relevance_counts[owner_label] += 1
                if relevant(owner_label):
                    claim_gold.append(candidate)
                    gold_candidates += 1
                    exact_route_has_gold |= candidate["rank_exact"] is not None
                    if candidate["rank_exact"] is None and candidate[
                        "rank_actor_masked"
                    ] is not None:
                        actor_mask_gold += 1
                        masked_only_has_gold = True
                    for cutoff in gold_at:
                        gold_at[cutoff] += candidate["union_rank"] <= cutoff
                if relevant(system_label):
                    localization_labels.append(
                        candidate_owner["owner_evidence_localization"]
                    )
                    proposal = candidate["evidence_proposal"]
                    if proposal["status"] == "SPAN_FOUND":
                        localization_words.append(proposal["word_count"])
                        localization_sentence_counts.append(
                            proposal["source_sentence_count"]
                        )
            if claim_gold:
                claims_with_gold += 1
                if masked_only_has_gold and not exact_route_has_gold:
                    actor_mask_rescue_claims += 1

    system_relevant = sum(relevant(system) for system, _ in relevance_pairs)
    true_positive_relevance = sum(
        relevant(system) and relevant(owner) for system, owner in relevance_pairs
    )
    retrieval_at = {
        f"gold_candidate_recall_at_{cutoff}": ratio(found, gold_candidates)
        for cutoff, found in gold_at.items()
    }

    evidence = payload["evidence_objects"]
    raw_occurrences = sum(len(item["occurrence_ids"]) for item in evidence)
    grouping = [
        owner_by_sentence[sentence["sentence_id"]]["evidence_grouping"][item["evidence_id"]]
        for sentence in sentences
        for item in evidence
        if any(
            claim_id
            in {
                claim["claim_id"]
                for claim in sentence["system_decomposition"]["claims"]
            }
            for claim_id in item["routed_claim_ids"]
        )
    ]

    direct_pairs: list[tuple[str, str]] = []
    direct_owner_counts: Counter[str] = Counter()
    inference_pairs: list[tuple[str, str]] = []
    inference_owner_counts: Counter[str] = Counter()
    corpus_pairs: list[tuple[str, str]] = []
    advisory_pairs: list[tuple[str, str]] = []
    for sentence in sentences:
        owner = owner_by_sentence[sentence["sentence_id"]]
        for claim in direct_claims(sentence):
            system_result = claim["direct_referee"]["system_result"]["status"]
            owner_result = owner["direct_referees"][claim["claim_id"]]["owner_result"]
            direct_pairs.append((system_result, owner_result))
            direct_owner_counts[owner_result] += 1
        for claim in inference_claims(sentence):
            system_result = claim["inference_referee"]["system_result"]["status"]
            owner_result = owner["inference_referees"][claim["claim_id"]]["owner_result"]
            inference_pairs.append((system_result, owner_result))
            inference_owner_counts[owner_result] += 1
        for claim in corpus_claims(sentence):
            corpus_pairs.append(
                (
                    claim["corpus_check"]["system_result"],
                    owner["corpus_checks"][claim["claim_id"]],
                )
            )
        advisory_pairs.append(
            (sentence["sentence_advisory"]["deterministic_status"], owner["sentence_advisory"])
        )

    def class_accuracy(
        pairs: list[tuple[str, str]], label: str
    ) -> dict[str, int | float | None]:
        gold = [pair for pair in pairs if pair[1] == label]
        return ratio(sum(system == owner for system, owner in gold), len(gold))

    conflict_gold = sum(owner == "CONFLICT" for _, owner in direct_pairs)
    conflict_caught = sum(
        system == owner == "CONFLICT" for system, owner in direct_pairs
    )
    system_conflicts = sum(system == "CONFLICT" for system, _ in direct_pairs)
    false_conflicts = sum(
        system == "CONFLICT" and owner != "CONFLICT" for system, owner in direct_pairs
    )
    warnings = {"SEMANTIC_CONFLICT", "PARTIAL_WARNING", "UNVERIFIED"}
    false_warnings = sum(
        system in warnings and owner not in warnings for system, owner in advisory_pairs
    )
    missed_issues = sum(
        system not in warnings and owner in warnings for system, owner in advisory_pairs
    )
    owner_unverified = sum(owner == "UNVERIFIED" for _, owner in advisory_pairs)
    unverified_correct = sum(
        system == owner == "UNVERIFIED" for system, owner in advisory_pairs
    )

    return {
        "metadata": {
            "read_sha256": payload["metadata"]["read_sha256"],
            "artifact_sha256": payload["metadata"]["artifact_sha256"],
            "owner_labels_exported_at": payload.get("owner_labels_exported_at"),
            "comparison_note": (
                "All accuracy metrics compare v3 system proposals with owner labels "
                "from this export. No v2 owner accuracy is inferred."
            ),
        },
        "stage_1_claim_decomposition": {
            "claim_boundary_accuracy": ratio(boundary_correct, boundary_total),
            "type_accuracy": ratio(type_correct, type_total),
            "missing_claim_count": missing_claims,
            "over_split_claim_count": over_split_claims,
            "sentences_flagged_missing_claim": missing_claim_flags,
            "sentences_flagged_should_be_one_claim": over_split_flags,
            "inference_premise_link_accuracy": ratio(premise_correct, premise_total),
        },
        "stage_2_broad_retrieval": {
            **retrieval_at,
            "claims_with_owner_relevant_candidates": claims_with_gold,
            "missing_evidence_rate": ratio(missing_evidence_claims, len(retrieval_claims)),
            "actor_mask_rescued_gold_candidate_count": actor_mask_gold,
            "actor_mask_rescued_claims": ratio(
                actor_mask_rescue_claims, claims_with_gold
            ),
        },
        "stage_3_relevance": {
            "accuracy": confusion_accuracy(relevance_pairs),
            "relevant_precision": ratio(true_positive_relevance, system_relevant),
            "directly_relevant_count": owner_relevance_counts["DIRECTLY_RELEVANT"],
            "partially_relevant_count": owner_relevance_counts["PARTIALLY_RELEVANT"],
            "irrelevant_noise_rate": ratio(
                owner_relevance_counts["NOT_RELEVANT"], len(relevance_pairs)
            ),
            "unclear_rate": ratio(
                owner_relevance_counts["UNCLEAR"], len(relevance_pairs)
            ),
        },
        "stage_4_evidence_localization": {
            "localization_correctness": ratio(
                localization_labels.count("SUFFICIENT"), len(localization_labels)
            ),
            "primary_evidence_words": mean_median(localization_words),
            "source_sentence_count": mean_median(localization_sentence_counts),
            "too_broad_rate": ratio(
                localization_labels.count("TOO_BROAD"), len(localization_labels)
            ),
            "missing_context_rate": ratio(
                localization_labels.count("MISSING_NEEDED_CONTEXT"),
                len(localization_labels),
            ),
            "unsupported_harvested_fact_discovery_rate": ratio(
                localization_labels.count("DOES_NOT_SUPPORT_FACT"),
                len(localization_labels),
            ),
        },
        "stage_5_evidence_identity": {
            "raw_evidence_occurrences": raw_occurrences,
            "unique_evidence_ids": len(evidence),
            "duplicate_occurrence_rate": ratio(
                raw_occurrences - len(evidence), raw_occurrences
            ),
            "duplicates_removed": raw_occurrences - len(evidence),
            "incorrect_grouping_count": grouping.count("SHOULD_BE_SEPARATE"),
            "missing_duplicate_count": grouping.count("MISSING_DUPLICATE"),
        },
        "stage_6_direct_claim_referee": {
            "accuracy": confusion_accuracy(direct_pairs),
            "conflict_recall": ratio(conflict_caught, conflict_gold),
            "false_conflict_rate": ratio(false_conflicts, system_conflicts),
            "supported_accuracy": class_accuracy(direct_pairs, "SUPPORTED"),
            "partial_support_accuracy": class_accuracy(
                direct_pairs, "PARTIALLY_SUPPORTED"
            ),
            "insufficient_evidence_accuracy": class_accuracy(
                direct_pairs, "INSUFFICIENT_EVIDENCE"
            ),
            "owner_result_counts": dict(sorted(direct_owner_counts.items())),
        },
        "stage_7_inference_referee": {
            "accuracy": confusion_accuracy(inference_pairs),
            "reasonable_inference_accuracy": class_accuracy(
                inference_pairs, "REASONABLE_INFERENCE"
            ),
            "overstatement_detection": class_accuracy(
                inference_pairs, "OVERSTATED_PARTIAL"
            ),
            "does_not_follow_detection": class_accuracy(
                inference_pairs, "DOES_NOT_FOLLOW"
            ),
            "insufficient_premise_handling": class_accuracy(
                inference_pairs, "INSUFFICIENT_PREMISES"
            ),
            "owner_result_counts": dict(sorted(inference_owner_counts.items())),
            "corpus_check_accuracy": confusion_accuracy(corpus_pairs),
            "corpus_claim_count": len(corpus_pairs),
        },
        "stage_8_sentence_advisory": {
            "accuracy": confusion_accuracy(advisory_pairs),
            "false_warning": ratio(false_warnings, len(advisory_pairs)),
            "missed_semantic_issue": ratio(missed_issues, len(advisory_pairs)),
            "unverified_handled_correctly": ratio(
                unverified_correct, owner_unverified
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a completed owner-exported semantic-labeling v3 JSON file."
    )
    parser.add_argument("export", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.export.read_text(encoding="utf-8"))
    report = score(payload)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
