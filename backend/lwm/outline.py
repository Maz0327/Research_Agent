"""The DENSE OUTLINE — the patch's core restoration (§5).

The historical finding this exists for: **thin research → thin outline →
generic/invented/trash script.** Repeated writer retries on Freemasons were
usually UPSTREAM information failures being misdiagnosed as writing failures.
The anti-seven-drafts method was:

    fact-check Brief → find THIN sections → targeted backfill →
    coverage-mapped outline → adversarial outline check → lock → draft

So this module builds an outline that is dense in FACTS and STORY DECISIONS —
not polished prose — and classifies every movement's coverage:

- **SOLID** — proceed.
- **PRECISION-RISK** — proceed with exact certainty constraints.
- **THIN** — do NOT send to the writer; backfill exactly the missing material.

`code decides, a model advises, a model never gates`: the model proposes a
classification and code re-derives one from the registry rows the movement
actually resolves. The STRICTER of the two wins, always.

Outline prose must never contain liftable narration — that leaked into drafts
in the pilot — so the same check the architecture pass uses runs here too.
"""

import json
import re
from pathlib import Path
from typing import Any

from backend.lwm import ledger, registry

STAGE = "5 outline"

COVERAGE = ("SOLID", "PRECISION-RISK", "THIN")
_SEVERITY = {"SOLID": 0, "PRECISION-RISK": 1, "THIN": 2}

# A movement resting on fewer than this many resolved registry rows has not
# got enough material behind it to be told, whatever a model thinks.
MIN_ROWS_SOLID = 4
MIN_ROWS_ANY = 2

