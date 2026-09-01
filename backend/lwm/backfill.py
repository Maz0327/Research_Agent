"""TARGETED BACKFILL (§7) — fill exactly what a THIN movement is missing.

**Never a full Research Agent rerun.** The whole job is expensive, it churns
every downstream artifact, and it is not what a thin movement needs: it needs
the specific missing material. So this uses the existing grounded search to
find sources for exactly the named gaps, extracts only the facts that answer
them, and APPENDS those as new registry rows carrying full provenance.

Appended rows are marked so nobody mistakes backfilled evidence for evidence
that came through the full research pipeline. The movement is then reclassified
against the enlarged registry — and if it is still THIN, it stays out of the
writer's hands and says why.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

from loguru import logger

from backend.lwm import registry

MAX_SOURCES_PER_BACKFILL = 4
BACKFILL_STATUS = "REPORTED"

_SCHEMA = {
    "type": "object",
    "properties": {"facts": {"type": "array", "items": {"type": "object", "properties": {
        "claim": {"type": "string"},
        "answers": {"type": "string"},
        "allowed": {"type": "string"},
        "prohibited": {"type": "string"},
        "quote": {"type": "string"},
    }, "required": ["claim", "answers", "allowed"]}}},
    "required": ["facts"],
}

_ROLE = """You are filling ONE specific hole in the research. You are given exactly what is
missing and the text of a source that may answer it.

Extract ONLY facts that answer the named missing material. A fact that is interesting but does not
answer the question is not wanted here — this is not a second research round.

For each fact give: the claim as the source supports it · which missing item it answers · the
allowed wording (certainty-controlled: what a narrator may safely say) · the prohibited wording
(the overstatement to avoid) · a short verbatim quote from the source if one carries it.

If the source does not answer the missing material, return no facts. Returning nothing is correct
and useful. Never stretch a source to cover a hole it does not cover."""


def run(episode: Path, movement: int, missing: list[str], client: Any = None,
        search=None, fetch=None) -> dict:
    """Backfill one movement's named gaps. Appends rows; reruns nothing."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")
    if search is None:
        from backend.pipeline.runs.search import grounded_search as search
    if fetch is None:
        from backend.pipeline.content_extraction import extract_content as fetch

    doc_0_path = episode / "research" / "doc_0.json"
    doc_0 = {}
    if doc_0_path.exists():
        payload = json.loads(doc_0_path.read_text())
        doc_0 = payload.get("data", payload)
    existing_urls = {s.get("url", "") for s in doc_0.get("sources", []) if s.get("url")}

    prompt = ("Find sources that answer exactly these missing pieces:\n"
              + "\n".join(f"- {m}" for m in missing))
    try:
        candidates = search(doc_0, prompt, existing_urls=existing_urls,
                            max_results=MAX_SOURCES_PER_BACKFILL) or []
    except Exception as e:
        logger.error(f"backfill search failed for movement {movement}: {e}")
        candidates = []

    found: list[dict] = []
    consulted: list[dict] = []
    for c in candidates[:MAX_SOURCES_PER_BACKFILL]:
        url = c.get("url")
        if not url:
            continue
        try:
            text = fetch(url) or ""
        except Exception as e:
            consulted.append({"url": url, "outcome": f"could not fetch: {e}"})
            continue
        if not text.strip():
            consulted.append({"url": url, "outcome": "no extractable content"})
            continue
        try:
            data, _ = client.generate_structured(
                prompt=("MISSING MATERIAL\n" + "\n".join(f"- {m}" for m in missing)
                        + f"\n\nSOURCE: {c.get('title') or url}\nURL: {url}\n\n{text}"),
                schema=_SCHEMA, system=_ROLE, max_tokens=6000)
        except Exception as e:
            consulted.append({"url": url, "outcome": f"extraction failed: {e}"})
            continue
        facts = data.get("facts") or []
        consulted.append({"url": url, "title": c.get("title"), "outcome": f"{len(facts)} fact(s)"})
        for f in facts:
            f["url"] = url
            f["source_title"] = c.get("title") or url
            found.append(f)

    appended = append_rows(episode, found, movement) if found else []
    if appended:
        _attach_rows(episode, movement, appended)
    record = {
        "movement": movement, "missing": missing, "at": str(date.today()),
        "sources_consulted": consulted, "facts_found": len(found),
        "registry_rows_appended": appended,
        "full_ra_job_rerun": False,
    }
    d = episode / "research" / "backfill"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"movement-{movement}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    return record


