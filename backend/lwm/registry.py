"""Stage 4: the canonical 9-column registry, derived from RA evidence.

Mechanical columns come from the job (code, here). Judgment columns come from
ONE fresh-family model pass (judge seat — never the drafter's), and code
validates everything the model returns: a row can cite only sources whose
harvested evidence actually supports its claim, statuses come from a closed
vocabulary, and a rerun regenerates the table rather than appending. The
Phase 0 lesson is built in: two of three hand-written validation rows
mis-attributed their sources, so provenance is checked by code, never
trusted from any author — human or model.
"""

from typing import Any

from loguru import logger

from backend.pipeline.text_similarity import content_tokens

CLASSES = ("STORY", "THEORY", "REALITY")
STATUSES = ("CONFIRMED", "REPORTED", "CONTESTED", "MISSING-SOURCE")

# A claim is supported by a source when this share of its content words
# appears in ONE of that source's harvested facts…
SUPPORT_FLOOR = 0.5
# …or, because key points are synthesized across several facts of one source,
# in the UNION of that source's facts — at a stricter floor, so a big source
# cannot vouch for an arbitrary claim just by having a lot of words.
UNION_FLOOR = 0.75


def _supported_by(claim: str, source_id: str,
                  evidence_by_source: dict[str, list[tuple[str, str]]],
                  own_kp_id: str = "") -> bool:
    want = content_tokens(claim)
    if not want:
        return False
    pool: set[str] = set()
    for kp_id, text in evidence_by_source.get(source_id, []):
        if own_kp_id and kp_id == own_kp_id:
            continue  # self-support is not support
        tokens = content_tokens(text)
        if len(want & tokens) / len(want) >= SUPPORT_FLOOR:
            return True
        pool |= tokens
    return len(want & pool) / len(want) >= UNION_FLOOR


def build(doc_0: dict, doc_1: dict, harvest: dict | None = None,
          judgment_client: Any = None) -> dict:
    """Rows from the job's key points; provenance validated against evidence.

    Args:
        doc_0: Source ledger (source ids ↔ urls/titles).
        doc_1: Jump-start — key points with source_ids and confidence,
            tensions naming contested key points.
        harvest: Optional {source_id: [fact, ...]} for support checking; when
            absent, key-point statements from doc_1 serve as the evidence pool.
        judgment_client: Structured client for the fresh-family pass; None
            leaves judgment columns pending (mechanical-only registry).
    """
    valid_sources = {s["source_id"] for s in doc_0.get("sources", []) if s.get("source_id")}

    # Evidence pool: harvested facts when available. Key-point statements are
    # only a fallback (no harvest), and NEVER a key point's own statement — a
    # claim must not be allowed to support itself, or a fabricated key point
    # citing any source would sail through validation.
    evidence: dict[str, list[tuple[str, str]]] = {}
    if harvest:
        for sid, facts in harvest.items():
            evidence.setdefault(sid, []).extend(("", f) for f in facts)
    else:
        for kp in doc_1.get("key_points", []):
            for sid in kp.get("source_ids", []):
                evidence.setdefault(sid, []).append(
                    (kp.get("key_point_id", ""), kp.get("statement", "")))

    contested_kps = {
        kp_id
        for t in doc_1.get("tensions", [])
        for kp_id in (t.get("involved_key_points") or [])
    }

    rows = []
    flagged = 0
    for kp in doc_1.get("key_points", []):
        claim = (kp.get("statement") or "").strip()
        if not claim:
            continue
        cited = [s for s in kp.get("source_ids", []) if s in valid_sources]
        # Provenance is decided structurally first: the RA recorded which of
        # its own extraction claims support this key point. Lexical similarity
        # finds suspects, it never convicts (doctrine) — real analytic key
        # points cover only 25-60% of their source's vocabulary, because the
        # words are the analyst's. So: a row keeps its RA provenance; lexical
        # support upgrades confidence; a row with NEITHER structural nor
        # lexical support is the fabrication case and is flagged.
        has_structure = bool(kp.get("supporting_claims"))
        lexical = [s for s in cited
                   if _supported_by(claim, s, evidence, kp.get("key_point_id", ""))]
        supported = cited if (has_structure and cited) else lexical
        if supported:
            if kp.get("key_point_id") in contested_kps:
                status = "CONTESTED"
            elif kp.get("confidence") == "high" and lexical:
                status = "CONFIRMED"  # earned twice: RA confidence AND the words are in the evidence
            else:
                status = "REPORTED"
        else:
            status, flagged = "MISSING-SOURCE", flagged + 1
        rows.append({
            "n": len(rows) + 1,
            "claim": claim,
            "class": "",           # judgment
            "status": status,       # mechanical seed; judgment may tighten wording, never invent
            "source": " · ".join(supported) or "—",
            "kp_id": kp.get("key_point_id", ""),
            "lb": "",              # judgment
            "allowed": "",         # judgment
            "prohibited": "",      # judgment
            "anchor": "—",         # judgment, only where applicable
        })

    judged = False
    if judgment_client is not None and rows:
        judged = _judgment_pass(rows, judgment_client)

    return {"rows": rows, "flagged": flagged, "judged": judged}


