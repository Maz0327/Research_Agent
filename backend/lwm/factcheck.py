"""Stage 10b — the final-script fact check (D-SFC-1).

The one verification that matters happens HERE, on the finished script,
against the live web. Contract: extract only verifiable claims with entities
intact → search → fetch the actual page → a reasoning model gives one of four
verdicts with a supporting quote → and SUPPORTED stands only when CODE finds
that quote in the fetched page. The checker NEVER edits the script. False
reassurance is the failure mode this design exists to prevent: models judge
most statements true regardless, so "verified" is expensive and "not enough
evidence" is cheap.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from backend.pipeline.text_similarity import content_tokens, has_negation

VERDICTS = ("SUPPORTED", "REFUTED", "CONFLICTING", "NOT ENOUGH EVIDENCE")
MAX_WORKERS = 6


# ---------------------------------------------------------------- extraction

_EXTRACT_ROLE = """Extract the objectively verifiable factual claims from this script.

A verifiable claim is a single event or state, with every modifier needed to pin it to the real
world — names, dates, places, numbers kept EXACTLY as the script has them. Resolve pronouns from
context. Skip opinions, framing, rhetorical questions, the narrator's interpretations, and
anything whose meaning you cannot pin down from the text — skipping is correct, guessing is not.
For claims the script ATTRIBUTES to someone ("Packer said he shot Bell in self-defense"), the
claim to verify is the attribution itself, marked attributed=true — not the underlying assertion.
Return each claim with the exact script sentence it came from."""

_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array", "items": {"type": "object", "properties": {
        "claim": {"type": "string"}, "script_line": {"type": "string"},
        "attributed": {"type": "boolean"},
    }, "required": ["claim", "script_line"]}}},
    "required": ["claims"],
}


def extract_claims(script: str, client: Any) -> list[dict]:
    """Model proposes; code verifies entities and grounding in the script."""
    data, _ = client.generate_structured(
        prompt=script, schema=_EXTRACT_SCHEMA, system=_EXTRACT_ROLE, max_tokens=16000)
    script_tokens = content_tokens(script)
    kept = []
    for c in data.get("claims", []):
        claim, line = (c.get("claim") or "").strip(), (c.get("script_line") or "").strip()
        if not claim or not line:
            continue
        # Entity preservation: every capitalised name and number in the claim
        # must exist in the script — an extractor that invents or mangles an
        # entity would send the verifier chasing the wrong fact.
        entities = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b\d[\d,.]*\b", claim))
        if any(e.lower() not in script.lower() for e in entities):
            logger.info(f"fact-check: dropped claim with unseen entity: {claim[:60]!r}")
            continue
        if not (content_tokens(claim) & script_tokens):
            continue
        kept.append({"claim": claim, "script_line": line,
                     "attributed": bool(c.get("attributed"))})
    return kept


# ------------------------------------------------------------ search + fetch

def default_search(query: str, max_results: int = 5) -> list[dict]:
    """Brave web search — the key already lives in this repo's settings."""
    import os
    import urllib.parse
    import urllib.request

    import backend.config  # noqa: F401 — loads .env into the environment
    key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not key:
        raise RuntimeError("no BRAVE_SEARCH_API_KEY configured for fact-check search")
    req = urllib.request.Request(
        "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
            {"q": query, "count": max_results}),
        headers={"X-Subscription-Token": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return [{"url": w.get("url"), "title": w.get("title"), "snippet": w.get("description", "")}
            for w in (data.get("web", {}).get("results") or [])[:max_results]]


def default_fetch(url: str) -> str:
    """Fetch a page's text through the existing Jina reader integration."""
    from backend.integrations.jina_reader_client import JinaReaderClient
    result = JinaReaderClient().extract(url)
    return (result or {}).get("content") or ""


# ------------------------------------------------------- quote verification

def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def quote_in_text(quote: str, page: str) -> bool:
    """Ordered evidence check — NEVER a bag of words.

    Exact normalized substring passes. Otherwise the quote's ordered 5-word
    shingles must overwhelmingly appear in the page, which tolerates an
    ellipsis or a rendering hiccup but fails any quote assembled from the
    page's vocabulary in a different order — the fabrication that sailed
    through the old bag-of-words check.
    """
    q, p = _normalize(quote), _normalize(page)
    if not q or not p:
        return False
    if q in p:
        return True
    words = q.split()
    if len(words) < 5:
        return False
    shingles = [" ".join(words[i:i + 5]) for i in range(len(words) - 4)]
    hits = sum(1 for s in shingles if s in p)
    return hits / len(shingles) >= 0.8


# ----------------------------------------------------------------- verdicts

_VERDICT_ROLE = """You are verifying ONE factual claim against fetched source material. Some of
these claims may be false — treat "true" as a conclusion that must be earned, not a default.

Answer with exactly one verdict:
- SUPPORTED: the material clearly supports the claim. You MUST include the url used and quote,
  VERBATIM from that source's text, the passage that supports it.
- REFUTED: the material clearly contradicts the claim. Include url + the contradicting quote.
- CONFLICTING: credible fetched sources genuinely disagree. Include both urls in notes.
- NOT ENOUGH EVIDENCE: the material neither supports nor refutes it. This is a good answer;
  never stretch a partial match into SUPPORTED.
An attributed claim ("X said Y") is verified as the attribution, not the underlying fact."""

_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string"}, "url": {"type": "string"},
                   "quote": {"type": "string"}, "notes": {"type": "string"}},
    "required": ["verdict"],
}


