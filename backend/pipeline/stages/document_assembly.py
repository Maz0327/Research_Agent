"""
Document Assembly Stage - Generates the 3 canonical documents.

This stage constructs:
- Doc 0: Source Ledger (Canonical Data Layer)
- Doc 1: Jump-Start (Research Direction Layer)
- Doc 2: Semantic Research Brief (80% Output)

Based on: docs/authoritative/spec/Document_Output_Format.md

Assembly Order (per RASS Section 4.5):
1. DOC 0 — Source Ledger
2. DOC 1 — Jump-Start
3. DOC 2 — Semantic Research Brief

Rules:
- DOC 1 and DOC 2 may not introduce new data
- All references must trace to DOC 0
- If DOC 0 is thin → DOC 1 and DOC 2 must reflect this explicitly
"""

from typing import Any, Optional

from loguru import logger

from backend.models.document_outputs import (
    ConfidenceAssessment,
    CrossCuttingAnalysis,
    JumpStartDirections,
    ResearchDirection,
    ResearchThread,
    SemanticBrief,
    SourceEntry,
    SourceLedger,
    SourceStatus,
    TranscriptProvenance,
    TriageLevel,
    VerificationItem,
)
from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    Gap,
    KeyPoint,
    SemanticExtractionResult,
    Tension,
    Theme,
)
from backend.pipeline.context import PipelineContext
from backend.state import update_job


class RawTextContractError(Exception):
    """Raised when Doc 0 would ship without a source's raw text.

    Doc 0's `full_text` is the canonical raw layer: the Briefing's Section 1
    is generated from it, the Source Vault is rendered from it, and the
    grounding gate matches every hard atom against it. Losing it silently
    turns a research document into an unverifiable one, so loss is a hard
    failure, not a warning.
    """


def verify_raw_text_preserved(ledger: SourceLedger, sources: list[dict]) -> None:
    """Check that every source's raw text survived into Doc 0 intact.

    Two failure directions are checked. Loss: a source that arrived with
    content whose ledger entry has no `full_text`, or a shorter one (silent
    truncation). Silence: an entry with no text and no stated reason, which
    reads as "this source had nothing to say" when the truth is unknown.

    Args:
        ledger: The assembled Source Ledger.
        sources: The source dicts the ledger was built from.

    Raises:
        RawTextContractError: If any source's raw text was lost or truncated.
    """
    incoming = {s.get("source_id"): (s.get("content") or "") for s in sources}
    losses: list[str] = []

    for entry in ledger.sources:
        original = incoming.get(entry.source_id, "")
        preserved = entry.full_text or ""

        if original and not preserved:
            losses.append(f"{entry.source_id}: {len(original)} chars in, none in Doc 0")
        elif original and len(preserved) < len(original):
            losses.append(
                f"{entry.source_id}: truncated {len(original)} -> {len(preserved)} chars"
            )
        elif not preserved and not entry.full_text_unavailable_reason:
            # Not a loss, but an unexplained hole. Name it rather than let the
            # document imply the source was empty.
            entry.full_text_unavailable_reason = (
                entry.failure_reason or "No text was captured for this source"
            )

    if losses:
        raise RawTextContractError(
            "Doc 0 lost raw source text (Briefing Section 1, the Source Vault, "
            "and the grounding gate all read it): " + "; ".join(losses)
        )