_MOVEMENT = {
    "type": "object",
    "properties": {
        "n": {"type": "integer"},
        "story_job": {"type": "string"},
        "audience_state_entering": {"type": "string"},
        "what_changes": {"type": "string"},
        "events": {"type": "array", "items": {"type": "string"}},
        "names": {"type": "array", "items": {"type": "string"}},
        "dates": {"type": "array", "items": {"type": "string"}},
        "actions": {"type": "array", "items": {"type": "string"}},
        "documents": {"type": "array", "items": {"type": "string"}},
        "numbers": {"type": "array", "items": {"type": "string"}},
        "quotes": {"type": "array", "items": {"type": "string"}},
        "registry_claim_ids": {"type": "array", "items": {"type": "integer"}},
        "brief_references": {"type": "array", "items": {"type": "string"}},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "setup_payoff_reveal": {"type": "string"},
        "forward_pull": {"type": "string"},
        "coverage": {"type": "string", "enum": list(COVERAGE)},
        "coverage_reason": {"type": "string"},
        "missing_material": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["n", "story_job", "events", "registry_claim_ids", "coverage"],
}

_SCHEMA = {"type": "object",
           "properties": {"movements": {"type": "array", "items": _MOVEMENT}},
           "required": ["movements"]}

_ROLE = """You build the DENSE OUTLINE for a documentary video. Dense in FACTS and STORY
DECISIONS — never in prose. Do not write a single sentence a drafter could lift; write what
happens and what it does, in working language.

The architecture is already decided and is law: keep its movements, its shape, its order.

For every movement, carry the actual material: the events in order, the names, the dates, the
actions, the documents, the numbers, quotes only where a quote is genuinely usable, the registry
row numbers each claim comes from, and the contradictions or uncertainty that live there. A
movement whose events you cannot tie to registry rows is a movement with no evidence behind it —
say so rather than filling it with plausible-sounding material. INVENTING CONNECTIVE FACTS IS THE
WORST THING YOU CAN DO HERE.

Then classify the movement's coverage honestly:
- SOLID — the material is there, specific and sourced.
- PRECISION-RISK — tellable, but something in it demands exact wording: a contested claim, a
  number that must not drift, an attribution that must survive.
- THIN — the material is not there. Name exactly what is missing in missing_material. Being
  honest here is the whole point of the field; a THIN movement gets researched, not written.

Never mark something SOLID to be agreeable. A wrong SOLID sends a writer to invent."""

_LIFTABLE = re.compile(r"[“\"]([^”\"]{80,})[”\"]")


def _resolved_rows(movement: dict, rows_by_n: dict[int, dict]) -> list[dict]:
    out = []
    for n in movement.get("registry_claim_ids") or []:
        row = rows_by_n.get(int(n)) if str(n).isdigit() or isinstance(n, int) else None
        if row:
            out.append(row)
    return out


def code_coverage(movement: dict, rows_by_n: dict[int, dict]) -> tuple[str, str]:
    """Coverage as the registry itself implies it. Code decides."""
    resolved = _resolved_rows(movement, rows_by_n)
    cited = len(movement.get("registry_claim_ids") or [])
    unresolved = cited - len(resolved)
    if len(resolved) < MIN_ROWS_ANY:
        return "THIN", (f"only {len(resolved)} registry row(s) resolve for this movement"
                        + (f" ({unresolved} cited row(s) do not exist)" if unresolved else ""))
    risky = [r for r in resolved if r["status"] in ("MISSING-SOURCE", "CONTESTED")]
    no_wording = [r for r in resolved if r["status"] != "REPORTED" and r["allowed"] in ("", "—")]
    if len(resolved) < MIN_ROWS_SOLID:
        return "THIN", f"{len(resolved)} resolved registry row(s) — below the floor for a movement"
    if unresolved:
        return "PRECISION-RISK", f"{unresolved} cited registry row(s) do not exist in the registry"
    if risky:
        return "PRECISION-RISK", ("rests on " + ", ".join(
            f"row {r['n']} ({r['status']})" for r in risky[:4])
            + " — certainty wording is load-bearing here")
    if no_wording:
        return "PRECISION-RISK", (f"{len(no_wording)} row(s) carry no allowed wording; "
                                  "the drafter has nothing to constrain certainty")
    return "SOLID", f"{len(resolved)} sourced registry rows, none contested or unsourced"


def stricter(a: str, b: str) -> str:
    return a if _SEVERITY.get(a, 2) >= _SEVERITY.get(b, 2) else b


def build(episode: Path, client: Any = None) -> dict:
    """The dense, coverage-classified outline. Advisory model, deciding code."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("writer")

    arch_path = episode / "outputs" / "story-architecture.json"
    if not arch_path.exists():
        raise RuntimeError("the outline is built from the story architecture; none exists")
    arch = json.loads(arch_path.read_text())
    rows = registry.read_table(episode)
    rows_by_n = {int(r["n"]): r for r in rows}

    from backend.lwm import angle as _angle
    pack = _angle.evidence_pack(episode)

    prompt = "\n".join([
        "THE STORY ARCHITECTURE — LAW",
        json.dumps({k: arch[k] for k in (
            "macro_shape", "why_this_shape", "audience_belief_entering",
            "what_changes_that_belief", "information_order_rationale", "movements",
            "legitimate_withholding", "human_stakes", "ending", "unresolved_uncertainty",
            "compressed_vs_full_scene")}, ensure_ascii=False, indent=1),
        "",
        f"THE REGISTRY — {len(rows)} rows. Cite by row number. Allowed and prohibited wording "
        "travel with the fact, always.",
        *[f"| {r['n']} | {r['claim']} | {r['class']} | {r['status']} | src {r['source']} | "
          f"LB {r['lb']} | say: {r['allowed']} | never: {r['prohibited']} | anchor: {r['anchor']} |"
          for r in rows],
        "",
        "THE RESEARCH RECORD — key points",
        *[f"- [{k['id']}] {k['statement']}" for k in pack["key_points"]],
        "",
        "DISAGREEMENTS",
        *[f"- {t['description']}" for t in pack["tensions"]],
        *[f"- {d['claim']} — {d['holders']}" for d in pack["disputes"]],
        "",
        "WHAT THE RESEARCH COULD NOT ESTABLISH",
        *[f"- {g}" for g in pack["gaps"]],
    ])
    data, _ = client.generate_structured(prompt=prompt, schema=_SCHEMA, system=_ROLE,
                                         max_tokens=20000)

    movements = []
    for m in data.get("movements") or []:
        model_cov = m.get("coverage") if m.get("coverage") in COVERAGE else "THIN"
        code_cov, why = code_coverage(m, rows_by_n)
        final = stricter(model_cov, code_cov)
        resolved = _resolved_rows(m, rows_by_n)
        m["coverage_model"] = model_cov
        m["coverage_code"] = code_cov
        m["coverage_code_reason"] = why
        m["coverage"] = final
        m["resolved_rows"] = [int(r["n"]) for r in resolved]
        m["allowed_wording"] = [{"row": int(r["n"]), "say": r["allowed"], "never": r["prohibited"]}
                                for r in resolved if r["allowed"] not in ("", "—")
                                or r["prohibited"] not in ("", "—")]
        if final == "THIN" and not (m.get("missing_material") or []):
            m["missing_material"] = [f"material behind: {m.get('story_job', 'this movement')}"
                                     f" — {why}"]
        movements.append(m)

    liftable = [q.group(1)[:120] for q in _LIFTABLE.finditer(json.dumps(movements, ensure_ascii=False))
                if len(q.group(1).split()) >= 12]

    out = {
        "episode": episode.name,
        "macro_shape": arch.get("macro_shape", ""),
        "movements": movements,
        "coverage_summary": {c: sum(1 for m in movements if m["coverage"] == c) for c in COVERAGE},
        "thin_movements": [m["n"] for m in movements if m["coverage"] == "THIN"],
        "liftable_prose": liftable,
        "registry_rows": len(rows),
    }
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "outline.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    text = render(out)
    (episode / "05-outline.md").write_text(text)
    (episode / "outputs" / "outline.txt").write_text(text)

    cov = out["coverage_summary"]
    ledger.update_row(episode, STAGE,
                      status="done" if not out["thin_movements"] else "done (THIN movements held)",
                      gate=f"coverage: {cov['SOLID']} SOLID · {cov['PRECISION-RISK']} "
                           f"PRECISION-RISK · {cov['THIN']} THIN",
                      notes=("dense outline; every movement sourced to registry rows"
                             if not out["thin_movements"] else
                             f"movements {out['thin_movements']} are THIN — targeted backfill "
                             "before any of them reaches the writer"))
    return out


def render(o: dict) -> str:
    cov = o["coverage_summary"]
    out = ["<!--\nartifact:  05-outline\nversion:   v2 (dense outline, Packer readiness patch §5)\n"
           "upstream:  04c-story-architecture · 04-sources-registry · 04b-briefing\n"
           f"readiness: {cov['SOLID']} SOLID · {cov['PRECISION-RISK']} PRECISION-RISK · "
           f"{cov['THIN']} THIN\n-->\n",
           "# Dense outline\n",
           f"Macro shape: **{o['macro_shape']}** · {o['registry_rows']} registry rows available\n",
           "Dense in facts and story decisions — never prose. A THIN movement does not reach the "
           "writer until targeted backfill fills exactly what is missing.\n"]
    for m in o["movements"]:
        badge = {"SOLID": "✅ SOLID", "PRECISION-RISK": "⚠️ PRECISION-RISK", "THIN": "⛔ THIN"}[m["coverage"]]
        out.append(f"## Movement {m.get('n')} — {m.get('story_job', '')}   [{badge}]\n")
        out.append(f"- **coverage:** {m['coverage']} (model said {m['coverage_model']}, "
                   f"code said {m['coverage_code']}: {m['coverage_code_reason']})")
        for label, key in [("Audience entering", "audience_state_entering"),
                           ("What changes", "what_changes"),
                           ("Setup / payoff / reveal", "setup_payoff_reveal"),
                           ("Forward pull", "forward_pull")]:
            if m.get(key):
                out.append(f"- **{label}:** {m[key]}")
        for label, key in [("Events", "events"), ("Names", "names"), ("Dates", "dates"),
                           ("Actions", "actions"), ("Documents", "documents"),
                           ("Numbers", "numbers"), ("Quotes usable", "quotes"),
                           ("Brief references", "brief_references"),
                           ("Contradictions / uncertainty", "contradictions")]:
            if m.get(key):
                out.append(f"- **{label}:**")
                out += [f"  - {i}" for i in m[key]]
        out.append(f"- **Registry rows:** {', '.join(str(n) for n in m.get('resolved_rows') or []) or '—'}")
        if m.get("allowed_wording"):
            out.append("- **Wording that travels with the facts:**")
            out += [f"  - row {w['row']} — say: {w['say'] or '—'} · never: {w['never'] or '—'}"
                    for w in m["allowed_wording"]]
        if m["coverage"] == "THIN":
            out.append("- **Missing material (backfill target):**")
            out += [f"  - {i}" for i in m.get("missing_material") or []]
        out.append("")
    if o["liftable_prose"]:
        out += ["> ⚠️ Liftable prose found in this outline. Outlines describe; they do not "
                "supply lines. Treat these as accidents:",
                *[f"> - “{q}…”" for q in o["liftable_prose"]], ""]
    return "\n".join(out)


_ADVERSARIAL_ROLE = """You are the adversarial check on an outline, before anyone writes a word.
Refute-first. Find, specifically: movements whose events are not actually supported by the registry
rows they cite · claims that would require the writer to invent connective tissue · places where
certainty would drift past the allowed wording · a movement that has a job but no material ·
material that is in the research and is being wasted. Give findings, not praise. No findings is a
valid answer only when you genuinely cannot find one."""

_ADVERSARIAL_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {"type": "object", "properties": {
        "movement": {"type": "integer"}, "problem": {"type": "string"},
        "severity": {"type": "string", "enum": ["blocking", "worth fixing", "note"]},
        "fix_upstream": {"type": "string"}}, "required": ["movement", "problem", "severity"]}}},
    "required": ["findings"],
}


def adversarial_check(episode: Path, client: Any = None) -> dict:
    """The pre-draft adversarial outline check. Advisory; recorded, never a gate."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")
    path = episode / "outputs" / "outline.json"
    if not path.exists():
        raise RuntimeError("no outline to check")
    o = json.loads(path.read_text())
    rows = registry.read_table(episode)
    prompt = "\n".join([
        "THE OUTLINE", json.dumps(o["movements"], ensure_ascii=False, indent=1), "",
        "THE REGISTRY IT CITES",
        *[f"| {r['n']} | {r['claim']} | {r['status']} | say: {r['allowed']} | never: {r['prohibited']} |"
          for r in rows],
    ])
    data, _ = client.generate_structured(prompt=prompt, schema=_ADVERSARIAL_SCHEMA,
                                         system=_ADVERSARIAL_ROLE, max_tokens=6000)
    findings = data.get("findings") or []
    o["adversarial_findings"] = findings
    path.write_text(json.dumps(o, indent=1, ensure_ascii=False))
    (episode / "05b-outline-check.md").write_text(
        "<!--\nartifact:  05b-outline-check\nversion:   v1\n-->\n\n"
        "# Adversarial outline check\n\n"
        + ("\n".join(f"- **M{f['movement']} · {f['severity']}** — {f['problem']}"
                     + (f"\n  - fix upstream: {f['fix_upstream']}" if f.get("fix_upstream") else "")
                     for f in findings) or "- no findings")
        + "\n")
    return {"findings": findings,
            "blocking": [f for f in findings if f.get("severity") == "blocking"]}