@dataclass
class Finding:
    claim: str
    script_line: str
    verdict: str
    url: str = ""
    quote: str = ""
    notes: str = ""
    quote_verified: bool = False
    material: bool = False
    load_bearing: bool = False
    downgraded_from: str = ""


def check_claim(claim: dict, client: Any, search, fetch) -> Finding:
    try:
        results = search(claim["claim"])
    except Exception as e:
        return Finding(claim=claim["claim"], script_line=claim["script_line"],
                       verdict="NOT ENOUGH EVIDENCE", notes=f"search failed: {e}")
    pages = []
    for r in results[:3]:
        try:
            text = fetch(r["url"])
        except Exception as e:
            logger.info(f"fact-check: fetch failed {r['url']}: {e}")
            continue
        if text.strip():
            pages.append({"url": r["url"], "text": text[:20000]})
    if not pages:
        return Finding(claim=claim["claim"], script_line=claim["script_line"],
                       verdict="NOT ENOUGH EVIDENCE", notes="no source page could be fetched")

    evidence = "\n\n".join(f"[SOURCE {p['url']}]\n{p['text']}" for p in pages)
    prompt = (f"CLAIM{' (attributed)' if claim.get('attributed') else ''}: {claim['claim']}\n\n"
              f"FETCHED MATERIAL:\n{evidence}")
    try:
        data, _ = client.generate_structured(
            prompt=prompt, schema=_VERDICT_SCHEMA, system=_VERDICT_ROLE, max_tokens=4000)
    except Exception as e:
        return Finding(claim=claim["claim"], script_line=claim["script_line"],
                       verdict="NOT ENOUGH EVIDENCE", notes=f"verdict call failed: {e}")

    verdict = (data.get("verdict") or "").upper().strip()
    if verdict not in VERDICTS:
        verdict = "NOT ENOUGH EVIDENCE"
    f = Finding(claim=claim["claim"], script_line=claim["script_line"], verdict=verdict,
                url=(data.get("url") or "").strip(), quote=(data.get("quote") or "").strip(),
                notes=(data.get("notes") or "").strip())

    if f.verdict in ("SUPPORTED", "REFUTED"):
        page = next((p for p in pages if p["url"] == f.url), None)
        # The teeth: the quoted evidence must exist, verbatim-ordered, in the
        # page WE fetched. A verdict whose receipt fails inspection is not a
        # verdict — it is downgraded, with the reason on the record.
        f.quote_verified = bool(page and f.quote and quote_in_text(f.quote, page["text"]))
        if not f.quote_verified:
            f.downgraded_from, f.verdict = f.verdict, "NOT ENOUGH EVIDENCE"
            f.notes = (f.notes + " | evidence quote not found in fetched source — verdict downgraded by code").strip(" |")
        elif f.verdict == "SUPPORTED" and has_negation(f.claim) and not has_negation(f.quote):
            # Polarity guard, one direction only: a NEGATED claim ("was not
            # convicted of murder") is never supported by an affirming quote —
            # that is the exact reversal that scored 1.000 in the old
            # similarity primitive. The other direction is fine: evidence
            # saying "manslaughter, not murder" legitimately supports an
            # un-negated manslaughter claim.
            f.downgraded_from, f.verdict = f.verdict, "NOT ENOUGH EVIDENCE"
            f.notes = (f.notes + " | negated claim vs affirming evidence — downgraded by code").strip(" |")

    # Materiality is decided by the caller, which knows the load-bearing rows.
    return f