def build_source_ledger(
    topic: str,
    sources: list[dict],
    extractions: list[SemanticExtractionResult],
) -> SourceLedger:
    """
    Build Doc 0: Source Ledger from ingested sources and extractions.

    Args:
        topic: Scope Lock sentence
        sources: List of raw source data dicts
        extractions: List of SemanticExtractionResult objects

    Returns:
        Assembled SourceLedger (Doc 0)
    """
    logger.info(f"Building Source Ledger for topic: {topic[:50]}...")

    ledger = SourceLedger(topic=topic)

    # Create extraction lookup by source_id
    extraction_map = {e.source_id: e for e in extractions}

    for source_data in sources:
        source_id = source_data.get("source_id", f"SRC_{len(ledger.sources) + 1}")
        extraction = extraction_map.get(source_id)

        # Determine status
        if source_data.get("failed"):
            status = SourceStatus.FAILED
        elif extraction and extraction.parse_error:
            status = SourceStatus.PARTIAL
        else:
            status = SourceStatus.INGESTED

        # Build transcript provenance for video sources
        # Note: Articles, Reddit, and other text sources don't have transcript provenance -
        # their provenance is captured in the source metadata (author, url, etc.) rather
        # than transcript chain (supadata → whisper → captions fallback).
        transcript_provenance = None
        if source_data.get("source_type") == "youtube":
            ts = source_data.get("transcript_source", "none")
            mode = AnalysisMode.VIDEO_ONLY

            if ts in ("supadata", "whisper"):
                mode = AnalysisMode.TRANSCRIPT_GROUNDED
            elif ts == "youtube_captions":
                mode = AnalysisMode.CAPTION_GROUNDED

            transcript_provenance = TranscriptProvenance(
                transcript_source=ts,
                transcript_status="success" if ts != "none" else "failed",
                captions_status=source_data.get("captions_status", "missing"),
                gemini_analysis_mode=mode,
                quote_verification=mode == AnalysisMode.TRANSCRIPT_GROUNDED,
                timestamp_grounding=mode != AnalysisMode.VIDEO_ONLY,
                semantic_precision=(
                    ConfidenceLevel.HIGH if mode == AnalysisMode.TRANSCRIPT_GROUNDED
                    else ConfidenceLevel.MEDIUM if mode == AnalysisMode.CAPTION_GROUNDED
                    else ConfidenceLevel.LOW
                ),
                notes=source_data.get("transcript_notes"),
            )

        # Build skim summary from extraction if available
        skim_summary = []
        if extraction:
            # Use first few key points as skim summary
            for kp in extraction.key_points[:5]:
                skim_summary.append(kp.statement)

        # Collect claim and theme IDs
        claim_ids = []
        theme_ids = []
        if extraction:
            claim_ids = [c.claim_id for c in extraction.claims]
            theme_ids = [t.theme_id for t in extraction.themes]

        # Build source entry
        entry = SourceEntry(
            source_id=source_id,
            source_type=source_data.get("source_type", "unknown"),
            title=source_data.get("title", "Untitled"),
            url=source_data.get("url", ""),
            status=status,
            creator=source_data.get("creator"),
            published=source_data.get("published"),
            duration=source_data.get("duration"),
            word_count=source_data.get("word_count"),
            skim_summary=skim_summary,
            claim_ids=claim_ids,
            entity_names=source_data.get("entities", []),
            theme_ids=theme_ids,
            # Empty string would read as "this source said nothing"; an absent
            # value plus a stated reason is the honest form.
            full_text=source_data.get("content") or None,
            full_text_unavailable_reason=(
                (
                    source_data.get("transcript_failure_reason")
                    or source_data.get("failure_reason")
                )
                if not source_data.get("content") else None
            ),
            transcript_provenance=transcript_provenance,
            failure_reason=source_data.get("failure_reason"),
        )

        ledger.sources.append(entry)

    verify_raw_text_preserved(ledger, sources)

    with_text = sum(1 for e in ledger.sources if e.full_text)
    raw_words = sum(len((e.full_text or "").split()) for e in ledger.sources)
    logger.info(
        f"Source Ledger built: {ledger.ingested_count} ingested, "
        f"{ledger.failed_count} failed, {with_text}/{len(ledger.sources)} with raw "
        f"text ({raw_words:,} words)"
    )
    return ledger


