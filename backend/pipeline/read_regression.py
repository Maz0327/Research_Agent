"""Cold-reader read regression (work order I.30).

Section 1 is the only part of the Briefing built to be read top to bottom, and
its whole job is that someone who reads it can hold a conversation about the
topic afterwards. That is testable, and it was tested by hand on 2026-08-15
(scored 8/10). This makes it an instrument that runs per Briefing and on any
change to the Read model.

The division follows the work order: the reader is a model, everything else is
code. A model is a good stand-in for a person meeting the topic cold; it is a
poor judge of whether that person understood, because asking a model to grade
comprehension gets a number with nothing under it. So the scoring is mechanical
— did the cold reader come away knowing the cast, the dispute, and what is
actually established, and is what they say traceable to the corpus?

Two scores, deliberately separate:
  coverage  - how much of what the Briefing establishes the reader retained
  grounding - how much of what the reader says traces to the corpus

A high coverage with low grounding is the dangerous result: a reader who came
away confident and wrong. It is worth more than either number alone.
"""
import json
import os
from typing import Any, Optional

from loguru import logger

from backend.models.briefing import Briefing
from backend.pipeline.briefing_gates import names_in, numbers_in, quotes_in
from backend.pipeline.quote_verification import VERIFIED, verify_quote

# The questions a person actually gets asked after saying they read about
# something. Fixed on purpose: a moving question set makes the trend line
# meaningless.
COLD_READER_QUESTIONS = (
    "What is this about, in your own words?",
    "Who are the people involved, and what did each of them do?",
    "What is actually in dispute, and who is on each side?",
    "What is solidly established here, and what is only claimed?",
    "If someone asked you about this at dinner, what would you tell them?",
)

READER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}

READER_ROLE = """You have just read the text below and nothing else. You have no
other knowledge of this subject — answer only from what you read.

Answer each question the way a person would in conversation: plainly, in a few
sentences, without headings or bullet points.

If the text did not tell you something, say so. "It didn't say" is a correct
answer and a useful one. Do not fill a gap with anything you might know from
elsewhere, and do not hedge a gap into a guess."""


def read_only_text(briefing: Briefing) -> str:
    """Extract Section 1 alone — what a cold reader is actually given."""
    parts = [briefing.read.lede]
    for paragraph in briefing.read.paragraphs:
        parts.append((f"{paragraph.label}: " if paragraph.label else "") + paragraph.text)
    return "\n\n".join(parts)


def expected_content(briefing: Briefing) -> dict[str, list[str]]:
    """What the Briefing establishes, which is what a reader should retain.

    Args:
        briefing: The assembled Briefing.

    Returns:
        Dict of players, disputes, and the topic's key figures.
    """
    return {
        "players": [player.name for player in briefing.players],
        "disputes": [dispute.claim for dispute in briefing.disputes],
        "figures": sorted(numbers_in(read_only_text(briefing))),
    }


def _mentions(answer_text: str, item: str) -> bool:
    """Did the reader mention this thing, allowing for partial names?"""
    lowered = answer_text.lower()
    if item.lower() in lowered:
        return True
    # A reader who says "Petrie" has retained "Flinders Petrie".
    tokens = [t for t in item.split() if len(t) > 3]
    return bool(tokens) and any(t.lower() in lowered for t in tokens)


def score_coverage(answers_text: str, expected: dict[str, list[str]]) -> dict:
    """Measure how much of what the Briefing establishes the reader retained.

    Args:
        answers_text: The reader's answers, joined.
        expected: Output of `expected_content`.

    Returns:
        Per-category rates plus the items the reader lost.
    """
    result: dict[str, Any] = {}
    for category in ("players", "disputes"):
        items = expected.get(category) or []
        if not items:
            result[category] = {"rate": None, "missed": []}
            continue
        missed = [item for item in items if not _mentions(answers_text, item)]
        result[category] = {
            "rate": round((len(items) - len(missed)) / len(items), 3),
            "missed": missed,
        }

    rates = [v["rate"] for v in result.values() if v["rate"] is not None]
    result["overall"] = round(sum(rates) / len(rates), 3) if rates else None
    return result


