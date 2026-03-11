"""Claim Extraction Pipeline for the Claim Extractor feature.

This module handles extracting claims from various source types:
- YouTube videos (with timestamp anchors if timing available, else line anchors)
- Articles/URLs (with line range anchors)
- User-provided text (with line range anchors)
- Screenshots (with image index anchors)

Key Design Decisions:
- NO claim verification - extraction only
- NO source retrieval - only analyze provided inputs
- Claims have anchors to locate them in source material
- Output stored as ClaimsDocument in Supabase Storage

Claim Extractor v2 Updates (2026-01-27):
- NO GUESSED TIMESTAMPS: If transcript_segments lack timing, use line anchors
- Entity extraction with excerpt+anchor evidence
- Warning codes for anchor coercion
- Run-scoped claims_doc generation support
"""
from datetime import datetime, timezone
from typing import Any, Optional, Callable

from loguru import logger

from backend.models.claims import (
    AnchorType,
    Claim,
    ClaimAnchor,
    ClaimCluster,
    ClaimInstance,
    ClaimRelation,
    ClaimRelationType,
    ClaimType,
    ClaimsDocument,
    ClaimsDocumentMetadata,
    ConfidenceLevel,
    ContextEvidence,
    Entity,
    EntityIndex,
    EntityType,
    ExtractionWarning,
    ImageAnchor,
    LineRangeAnchor,
    RhetoricalFraming,
    SourceSummary,
    SourceType,
    TimestampAnchor,
    WarningCode,
)


# Prompt templates for claim extraction

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are a claim extraction specialist. Your job is to identify ALL claims made in the provided content.

A claim is any statement that:
1. Asserts something is true or false
2. Makes a factual statement (even if unverified)
3. Expresses an opinion presented as fact
4. Implies something through context

Types of claims:
- EXPLICIT: Directly stated in the content
- IMPLIED: Not directly stated but clearly suggested by the context

For each claim, you must:
1. Extract the exact claim statement
2. Classify it as explicit or implied
3. Assign a confidence level (high/medium/low) based on clarity
4. Provide an anchor (location reference) in the source

ENRICHMENT REQUIREMENTS (v3):
- SPEAKER: Identify who is making each claim. Use the person's name if attributed ("Tim Cook said..."), "the author" for article claims with no attribution, "narrator" for video narration, or "unknown" if unclear. The speaker is the CLAIMANT, not just someone mentioned.
- FRAMING: Classify how the claim is presented:
  * stated_as_fact — presented as established truth with no hedging
  * opinion — clearly an editorial opinion or judgment
  * disputed — acknowledged as contested or controversial in the text
  * speculative — forward-looking, uncertain ("may", "expected to", "could")
  * attributed — explicitly cited from a named source ("according to X")
  * hedged — qualified with caveats ("approximately", "sources say", "believed to be")
- SIGNIFICANCE: One sentence on why the claim matters or what it implies. Focus on context, consequences, or scale.
- TAGS: 1-3 topic categories (e.g., "financial", "technology", "political", "employment", "legal", "health", "environmental", "military", "social").

IMPORTANT RULES:
- Extract ALL claims, not just controversial ones
- Do NOT verify claims - just extract them
- Do NOT add claims not present in the source
- Include both major and minor claims
- Be thorough - missing claims is worse than over-extracting"""

# V2: YouTube extraction with timed segments (timestamps allowed)
YOUTUBE_EXTRACTION_TIMED_PROMPT = """Analyze this YouTube video transcript and extract ALL claims AND entities.

VIDEO TITLE: {title}
VIDEO URL: {url}
SOURCE_ID: {source_id}

TIMED TRANSCRIPT SEGMENTS:
{transcript_segments}

EXTRACTION RULES:
1. For each claim, provide a verbatim_excerpt from the transcript (up to 500 chars)
2. timestamp_start/end MUST be within the segment time bounds provided
3. Extract ALL named entities (people, organizations, places)
4. For unnamed entities ("their founders", "a senior official"), create entries in unnamed_entities
5. Identify the SPEAKER for each claim — who is making or asserting the claim
6. Classify the rhetorical FRAMING of each claim
7. Explain the SIGNIFICANCE of each claim in one sentence
8. Assign 1-3 topic TAGS to categorize each claim

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string (paraphrased claim statement)",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "timestamp_start": number (seconds, must match segment bounds),
      "timestamp_end": number | null,
      "verbatim_excerpt": "string (exact text from transcript, up to 500 chars)",
      "context": "string (2-4 sentences of surrounding context)",
      "entities_mentioned": ["entity_label", ...],
      "speaker": "string (who is making this claim — speaker name if identifiable, 'narrator' if unknown)",
      "framing": "stated_as_fact" | "opinion" | "disputed" | "speculative" | "attributed" | "hedged",
      "significance": "string (one sentence explaining why this claim matters)",
      "tags": ["string (1-3 topic tags like 'financial', 'technology', 'political')"]
    }}
  ],
  "entities": {{
    "people": [
      {{
        "label": "string",
        "context_summary": "string (1-2 sentences about who they are)",
        "excerpt": "string (verbatim from transcript)",
        "timestamp_start": number
      }}
    ],
    "orgs": [...],
    "places": [...],
    "unnamed": [
      {{
        "label": "string (e.g., 'their founders', 'a senior official')",
        "context_summary": "string",
        "excerpt": "string",
        "timestamp_start": number
      }}
    ]
  }}
}}"""

# V2: YouTube extraction WITHOUT timing (use line anchors)
YOUTUBE_EXTRACTION_LINES_PROMPT = """Analyze this YouTube video transcript and extract ALL claims AND entities.

VIDEO TITLE: {title}
VIDEO URL: {url}
SOURCE_ID: {source_id}

TRANSCRIPT (line-numbered):
{numbered_transcript}

IMPORTANT: This transcript does NOT have timing information.
Use LINE NUMBERS (start_line, end_line) instead of timestamps.