def build_jump_start(
    scope_lock: tuple[list[str], list[str]],
    extractions: list[SemanticExtractionResult],
    gaps: list[Gap],
    source_coverage: dict | None = None,
) -> JumpStartDirections:
    """
    Build Doc 1: Jump-Start from extractions and identified gaps.

    Groups key points by theme into ResearchThreads, attaches gaps and
    research directions inline, and builds cross-cutting analysis from
    Phase 5 source_coverage data.

    Args:
        scope_lock: Tuple of (scope_in, scope_out) lists
        extractions: List of SemanticExtractionResult objects
        gaps: List of identified Gaps
        source_coverage: Optional Phase 5 map of key_point_id -> [source_ids]

    Returns:
        Assembled JumpStartDirections (Doc 1)
    """
    logger.info("Building Jump-Start directions...")

    scope_in, scope_out = scope_lock

    # Aggregate all semantic units from all extractions
    all_key_points = []
    all_themes = []
    all_tensions = []
    perspectives = set()

    for extraction in extractions:
        all_key_points.extend(extraction.key_points)
        all_themes.extend(extraction.themes)
        all_tensions.extend(extraction.tensions)
        perspectives.add(extraction.source_id)

    # Build research directions from gaps
    research_directions = []
    for i, gap in enumerate(gaps, 1):
        direction = ResearchDirection(
            priority=i,
            what_to_look_for=gap.description,
            example_queries=[gap.suggested_research_direction] if gap.suggested_research_direction else [],
            why_it_matters=gap.why_expected,
        )
        research_directions.append(direction)

    # Build verification items from claims needing verification
    verification_items = []
    for extraction in extractions:
        for claim in extraction.claims:
            if claim.confidence == ConfidenceLevel.LOW or not claim.supporting_quotes:
                verification_items.append(VerificationItem(
                    item_id=f"VER_{len(verification_items) + 1}",
                    description=f"Verify: {claim.statement[:100]}...",
                    status="pending",
                ))

    # ---- THEMATIC GROUPING ----
    # Build lookup maps
    kp_map: dict[str, KeyPoint] = {kp.key_point_id: kp for kp in all_key_points}
    gap_map: dict[str, Gap] = {g.gap_id: g for g in gaps}
    # Map gap_id -> ResearchDirection (keyed by gap_id for uniqueness)
    rd_map: dict[str, ResearchDirection] = {}
    for gap_obj, rd in zip(gaps, research_directions):
        rd_map[gap_obj.gap_id] = rd

    # Track which KPs and gaps have been assigned to a thread
    assigned_kp_ids: set[str] = set()
    assigned_gap_ids: set[str] = set()

    research_threads: list[ResearchThread] = []

    for theme in all_themes:
        # Find key points for this theme
        thread_kps = []
        for kp_id in theme.related_key_points:
            if kp_id in kp_map:
                thread_kps.append(kp_map[kp_id])
                assigned_kp_ids.add(kp_id)

        # Find gaps related to this theme
        thread_gaps = []
        for gap in gaps:
            if gap.gap_id in assigned_gap_ids:
                continue
            # Match by related_themes or by overlapping key points
            theme_match = theme.theme_id in (gap.related_themes or [])
            kp_overlap = bool(
                set(gap.related_key_points or []) & set(theme.related_key_points or [])
            )
            if theme_match or kp_overlap:
                thread_gaps.append(gap)
                assigned_gap_ids.add(gap.gap_id)

        # Find research directions for these gaps
        thread_rds = []
        for gap in thread_gaps:
            if gap.gap_id in rd_map:
                thread_rds.append(rd_map[gap.gap_id])

        # Enrich theme with Phase 5 data if available
        if source_coverage and len(extractions) > 1:
            theme_sources = set()
            for kp_id in theme.related_key_points:
                if kp_id in source_coverage:
                    theme_sources.update(source_coverage[kp_id])
            theme.sources_supporting = list(theme_sources)
            theme.is_consensus = len(theme_sources) >= 2

        research_threads.append(ResearchThread(
            theme=theme,
            key_points=thread_kps,
            gaps=thread_gaps,
            research_directions=thread_rds,
        ))

    # Handle orphan KPs (not assigned to any theme)
    orphan_kps = [kp for kp in all_key_points if kp.key_point_id not in assigned_kp_ids]
    orphan_gaps = [g for g in gaps if g.gap_id not in assigned_gap_ids]

    if orphan_kps or orphan_gaps:
        general_theme = Theme(
            theme_id="THEME_GENERAL",
            label="General Findings",
            description="Key points and gaps not yet associated with a specific research thread.",
            related_key_points=[kp.key_point_id for kp in orphan_kps],
        )
        orphan_rds = [
            rd_map[g.gap_id] for g in orphan_gaps
            if g.gap_id in rd_map
        ]
        research_threads.append(ResearchThread(
            theme=general_theme,
            key_points=orphan_kps,
            gaps=orphan_gaps,
            research_directions=orphan_rds,
        ))

    # ---- CROSS-CUTTING ANALYSIS ----
    cross_cutting = None
    if source_coverage and len(extractions) > 1:
        confirmed = []
        single_source = []

        for kp in all_key_points:
            sources = source_coverage.get(kp.key_point_id, kp.source_ids or [])
            if len(sources) >= 2:
                confirmed.append({
                    "statement": kp.statement,
                    "sources": list(sources),
                })
            elif len(sources) == 1:
                single_source.append({
                    "statement": kp.statement,
                    "source": list(sources)[0],
                })

        conflicts = []
        for tension in all_tensions:
            if getattr(tension, "is_cross_source", False):
                conflicts.append({
                    "description": tension.description,
                    "sources_a": getattr(tension, "sources_position_a", []),
                    "sources_b": getattr(tension, "sources_position_b", []),
                })

        cross_cutting = CrossCuttingAnalysis(
            confirmed=confirmed,
            conflicts=conflicts,
            single_source=single_source,
        )

    # Generate next steps
    next_steps = []
    if gaps:
        next_steps.append(f"Address gap: {gaps[0].description}")
    if all_tensions:
        next_steps.append(f"Resolve tension: {all_tensions[0].description}")
    if verification_items:
        next_steps.append(f"Verify {len(verification_items)} unconfirmed claims")
    if len(next_steps) < 3:
        next_steps.append("Review source ledger for additional context")

    # Determine confidence
    confidence = ConfidenceLevel.MEDIUM
    if len(extractions) >= 2 and len(gaps) <= 5:
        confidence = ConfidenceLevel.HIGH
    elif len(extractions) == 1 or len(gaps) > 7:
        confidence = ConfidenceLevel.LOW

    jump_start = JumpStartDirections(
        scope_in=scope_in,
        scope_out=scope_out,
        source_count=len(extractions),
        perspectives_represented=list(perspectives),
        key_points=all_key_points,
        tensions=all_tensions,
        gaps=gaps,
        research_directions=research_directions[:5],
        verification_items=verification_items[:10],
        next_steps=next_steps[:3],
        confidence=confidence,
        research_threads=research_threads,
        cross_cutting=cross_cutting,
    )

    logger.info(
        f"Jump-Start built: {len(all_key_points)} key points, "
        f"{len(research_threads)} threads, {len(gaps)} gaps"
    )
    return jump_start


