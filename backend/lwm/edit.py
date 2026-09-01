"""Stages 8 and 9b — the constrained edit train, pairs-applied-by-code (D-24).

The doctrine this implements is the pipeline's own, not a new invention:
editors PROPOSE old→new pairs and code APPLIES them — the model never
re-emits prose (TIC-PASS.md contract). Every pair passes the entity
invariant (numbers unchanged), must match exactly once, and lands in the
edit log as a typed flag with a written disposition. The pace edit consumes
the grip map, protects held passages, and must move net length down.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from backend.lwm import paths

# The existing cap: any prose-producing pass counts; two cycles, never more.
EDIT_CYCLE_CAP = 2

_PAIRS_SCHEMA = {
    "type": "object",
    "properties": {"pairs": {"type": "array", "items": {"type": "object", "properties": {
        "old": {"type": "string"}, "new": {"type": "string"}, "why": {"type": "string"},
    }, "required": ["old", "new"]}}},
    "required": ["pairs"],
}


def _numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d[\d,.]*", text))


def apply_pairs(text: str, pairs: list[dict], kind: str,
                protected: list[str] | None = None,
                allowed_numbers: set[str] | None = None) -> tuple[str, list[dict]]:
    """Apply editor pairs under the invariants; return (text, dispositions).

    A pair is REJECTED (never partially applied) when: its `old` is not found,
    is not unique, changes a number (entity invariant — unless the number is
    one `allowed_numbers` carries, i.e. Maz's own correction named it, which
    is the factual-correction path), or touches a protected passage. Rejections are dispositions, not errors — the edit log
    records why, and the prose stands.
    """
    dispositions = []
    for pair in pairs:
        old, new = pair.get("old", ""), pair.get("new", "")
        why = pair.get("why", "")
        if not old:
            continue
        count = text.count(old)
        number_change_ok = _numbers(old) == _numbers(new) or (
            allowed_numbers is not None
            and set(_numbers(new)) <= set(_numbers(old)) | allowed_numbers
        )
        if count == 0:
            verdict = "REJECTED — old text not found (editor drifted from the draft)"
        elif count > 1:
            verdict = f"REJECTED — old text matches {count} places; pairs must be unambiguous"
        elif not number_change_ok:
            verdict = "REJECTED — entity invariant: a pair may not change numbers the correction did not name"
        elif any(p and old in p for p in (protected or [])):
            verdict = "REJECTED — touches a held passage (grip map protection)"
        else:
            text = text.replace(old, new, 1)
            verdict = "APPLIED"
        dispositions.append({"kind": kind, "old": old, "new": new, "why": why,
                             "disposition": verdict})
    return text, dispositions


def _propose(client: Any, system: str, prompt: str) -> list[dict]:
    data, _ = client.generate_structured(prompt=prompt, schema=_PAIRS_SCHEMA,
                                         system=system, max_tokens=8000)
    return data.get("pairs") or []


_DELTA_ROLE = """You are the delta scan. Compare the draft against the registry: wherever the
draft states a claim with MORE certainty than its row's allowed wording, uses prohibited wording,
or voices a comparison that is not the row's anchor, propose the smallest old→new pair that
restores the registry's wording. Old must be copied VERBATIM from the draft, long enough to be
unique. Never touch anything else; smallest diffs win. No pairs is a fine answer."""

_TIC_ROLE = """You are the register pass (TIC). Find constructed-elegance tics: antithesis
("not X — Y"), buildup-then-one-word-deflation, epigram closers, announced withholds, anything a
mouth wouldn't say at pace. Propose the smallest old→new pairs that make it speech. Old verbatim
from the draft, unique. Numbers must not change. No pairs is a fine answer."""

_ANTECEDENT_ROLE = """You are the antecedent sweep. Find pronouns and references whose antecedent
a listener (hearing once, at pace) could mis-assign, and propose smallest old→new pairs that pin
them. Old verbatim, unique. No pairs is a fine answer."""


_CONSTRUCTIVE_ROLE = """You are the CONSTRUCTIVE EDITOR. Reviewers and a mechanical AI-tic
detector have marked places in this script. Your job is NOT only to remove AI tells. It is to make
the script BETTER: clearer, with more narrative force, with connective tissue that actually
connects, explanations a listener follows at pace, transitions that are real, rhythm that sounds
spoken — and, yes, the identified AI residue gone.

