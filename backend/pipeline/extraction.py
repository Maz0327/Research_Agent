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

try:
    from datasketch import MinHash, MinHashLSH
    MINHASH_AVAILABLE = True
except ImportError:
    MINHASH_AVAILABLE = False
    logger.warning("datasketch not installed. Using fallback O(n²) dedup. Install with: pip install datasketch")

from backend.config import require_openai, MissingRequiredSettingError
from backend.integrations.transcripts import TranscriptItem
from backend.models.claim import Claim, Citation
from backend.models.source import SourceItem


# Memory thresholds for extraction
MEMORY_WARNING_THRESHOLD = 75  # Log warning at 75% memory usage
MEMORY_CRITICAL_THRESHOLD = 85  # Stop processing at 85% memory usage


def _log_memory(label: str) -> float:
    """
    Log current memory usage for debugging.

    Args:
        label: Description of current operation

    Returns:
        Memory usage in MB
    """
    if not PSUTIL_AVAILABLE:
        return 0.0

    try:
        import os
        process = psutil.Process(os.getpid())
        mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"[MEMORY] {label}: {mb:.1f} MB")
        return mb
    except Exception:
        return 0.0


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


def _chunk_transcript_text(text: str):
    """
    Chunk transcript text into 1-3 minute windows (~1200-2000 words).

    MEMORY OPTIMIZED: Uses generator to avoid materializing all chunks.

    Args:
        text: Transcript text

    Yields:
        Tuples: (chunk_text, start_word_idx, end_word_idx)
    """
    words = text.split()
    total_words = len(words)

    start = 0
    while start < total_words:
        # Target chunk size in middle of range
        target_size = (TRANSCRIPT_CHUNK_WORDS_MIN + TRANSCRIPT_CHUNK_WORDS_MAX) // 2
        end = min(start + target_size, total_words)

        chunk_text = " ".join(words[start:end])
        yield (chunk_text, start, end)

        # Overlap by ~100 words (reduced from 200 to save memory)
        start = end - 100
        if start >= total_words:
            break

    # Explicit cleanup
    del words


def _chunk_web_text(text: str):
    """
    Chunk web text into ~1500-2500 token segments.

    MEMORY OPTIMIZED: Uses generator to avoid materializing all chunks.

    Args:
        text: Web article text

    Yields:
        Tuples: (chunk_text, start_word_idx, end_word_idx)
    """
    words = text.split()
    total_words = len(words)

    # Convert token ranges to word ranges (approximate)
    words_min = int(WEB_CHUNK_TOKENS_MIN / TOKENS_PER_WORD)
    words_max = int(WEB_CHUNK_TOKENS_MAX / TOKENS_PER_WORD)

    start = 0
    while start < total_words:
        target_size = (words_min + words_max) // 2
        end = min(start + target_size, total_words)

        chunk_text = " ".join(words[start:end])
        yield (chunk_text, start, end)

        # Overlap by ~100 words (reduced from 200 to save memory)
        start = end - 100
        if start >= total_words:
            break

    # Explicit cleanup
    del words


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
        
        # Minimum score threshold (raised from 3 to 4 to reduce LLM calls ~30%)
        if score >= 4:
            candidates.append({
                "text": sentence,
                "score": score,
                "reasons": reasons,
            })
    
    return candidates


def _validate_openai_key(api_key: str) -> bool:
    """
    Validate OpenAI API key with a minimal test call.

    Args:
        api_key: OpenAI API key to validate

    Returns:
        True if key is valid, False otherwise
    """
    try:
        client = OpenAI(api_key=api_key)
        # Minimal API call to validate key (cheap and fast)
        client.models.list()
        return True
    except Exception as e:
        logger.error(f"OpenAI API key validation failed: {e}")
        return False


# Cache for validated API key (avoid repeated validation calls)
_validated_api_key: str | None = None


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
    global _validated_api_key

    if not candidates:
        return []

    # Skip if we already know the key is invalid
    if _validated_api_key is False:
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