EXTRACTION RULES:
1. For each claim, provide a verbatim_excerpt from the transcript (up to 500 chars)
2. Use start_line/end_line to reference where the claim appears
3. Extract ALL named entities (people, organizations, places)
4. For unnamed entities ("their founders", "a senior official"), create entries in unnamed_entities
5. Identify the SPEAKER for each claim — who is making or asserting the claim
6. Classify the rhetorical FRAMING of each claim
7. Explain the SIGNIFICANCE of each claim in one sentence
8. Assign 1-3 topic TAGS to categorize each claim

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string (paraphrased claim statement)",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "start_line": number (1-indexed),
      "end_line": number,
      "verbatim_excerpt": "string (exact text from transcript, up to 500 chars)",
      "context": "string (2-4 sentences of surrounding context)",
      "entities_mentioned": ["entity_label", ...],
      "speaker": "string (who is making this claim — speaker name if identifiable, 'narrator' if unknown)",
      "framing": "stated_as_fact" | "opinion" | "disputed" | "speculative" | "attributed" | "hedged",
      "significance": "string (one sentence explaining why this claim matters)",
      "tags": ["string (1-3 topic tags like 'financial', 'technology', 'political')"]
    }}
  ],
  "entities": {{
    "people": [
      {{
        "label": "string",
        "context_summary": "string (1-2 sentences about who they are)",
        "excerpt": "string (verbatim from transcript)",
        "start_line": number
      }}
    ],
    "orgs": [...],
    "places": [...],
    "unnamed": [
      {{
        "label": "string (e.g., 'their founders', 'a senior official')",
        "context_summary": "string",
        "excerpt": "string",
        "start_line": number
      }}
    ]
  }}
}}"""

# Legacy prompt for backward compatibility
YOUTUBE_EXTRACTION_PROMPT = """Analyze this YouTube video transcript and extract ALL claims made.

VIDEO TITLE: {title}
VIDEO URL: {url}

TRANSCRIPT:
{transcript}

For each claim found, provide:
1. claim_text: The claim statement (paraphrase if needed for clarity)
2. claim_type: "explicit" or "implied"
3. confidence: "high", "medium", or "low"
4. timestamp_start: Start time in seconds where claim appears
5. timestamp_end: End time in seconds (optional, use same as start if point-in-time)
6. context: Brief surrounding context (1-2 sentences)
7. verbatim_excerpt: The exact text from the transcript (NEW in v2)
8. entities_mentioned: List of entity labels mentioned (NEW in v2)

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "timestamp_start": number,
      "timestamp_end": number | null,
      "context": "string",
      "verbatim_excerpt": "string",
      "entities_mentioned": ["string", ...]
    }}
  ],
  "entities": {{
    "people": [{{"label": "string", "context_summary": "string", "excerpt": "string", "timestamp_start": number}}],
    "orgs": [...],
    "places": [...],
    "unnamed": [...]
  }}
}}"""

TEXT_EXTRACTION_PROMPT = """Analyze this text content and extract ALL claims AND entities.

SOURCE TITLE: {title}
SOURCE TYPE: {source_type}
SOURCE_ID: {source_id}

CONTENT (line-numbered):
{content}

EXTRACTION RULES:
1. For each claim, provide a verbatim_excerpt from the content (up to 500 chars)
2. Use start_line/end_line to reference where the claim appears
3. Extract ALL named entities (people, organizations, places)
4. For unnamed entities ("their founders", "a senior official"), create entries in unnamed_entities
5. Identify the SPEAKER for each claim — who is making or asserting the claim
6. Classify the rhetorical FRAMING of each claim
7. Explain the SIGNIFICANCE of each claim in one sentence
8. Assign 1-3 topic TAGS to categorize each claim

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string (paraphrased claim statement)",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "start_line": number (1-indexed),
      "end_line": number,
      "verbatim_excerpt": "string (exact text from content, up to 500 chars)",
      "context": "string (2-4 sentences of surrounding context)",
      "entities_mentioned": ["entity_label", ...],
      "speaker": "string (who is making this claim — person name if attributed, 'the author' if unattributed)",
      "framing": "stated_as_fact" | "opinion" | "disputed" | "speculative" | "attributed" | "hedged",
      "significance": "string (one sentence explaining why this claim matters)",
      "tags": ["string (1-3 topic tags like 'financial', 'technology', 'political')"]
    }}
  ],
  "entities": {{
    "people": [
      {{
        "label": "string",
        "context_summary": "string (1-2 sentences about who they are)",
        "excerpt": "string (verbatim from content)",
        "start_line": number
      }}
    ],
    "orgs": [...],
    "places": [...],
    "unnamed": [
      {{
        "label": "string (e.g., 'their founders', 'a senior official')",
        "context_summary": "string",
        "excerpt": "string",
        "start_line": number
      }}
    ]
  }}
}}"""

SCREENSHOT_EXTRACTION_PROMPT = """Analyze this screenshot image and extract ALL claims AND entities visible in it.

IMAGE INDEX: {image_index}
SOURCE_ID: {source_id}
PLATFORM HINT: {platform_hint}
OCR TEXT (if available):
{ocr_text}

EXTRACTION RULES:
1. For each claim, provide the verbatim text from the image if visible (up to 500 chars)
2. Specify the region where the claim appears
3. Extract ALL named entities (people, organizations, places) visible
4. For unnamed entities ("their founders", "a senior official"), create entries in unnamed_entities
5. Identify the SPEAKER for each claim — who is making or asserting the claim (account name, author, or 'unknown')
6. Classify the rhetorical FRAMING of each claim
7. Explain the SIGNIFICANCE of each claim in one sentence
8. Assign 1-3 topic TAGS to categorize each claim

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string (paraphrased claim statement)",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "region": "string (e.g., 'top', 'center', 'bottom-left')",
      "ocr_excerpt": "string (verbatim text if visible, up to 500 chars) | null",
      "context": "string (2-4 sentences about what the image shows and surrounding context)",
      "entities_mentioned": ["entity_label", ...],
      "speaker": "string (who is making this claim — account name, author, or 'unknown' if not visible)",
      "framing": "stated_as_fact" | "opinion" | "disputed" | "speculative" | "attributed" | "hedged",
      "significance": "string (one sentence explaining why this claim matters)",
      "tags": ["string (1-3 topic tags like 'financial', 'technology', 'political')"]
    }}
  ],
  "entities": {{
    "people": [
      {{
        "label": "string",
        "context_summary": "string (1-2 sentences about who they are)",
        "excerpt": "string (verbatim text from image if visible)",
        "region": "string"
      }}
    ],
    "orgs": [...],
    "places": [...],
    "unnamed": [
      {{
        "label": "string (e.g., 'their founders', 'a senior official')",
        "context_summary": "string",
        "excerpt": "string",
        "region": "string"
      }}
    ]
  }}
}}"""

# V3: Post-parse relationship detection prompt
CLAIM_RELATIONSHIP_PROMPT = """Given these extracted claims, identify relationships between them.