You propose old→new pairs and nothing else. Code applies them. `old` must be copied VERBATIM from
the script and be long enough to appear exactly once. Never change a number the findings did not
name. Never touch attribution, hedges or source framing — those are load-bearing honesty, not
padding. Smallest diffs that do the job. Where a finding is wrong, propose no pair for it; a pair
you cannot make safely is one you should not make."""


def _findings_brief(reviews: dict, lint: dict) -> str:
    lines = ["REVIEWER FINDINGS"]
    for f in reviews.get("findings", []):
        if f.get("reviewer_failed"):
            continue
        lines.append(f"- [{f.get('reviewer')}·{f.get('severity')}] {f.get('problem')}")
        if f.get("quote"):
            lines.append(f"    at: \u201c{f['quote']}\u201d")
        if f.get("suggested_direction"):
            lines.append(f"    direction: {f['suggested_direction']}")
    lines.append("")
    lines.append("MECHANICAL AI-TIC FLAGS (locations only — the detector renders no verdict)")
    for f in (lint.get("flags") or []):
        lines.append(f"- L{f.get('line')} [{f.get('id')}] {f.get('name')}"
                     + (" [in a quotation — usually leave it]" if f.get("inQuote") else "")
                     + f": \u00ab{str(f.get('match', ''))[:120]}\u00bb")
    for c in (lint.get("counters") or []):
        if c.get("status") not in ("in band", "reference-only"):
            lines.append(f"- counter [{c.get('id')}] {c.get('name')}: observed {c.get('observed')} "
                         f"{c.get('unit', '')} — {c.get('status')}")
    return "\n".join(lines)


def edit_train(episode: Path, client: Any, reviewer_client: Any = None) -> dict:
    """Stage 8: review → lint → constructive edit → mechanical passes, capped.

    Order matters and it is the patch's order: the draft was written FREE, so
    the rule walls arrive now. The three reviewers and the AI-tic detector run
    first and their findings — whole, structured, not a truncated stdout tail —
    become the constructive editor's brief. Then the existing mechanical passes
    (delta scan against the registry, register/TIC, antecedent) run as before.

    THE TWO-CYCLE TRIPWIRE (§14): at most two substantial prose-producing
    correction cycles. If the script is still materially broken after that, we
    STOP WRITING and say which upstream stage owns it. Draft 7 / Draft 8 /
    Draft 9 is the behaviour this cap exists to prevent.
    """
    from backend.lwm import review as _review

    draft_path = episode / "07-draft.md"
    text = draft_path.read_text()
    registry_md = (episode / "04-sources-registry.md")
    registry_text = registry_md.read_text() if registry_md.exists() else ""
    log: list[dict] = []
    cycles = 0
    changed = False
    reviews: dict = {"by_reviewer": {}, "findings": [], "counts": {}, "material": []}
    lint_out: dict = {"ran": False, "flags": [], "counters": [], "summary": {}}
    tripwire = None

    for cycle in range(EDIT_CYCLE_CAP):
        cycles = cycle + 1
        before = text
        draft_path.write_text(text)

        reviews = _review.run(episode, client=reviewer_client or client)
        lint_out = run_lint(draft_path)

        pairs = _propose(client, _CONSTRUCTIVE_ROLE,
                         f"{_findings_brief(reviews, lint_out)}\n\nTHE SCRIPT\n{text}")
        text, d = apply_pairs(text, pairs, "constructive")
        log += d

        # The registry travels WHOLE to the delta scan: a claim whose allowed
        # wording fell off the end of a truncated registry is exactly the
        # drift this pass exists to catch.
        pairs = _propose(client, _DELTA_ROLE, f"REGISTRY\n{registry_text}\n\nDRAFT\n{text}")
        text, d = apply_pairs(text, pairs, "delta")
        log += d
        pairs = _propose(client, _TIC_ROLE, text)
        text, d = apply_pairs(text, pairs, "tic")
        log += d
        pairs = _propose(client, _ANTECEDENT_ROLE, text)
        text, d = apply_pairs(text, pairs, "antecedent")
        log += d
        changed = text != before
        if not changed:
            break  # clean cycle — the cap exists for the other case

    draft_path.write_text(text)

    # Is it STILL materially broken? The tripwire is not about exhausting the
    # cap; it is about the finding that more prose passes cannot fix this. If
    # the last cycle changed nothing, the reviews we already have are current;
    # if it did change the prose, we look again before concluding anything.
    if changed:
        reviews = _review.run(episode, client=reviewer_client or client)
    material = reviews.get("material") or []
    if material:
        tripwire = diagnose_upstream(episode, material, cycles)

    _write_edit_log(episode, log, cycles, lint_out, reviews, tripwire)
    (episode / "08-review-findings.md").write_text(_review.render(reviews, lint_out))
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "lint-findings.json").write_text(
        json.dumps(lint_out, indent=1, ensure_ascii=False))

    return {"cycles": cycles,
            "applied": sum(1 for e in log if e["disposition"] == "APPLIED"),
            "rejected": sum(1 for e in log if e["disposition"] != "APPLIED"),
            "review_counts": reviews.get("counts", {}),
            "lint_flags": (lint_out.get("summary") or {}).get("flagCount", 0),
            "lint_counters_outside_band": (lint_out.get("summary") or {}).get("countersOutsideBand", 0),
            "tripwire": tripwire}


# Where a material problem that survived two edit cycles actually lives. The
# point of the tripwire is that more prose passes cannot fix any of these.
_UPSTREAM = [
    ("fact-integrity", "research / registry",
     "the material behind these claims is wrong, missing or was never sourced — "
     "targeted backfill, not another edit pass"),
    ("story-thread", "angle · story architecture · outline",
     "the story being told is not landing — that is a structure decision, not a sentence problem"),
    ("semantic-register", "writer cargo / draft packet",
     "the drafter was handed something that made it write this way — fix the packet, redraft"),
]


def diagnose_upstream(episode: Path, material: list[dict], cycles: int = EDIT_CYCLE_CAP) -> dict:
    """The tripwire's output: STOP WRITING, and name what owns the problem."""
    by_reviewer: dict[str, int] = {}
    for f in material:
        by_reviewer[f.get("reviewer", "?")] = by_reviewer.get(f.get("reviewer", "?"), 0) + 1
    routes = [{"reviewer": r, "owner": owner, "why": why, "findings": by_reviewer[r]}
              for r, owner, why in _UPSTREAM if by_reviewer.get(r)]
    diagnosis = {
        "stop_writing": True,
        "cycles_used": cycles,
        "material_findings": len(material),
        "by_reviewer": by_reviewer,
        "routes": routes,
        "rule": ("Two substantial correction cycles are the cap. A third prose pass is the "
                 "Draft 7 / Draft 8 / Draft 9 spiral; the defect is upstream."),
    }
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "tripwire.json").write_text(
        json.dumps(diagnosis, indent=1, ensure_ascii=False))
    return diagnosis