def score_grounding(answers_text: str, corpus: str) -> dict:
    """Measure how much of what the reader says traces back to the corpus.

    A reader can only repeat what Section 1 told them, so an ungrounded atom
    here means Section 1 put it there — this doubles as a check on the Read.

    Args:
        answers_text: The reader's answers, joined.
        corpus: All raw source text.

    Returns:
        Ungrounded rate and the offending atoms.
    """
    corpus_lower = corpus.lower()
    ungrounded: list[str] = []
    atoms = 0

    for number in numbers_in(answers_text):
        atoms += 1
        if number.lower() not in corpus_lower:
            ungrounded.append(number)

    for name in names_in(answers_text):
        atoms += 1
        if name.lower() not in corpus_lower:
            ungrounded.append(name)

    for quote in quotes_in(answers_text):
        atoms += 1
        if verify_quote(quote, corpus).get("verdict") != VERIFIED:
            ungrounded.append(quote[:60])

    return {
        "atoms": atoms,
        "ungrounded": len(ungrounded),
        "ungrounded_rate": round(len(ungrounded) / atoms, 3) if atoms else 0.0,
        "items": ungrounded[:10],
    }


def run_cold_reader(briefing: Briefing, client: Any) -> list[dict]:
    """Give a blind reader Section 1 and ask what they came away with.

    Args:
        briefing: The assembled Briefing.
        client: A structured client.

    Returns:
        The reader's answers, or [] when the call fails.
    """
    prompt = (
        read_only_text(briefing)
        + "\n\n---\n\nQUESTIONS:\n"
        + "\n".join(f"- {q}" for q in COLD_READER_QUESTIONS)
    )
    try:
        data, _usage = client.generate_structured(
            prompt=prompt,
            schema=READER_SCHEMA,
            system=READER_ROLE,
            max_tokens=4_000,
        )
    except Exception as exc:
        logger.warning(f"Read regression: cold reader call failed ({exc})")
        return []
    return list(data.get("answers") or [])


def read_regression(
    briefing: Briefing,
    corpus: str,
    client: Any,
    history_path: Optional[str] = None,
) -> dict:
    """Run the cold-reader test and score it against the trend.

    Args:
        briefing: The assembled Briefing.
        corpus: All raw source text, for the grounding half.
        client: A structured client for the reader call.
        history_path: JSON file of previous runs; None skips trend tracking.

    Returns:
        The scored result, with the delta against the last run when available.
    """
    answers = run_cold_reader(briefing, client)
    if not answers:
        return {"ran": False, "reason": "cold reader call failed"}

    answers_text = " ".join(a.get("answer", "") for a in answers)
    coverage = score_coverage(answers_text, expected_content(briefing))
    grounding = score_grounding(answers_text, corpus)

    result = {
        "ran": True,
        "job_id": briefing.job_id,
        "topic": briefing.topic,
        "coverage": coverage,
        "grounding": grounding,
        "answer_words": len(answers_text.split()),
        "answers": answers,
    }

    if history_path:
        result["trend"] = _track(history_path, result)
    return result


def _track(history_path: str, result: dict) -> dict:
    """Append this run to the history and report the delta against the last one."""
    history: list[dict] = []
    if os.path.exists(history_path):
        try:
            with open(history_path) as handle:
                history = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Read regression: unreadable history ({exc}); starting fresh")

    previous = history[-1] if history else None
    entry = {
        "job_id": result["job_id"],
        "coverage": result["coverage"]["overall"],
        "ungrounded_rate": result["grounding"]["ungrounded_rate"],
    }
    history.append(entry)

    try:
        with open(history_path, "w") as handle:
            json.dump(history[-50:], handle, indent=1)
    except OSError as exc:
        logger.warning(f"Read regression: could not write history ({exc})")

    if not previous or previous.get("coverage") is None or entry["coverage"] is None:
        return {"runs": len(history), "coverage_delta": None, "grounding_delta": None}

    return {
        "runs": len(history),
        "coverage_delta": round(entry["coverage"] - previous["coverage"], 3),
        "grounding_delta": round(
            entry["ungrounded_rate"] - previous.get("ungrounded_rate", 0.0), 3
        ),
    }
