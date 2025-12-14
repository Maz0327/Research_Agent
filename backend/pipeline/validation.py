"""Claim validation using Perplexity AI."""
import re
from typing import Optional

from loguru import logger

from backend.config import require_perplexity, MissingRequiredSettingError
# Import internal function (it's not exported, so we import from module)
from backend.integrations import perplexity_client
from backend.models.claim import Claim, Citation, EvidenceRecord, EvidenceStatus
from backend.models.job_config import JobConfig


def _validate_single_claim(
    claim: Claim,
    topic: str,
    api_key: str,
    max_links_per_claim: int,
) -> EvidenceRecord:
    """
    Validate a single claim using Perplexity AI.
    
    Args:
        claim: Claim to validate
        topic: Research topic for context
        api_key: Perplexity API key
        max_links_per_claim: Maximum evidence links per claim
        
    Returns:
        EvidenceRecord with validation results
    """
    query = f"""Validate this claim about the topic "{topic}":

Claim: {claim.canonical_claim}

Original quote: {claim.verbatim_quote or "N/A"}

Task:
1. Determine if this claim is Verified, Debunked, or Unproven
2. Provide URLs that support the claim (evidence_for)
3. Provide URLs that contradict the claim (evidence_against)
4. Provide brief notes explaining your assessment

Focus on finding independent sources (news, official reports, fact-checks) that verify or debunk this claim.
Return evidence URLs in your response."""
    
    try:
        response = perplexity_client._perplexity_search(query, model="llama-3.1-sonar-large-128k-online")
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Extract URLs from response
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
        all_urls = re.findall(url_pattern, content)
        all_urls = [url.strip().rstrip('.,;:!?)') for url in all_urls]
        all_urls = list(dict.fromkeys(all_urls))  # Dedupe
        
        # Determine status from content
        content_lower = content.lower()
        status = EvidenceStatus.UNPROVEN  # Default
        
        if any(word in content_lower for word in ["verified", "confirmed", "true", "accurate", "correct"]):
            # Check for strong verification language
            if any(word in content_lower for word in ["debunked", "false", "incorrect", "wrong", "inaccurate"]):
                # Mixed - determine which is stronger
                verify_count = sum(1 for word in ["verified", "confirmed", "true"] if word in content_lower)
                debunk_count = sum(1 for word in ["debunked", "false", "incorrect"] if word in content_lower)
                if debunk_count > verify_count:
                    status = EvidenceStatus.DEBUNKED
                else:
                    status = EvidenceStatus.VERIFIED
            else:
                status = EvidenceStatus.VERIFIED
        elif any(word in content_lower for word in ["debunked", "false", "incorrect", "wrong", "inaccurate", "disproven"]):
            status = EvidenceStatus.DEBUNKED
        
        # Split URLs into evidence_for and evidence_against (heuristic)
        # This is approximate - ideally Perplexity would structure this, but we work with what we have
        evidence_for_urls = []
        evidence_against_urls = []
        
        # Simple heuristic: URLs mentioned near positive language go to evidence_for
        # URLs mentioned near negative language go to evidence_against
        # For now, split evenly if we can't determine
        if status == EvidenceStatus.VERIFIED:
            evidence_for_urls = all_urls[:max_links_per_claim]
        elif status == EvidenceStatus.DEBUNKED:
            evidence_against_urls = all_urls[:max_links_per_claim]
        else:
            # Unproven - split URLs
            mid = len(all_urls) // 2
            evidence_for_urls = all_urls[:mid]
            evidence_against_urls = all_urls[mid:mid + max_links_per_claim]
        
        # Cap to max_links_per_claim
        evidence_for_urls = evidence_for_urls[:max_links_per_claim]
        evidence_against_urls = evidence_against_urls[:max_links_per_claim]
        
        # Create Citation objects
        evidence_for = [Citation(url=url) for url in evidence_for_urls]
        evidence_against = [Citation(url=url) for url in evidence_against_urls]
        
        # Extract notes (first 500 chars of response, or custom note)
        notes = content[:500] + "..." if len(content) > 500 else content
        if not notes.strip():
            notes = f"Validation result: {status.value}"
        
        return EvidenceRecord(
            claim_id=claim.claim_id,
            status=status,
            evidence_for=evidence_for,
            evidence_against=evidence_against,
            notes=notes,
        )
    
    except Exception as e:
        logger.warning(f"Failed to validate claim {claim.claim_id}: {e}")
        return EvidenceRecord(
            claim_id=claim.claim_id,
            status=EvidenceStatus.UNPROVEN,
            evidence_for=[],
            evidence_against=[],
            notes=f"Validation failed: {str(e)}",
        )


def _run_missing_angles_analysis(
    topic: str,
    claims: list[Claim],
    api_key: str,
) -> str:
    """
    Run "Referee / Missing Angles" analysis for the whole topic.
    
    Args:
        topic: Research topic
        claims: List of extracted claims
        api_key: Perplexity API key
        
    Returns:
        Markdown text with missing angles analysis
    """
    # Summarize claims for context
    claims_summary = "\n".join(f"- {claim.canonical_claim}" for claim in claims[:20])  # Top 20
    
    query = f"""Analyze this research topic and claims list to identify missing angles or perspectives:

Topic: {topic}

Current claims extracted:
{claims_summary}

Task:
1. Identify important angles or perspectives that are missing from the current claims
2. Suggest what additional research or sources would be valuable
3. Point out potential biases or one-sided narratives
4. Recommend areas that need more investigation

Provide a structured analysis with clear recommendations."""
    
    try:
        response = perplexity_client._perplexity_search(query, model="llama-3.1-sonar-large-128k-online")
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content
    except Exception as e:
        logger.warning(f"Failed to run missing angles analysis: {e}")
        return f"# Missing Angles Analysis\n\n*Analysis failed: {str(e)}*"