CLAIMS:
{claims_list}

For each pair of related claims, specify the relationship. Only include CLEAR relationships.

Relationship types:
- supports: This claim corroborates or reinforces the target claim
- contradicts: This claim opposes or undermines the target claim
- qualifies: This claim adds nuance, caveats, or conditions to the target claim
- extends: This claim builds on or expands the target claim

RULES:
- Only identify relationships that are clearly supported by the claim content
- Do NOT force relationships — many claims will be unrelated
- A claim can have multiple relationships
- Prefer quality over quantity — fewer confident links beat many weak ones

Return a JSON object:
{{
  "relationships": [
    {{
      "source_claim_id": "CLM_SRC_001_001",
      "target_claim_id": "CLM_SRC_001_003",
      "relation_type": "supports" | "contradicts" | "qualifies" | "extends",
      "explanation": "string (one sentence explaining the relationship)"
    }}
  ]
}}"""


def link_related_claims(
    gemini_client: Any,
    doc: "ClaimsDocument",
    model: str = "gemini-2.5-flash",
) -> "ClaimsDocument":
    """Post-parse step: identify relationships between extracted claims.

    Sends all claim IDs and texts to Gemini to identify supports/contradicts/
    qualifies/extends relationships. Populates claim.related_claims on matching
    claims.

    Skips if fewer than 2 claims. Batches at 50 claims to manage token budget.
    Wrapped in try/except so failure does not crash the pipeline.

    Args:
        gemini_client: GeminiClient instance
        doc: ClaimsDocument with extracted claims
        model: Gemini model to use

    Returns:
        Updated ClaimsDocument with related_claims populated
    """
    if len(doc.claims) < 2:
        return doc

    try:
        # Build claims list for the prompt (batch at 50)
        batch_size = 50
        claim_map = {c.claim_id: c for c in doc.claims}

        for batch_start in range(0, len(doc.claims), batch_size):
            batch = doc.claims[batch_start:batch_start + batch_size]
            claims_list = "\n".join(
                f'{c.claim_id}: "{c.text}"' for c in batch
            )

            prompt = CLAIM_RELATIONSHIP_PROMPT.format(claims_list=claims_list)

            response = gemini_client.generate_json(
                prompt=prompt,
                model=model,
                temperature=0.1,
            )

            if not response or "error" in response:
                logger.warning(f"Claim relationship detection returned error: {response}")
                continue

            # Gemini client wraps responses as {"data": {...}, "cost": ...}
            response_data = response.get("data", response)
            relationships = response_data.get("relationships", [])
            _valid_rel_types = {e.value for e in ClaimRelationType}

            for rel in relationships:
                source_id = rel.get("source_claim_id")
                target_id = rel.get("target_claim_id")
                rel_type = rel.get("relation_type")

                if (
                    source_id in claim_map
                    and target_id in claim_map
                    and rel_type in _valid_rel_types
                ):
                    claim_map[source_id].related_claims.append(
                        ClaimRelation(
                            target_claim_id=target_id,
                            relation_type=ClaimRelationType(rel_type),
                            explanation=rel.get("explanation"),
                        )
                    )

        linked_count = sum(1 for c in doc.claims if c.related_claims)
        total_rels = sum(len(c.related_claims) for c in doc.claims)
        logger.info(
            f"Claim relationship linking complete: {total_rels} relationships "
            f"across {linked_count}/{len(doc.claims)} claims"
        )

    except Exception as e:
        logger.warning(f"Claim relationship linking failed (non-fatal): {e}")

    return doc


def format_timestamp(seconds: int) -> str:
    """Format seconds as human-readable timestamp (MM:SS or HH:MM:SS)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def number_lines(text: str) -> str:
    """Add line numbers to text for line-based extraction."""
    lines = text.split('\n')
    numbered = []
    for i, line in enumerate(lines, 1):
        numbered.append(f"{i}: {line}")
    return '\n'.join(numbered)


def parse_transcript_segments(transcript_data: dict) -> tuple[list[dict], bool]:
    """Parse transcript data and determine if timing is available.

    Args:
        transcript_data: Raw transcript response from Supadata

    Returns:
        Tuple of (segments, timing_available)
        - segments: List of {text, start_ms, end_ms} if timed, else [{text}]
        - timing_available: True if real timing exists
    """
    # Check for content with timing
    content = transcript_data.get("content") or transcript_data.get("segments")

    if isinstance(content, list) and len(content) > 0:
        first = content[0]
        if isinstance(first, dict) and ("start" in first or "start_ms" in first):
            # Has timing - convert to standard format
            segments = []
            for seg in content:
                if isinstance(seg, dict):
                    segments.append({
                        "text": seg.get("text", ""),
                        "start_ms": seg.get("start_ms") or (seg.get("start", 0) * 1000),
                        "end_ms": seg.get("end_ms") or (seg.get("end", 0) * 1000),
                    })
            if segments and any(s.get("start_ms", 0) > 0 or s.get("end_ms", 0) > 0 for s in segments):
                return segments, True

    # No timing available - return text only
    text = transcript_data.get("text", "")
    if not text and isinstance(content, list):
        text = " ".join(
            seg.get("text", "") if isinstance(seg, dict) else str(seg)
            for seg in content
        )

    return [{"text": text}], False


def format_timed_segments(segments: list[dict]) -> str:
    """Format timed segments for LLM prompt."""
    lines = []
    for seg in segments:
        start_sec = seg.get("start_ms", 0) / 1000
        end_sec = seg.get("end_ms", 0) / 1000
        text = seg.get("text", "")
        lines.append(f"[{start_sec:.1f}s - {end_sec:.1f}s]: {text}")
    return '\n'.join(lines)


