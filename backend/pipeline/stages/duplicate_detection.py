"""Detect syndicated duplicates among sources, by code.

Wire stories are republished verbatim under several mastheads. Counted
naively, four copies of one article look like four sources agreeing, which is
the single most misleading thing a research document can say. On the films
corpus SRC_7 and SRC_8 are the same Conversation piece, one of them
republished by ScreenHub, and the pipeline counted them as two.

The decision is mechanical: 8-word shingle containment over the raw texts.
Measured on that corpus, the syndicated pair scores 0.976 and every other pair
scores 0.000, so the separation is not marginal. A model is never asked.
"""

from typing import Optional

from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.pipeline.injection_guard import flag_sources, injection_warning
from backend.pipeline.text_similarity import shingle_overlap

# Calibrated on the films corpus: syndicated pair 0.976, all 27 other pairs
# 0.000. Half the shorter text appearing verbatim in the longer one is well
# clear of anything two independently written articles produce.
DUPLICATE_THRESHOLD = 0.50

# Shorter than this, shingle overlap is not a reliable signal
_MIN_WORDS_TO_COMPARE = 200


def _first_published(
    a: tuple[str, str, Optional[str]],
    b: tuple[str, str, Optional[str]],
) -> tuple[str, str]:
    """Decide which of two identical sources is the original.

    Publication date decides it: the outlet that ran the story first is the
    one the pipeline should attribute. When dates are missing or equal, the
    fuller text wins, since a republication is usually trimmed.

    Args:
        a: (source_id, text, published) for the first source.
        b: (source_id, text, published) for the second.

    Returns:
        Tuple of (canonical_id, duplicate_id).
    """
    id_a, text_a, date_a = a
    id_b, text_b, date_b = b

    if date_a and date_b and date_a != date_b:
        return (id_a, id_b) if date_a < date_b else (id_b, id_a)

    return (id_a, id_b) if len(text_a.split()) >= len(text_b.split()) else (id_b, id_a)


def find_duplicate_sources(
    sources: list[tuple],
    threshold: float = DUPLICATE_THRESHOLD,
) -> tuple[dict[str, str], list[dict]]:
    """Find sources that are republished copies of each other.

    Nothing is deleted: duplicates keep their own entry in the ledger and the
    Source Trail, they simply stop counting as independent corroboration.

    Args:
        sources: Tuples of (source_id, raw text) or (source_id, raw text,
            published date), in ledger order. Dates decide which copy is the
            original where they exist.
        threshold: Minimum shingle containment to call two sources copies.

    Returns:
        Tuple of (duplicate_of, report). `duplicate_of` maps a duplicate's
        source ID to its canonical source ID. `report` lists each detected
        pair with its score, for the ledger and the Source Trail.
    """
    comparable = [
        (source[0], source[1], source[2] if len(source) > 2 else None)
        for source in sources
        if source[1] and len(source[1].split()) >= _MIN_WORDS_TO_COMPARE
    ]

    duplicate_of: dict[str, str] = {}
    report: list[dict] = []

    for index, source_a in enumerate(comparable):
        for source_b in comparable[index + 1:]:
            score = shingle_overlap(source_a[1], source_b[1])
            if score < threshold:
                continue

            canonical, duplicate = _first_published(source_a, source_b)
            # Follow an existing chain so A->B->C collapses to one canonical.
            canonical = duplicate_of.get(canonical, canonical)
            if duplicate == canonical:
                continue

            duplicate_of[duplicate] = canonical
            report.append(
                {
                    "duplicate": duplicate,
                    "canonical": canonical,
                    "overlap": round(score, 3),
                }
            )

    return duplicate_of, report


def stage_duplicate_detection(ctx: PipelineContext) -> None:
    """Pipeline stage: mark syndicated duplicates before anything counts sources.

    Runs before extraction so every later count (corroboration, evidence
    status chips, source totals) works from independent sources rather than
    copies. Stores `duplicate_sources` and `duplicate_source_report` on the
    context.

    Args:
        ctx: Pipeline context carrying `source_identity_packages`.
    """
    packages = getattr(ctx, "source_identity_packages", [])
    sources = [
        (pkg.source_id, pkg.content or "", getattr(pkg, "published", None))
        for pkg in packages
    ]

    duplicate_of, report = find_duplicate_sources(sources)
    ctx.duplicate_sources = duplicate_of
    ctx.duplicate_source_report = report

    # The same walk over every source is the natural place to flag text that
    # addresses a model rather than a reader (work order I.28).
    flagged = flag_sources(
        [{"source_id": sid, "full_text": text} for sid, text, *_ in sources]
    )
    ctx.injection_flags = flagged
    for source_id, findings in flagged.items():
        warning = injection_warning(source_id, findings)
        if warning:
            logger.warning(f"[{ctx.job_id}] {warning}")
            ctx.add_warning(warning)

    if not report:
        logger.info(f"[{ctx.job_id}] No syndicated duplicates among {len(sources)} sources")
        return

    for pair in report:
        message = (
            f"{pair['duplicate']} is a republished copy of {pair['canonical']} "
            f"({pair['overlap']:.0%} of its text matches verbatim); it stops "
            f"counting as an independent source"
        )
        logger.info(f"[{ctx.job_id}] {message}")
        ctx.add_warning(message)


def canonical_source(ctx: PipelineContext, source_id: str) -> str:
    """Resolve a source ID to the source it duplicates, if any.

    Args:
        ctx: Pipeline context.
        source_id: Any source ID.

    Returns:
        The canonical source ID, or the input when it is not a duplicate.
    """
    duplicate_of: Optional[dict] = getattr(ctx, "duplicate_sources", None)
    return (duplicate_of or {}).get(source_id, source_id)