def _dedupe_claims_minhash(claims: list[Claim], threshold: float = 0.7) -> list[Claim]:
    """
    Deduplicate claims using MinHash LSH (O(n) complexity).

    Research-validated optimization (Dec 2025):
    - Replaces O(n²) Jaccard similarity with O(n) MinHash LSH
    - Scales linearly with claim count instead of quadratically

    Args:
        claims: List of Claim objects
        threshold: Similarity threshold for grouping (default 0.7)

    Returns:
        Deduplicated list of Claim objects with merged citations
    """
    if not claims:
        return []

    if len(claims) < 10:
        # For small sets, O(n²) is fine and avoids LSH overhead
        return _dedupe_claims_fallback(claims, threshold)

    logger.info(f"MinHash LSH dedup: {len(claims)} claims (threshold={threshold})")

    # Build LSH index
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    minhashes: dict[int, MinHash] = {}

    for i, claim in enumerate(claims):
        m = MinHash(num_perm=128)
        # Tokenize and hash words
        for word in claim.canonical_claim.lower().split():
            m.update(word.encode('utf8'))
        lsh.insert(f"claim_{i}", m)
        minhashes[i] = m

    # Group similar claims
    deduped: list[Claim] = []
    processed: set[int] = set()

    for i in range(len(claims)):
        if i in processed:
            continue

        # Query LSH for similar claims
        similar_ids = lsh.query(minhashes[i])
        group_indices = [int(s.split('_')[1]) for s in similar_ids]
        processed.update(group_indices)

        # Build similar group
        similar_group = [claims[idx] for idx in group_indices]

        # Merge citations from similar claims
        all_citations: list[Citation] = []
        seen_citations: set[tuple] = set()

        for similar_claim in similar_group:
            for citation in similar_claim.citations:
                citation_key = (citation.url, citation.locator or "")
                if citation_key not in seen_citations:
                    all_citations.append(citation)
                    seen_citations.add(citation_key)

        # Use highest confidence claim as base
        best_idx = max(group_indices, key=lambda idx: claims[idx].confidence)
        merged_claim = claims[best_idx].model_copy()
        merged_claim.citations = all_citations
        merged_claim.confidence = max(c.confidence for c in similar_group)

        deduped.append(merged_claim)

    logger.info(f"MinHash dedup: {len(claims)} → {len(deduped)} claims")
    return deduped


def _dedupe_claims_fallback(claims: list[Claim], threshold: float = 0.7) -> list[Claim]:
    """
    Fallback O(n²) deduplication when MinHash is not available or for small sets.

    Args:
        claims: List of Claim objects
        threshold: Similarity threshold

    Returns:
        Deduplicated list of Claim objects with merged citations
    """
    if not claims:
        return []

    deduped: list[Claim] = []
    processed: set[int] = set()

    for i, claim in enumerate(claims):
        if i in processed:
            continue

        similar_group = [claim]
        processed.add(i)

        for j, other_claim in enumerate(claims[i+1:], start=i+1):
            if j in processed:
                continue

            similarity = _similarity_score(claim.canonical_claim, other_claim.canonical_claim)
            if similarity >= threshold:
                similar_group.append(other_claim)
                processed.add(j)

        # Merge citations
        all_citations: list[Citation] = []
        seen_citations: set[tuple] = set()

        for similar_claim in similar_group:
            for citation in similar_claim.citations:
                citation_key = (citation.url, citation.locator or "")
                if citation_key not in seen_citations:
                    all_citations.append(citation)
                    seen_citations.add(citation_key)

        merged_claim = similar_group[0].model_copy()
        merged_claim.citations = all_citations
        merged_claim.confidence = max(c.confidence for c in similar_group)

        deduped.append(merged_claim)

    return deduped


def _dedupe_claims(claims: list[Claim]) -> list[Claim]:
    """
    Deduplicate claims by canonical_claim similarity and merge citations.

    Uses MinHash LSH for O(n) complexity when available, falls back to O(n²).

    Args:
        claims: List of Claim objects

    Returns:
        Deduplicated list of Claim objects with merged citations
    """
    if MINHASH_AVAILABLE:
        return _dedupe_claims_minhash(claims)
    else:
        return _dedupe_claims_fallback(claims)