_PACE_ROLE = """You are the pace edit — serial, whole-script, one pass. The grip map tells you
where readers were held and where they drifted. Compress or cut coasting tissue in the drifting
stretches: propose old→new pairs where new is shorter (new may be empty = a clean cut). NEVER
touch the held passages. NEVER cut attribution or integrity hedges ("Packer said", "the analysis
suggested") — they are load-bearing honesty, not tissue. Additions only where a cut breaks a
join, and then minimal. Old verbatim, unique. Net length must come down."""


def pace_edit(episode: Path, client: Any) -> dict:
    """Stage 9b: consume the grip map, protect held passages, net length down."""
    draft_path = episode / "07-draft.md"
    text = draft_path.read_text()
    grip_map_path = episode / "09-grip-gate-b.md"
    grip_map = grip_map_path.read_text() if grip_map_path.exists() else ""
    held = re.findall(r"held: “([^”]+)”", grip_map)

    # The grip map travels whole: the held passages are the protect-list, and a
    # protect-list cut off at a character count protects the wrong things.
    pairs = _propose(client, _PACE_ROLE, f"GRIP MAP\n{grip_map}\n\nSCRIPT\n{text}")
    new_text, dispositions = apply_pairs(text, pairs, "pace", protected=held)

    before_words, after_words = len(text.split()), len(new_text.split())
    if after_words >= before_words and any(d["disposition"] == "APPLIED" for d in dispositions):
        # A pace edit that grows the script is not a pace edit. Keep the prose.
        result = {"applied": 0, "note": "pass rejected: net length did not come down",
                  "words": f"{before_words} → {before_words}"}
        new_text = text
    else:
        result = {"applied": sum(1 for d in dispositions if d["disposition"] == "APPLIED"),
                  "words": f"{before_words} → {after_words}"}
    draft_path.write_text(new_text)
    (episode / "09b-pace-edit.md").write_text(
        "<!--\nartifact:  09b-pace-edit\nversion:   v1\n-->\n\n# Pace edit\n\n"
        f"words before → after: {result['words']}\n\n"
        + "\n".join(f"- [{d['kind']}] {d['disposition']}: “{d['old'][:70]}…”" for d in dispositions)
        + "\n")
    return result


