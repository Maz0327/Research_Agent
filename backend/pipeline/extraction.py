"""Claim and quote extraction from transcripts and web sources."""
import gc
import re
import uuid
from collections import defaultdict

from loguru import logger
from openai import OpenAI
from pydantic import ValidationError

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed. Memory monitoring disabled. Install with: pip install psutil")

from backend.config import require_openai, MissingRequiredSettingError
from backend.integrations.transcripts import TranscriptItem
from backend.models.claim import Claim, Citation
from backend.models.source import SourceItem


# Memory thresholds for extraction
MEMORY_WARNING_THRESHOLD = 75  # Log warning at 75% memory usage
MEMORY_CRITICAL_THRESHOLD = 85  # Stop processing at 85% memory usage


def _check_memory_pressure() -> tuple[bool, float]:
    """
    Check if system memory is under pressure.

    Returns:
        Tuple of (is_critical, memory_percent).
        is_critical is True if memory usage exceeds MEMORY_CRITICAL_THRESHOLD.
    """
    if not PSUTIL_AVAILABLE:
        return False, 0.0

    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        if memory_percent >= MEMORY_CRITICAL_THRESHOLD:
            logger.warning(f"Memory critical: {memory_percent:.1f}% used. Stopping extraction.")
            return True, memory_percent
        elif memory_percent >= MEMORY_WARNING_THRESHOLD:
            logger.info(f"Memory warning: {memory_percent:.1f}% used. Consider reducing batch size.")

        return False, memory_percent
    except Exception as e:
        logger.debug(f"Failed to check memory: {e}")
        return False, 0.0


# Approximate words per minute for transcripts (average speaking rate)
WORDS_PER_MINUTE = 150

# Chunk sizes
TRANSCRIPT_CHUNK_WORDS_MIN = 1200  # ~8 minutes
TRANSCRIPT_CHUNK_WORDS_MAX = 2000  # ~13 minutes
WEB_CHUNK_TOKENS_MIN = 1500
WEB_CHUNK_TOKENS_MAX = 2500

# Approximate tokens per word (for web text)
TOKENS_PER_WORD = 1.3


def _chunk_transcript_text(text: str) -> list[tuple[str, int, int]]:
    """
    Chunk transcript text into 1-3 minute windows (~1200-2000 words).
    
    Args:
        text: Transcript text
        
    Returns:
        List of tuples: (chunk_text, start_word_idx, end_word_idx)
    """
    words = text.split()
    chunks = []
    
    start = 0
    while start < len(words):
        # Target chunk size in middle of range
        target_size = (TRANSCRIPT_CHUNK_WORDS_MIN + TRANSCRIPT_CHUNK_WORDS_MAX) // 2
        end = min(start + target_size, len(words))
        
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append((chunk_text, start, end))
        
        # Overlap by ~200 words to avoid breaking sentences
        start = end - 200
        if start >= len(words):
            break
    
    return chunks


def _chunk_web_text(text: str) -> list[tuple[str, int, int]]:
    """
    Chunk web text into ~1500-2500 token segments.
    
    Args:
        text: Web article text
        
    Returns:
        List of tuples: (chunk_text, start_word_idx, end_word_idx)
    """
    words = text.split()
    chunks = []
    
    # Convert token ranges to word ranges (approximate)
    words_min = int(WEB_CHUNK_TOKENS_MIN / TOKENS_PER_WORD)
    words_max = int(WEB_CHUNK_TOKENS_MAX / TOKENS_PER_WORD)
    
    start = 0
    while start < len(words):
        target_size = (words_min + words_max) // 2
        end = min(start + target_size, len(words))
        
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append((chunk_text, start, end))
        
        # Overlap by ~200 words
        start = end - 200
        if start >= len(words):
            break
    
    return chunks