def merge_booster_into_threads_dict(
    jump_start_dict: dict,
    booster_output_dict: dict,
) -> dict:
    """
    Map booster output items into their corresponding research threads by
    matching gap_id and theme_id references.

    Operates on dict representations (as stored in artifacts) so it can be
    called from worker.py after booster completes without reconstructing
    full dataclass objects.

    Items that don't match any thread are collected into a synthetic
    "General Research Directions" thread.

    Args:
        jump_start_dict: Doc 1 as dict (with research_threads key)
        booster_output_dict: BoosterOutput as dict

    Returns:
        Updated jump_start_dict with booster items folded into threads
    """
    threads = jump_start_dict.get("research_threads", [])
    if not threads:
        logger.info("No research threads to merge booster into — skipping")
        return jump_start_dict

    # Build lookup maps: theme_id -> thread index, gap_id -> thread index
    theme_to_idx: dict[str, int] = {}
    gap_to_idx: dict[str, int] = {}

    for idx, thread in enumerate(threads):
        theme_data = thread.get("theme", {})
        tid = theme_data.get("theme_id", "")
        if tid:
            theme_to_idx[tid] = idx
        for gap in thread.get("gaps", []):
            gid = gap.get("gap_id", "")
            if gid:
                gap_to_idx[gid] = idx

    # Initialize booster lists on each thread if not present
    for thread in threads:
        thread.setdefault("booster_search_queries", [])
        thread.setdefault("booster_research_questions", [])
        thread.setdefault("booster_primary_sources", [])
        thread.setdefault("booster_missing_perspectives", [])

    unmatched_queries = []
    unmatched_questions = []
    unmatched_sources = []
    unmatched_perspectives = []

    # Map search queries
    for sq in booster_output_dict.get("suggested_search_queries", []):
        matched = False
        rt = sq.get("related_theme")
        rg = sq.get("related_gap")
        if rt and rt in theme_to_idx:
            threads[theme_to_idx[rt]]["booster_search_queries"].append(sq)
            matched = True
        elif rg and rg in gap_to_idx:
            threads[gap_to_idx[rg]]["booster_search_queries"].append(sq)
            matched = True
        if not matched:
            unmatched_queries.append(sq)

    # Map research questions
    for rq in booster_output_dict.get("research_questions", []):
        matched = False
        rt = rq.get("related_theme")
        if rt and rt in theme_to_idx:
            threads[theme_to_idx[rt]]["booster_research_questions"].append(rq)
            matched = True
        if not matched:
            unmatched_questions.append(rq)

    # Map primary source directions
    for psd in booster_output_dict.get("primary_source_directions", []):
        matched = False
        rg = psd.get("related_gap")
        if rg and rg in gap_to_idx:
            threads[gap_to_idx[rg]]["booster_primary_sources"].append(psd)
            matched = True
        if not matched:
            unmatched_sources.append(psd)

    # Map missing perspectives
    for mp in booster_output_dict.get("missing_perspectives", []):
        matched = False
        for rg in (mp.get("related_gaps") or []):
            if rg in gap_to_idx:
                threads[gap_to_idx[rg]]["booster_missing_perspectives"].append(mp)
                matched = True
                break
        if not matched:
            unmatched_perspectives.append(mp)

    # Create General Research Directions thread for unmatched items
    if unmatched_queries or unmatched_questions or unmatched_sources or unmatched_perspectives:
        general_thread = {
            "theme": {
                "theme_id": "THEME_BOOSTER_GENERAL",
                "label": "General Research Directions",
                "description": "Research directions from the Deep Research Booster that apply broadly across the topic.",
                "related_key_points": [],
            },
            "key_points": [],
            "gaps": [],
            "research_directions": [],
            "booster_search_queries": unmatched_queries,
            "booster_research_questions": unmatched_questions,
            "booster_primary_sources": unmatched_sources,
            "booster_missing_perspectives": unmatched_perspectives,
        }
        threads.append(general_thread)

    jump_start_dict["research_threads"] = threads

    total_merged = (
        len(booster_output_dict.get("suggested_search_queries", []))
        + len(booster_output_dict.get("research_questions", []))
        + len(booster_output_dict.get("primary_source_directions", []))
        + len(booster_output_dict.get("missing_perspectives", []))
    )
    total_unmatched = (
        len(unmatched_queries) + len(unmatched_questions)
        + len(unmatched_sources) + len(unmatched_perspectives)
    )
    logger.info(
        f"Booster merge: {total_merged} items total, "
        f"{total_merged - total_unmatched} matched to threads, "
        f"{total_unmatched} in General"
    )

    return jump_start_dict