def validate_timestamp_bounds(
    timestamp_start: int,
    timestamp_end: Optional[int],
    segments: list[dict],
    source_id: str,
) -> tuple[Optional[int], Optional[int], Optional[ExtractionWarning]]:
    """Validate that timestamps fall within known segment bounds.

    Args:
        timestamp_start: Start time in seconds
        timestamp_end: End time in seconds (optional)
        segments: List of segments with timing
        source_id: Source ID for warning

    Returns:
        Tuple of (validated_start, validated_end, warning_if_any)
    """
    if not segments:
        return timestamp_start, timestamp_end, None

    # Find bounds
    min_time_ms = min(s.get("start_ms", 0) for s in segments)
    max_time_ms = max(s.get("end_ms", 0) for s in segments)

    min_sec = min_time_ms / 1000
    max_sec = max_time_ms / 1000

    warning = None

    # Clamp start
    if timestamp_start < min_sec:
        timestamp_start = int(min_sec)
        warning = ExtractionWarning(
            code=WarningCode.TIMESTAMP_OUT_OF_BOUNDS,
            message=f"Timestamp {timestamp_start}s clamped to segment bounds",
            source_id=source_id,
        )
    elif timestamp_start > max_sec:
        timestamp_start = int(max_sec)
        warning = ExtractionWarning(
            code=WarningCode.TIMESTAMP_OUT_OF_BOUNDS,
            message=f"Timestamp {timestamp_start}s clamped to segment bounds",
            source_id=source_id,
        )

    # Clamp end if provided
    if timestamp_end is not None:
        if timestamp_end > max_sec:
            timestamp_end = int(max_sec)
        if timestamp_end < timestamp_start:
            timestamp_end = timestamp_start

    return timestamp_start, timestamp_end, warning


def extract_entities_from_response(
    raw_entities: dict,
    source_id: str,
    timing_available: bool,
) -> tuple[list[Entity], list[ExtractionWarning]]:
    """Extract Entity objects from LLM response.

    Args:
        raw_entities: Raw entities dict from LLM
        source_id: Source ID for anchors
        timing_available: Whether to use timestamp or line anchors

    Returns:
        Tuple of (entities, warnings)
    """
    entities = []
    warnings = []
    entity_counter = 1

    for entity_type, raw_list in raw_entities.items():
        if not isinstance(raw_list, list):
            continue

        # Map string type to EntityType enum
        if entity_type == "people":
            etype = EntityType.PERSON
        elif entity_type == "orgs":
            etype = EntityType.ORG
        elif entity_type == "places":
            etype = EntityType.PLACE
        elif entity_type == "unnamed":
            etype = EntityType.UNNAMED
        else:
            continue

        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            label = raw.get("label", "").strip()
            if not label:
                continue

            excerpt = raw.get("excerpt", "").strip()
            if not excerpt:
                warnings.append(ExtractionWarning(
                    code=WarningCode.ENTITY_MISSING_EVIDENCE,
                    message=f"Entity '{label}' has no verbatim excerpt",
                    source_id=source_id,
                ))
                # Create minimal excerpt from context_summary
                excerpt = raw.get("context_summary", label)[:100]

            # Build anchor
            if timing_available and "timestamp_start" in raw:
                anchor = ClaimAnchor(
                    timestamp=TimestampAnchor(
                        start_seconds=raw.get("timestamp_start", 0),
                        end_seconds=raw.get("timestamp_end"),
                        formatted=format_timestamp(raw.get("timestamp_start", 0)),
                        source_id=source_id,
                    ),
                    source_id=source_id,
                )
            else:
                anchor = ClaimAnchor(
                    line_range=LineRangeAnchor(
                        start_line=raw.get("start_line", 1),
                        end_line=raw.get("end_line", raw.get("start_line", 1)),
                        excerpt=excerpt[:200],
                        source_id=source_id,
                    ),
                    source_id=source_id,
                )

            entity = Entity(
                entity_id=f"ENT_{source_id}_{entity_counter:03d}",
                canonical_label=label,
                entity_type=etype,
                aliases=raw.get("aliases", []),
                context_summary=raw.get("context_summary", f"Entity mentioned in source")[:500],
                context_evidence=[
                    ContextEvidence(
                        excerpt=excerpt,
                        anchor=anchor,
                        source_id=source_id,
                    )
                ],
                top_anchors=[anchor],
            )
            entities.append(entity)
            entity_counter += 1

    return entities, warnings


