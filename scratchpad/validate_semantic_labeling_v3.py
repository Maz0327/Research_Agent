"""Targeted structural validation for the frozen D-038 semantic-labeling v3."""

from __future__ import annotations

import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings  # noqa: E402
from backend.pipeline.stages.harvest_stage import build_inventory  # noqa: E402
from scratchpad.build_semantic_labeling_current_read import (  # noqa: E402
    actor_mask,
    read_json,
    read_source_vault,
    selected_sentences,
    stable_hash,
)
from scratchpad.build_semantic_labeling_v3 import (  # noqa: E402
    CLAIM_TYPES,
    DEFAULT_FACT_CACHE,
    DEFAULT_HARVEST,
    DEFAULT_HTML,
    DEFAULT_JSON,
    DEFAULT_READ,
    DEFAULT_SOURCE_VAULT,
    DEFAULT_V3_CACHE,
    DIRECT_RESULTS,
    EMBEDDING_MODEL,
    INFERENCE_RESULTS,
    RELEVANCE_LABELS,
    TOP_PER_ROUTE,
    deterministic_advisory,
    evidence_identity,
    source_sentence_units,
)

BASELINE = "0cb2a1aaf96514a921072c561fa597dffdc8cae1"
V2_FILES = (
    "scratchpad/build_semantic_labeling_current_read.py",
    "scratchpad/semantic_labeling_current_read.json",
    "scratchpad/semantic_labeling_current_read.html",
    "scratchpad/validate_semantic_labeling_current_read.py",
)
ALLOWED_NEW_FILES = {
    "scratchpad/build_semantic_labeling_v3.py",
    "scratchpad/semantic_labeling_v3.json",
    "scratchpad/semantic_labeling_v3.html",
    "scratchpad/semantic_labeling_v3_cache.json.gz",
    "scratchpad/validate_semantic_labeling_v3.py",
    "scratchpad/score_semantic_labeling_v3.py",
}


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    )


def validate_repo_scope() -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    assert ancestor.returncode == 0, "Required baseline is not an ancestor of HEAD"
    for path in V2_FILES:
        baseline = subprocess.check_output(
            ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT
        )
        assert (ROOT / path).read_bytes() == baseline, f"v2 changed: {path}"
    changed = set(
        filter(None, git_output("diff", "--name-only", BASELINE, "--").splitlines())
    )
    untracked = {
        path
        for path in git_output("ls-files", "--others", "--exclude-standard").splitlines()
        if not path.startswith((".agents/", ".codex/"))
    }
    assert changed | untracked <= ALLOWED_NEW_FILES, changed | untracked