def _matches_lb(claim: str, lb_claims: list[str]) -> bool:
    """Deterministic LB matching: content-token containment against a
    load-bearing registry claim. Code decides; no model in the loop."""
    from backend.pipeline.text_similarity import statement_similarity
    return any(statement_similarity(claim, lb) >= 0.5 for lb in lb_claims)


def load_bearing_claims(episode: Path) -> list[str]:
    """The registry's LB rows — the stage-4 context 10b materiality rests on."""
    reg = episode / "04-sources-registry.md"
    if not reg.exists():
        return []
    rows = []
    for line in reg.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) == 9 and cells[0] not in ("#", "---") and cells[5] == "y":
            rows.append(cells[1])
    return rows


def run(script_path: Path, out_dir: Path, client: Any, search=None, fetch=None,
        claims: list[dict] | None = None, lb_claims: list[str] | None = None) -> dict:
    """The whole pass. Reads the script; never writes it.

    Returns the summary; writes `10b-fact-check.md` (for Maz: material findings
    first, short) and `10b-fact-check.json` (for the UI: everything).
    """
    script = script_path.read_text()
    search = search or default_search
    fetch = fetch or default_fetch
    claims = claims if claims is not None else extract_claims(script, client)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        findings = list(pool.map(lambda c: check_claim(c, client, search, fetch), claims))

    # Materiality (D-SFC policy): REFUTED and CONFLICTING block regardless.
    # A LOAD-BEARING claim that cannot be verified blocks too — the video
    # rests on it, so "not enough evidence" needs Maz's ruling, not a shrug.
    # An unverifiable aside stays advisory: never Maz homework.
    lb = lb_claims or []
    for f in findings:
        f.load_bearing = _matches_lb(f.claim, lb)
        f.material = (f.verdict in ("REFUTED", "CONFLICTING")
                      or (f.load_bearing and f.verdict == "NOT ENOUGH EVIDENCE"))

    counts = {v: sum(1 for f in findings if f.verdict == v) for v in VERDICTS}
    material = [f for f in findings if f.material]

    report = {
        "script": str(script_path), "claims_checked": len(findings),
        "counts": counts, "material_findings": len(material),
        "blocks_recording": bool(material),
        "findings": [asdict(f) for f in findings],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "10b-fact-check.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    (out_dir / "10b-fact-check.md").write_text(_render_md(report))
    return report


def _render_md(report: dict) -> str:
    lines = [
        "<!--\nartifact:  10b-fact-check\nversion:   v1\nreadiness: complete\n-->\n",
        "# Final script fact-check (D-SFC-1)\n",
        f"{report['claims_checked']} claims checked · "
        + " · ".join(f"{v.lower()} {n}" for v, n in report["counts"].items()) + "\n",
        ("**MATERIAL BLOCKERS — a ruling is needed before recording:**"
         if report["material_findings"] else
         "**No material blockers.** Nothing blocks recording."),
        "",
    ]
    for f in report["findings"]:
        if f["material"]:
            lb_tag = " · LOAD-BEARING" if f.get("load_bearing") else ""
            lines.append(f"- **{f['verdict']}{lb_tag}** — {f['claim']}\n  - script: “{f['script_line'][:140]}”\n"
                         f"  - evidence: {f['url']} — “{f['quote'][:200]}”\n  - {f['notes']}")
    minor = [f for f in report["findings"] if not f["material"] and f["verdict"] != "SUPPORTED"]
    if minor:
        lines.append(f"\n<details><summary>{len(minor)} advisory unconfirmed (minor claims — not homework, no ruling needed)</summary>\n")
        lines += [f"- {f['claim'][:120]} — {f['verdict']}" for f in minor]
        lines.append("</details>")
    lines.append("\nThe checker never edits the script. Rulings are Maz's.")
    return "\n".join(lines) + "\n"