def build_semantic_brief(
    semantic_core: str,
    extractions: list[SemanticExtractionResult],
    gaps: list[Gap],
    overall_confidence: ConfidenceLevel,
    confidence_reasoning: list[str],
    source_contributions: dict | None = None,
    source_coverage: dict | None = None,
    topic: str = "",
) -> SemanticBrief:
    """
    Build Doc 2: Semantic Research Brief from synthesis results.

    Args:
        semantic_core: 2-4 sentence description of topic's core
        extractions: List of SemanticExtractionResult objects
        gaps: List of identified Gaps
        overall_confidence: Calibrated confidence level
        confidence_reasoning: List of reasons for confidence level
        source_contributions: Optional dict mapping source_id → {key_points, claims, ...} (Phase 5)
        source_coverage: Optional dict mapping key_point_id → [source_ids] (Phase 5)
        topic: Research topic string for SCQA generation

    Returns:
        Assembled SemanticBrief (Doc 2)
    """
    logger.info("Building Semantic Research Brief...")

    # Aggregate semantic units
    all_key_points = []
    all_themes = []
    all_tensions = []
    based_on_kps = []

    for extraction in extractions:
        all_key_points.extend(extraction.key_points)
        all_themes.extend(extraction.themes)
        all_tensions.extend(extraction.tensions)

        if extraction.key_points:
            based_on_kps.append(extraction.key_points[0].key_point_id)

    # Phase 5: Enrich themes with source attribution
    if source_coverage and len(extractions) > 1:
        for theme in all_themes:
            # Collect unique source IDs from related key points
            theme_sources = set()
            for kp_id in theme.related_key_points:
                if kp_id in source_coverage:
                    theme_sources.update(source_coverage[kp_id])
            theme.sources_supporting = list(theme_sources)
            theme.is_consensus = len(theme_sources) >= 2

    # Phase 5: Mark cross-source tensions
    if source_coverage and len(extractions) > 1:
        for tension in all_tensions:
            tension_sources = set()
            for kp_id in tension.involved_key_points:
                if kp_id in source_coverage:
                    tension_sources.update(source_coverage[kp_id])
            if len(tension_sources) > 1:
                tension.is_cross_source = True
                # Split sources into positions (simple split for now)
                sources_list = list(tension_sources)
                mid = len(sources_list) // 2 or 1
                tension.sources_position_a = sources_list[:mid]
                tension.sources_position_b = sources_list[mid:]

    # Determine triage level
    triage = TriageLevel.USABLE
    issues = []

    if len(all_key_points) < 8:
        issues.append(f"Only {len(all_key_points)} key points (minimum 8)")
    if len(all_themes) < 4:
        issues.append(f"Only {len(all_themes)} themes (minimum 4)")
    if len(gaps) < 5:
        issues.append(f"Only {len(gaps)} gaps (minimum 5)")

    if len(issues) > 2:
        triage = TriageLevel.THIN
    elif len(issues) > 0:
        triage = TriageLevel.USABLE

    # Check for degraded sources
    degraded_sources = sum(
        1 for e in extractions
        if e.analysis_mode in (AnalysisMode.VIDEO_ONLY, AnalysisMode.CAPTION_GROUNDED)
    )
    if degraded_sources > len(extractions) / 2:
        triage = TriageLevel.DEGRADED

    # R6: Build SCQA programmatically from existing data
    scqa = {}
    topic_str = topic or "this topic"
    scqa["situation"] = f"You're researching {topic_str}."
    # Complication: Most significant tension or gap
    if all_tensions:
        scqa["complication"] = all_tensions[0].description
    elif gaps:
        scqa["complication"] = f"There are {len(gaps)} gaps in what the sources cover."
    else:
        scqa["complication"] = "No major disagreements found across sources."
    # Question: Direct, not academic
    if all_themes:
        theme_label = all_themes[0].label.lower()
        scqa["question"] = (
            f"What do the sources actually tell you about {theme_label}?"
        )
    # Answer: The semantic core itself
    scqa["answer"] = semantic_core

    # Build source_ids list for heatmap
    source_id_list = list({
        sid
        for e in extractions
        for sid in ([e.source_id] if hasattr(e, "source_id") and e.source_id else [])
    })

    brief = SemanticBrief(
        semantic_core=semantic_core,
        semantic_core_based_on=based_on_kps[:3],
        themes=all_themes,
        key_points=all_key_points,
        tensions=all_tensions,
        gaps=gaps,
        confidence=ConfidenceAssessment(
            level=overall_confidence,
            reasoning=confidence_reasoning,
        ),
        speculative_observations=[],  # Populated by synthesis if needed
        triage=triage,
        warnings=issues,
        scqa=scqa,
        source_ids=source_id_list,
        source_coverage=source_coverage,
    )

    logger.info(f"Semantic Brief built: triage={triage.value}, confidence={overall_confidence.value}")
    return brief