def run_lint(draft_path: Path) -> dict:
    """The tier-1 AI-tic / regression detector, structured and whole (§12).

    The detector is NOT rebuilt, NOT replaced and NOT modified — it is a large
    researched bank of AI tells and it flags only. What changes here is that
    its findings survive: it is asked for `--json` and the parsed result is
    kept, instead of a 200/2000-character tail of stdout that discarded most of
    what it found.
    """
    mjs = paths.pipeline_dir() / "lint" / "regression-tier1.mjs"
    if not draft_path.exists():
        return {"ran": False, "reason": "no draft to lint", "flags": [], "counters": [],
                "summary": {"flagCount": 0, "countersOutsideBand": 0}}
    if not mjs.exists():
        return {"ran": False, "reason": "lint unavailable (no regression-tier1.mjs in workspace)",
                "flags": [], "counters": [], "summary": {"flagCount": 0, "countersOutsideBand": 0}}
    try:
        proc = subprocess.run(["node", str(mjs), str(draft_path), "--json"],
                              capture_output=True, text=True, timeout=180)
        data = json.loads(proc.stdout)
        data["ran"] = True
        return data
    except Exception as e:  # lint is advisory; its absence is a note, not a failure
        logger.warning(f"lint did not run on {draft_path.name}: {e}")
        return {"ran": False, "reason": f"lint failed to run: {e}", "flags": [], "counters": [],
                "summary": {"flagCount": 0, "countersOutsideBand": 0}}


def _write_edit_log(episode: Path, log: list[dict], cycles: int, lint_out: dict,
                    reviews: dict, tripwire: dict | None = None) -> None:
    s = lint_out.get("summary") or {}
    lines = [
        "<!--\nartifact:  08-edit-log\nversion:   v2 (review + constructive edit train)\n-->\n",
        f"# Edit log\n\ncycles used: {cycles} (cap {EDIT_CYCLE_CAP})\n",
        "Reviewer findings: "
        + (" · ".join(f"{k} {v}" for k, v in (reviews.get("counts") or {}).items()) or "—"),
        f"Lint: {s.get('flagCount', 0)} shape flags · "
        f"{s.get('countersOutsideBand', 0)} counters outside band"
        + ("" if lint_out.get("ran") else f" (did not run: {lint_out.get('reason', '?')})"),
        "\nFull findings: `08-review-findings.md` · `outputs/review-findings.json` · "
        "`outputs/lint-findings.json`\n",
    ]
    for e in log:
        lines.append(f"- **[{e['kind']}]** {e['disposition']}")
        lines.append(f"  - old: \u201c{e['old'][:110]}\u201d")
        if e["disposition"] == "APPLIED":
            lines.append(f"  - new: \u201c{e['new'][:110]}\u201d")
        if e.get("why"):
            lines.append(f"  - why: {e['why'][:110]}")
    if tripwire:
        lines += ["\n## ⛔ TWO-CYCLE TRIPWIRE — STOP WRITING\n",
                  f"{tripwire['material_findings']} material finding(s) survived "
                  f"{tripwire['cycles_used']} correction cycles. {tripwire['rule']}\n",
                  "Upstream owners:"]
        lines += [f"- **{r['owner']}** ({r['findings']} finding(s) from {r['reviewer']}) — {r['why']}"
                  for r in tripwire["routes"]]
        lines.append("")
    (episode / "08-edit-log.md").write_text("\n".join(lines) + "\n")