def append_rows(episode: Path, facts: list[dict], movement: int) -> list[int]:
    """Append backfilled facts to the registry table, provenance intact.

    The existing table is never regenerated — regeneration would discard the
    judgment pass that already ran over it. Rows are appended with a source
    that names the URL, so a reader can always see which evidence arrived
    through backfill rather than through the research job.
    """
    p = episode / "04-sources-registry.md"
    if not p.exists():
        raise RuntimeError("no registry to append to")
    existing = registry.read_table(episode)
    next_n = max((int(r["n"]) for r in existing), default=0) + 1
    claims = {r["claim"].strip().lower() for r in existing}

    lines, added = [], []
    for f in facts:
        claim = (f.get("claim") or "").strip()
        if not claim or claim.lower() in claims:
            continue
        claims.add(claim.lower())
        lines.append("| {n} | {claim} | THEORY | {status} | backfill M{m}: {url} | n | {allowed} | "
                     "{prohibited} | — |".format(
                         n=next_n, claim=claim.replace("|", "/"), status=BACKFILL_STATUS,
                         m=movement, url=(f.get("url") or "—").replace("|", "/"),
                         allowed=(f.get("allowed") or "—").replace("|", "/"),
                         prohibited=(f.get("prohibited") or "—").replace("|", "/")))
        added.append(next_n)
        next_n += 1

    if not lines:
        return []
    text = p.read_text()
    table_end = text.rfind("|\n")
    insert_at = text.index("\n", table_end + 1) if table_end != -1 else len(text)
    p.write_text(text[:insert_at + 1] + "\n".join(lines) + "\n" + text[insert_at + 1:])
    return added


def _attach_rows(episode: Path, movement: int, rows: list[int]) -> None:
    """The backfilled rows belong to the movement that needed them."""
    path = episode / "outputs" / "outline.json"
    if not path.exists():
        return
    o = json.loads(path.read_text())
    for m in o["movements"]:
        if int(m.get("n", 0)) == movement:
            ids = [int(n) for n in (m.get("registry_claim_ids") or [])]
            m["registry_claim_ids"] = ids + [n for n in rows if n not in ids]
            m["backfilled_rows"] = sorted(set((m.get("backfilled_rows") or []) + rows))
    path.write_text(json.dumps(o, indent=1, ensure_ascii=False))


def reclassify(episode: Path, movement: int) -> dict:
    """Re-derive one movement's coverage against the enlarged registry."""
    from backend.lwm import outline as _outline

    path = episode / "outputs" / "outline.json"
    o = json.loads(path.read_text())
    rows_by_n = {int(r["n"]): r for r in registry.read_table(episode)}
    for m in o["movements"]:
        if int(m.get("n", 0)) != movement:
            continue
        code_cov, why = _outline.code_coverage(m, rows_by_n)
        m["coverage_code"], m["coverage_code_reason"] = code_cov, why
        m["coverage"] = _outline.stricter(m.get("coverage_model", "THIN"), code_cov)
        m["resolved_rows"] = [int(n) for n in (m.get("registry_claim_ids") or [])
                              if int(n) in rows_by_n]
        o["thin_movements"] = [x["n"] for x in o["movements"] if x["coverage"] == "THIN"]
        o["coverage_summary"] = {c: sum(1 for x in o["movements"] if x["coverage"] == c)
                                 for c in _outline.COVERAGE}
        path.write_text(json.dumps(o, indent=1, ensure_ascii=False))
        text = _outline.render(o)
        (episode / "05-outline.md").write_text(text)
        (episode / "outputs" / "outline.txt").write_text(text)
        return {"movement": movement, "coverage": m["coverage"], "reason": why}
    raise KeyError(f"movement {movement} is not in the outline")