def validate_claims(
    claims: list[Claim],
    job: JobConfig,
) -> tuple[list[EvidenceRecord], str, str]:
    """
    Validate claims using Perplexity AI.
    
    Args:
        claims: List of Claim objects to validate
        job: JobConfig with budgets and topic
        
    Returns:
        Tuple of (evidence_records, evidence_table_md, missing_angles_md)
        
    Raises:
        MissingRequiredSettingError: If PERPLEXITY_API_KEY is not configured
    """
    # Validate inputs
    if not claims:
        logger.warning("No claims provided for validation")
        return [], "# Evidence Table\n\n*No claims to validate.*", "# Missing Angles\n\n*No claims available.*"
    
    try:
        settings = require_perplexity()
        api_key = settings.perplexity_api_key
    except MissingRequiredSettingError:
        logger.warning("Perplexity API key not configured. Returning empty validation results.")
        return (
            [],
            "# Evidence Table\n\n*Perplexity API key required for claim validation.*",
            "# Missing Angles\n\n*Perplexity API key required for analysis.*",
        )
    
    # Select top N claims (by confidence or just first N)
    # Sort by confidence descending
    sorted_claims = sorted(claims, key=lambda c: c.confidence, reverse=True)
    claims_to_validate = sorted_claims[:job.budgets.max_claims_to_validate]
    
    logger.info(f"Validating {len(claims_to_validate)} claims (top {job.budgets.max_claims_to_validate} by confidence)")
    
    evidence_records: list[EvidenceRecord] = []
    
    # Validate each claim
    for claim in claims_to_validate:
        try:
            evidence_record = _validate_single_claim(
                claim,
                job.topic,
                api_key,
                job.budgets.max_validation_links_per_claim,
            )
            evidence_records.append(evidence_record)
        except Exception as e:
            logger.warning(f"Failed to validate claim {claim.claim_id}: {e}")
            # Create unproven record with error note
            evidence_records.append(
                EvidenceRecord(
                    claim_id=claim.claim_id,
                    status=EvidenceStatus.UNPROVEN,
                    evidence_for=[],
                    evidence_against=[],
                    notes=f"Validation error: {str(e)}",
                )
            )
    
    # Run missing angles analysis
    try:
        missing_angles_md = _run_missing_angles_analysis(job.topic, claims, api_key)
    except Exception as e:
        logger.warning(f"Missing angles analysis failed: {e}")
        missing_angles_md = f"# Missing Angles\n\n*Analysis failed: {str(e)}*"
    
    # Generate evidence table markdown
    evidence_table_md = _generate_evidence_table_md(claims, evidence_records, job.topic)
    
    return evidence_records, evidence_table_md, missing_angles_md


def _generate_evidence_table_md(
    claims: list[Claim],
    evidence_records: list[EvidenceRecord],
    topic: str,
) -> str:
    """
    Generate evidence table markdown.
    
    Args:
        claims: List of all claims
        evidence_records: List of EvidenceRecord objects
        topic: Research topic
        
    Returns:
        Markdown string with evidence table
    """
    lines = [
        "# Evidence Table",
        "",
        f"**Topic:** {topic}",
        f"**Claims Validated:** {len(evidence_records)}",
        "",
        "| Claim ID | Canonical Claim | Status | Evidence For | Evidence Against | Notes |",
        "|----------|----------------|--------|--------------|------------------|-------|",
    ]
    
    if not evidence_records:
        lines.append("| *No claims validated* | | | | | |")
        return "\n".join(lines)
    
    # Create lookup for claims
    claims_by_id = {claim.claim_id: claim for claim in claims}
    
    for evidence in evidence_records:
        claim = claims_by_id.get(evidence.claim_id)
        canonical = claim.canonical_claim if claim else evidence.claim_id
        canonical = canonical[:80] + "..." if len(canonical) > 80 else canonical
        
        status = evidence.status.value
        evidence_for_count = len(evidence.evidence_for)
        evidence_against_count = len(evidence.evidence_against)
        
        # Truncate notes
        notes = evidence.notes or ""
        notes = notes[:100] + "..." if len(notes) > 100 else notes
        
        lines.append(
            f"| {evidence.claim_id} | {canonical} | {status} | {evidence_for_count} | {evidence_against_count} | {notes} |"
        )
    
    # Add detailed evidence section
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Evidence")
    lines.append("")
    
    for evidence in evidence_records:
        claim = claims_by_id.get(evidence.claim_id)
        canonical = claim.canonical_claim if claim else evidence.claim_id
        
        lines.append(f"### {evidence.claim_id}: {canonical[:100]}")
        lines.append("")
        lines.append(f"**Status:** {evidence.status.value}")
        lines.append("")
        
        if evidence.evidence_for:
            lines.append("**Evidence For:**")
            for citation in evidence.evidence_for:
                lines.append(f"- [{citation.url}]({citation.url})")
            lines.append("")
        
        if evidence.evidence_against:
            lines.append("**Evidence Against:**")
            for citation in evidence.evidence_against:
                lines.append(f"- [{citation.url}]({citation.url})")
            lines.append("")
        
        if evidence.notes:
            lines.append(f"**Notes:** {evidence.notes}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)

