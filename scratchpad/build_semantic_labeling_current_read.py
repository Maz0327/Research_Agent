"""Build the owner-labeling artifact for the accepted D-038 Hawara Read.

This is deliberately scratchpad tooling. It reproduces the settled retrieval
workflow: current Read sentence -> original/actor-masked embedding union ->
top-K candidates with a score floor -> the shared small raw-source windows.
Similarity retrieves context; it is never treated as a correctness verdict.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import math
import re
import sys
import time
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings  # noqa: E402
from backend.pipeline.briefing_routing import paragraphs_for_fact  # noqa: E402
from backend.pipeline.stages.harvest_stage import build_inventory  # noqa: E402
from backend.pipeline.text_similarity import content_tokens  # noqa: E402

DEFAULT_READ = ROOT / "scratchpad/current_d038_read.json"
DEFAULT_HARVEST = ROOT / "scratchpad/current_harvest.json"
DEFAULT_SOURCE_VAULT = (
    ROOT
    / "plans/260814-claim-graph-briefing/artifacts/hawara-run/hawara-vault.html"
)
DEFAULT_JSON = ROOT / "scratchpad/semantic_labeling_current_read.json"
DEFAULT_HTML = ROOT / "scratchpad/semantic_labeling_current_read.html"
DEFAULT_CACHE = ROOT / "scratchpad/fact_embeddings_current_read.json.gz"

EMBEDDING_MODEL = "qwen3.7-text-embedding"
TOP_K = 3
MIN_SCORE = 0.55
MAX_EVIDENCE_WORDS = 180
NAME = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")

# Deliberately spread across the lede and every D-038 paragraph. The sample
# includes straightforward source claims, analytical lines, negative/corpus
# claims, and mixed source-plus-inference cases.
SELECTED_POSITIONS = [
    (0, 1),
    (0, 2),
    (0, 5),
    (1, 3),
    (1, 6),
    (2, 3),
    (3, 0),
    (3, 1),
    (4, 5),
    (5, 6),
    (5, 11),
    (6, 8),
    (7, 4),
    (8, 4),
    (9, 5),
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class SourceVaultParser(HTMLParser):
    """Recover the source records embedded in the checked-in raw-source vault."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[dict[str, Any]] = []
        self._source: dict[str, Any] | None = None
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._meta_depth = 0

    @staticmethod
    def _classes(attributes: list[tuple[str, str | None]]) -> set[str]:
        return set(dict(attributes).get("class", "").split())

    def handle_starttag(
        self, tag: str, attributes: list[tuple[str, str | None]]
    ) -> None:
        attrs = dict(attributes)
        classes = self._classes(attributes)
        if tag == "section" and "src-block" in classes:
            source_id = (attrs.get("id") or "").upper()
            self._source = {"source_id": source_id, "title": "", "url": "", "full_text": ""}
        elif self._source is not None and tag == "h2":
            self._capture, self._buffer = "title", []
        elif self._source is not None and tag == "p" and "meta" in classes:
            self._meta_depth = 1
        elif self._source is not None and self._meta_depth and tag == "a":
            self._source["url"] = attrs.get("href") or ""
        elif self._source is not None and tag == "div" and "fulltext" in classes:
            self._capture, self._buffer = "full_text", []

    def handle_endtag(self, tag: str) -> None:
        if self._source is None:
            return
        if self._capture == "title" and tag == "h2":
            self._source["title"] = "".join(self._buffer).strip()
            self._capture, self._buffer = None, []
        elif self._capture == "full_text" and tag == "div":
            self._source["full_text"] = "".join(self._buffer).strip()
            self._capture, self._buffer = None, []
        elif self._meta_depth and tag == "p":
            self._meta_depth = 0
        elif tag == "section":
            self.sources.append(self._source)
            self._source = None

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)


