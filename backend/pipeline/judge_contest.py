"""Score judge models against ground truth, with the protocol the plan names.

A judge slot cannot be filled by reading model cards. The incumbent
(`kimi-k2.5`) was defensible because an independent study measured it; both
successors have no judge data at all, so the choice has to be made locally
(EXECUTION-PLAN section 1).

Three measurements, and the first one is the reason the other two exist:

- **Cohen's kappa** against a constructed labelled set. Never raw agreement,
  which flatters by roughly 38 points on a balanced set because always
  answering "supported" already scores 50%.
- **Position swap.** The same pair judged A/B and then B/A. A judge that
  changes its answer when the order changes is measuring position, not truth.
- **Test-retest.** The same items three times. Reproducibility is not
  correctness - a judge can be reliably wrong - so it is reported beside kappa
  and never instead of it.

Standing law: the judge is never a Claude model while Claude does synthesis,
and never shares a vendor with extraction.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger

from backend.models.briefing import _object
from backend.pipeline.faithfulness_set import cohens_kappa
from backend.pipeline.text_similarity import content_tokens

JUDGE_ROLE = """You check whether a statement is supported by source material.

You are given an extract from a source, and one statement. Answer only whether
the source material supports the statement as written.

Rules:
- Supported means the material says it. Not that it sounds plausible, not that
  it is probably true in the world, not that a similar thing is said.
- A statement with a different number, a different name, a reversed meaning, or
  an added specific the material does not contain is UNSUPPORTED, however
  reasonable it reads.
- If the material is silent on the statement, that is UNSUPPORTED.
- Judge the statement as written. Do not repair it."""

VERDICT_SCHEMA = _object(
    {
        "verdict": {"type": "string", "enum": ["supported", "unsupported"]},
        "reason": {"type": "string"},
    }
)

PAIR_SCHEMA = _object(
    {
        "supported_option": {"type": "string", "enum": ["A", "B"]},
        "reason": {"type": "string"},
    }
)

PAIR_ROLE = """You are shown source material and two statements, A and B.

Exactly one of them is supported by the material as written. The other has been
altered: a changed number, a swapped name, a reversed meaning, or an added
detail the material does not contain.

