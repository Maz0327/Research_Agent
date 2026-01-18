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
    JumpStartDirections,
    ResearchDirection,
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
            full_text=source_data.get("content"),
            full_text_unavailable_reason=(
                source_data.get("transcript_failure_reason")
                if not source_data.get("content") else None
            ),
            transcript_provenance=transcript_provenance,
            failure_reason=source_data.get("failure_reason"),
        )

        ledger.sources.append(entry)

    logger.info(f"Source Ledger built: {ledger.ingested_count} ingested, {ledger.failed_count} failed")
    return ledger


def build_jump_start(
    scope_lock: tuple[list[str], list[str]],
    extractions: list[SemanticExtractionResult],
    gaps: list[Gap],
) -> JumpStartDirections:
    """
    Build Doc 1: Jump-Start from extractions and identified gaps.

    Args:
        scope_lock: Tuple of (scope_in, scope_out) lists
        extractions: List of SemanticExtractionResult objects
        gaps: List of identified Gaps

    Returns:
        Assembled JumpStartDirections (Doc 1)
    """
    logger.info("Building Jump-Start directions...")

    scope_in, scope_out = scope_lock

    # Aggregate key points from all extractions
    all_key_points = []
    all_tensions = []
    perspectives = set()

    for extraction in extractions:
        all_key_points.extend(extraction.key_points)
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
        research_directions=research_directions[:5],  # Limit to top 5
        verification_items=verification_items[:10],  # Limit to 10
        next_steps=next_steps[:3],  # Always exactly 3
        confidence=confidence,
    )

    logger.info(f"Jump-Start built: {len(all_key_points)} key points, {len(gaps)} gaps")
    return jump_start


def build_semantic_brief(
    semantic_core: str,
    extractions: list[SemanticExtractionResult],
    gaps: list[Gap],
    overall_confidence: ConfidenceLevel,
    confidence_reasoning: list[str],
    source_contributions: dict | None = None,
    source_coverage: dict | None = None,
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
    )

    logger.info(f"Semantic Brief built: triage={triage.value}, confidence={overall_confidence.value}")
    return brief


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

    # Build Doc 1: Jump-Start
    doc_1 = build_jump_start(
        scope_lock=(scope_in, scope_out),
        extractions=extractions,
        gaps=gaps,
    )

    # Build Doc 2: Semantic Brief
    # Generate semantic core (in production, this comes from synthesis)
    semantic_core = (
        f"This research examines {ctx.topic}. "
        f"Analysis of {len(sources)} sources reveals "
        f"{len(doc_1.key_points)} key points across {len(doc_1.tensions)} areas of tension."
    )

    # Calibrate confidence
    confidence_reasoning = []
    if len(sources) >= 2:
        confidence_reasoning.append("Multiple sources available")
    else:
        confidence_reasoning.append("Single source limits perspective")

    if doc_0.failed_count > 0:
        confidence_reasoning.append(f"{doc_0.failed_count} sources failed ingestion")

    if len(doc_1.tensions) > 0:
        confidence_reasoning.append(f"{len(doc_1.tensions)} unresolved tensions")

    # Phase 5: Get source tracking from context if available
    source_contributions = getattr(ctx, "source_contributions", None)
    source_coverage = getattr(ctx, "source_coverage", None)

    doc_2 = build_semantic_brief(
        semantic_core=semantic_core,
        extractions=extractions,
        gaps=gaps,
        overall_confidence=doc_1.confidence,
        confidence_reasoning=confidence_reasoning,
        source_contributions=source_contributions,
        source_coverage=source_coverage,
    )

    # Store documents in context (dict format)
    ctx.source_ledger = doc_0.to_dict()
    ctx.jump_start = doc_1.to_dict()
    ctx.semantic_brief = doc_2.to_dict()

    # Also store in outputs for compatibility
    ctx.outputs["source_ledger"] = doc_0.to_dict()
    ctx.outputs["jump_start"] = doc_1.to_dict()
    ctx.outputs["semantic_brief"] = doc_2.to_dict()

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