def read_source_vault(path: Path) -> list[dict[str, Any]]:
    parser = SourceVaultParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.sources


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sentence_split(text: str) -> list[str]:
    """Match the sentence split used by the earlier semantic experiments."""
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def selected_sentences(read_data: dict[str, Any]) -> list[dict[str, Any]]:
    read = read_data["read"]
    parts = [("The Read lede", read["lede"])] + [
        (paragraph["label"], paragraph["text"]) for paragraph in read["paragraphs"]
    ]
    selected: list[dict[str, Any]] = []
    absolute = 0
    absolute_by_position: dict[tuple[int, int], int] = {}
    split_parts: list[tuple[str, list[str]]] = []
    for paragraph_index, (label, text) in enumerate(parts):
        sentences = sentence_split(text)
        split_parts.append((label, sentences))
        for sentence_index, _ in enumerate(sentences):
            absolute += 1
            absolute_by_position[(paragraph_index, sentence_index)] = absolute

    for sample_index, (paragraph_index, sentence_index) in enumerate(
        SELECTED_POSITIONS, 1
    ):
        label, sentences = split_parts[paragraph_index]
        sentence = sentences[sentence_index]
        selected.append(
            {
                "sentence_id": f"D038-S{sample_index:02d}",
                "index": sample_index,
                "sentence": sentence,
                "paragraph_index": paragraph_index,
                "paragraph_label": label,
                "sentence_index_in_paragraph": sentence_index,
                "absolute_sentence_index": absolute_by_position[
                    (paragraph_index, sentence_index)
                ],
            }
        )
    return selected


def actor_mask(text: str) -> str:
    return NAME.sub("[P]", text)


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def compact_evidence_window(
    raw_window: str, fact_text: str, limit: int = MAX_EVIDENCE_WORDS
) -> dict[str, Any]:
    """Bound an oversized selected block to a relevant contiguous excerpt.

    `paragraphs_for_fact()` remains the evidence selector. This only prevents
    an unusually long article paragraph from becoming an owner-facing dump.
    The chosen excerpt maximizes overlap with the already-selected fact; it
    does not retrieve or rank facts.
    """
    words = raw_window.split()
    if len(words) <= limit:
        return {
            "text": raw_window,
            "word_count": len(words),
            "character_count": len(raw_window),
            "selected_block_word_count": len(words),
            "excerpted_for_display": False,
        }

    fact_tokens = content_tokens(fact_text)
    best_start = 0
    best_score = -1
    last_start = len(words) - limit
    starts = list(range(0, last_start + 1, 20))
    if starts[-1] != last_start:
        starts.append(last_start)
    for start in starts:
        excerpt = " ".join(words[start : start + limit])
        score = len(fact_tokens & content_tokens(excerpt))
        if score > best_score:
            best_score = score
            best_start = start
    excerpt = " ".join(words[best_start : best_start + limit])
    return {
        "text": excerpt,
        "word_count": len(excerpt.split()),
        "character_count": len(excerpt),
        "selected_block_word_count": len(words),
        "excerpted_for_display": True,
        "words_omitted_before": best_start,
        "words_omitted_after": len(words) - best_start - limit,
    }


def embed_texts(
    texts: list[str],
    existing: list[list[float]] | None = None,
    checkpoint: Any | None = None,
) -> list[list[float]]:
    settings = get_settings()
    key = settings.dashscope_api_key
    if not key:
        raise RuntimeError("QWEN_API_KEY is required to rebuild the embedding cache")
    endpoint = settings.dashscope_base_url.rstrip("/") + "/embeddings"
    embeddings: list[list[float]] = list(existing or [])
    for start in range(len(embeddings), len(texts), 10):
        batch = texts[start : start + 10]
        payload = json.dumps({"model": EMBEDDING_MODEL, "input": batch}).encode()
        last_error: Exception | None = None
        for attempt in range(1, 6):
            request = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    rows = json.load(response)["data"]
                indices = [row.get("index") for row in rows]
                if len(rows) != len(batch) or set(indices) != set(range(len(batch))):
                    raise ValueError(
                        f"embedding response indices {indices!r} do not cover "
                        f"the {len(batch)} requested texts"
                    )
                rows.sort(key=lambda row: row.get("index", 0))
                vectors = [row.get("embedding") for row in rows]
                if not all(isinstance(vector, list) and vector for vector in vectors):
                    raise ValueError("embedding response contains an empty or invalid vector")
                dimensions = {len(vector) for vector in vectors}
                if len(dimensions) != 1:
                    raise ValueError(
                        f"embedding response mixes vector dimensions: {dimensions}"
                    )
                if embeddings and dimensions != {len(embeddings[0])}:
                    raise ValueError(
                        "embedding response dimensions differ from the existing cache"
                    )
                embeddings.extend(vectors)
                last_error = None
                break
            except Exception as error:  # endpoint once dropped a partial response
                last_error = error
                if attempt == 5:
                    break
                time.sleep(min(12, 1.5**attempt))
        if last_error is not None:
            raise RuntimeError(
                f"Embedding batch {start // 10 + 1} failed after retries: {last_error}"
            ) from last_error
        completed = min(start + 10, len(texts))
        if checkpoint is not None and (completed % 100 == 0 or completed == len(texts)):
            checkpoint(embeddings)
        print(f"embedded {completed}/{len(texts)}", flush=True)
    return embeddings


