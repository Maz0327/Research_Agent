"""Stages 8 and 9b — the constrained edit train, pairs-applied-by-code (D-24).

The doctrine this implements is the pipeline's own, not a new invention:
editors PROPOSE old→new pairs and code APPLIES them — the model never
re-emits prose (TIC-PASS.md contract). Every pair passes the entity
invariant (numbers unchanged), must match exactly once, and lands in the
edit log as a typed flag with a written disposition. The pace edit consumes
the grip map, protects held passages, and must move net length down.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

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


def edit_train(episode: Path, client: Any) -> dict:
    """Stage 8: delta scan → TIC ×2 → antecedent sweep → lint, capped, logged."""
    draft_path = episode / "07-draft.md"
    text = draft_path.read_text()
    registry = (episode / "04-sources-registry.md").read_text() if (episode / "04-sources-registry.md").exists() else ""
    log: list[dict] = []
    cycles = 0

    for cycle in range(EDIT_CYCLE_CAP):
        cycles = cycle + 1
        before = text
        pairs = _propose(client, _DELTA_ROLE, f"REGISTRY\n{registry[:20000]}\n\nDRAFT\n{text}")
        text, d = apply_pairs(text, pairs, "delta")
        log += d
        pairs = _propose(client, _TIC_ROLE, text)
        text, d = apply_pairs(text, pairs, "tic")
        log += d
        pairs = _propose(client, _ANTECEDENT_ROLE, text)
        text, d = apply_pairs(text, pairs, "antecedent")
        log += d
        if text == before:
            break  # clean cycle — the cap exists for the other case

    draft_path.write_text(text)
    lint_out = run_lint(draft_path)
    _write_edit_log(episode, log, cycles, lint_out)
    return {"cycles": cycles, "applied": sum(1 for e in log if e["disposition"] == "APPLIED"),
            "rejected": sum(1 for e in log if e["disposition"] != "APPLIED"),
            "lint": lint_out[:200]}


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

    pairs = _propose(client, _PACE_ROLE, f"GRIP MAP\n{grip_map[:6000]}\n\nSCRIPT\n{text}")
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


def run_lint(draft_path: Path) -> str:
    mjs = paths.pipeline_dir() / "lint" / "regression-tier1.mjs"
    if not mjs.exists():
        return "lint unavailable (no regression-tier1.mjs in workspace)"
    try:
        proc = subprocess.run(["node", str(mjs), str(draft_path)],
                              capture_output=True, text=True, timeout=120)
        return (proc.stdout or proc.stderr)[-2000:]
    except Exception as e:  # lint is advisory; its absence is a note, not a failure
        return f"lint failed to run: {e}"


def _write_edit_log(episode: Path, log: list[dict], cycles: int, lint_out: str) -> None:
    lines = [
        "<!--\nartifact:  08-edit-log\nversion:   v1 (lwm edit train)\n-->\n",
        f"# Edit log\n\ncycles used: {cycles} (cap {EDIT_CYCLE_CAP})\n",
    ]
    for e in log:
        lines.append(f"- **[{e['kind']}]** {e['disposition']}")
        lines.append(f"  - old: “{e['old'][:110]}”")
        if e["disposition"] == "APPLIED":
            lines.append(f"  - new: “{e['new'][:110]}”")
        if e.get("why"):
            lines.append(f"  - why: {e['why'][:110]}")
    lines.append(f"\n## Lint (advisory)\n```\n{lint_out}\n```")
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