def _extract_claim_candidates(chunk_text: str) -> list[dict]:
    """
    Extract high-recall claim candidates using deterministic heuristics.
    
    Looks for:
    - Numbers and dates
    - Named entities (capitalized words/phrases)
    - Assertion verbs (said, claimed, stated, alleged, reported, etc.)
    - Question markers
    
    Args:
        chunk_text: Text chunk to analyze
        
    Returns:
        List of candidate dicts with 'text' and 'score'
    """
    candidates = []
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', chunk_text)
    
    assertion_verbs = [
        r'\b(said|claimed|stated|alleged|reported|announced|revealed|'
        r'declared|insisted|maintained|asserted|contended|argued|'
        r'confirmed|denied|admitted|acknowledged|testified|witnessed)\b',
    ]
    
    date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|'
    date_pattern += r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4})\b'
    
    number_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b'
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:  # Skip very short sentences
            continue
        
        score = 0
        reasons = []
        
        # Check for assertion verbs
        if re.search(assertion_verbs[0], sentence, re.IGNORECASE):
            score += 3
            reasons.append("assertion_verb")
        
        # Check for dates
        if re.search(date_pattern, sentence, re.IGNORECASE):
            score += 2
            reasons.append("date")
        
        # Check for numbers
        if re.search(number_pattern, sentence):
            score += 1
            reasons.append("number")
        
        # Check for capitalized entities (simple heuristic)
        capital_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence)
        if len(capital_words) >= 2:  # Multiple potential entities
            score += 2
            reasons.append("entities")
        
        # Minimum score threshold
        if score >= 3:
            candidates.append({
                "text": sentence,
                "score": score,
                "reasons": reasons,
            })
    
    return candidates