Answer which one the material supports. Judge the statements as written."""


@dataclass
class JudgeScore:
    """What one judge did on the labelled set."""

    model: str
    kappa: float = 0.0
    accuracy: float = 0.0
    by_corruption: dict = field(default_factory=dict)
    position_consistency: Optional[float] = None
    test_retest: Optional[float] = None
    calls: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "kappa": round(self.kappa, 3),
            "accuracy": round(self.accuracy, 3),
            "by_corruption": self.by_corruption,
            "position_consistency": (
                round(self.position_consistency, 3)
                if self.position_consistency is not None
                else None
            ),
            "test_retest": (
                round(self.test_retest, 3) if self.test_retest is not None else None
            ),
            "calls": self.calls,
            "errors": self.errors,
        }


def source_window(statement: str, source_text: str, words: int = 260) -> str:
    """Pull the part of a source a statement is about.

    A judge given a whole transcript is being asked a retrieval question as
    well as a faithfulness one. The window keeps the task to the one being
    measured.

    Args:
        statement: The statement under judgment.
        source_text: The full source.
        words: Window width.

    Returns:
        The best-matching window of the source.
    """
    tokens = content_tokens(statement)
    source_words = source_text.split()
    if not tokens or len(source_words) <= words:
        return source_text

    best_start, best_overlap = 0, -1
    step = max(20, words // 4)
    for start in range(0, len(source_words) - words, step):
        window = " ".join(source_words[start: start + words])
        overlap = len(tokens & content_tokens(window))
        if overlap > best_overlap:
            best_overlap, best_start = overlap, start

    return " ".join(source_words[best_start: best_start + words])


def judge_item(client: Any, statement: str, material: str) -> Optional[str]:
    """Ask one judge about one statement.

    Args:
        client: A structured-output client.
        statement: The statement under judgment.
        material: The source extract.

    Returns:
        "supported", "unsupported", or None when the call failed.
    """
    try:
        data, _ = client.generate_structured(
            prompt=f"SOURCE MATERIAL\n{material}\n\nSTATEMENT\n{statement}",
            schema=VERDICT_SCHEMA,
            system=JUDGE_ROLE,
            max_tokens=500,
        )
    except Exception as e:
        logger.warning(f"Judge call failed: {e}")
        return None
    verdict = (data.get("verdict") or "").strip().lower()
    return verdict if verdict in ("supported", "unsupported") else None


def judge_pair(client: Any, option_a: str, option_b: str, material: str) -> Optional[str]:
    """Ask one judge which of two statements the material supports.

    Args:
        client: A structured-output client.
        option_a: Statement shown first.
        option_b: Statement shown second.
        material: The source extract.

    Returns:
        "A", "B", or None when the call failed.
    """
    try:
        data, _ = client.generate_structured(
            prompt=(
                f"SOURCE MATERIAL\n{material}\n\n"
                f"STATEMENT A\n{option_a}\n\nSTATEMENT B\n{option_b}"
            ),
            schema=PAIR_SCHEMA,
            system=PAIR_ROLE,
            max_tokens=500,
        )
    except Exception as e:
        logger.warning(f"Judge pair call failed: {e}")
        return None
    choice = (data.get("supported_option") or "").strip().upper()
    return choice if choice in ("A", "B") else None


def score_judge(
    client: Any,
    model: str,
    items: list[dict],
    windows: dict[str, str],
    repeats: int = 3,
) -> JudgeScore:
    """Run the full protocol against one judge.

    Args:
        client: A structured-output client for this judge.
        model: The model's ID, for the report.
        items: The labelled faithfulness set.
        windows: Map of item_id to the source extract for that item.
        repeats: How many times to repeat the classification pass.

    Returns:
        A JudgeScore.
    """
    score = JudgeScore(model=model)
    runs: list[list[Optional[str]]] = []

    for run in range(repeats):
        verdicts = []
        for item in items:
            verdict = judge_item(client, item["statement"], windows[item["item_id"]])
            score.calls += 1
            if verdict is None:
                score.errors += 1
            verdicts.append(verdict)
        runs.append(verdicts)
        logger.info(f"{model}: classification run {run + 1}/{repeats} done")

    # Kappa on the first run, which is the judge's answer under normal use.
    truth = [item["label"] for item in items]
    first = [v or "unsupported" for v in runs[0]]
    score.kappa = cohens_kappa(truth, first)
    score.accuracy = sum(1 for t, p in zip(truth, first, strict=False) if t == p) / len(truth)

    by_corruption: dict[str, list[int]] = {}
    for item, verdict in zip(items, first, strict=False):
        key = item["corruption"] or "supported"
        by_corruption.setdefault(key, []).append(int(verdict == item["label"]))
    score.by_corruption = {
        key: round(sum(v) / len(v), 2) for key, v in sorted(by_corruption.items())
    }

    if repeats > 1:
        agreements = [
            sum(1 for a, b in zip(runs[0], runs[i], strict=False) if a == b) / len(items)
            for i in range(1, repeats)
        ]
        score.test_retest = sum(agreements) / len(agreements)

    return score


def score_position_bias(
    client: Any, items: list[dict], windows: dict[str, str], pairs: int = 12
) -> tuple[float, int]:
    """Measure whether order changes a judge's answer.

    Each pair is judged twice with the options swapped. A judge measuring truth
    gives the same answer both times.

    Args:
        client: A structured-output client.
        items: The labelled set.
        windows: Map of item_id to source extract.
        pairs: How many pairs to test.

    Returns:
        Tuple of (consistency 0.0-1.0, number of pairs actually judged).
    """
    supported = [i for i in items if i["label"] == "supported"]
    unsupported = [i for i in items if i["label"] == "unsupported"]
    tested, consistent = 0, 0

    for real, fake in list(zip(supported, unsupported, strict=False))[:pairs]:
        material = windows[real["item_id"]]
        forward = judge_pair(client, real["statement"], fake["statement"], material)
        backward = judge_pair(client, fake["statement"], real["statement"], material)
        if forward is None or backward is None:
            continue
        tested += 1
        # Consistent means the same statement wins both times, which shows up
        # as opposite letters once the options have been swapped.
        if forward != backward:
            consistent += 1

    return (consistent / tested if tested else 0.0), tested
