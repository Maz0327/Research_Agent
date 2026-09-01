"""The ANGLE stage (D-V1-7) — name the story already being told, then offer
genuinely different ones.

Runs AFTER research and the Brief (D-V1-6). It produces the material for one
creative decision and then stops: **no agent chooses an angle for Maz.**

Three disciplines are enforced by code, not by asking a model nicely:

1. **Naming.** What the sources agree on is "the baseline of what our sources
   tell". It is only called anything stronger when the sources were actually
   supplied by the creator, and never "the mainstream story" — that would
   assert broader external research nobody performed.
2. **Story level, not detail level.** Three alternatives that are the same
   story with forensic / trial / parole emphasis are ONE story. The distinctness
   check below compares central story AND driving question; an alternative that
   fails is regenerated once and, if it fails again, is labelled as what it is
   rather than passed off as different.
3. **Novelty is not better.** `baseline_is_strongest` is a first-class outcome.
   If the familiar story is the strongest story, the artifact says so.

Context is selected structurally — key points, tensions, gaps, disputes, source
summaries — never by slicing the first N characters off a document (§6).
"""

import json
import re
from pathlib import Path
from typing import Any

from backend.lwm import ledger

STAGE = "1 angle"

# The four verdicts a custom angle can come back with (D-V1-7). Maz overrides
# regardless — this is information, never a gate.
CUSTOM_VERDICTS = ("strongly supported", "workable but thin",
                   "conflicts with evidence", "needs targeted research")

_ANGLE_PROPS = {
    "name": {"type": "string"},
    "central_story": {"type": "string"},
    "driving_question": {"type": "string"},
    "viewer_payoff": {"type": "string"},
    "strongest_evidence": {"type": "string"},
    "strongest_reveal": {"type": "string"},
    "stakes": {"type": "string"},
    "difference_from_baseline": {"type": "string"},
    "weaknesses": {"type": "string"},
}
_ANGLE_SCHEMA = {"type": "object", "properties": _ANGLE_PROPS,
                 "required": ["name", "central_story", "driving_question", "viewer_payoff"]}

_OPTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "story_already_told": {"type": "object", "properties": {
            "dominant_story": {"type": "string"},
            "driving_question": {"type": "string"},
            "typical_beginning": {"type": "string"},
            "typical_middle": {"type": "string"},
            "typical_ending": {"type": "string"},
            "common_conclusion": {"type": "string"},
            "repeated_facts": {"type": "array", "items": {"type": "string"}},
            "disagreements": {"type": "array", "items": {"type": "string"}},
            "missed_by_sources": {"type": "array", "items": {"type": "string"}},
        }, "required": ["dominant_story", "driving_question", "common_conclusion"]},
        "baseline": _ANGLE_SCHEMA,
        "alternatives": {"type": "array", "items": _ANGLE_SCHEMA},
        "baseline_is_strongest": {"type": "boolean"},
        "strongest_why": {"type": "string"},
    },
    "required": ["story_already_told", "baseline", "alternatives",
                 "baseline_is_strongest", "strongest_why"],
}

_ROLE = """You are laying out the STORY CHOICE for a documentary video, from finished research.
You do not choose. You lay out real options honestly and the creator picks.

FIRST: name THE STORY ALREADY BEING TOLD by the sources in the pile — the dominant story, the
driving question they all circle, the typical beginning/middle/ending, the conclusion a viewer
takes away, the facts nearly all of them repeat, where they disagree, and what the deeper research
found that most of them missed. Describe only what is in the pile. Never call it "the mainstream
story", "the accepted account" or "what everyone believes" — you have not surveyed the world, only
these sources.

THEN: the baseline angle (telling that existing story well) and THREE genuinely different
alternatives. They must differ at the STORY level: a different central story, a different driving
question, a different payoff. Same story with forensic detail, same story with trial detail, same
story with parole detail are NOT three alternatives — they are one story with three emphases. If
you cannot find three real story-level alternatives from this evidence, say so in the weaknesses
field of the ones you strain to produce rather than inventing.

FINALLY: is the familiar/baseline story still the strongest? NOVELTY IS NOT AUTOMATICALLY BETTER.
If the baseline is strongest, set baseline_is_strongest true and say plainly why. Do not
manufacture a weaker unique angle to look clever.

Every angle carries: central story · driving question · viewer payoff · strongest evidence
(cite what it rests on) · strongest reveal or consequence · stakes · how it differs from the
baseline · its weaknesses and risks. Weaknesses are mandatory and specific."""


