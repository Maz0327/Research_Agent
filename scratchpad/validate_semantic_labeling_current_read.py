"""Targeted structural checks for the current D-038 labeling artifact."""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scratchpad.build_semantic_labeling_current_read import (  # noqa: E402
    DEFAULT_HARVEST,
    DEFAULT_HTML,
    DEFAULT_JSON,
    DEFAULT_READ,
    DEFAULT_SOURCE_VAULT,
    MAX_EVIDENCE_WORDS,
    actor_mask,
    read_json,
    read_source_vault,
    selected_sentences,
    stable_hash,
)

QUESTION = (
    "Is this sentence repeating information from a source, or is it the writer "
    "making its own point?"
)


def normalized(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    dataset = read_json(DEFAULT_JSON)
    read_data = read_json(DEFAULT_READ)
    harvest_payload = read_json(DEFAULT_HARVEST)
    harvest = harvest_payload["harvest"]
    html = DEFAULT_HTML.read_text(encoding="utf-8")
    sources = read_source_vault(DEFAULT_SOURCE_VAULT)
    source_text = {
        source["source_id"]: normalized(source["full_text"]) for source in sources
    }
    expected = selected_sentences(read_data)
    items = dataset["items"]
    metadata = dataset["metadata"]

    assert len(items) == 15
    assert [item["sentence"] for item in items] == [
        item["sentence"] for item in expected
    ]
    assert [item["paragraph_index"] for item in items] == [
        item["paragraph_index"] for item in expected
    ]
    assert set(item["paragraph_index"] for item in items) == set(range(10))
    assert metadata["decision"] == "D-038"
    assert metadata["job_id"] == "hawara-rerun"
    assert metadata["briefing_version"] == "1"
    assert metadata["read_generated_on"] == "2026-08-22"
    assert metadata["read_word_count"] == 1816
    assert metadata["read_paragraph_count"] == 9
    assert metadata["read_sha256"] == stable_hash(read_data["read"])
    assert metadata["harvest_fact_count"] == sum(map(len, harvest.values())) == 1270
    assert harvest_payload["metadata"]["harvest_fact_count"] == 1270
    assert harvest_payload["metadata"]["harvest_sha256"] == stable_hash(harvest)
    assert metadata["embedding_model"] == "qwen3.7-text-embedding"
    assert metadata["retrieval"]["method"] == "embedding"
    assert metadata["retrieval"]["query_union"] == [
        "original",
        "actor_masked_where_applicable",
    ]
    assert metadata["retrieval"]["top_k"] == 3
    assert metadata["retrieval"]["minimum_score_floor"] == 0.55
    assert metadata["retrieval"]["similarity_is_correctness_verdict"] is False
    assert metadata["maximum_display_evidence_window_words"] == MAX_EVIDENCE_WORDS
    with gzip.open(
        ROOT / "scratchpad/fact_embeddings_current_read.json.gz",
        "rt",
        encoding="utf-8",
    ) as handle:
        cache = json.load(handle)
    expected_query_hashes: dict[str, str] = {}
    for item in expected:
        original_key = f"{item['sentence_id']}:original"
        expected_query_hashes[original_key] = stable_hash(item["sentence"])
        masked = actor_mask(item["sentence"])
        if masked != item["sentence"]:
            expected_query_hashes[f"{item['sentence_id']}:masked"] = stable_hash(masked)
    assert cache["metadata"]["query_text_sha256_by_key"] == expected_query_hashes
    assert set(cache["query_embeddings"]) == set(expected_query_hashes)

    inventory = {
        f"{source_id}:F_{index}": fact
        for source_id, facts in harvest.items()
        for index, fact in enumerate(facts, 1)
    }
    shown_windows = 0
    for item in items:
        assert item["owner_category"] is None
        assert item["owner_match_judgment"] is None
        assert len(item["retrieved_candidates"]) <= 3
        assert item["retrieval_no_candidate_above_floor"] is (
            not item["retrieved_candidates"]
        )
        for rank, candidate in enumerate(item["retrieved_candidates"], 1):
            assert candidate["rank"] == rank
            assert candidate["fact_text"] == inventory[candidate["fact_id"]]
            assert candidate["fact_id"].startswith(candidate["source_id"] + ":F_")
            assert isinstance(candidate["embedding_score"], float)
            assert isinstance(candidate["original_query_score"], float)
            assert isinstance(candidate["masked_query_score"], float)
            assert candidate["embedding_score"] >= 0.55
            assert candidate["winning_query"] in {"original", "masked"}
            assert candidate["raw_evidence_windows"]
            for window in candidate["raw_evidence_windows"]:
                shown_windows += 1
                assert 0 < window["word_count"] <= MAX_EVIDENCE_WORDS
                assert window["word_count"] < len(
                    source_text[candidate["source_id"]].split()
                )
                assert normalized(window["text"]) in source_text[candidate["source_id"]]

    embedded_match = re.search(
        r"const DATA=(.*?);\nconst STORAGE_KEY=", html, flags=re.DOTALL
    )
    assert embedded_match is not None
    assert json.loads(embedded_match.group(1)) == dataset
    assert html.count(QUESTION) == 1
    assert ">SOURCE</button>" in html
    assert ">WRITER’S OWN POINT</button>" in html
    assert "source evidence stays hidden" not in html.lower()
    assert "https://" not in re.sub(r"const DATA=.*?;\nconst STORAGE_KEY=", "", html, flags=re.DOTALL)

    print(
        json.dumps(
            {
                "cards": len(items),
                "paragraph_positions": sorted(
                    set(item["paragraph_index"] for item in items)
                ),
                "retrieved_candidates": sum(
                    len(item["retrieved_candidates"]) for item in items
                ),
                "raw_evidence_windows": shown_windows,
                "maximum_window_words": max(
                    window["word_count"]
                    for item in items
                    for candidate in item["retrieved_candidates"]
                    for window in candidate["raw_evidence_windows"]
                ),
                "read_sha256": metadata["read_sha256"],
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