def load_or_build_embeddings(
    cache_path: Path,
    inventory: list[dict[str, Any]],
    samples: list[dict[str, Any]],
) -> tuple[list[list[float]], dict[str, list[float]], bool]:
    inventory_signature = [
        [fact["fact_id"], fact["source_id"], fact["text"]] for fact in inventory
    ]
    inventory_sha = stable_hash(inventory_signature)
    partial_path = cache_path.with_name(cache_path.name + ".partial")
    queries: dict[str, str] = {}
    for sample in samples:
        sentence = sample["sentence"]
        queries[f"{sample['sentence_id']}:original"] = sentence
        masked = actor_mask(sentence)
        if masked != sentence:
            queries[f"{sample['sentence_id']}:masked"] = masked
    query_hashes = {key: stable_hash(text) for key, text in queries.items()}

    cache: dict[str, Any] | None = None
    if cache_path.exists():
        with gzip.open(cache_path, "rt", encoding="utf-8") as handle:
            candidate = json.load(handle)
        metadata = candidate.get("metadata", {})
        if (
            metadata.get("embedding_model") == EMBEDDING_MODEL
            and metadata.get("inventory_sha256") == inventory_sha
            and metadata.get("fact_count") == len(inventory)
            and len(candidate.get("fact_embeddings", [])) == len(inventory)
        ):
            cache = candidate

    rebuilt = cache is None
    if cache is None:
        partial_embeddings: list[list[float]] = []
        if partial_path.exists():
            with gzip.open(partial_path, "rt", encoding="utf-8") as handle:
                partial = json.load(handle)
            if (
                partial.get("embedding_model") == EMBEDDING_MODEL
                and partial.get("inventory_sha256") == inventory_sha
                and len(partial.get("fact_embeddings", [])) <= len(inventory)
            ):
                partial_embeddings = partial["fact_embeddings"]
                print(
                    f"resuming cached partial embeddings at {len(partial_embeddings)}/{len(inventory)}",
                    flush=True,
                )

        def save_partial(embeddings: list[list[float]]) -> None:
            partial_path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(
                partial_path, "wt", encoding="utf-8", compresslevel=3
            ) as handle:
                json.dump(
                    {
                        "embedding_model": EMBEDDING_MODEL,
                        "inventory_sha256": inventory_sha,
                        "fact_embeddings": embeddings,
                    },
                    handle,
                    separators=(",", ":"),
                )

        fact_embeddings = embed_texts(
            [fact["text"] for fact in inventory],
            existing=partial_embeddings,
            checkpoint=save_partial,
        )
        query_embeddings: dict[str, list[float]] = {}
    else:
        fact_embeddings = cache["fact_embeddings"]
        cached_queries = cache.get("query_embeddings", {})
        cached_query_hashes = cache.get("metadata", {}).get(
            "query_text_sha256_by_key", {}
        )
        query_embeddings = {
            key: embedding
            for key, embedding in cached_queries.items()
            if key in query_hashes
            and cached_query_hashes.get(key) == query_hashes[key]
        }

    missing_keys = [key for key in queries if key not in query_embeddings]
    if missing_keys:
        new_embeddings = embed_texts([queries[key] for key in missing_keys])
        query_embeddings.update(zip(missing_keys, new_embeddings, strict=True))

    if rebuilt or missing_keys:
        dimensions = len(fact_embeddings[0]) if fact_embeddings else 0
        payload = {
            "metadata": {
                "schema_version": 1,
                "embedding_model": EMBEDDING_MODEL,
                "fact_count": len(inventory),
                "dimensions": dimensions,
                "inventory_sha256": inventory_sha,
                "fact_ids": [fact["fact_id"] for fact in inventory],
                "query_text_sha256_by_key": query_hashes,
                "created_at": datetime.now(UTC).isoformat(),
            },
            "fact_embeddings": fact_embeddings,
            "query_embeddings": query_embeddings,
        }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(cache_path, "wt", encoding="utf-8", compresslevel=6) as handle:
            json.dump(payload, handle, separators=(",", ":"))
        if partial_path.exists():
            partial_path.unlink()

    return fact_embeddings, query_embeddings, not rebuilt