def extract_claims_from_youtube(
    gemini_client: Any,
    video_url: str,
    title: str,
    transcript: str,
    source_id: str,
    model: str = "gemini-2.5-flash",
    transcript_data: Optional[dict] = None,
) -> tuple[list[Claim], SourceSummary, list[Entity], list[ExtractionWarning]]:
    """Extract claims and entities from a YouTube video transcript.

    V2 Update: Returns entities and warnings. Uses line anchors if timing unavailable.

    Args:
        gemini_client: GeminiClient instance
        video_url: YouTube video URL
        title: Video title
        transcript: Video transcript text (used if transcript_data is None)
        source_id: Unique source identifier (SRC_001, ...)
        model: Gemini model to use
        transcript_data: Optional raw transcript response with segments

    Returns:
        Tuple of (claims, source_summary, entities, warnings)
    """
    warnings: list[ExtractionWarning] = []
    entities: list[Entity] = []

    # Determine if timing is available
    timing_available = False
    segments: list[dict] = []

    if transcript_data:
        segments, timing_available = parse_transcript_segments(transcript_data)

    # Choose prompt based on timing availability
    if timing_available and segments:
        prompt = YOUTUBE_EXTRACTION_TIMED_PROMPT.format(
            title=title,
            url=video_url,
            source_id=source_id,
            transcript_segments=format_timed_segments(segments),
        )
        anchor_type = AnchorType.YOUTUBE_TIMESTAMP
    else:
        # No timing - use line-numbered transcript
        numbered = number_lines(transcript)
        prompt = YOUTUBE_EXTRACTION_LINES_PROMPT.format(
            title=title,
            url=video_url,
            source_id=source_id,
            numbered_transcript=numbered,
        )
        anchor_type = AnchorType.TEXT_LINE_RANGE
        warnings.append(ExtractionWarning(
            code=WarningCode.TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS,
            message=f"Transcript timing unavailable for {video_url}; using line anchors",
            source_id=source_id,
        ))

    try:
        result = gemini_client.generate_json(
            prompt=prompt,
            system_message=CLAIM_EXTRACTION_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,  # Low temperature for extraction
        )

        if result.get("error"):
            logger.warning(f"Claim extraction error for {video_url}: {result['error']}")
            return [], SourceSummary(
                source_id=source_id,
                source_type=SourceType.YOUTUBE,
                title=title,
                url=video_url,
                claim_count=0,
                timing_available=timing_available,
                anchor_type_used=anchor_type,
            ), [], warnings

        data = result.get("data", {})
        # Handle both cases: Gemini may return {"claims": [...]} or just [...]
        if isinstance(data, list):
            raw_claims = data  # Gemini returned claims array directly
            raw_entities = {}
        else:
            raw_claims = data.get("claims", [])
            raw_entities = data.get("entities", {})

        claims: list[Claim] = []
        explicit_count = 0
        implied_count = 0

        for i, raw in enumerate(raw_claims):
            claim_type = ClaimType.EXPLICIT if raw.get("claim_type") == "explicit" else ClaimType.IMPLIED
            confidence = ConfidenceLevel(raw.get("confidence", "medium"))

            # Build anchor based on timing availability
            if timing_available and "timestamp_start" in raw:
                start_sec = raw.get("timestamp_start", 0)
                end_sec = raw.get("timestamp_end")

                # Validate timestamp bounds
                start_sec, end_sec, bound_warning = validate_timestamp_bounds(
                    start_sec, end_sec, segments, source_id
                )
                if bound_warning:
                    warnings.append(bound_warning)

                if end_sec:
                    formatted = f"{format_timestamp(start_sec)}-{format_timestamp(end_sec)}"
                else:
                    formatted = format_timestamp(start_sec)
                    end_sec = start_sec

                anchor = ClaimAnchor(
                    timestamp=TimestampAnchor(
                        start_seconds=start_sec,
                        end_seconds=end_sec,
                        formatted=formatted,
                        source_id=source_id,
                    ),
                    source_id=source_id,
                )
            else:
                # Use line range anchor
                start_line = raw.get("start_line", 1)
                end_line = raw.get("end_line", start_line)
                excerpt = raw.get("verbatim_excerpt", raw.get("excerpt", ""))[:200]

                # If LLM returned timestamp when timing unavailable, coerce to line
                if "timestamp_start" in raw and not timing_available:
                    warnings.append(ExtractionWarning(
                        code=WarningCode.TIMESTAMP_COERCED_TO_LINE,
                        message=f"Timestamp coerced to line anchor (timing unavailable)",
                        source_id=source_id,
                        details={"original_timestamp": raw.get("timestamp_start")},
                    ))

                anchor = ClaimAnchor(
                    line_range=LineRangeAnchor(
                        start_line=start_line,
                        end_line=end_line,
                        excerpt=excerpt,
                        source_id=source_id,
                    ),
                    source_id=source_id,
                )

            # V3: Parse rhetorical framing safely
            _valid_framings = {e.value for e in RhetoricalFraming}
            raw_framing = raw.get("framing")
            parsed_framing = RhetoricalFraming(raw_framing) if raw_framing in _valid_framings else None

            claim = Claim(
                claim_id=f"CLM_{source_id}_{i+1:03d}",
                text=raw.get("claim_text", ""),
                claim_type=claim_type,
                confidence=confidence,
                anchor=anchor,
                source_id=source_id,
                context=raw.get("context"),
                verbatim_excerpt=raw.get("verbatim_excerpt"),
                entities_involved=raw.get("entities_mentioned", []),
                # V3 enrichment fields
                speaker=raw.get("speaker"),
                framing=parsed_framing,
                significance=raw.get("significance"),
                tags=raw.get("tags", []),
            )

            # Validate claim has evidence
            if not claim.has_evidence():
                warnings.append(ExtractionWarning(
                    code=WarningCode.CLAIM_MISSING_ANCHOR,
                    message=f"Claim {claim.claim_id} has no verbatim evidence",
                    source_id=source_id,
                ))

            claims.append(claim)

            if claim_type == ClaimType.EXPLICIT:
                explicit_count += 1
            else:
                implied_count += 1

        # Extract entities
        if raw_entities:
            extracted_entities, entity_warnings = extract_entities_from_response(
                raw_entities, source_id, timing_available
            )
            entities.extend(extracted_entities)
            warnings.extend(entity_warnings)

        source_summary = SourceSummary(
            source_id=source_id,
            source_type=SourceType.YOUTUBE,
            title=title,
            url=video_url,
            claim_count=len(claims),
            explicit_count=explicit_count,
            implied_count=implied_count,
            timing_available=timing_available,
            anchor_type_used=anchor_type,
            entity_count=len(entities),
        )

        logger.info(
            f"Extracted {len(claims)} claims, {len(entities)} entities from YouTube: {title} "
            f"(timing={'yes' if timing_available else 'no'})"
        )
        return claims, source_summary, entities, warnings

    except Exception as e:
        logger.error(f"Failed to extract claims from YouTube {video_url}: {e}")
        return [], SourceSummary(
            source_id=source_id,
            source_type=SourceType.YOUTUBE,
            title=title,
            url=video_url,
            claim_count=0,
            timing_available=timing_available,
            anchor_type_used=anchor_type,
        ), [], warnings