_D_CORRECTION_ROLE = """You are applying the creator's ONE correction to a finished script
candidate. Propose the SMALLEST set of old→new pairs that satisfies exactly what the correction
asks — nothing else. Old must be copied VERBATIM from the candidate and long enough to be unique.
Never rewrite passages the correction does not concern; never change numbers unless the correction
itself names them. No pairs means you could not find a safe way — say so by returning none."""


def d_correction_pass(episode: Path, client: Any) -> dict:
    """Stage 10 in `corrections requested`: revise the candidate, pairs-by-code.

    Reads the newest unapplied D correction, has the locked editor seat
    propose pairs, applies them under the invariants (numbers may change only
    when the correction itself names them), records exactly what changed in
    `10-correction-pass.md`, marks the correction applied, and returns the
    stage to `candidate ready` for a fresh D approval. The editor NEVER
    re-emits the script; a pass with zero applied pairs still returns to D,
    with that fact on the record, so Maz sees it rather than a silent no-op.
    """
    import json

    from backend.lwm import ledger as _ledger

    candidate = episode / "10-final-candidate.md"
    dc_path = episode / "outputs" / "d-corrections.json"
    if not dc_path.exists():
        raise RuntimeError("stage 10 says corrections requested but outputs/d-corrections.json is missing")
    dc = json.loads(dc_path.read_text())
    pending = [c for c in dc["corrections"] if not c.get("applied")]
    if not pending:
        raise RuntimeError("corrections requested but every stored correction is already applied")
    correction = pending[-1]

    text = candidate.read_text()
    allowed = set(_numbers(correction["text"]))
    pairs = _propose(client, _D_CORRECTION_ROLE,
                     f"THE CORRECTION\n{correction['text']}\n\nCANDIDATE\n{text}")
    new_text, dispositions = apply_pairs(text, pairs, "d-correction",
                                          allowed_numbers=allowed)
    candidate.write_text(new_text)

    applied = [d for d in dispositions if d["disposition"] == "APPLIED"]
    log_path = episode / "10-correction-pass.md"
    entry = [f"\n## Correction pass — {correction['at']}",
             f"**Maz asked:** {correction['text']}", ""]
    for d in dispositions:
        entry.append(f"- [{d['disposition']}] “{d['old'][:100]}” → “{d['new'][:100]}”")
    if not dispositions:
        entry.append("- editor proposed no safe pairs — candidate unchanged; Maz sees this at D")
    log_path.write_text((log_path.read_text() if log_path.exists() else
                         "<!--\nartifact:  10-correction-pass\n-->\n# D correction passes\n")
                        + "\n".join(entry) + "\n")

    correction["applied"] = True
    correction["pairs_applied"] = len(applied)
    dc_path.write_text(json.dumps(dc, indent=1))

    rev = sum(1 for c in dc["corrections"] if c.get("applied"))
    _ledger.update_row(episode, "10 ear loop + locks", status=f"candidate ready (rev {rev + 1})",
                       notes=f"correction applied via pairs ({len(applied)} applied, "
                             f"{len(dispositions) - len(applied)} rejected) — 10-correction-pass.md; "
                             "back to touchpoint D")
    return {"applied": len(applied), "rejected": len(dispositions) - len(applied),
            "changed": new_text != text}
