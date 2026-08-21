"""Grounding repair: fix invented facts instead of only reporting them (D-036).

The grounding gate finds every hard atom — name, number, quoted span — that the
Briefing asserts and the corpus does not contain. In the short fields it then
deletes the offending sentence. In the long prose it stops there and reports,
because cutting a sentence out of the middle of an argument does its own damage.

Reporting is not enough. Measured 2026-08-20 across the writer bake-off, a Read
carries roughly 3 to 8 invented atoms depending on the model, and the ones in
long prose reached the reader flagged rather than fixed.

This pass closes that. For each invented atom it asks the model one narrow
question — the corpus says this, you wrote that, which is it — and code splices
the answer in. Three properties matter and all three are deliberate:

- **The model never sees the document back.** It answers about one atom, in one
  passage, and returns a replacement fragment. It cannot quietly rewrite an
  argument while correcting a number (D-024, pairs applied by code).
- **Deletion is always available and always safe.** When the corpus does not
  support any version of the claim, the answer is to cut the clause, and code
  does the cutting.
- **One round.** An atom the round cannot fix stays flagged. Inventing a
  correction to clear a gate finding would be the worst possible outcome here.

Honest limit, stated so nobody mistakes this for more than it is: this repairs
facts the corpus does not contain. A fact the corpus DOES contain, attached to
the wrong person or with its meaning reversed, passes this pass untouched. That
is a reading problem, not a matching one, and it belongs to the semantic check.
"""
import re
from typing import Any

from loguru import logger

from backend.models.briefing import _array_of, _object
from backend.pipeline.briefing_gates import GateReport, briefing_prose

REPAIR_SCHEMA: dict = _object(
    {
        "repairs": _array_of(
            {
                "atom": {"type": "string"},
                "action": {"type": "string", "enum": ["keep", "correct", "cut"]},
                "replacement": {"type": "string"},
            }
        )
    }
)

REPAIR_ROLE = """You are correcting specific facts in a research document against
the source material they came from.

You will be given, for each item: a passage from the document, one ATOM in it (a
name, a number, or a quoted phrase), and the SOURCE TEXT that passage was
written from.

A mechanical check could not find the atom in the source. That check matches
text, so it raises false alarms — the source may say "King Tut" where the
document says "Tutankhamun", or spell a name with a different character. You can
read. Decide which of three things is true:

  action "keep" - the source DOES support this, and the checker was wrong. A
      different name for the same person or place, a different spelling, a
      figure written differently (3,000 vs 3000 vs three thousand). Leave
      `replacement` empty. Use this whenever the fact is genuinely there — a
      wrongly deleted true fact is worse than a flagged one.

  action "correct" - the source gives a DIFFERENT value for the same fact.
      Put the source's value in `replacement`. Example: the document says 9,000
      chambers, the source says 3,000 - replacement is "3,000".

  action "cut" - the source does not support this fact in any form, so the
      claim has to go. Put the exact words to REMOVE from the passage in
      `replacement`: the shortest fragment whose removal leaves a sentence that
      still reads correctly. Usually a clause, occasionally a whole sentence.

Rules:
- Never invent a value. If the source does not give one, the action is "cut".
- When you are unsure between "keep" and "cut", choose "keep" and let a human
  see the flag. Deleting a true statement is the worst outcome available here.
- `replacement` for a "correct" is ONLY the new value, not a rewritten sentence.
- `replacement` for a "cut" must be text that appears in the passage verbatim,
  copied exactly, including its punctuation.
- Do not fix anything you were not asked about. One atom, one answer.

Return one entry for every atom you are given, and no others."""


