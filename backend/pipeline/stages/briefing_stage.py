"""Build the Research Briefing: passes, gates, assembly (work order Section J).

The order is the approved one and the division of labour is the point. Code
routes the facts, decides what goes where, counts names, computes chips,
checks coverage and grounding, and assembles the JSON. The model writes prose
into fields it is handed.

Nothing here re-emits a document to edit it. Coverage misses are repaired by
appending, which is the only edit shape this project trusts.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from backend.config import get_settings
from backend.models.briefing import (
    Briefing,
    BriefingMeta,
    Dispute,
    InfoGap,
    Read,
    SourceTrailEntry,
)
from backend.pipeline.briefing_cast import build_cast
from backend.pipeline.briefing_gates import (
    coverage_gate,
    fact_is_covered,
    grounding_gate,
    strip_ungrounded_fields,
)
from backend.pipeline.briefing_lint import lint_briefing
from backend.pipeline.briefing_passes import (
    build_anecdotes,
    build_record_entries,
    repair_file_coverage,
    run_blurb_pass,
    run_contribution_pass,
    run_dispute_pass,
    run_file_pass,
    run_read_pass,
    run_subject_map_pass,
)
from backend.pipeline.briefing_routing import (
    evidence_chip,
    route_facts,
    select_disputes,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.corpus_balance import build_corpus_balance
from backend.pipeline.formatters.briefing_renderer import (
    render_briefing_html,
    render_briefing_markdown,
)
from backend.pipeline.formatters.source_vault import render_source_vault
from backend.pipeline.grounding_repair import repair_grounding
from backend.pipeline.intro_repair import repair_inline_introductions
from backend.state import update_job


def build_briefing(
    ctx: PipelineContext,
    client: Any,
    sources: list[dict],
    disputes_input: list[dict] | None = None,
    gaps: list[dict] | None = None,
    read: Read | None = None,
    subject_map: tuple[list[dict], list[str]] | None = None,
    read_client: Any = None,
) -> tuple[Briefing, dict]:
    """Run every pass and assemble the Briefing.

    Args:
        ctx: Pipeline context (carries the harvest and the duplicate map).
        client: A structured-output client.
        sources: Source dicts with `source_id`, `title`, `full_text`, and
            optional `source_type`, `creator`, `published`, `duplicate_of`.
        disputes_input: Disputes code selected upstream, each with `claim`,
            `holders`, `evidence_for`, `evidence_against`, `source_ids_for`,
            `source_ids_against`, and optional chip inputs.
        gaps: Gap-analysis output, transformed straight into Info Gaps.
        read: An already-written Section 1. Supplying it skips pass 1, which is
            what an iterate run wants: the reference layer is rebuilt from new
            material while the read the owner already accepted stands.
        subject_map: An already-decided (subjects, anecdote_ids) grouping.
            Supplying it skips pass 2 the same way.
        read_client: Client for pass 1 only. Section 1 is the one place the
            model choice was measured to matter (D-034: 0% ungrounded against a
            substitute's ~5%), and the one place a model composes freely rather
            than filling slots code already chose. Defaults to `client`.

    Returns:
        Tuple of (Briefing, report). The report carries both gates and the
        repair record.
    """
    duplicate_of = getattr(ctx, "duplicate_sources", {}) or {}
    inventory = list(getattr(ctx, "harvest_inventory", []) or [])
    raw_by_source = {
        s["source_id"]: (s.get("full_text") or "") for s in sources if s.get("source_id")
    }
    facts_by_source: dict[str, list[str]] = {}
    for fact in inventory:
        facts_by_source.setdefault(fact["source_id"], []).append(fact["text"])

    disputes_input = disputes_input or []

    # --- Pass 1: the Read, from raw text only -------------------------------
    if read is None:
        logger.info(f"[{ctx.job_id}] Briefing pass 1: the Read")
        read = run_read_pass(read_client or client, ctx.topic, sources)
    else:
        logger.info(f"[{ctx.job_id}] Briefing pass 1 skipped: Section 1 supplied")

    # --- Code routing before any reference prose is written -----------------
    routed = route_facts(inventory, [d.get("claim", "") for d in disputes_input])
    logger.info(
        f"[{ctx.job_id}] Routed {len(inventory)} facts: {len(routed['record'])} dated, "
        f"{len(routed['disputed'])} disputed, {len(routed['remaining'])} to group"
    )

    # --- Pass 2: subject map ------------------------------------------------
    if subject_map is None:
        logger.info(f"[{ctx.job_id}] Briefing pass 2: subject map")
        subjects, anecdote_ids = run_subject_map_pass(client, routed["remaining"])
    else:
        subjects, anecdote_ids = subject_map
        logger.info(f"[{ctx.job_id}] Briefing pass 2 skipped: grouping supplied")
    by_id = {f["fact_id"]: f for f in inventory}

    skipped_files: list[dict] = []

    # --- Pass 3: files, with a per-file coverage check ----------------------
    files = []
    repairs: list[dict] = []
    for subject in subjects:
        facts = [by_id[i] for i in subject["fact_ids"] if i in by_id]
        if not facts:
            continue
        logger.info(f"[{ctx.job_id}] Briefing pass 3: file '{subject['title']}'")
        # One failed section must not lose a Briefing the research already paid
        # for. Skip it, record it, carry on — the coverage gate then reports
        # the facts that went unplaced, so the loss is visible rather than
        # silent.
        try:
            file = run_file_pass(client, subject["title"], facts, raw_by_source)
        except Exception as exc:
            logger.warning(
                f"[{ctx.job_id}] file section {subject['title']!r} failed ({exc}); "
                f"skipping it, {len(facts)} facts left for the coverage gate to report"
            )
            skipped_files.append({"title": subject["title"], "facts": len(facts),
                                  "error": str(exc)[:200]})
            continue

        missing = [f for f in facts if not fact_is_covered(f["text"], [file.body])]
        if missing:
            logger.info(
                f"[{ctx.job_id}] File '{file.title}' missed {len(missing)} fact(s); "
                f"appending one repair paragraph"
            )
            file = repair_file_coverage(client, file, missing, raw_by_source)
            still_missing = [
                f for f in missing if not fact_is_covered(f["text"], [file.body])
            ]
            repairs.append(
                {
                    "file": file.title,
                    "missing": len(missing),
                    "still_missing": len(still_missing),
                }
            )
        file.chips = [
            evidence_chip(file.source_ids, duplicate_of=duplicate_of)
        ]
        files.append(file)

    # --- Pass 4: disputes (code selected them, code computes the chip) ------
    disputes = []
    for spec in disputes_input:
        logger.info(f"[{ctx.job_id}] Briefing pass 4: dispute '{spec.get('claim', '')[:50]}'")
        case_for, case_against = run_dispute_pass(
            client,
            claim=spec.get("claim", ""),
            holders=spec.get("holders", ""),
            evidence_for=spec.get("evidence_for", []),
            evidence_against=spec.get("evidence_against", []),
            source_ids_for=spec.get("source_ids_for", []),
            source_ids_against=spec.get("source_ids_against", []),
        )
        disputes.append(
            Dispute(
                claim=spec.get("claim", ""),
                holders=spec.get("holders", ""),
                chip=evidence_chip(
                    list(spec.get("source_ids_for", []))
                    + list(spec.get("source_ids_against", [])),
                    duplicate_of=duplicate_of,
                    contested=bool(spec.get("evidence_against")),
                    belief_migration=bool(spec.get("belief_migration")),
                    verifiable=spec.get("verifiable", True),
                ),
                case_for=case_for,
                case_against=case_against,
            )
        )

    # --- Pass 5: the Record (code skeleton, model blurbs) -------------------
    logger.info(f"[{ctx.job_id}] Briefing pass 5: the Record")
    record_blurbs = run_blurb_pass(client, [f["text"] for f in routed["record"]])
    record = build_record_entries(routed["record"], record_blurbs)

    # --- Pass 6: players (code counts, model writes) ------------------------
    section_prose = {
        "read": " ".join([read.lede] + [p.text for p in read.paragraphs]),
        "files": " ".join(f.body for f in files),
        "record": " ".join(e.what for e in record),
        "disputes": " ".join(
            f"{d.claim} {d.holders} {d.case_for.text} {d.case_against.text}"
            for d in disputes
        ),
    }
    # The cast is read out of the finished briefing, because that is the
    # document a reader looks names up in. The capitalisation heuristic this
    # replaces required a space in a name, so it never saw the 601 mentions of
    # "Packer" and left the subject of the briefing out of his own cast list.
    brief_text = "\n\n".join(section_prose.values())
    players, organisations, places = build_cast(
        client, brief_text, inventory, ctx.job_id
    )

    # --- Pass 7: anecdotes, gaps, source trail ------------------------------
    anecdote_facts = [by_id[i] for i in anecdote_ids if i in by_id]
    anecdote_blurbs = run_blurb_pass(client, [f["text"] for f in anecdote_facts])
    anecdotes = build_anecdotes(anecdote_facts, anecdote_blurbs)

    info_gaps = [
        InfoGap(
            question=(gap.get("label") or gap.get("description") or "").strip(),
            why=(gap.get("why_expected") or "").strip(),
            go_get=(gap.get("suggested_research_direction") or "").strip(),
        )
        for gap in (gaps or [])
        if (gap.get("label") or gap.get("description"))
    ]

    contributions = run_contribution_pass(client, sources, facts_by_source)
    trail = [
        SourceTrailEntry(
            source_id=source["source_id"],
            title=source.get("title") or "Untitled",
            kind=source.get("source_type"),
            year=str(source.get("published")) if source.get("published") else None,
            creator=source.get("creator"),
            contribution=contributions.get(source["source_id"]),
            vault_anchor=f"#{source['source_id'].lower()}",
            duplicate_of=duplicate_of.get(source["source_id"]),
            accessible=bool((source.get("full_text") or "").strip()),
            note=None if (source.get("full_text") or "").strip() else "No text captured",
        )
        for source in sources
        if source.get("source_id")
    ]

    # --- Corpus balance: the advisory header block (work order I.24) --------
    # Advisory only. A lopsided corpus may be deliberate; it may never be
    # invisible. Never allowed to fail the build.
    logger.info(f"[{ctx.job_id}] Briefing: corpus balance")
    duplicate_groups: list[list[str]] = []
    for copy_id, original_id in duplicate_of.items():
        for group in duplicate_groups:
            if original_id in group:
                group.append(copy_id)
                break
        else:
            duplicate_groups.append([original_id, copy_id])
    balance = build_corpus_balance(sources, client, ctx.topic, duplicate_groups)

    # --- Pass 8: assemble, then check both directions -----------------------
    raw_words = sum(len(text.split()) for text in raw_by_source.values())
    briefing = Briefing(
        job_id=ctx.job_id,
        topic=ctx.topic,
        meta=BriefingMeta(
            source_count=len(sources),
            independent_source_count=len(sources) - len(duplicate_of),
            raw_words=raw_words,
            quote_verification_rate=getattr(ctx, "verification_rate", None),
            confidence=getattr(ctx, "overall_confidence", None)
            and getattr(getattr(ctx, "overall_confidence", None), "value", None),
            generated_on=datetime.now(UTC).date().isoformat(),
        ),
        read=read,
        players=players,
        organisations=organisations,
        places=places,
        record=record,
        files=files,
        disputes=disputes,
        anecdotes=anecdotes,
        info_gaps=info_gaps,
        source_trail=trail,
        corpus_balance=balance,
    )

    raw_texts = list(raw_by_source.values())
    harvest_texts = [fact["text"] for fact in inventory]

    grounding = grounding_gate(briefing, raw_texts, harvest_texts)
    # Repair-or-strip, never ship (work order 16a). Short generated fields lose
    # the sentences that rest on atoms the corpus does not contain; findings in
    # the long prose are reported for a repair round instead, because cutting a
    # sentence out of the middle of an argument is its own kind of damage.
    stripped = strip_ungrounded_fields(briefing, grounding)
    if stripped:
        grounding = grounding_gate(briefing, raw_texts, harvest_texts)

    # D-036: the long prose used to stop at "reported". One repair round asks
    # the model about each invented atom in isolation and code splices the
    # answer in, so an invented figure is corrected or its clause cut rather
    # than reaching the reader with a flag on it.
    grounding_repairs = repair_grounding(briefing, grounding, raw_texts, client)
    if grounding_repairs.get("applied"):
        grounding = grounding_gate(briefing, raw_texts, harvest_texts)

    # ONE repair round of pairs (section J pass 8). The model writes a gloss per
    # name and code splices it in — it never sees the document back, so a repair
    # cannot quietly change a fact while fixing a name (D-024).
    intro_repair = repair_inline_introductions(briefing, client, ctx.topic)
    people = set(intro_repair.get("people") or []) if intro_repair.get("ran") else None
    if intro_repair.get("applied"):
        logger.info(
            f"[{ctx.job_id}] intro repair: {len(intro_repair['applied'])} "
            f"introduction(s) spliced, {len(intro_repair['unresolved'])} unresolved"
        )

    lint = lint_briefing(briefing, people=people)
    coverage = coverage_gate(briefing, inventory)
    logger.info(
        f"[{ctx.job_id}] briefing lint: {len(lint.errors)} error(s), "
        f"{len(lint.advisories)} advisory(ies)"
    )
    logger.info(f"[{ctx.job_id}] {coverage.summary()}")
    logger.info(f"[{ctx.job_id}] {grounding.summary()}")

    report = {
        "coverage": coverage.to_dict(),
        "grounding": grounding.to_dict(),
        "grounding_strips": stripped,
        "grounding_repairs": grounding_repairs,
        "skipped_files": skipped_files,
        "lint": lint.to_dict(),
        "intro_repair": intro_repair,
        "file_repairs": repairs,
    }
    return briefing, report


def stage_briefing(ctx: PipelineContext) -> None:
    """Pipeline stage: generate the Briefing and store it on the context.

    Non-fatal by design while the legacy documents still ship: a failed
    Briefing degrades to the old outputs plus a recorded warning rather than
    failing a job that already paid for its research.

    Args:
        ctx: Pipeline context, after harvest and synthesis.
    """
    settings = get_settings()
    packages = getattr(ctx, "source_identity_packages", [])
    if not packages:
        logger.info(f"[{ctx.job_id}] Briefing skipped: no sources")
        return

    update_job(ctx.job_id, stage="briefing")

    sources = [
        {
            "source_id": pkg.source_id,
            "title": pkg.title,
            "source_type": pkg.source_type,
            "creator": pkg.creator,
            "published": pkg.published,
            "full_text": pkg.content or "",
            "duplicate_of": (getattr(ctx, "duplicate_sources", {}) or {}).get(pkg.source_id),
        }
        for pkg in packages
    ]

    # Disputes are chosen by code from what the pipeline already found, never
    # by asking a model what is contested.
    key_points = {
        point.key_point_id: {
            "statement": point.statement,
            "source_ids": list(point.source_ids or []),
        }
        for extraction in getattr(ctx, "semantic_extractions", [])
        for point in getattr(extraction, "key_points", [])
    }
    disputes = select_disputes(
        claim_graph=getattr(ctx, "claim_graph", None),
        tensions=[
            tension
            for extraction in getattr(ctx, "semantic_extractions", [])
            for tension in getattr(extraction, "tensions", [])
        ],
        inventory=getattr(ctx, "harvest_inventory", []) or [],
        key_points=key_points,
    )

    try:
        # Provider-agnostic (D-034): the Briefing prose slot is env-driven like
        # every other slot, so it can move off a vendor without a code change.
        from backend.integrations.structured_client import get_structured_client

        client = get_structured_client(settings.model_distill)

        # Section 1 gets its own client (D-035). It is the only pass where a
        # model composes from raw text rather than filling slots code already
        # chose, and the only one where the model choice moved the measured
        # numbers. A failure to reach it degrades to the main client rather
        # than losing a Briefing the research has already been paid for.
        read_client = client
        if settings.model_read and settings.model_read != settings.model_distill:
            try:
                read_client = get_structured_client(settings.model_read)
                logger.info(f"[{ctx.job_id}] the Read routes to {settings.model_read}")
            except Exception as e:
                logger.warning(
                    f"[{ctx.job_id}] the Read cannot reach {settings.model_read} "
                    f"({e}); falling back to {settings.model_distill}"
                )

        briefing, report = build_briefing(
            ctx,
            client,
            sources,
            disputes_input=disputes,
            gaps=[g.to_dict() if hasattr(g, "to_dict") else g for g in getattr(ctx, "identified_gaps", [])],
            read_client=read_client,
        )
    except Exception as e:
        logger.error(f"[{ctx.job_id}] Briefing generation failed: {e}")
        ctx.add_warning(f"Briefing generation failed: {e}")
        return

    ctx.briefing = briefing
    ctx.briefing_report = report

    # The canonical artifact is the JSON; the HTML is the primary render and
    # the Markdown a lossy secondary export (D-025). All three travel with the
    # job so completion can store them without rebuilding anything.
    vault_html = render_source_vault(
        title=f"{ctx.topic[:60]} — sources",
        sources=sources,
        job_id=ctx.job_id,
        generated_on=briefing.meta.generated_on or "",
    )
    ctx.outputs["briefing"] = briefing.model_dump(mode="json")
    ctx.outputs["briefing_md"] = render_briefing_markdown(briefing)
    ctx.outputs["briefing_html"] = render_briefing_html(briefing)
    ctx.outputs["briefing_report"] = report
    ctx.outputs["source_vault_html"] = vault_html

    for finding in report["grounding"]["findings"][:10]:
        ctx.add_warning(
            f"Grounding: {finding['kind']} {finding['value']!r} in {finding['where']} "
            f"is not in any source"
        )
    for finding in report["coverage"]["findings"][:10]:
        ctx.add_warning(
            f"Coverage: {finding['where']} was harvested but never said"
        )
