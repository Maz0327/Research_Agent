"""THE REVIEW STACK (§10–11) — three reviewers, after the free draft.

They run on finished prose, never in the writer's head (§8). They FIND; they do
not rewrite. Their findings feed the Constructive Editor, which proposes pairs
that code applies.

- **FACT / INTEGRITY** — factual fidelity, names, dates, numbers, chronology,
  quote handling, attribution, certainty, hedge preservation, contradictions,
  and invented factual connective tissue. Separate from stage 10b: this checks
  the draft against the registry we already hold; 10b verifies the LOCKED
  script against the live web, and neither replaces the other.
- **STORY THREAD** — does the chosen angle survive, is the central question
  answered, is the packaging promise paid, momentum, buried ledes, detached
  facts, detours, setup/payoff, back-half weakness, the ending.
- **SEMANTIC / REGISTER** — antecedents, confusing references, semantic
  weirdness, unnatural spoken language, unintended implication, artificial
  transitions, clarity of explanation. The antecedent sweep lives HERE.

None of them ever summons Maz (§15, V1 touchpoint policy). Findings are
internal, written to the ledger and to `08-review-findings.md`.
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from backend.lwm import registry

REVIEWERS = ("fact-integrity", "story-thread", "semantic-register")

_FINDING = {
    "type": "object",
    "properties": {
        "quote": {"type": "string"},
        "problem": {"type": "string"},
        "severity": {"type": "string", "enum": ["material", "worth fixing", "note"]},
        "suggested_direction": {"type": "string"},
        "registry_row": {"type": "integer"},
    },
    "required": ["quote", "problem", "severity"],
}
_SCHEMA = {"type": "object", "properties": {"findings": {"type": "array", "items": _FINDING}},
           "required": ["findings"]}

_ROLES = {
    "fact-integrity": """You are the FACT AND INTEGRITY reviewer on a documentary draft. Refute-first.
Check the prose against the registry it was written from. Find: facts that drifted · names, dates,
numbers or chronology that do not match · quotes handled loosely or attributed to the wrong mouth ·
certainty that exceeds the row's allowed wording · prohibited wording that got used anyway · hedges
and source framing that disappeared between the registry and the prose · contradictions the draft
flattened into one version · and above all INVENTED FACTUAL CONNECTIVE TISSUE — the plausible
joining sentence that no source supports.
Quote the exact line. Name the registry row where there is one. You do not rewrite.""",

    "story-thread": """You are the STORY THREAD reviewer on a documentary draft. You are asking
whether this is still the video we decided to make. Find: places where the chosen angle stops
being the story · the central question going unanswered or unasked · the packaging promise left
unpaid · momentum dying · a buried lede (the best thing in a section arriving after the reason to
care) · facts that sit detached from the story doing no work · detours · setups with no payoff and
payoffs with no setup · back-half weakness · an ending that does not land the story it opened.
Quote the exact line. You do not rewrite.""",

    "semantic-register": """You are the SEMANTIC AND REGISTER reviewer on a documentary draft that
will be SPOKEN ALOUD ONCE, at pace, to a listener who cannot rewind. Find: pronouns and references
whose antecedent a listener could mis-assign · confusing or ambiguous reference · sentences that
mean something other than intended · language nobody says out loud · unintended implication
(including implications about real people that the evidence does not support) · transitions that
are artificial joins rather than real ones · explanations a listener could not follow at pace.
Quote the exact line. You do not rewrite.""",
}


def run(episode: Path, client: Any = None, draft_name: str = "07-draft.md") -> dict:
    """All three reviewers over the current draft. Findings only."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")

    draft_path = episode / draft_name
    text = draft_path.read_text()
    rows = registry.read_table(episode)
    registry_block = "\n".join(
        f"| {r['n']} | {r['claim']} | {r['status']} | say: {r['allowed']} | never: {r['prohibited']} |"
        for r in rows)

    angle_path = episode / "outputs" / "angle-options.json"
    chosen = json.loads(angle_path.read_text()).get("chosen") if angle_path.exists() else None
    from backend.lwm import packaging as _packaging
    promise = _packaging.promise(episode)          # the CHOSEN promise when one exists

    context = {
        "fact-integrity": f"THE REGISTRY THE DRAFT WAS WRITTEN FROM\n{registry_block}\n\n",
        "story-thread": ("THE STORY WE CHOSE\n"
                         + json.dumps(chosen or {}, ensure_ascii=False, indent=1)
                         + f"\n\nTHE PROMISE THE PACKAGING MADE: {promise or '(none recorded)'}\n\n"),
        "semantic-register": "",
    }

    out: dict[str, list[dict]] = {}
    for name in REVIEWERS:
        try:
            data, _ = client.generate_structured(prompt=context[name] + "THE DRAFT\n" + text,
                                                 schema=_SCHEMA, system=_ROLES[name],
                                                 max_tokens=8000)
            out[name] = data.get("findings") or []
        except Exception as e:
            logger.error(f"reviewer {name} failed: {e}")
            out[name] = [{"quote": "", "problem": f"reviewer did not run: {e}",
                          "severity": "note", "reviewer_failed": True}]
    for name, findings in out.items():
        for f in findings:
            f["reviewer"] = name

    all_findings = [f for fs in out.values() for f in fs]
    result = {
        "by_reviewer": out,
        "findings": all_findings,
        "counts": {n: len(out[n]) for n in REVIEWERS},
        "material": [f for f in all_findings if f.get("severity") == "material"],
        "failed_reviewers": [n for n in REVIEWERS
                             if any(f.get("reviewer_failed") for f in out[n])],
    }
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "review-findings.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False))
    return result


def render(result: dict, lint: dict | None = None) -> str:
    out = ["<!--\nartifact:  08-review-findings\nversion:   v1 (review stack, readiness patch §10-11)\n"
           "readiness: findings only — reviewers never rewrite and never summon Maz\n-->\n",
           "# Review findings\n",
           "Internal. These feed the constructive editor; none of them is homework for Maz.\n"]
    for name in REVIEWERS:
        findings = result["by_reviewer"].get(name, [])
        out.append(f"## {name} — {len(findings)} finding(s)\n")
        if not findings:
            out.append("- (none)\n")
        for f in findings:
            row = f" · registry row {f['registry_row']}" if f.get("registry_row") else ""
            out.append(f"- **{f.get('severity', 'note')}**{row} — {f.get('problem', '')}")
            if f.get("quote"):
                out.append(f"  - “{f['quote'][:180]}”")
            if f.get("suggested_direction"):
                out.append(f"  - direction: {f['suggested_direction']}")
        out.append("")
    if lint is not None:
        s = lint.get("summary") or {}
        out += [f"## AI-tic / regression lint — {s.get('flagCount', 0)} shape flags, "
                f"{s.get('countersOutsideBand', 0)} counters outside band\n",
                "Flags only. The detector renders no verdict and changes nothing.\n"]
        for f in (lint.get("flags") or [])[:200]:
            out.append(f"- L{f.get('line')} [{f.get('id')}] {f.get('name')}"
                       + (" [in-quote]" if f.get("inQuote") else ""))
            if f.get("match"):
                out.append(f"  - «{str(f['match'])[:120]}»")
        for c in (lint.get("counters") or []):
            if c.get("status") not in ("in band", "reference-only"):
                out.append(f"- ! [{c.get('id')}] {c.get('name')}: observed {c.get('observed')} "
                           f"{c.get('unit', '')} — {c.get('status')}")
        out.append("")
    return "\n".join(out)