def main() -> None:
    dataset = read_json(DEFAULT_JSON)
    read_data = read_json(DEFAULT_READ)
    harvest_payload = read_json(DEFAULT_HARVEST)
    html = DEFAULT_HTML.read_text(encoding="utf-8")
    sources = read_source_vault(DEFAULT_SOURCE_VAULT)
    source_by_id = {source["source_id"]: source["full_text"] for source in sources}
    units_by_source = {
        source_id: source_sentence_units(text)
        for source_id, text in source_by_id.items()
    }
    expected = selected_sentences(read_data)
    sentences = dataset["sentences"]
    metadata = dataset["metadata"]
    harvest = harvest_payload["harvest"]
    inventory = build_inventory(harvest)
    facts = {fact["fact_id"]: fact for fact in inventory}

    assert len(sentences) == len(expected) == 15
    for actual, frozen in zip(sentences, expected, strict=True):
        for key in (
            "sentence_id",
            "index",
            "sentence",
            "paragraph_index",
            "paragraph_label",
            "sentence_index_in_paragraph",
            "absolute_sentence_index",
        ):
            assert actual[key] == frozen[key], (actual["sentence_id"], key)
    assert metadata["selected_sentence_sha256"] == stable_hash(expected)
    assert metadata["read_sha256"] == stable_hash(read_data["read"])
    assert metadata["read_sha256"] == (
        "ea8dfd6c18edb27d7f7dc85e5da6e9e193b528c8e16876c6481c585d00029b0e"
    )
    assert metadata["harvest"]["replayed_scratchpad_fact_count"] == len(inventory) == 1270
    assert metadata["harvest"]["accepted_live_d038_fact_count"] == 1253
    assert metadata["harvest"]["accepted_live_and_replay_are_identical"] is False
    assert metadata["harvest"]["replayed_harvest_sha256"] == stable_hash(harvest)
    assert metadata["embedding"]["model"] == EMBEDDING_MODEL
    assert metadata["embedding"]["fact_cache_reused"] is True
    assert metadata["judge"]["provider"] == "openai"
    assert metadata["judge"]["model"] == "gpt-5.6-terra"
    assert metadata["allowed_corpus_results"] == [
        "CORPUS_CLAIM_VERIFIED",
        "COUNTEREXAMPLE_FOUND",
        "CORPUS_CHECK_INCOMPLETE",
    ]
    assert metadata["architecture_order"] == [
        "research",
        "full_rich_research_packet",
        "writer",
        "finished_read",
        "semantic_verification",
    ]
    assert metadata["verification_can_modify_writer_inputs"] is False
    assert metadata["verification_can_rewrite_read"] is False
    assert metadata["retrieval"]["top_per_route_before_union"] == TOP_PER_ROUTE == 10
    assert metadata["retrieval"]["similarity_threshold"] is None
    assert metadata["retrieval"]["fact_deduplication"] == "exact FACT_ID only"

    with gzip.open(DEFAULT_FACT_CACHE, "rt", encoding="utf-8") as handle:
        fact_cache = json.load(handle)
    assert fact_cache["metadata"]["embedding_model"] == EMBEDDING_MODEL
    assert fact_cache["metadata"]["inventory_sha256"] == metadata["embedding"][
        "fact_inventory_sha256"
    ]
    assert len(fact_cache["fact_embeddings"]) == 1270
    with gzip.open(DEFAULT_V3_CACHE, "rt", encoding="utf-8") as handle:
        v3_cache = json.load(handle)
    assert v3_cache["metadata"]["embedding_model"] == EMBEDDING_MODEL
    assert v3_cache["metadata"]["inventory_sha256"] == metadata["embedding"][
        "fact_inventory_sha256"
    ]
    assert v3_cache["metadata"]["judge_model"] == "gpt-5.6-terra"
    assert v3_cache["metadata"]["judge_provider"] == "openai"
    assert len(v3_cache["model_calls"]) == (
        metadata["judge"]["calls_created_this_run"]
        + metadata["judge"]["calls_reused_this_run"]
    )

    direct_claims = 0
    candidates_seen = 0
    localized_occurrences = 0
    no_span_occurrences = 0
    lexical_helped_occurrences = 0
    old_route_missed_occurrences = 0
    corpus_conceptual_counts = {
        "POSSIBLE_COUNTEREXAMPLE_FOUND": 0,
        "NOTHING_FOUND": 0,
        "CHECK_INCOMPLETE": 0,
    }
    referenced_evidence_ids: set[str] = set()
    query_keys: set[str] = set()
    for sentence in sentences:
        assert sentence["owner_decomposition"] is None
        assert sentence["system_decomposition"]["model"] == "gpt-5.6-terra"
        assert sentence["system_decomposition"]["provider"] == "openai"
        claims = sentence["system_decomposition"]["claims"]
        claim_ids = {claim["claim_id"] for claim in claims}
        assert sentence["sentence_advisory"] == deterministic_advisory(claims)
        for claim in claims:
            assert claim["type"] in CLAIM_TYPES
            assert claim["claim_id"].startswith(sentence["sentence_id"] + ":C")
            assert set(claim["derived_from_claim_ids"]) <= claim_ids
            if claim["type"] == "SOURCE_GROUNDED_INFERENCE":
                assert claim["derived_from_claim_ids"]
                result = claim["inference_referee"]["system_result"]
                assert result["status"] in INFERENCE_RESULTS
                assert claim["inference_referee"]["owner_result"] is None
            elif claim["type"] == "WRITER_ANALYSIS":
                assert claim["analysis_result"] == "NO_SOURCE_VERIFICATION_REQUIRED"
                assert "retrieval" not in claim
            elif claim["type"] == "CORPUS_META":
                corpus_check = claim["corpus_check"]
                assert corpus_check["system_result"] in {
                    "COUNTEREXAMPLE_FOUND",
                    "CORPUS_CHECK_INCOMPLETE",
                }
                assert corpus_check["conceptual_result"] in {
                    "POSSIBLE_COUNTEREXAMPLE_FOUND",
                    "NOTHING_FOUND",
                    "CHECK_INCOMPLETE",
                }
                assert (corpus_check["system_result"] == "COUNTEREXAMPLE_FOUND") is (
                    corpus_check["conceptual_result"] == "POSSIBLE_COUNTEREXAMPLE_FOUND"
                )
                assert (
                    corpus_check["method"]
                    == "full_corpus_semantic_counterexample_search"
                )
                assert corpus_check["positive_proposition"]
                assert corpus_check["nothing_found_is_proof_of_absence"] is False
                assert corpus_check["sources_checked"] == len(source_by_id)
                assert corpus_check["full_corpus_windows_searched"] == sum(
                    len(units) for units in units_by_source.values()
                )
                counterexample_ids = {
                    window["candidate_id"] for window in corpus_check["counterexamples"]
                }
                confirming_ids = {
                    window["candidate_id"]
                    for window in corpus_check["confirming_passages"]
                }
                assert not (counterexample_ids & confirming_ids)
                seen_window_ids = set()
                for window in corpus_check["candidate_windows"]:
                    seen_window_ids.add(window["candidate_id"])
                    raw = source_by_id[window["source_id"]]
                    assert (
                        raw[window["start_char"] : window["end_char"]]
                        == window["exact_raw_text"]
                    )
                    relation = window["model_relation"]
                    assert relation in {
                        "CONTRADICTS_CLAIM",
                        "SUPPORTS_CLAIM",
                        "UNRELATED",
                    }
                    assert (relation == "CONTRADICTS_CLAIM") is (
                        window["candidate_id"] in counterexample_ids
                    )
                    assert (relation == "SUPPORTS_CLAIM") is (
                        window["candidate_id"] in confirming_ids
                    )
                assert (counterexample_ids | confirming_ids) <= seen_window_ids
                corpus_conceptual_counts[corpus_check["conceptual_result"]] += 1
                query_keys.add(f"{claim['claim_id']}:corpus_positive_proposition")
                assert corpus_check["owner_result"] is None
                assert "retrieval" not in claim
            else:
                direct_claims += 1
                retrieval = claim["retrieval"]
                assert retrieval["exact_query"] == claim["text"]
                assert retrieval["actor_masked_query"] == actor_mask(claim["text"])
                assert retrieval["actor_masked_query"] != claim["text"]
                assert retrieval["top_per_route"] == 10
                assert retrieval["similarity_threshold"] is None
                assert retrieval["deduplication"] == "exact FACT_ID only"
                candidates = retrieval["candidates"]
                fact_ids = [candidate["fact_id"] for candidate in candidates]
                assert len(fact_ids) == len(set(fact_ids))
                assert sorted(
                    candidate["rank_exact"]
                    for candidate in candidates
                    if candidate["rank_exact"] is not None
                ) == list(range(1, 11))
                assert sorted(
                    candidate["rank_actor_masked"]
                    for candidate in candidates
                    if candidate["rank_actor_masked"] is not None
                ) == list(range(1, 11))
                query_keys |= {
                    f"{claim['claim_id']}:exact",
                    f"{claim['claim_id']}:actor_masked",
                }
                result = claim["direct_referee"]["system_result"]
                assert result["status"] in DIRECT_RESULTS
                assert claim["direct_referee"]["owner_result"] is None
                for rank, candidate in enumerate(candidates, 1):
                    candidates_seen += 1
                    assert candidate["union_rank"] == rank
                    assert candidate["fact_id"].startswith(candidate["source_id"] + ":F_")
                    assert candidate["fact_text"] == facts[candidate["fact_id"]]["text"]
                    assert candidate["source_id"] == facts[candidate["fact_id"]]["source_id"]
                    assert candidate["retrieved_by"] in {"exact", "actor_masked", "both"}
                    assert candidate["system_relevance"]["label"] in RELEVANCE_LABELS
                    assert candidate["owner_relevance"] is None
                    assert candidate["owner_evidence_localization"] is None
                    relevant = candidate["system_relevance"]["label"] in {
                        "DIRECTLY_RELEVANT",
                        "PARTIALLY_RELEVANT",
                    }
                    proposal = candidate["evidence_proposal"]
                    assert (proposal is not None) is relevant
                    if not relevant:
                        continue
                    assert (
                        proposal["routing_method"]
                        == "full_source_semantic_search_with_lexical_union"
                    )
                    search_metadata = proposal["search_metadata"]
                    assert search_metadata["search_scope"] == "entire_known_source"
                    assert search_metadata["full_source_units_searched"] == len(
                        units_by_source[candidate["source_id"]]
                    )
                    assert search_metadata["similarity_threshold"] is None
                    if proposal["status"] == "NO_SUPPORTING_SPAN_FOUND":
                        assert "start_char" not in proposal and "exact_raw_text" not in proposal
                        assert search_metadata["winning_semantic_rank"] is None
                        no_span_occurrences += 1
                        continue
                    assert proposal["status"] == "SPAN_FOUND"
                    assert search_metadata["winning_semantic_rank"] >= 1
                    lexical_helped_occurrences += bool(
                        search_metadata["lexical_search_helped"]
                    )
                    old_route_missed_occurrences += bool(
                        search_metadata[
                            "old_routing_location_would_have_missed_final_evidence"
                        ]
                    )
                    localized_occurrences += 1
                    assert proposal["source_id"] == candidate["source_id"]
                    raw = source_by_id[proposal["source_id"]]
                    assert raw[proposal["start_char"] : proposal["end_char"]] == proposal[
                        "exact_raw_text"
                    ]
                    assert proposal["word_count"] == len(proposal["exact_raw_text"].split())
                    assert proposal["source_sentence_count"] == (
                        proposal["end_sentence_index"] - proposal["start_sentence_index"] + 1
                    )
                    assert 1 <= proposal["source_sentence_count"] <= 3
                    units = units_by_source[proposal["source_id"]]
                    assert units[proposal["start_sentence_index"]]["start_char"] == proposal[
                        "start_char"
                    ]
                    assert units[proposal["end_sentence_index"]]["end_char"] == proposal[
                        "end_char"
                    ]
                    assert proposal["evidence_id"] == evidence_identity(proposal)
                    assert proposal["supporting_fact_ids"] == [candidate["fact_id"]]
                    referenced_evidence_ids.add(proposal["evidence_id"])

    assert set(v3_cache["query_embeddings"]) == query_keys
    for key, cached in v3_cache["query_embeddings"].items():
        assert len(cached["embedding"]) == metadata["embedding"]["dimensions"]
        assert re.fullmatch(r"[0-9a-f]{64}", cached["text_sha256"]), key
    expected_unit_keys = {
        f"{source_id}:{unit['sentence_index']}"
        for source_id, units in units_by_source.items()
        for unit in units
    }
    assert set(v3_cache["source_unit_embeddings"]) == expected_unit_keys
    for key, cached in v3_cache["source_unit_embeddings"].items():
        assert len(cached["embedding"]) == metadata["embedding"]["dimensions"]
        assert re.fullmatch(r"[0-9a-f]{64}", cached["text_sha256"]), key

    evidence_objects = dataset["evidence_objects"]
    evidence_ids = [evidence["evidence_id"] for evidence in evidence_objects]
    assert len(evidence_ids) == len(set(evidence_ids))
    assert set(evidence_ids) == referenced_evidence_ids
    for evidence in evidence_objects:
        assert evidence["evidence_id"] == evidence_identity(evidence)
        raw = source_by_id[evidence["source_id"]]
        assert raw[evidence["start_char"] : evidence["end_char"]] == evidence[
            "exact_raw_text"
        ]
        assert 1 <= evidence["source_sentence_count"] <= 3
        assert evidence["word_count"] <= 180
        assert evidence["owner_grouping"] is None
        assert all(fact_id in facts for fact_id in evidence["supporting_fact_ids"])
        assert all(
            fact_id.startswith(evidence["source_id"] + ":F_")
            for fact_id in evidence["supporting_fact_ids"]
        )

    stats = metadata["generation_statistics"]
    assert stats["direct_claims"] == direct_claims
    assert stats["retrieval_candidate_occurrences"] == candidates_seen
    assert stats["raw_localized_evidence_occurrences"] == localized_occurrences
    assert stats["unique_evidence_ids"] == len(evidence_objects)
    assert stats["duplicates_eliminated"] == localized_occurrences - len(evidence_objects)
    assert stats["no_supporting_span_found"] == no_span_occurrences
    assert stats["localizations_where_lexical_search_helped"] == lexical_helped_occurrences
    assert (
        stats["localized_evidence_old_route_would_have_missed"]
        == old_route_missed_occurrences
    )
    assert stats["corpus_claim_conceptual_results"] == corpus_conceptual_counts
    assert stats["full_source_unit_inventory"] == sum(
        len(units) for units in units_by_source.values()
    )
    assert metadata["localization"]["search_scope"] == "entire known source"
    assert metadata["localization"]["similarity_threshold"] is None
    assert metadata["localization"]["no_supporting_span_found_is_truth_verdict"] is False
    assert (
        metadata["corpus_check"]["method"]
        == "full_corpus_semantic_counterexample_search"
    )
    assert metadata["corpus_check"]["nothing_found_proves_absence"] is False
    artifact_hash = stable_hash(
        {
            "sentences": sentences,
            "evidence_objects": evidence_objects,
            "read_sha256": metadata["read_sha256"],
            "inventory_sha256": metadata["embedding"]["fact_inventory_sha256"],
            "judge_model": metadata["judge"]["model"],
        }
    )
    assert metadata["artifact_sha256"] == artifact_hash

    embedded = re.search(r"const DATA=(.*?);\nconst FRIENDLY_LABELS=", html, re.DOTALL)
    assert embedded is not None and json.loads(embedded.group(1)) == dataset
    storage = re.search(r'const STORAGE_KEY="([^"]+)', html)
    assert storage is not None and storage.group(1).startswith("semantic-labeling-v3:")
    assert "semantic-labeling-current-read" not in html
    assert "semantic-labeling-v2" not in html
    assert "localStorage" in html
    assert "Export labeled JSON" in html and "Reset v3 labels" in html
    assert "MISSING THE FACT/EVIDENCE I NEED" in html
    assert "NO_SOURCE_VERIFICATION_REQUIRED" in html
    assert "SYSTEM RESEARCH-CONTENT RESULT" in html
    assert "corpus_checks" in html
    assert "FRIENDLY_LABELS" in html
    assert "function friendly" in html
    assert "Source-based fact" in html
    assert "Conclusion drawn from the research" in html
    assert "Couldn’t find the source passage" in html or (
        "Couldn't find the source passage" in html
    )
    assert "Nothing found" in html
    assert "Nothing found against this" in html
    scrubbed = re.sub(
        r"const DATA=.*?;\nconst FRIENDLY_LABELS=",
        "const FRIENDLY_LABELS=",
        html,
        flags=re.DOTALL,
    )
    assert "https://" not in scrubbed and "http://" not in scrubbed
    settings = get_settings()
    combined = DEFAULT_JSON.read_text(encoding="utf-8") + html
    for secret in (settings.openai_api_key, settings.dashscope_api_key):
        if secret:
            assert secret not in combined

    validate_repo_scope()
    print(
        json.dumps(
            {
                "status": "PASS",
                "sentences": len(sentences),
                "direct_claims": direct_claims,
                "retrieval_candidates": candidates_seen,
                "localized_occurrences": localized_occurrences,
                "unique_evidence_ids": len(evidence_objects),
                "maximum_evidence_words": max(
                    evidence["word_count"] for evidence in evidence_objects
                ),
                "read_sha256": metadata["read_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