def generate_executive_summary(
    jump_start: JumpStartDirections,
    semantic_brief: SemanticBrief,
    producer_packet: dict | None = None,
) -> str:
    """Generate a cross-document executive summary (R15).

    This is 100% programmatic — no LLM call.
    Computes summary from existing data structures.

    Args:
        jump_start: Doc 1 data
        semantic_brief: Doc 2 data
        producer_packet: Optional Doc 3 data (as dict)

    Returns:
        Markdown string for executive summary
    """
    parts: list[str] = []

    # What was researched
    thread_count = len(jump_start.research_threads)
    kp_count = len(jump_start.key_points)
    parts.append(
        f"Researched using **{jump_start.source_count} sources** "
        f"covering **{thread_count} themes** "
        f"with **{kp_count} key findings**."
    )

    # Core insight
    if semantic_brief.semantic_core:
        parts.append(f"**Core insight:** {semantic_brief.semantic_core}")

    # Consensus state
    if jump_start.cross_cutting:
        confirmed = len(jump_start.cross_cutting.confirmed)
        conflicts = len(jump_start.cross_cutting.conflicts)
        single = len(jump_start.cross_cutting.single_source)
        if confirmed > 0 and conflicts == 0:
            parts.append(
                f"**{confirmed} claims confirmed** across sources with no active disputes."
            )
        elif confirmed > 0 and conflicts > 0:
            parts.append(
                f"**{confirmed} claims confirmed** across sources, "
                f"**{conflicts} active tension{'s' if conflicts > 1 else ''}** "
                f"where sources disagree."
            )
        elif single > 0:
            parts.append(
                f"Limited cross-source verification — "
                f"**{single} claims** backed by a single source only."
            )

    # Recommended angle (if producer ran)
    if producer_packet:
        rec_angle_id = producer_packet.get("recommended_angle_id")
        angles = producer_packet.get("narrative_angles", [])
        reasoning = producer_packet.get("recommendation_reasoning", "")
        if rec_angle_id and angles:
            angle = next(
                (a for a in angles if a.get("angle_id") == rec_angle_id),
                None,
            )
            if angle:
                conf = angle.get("confidence", "")
                conf_str = f" ({conf} confidence)" if conf else ""
                parts.append(
                    f"**Recommended angle:** {angle.get('title', rec_angle_id)}{conf_str}."
                )
                if reasoning:
                    parts.append(f"*{reasoning}*")

    # Top priority next step
    if jump_start.research_directions:
        rd = jump_start.research_directions[0]
        parts.append(f"**Next step:** {rd.what_to_look_for}")

    # Gap count
    gap_count = len(jump_start.gaps)
    if gap_count > 0:
        parts.append(
            f"**{gap_count} gap{'s' if gap_count > 1 else ''}** identified "
            f"where additional research would strengthen the analysis."
        )

    # Confidence
    conf_map = {
        "high": "🟢 High",
        "medium": "🟡 Medium",
        "low": "🔴 Low",
    }
    conf_badge = conf_map.get(jump_start.confidence.value, jump_start.confidence.value)
    parts.append(f"Overall confidence: {conf_badge}.")

    return "\n\n".join(parts)