def extract_claims(
    transcripts: list[TranscriptItem],
    web_sources: list[SourceItem],
    max_chunks: int = 30,   # Reduced from 50 for memory safety
    batch_size: int = 2,    # Process 2 chunks at a time (reduced from 5)
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
    global _validated_api_key

    try:
        settings = require_openai()
        api_key = settings.openai_api_key
    except MissingRequiredSettingError:
        logger.warning("OpenAI API key not configured. Returning empty extraction results.")
        return [], "# Quote Bank\n\n*OpenAI API key required for claim extraction.*", "# Claims Ledger\n\n*OpenAI API key required.*"

    # Early validation: Check API key ONCE before processing any chunks
    # This prevents dozens of failed API calls that waste memory
    if _validated_api_key != api_key:
        logger.info("Validating OpenAI API key before extraction...")
        if _validate_openai_key(api_key):
            _validated_api_key = api_key
            logger.info("OpenAI API key validated successfully")
        else:
            _validated_api_key = False  # type: ignore
            logger.error("OpenAI API key is invalid. Skipping claim extraction.")
            return [], "# Quote Bank\n\n*OpenAI API key is invalid. Please check your configuration.*", "# Claims Ledger\n\n*OpenAI API key invalid.*"

    all_claims: list[Claim] = []
    chunks_processed = 0
    batch_claims: list[Claim] = []

    _log_memory("Extraction start")
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

        _log_memory(f"Before transcript {transcript_idx + 1}/{len(transcripts)}")
        logger.info(f"Processing transcript {transcript_idx + 1}/{len(transcripts)}: {transcript.video_url}")

        # Store text for processing, then use generator
        transcript_text = transcript.text
        text_len = len(transcript_text)
        logger.info(f"  Transcript text length: {text_len} chars")

        chunk_idx = 0
        for chunk_text, start_idx, end_idx in _chunk_transcript_text(transcript_text):
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
                chunk_idx += 1
                del chunk_text  # Explicit cleanup
                continue

            logger.debug(f"  Chunk {chunk_idx + 1}: {len(candidates)} candidates")

            # Canonicalize with OpenAI
            claims = _canonicalize_claims_with_openai(candidates, chunk_text, api_key)

            # Cleanup chunk_text immediately after OpenAI call
            del chunk_text

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
            chunk_idx += 1

            # Cleanup after each chunk to prevent memory buildup
            del candidates, claims
            gc.collect()

            # Batch processing: deduplicate and merge every batch_size chunks
            if len(batch_claims) >= batch_size * 2:  # Reduced threshold for earlier cleanup
                logger.info(f"  Batch deduplication: {len(batch_claims)} claims in batch")
                batch_deduped = _dedupe_claims(batch_claims)
                all_claims.extend(batch_deduped)
                batch_claims = []  # Clear batch memory
                gc.collect()  # Force garbage collection to free memory
                logger.info(f"  After dedup: {len(batch_deduped)} unique claims. Total: {len(all_claims)}")

        # Cleanup transcript text after processing all its chunks
        del transcript_text
        gc.collect()
        _log_memory(f"After transcript {transcript_idx + 1}/{len(transcripts)}")

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

        _log_memory(f"Before source {source_idx + 1}/{len(web_sources)}")
        logger.info(f"Processing web source {source_idx + 1}/{len(web_sources)}: {source.url}")

        # Store text length for logging, then process as generator
        source_text = source.text
        text_len = len(source_text)
        logger.info(f"  Source text length: {text_len} chars")

        chunk_idx = 0
        for chunk_text, start_idx, end_idx in _chunk_web_text(source_text):
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
                chunk_idx += 1
                del chunk_text  # Explicit cleanup
                continue

            logger.debug(f"  Chunk {chunk_idx + 1}: {len(candidates)} candidates")

            # Canonicalize with OpenAI
            claims = _canonicalize_claims_with_openai(candidates, chunk_text, api_key)

            # Cleanup chunk_text immediately after OpenAI call
            del chunk_text

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
            chunk_idx += 1

            # Cleanup after each chunk to prevent memory buildup
            del candidates, claims
            gc.collect()

            # Batch processing: deduplicate and merge every batch_size chunks
            if len(batch_claims) >= batch_size * 2:  # Reduced threshold for earlier cleanup
                logger.info(f"  Batch deduplication: {len(batch_claims)} claims in batch")
                batch_deduped = _dedupe_claims(batch_claims)
                all_claims.extend(batch_deduped)
                batch_claims = []  # Clear batch memory
                gc.collect()  # Force garbage collection to free memory
                logger.info(f"  After dedup: {len(batch_deduped)} unique claims. Total: {len(all_claims)}")

        # Cleanup source text after processing all its chunks
        del source_text
        gc.collect()
        _log_memory(f"After source {source_idx + 1}/{len(web_sources)}")

    # Process remaining batch claims
    if batch_claims:
        logger.info(f"Final batch deduplication: {len(batch_claims)} claims in batch")
        batch_deduped = _dedupe_claims(batch_claims)
        all_claims.extend(batch_deduped)
        batch_claims = []
        gc.collect()  # Force garbage collection to free memory
        logger.info(f"After final dedup: {len(batch_deduped)} unique claims. Total: {len(all_claims)}")

    # Final deduplicate across all batches
    _log_memory("Before final dedup")
    logger.info(f"Final global deduplication: {len(all_claims)} claims before final dedup")
    deduped_claims = _dedupe_claims(all_claims)

    # Cleanup intermediate data
    del all_claims
    gc.collect()

    _log_memory("Extraction complete")
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