def extract_claims_from_text(
    gemini_client: Any,
    content: str,
    title: str,
    source_id: str,
    source_type: SourceType = SourceType.TEXT,
    url: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> tuple[list[Claim], SourceSummary, list[Entity], list[ExtractionWarning]]:
    """Extract claims and entities from text content.

    V2 Update: Returns entities and warnings.

    Args:
        gemini_client: GeminiClient instance
        content: Text content to analyze
        title: Content title
        source_id: Unique source identifier
        source_type: Type of source (TEXT or ARTICLE)
        url: Optional URL for articles
        model: Gemini model to use

    Returns:
        Tuple of (claims, source_summary, entities, warnings)
    """
    warnings: list[ExtractionWarning] = []
    entities: list[Entity] = []

    # Number lines for extraction
    numbered_content = number_lines(content)

    prompt = TEXT_EXTRACTION_PROMPT.format(
        title=title,
        source_type=source_type.value,
        source_id=source_id,
        content=numbered_content,
    )

    try:
        result = gemini_client.generate_json(
            prompt=prompt,
            system_message=CLAIM_EXTRACTION_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

        if result.get("error"):
            logger.warning(f"Claim extraction error for {title}: {result['error']}")
            return [], SourceSummary(
                source_id=source_id,
                source_type=source_type,
                title=title,
                url=url,
                claim_count=0,
                anchor_type_used=AnchorType.TEXT_LINE_RANGE,
            ), [], warnings

        data = result.get("data", {})
        # Handle both cases: Gemini may return {"claims": [...]} or just [...]
        if isinstance(data, list):
            raw_claims = data  # Gemini returned claims array directly
            raw_entities = {}
        else:
            raw_claims = data.get("claims", [])
            raw_entities = data.get("entities", {})

        claims: list[Claim] = []
        explicit_count = 0
        implied_count = 0

        for i, raw in enumerate(raw_claims):
            claim_type = ClaimType.EXPLICIT if raw.get("claim_type") == "explicit" else ClaimType.IMPLIED
            confidence = ConfidenceLevel(raw.get("confidence", "medium"))

            # Build line range anchor
            start_line = raw.get("start_line", 1)
            end_line = raw.get("end_line", start_line)
            excerpt = raw.get("verbatim_excerpt", raw.get("excerpt", ""))[:200]

            anchor = ClaimAnchor(
                line_range=LineRangeAnchor(
                    start_line=start_line,
                    end_line=end_line,
                    excerpt=excerpt,
                    source_id=source_id,
                ),
                source_id=source_id,
            )

            # V3: Parse rhetorical framing safely
            _valid_framings = {e.value for e in RhetoricalFraming}
            raw_framing = raw.get("framing")
            parsed_framing = RhetoricalFraming(raw_framing) if raw_framing in _valid_framings else None

            claim = Claim(
                claim_id=f"CLM_{source_id}_{i+1:03d}",
                text=raw.get("claim_text", ""),
                claim_type=claim_type,
                confidence=confidence,
                anchor=anchor,
                source_id=source_id,
                context=raw.get("context"),
                verbatim_excerpt=raw.get("verbatim_excerpt"),
                entities_involved=raw.get("entities_mentioned", []),
                # V3 enrichment fields
                speaker=raw.get("speaker"),
                framing=parsed_framing,
                significance=raw.get("significance"),
                tags=raw.get("tags", []),
            )

            # Validate claim has evidence
            if not claim.has_evidence():
                warnings.append(ExtractionWarning(
                    code=WarningCode.CLAIM_MISSING_ANCHOR,
                    message=f"Claim {claim.claim_id} has no verbatim evidence",
                    source_id=source_id,
                ))

            claims.append(claim)

            if claim_type == ClaimType.EXPLICIT:
                explicit_count += 1
            else:
                implied_count += 1

        # Extract entities
        if raw_entities:
            extracted_entities, entity_warnings = extract_entities_from_response(
                raw_entities, source_id, timing_available=False
            )
            entities.extend(extracted_entities)
            warnings.extend(entity_warnings)

        source_summary = SourceSummary(
            source_id=source_id,
            source_type=source_type,
            title=title,
            url=url,
            claim_count=len(claims),
            explicit_count=explicit_count,
            implied_count=implied_count,
            timing_available=False,
            anchor_type_used=AnchorType.TEXT_LINE_RANGE,
            entity_count=len(entities),
        )

        logger.info(f"Extracted {len(claims)} claims, {len(entities)} entities from text: {title}")
        return claims, source_summary, entities, warnings

    except Exception as e:
        logger.error(f"Failed to extract claims from text {title}: {e}")
        return [], SourceSummary(
            source_id=source_id,
            source_type=source_type,
            title=title,
            url=url,
            claim_count=0,
            anchor_type_used=AnchorType.TEXT_LINE_RANGE,
        ), [], warnings


def extract_claims_from_screenshot(
    gemini_client: Any,
    image_base64: str,
    image_index: int,
    source_id: str,
    platform_hint: Optional[str] = None,
    ocr_text: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> tuple[list[Claim], SourceSummary, list[Entity], list[ExtractionWarning]]:
    """Extract claims and entities from a screenshot image.

    V2 Update: Returns entities and warnings.

    Args:
        gemini_client: GeminiClient instance
        image_base64: Base64-encoded image data
        image_index: Index of this screenshot (0-indexed)
        source_id: Unique source identifier
        platform_hint: Optional platform hint (twitter, reddit, etc.)
        ocr_text: Optional pre-extracted OCR text
        model: Gemini model to use

    Returns:
        Tuple of (claims, source_summary, entities, warnings)
    """
    warnings: list[ExtractionWarning] = []
    entities: list[Entity] = []

    prompt = SCREENSHOT_EXTRACTION_PROMPT.format(
        image_index=image_index,
        source_id=source_id,
        platform_hint=platform_hint or "unknown",
        ocr_text=ocr_text or "(No OCR text available)",
    )

    title = f"Screenshot #{image_index + 1}"
    if platform_hint:
        title = f"{platform_hint.title()} Screenshot #{image_index + 1}"

    try:
        # Use vision capabilities
        result = gemini_client.generate_json_with_image(
            prompt=prompt,
            image_base64=image_base64,
            system_message=CLAIM_EXTRACTION_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

        if result.get("error"):
            logger.warning(f"Claim extraction error for screenshot {image_index}: {result['error']}")
            return [], SourceSummary(
                source_id=source_id,
                source_type=SourceType.SCREENSHOT,
                title=title,
                claim_count=0,
                anchor_type_used=AnchorType.IMAGE_INDEX,
            ), [], warnings

        data = result.get("data", {})
        # Handle both cases: Gemini may return {"claims": [...]} or just [...]
        if isinstance(data, list):
            raw_claims = data  # Gemini returned claims array directly
            raw_entities = {}
        else:
            raw_claims = data.get("claims", [])
            raw_entities = data.get("entities", {})

        claims: list[Claim] = []
        explicit_count = 0
        implied_count = 0

        for i, raw in enumerate(raw_claims):
            claim_type = ClaimType.EXPLICIT if raw.get("claim_type") == "explicit" else ClaimType.IMPLIED
            confidence = ConfidenceLevel(raw.get("confidence", "medium"))

            # Build image anchor
            anchor = ClaimAnchor(
                image=ImageAnchor(
                    image_index=image_index,
                    region=raw.get("region"),
                    ocr_excerpt=raw.get("ocr_excerpt"),
                    source_id=source_id,
                ),
                source_id=source_id,
            )

            # V3: Parse rhetorical framing safely
            _valid_framings = {e.value for e in RhetoricalFraming}
            raw_framing = raw.get("framing")
            parsed_framing = RhetoricalFraming(raw_framing) if raw_framing in _valid_framings else None

            claim = Claim(
                claim_id=f"CLM_{source_id}_{i+1:03d}",
                text=raw.get("claim_text", ""),
                claim_type=claim_type,
                confidence=confidence,
                anchor=anchor,
                source_id=source_id,
                context=raw.get("context"),
                verbatim_excerpt=raw.get("ocr_excerpt"),
                entities_involved=raw.get("entities_mentioned", []),
                # V3 enrichment fields
                speaker=raw.get("speaker"),
                framing=parsed_framing,
                significance=raw.get("significance"),
                tags=raw.get("tags", []),
            )

            # Validate claim has evidence
            if not claim.has_evidence():
                warnings.append(ExtractionWarning(
                    code=WarningCode.CLAIM_MISSING_ANCHOR,
                    message=f"Claim {claim.claim_id} has no verbatim evidence",
                    source_id=source_id,
                ))

            claims.append(claim)

            if claim_type == ClaimType.EXPLICIT:
                explicit_count += 1
            else:
                implied_count += 1

        # Extract entities from screenshot
        if raw_entities:
            extracted_entities, entity_warnings = extract_entities_from_screenshot_response(
                raw_entities, source_id, image_index
            )
            entities.extend(extracted_entities)
            warnings.extend(entity_warnings)

        source_summary = SourceSummary(
            source_id=source_id,
            source_type=SourceType.SCREENSHOT,
            title=title,
            claim_count=len(claims),
            explicit_count=explicit_count,
            implied_count=implied_count,
            timing_available=False,
            anchor_type_used=AnchorType.IMAGE_INDEX,
            entity_count=len(entities),
        )

        logger.info(f"Extracted {len(claims)} claims, {len(entities)} entities from screenshot {image_index}")
        return claims, source_summary, entities, warnings

    except Exception as e:
        logger.error(f"Failed to extract claims from screenshot {image_index}: {e}")
        return [], SourceSummary(
            source_id=source_id,
            source_type=SourceType.SCREENSHOT,
            title=title,
            claim_count=0,
            anchor_type_used=AnchorType.IMAGE_INDEX,
        ), [], warnings


def extract_entities_from_screenshot_response(
    raw_entities: dict,
    source_id: str,
    image_index: int,
) -> tuple[list[Entity], list[ExtractionWarning]]:
    """Extract Entity objects from screenshot LLM response.

    Args:
        raw_entities: Raw entities dict from LLM
        source_id: Source ID for anchors
        image_index: Screenshot index

    Returns:
        Tuple of (entities, warnings)
    """
    entities = []
    warnings = []
    entity_counter = 1

    for entity_type, raw_list in raw_entities.items():
        if not isinstance(raw_list, list):
            continue

        # Map string type to EntityType enum
        if entity_type == "people":
            etype = EntityType.PERSON
        elif entity_type == "orgs":
            etype = EntityType.ORG
        elif entity_type == "places":
            etype = EntityType.PLACE
        elif entity_type == "unnamed":
            etype = EntityType.UNNAMED
        else:
            continue

        for raw in raw_list:
            if not isinstance(raw, dict):
                continue

            label = raw.get("label", "").strip()
            if not label:
                continue

            excerpt = raw.get("excerpt", "").strip()
            if not excerpt:
                warnings.append(ExtractionWarning(
                    code=WarningCode.ENTITY_MISSING_EVIDENCE,
                    message=f"Entity '{label}' has no verbatim excerpt",
                    source_id=source_id,
                ))
                excerpt = raw.get("context_summary", label)[:100]

            # Build image anchor
            anchor = ClaimAnchor(
                image=ImageAnchor(
                    image_index=image_index,
                    region=raw.get("region"),
                    ocr_excerpt=excerpt[:200],
                    source_id=source_id,
                ),
                source_id=source_id,
            )

            entity = Entity(
                entity_id=f"ENT_{source_id}_{entity_counter:03d}",
                canonical_label=label,
                entity_type=etype,
                aliases=raw.get("aliases", []),
                context_summary=raw.get("context_summary", f"Entity mentioned in source")[:500],
                context_evidence=[
                    ContextEvidence(
                        excerpt=excerpt,
                        anchor=anchor,
                        source_id=source_id,
                    )
                ],
                top_anchors=[anchor],
            )
            entities.append(entity)
            entity_counter += 1

    return entities, warnings


def run_claim_extraction_pipeline(
    gemini_client: Any,
    job_id: str,
    title: str,
    video_urls: list[str] = None,
    article_urls: list[str] = None,
    text_inputs: list[dict] = None,
    screenshots: list[dict] = None,
    model: str = "gemini-2.5-flash",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    run_id: Optional[str] = None,
) -> ClaimsDocument:
    """Run the complete claim extraction pipeline.

    V2 Update: Extracts entities and handles timing availability for anchors.

    Args:
        gemini_client: GeminiClient instance
        job_id: Job identifier
        title: Job title
        video_urls: List of YouTube URLs to analyze
        article_urls: List of article URLs to fetch and analyze
        text_inputs: List of dicts with {title, content}
        screenshots: List of dicts with {filename, base64, platform_hint}
        model: Gemini model to use
        progress_callback: Optional callback(current, total, status)
        run_id: Optional run ID if triggered from a semantic run

    Returns:
        ClaimsDocument with all extracted claims, entities, and warnings
    """
    from backend.integrations.supadata_client import SupadataClient

    video_urls = video_urls or []
    article_urls = article_urls or []
    text_inputs = text_inputs or []
    screenshots = screenshots or []

    # Calculate total sources for progress
    total_sources = len(video_urls) + len(article_urls) + len(text_inputs) + len(screenshots)
    current_source = 0

    # Create claims document
    doc = ClaimsDocument.create_empty(job_id, title, run_id=run_id)
    doc.metadata.extraction_model = model

    # Process YouTube videos
    for i, url in enumerate(video_urls):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing video {i+1}/{len(video_urls)}")

        source_id = f"SRC_{current_source:03d}"

        # Fetch transcript and metadata using Supadata
        try:
            supadata = SupadataClient()

            # Fetch metadata first for title
            from backend.integrations.supadata_client import fetch_video_metadata
            metadata = fetch_video_metadata(url)
            video_title = metadata.get("title", f"Video {i+1}") if metadata else f"Video {i+1}"

            # Fetch transcript with raw response for timing check
            transcript_result = supadata.get_transcript(url)
            transcript = transcript_result.get("text", "")

            if not transcript:
                logger.warning(f"No transcript available for {url}")
                doc.add_source(SourceSummary(
                    source_id=source_id,
                    source_type=SourceType.YOUTUBE,
                    title=video_title,
                    url=url,
                    claim_count=0,
                    timing_available=False,
                    anchor_type_used=AnchorType.TEXT_LINE_RANGE,
                ))
                doc.add_warning(
                    WarningCode.EMPTY_EXTRACTION,
                    f"No transcript available for {video_title}",
                    source_id=source_id,
                )
                continue

            # V2: Pass transcript_data for timing detection
            claims, summary, entities, warnings = extract_claims_from_youtube(
                gemini_client, url, video_title, transcript, source_id, model,
                transcript_data=transcript_result,
            )
            doc.add_source(summary)
            for claim in claims:
                doc.add_claim(claim)
            for entity in entities:
                doc.add_entity(entity)
            for warning in warnings:
                doc.warnings.append(warning)

        except Exception as e:
            logger.error(f"Failed to process YouTube video {url}: {e}")
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.YOUTUBE,
                title=f"Video {i+1}",
                url=url,
                claim_count=0,
                timing_available=False,
            ))

    # Process article URLs
    for i, url in enumerate(article_urls):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing article {i+1}/{len(article_urls)}")

        source_id = f"SRC_{current_source:03d}"

        # Fetch article content using Supadata
        try:
            supadata = SupadataClient()
            article = supadata.scrape_url(url)
            content = article.get("content", "")
            # Extract title from URL or use default
            article_title = url.split("/")[-1].replace("-", " ").replace("_", " ")[:50] or f"Article {i+1}"

            if not content:
                logger.warning(f"No content fetched for {url}")
                doc.add_source(SourceSummary(
                    source_id=source_id,
                    source_type=SourceType.ARTICLE,
                    title=article_title,
                    url=url,
                    claim_count=0,
                    anchor_type_used=AnchorType.TEXT_LINE_RANGE,
                ))
                doc.add_warning(
                    WarningCode.EMPTY_EXTRACTION,
                    f"No content fetched for {article_title}",
                    source_id=source_id,
                )
                continue

            claims, summary, entities, warnings = extract_claims_from_text(
                gemini_client, content, article_title, source_id,
                source_type=SourceType.ARTICLE, url=url, model=model
            )
            doc.add_source(summary)
            for claim in claims:
                doc.add_claim(claim)
            for entity in entities:
                doc.add_entity(entity)
            for warning in warnings:
                doc.warnings.append(warning)

        except Exception as e:
            logger.error(f"Failed to process article {url}: {e}")
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.ARTICLE,
                title=f"Article {i+1}",
                url=url,
                claim_count=0,
            ))

    # Process text inputs
    for i, text_input in enumerate(text_inputs):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing text {i+1}/{len(text_inputs)}")

        source_id = f"SRC_{current_source:03d}"
        text_title = text_input.get("title", f"Text Input {i+1}")
        content = text_input.get("content", "")

        if not content:
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.TEXT,
                title=text_title,
                claim_count=0,
                anchor_type_used=AnchorType.TEXT_LINE_RANGE,
            ))
            doc.add_warning(
                WarningCode.EMPTY_EXTRACTION,
                f"No content provided for {text_title}",
                source_id=source_id,
            )
            continue

        claims, summary, entities, warnings = extract_claims_from_text(
            gemini_client, content, text_title, source_id,
            source_type=SourceType.TEXT, model=model
        )
        doc.add_source(summary)
        for claim in claims:
            doc.add_claim(claim)
        for entity in entities:
            doc.add_entity(entity)
        for warning in warnings:
            doc.warnings.append(warning)

    # Process screenshots
    for i, screenshot in enumerate(screenshots):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing screenshot {i+1}/{len(screenshots)}")

        source_id = f"SRC_{current_source:03d}"
        image_base64 = screenshot.get("base64", "")
        platform_hint = screenshot.get("platform_hint")

        if not image_base64:
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.SCREENSHOT,
                title=f"Screenshot {i+1}",
                claim_count=0,
                anchor_type_used=AnchorType.IMAGE_INDEX,
            ))
            doc.add_warning(
                WarningCode.EMPTY_EXTRACTION,
                f"No image data for Screenshot {i+1}",
                source_id=source_id,
            )
            continue

        claims, summary, entities, warnings = extract_claims_from_screenshot(
            gemini_client, image_base64, i, source_id,
            platform_hint=platform_hint, model=model
        )
        doc.add_source(summary)
        for claim in claims:
            doc.add_claim(claim)
        for entity in entities:
            doc.add_entity(entity)
        for warning in warnings:
            doc.warnings.append(warning)

    # V3: Link related claims (post-parse step)
    if doc.metadata.total_claims >= 2:
        doc = link_related_claims(gemini_client, doc, model=model)

    # Check for empty extraction
    if doc.metadata.total_claims == 0:
        doc.add_warning(
            WarningCode.EMPTY_EXTRACTION,
            "No claims extracted from any source",
        )

    logger.info(
        f"Claim extraction complete: {doc.metadata.total_claims} claims, "
        f"{doc.metadata.total_entities} entities from {doc.metadata.source_count} sources "
        f"({len(doc.warnings)} warnings)"
    )
    return doc