def _canonicalize_claims_with_openai(
    candidates: list[dict],
    chunk_text: str,
    api_key: str,
) -> list[Claim]:
    """
    Use OpenAI structured output to canonicalize claim candidates into Claim objects.
    
    Args:
        candidates: List of candidate dicts with 'text'
        chunk_text: Original chunk text (for substring validation)
        api_key: OpenAI API key
        
    Returns:
        List of Claim objects (filtered by substring requirement)
    """
    if not candidates:
        return []
    
    client = OpenAI(api_key=api_key)
    
    # Prepare candidate texts
    candidate_texts = [c["text"] for c in candidates]
    candidates_str = "\n".join(f"{i+1}. {text}" for i, text in enumerate(candidate_texts))
    
    prompt = f"""Extract claims from these candidate statements. For each valid claim, create a Claim object.

Original chunk context:
{chunk_text[:500]}...

Candidate statements to analyze:
{candidates_str}

Requirements:
1. Extract canonical claims (normalized, factual statements)
2. Identify claim_type (factual, opinion, prediction, allegation, timeline_event)
3. Extract entities (people, organizations, places)
4. Provide verbatim_quote - this MUST be an exact substring of the original chunk text
5. If verbatim_quote is not an exact substring, discard that claim
6. Set confidence score (0.0-1.0)

Return JSON array of Claim objects. Each claim must have verbatim_quote that exactly matches text in the chunk."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a claim extraction assistant. Return valid JSON array of Claim objects. verbatim_quote must be exact substring of chunk.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        import json
        content = response.choices[0].message.content
        if not content:
            return []
        
        data = json.loads(content)
        
        # Handle both {"claims": [...]} and [...] formats
        claims_data = data.get("claims", data) if isinstance(data, dict) else data
        if not isinstance(claims_data, list):
            claims_data = [claims_data]
        
        validated_claims = []
        for claim_data in claims_data:
            try:
                # Generate claim_id if not provided
                if "claim_id" not in claim_data:
                    claim_data["claim_id"] = f"claim_{uuid.uuid4().hex[:8]}"
                
                # Validate verbatim_quote is exact substring (HARD REQUIREMENT)
                verbatim = claim_data.get("verbatim_quote")
                if verbatim:
                    # First try exact match
                    if verbatim in chunk_text:
                        pass  # Valid, keep as-is
                    else:
                        # Try normalization (whitespace differences)
                        verbatim_normalized = re.sub(r'\s+', ' ', verbatim.strip())
                        chunk_normalized = re.sub(r'\s+', ' ', chunk_text)
                        if verbatim_normalized in chunk_normalized:
                            # Update verbatim_quote to normalized version for consistency
                            claim_data["verbatim_quote"] = verbatim_normalized
                        else:
                            # Not found even after normalization - DISCARD (hard requirement)
                            logger.warning(f"verbatim_quote not found in chunk (even after normalization), discarding: {verbatim[:50]}...")
                            continue
                
                # Build Citation if URL provided
                if "citations" not in claim_data or not claim_data["citations"]:
                    claim_data["citations"] = []
                
                # Validate and create Claim
                claim = Claim.model_validate(claim_data)
                validated_claims.append(claim)
            
            except ValidationError as e:
                logger.warning(f"Validation error for claim: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing claim: {e}")
                continue
        
        return validated_claims
    
    except Exception as e:
        logger.exception(f"Error canonicalizing claims with OpenAI: {e}")
        return []


def _similarity_score(text1: str, text2: str) -> float:
    """
    Compute simple similarity score between two texts (0.0-1.0).
    
    Uses word overlap and edit distance approximation.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score (0.0 = completely different, 1.0 = identical)
    """
    # Normalize and tokenize
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity (word overlap)
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    if union == 0:
        return 0.0
    
    jaccard = intersection / union
    
    # Also check if one is substring of the other (high similarity)
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    if text1_lower in text2_lower or text2_lower in text1_lower:
        substring_bonus = 0.3
        jaccard = min(1.0, jaccard + substring_bonus)
    
    return jaccard


def _dedupe_claims(claims: list[Claim]) -> list[Claim]:
    """
    Deduplicate claims by canonical_claim similarity and merge citations.
    
    Args:
        claims: List of Claim objects
        
    Returns:
        Deduplicated list of Claim objects with merged citations
    """
    if not claims:
        return []
    
    # Group by similarity
    SIMILARITY_THRESHOLD = 0.7
    
    deduped: list[Claim] = []
    processed = set()
    
    for i, claim in enumerate(claims):
        if i in processed:
            continue
        
        # Find similar claims
        similar_group = [claim]
        processed.add(i)
        
        for j, other_claim in enumerate(claims[i+1:], start=i+1):
            if j in processed:
                continue
            
            similarity = _similarity_score(claim.canonical_claim, other_claim.canonical_claim)
            if similarity >= SIMILARITY_THRESHOLD:
                similar_group.append(other_claim)
                processed.add(j)
        
        # Merge citations from similar claims
        all_citations = []
        seen_citations = set()
        
        for similar_claim in similar_group:
            for citation in similar_claim.citations:
                # Create citation key for deduplication
                citation_key = (citation.url, citation.locator or "")
                if citation_key not in seen_citations:
                    all_citations.append(citation)
                    seen_citations.add(citation_key)
        
        # Use the first (or best) claim as base, merge citations
        merged_claim = similar_group[0].model_copy()
        merged_claim.citations = all_citations
        
        # Use highest confidence
        merged_claim.confidence = max(c.confidence for c in similar_group)
        
        deduped.append(merged_claim)
    
    return deduped


def extract_claims(
    transcripts: list[TranscriptItem],
    web_sources: list[SourceItem],
    max_chunks: int = 50,   # Reduced from 100 to prevent memory exhaustion
    batch_size: int = 5,    # Reduced from 10 for more frequent memory cleanup
) -> tuple[list[Claim], str, str]:
    """
    Extract claims from transcripts and web sources with memory-efficient batching.

    Args:
        transcripts: List of transcript items to extract from
        web_sources: List of web source items to extract from
        max_chunks: Maximum total chunks to process (prevents memory exhaustion)
        batch_size: Number of chunks to process before deduplicating and clearing memory

    Returns:
        Tuple of (claims list, quote_bank_md, claims_ledger_md)

    Raises:
        MissingRequiredSettingError: If OPENAI_API_KEY is not configured
    """
    try:
        settings = require_openai()
        api_key = settings.openai_api_key
    except MissingRequiredSettingError:
        logger.warning("OpenAI API key not configured. Returning empty extraction results.")
        return [], "# Quote Bank\n\n*OpenAI API key required for claim extraction.*", "# Claims Ledger\n\n*OpenAI API key required.*"

    all_claims: list[Claim] = []
    chunks_processed = 0
    batch_claims: list[Claim] = []

    logger.info(f"Starting claim extraction from {len(transcripts)} transcripts and {len(web_sources)} web sources")
    logger.info(f"Memory optimization: max_chunks={max_chunks}, batch_size={batch_size}")

    # Process transcripts
    for transcript_idx, transcript in enumerate(transcripts):
        if chunks_processed >= max_chunks:
            logger.warning(f"Reached max_chunks limit ({max_chunks}). Stopping transcript processing.")
            break

        # Check memory pressure before processing
        is_critical, mem_pct = _check_memory_pressure()
        if is_critical:
            logger.warning(f"Memory critical ({mem_pct:.1f}%). Stopping transcript processing early.")
            break

        if not transcript.text or transcript.status != "available":
            continue

        logger.info(f"Processing transcript {transcript_idx + 1}/{len(transcripts)}: {transcript.video_url}")
        chunks = _chunk_transcript_text(transcript.text)
        logger.info(f"  Generated {len(chunks)} chunks from transcript")

        for chunk_idx, (chunk_text, start_idx, end_idx) in enumerate(chunks):
            if chunks_processed >= max_chunks:
                logger.warning(f"Reached max_chunks limit ({max_chunks}). Stopping chunk processing.")
                break

            # Check memory pressure before each chunk
            is_critical, _ = _check_memory_pressure()
            if is_critical:
                logger.warning("Memory critical. Stopping chunk processing early.")
                break

            # Extract candidates
            candidates = _extract_claim_candidates(chunk_text)

            if not candidates:
                chunks_processed += 1
                continue

            logger.debug(f"  Chunk {chunk_idx + 1}/{len(chunks)}: {len(candidates)} candidates")

            # Canonicalize with OpenAI
            claims = _canonicalize_claims_with_openai(candidates, chunk_text, api_key)

            # Add citations to claims
            for claim in claims:
                # Add transcript citation
                citation = Citation(
                    url=transcript.video_url,
                    locator=f"Word {start_idx}-{end_idx}",  # Approximate location
                )
                if not claim.citations:
                    claim.citations = []
                claim.citations.append(citation)

            batch_claims.extend(claims)
            chunks_processed += 1

            # Cleanup after each chunk to prevent memory buildup
            del candidates, claims
            gc.collect()

            # Batch processing: deduplicate and merge every batch_size chunks (reduced threshold)
            if len(batch_claims) >= batch_size * 3:  # Reduced from batch_size * 5
                logger.info(f"  Batch deduplication: {len(batch_claims)} claims in batch")
                batch_deduped = _dedupe_claims(batch_claims)
                all_claims.extend(batch_deduped)
                batch_claims = []  # Clear batch memory
                gc.collect()  # Force garbage collection to free memory
                logger.info(f"  After dedup: {len(batch_deduped)} unique claims. Total: {len(all_claims)}")

    # Process web sources
    for source_idx, source in enumerate(web_sources):
        if chunks_processed >= max_chunks:
            logger.warning(f"Reached max_chunks limit ({max_chunks}). Stopping web source processing.")
            break

        # Check memory pressure before processing
        is_critical, mem_pct = _check_memory_pressure()
        if is_critical:
            logger.warning(f"Memory critical ({mem_pct:.1f}%). Stopping web source processing early.")
            break

        if not source.text:
            continue

        logger.info(f"Processing web source {source_idx + 1}/{len(web_sources)}: {source.url}")
        chunks = _chunk_web_text(source.text)
        logger.info(f"  Generated {len(chunks)} chunks from web source")

        for chunk_idx, (chunk_text, start_idx, end_idx) in enumerate(chunks):
            if chunks_processed >= max_chunks:
                logger.warning(f"Reached max_chunks limit ({max_chunks}). Stopping chunk processing.")
                break

            # Check memory pressure before each chunk
            is_critical, _ = _check_memory_pressure()
            if is_critical:
                logger.warning("Memory critical. Stopping chunk processing early.")
                break

            # Extract candidates
            candidates = _extract_claim_candidates(chunk_text)

            if not candidates:
                chunks_processed += 1
                continue

            logger.debug(f"  Chunk {chunk_idx + 1}/{len(chunks)}: {len(candidates)} candidates")

            # Canonicalize with OpenAI
            claims = _canonicalize_claims_with_openai(candidates, chunk_text, api_key)

            # Add citations to claims
            for claim in claims:
                citation = Citation(
                    url=source.url,
                    locator=f"Word {start_idx}-{end_idx}",
                )
                if not claim.citations:
                    claim.citations = []
                claim.citations.append(citation)

            batch_claims.extend(claims)
            chunks_processed += 1

            # Cleanup after each chunk to prevent memory buildup
            del candidates, claims
            gc.collect()

            # Batch processing: deduplicate and merge every batch_size chunks (reduced threshold)
            if len(batch_claims) >= batch_size * 3:
                logger.info(f"  Batch deduplication: {len(batch_claims)} claims in batch")
                batch_deduped = _dedupe_claims(batch_claims)
                all_claims.extend(batch_deduped)
                batch_claims = []  # Clear batch memory
                gc.collect()  # Force garbage collection to free memory
                logger.info(f"  After dedup: {len(batch_deduped)} unique claims. Total: {len(all_claims)}")

    # Process remaining batch claims
    if batch_claims:
        logger.info(f"Final batch deduplication: {len(batch_claims)} claims in batch")
        batch_deduped = _dedupe_claims(batch_claims)
        all_claims.extend(batch_deduped)
        batch_claims = []
        gc.collect()  # Force garbage collection to free memory
        logger.info(f"After final dedup: {len(batch_deduped)} unique claims. Total: {len(all_claims)}")

    # Final deduplicate across all batches
    logger.info(f"Final global deduplication: {len(all_claims)} claims before final dedup")
    deduped_claims = _dedupe_claims(all_claims)
    logger.info(f"Extraction complete: {len(deduped_claims)} unique claims extracted from {chunks_processed} chunks")

    # Generate markdown outputs
    quote_bank_md = _generate_quote_bank_md(deduped_claims)
    claims_ledger_md = _generate_claims_ledger_md(deduped_claims)

    return deduped_claims, quote_bank_md, claims_ledger_md


def _generate_quote_bank_md(claims: list[Claim]) -> str:
    """
    Generate quote bank markdown grouped by topic/entity.
    
    Args:
        claims: List of Claim objects
        
    Returns:
        Markdown string
    """
    lines = ["# Quote Bank", ""]
    
    if not claims:
        lines.append("*No quotes extracted.*")
        return "\n".join(lines)
    
    # Group by primary entity (first entity in list)
    by_entity: dict[str, list[Claim]] = defaultdict(list)
    ungrouped = []
    
    for claim in claims:
        if claim.entities:
            primary_entity = claim.entities[0]
            by_entity[primary_entity].append(claim)
        else:
            ungrouped.append(claim)
    
    # Sort entities
    for entity in sorted(by_entity.keys()):
        lines.append(f"## {entity}")
        lines.append("")
        
        for claim in by_entity[entity]:
            if claim.verbatim_quote:
                # Format citation
                citation_strs = []
                for citation in claim.citations:
                    if citation.locator:
                        citation_strs.append(f"[{citation.locator}]({citation.url})")
                    else:
                        citation_strs.append(f"[Source]({citation.url})")
                
                citation_block = " | ".join(citation_strs)
                lines.append(f"> {claim.verbatim_quote}")
                lines.append("")
                lines.append(f"*Citation: {citation_block}*")
                lines.append("")
    
    # Ungrouped claims
    if ungrouped:
        lines.append("## Other")
        lines.append("")
        for claim in ungrouped:
            if claim.verbatim_quote:
                citation_strs = []
                for citation in claim.citations:
                    if citation.locator:
                        citation_strs.append(f"[{citation.locator}]({citation.url})")
                    else:
                        citation_strs.append(f"[Source]({citation.url})")
                
                citation_block = " | ".join(citation_strs)
                lines.append(f"> {claim.verbatim_quote}")
                lines.append("")
                lines.append(f"*Citation: {citation_block}*")
                lines.append("")
    
    return "\n".join(lines)


def _generate_claims_ledger_md(claims: list[Claim]) -> str:
    """
    Generate claims ledger markdown table.
    
    Args:
        claims: List of Claim objects
        
    Returns:
        Markdown string with table
    """
    lines = [
        "# Claims Ledger",
        "",
        "| Claim ID | Canonical Claim | Type | Entities | Confidence | Citations |",
        "|----------|----------------|------|----------|------------|-----------|",
    ]
    
    if not claims:
        lines.append("| *No claims extracted* | | | | | |")
        return "\n".join(lines)
    
    for claim in claims:
        claim_id = claim.claim_id
        canonical = claim.canonical_claim[:100] + "..." if len(claim.canonical_claim) > 100 else claim.canonical_claim
        claim_type = claim.claim_type.value
        entities = ", ".join(claim.entities[:3])  # First 3 entities
        if len(claim.entities) > 3:
            entities += "..."
        confidence = f"{claim.confidence:.2f}"
        citation_count = str(len(claim.citations))
        
        lines.append(f"| {claim_id} | {canonical} | {claim_type} | {entities} | {confidence} | {citation_count} |")
    
    return "\n".join(lines)