def validate_provenance_chain(ctx: PipelineContext) -> list[str]:
    """
    Validate all references trace back to Doc 0.

    Per Validation_and_Retry_Rules.md V8:
    - Theme.related_key_points → must exist in key_points
    - KeyPoint.source_ids → must exist in sources
    - Tension.involved_key_points → must exist in key_points

    Args:
        ctx: Pipeline context with source_identity_packages and semantic_extractions

    Returns:
        List of warning messages for broken references
    """
    warnings = []

    # Collect valid source IDs from source_identity_packages
    valid_source_ids = set()
    for pkg in getattr(ctx, "source_identity_packages", []):
        valid_source_ids.add(pkg.source_id)

    # Collect valid key point IDs and validate source references
    valid_kp_ids = set()
    for extraction in getattr(ctx, "semantic_extractions", []):
        # Validate key points have valid source references
        for kp in extraction.key_points:
            valid_kp_ids.add(kp.key_point_id)
            for sid in kp.source_ids:
                if sid not in valid_source_ids:
                    warnings.append(
                        f"KeyPoint {kp.key_point_id} references invalid source {sid}"
                    )
                    logger.warning(f"Provenance: {warnings[-1]}")

        # Validate themes reference valid key points
        for theme in extraction.themes:
            for kp_id in theme.related_key_points:
                if kp_id not in valid_kp_ids:
                    warnings.append(
                        f"Theme {theme.theme_id} references invalid key_point {kp_id}"
                    )
                    logger.warning(f"Provenance: {warnings[-1]}")

        # Validate tensions reference valid key points
        for tension in extraction.tensions:
            for kp_id in tension.involved_key_points:
                if kp_id not in valid_kp_ids:
                    warnings.append(
                        f"Tension {tension.tension_id} references invalid key_point {kp_id}"
                    )
                    logger.warning(f"Provenance: {warnings[-1]}")

    if warnings:
        logger.warning(f"Provenance validation found {len(warnings)} broken references")
    else:
        logger.debug("Provenance validation passed - all references valid")

    return warnings