_JUDGMENT_ROLE = """You are the fresh-eyes fact-check pass on a claim registry for a
storytelling script. Refute-first; agreeableness is failure. For each numbered claim decide:
- class: STORY (a source's account, must be told as them saying it) / THEORY (interpretation)
  / REALITY (safe to state flatly in our own voice)
- lb: is this claim load-bearing for the video (top-five the story rests on)? true/false
- allowed: the certainty-controlled wording the drafter may use (short phrase)
- prohibited: wording that overstates it (short phrase, or empty)
- anchor: ONLY if the claim carries a number that invites comparison, one verified everyday
  comparison using the claim's own figure; otherwise empty. Never invent a figure.
Return one entry per claim number."""

_JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {"rows": {"type": "array", "items": {"type": "object", "properties": {
        "n": {"type": "integer"}, "class": {"type": "string"}, "lb": {"type": "boolean"},
        "allowed": {"type": "string"}, "prohibited": {"type": "string"}, "anchor": {"type": "string"},
    }, "required": ["n", "class", "lb", "allowed"]}}},
    "required": ["rows"],
}


def _judgment_pass(rows: list[dict], client: Any) -> bool:
    """One structured call per batch; code applies only well-formed answers."""
    ok = True
    for start in range(0, len(rows), 20):
        batch = rows[start:start + 20]
        listing = "\n".join(f"{r['n']}. {r['claim']}  [status: {r['status']}]" for r in batch)
        try:
            data, _ = client.generate_structured(
                prompt=listing, schema=_JUDGMENT_SCHEMA, system=_JUDGMENT_ROLE, max_tokens=8000)
        except Exception as e:
            logger.error(f"registry judgment batch failed at row {start + 1}: {e}")
            ok = False
            continue
        by_n = {r["n"]: r for r in batch}
        for ans in data.get("rows", []):
            row = by_n.get(ans.get("n"))
            cls = (ans.get("class") or "").upper()
            if not row or cls not in CLASSES:
                continue  # malformed answers are dropped, never guessed at
            row["class"] = cls
            row["lb"] = "y" if ans.get("lb") else "n"
            row["allowed"] = (ans.get("allowed") or "").strip()
            row["prohibited"] = (ans.get("prohibited") or "").strip()
            anchor = (ans.get("anchor") or "").strip()
            # An anchor may only use numbers the claim itself carries (D-21:
            # translate once, never invent).
            if anchor and _numbers_ok(anchor, row["claim"]):
                row["anchor"] = anchor
    return ok


def _numbers_ok(anchor: str, claim: str) -> bool:
    import re
    claim_numbers = set(re.findall(r"\d[\d,.]*", claim))
    anchor_numbers = set(re.findall(r"\d[\d,.]*", anchor))
    return anchor_numbers <= claim_numbers or not anchor_numbers


def validate(rows: list[dict]) -> list[str]:
    """Code validation — the tests' contract. Empty list = valid."""
    problems = []
    seen = set()
    for r in rows:
        if r["status"] not in STATUSES:
            problems.append(f"row {r['n']}: invalid status {r['status']!r}")
        if r["class"] and r["class"] not in CLASSES:
            problems.append(f"row {r['n']}: invalid class {r['class']!r}")
        if r["lb"] not in ("", "y", "n"):
            problems.append(f"row {r['n']}: invalid LB {r['lb']!r}")
        if r["status"] != "MISSING-SOURCE" and r["source"] == "—":
            problems.append(f"row {r['n']}: no source but status {r['status']}")
        key = r["kp_id"] or r["claim"]
        if key in seen:
            problems.append(f"row {r['n']}: duplicate of {key!r}")
        seen.add(key)
    return problems


def render(reg: dict, job_id: str) -> str:
    head = f"""<!--
artifact:  04-sources-registry
version:   v2 (generated by lwm handoff from RA job {job_id})
upstream:  03-brief (RA Doc 0 = source truth)
readiness: {'populated' if reg['judged'] else 'mechanical columns only — judgment pass pending'}
unresolved: {reg['flagged']} row(s) MISSING-SOURCE (attribute, never cut)
-->

# Sources registry

Derived from RA job `{job_id}`. Doc 0 (preserved at `research/doc_0.json`) resolves every source
id. Writer-safety, not re-research; open-web verification happens on the finished script (D-SFC-1,
stage 10b). Regenerating this file replaces the whole table — rows are never appended twice.

| # | claim | class | status | source | LB | allowed wording | prohibited wording | anchor |
|---|---|---|---|---|---|---|---|---|
"""
    lines = [
        "| {n} | {claim} | {cls} | {status} | {source} | {lb} | {allowed} | {prohibited} | {anchor} |".format(
            n=r["n"], claim=r["claim"].replace("|", "/"), cls=r["class"] or "—",
            status=r["status"], source=r["source"], lb=r["lb"] or "—",
            allowed=r["allowed"].replace("|", "/") or "—",
            prohibited=r["prohibited"].replace("|", "/") or "—", anchor=r["anchor"] or "—")
        for r in reg["rows"]
    ]
    return head + "\n".join(lines) + "\n\nMISSING SOURCE = attribute and keep, never cut. A negative strikes the specific, never the event.\n"