# ── the evidence the decision rests on, selected structurally ────────────────

def _load(episode: Path, name: str) -> dict:
    p = episode / "research" / name
    if not p.exists():
        return {}
    payload = json.loads(p.read_text())
    return payload.get("data", payload)


def source_corpus(episode: Path) -> dict:
    """Where the baseline comes from, and what we are entitled to call it.

    Supplied sources (the creator handed them over) and research-discovered
    sources (the Research Agent found them) are different evidence for
    different claims. Packer, for example, has ZERO supplied sources — every
    one of its eleven came out of research — so its baseline is honestly "what
    the research corpus tells", not "what your sources tell", and under no
    circumstance "the mainstream story".
    """
    from backend.lwm import manifest

    supplied = [s for s in manifest.load(episode)["sources"]]
    doc_0 = _load(episode, "doc_0.json")
    discovered = [
        {"id": s.get("source_id"), "type": s.get("source_type"), "title": s.get("title"),
         "creator": s.get("creator"), "url": s.get("url"),
         "summary": (s.get("skim_summary") or "")}
        for s in doc_0.get("sources", []) if s.get("status") != "failed"
    ]
    supplied_ra_ids = {s.get("ra_source_id") for s in supplied if s.get("ra_source_id")}
    for d in discovered:
        d["supplied_by_creator"] = d["id"] in supplied_ra_ids

    n_supplied = sum(1 for d in discovered if d["supplied_by_creator"])
    if n_supplied:
        basis = "the sources you supplied"
        caveat = (f"{n_supplied} of {len(discovered)} sources were supplied by you; "
                  "the rest were found by research.")
    else:
        basis = "the research corpus"
        caveat = ("You supplied no sources for this episode — every source here was found by "
                  "research. So this is what the research corpus tells, not a survey of what "
                  "the world believes.")
    return {"basis": basis, "caveat": caveat, "sources": discovered,
            "supplied_count": n_supplied, "total": len(discovered)}


def evidence_pack(episode: Path) -> dict:
    """Complete, structured research context — no first-N-character slicing."""
    doc_1, doc_2 = _load(episode, "doc_1.json"), _load(episode, "doc_2.json")
    corpus = source_corpus(episode)
    return {
        "corpus": corpus,
        "read": (doc_2.get("read") or {}),
        "key_points": [{"id": k.get("key_point_id"), "statement": k.get("statement"),
                        "confidence": k.get("confidence"), "sources": k.get("source_ids")}
                       for k in doc_1.get("key_points", [])],
        "tensions": [{"description": t.get("description"), "sources": t.get("source_ids")}
                     for t in doc_1.get("tensions", [])],
        "disputes": [{"claim": d.get("claim"), "holders": d.get("holders")}
                     for d in doc_2.get("disputes", [])],
        "gaps": [g.get("description") for g in doc_1.get("gaps", [])],
        "record_span": [r.get("when") for r in doc_2.get("record", []) if r.get("when")],
        "anecdotes": [a.get("title") or a.get("what") or "" for a in doc_2.get("anecdotes", [])],
    }


def previous_idea(episode: Path) -> str:
    """Maz's earlier angle note, if the ledger carries one.

    D-V1-12: Packer's "tell it as it happened, buried-evidence twist lands
    late" is a PREVIOUS IDEA and an input to this decision — never a locked
    angle, and never chosen on his behalf.
    """
    rows = ledger.read_rows(episode)
    row = rows.get(STAGE)
    note = (row.notes if row else "") or ""
    if row and row.status.strip().lower().startswith("chosen"):
        return ""
    note = re.sub(r"^\s*spine chosen:\s*", "", note, flags=re.I).strip()
    return "" if note.lower().startswith(("options ready", "—")) else note