def _sentence_around(text: str, atom: str, width: int = 320) -> str:
    """The passage around an atom, for the model to judge it in context."""
    position = text.find(atom)
    if position < 0:
        return text[:width]
    return text[max(0, position - width // 2) : position + len(atom) + width // 2]


def _tidy(text: str) -> str:
    """Clean up the punctuation a removal leaves behind."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*([,.;:])", r"\2", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def apply_repair(text: str, atom: str, action: str, replacement: str) -> tuple[str, bool]:
    """Apply one repair to one passage.

    Args:
        text: The passage.
        atom: The atom the corpus does not contain.
        action: "correct" or "cut".
        replacement: The corrected value, or the fragment to remove.

    Returns:
        Tuple of (text, whether anything changed).
    """
    if action == "keep":
        # The checker was wrong and the model overruled it. Nothing to change.
        return text, False

    if not text or not replacement:
        return text, False

    if action == "correct":
        if atom not in text:
            return text, False
        return text.replace(atom, replacement, 1), True

    if action == "cut":
        if replacement in text:
            return _tidy(text.replace(replacement, "", 1)), True
        # The model paraphrased the fragment. Fall back to cutting the sentence
        # that carries the atom — coarser, but it never leaves the invention in.
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if atom in sentence:
                return _tidy(text.replace(sentence, "", 1)), True
    return text, False


def _prose_targets(briefing, report: GateReport) -> dict[str, list[str]]:
    """Group the gate's findings by the prose location that carries them."""
    by_location: dict[str, list[str]] = {}
    for finding in report.findings:
        by_location.setdefault(finding.where, []).append(finding.value)
    return by_location


def _set_prose(briefing, where: str, text: str) -> bool:
    """Write repaired text back to the field the gate named. True if it landed."""
    if where == "read.lede":
        briefing.read.lede = text
        return True

    match = re.match(r"read\.paragraphs\[(\d+)\]", where)
    if match:
        briefing.read.paragraphs[int(match.group(1))].text = text
        return True

    match = re.match(r"disputes\[(\d+)\]\.(for|against|claim|holders)", where)
    if match:
        dispute = briefing.disputes[int(match.group(1))]
        field = match.group(2)
        if field == "for":
            dispute.case_for.text = text
        elif field == "against":
            dispute.case_against.text = text
        else:
            setattr(dispute, field, text)
        return True

    match = re.match(r"files\[(.+)\]$", where)
    if match:
        for file in briefing.files:
            if file.title == match.group(1):
                file.body = text
                return True
    return False


def repair_grounding(
    briefing,
    report: GateReport,
    raw_texts: list[str],
    client: Any,
    max_atoms: int = 25,
) -> dict:
    """Run one repair round over the atoms the corpus does not contain.

    Args:
        briefing: The assembled Briefing, edited in place.
        report: The grounding gate's report.
        raw_texts: The corpus, for the model to check against.
        client: A structured client.
        max_atoms: Ceiling on atoms repaired in one round.

    Returns:
        A record of the round, including what could not be fixed.
    """
    targets = _prose_targets(briefing, report)
    if not targets:
        return {"ran": False, "reason": "nothing ungrounded"}

    prose = dict(briefing_prose(briefing))
    corpus = "\n\n".join(raw_texts)

    items: list[dict] = []
    for where, atoms in targets.items():
        text = prose.get(where)
        if not text:
            continue
        for atom in atoms:
            if len(items) >= max_atoms:
                break
            items.append(
                {"where": where, "atom": atom, "passage": _sentence_around(text, atom)}
            )

    if not items:
        return {"ran": False, "reason": "no repairable prose locations"}

    payload = "\n\n---\n\n".join(
        f"ATOM: {item['atom']}\nPASSAGE: {item['passage']}\n"
        f"SOURCE TEXT: {_relevant_corpus(corpus, item['passage'])}"
        for item in items
    )

    try:
        data, _usage = client.generate_structured(
            prompt=payload,
            schema=REPAIR_SCHEMA,
            system=REPAIR_ROLE,
            max_tokens=4_000,
        )
    except Exception as exc:
        logger.warning(f"Grounding repair failed ({exc}); findings stand as reported")
        return {"ran": False, "reason": f"call failed: {exc}"}

    answers = {r["atom"]: r for r in (data.get("repairs") or []) if r.get("atom")}
    applied, unresolved, overruled = [], [], []

    for item in items:
        answer = answers.get(item["atom"])
        if not answer:
            unresolved.append(item["atom"])
            continue
        if answer.get("action") == "keep":
            # A false alarm from the text matcher, not an invented fact.
            overruled.append(item["atom"])
            continue
        current = prose.get(item["where"], "")
        repaired, changed = apply_repair(
            current, item["atom"], answer.get("action", ""), answer.get("replacement", "")
        )
        if changed and _set_prose(briefing, item["where"], repaired):
            prose[item["where"]] = repaired
            applied.append(
                {
                    "where": item["where"],
                    "atom": item["atom"],
                    "action": answer.get("action"),
                    "replacement": answer.get("replacement", "")[:80],
                }
            )
        else:
            unresolved.append(item["atom"])

    logger.info(
        f"Grounding repair: {len(applied)} of {len(items)} fixed, "
        f"{len(overruled)} were false alarms, {len(unresolved)} left flagged"
    )
    return {
        "ran": True,
        "considered": len(items),
        "applied": applied,
        "overruled": overruled,
        "unresolved": unresolved,
    }


def _relevant_corpus(corpus: str, passage: str, width: int = 2_000) -> str:
    """Find the part of the corpus a passage is about.

    Handing over the whole corpus would swamp the call; handing over its first
    2,000 characters would ask about evidence that is not there — the same
    defect D-033 found in the judge.
    """
    from backend.pipeline.text_similarity import content_tokens

    wanted = content_tokens(passage)
    if not wanted:
        return corpus[:width]

    words = corpus.split()
    step = 300
    best, best_score = 0, -1.0
    for start in range(0, max(1, len(words) - step), step):
        window = " ".join(words[start : start + step])
        score = len(wanted & content_tokens(window))
        if score > best_score:
            best, best_score = start, score
    return " ".join(words[best : best + step * 2])[:width]
