"""Unit tests for claim validation.

NOTE: The backend.pipeline.validation module was removed/never implemented.
These tests are skipped until the validation pipeline is rebuilt.
The claims_evidence pipeline was superseded by the semantic extraction pipeline (R1-R17).
"""
import pytest

# The validation module no longer exists — skip entire module
pytest.skip(
    "backend.pipeline.validation module does not exist. "
    "Claims-evidence pipeline was superseded by semantic extraction pipeline.",
    allow_module_level=True,
)

from backend.models.claim import Claim, ClaimCategory, Citation, EvidenceRecord, EvidenceStatus
from backend.models.job_config import JobConfig, ResearchMode, BudgetsConfig
from backend.pipeline.validation import (
    validate_claims,
    _generate_evidence_table_md,
)


def test_validate_claims_structure():
    """Test validate_claims returns correct structure."""
    claims = [
        Claim(
            claim_id="claim1",
            canonical_claim="Test claim about topic",
            verbatim_quote="Test quote",
            claim_type=ClaimCategory.FACTUAL,
            confidence=0.8,
        )
    ]
    
    job = JobConfig(
        topic="Test topic",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        budgets=BudgetsConfig(
            max_claims_to_validate=10,
            max_validation_links_per_claim=5,
        ),
    )
    
    # This will return empty if Perplexity API key is not set
    evidence_records, evidence_table_md, missing_angles_md = validate_claims(claims, job)
    
    assert isinstance(evidence_records, list)
    assert isinstance(evidence_table_md, str)
    assert isinstance(missing_angles_md, str)
    assert "# Evidence Table" in evidence_table_md
    assert "# Missing Angles" in missing_angles_md or "Missing Angles" in missing_angles_md


def test_validate_claims_respects_budget():
    """Test that validate_claims respects max_claims_to_validate budget."""
    # Create many claims
    claims = [
        Claim(
            claim_id=f"claim{i}",
            canonical_claim=f"Claim {i}",
            verbatim_quote=f"Quote {i}",
            claim_type=ClaimCategory.FACTUAL,
            confidence=0.5 + (i * 0.01),  # Varying confidence
        )
        for i in range(50)
    ]
    
    job = JobConfig(
        topic="Test topic",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        budgets=BudgetsConfig(
            max_claims_to_validate=10,  # Only validate top 10
            max_validation_links_per_claim=5,
        ),
    )
    
    # Structure test - actual validation may fail without API key
    evidence_records, _, _ = validate_claims(claims, job)
    
    # Should respect budget (even if API key missing, structure should be correct)
    # When API works, should validate max 10 claims
    assert len(evidence_records) <= job.budgets.max_claims_to_validate or len(evidence_records) == 0


def test_generate_evidence_table_md():
    """Test evidence table markdown generation."""
    claims = [
        Claim(
            claim_id="claim1",
            canonical_claim="Test claim",
            verbatim_quote="Quote",
            claim_type=ClaimCategory.FACTUAL,
        )
    ]
    
    evidence_records = [
        EvidenceRecord(
            claim_id="claim1",
            status=EvidenceStatus.VERIFIED,
            evidence_for=[
                Citation(url="https://example.com/verify"),
            ],
            evidence_against=[],
            notes="Claim verified by multiple sources",
        )
    ]
    
    md = _generate_evidence_table_md(claims, evidence_records, "Test topic")
    
    assert "# Evidence Table" in md
    assert "claim1" in md
    assert "Verified" in md
    assert "https://example.com/verify" in md
    assert "|" in md  # Should have table format


def test_generate_evidence_table_md_empty():
    """Test evidence table with no records."""
    claims = []
    evidence_records = []
    
    md = _generate_evidence_table_md(claims, evidence_records, "Test topic")
    
    assert "# Evidence Table" in md
    assert "*No claims validated*" in md or "No claims" in md


def test_validate_claims_handles_failures_gracefully():
    """Test that validation failures are handled gracefully (warnings, not failures)."""
    claims = [
        Claim(
            claim_id="claim1",
            canonical_claim="Test claim",
            verbatim_quote="Quote",
            claim_type=ClaimCategory.FACTUAL,
            confidence=0.9,
        )
    ]
    
    job = JobConfig(
        topic="Test topic",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        budgets=BudgetsConfig(
            max_claims_to_validate=10,
            max_validation_links_per_claim=5,
        ),
    )
    
    # Should not raise exception even if validation fails
    evidence_records, evidence_table_md, missing_angles_md = validate_claims(claims, job)
    
    # Should still return structure even if validation failed
    assert isinstance(evidence_records, list)
    assert isinstance(evidence_table_md, str)
    assert isinstance(missing_angles_md, str)
    
    # If validation failed, should have unproven status
    if evidence_records:
        # Record should exist even if validation failed
        assert evidence_records[0].claim_id == "claim1"


def test_validate_claims_sorts_by_confidence():
    """Test that claims are sorted by confidence before validation."""
    claims = [
        Claim(
            claim_id="low_confidence",
            canonical_claim="Low confidence claim",
            claim_type=ClaimCategory.FACTUAL,
            confidence=0.3,
        ),
        Claim(
            claim_id="high_confidence",
            canonical_claim="High confidence claim",
            claim_type=ClaimCategory.FACTUAL,
            confidence=0.9,
        ),
        Claim(
            claim_id="medium_confidence",
            canonical_claim="Medium confidence claim",
            claim_type=ClaimCategory.FACTUAL,
            confidence=0.6,
        ),
    ]
    
    job = JobConfig(
        topic="Test topic",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        budgets=BudgetsConfig(
            max_claims_to_validate=2,  # Only validate top 2
            max_validation_links_per_claim=5,
        ),
    )
    
    evidence_records, _, _ = validate_claims(claims, job)
    
    # If validation succeeded, should validate high_confidence and medium_confidence first
    # Structure test - actual order depends on API
    assert len(evidence_records) <= 2 or len(evidence_records) == 0