# ── story-level distinctness, checked by code ────────────────────────────────

_STOP = set("""a an and are as at be but by for from had has have he her his how i if in into is it
its no not of on or our she that the their them then there these they this to was were what when
which who why will with you your story about""".split())


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", (text or "").lower()) if w not in _STOP and len(w) > 2}


def _same_story(a: dict, b: dict, floor: float = 0.6) -> bool:
    """Two angles are the same story when both their central story AND their
    driving question are largely the same words. Detail differences ride on
    top of an unchanged story and score high on both."""
    for field in ("central_story", "driving_question"):
        ta, tb = _tokens(a.get(field, "")), _tokens(b.get(field, ""))
        if not ta or not tb:
            return False
        if len(ta & tb) / min(len(ta), len(tb)) < floor:
            return False
    return True


def distinctness(baseline: dict, alternatives: list[dict]) -> list[dict]:
    """Per-alternative: is it story-level different, and if not, from what."""
    out = []
    for i, alt in enumerate(alternatives):
        clashes = []
        if _same_story(alt, baseline):
            clashes.append("the baseline")
        for j, other in enumerate(alternatives):
            if j < i and _same_story(alt, other):
                clashes.append(other.get("name") or f"alternative {j + 1}")
        out.append({"name": alt.get("name") or f"alternative {i + 1}",
                    "story_level": not clashes,
                    "same_story_as": clashes})
    return out


# ── build ────────────────────────────────────────────────────────────────────

def _prompt(pack: dict, prev: str, retry_note: str = "") -> str:
    c = pack["corpus"]
    lines = [
        f"SOURCE BASIS: {c['basis']}. {c['caveat']}",
        "",
        "SOURCES IN THE PILE",
    ]
    for s in c["sources"]:
        tag = "SUPPLIED BY THE CREATOR" if s["supplied_by_creator"] else "found by research"
        lines.append(f"- [{s['id']}] ({s['type']}, {tag}) {s['title']} — {s['creator'] or '—'}")
        if s["summary"]:
            lines.append(f"    {s['summary']}")
    read = pack["read"]
    if read:
        lines += ["", "WHAT THE PILE ADDS UP TO (research read)", read.get("lede", "")]
        lines += [p if isinstance(p, str) else json.dumps(p) for p in (read.get("paragraphs") or [])]
    lines += ["", f"KEY POINTS ({len(pack['key_points'])})"]
    lines += [f"- [{k['id']}] {k['statement']}  (confidence {k['confidence']}; {', '.join(k['sources'] or [])})"
              for k in pack["key_points"]]
    lines += ["", f"WHERE THE SOURCES DISAGREE ({len(pack['tensions'])} tensions, {len(pack['disputes'])} disputes)"]
    lines += [f"- {t['description']}" for t in pack["tensions"]]
    lines += [f"- {d['claim']} — {d['holders']}" for d in pack["disputes"]]
    lines += ["", "WHAT THE RESEARCH COULD NOT ESTABLISH"]
    lines += [f"- {g}" for g in pack["gaps"]]
    if pack["anecdotes"]:
        lines += ["", "HUMAN MATERIAL"] + [f"- {a}" for a in pack["anecdotes"] if a]
    if prev:
        lines += ["", "A PREVIOUS IDEA THE CREATOR HAD (an input, NOT a decision, NOT necessarily right)",
                  prev]
    if retry_note:
        lines += ["", "THE PREVIOUS ATTEMPT FAILED THE STORY-LEVEL TEST", retry_note]
    return "\n".join(lines)