def build_cards(
    samples: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    fact_embeddings: list[list[float]],
    query_embeddings: dict[str, list[float]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources_by_id = {source["source_id"]: source for source in sources}
    cards: list[dict[str, Any]] = []

    for sample in samples:
        original = query_embeddings[f"{sample['sentence_id']}:original"]
        masked_key = f"{sample['sentence_id']}:masked"
        masked = query_embeddings.get(masked_key, original)
        ranked: list[tuple[float, float, float, int]] = []
        for fact_index, fact_embedding in enumerate(fact_embeddings):
            original_score = cosine(original, fact_embedding)
            masked_score = cosine(masked, fact_embedding)
            ranked.append(
                (
                    max(original_score, masked_score),
                    original_score,
                    masked_score,
                    fact_index,
                )
            )
        ranked.sort(key=lambda row: (-row[0], inventory[row[3]]["fact_id"]))
        selected = [row for row in ranked[:TOP_K] if row[0] >= MIN_SCORE]

        candidates = []
        for rank, (score, original_score, masked_score, fact_index) in enumerate(
            selected, 1
        ):
            fact = inventory[fact_index]
            source = sources_by_id[fact["source_id"]]
            windows = paragraphs_for_fact(
                fact["text"], source.get("full_text") or "", window=2
            )
            candidates.append(
                {
                    "rank": rank,
                    "fact_id": fact["fact_id"],
                    "fact_text": fact["text"],
                    "source_id": fact["source_id"],
                    "source_title": source.get("title") or "Untitled source",
                    "embedding_score": round(score, 6),
                    "original_query_score": round(original_score, 6),
                    "masked_query_score": round(masked_score, 6),
                    "winning_query": (
                        "masked" if masked_score > original_score else "original"
                    ),
                    "raw_evidence_windows": [
                        compact_evidence_window(window, fact["text"])
                        for window in windows
                    ],
                }
            )

        card = dict(sample)
        card.update(
            {
                "masked_query": actor_mask(sample["sentence"]),
                "mask_applied": actor_mask(sample["sentence"])
                != sample["sentence"],
                "retrieval_no_candidate_above_floor": not selected,
                "retrieved_candidates": candidates,
                "owner_category": None,
                "owner_match_judgment": None,
            }
        )
        cards.append(card)
    return cards


def html_document(dataset: dict[str, Any]) -> str:
    embedded = (
        json.dumps(dataset, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    title = html.escape(dataset["metadata"]["current_read_identifier"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Source or writer's own point?</title>
<style>
:root{{--paper:#eef1f3;--card:#fff;--ink:#131a20;--muted:#5d6b76;--rule:#d6dee3;
  --accent:#9a5b00;--accent-soft:#fdf1de;--pick:#2f4f5e;--pick-soft:#e4eef2;--src:#f6f8f9}}
@media (prefers-color-scheme:dark){{:root{{--paper:#0e1418;--card:#161e24;--ink:#e6edf1;
  --muted:#93a3ae;--rule:#2a353d;--accent:#e0a24a;--accent-soft:#2a2015;
  --pick:#8fc0d4;--pick-soft:#17262d;--src:#111920}}}}
*{{box-sizing:border-box}}
body{{background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif;
  margin:0;padding:0 20px 72px;line-height:1.55}}
.wrap{{max-width:760px;margin:0 auto}}
header{{padding:50px 0 22px}}
h1{{font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;font-weight:500;
  font-size:clamp(29px,5vw,38px);line-height:1.15;margin:0 0 12px}}
.lede{{color:var(--muted);font-size:16px;margin:0;max-width:65ch}}
.version{{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);margin-top:14px}}
.bar{{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--paper) 94%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--rule);padding:12px 0;margin-bottom:28px;
  display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
.progress{{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}}
.progress b{{color:var(--accent)}}
.summary{{flex:1;text-align:right;color:var(--muted);font-size:13px}}
.card{{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:clamp(20px,5vw,30px)}}
.position{{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);margin-bottom:15px}}
.sentence{{font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;font-size:22px;
  line-height:1.55;margin:0 0 24px}}
.question{{font-size:16px;font-weight:600;margin:0 0 13px}}
.choices{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
button{{font-family:inherit;font-size:14px;font-weight:600;border:1px solid var(--rule);border-radius:8px;padding:12px 15px;
  cursor:pointer;background:transparent;color:var(--ink)}}
button:hover:not(:disabled){{border-color:var(--accent);background:var(--accent-soft)}}
button:focus-visible{{outline:3px solid var(--accent);outline-offset:2px}}
button[aria-pressed="true"]{{background:var(--accent-soft);border-color:var(--accent)}}
button.analysis[aria-pressed="true"]{{background:var(--pick-soft);border-color:var(--pick)}}
button:disabled{{opacity:.45;cursor:not-allowed}}
.evidence{{margin-top:24px;padding-top:21px;border-top:1px dashed var(--rule)}}
.evidence-intro{{color:var(--muted);font-size:14px;margin:0 0 16px}}
.candidate{{background:var(--src);border:1px solid var(--rule);border-radius:9px;padding:16px;margin:0 0 13px}}
.candidate-head{{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);margin-bottom:8px}}
.fact{{font-size:14px;margin:0 0 13px}}
.window{{border-left:3px solid var(--rule);padding-left:12px;color:var(--muted);font-size:14px;
  line-height:1.62;margin:10px 0 0;white-space:pre-wrap}}
.window-meta{{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);margin-top:10px}}
.second{{font-weight:600;margin:20px 0 12px}}
.judgments{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.nav{{display:flex;gap:10px;justify-content:space-between;margin-top:18px}}
.nav-group{{display:flex;gap:10px}}
.primary{{background:var(--ink);color:var(--card);border-color:var(--ink)}}
.primary:hover:not(:disabled){{background:var(--accent);border-color:var(--accent);color:white}}
.complete{{margin-top:18px;padding:15px;border:1px solid var(--pick);background:var(--pick-soft);
  border-radius:9px}}
[hidden]{{display:none!important}}
@media(max-width:620px){{.choices,.judgments{{grid-template-columns:1fr}}.summary{{text-align:left;flex-basis:100%}}
  .nav{{align-items:stretch}}.nav-group{{flex:1}}.nav-group button{{flex:1}}}}
@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;transition:none!important}}}}
</style>
</head>
<body>
<main class="wrap">
<header>
  <h1>Source, or the writer’s own point?</h1>
  <p class="lede">You’ll see 15 sentences from the current Read. First decide what kind of sentence it is. If you choose SOURCE, the best retrieved passages will appear so you can check whether the sentence matches them. You never need to identify provenance or judge the retrieval.</p>
  <div class="version">{title}</div>
</header>
<div class="bar">
  <span class="progress"><b id="step">1 / 15</b> · <span id="answered">0 answered</span></span>
  <span class="summary" id="summary">No answer selected</span>
  <button id="exportTop" type="button">Export JSON</button>
</div>
<article class="card" id="card" tabindex="-1" aria-live="polite">
  <div class="position" id="position"></div>
  <p class="sentence" id="sentence"></p>
  <p class="question">Is this sentence repeating information from a source, or is it the writer making its own point?</p>
  <div class="choices">
    <button id="source" type="button" data-category="source">SOURCE</button>
    <button id="analysis" class="analysis" type="button" data-category="analysis">WRITER’S OWN POINT</button>
  </div>
  <section class="evidence" id="evidence" hidden>
    <p class="evidence-intro">These passages are the closest retrieved context, not ground truth. Read them only to decide whether the sentence matches what the source says.</p>
    <div id="candidates"></div>
    <p class="second">Does the sentence match what the source evidence says?</p>
    <div class="judgments" id="judgments">
      <button type="button" data-judgment="match">MATCHES SOURCE</button>
      <button type="button" data-judgment="mismatch">DOES NOT MATCH</button>
      <button type="button" data-judgment="unclear">NOT ENOUGH TO TELL</button>
    </div>
  </section>
  <div class="complete" id="complete" hidden>All 15 are answered. Export the JSON for the semantic-check benchmark.</div>
  <nav class="nav" aria-label="Sentence navigation">
    <div class="nav-group"><button id="previous" type="button">Previous</button><button id="next" type="button">Next</button></div>
    <button class="primary" id="exportBottom" type="button">Export JSON</button>
  </nav>
</article>
</main>
<script>
const DATA={embedded};
const STORAGE_KEY="semantic-labeling:"+DATA.metadata.labeling_artifact_sha256;
let current=0;
let answers={{}};
try{{answers=JSON.parse(sessionStorage.getItem(STORAGE_KEY)||"{{}}")||{{}};}}catch(_error){{answers={{}};}}
const byId=id=>document.getElementById(id);
function answerFor(item){{return answers[item.sentence_id]||{{owner_category:null,owner_match_judgment:null}};}}
function completeAnswer(answer){{return answer.owner_category==="analysis"||(answer.owner_category==="source"&&!!answer.owner_match_judgment);}}
function save(){{try{{sessionStorage.setItem(STORAGE_KEY,JSON.stringify(answers));}}catch(_error){{/* State still lives in memory when storage is unavailable. */}}}}
function setPressed(container,attribute,value){{container.querySelectorAll("button[data-"+attribute+"]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset[attribute]===value)));}}
function evidenceCard(candidate){{
  const article=document.createElement("article"); article.className="candidate";
  const head=document.createElement("div"); head.className="candidate-head";
  head.textContent="#"+candidate.rank+" · "+candidate.fact_id+" · "+candidate.source_id+" · score "+candidate.embedding_score.toFixed(3)+" · "+candidate.source_title;
  const fact=document.createElement("p"); fact.className="fact"; fact.textContent="Retrieved fact: "+candidate.fact_text;
  article.append(head,fact);
  candidate.raw_evidence_windows.forEach((window,index)=>{{
    const passage=document.createElement("p"); passage.className="window"; passage.textContent=window.text;
    const meta=document.createElement("div"); meta.className="window-meta";
    meta.textContent="Raw evidence window "+(index+1)+" · "+window.word_count+" words"+(window.excerpted_for_display?" · bounded excerpt from a "+window.selected_block_word_count+"-word selected block":"");
    article.append(passage,meta);
  }});
  return article;
}}
function render(focus=false){{
  const item=DATA.items[current],answer=answerFor(item);
  byId("step").textContent=(current+1)+" / "+DATA.items.length;
  const done=DATA.items.filter(row=>completeAnswer(answerFor(row))).length;
  byId("answered").textContent=done+" answered";
  byId("position").textContent=item.sentence_id+" · "+item.paragraph_label+" · paragraph "+item.paragraph_index+", sentence "+item.sentence_index_in_paragraph;
  byId("sentence").textContent=item.sentence;
  setPressed(document.querySelector(".choices"),"category",answer.owner_category);
  byId("evidence").hidden=answer.owner_category!=="source";
  const candidates=byId("candidates"); candidates.replaceChildren();
  if(answer.owner_category==="source"){{
    if(item.retrieved_candidates.length) item.retrieved_candidates.forEach(candidate=>candidates.append(evidenceCard(candidate)));
    else{{const empty=document.createElement("p");empty.className="candidate";empty.textContent="No retrieved fact met the 0.55 minimum score. Choose NOT ENOUGH TO TELL if the available evidence cannot support a match judgment.";candidates.append(empty);}}
  }}
  setPressed(byId("judgments"),"judgment",answer.owner_match_judgment);
  byId("summary").textContent=answer.owner_category==="analysis"?"WRITER’S OWN POINT selected":answer.owner_category==="source"?(answer.owner_match_judgment?"SOURCE · "+answer.owner_match_judgment.toUpperCase():"SOURCE selected · match judgment needed"):"No answer selected";
  byId("previous").disabled=current===0;
  byId("next").disabled=!completeAnswer(answer)||current===DATA.items.length-1;
  byId("complete").hidden=done!==DATA.items.length;
  if(focus){{byId("card").focus();window.scrollTo({{top:0,behavior:"smooth"}});}}
}}
document.querySelectorAll("[data-category]").forEach(button=>button.addEventListener("click",()=>{{
  const item=DATA.items[current],category=button.dataset.category;
  answers[item.sentence_id]={{owner_category:category,owner_match_judgment:null}};
  save();render();
}}));
document.querySelectorAll("[data-judgment]").forEach(button=>button.addEventListener("click",()=>{{
  const item=DATA.items[current],answer=answerFor(item);
  if(answer.owner_category!=="source") return;
  answers[item.sentence_id]={{owner_category:"source",owner_match_judgment:button.dataset.judgment}};
  save();render();
}}));
byId("previous").addEventListener("click",()=>{{if(current>0){{current--;render(true);}}}});
byId("next").addEventListener("click",()=>{{if(current<DATA.items.length-1&&completeAnswer(answerFor(DATA.items[current]))){{current++;render(true);}}}});
function exportJson(){{
  const payload=JSON.parse(JSON.stringify(DATA)); payload.exported_at=new Date().toISOString();
  payload.items=payload.items.map(item=>Object.assign(item,answerFor(item)));
  const blob=new Blob([JSON.stringify(payload,null,2)],{{type:"application/json"}});
  const link=document.createElement("a"),url=URL.createObjectURL(blob); link.href=url;
  link.download="semantic_labeling_current_read.json"; document.body.append(link); link.click(); link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}}
byId("exportTop").addEventListener("click",exportJson);byId("exportBottom").addEventListener("click",exportJson);
render();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read", type=Path, default=DEFAULT_READ)
    parser.add_argument("--harvest", type=Path, default=DEFAULT_HARVEST)
    parser.add_argument("--source-vault", type=Path, default=DEFAULT_SOURCE_VAULT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()

    read_data = read_json(args.read)
    harvest_payload = read_json(args.harvest)
    sources = read_source_vault(args.source_vault)
    if not (
        isinstance(harvest_payload, dict)
        and isinstance(harvest_payload.get("metadata"), dict)
        and isinstance(harvest_payload.get("harvest"), dict)
    ):
        raise ValueError("Current harvest is missing its source/model provenance")
    harvest = harvest_payload["harvest"]
    harvest_provenance = harvest_payload["metadata"]
    source_signature = [
        [source["source_id"], source["title"], source["url"], source["full_text"]]
        for source in sources
    ]
    expected_source_hash = stable_hash(source_signature)
    if harvest_provenance.get("source_vault_sha256") != expected_source_hash:
        raise ValueError("Harvest source-vault fingerprint does not match the current vault")
    if harvest_provenance.get("harvest_sha256") != stable_hash(harvest):
        raise ValueError("Harvest content fingerprint does not match its provenance")
    if harvest_provenance.get("harvest_fact_count") != sum(
        map(len, harvest.values())
    ):
        raise ValueError("Harvest fact count does not match its provenance")
    settings = get_settings()
    expected_harvest_configuration = {
        "harvest_max_chars": settings.harvest_max_chars,
        "harvest_chunk_overlap": settings.harvest_chunk_overlap,
        "harvest_facts_per_1000": settings.harvest_facts_per_1000,
    }
    if harvest_provenance.get("harvest_model") != settings.model_harvest:
        raise ValueError("Harvest model does not match the current harvest seat")
    if (
        harvest_provenance.get("harvest_configuration")
        != expected_harvest_configuration
    ):
        raise ValueError("Harvest configuration does not match current settings")
    inventory = build_inventory(harvest)
    samples = selected_sentences(read_data)

    if not inventory:
        raise ValueError("The current-source harvest is empty")
    if len(sources) != 16:
        raise ValueError(f"Expected all 16 current sources; got {len(sources)}")
    if sum(len(source["full_text"].split()) for source in sources) != 42263:
        raise ValueError("The source vault does not match the 42,263-word D-038 input")
    if len(samples) != 15:
        raise ValueError(f"Expected exactly 15 selected sentences; got {len(samples)}")

    fact_embeddings, query_embeddings, reused = load_or_build_embeddings(
        args.cache, inventory, samples
    )
    cards = build_cards(
        samples,
        inventory,
        fact_embeddings,
        query_embeddings,
        sources,
    )

    read_snapshot = read_data["read"]
    read_sha = stable_hash(read_snapshot)
    metadata = {
        "schema_version": 1,
        "task": "owner_source_vs_analysis_labeling",
        "current_read_identifier": (
            "D-038 accepted Hawara Read · hawara-rerun · Briefing v1 · 2026-08-22"
        ),
        "decision": "D-038",
        "job_id": read_data.get("job_id"),
        "briefing_version": read_data.get("briefing_version"),
        "read_generated_on": read_data.get("meta", {}).get("generated_on"),
        "topic": read_data.get("topic"),
        "read_sha256": read_sha,
        "read_word_count": len(
            " ".join(
                [read_snapshot["lede"]]
                + [paragraph["text"] for paragraph in read_snapshot["paragraphs"]]
            ).split()
        ),
        "read_paragraph_count": len(read_snapshot["paragraphs"]),
        "harvest_fact_count": len(inventory),
        "harvest_sha256": stable_hash(harvest),
        "harvest_recovery": {
            "accepted_run_fact_count": 1253,
            "accepted_cache_available": False,
            "replayed_fact_count": len(inventory),
            "replayed_model": "gpt-5.4-mini",
            "source_vault_word_count": 42263,
            "note": (
                "The accepted 1,253-fact scratchpad harvest was never checked in. "
                "A harvest-only replay against the exact checked-in 16-source vault "
                "returned a nondeterministic 1,270 facts; none were arbitrarily removed."
            ),
        },
        "embedding_model": EMBEDDING_MODEL,
        "embedding_cache": args.cache.name,
        "embedding_cache_reused_for_this_build": reused,
        "embedding_cache_provenance": {
            "legacy_pre_d038_fact_count": 633,
            "legacy_cache_reused": False,
            "current_cache_fact_count": len(inventory),
            "current_cache_reused_for_final_render": reused,
            "task_action": (
                "rebuilt for the recovered current-source harvest, then reused "
                "for deterministic final renders"
            ),
        },
        "retrieval": {
            "method": "embedding",
            "query_union": ["original", "actor_masked_where_applicable"],
            "top_k": TOP_K,
            "minimum_score_floor": MIN_SCORE,
            "no_candidate_behavior": (
                "show no passage and let the owner record the unclear judgment "
                "when no candidate meets the floor"
            ),
            "similarity_is_correctness_verdict": False,
        },
        "evidence_window_function": (
            "backend.pipeline.briefing_routing.paragraphs_for_fact(window=2), "
            "using backend.pipeline.harvest_audit.blocks_of fallback; selected "
            "blocks over 180 words are bounded to a relevant contiguous excerpt"
        ),
        "maximum_display_evidence_window_words": MAX_EVIDENCE_WORDS,
        "sampling": {
            "count": 15,
            "method": (
                "manual varied sample across the lede and all nine D-038 Read "
                "paragraphs, including factual, analytical, negative/corpus, "
                "and mixed source-plus-inference sentences"
            ),
            "selected_positions": [list(position) for position in SELECTED_POSITIONS],
        },
        "built_at": datetime.now(UTC).isoformat(),
    }
    metadata["labeling_artifact_sha256"] = stable_hash(
        [
            {
                "sentence_id": card["sentence_id"],
                "sentence": card["sentence"],
                "retrieved_candidates": card["retrieved_candidates"],
            }
            for card in cards
        ]
    )
    dataset = {"metadata": metadata, "items": cards}
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    with args.json_output.open("w", encoding="utf-8") as handle:
        json.dump(dataset, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    args.html_output.write_text(html_document(dataset), encoding="utf-8")

    window_sizes = [
        window["word_count"]
        for card in cards
        for candidate in card["retrieved_candidates"]
        for window in candidate["raw_evidence_windows"]
    ]
    print(
        json.dumps(
            {
                "read": metadata["current_read_identifier"],
                "read_sha256": read_sha,
                "facts": len(inventory),
                "cards": len(cards),
                "cache_reused": reused,
                "max_evidence_window_words": max(window_sizes, default=0),
                "json": str(args.json_output),
                "html": str(args.html_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