def stage_document_assembly(ctx: PipelineContext) -> dict:
    """
    Pipeline stage: Assemble the 3 canonical documents.

    PREREQUISITE: source_identity and semantic_extraction stages must run first.

    This stage:
    1. Validates provenance chain (V8)
    2. Builds Doc 0 (Source Ledger) from source_identity_packages
    3. Builds Doc 1 (Jump-Start) from extractions and gaps
    4. Builds Doc 2 (Semantic Brief) from synthesis

    Returns:
        Dict containing all three documents
    """
    logger.info(f"[{ctx.job_id}] Stage: Document Assembly")

    update_job(
        ctx.job_id,
        stage="document_assembly",
        progress_percent=70,
    )

    # V8: Validate provenance chain before document assembly
    provenance_warnings = validate_provenance_chain(ctx)
    for warning in provenance_warnings:
        ctx.add_warning(warning)

    if provenance_warnings:
        logger.warning(
            f"[{ctx.job_id}] Provenance validation: {len(provenance_warnings)} issues found"
        )

    # Get source identity packages (from source_identity stage)
    packages = getattr(ctx, "source_identity_packages", [])

    # Convert packages to source dicts for build_source_ledger
    sources = []
    for pkg in packages:
        sources.append({
            "source_id": pkg.source_id,
            "source_type": pkg.source_type,
            "title": pkg.title,
            "url": pkg.url,
            "creator": pkg.creator,
            "published": pkg.published,
            "duration": f"{pkg.duration_seconds}s" if pkg.duration_seconds else None,
            "word_count": pkg.content_word_count,
            "content": pkg.content,
            "transcript_source": pkg.transcript_source,
            "failed": not pkg.is_accessible,
            "failure_reason": pkg.failure_reason,
            "captions_status": "success" if pkg.transcript_source == "youtube_captions" else "missing",
        })

    extractions = getattr(ctx, "semantic_extractions", [])
    gaps = getattr(ctx, "identified_gaps", [])
    scope_in = getattr(ctx, "scope_in", ["Research topic"])
    scope_out = getattr(ctx, "scope_out", ["Unrelated topics"])

    # Build Doc 0: Source Ledger
    doc_0 = build_source_ledger(
        topic=ctx.topic,
        sources=sources,
        extractions=extractions,
    )

    # Build Doc 1: Jump-Start (with thematic grouping)
    source_coverage = getattr(ctx, "source_coverage", None)
    doc_1 = build_jump_start(
        scope_lock=(scope_in, scope_out),
        extractions=extractions,
        gaps=gaps,
        source_coverage=source_coverage,
    )

    # Build Doc 2: Semantic Brief
    # Use real semantic_core from synthesis stage if available
    semantic_core = getattr(ctx, "semantic_core", "")
    if not semantic_core:
        # Fallback template only when synthesis didn't produce one
        semantic_core = (
            f"This research examines {ctx.topic}. "
            f"Analysis of {len(sources)} sources reveals "
            f"{len(doc_1.key_points)} key points across "
            f"{len(doc_1.tensions)} areas of tension."
        )

    # Calibrate confidence — deterministic formula, not vibes
    total_sources = len(sources)
    failed_sources = doc_0.failed_count
    tension_count = len(doc_1.tensions)

    # Determine confidence level based on hard thresholds
    if failed_sources / max(total_sources, 1) > 0.3:
        # >30% sources failed = never HIGH
        overall_confidence = ConfidenceLevel.LOW
    elif tension_count > 10 or total_sources < 2:
        # Many tensions or single source = cap at MEDIUM
        overall_confidence = ConfidenceLevel.MEDIUM
    else:
        # Use synthesis stage assessment
        overall_confidence = doc_1.confidence

    # Build reasoning from facts, not generic statements
    confidence_reasoning = []
    if failed_sources > 0:
        confidence_reasoning.append(
            f"{failed_sources}/{total_sources} sources failed ingestion"
        )
    if total_sources >= 3:
        confidence_reasoning.append(
            f"{total_sources} sources provide reasonable coverage"
        )
    elif total_sources == 1:
        confidence_reasoning.append("Single source limits perspective")
    if tension_count > 8:
        confidence_reasoning.append(
            f"{tension_count} unresolved tensions — contested topic"
        )
    elif tension_count > 0:
        confidence_reasoning.append(
            f"{tension_count} unresolved tension{'s' if tension_count != 1 else ''}"
        )

    # Phase 5: Get source tracking from context if available
    source_contributions = getattr(ctx, "source_contributions", None)
    source_coverage = getattr(ctx, "source_coverage", None)

    doc_2 = build_semantic_brief(
        semantic_core=semantic_core,
        extractions=extractions,
        gaps=gaps,
        overall_confidence=overall_confidence,
        confidence_reasoning=confidence_reasoning,
        source_contributions=source_contributions,
        source_coverage=source_coverage,
        topic=ctx.topic,
    )

    # Store documents in context (dict format)
    ctx.source_ledger = doc_0.to_dict()
    ctx.jump_start = doc_1.to_dict()
    ctx.semantic_brief = doc_2.to_dict()

    # Also store in outputs for compatibility
    ctx.outputs["source_ledger"] = doc_0.to_dict()
    ctx.outputs["jump_start"] = doc_1.to_dict()
    ctx.outputs["semantic_brief"] = doc_2.to_dict()

    # R15: Generate cross-document executive summary (programmatic, no LLM)
    producer_packet_data = getattr(ctx, "producer_packet", None)
    executive_summary = generate_executive_summary(doc_1, doc_2, producer_packet_data)
    ctx.outputs["executive_summary"] = executive_summary

    # Also store markdown versions
    ctx.outputs["source_ledger_md"] = doc_0.to_markdown()
    ctx.outputs["jump_start_md"] = doc_1.to_markdown()
    ctx.outputs["semantic_brief_md"] = doc_2.to_markdown()

    # Update job with document assembly summary
    update_job(
        ctx.job_id,
        partial_outputs={
            "document_assembly_summary": {
                "doc_0_sources": len(doc_0.sources),
                "doc_1_key_points": len(doc_1.key_points),
                "doc_1_gaps": len(doc_1.gaps),
                "doc_2_themes": len(doc_2.themes),
                "doc_2_triage": doc_2.triage.value,
            }
        },
    )

    result = {
        "source_ledger": doc_0,
        "jump_start": doc_1,
        "semantic_brief": doc_2,
    }

    logger.info(
        f"Document assembly complete: "
        f"Doc 0 ({doc_0.ingested_count} sources), "
        f"Doc 1 ({len(doc_1.gaps)} gaps), "
        f"Doc 2 ({doc_2.triage.value})"
    )

    return result