def build(episode: Path, client: Any = None) -> dict:
    """Lay out the angle decision. Writes the artifacts; chooses nothing."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")

    pack = evidence_pack(episode)
    prev = previous_idea(episode)
    data, _ = client.generate_structured(prompt=_prompt(pack, prev), schema=_OPTIONS_SCHEMA,
                                         system=_ROLE, max_tokens=12000)

    alts = list(data.get("alternatives") or [])
    checks = distinctness(data["baseline"], alts)
    if any(not c["story_level"] for c in checks):
        # ONE regeneration, naming exactly what collapsed. Then we report the
        # truth rather than dressing an emphasis up as an alternative.
        note = "; ".join(f"{c['name']} is the same story as {' and '.join(c['same_story_as'])}"
                         for c in checks if not c["story_level"])
        retry, _ = client.generate_structured(
            prompt=_prompt(pack, prev, retry_note=note + ". Different DETAIL is not a different "
                                                        "STORY. Give story-level alternatives or "
                                                        "say in weaknesses that the evidence does "
                                                        "not support one."),
            schema=_OPTIONS_SCHEMA, system=_ROLE, max_tokens=12000)
        retry_checks = distinctness(retry["baseline"], list(retry.get("alternatives") or []))
        if sum(c["story_level"] for c in retry_checks) >= sum(c["story_level"] for c in checks):
            data, alts, checks = retry, list(retry.get("alternatives") or []), retry_checks

    options = {
        "episode": episode.name,
        "basis": pack["corpus"]["basis"],
        "basis_caveat": pack["corpus"]["caveat"],
        "supplied_sources": pack["corpus"]["supplied_count"],
        "total_sources": pack["corpus"]["total"],
        "story_already_told": data["story_already_told"],
        "baseline": data["baseline"],
        "alternatives": alts,
        "distinctness": checks,
        "baseline_is_strongest": bool(data.get("baseline_is_strongest")),
        "strongest_why": data.get("strongest_why", ""),
        "previous_maz_idea": prev,
        "custom_option": "Type your own angle; the system checks it against the evidence and you "
                         "override regardless.",
        "chosen": None,
    }
    (episode / "outputs").mkdir(exist_ok=True)
    (episode / "outputs" / "angle-options.json").write_text(
        json.dumps(options, indent=1, ensure_ascii=False))
    (episode / "01-angle-options.md").write_text(render(options))
    note = f"baseline + {len(alts)} alternative(s)"
    if prev:
        note += " + Maz's previous idea (D-V1-12: an input, not a lock)"
    note += "; system read: baseline strongest" if options["baseline_is_strongest"] else \
            "; system read: an alternative is stronger"
    ledger.update_row(episode, STAGE, status="options ready",
                      gate="KILL gate: not run", notes=note)
    return options


def _angle_md(a: dict, heading: str, check: dict | None = None) -> list[str]:
    out = [f"### {heading} — {a.get('name', '(unnamed)')}", ""]
    for label, key in [("Central story", "central_story"), ("Driving question", "driving_question"),
                       ("What the viewer gets", "viewer_payoff"),
                       ("Strongest evidence", "strongest_evidence"),
                       ("Strongest reveal / consequence", "strongest_reveal"),
                       ("Stakes", "stakes"),
                       ("How it differs from the baseline", "difference_from_baseline"),
                       ("Weaknesses and risks", "weaknesses")]:
        if a.get(key):
            out.append(f"- **{label}:** {a[key]}")
    if check and not check["story_level"]:
        out.append(f"- ⚠️ **Not a story-level alternative** — it is the same story as "
                   f"{' and '.join(check['same_story_as'])}, told with different emphasis.")
    out.append("")
    return out


def render(o: dict) -> str:
    s = o["story_already_told"]
    out = [
        "<!--\nartifact:  01-angle-options\nversion:   v1 (lwm angle stage, D-V1-7)\n"
        "upstream:  03-brief · 04b-briefing · 04-sources-registry\n"
        "readiness: awaiting the creator's choice — no agent chooses an angle\n-->\n",
        "# The story choice\n",
        f"Drawn from **{o['basis']}** — {o['supplied_sources']} of {o['total_sources']} sources "
        f"supplied by you.\n",
        f"> {o['basis_caveat']}\n",
        "## The story already being told\n",
        f"- **Dominant story:** {s.get('dominant_story', '')}",
        f"- **The question they all circle:** {s.get('driving_question', '')}",
        f"- **Typical beginning:** {s.get('typical_beginning', '—')}",
        f"- **Typical middle:** {s.get('typical_middle', '—')}",
        f"- **Typical ending:** {s.get('typical_ending', '—')}",
        f"- **What a viewer takes away:** {s.get('common_conclusion', '')}\n",
    ]
    for label, key in [("Facts nearly all of them repeat", "repeated_facts"),
                       ("Where they disagree", "disagreements"),
                       ("What our research found that they missed", "missed_by_sources")]:
        items = s.get(key) or []
        out.append(f"**{label}**\n")
        out += [f"- {i}" for i in items] or ["- (none recorded)"]
        out.append("")

    out.append("## Your options\n")
    if o["baseline_is_strongest"]:
        out.append(f"**The system's read: the familiar story is still the strongest one.** "
                   f"{o['strongest_why']}\n")
    else:
        out.append(f"**The system's read:** {o['strongest_why']}\n")
    out += _angle_md(o["baseline"], "Option 1 · BASELINE")
    for i, (alt, chk) in enumerate(zip(o["alternatives"], o["distinctness"], strict=False), start=2):
        out += _angle_md(alt, f"Option {i} · ALTERNATIVE", chk)
    if o["previous_maz_idea"]:
        out += ["### Your previous idea\n",
                f"> {o['previous_maz_idea']}\n",
                "Recorded before the research came back. It is an input to this decision, "
                "not a decision — nothing has locked it.\n"]
    out += ["### Your own angle\n", o["custom_option"], "",
            "---\n",
            "Choose with `lwm decide angle --baseline` · `--alt N` · `--previous` · "
            "`--custom \"…\"`, or in the dashboard. Nothing downstream runs until you do.\n"]
    return "\n".join(out)


# ── custom angle assessment ──────────────────────────────────────────────────

_CUSTOM_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(CUSTOM_VERDICTS)},
        "why": {"type": "string"},
        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "research_needed": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "why"],
}

_CUSTOM_ROLE = """The creator has written his own angle. Check it against the research evidence and
report ONE verdict:
- "strongly supported" — the evidence carries this story.
- "workable but thin" — tellable, but the material is thinner than it should be; say where.
- "conflicts with evidence" — something in the research contradicts it; name what.
- "needs targeted research" — it could work, but specific material is missing; name exactly what.
You are informing a decision, not making one. He overrides you regardless, and that is correct.
Be specific and cite the evidence you are reasoning from. Never flatter."""


def assess_custom(episode: Path, text: str, client: Any = None) -> dict:
    """One of four verdicts on Maz's own angle. Advisory — he overrides."""
    if client is None:
        from backend.lwm.routing import seat_client
        client, _m = seat_client("judge")
    pack = evidence_pack(episode)
    data, _ = client.generate_structured(
        prompt=f"THE CREATOR'S ANGLE\n{text}\n\n{_prompt(pack, '')}",
        schema=_CUSTOM_SCHEMA, system=_CUSTOM_ROLE, max_tokens=4000)
    verdict = data.get("verdict", "")
    if verdict not in CUSTOM_VERDICTS:
        verdict = "needs targeted research"
        data["why"] = ("the assessment did not return one of the four verdicts, so this is the "
                       "safe reading, not a judgment: " + data.get("why", ""))
    return {"angle": text, "verdict": verdict, "why": data.get("why", ""),
            "supporting_evidence": data.get("supporting_evidence") or [],
            "conflicts": data.get("conflicts") or [],
            "research_needed": data.get("research_needed") or [],
            "override": "Maz's choice stands regardless of this verdict."}
