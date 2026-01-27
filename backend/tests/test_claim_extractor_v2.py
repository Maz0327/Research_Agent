"""
Tests for Claim Extractor v2 functionality.

Tests cover:
1. Anchor validation (timestamp vs line)
2. Entity Index schema
3. Warning codes
4. ClaimsDocument structure
"""
import pytest
from datetime import datetime, timezone

from backend.models.claims import (
    AnchorType,
    Claim,
    ClaimAnchor,
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
    SourceSummary,
    SourceType,
    TimestampAnchor,
    WarningCode,
)


class TestAnchorModels:
    """Tests for anchor models and validation."""

    def test_timestamp_anchor_creation(self):
        """Test creating a timestamp anchor."""
        anchor = TimestampAnchor(
            start_seconds=120,
            end_seconds=145,
            formatted="2:00-2:25",
            source_id="SRC_001",
        )
        assert anchor.start_seconds == 120
        assert anchor.end_seconds == 145
        assert anchor.formatted == "2:00-2:25"
        assert anchor.source_id == "SRC_001"

    def test_timestamp_anchor_requires_non_negative(self):
        """Test that timestamp seconds must be non-negative."""
        with pytest.raises(ValueError):
            TimestampAnchor(
                start_seconds=-5,
                end_seconds=10,
                formatted="-0:05-0:10",
            )

    def test_line_range_anchor_creation(self):
        """Test creating a line range anchor."""
        anchor = LineRangeAnchor(
            start_line=10,
            end_line=15,
            excerpt="This is the verbatim text from the source.",
            source_id="SRC_002",
        )
        assert anchor.start_line == 10
        assert anchor.end_line == 15
        assert anchor.excerpt == "This is the verbatim text from the source."
        assert anchor.source_id == "SRC_002"

    def test_line_range_anchor_requires_positive_lines(self):
        """Test that line numbers must be positive (1-indexed)."""
        with pytest.raises(ValueError):
            LineRangeAnchor(start_line=0, end_line=5, excerpt="test")

    def test_claim_anchor_get_anchor_type(self):
        """Test ClaimAnchor.get_anchor_type() returns correct type."""
        # Timestamp anchor
        ts_anchor = ClaimAnchor(
            timestamp=TimestampAnchor(start_seconds=60, formatted="1:00"),
        )
        assert ts_anchor.get_anchor_type() == AnchorType.YOUTUBE_TIMESTAMP

        # Line range anchor
        line_anchor = ClaimAnchor(
            line_range=LineRangeAnchor(start_line=1, end_line=5, excerpt="test"),
        )
        assert line_anchor.get_anchor_type() == AnchorType.TEXT_LINE_RANGE

        # Image anchor
        img_anchor = ClaimAnchor(
            image=ImageAnchor(image_index=0, region="center"),
        )
        assert img_anchor.get_anchor_type() == AnchorType.IMAGE_INDEX

    def test_claim_anchor_get_source_id(self):
        """Test ClaimAnchor.get_source_id() from nested or top-level."""
        # Source ID on ClaimAnchor
        anchor1 = ClaimAnchor(
            line_range=LineRangeAnchor(start_line=1, end_line=5),
            source_id="SRC_001",
        )
        assert anchor1.get_source_id() == "SRC_001"

        # Source ID on nested anchor
        anchor2 = ClaimAnchor(
            timestamp=TimestampAnchor(
                start_seconds=60,
                formatted="1:00",
                source_id="SRC_002",
            ),
        )
        assert anchor2.get_source_id() == "SRC_002"

    def test_claim_anchor_has_valid_anchor(self):
        """Test ClaimAnchor.has_valid_anchor()."""
        # Valid anchor
        valid = ClaimAnchor(
            line_range=LineRangeAnchor(start_line=1, end_line=5),
        )
        assert valid.has_valid_anchor() is True

        # Empty anchor
        empty = ClaimAnchor()
        assert empty.has_valid_anchor() is False


class TestEntityModels:
    """Tests for Entity Index models."""

    def test_entity_creation(self):
        """Test creating an entity with required fields."""
        anchor = ClaimAnchor(
            line_range=LineRangeAnchor(
                start_line=5,
                end_line=7,
                excerpt="John Smith, the CEO of Acme Corp",
                source_id="SRC_001",
            ),
            source_id="SRC_001",
        )

        entity = Entity(
            entity_id="ENT_SRC_001_001",
            canonical_label="John Smith",
            entity_type=EntityType.PERSON,
            aliases=["J. Smith", "Smith"],
            context_summary="CEO of Acme Corp, mentioned discussing quarterly earnings.",
            context_evidence=[
                ContextEvidence(
                    excerpt="John Smith, the CEO of Acme Corp",
                    anchor=anchor,
                    source_id="SRC_001",
                )
            ],
            top_anchors=[anchor],
        )

        assert entity.entity_id == "ENT_SRC_001_001"
        assert entity.canonical_label == "John Smith"
        assert entity.entity_type == EntityType.PERSON
        assert len(entity.aliases) == 2
        assert len(entity.context_evidence) == 1

    def test_entity_requires_context_evidence(self):
        """Test that entity requires at least one context_evidence."""
        anchor = ClaimAnchor(
            line_range=LineRangeAnchor(start_line=1, end_line=1),
        )

        with pytest.raises(ValueError):
            Entity(
                entity_id="ENT_001",
                canonical_label="Test",
                entity_type=EntityType.PERSON,
                context_summary="Test summary",
                context_evidence=[],  # Empty - should fail
            )

    def test_unnamed_entity_type(self):
        """Test unnamed entities (e.g., 'their founders')."""
        anchor = ClaimAnchor(
            line_range=LineRangeAnchor(
                start_line=10,
                end_line=10,
                excerpt="according to their founders",
            ),
        )

        entity = Entity(
            entity_id="ENT_001",
            canonical_label="their founders",
            entity_type=EntityType.UNNAMED,
            context_summary="Unnamed founders referenced in the context of company history.",
            context_evidence=[
                ContextEvidence(
                    excerpt="according to their founders",
                    anchor=anchor,
                    source_id="SRC_001",
                )
            ],
        )

        assert entity.entity_type == EntityType.UNNAMED

    def test_entity_index_operations(self):
        """Test EntityIndex helper methods."""
        index = EntityIndex()

        # Create test entities
        person = Entity(
            entity_id="ENT_001",
            canonical_label="Alice",
            entity_type=EntityType.PERSON,
            context_summary="Test person",
            context_evidence=[
                ContextEvidence(
                    excerpt="Alice said",
                    anchor=ClaimAnchor(line_range=LineRangeAnchor(start_line=1, end_line=1)),
                    source_id="SRC_001",
                )
            ],
        )

        org = Entity(
            entity_id="ENT_002",
            canonical_label="Acme Corp",
            entity_type=EntityType.ORG,
            context_summary="Test org",
            context_evidence=[
                ContextEvidence(
                    excerpt="Acme Corp announced",
                    anchor=ClaimAnchor(line_range=LineRangeAnchor(start_line=2, end_line=2)),
                    source_id="SRC_001",
                )
            ],
        )

        index.people.append(person)
        index.orgs.append(org)

        # Test get_entity
        assert index.get_entity("ENT_001") == person
        assert index.get_entity("ENT_002") == org
        assert index.get_entity("ENT_999") is None

        # Test all_entities
        assert len(index.all_entities()) == 2

        # Test entity_count
        assert index.entity_count() == 2


class TestClaimsDocument:
    """Tests for ClaimsDocument structure."""

    def test_create_empty_document(self):
        """Test creating an empty claims document."""
        doc = ClaimsDocument.create_empty(
            job_id="test-job-123",
            title="Test Research",
            run_id="run_0",
        )

        assert doc.metadata.job_id == "test-job-123"
        assert doc.metadata.run_id == "run_0"
        assert doc.metadata.title == "Test Research"
        assert doc.metadata.version == "2.0"
        assert doc.metadata.total_claims == 0
        assert doc.metadata.total_entities == 0
        assert len(doc.claims) == 0
        assert len(doc.sources) == 0
        assert doc.entities.entity_count() == 0

    def test_add_claim(self):
        """Test adding a claim updates counts."""
        doc = ClaimsDocument.create_empty("job-1", "Test")

        claim = Claim(
            claim_id="CLM_SRC_001_001",
            text="The company reported record profits.",
            claim_type=ClaimType.EXPLICIT,
            confidence=ConfidenceLevel.HIGH,
            anchor=ClaimAnchor(
                line_range=LineRangeAnchor(start_line=5, end_line=5),
            ),
            source_id="SRC_001",
            verbatim_excerpt="reported record profits in Q4",
        )

        doc.add_claim(claim)

        assert doc.metadata.total_claims == 1
        assert doc.metadata.total_explicit == 1
        assert doc.metadata.total_implied == 0
        assert len(doc.claims) == 1

    def test_add_entity(self):
        """Test adding an entity updates counts and index."""
        doc = ClaimsDocument.create_empty("job-1", "Test")

        entity = Entity(
            entity_id="ENT_001",
            canonical_label="Test Person",
            entity_type=EntityType.PERSON,
            context_summary="A test person.",
            context_evidence=[
                ContextEvidence(
                    excerpt="Test Person said",
                    anchor=ClaimAnchor(line_range=LineRangeAnchor(start_line=1, end_line=1)),
                    source_id="SRC_001",
                )
            ],
        )

        doc.add_entity(entity)

        assert doc.metadata.total_entities == 1
        assert len(doc.entities.people) == 1

    def test_add_warning(self):
        """Test adding warnings."""
        doc = ClaimsDocument.create_empty("job-1", "Test")

        doc.add_warning(
            WarningCode.TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS,
            "Transcript timing unavailable for video",
            source_id="SRC_001",
        )

        assert len(doc.warnings) == 1
        assert doc.warnings[0].code == WarningCode.TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS
        assert doc.warnings[0].source_id == "SRC_001"

    def test_source_summary_with_timing(self):
        """Test SourceSummary with timing fields."""
        summary = SourceSummary(
            source_id="SRC_001",
            source_type=SourceType.YOUTUBE,
            title="Test Video",
            url="https://youtube.com/watch?v=abc",
            claim_count=5,
            explicit_count=3,
            implied_count=2,
            timing_available=True,
            anchor_type_used=AnchorType.YOUTUBE_TIMESTAMP,
            entity_count=3,
        )

        assert summary.timing_available is True
        assert summary.anchor_type_used == AnchorType.YOUTUBE_TIMESTAMP
        assert summary.entity_count == 3

    def test_claim_has_evidence(self):
        """Test Claim.has_evidence()."""
        # Claim with verbatim_excerpt
        claim1 = Claim(
            claim_id="CLM_001",
            text="Test claim",
            claim_type=ClaimType.EXPLICIT,
            confidence=ConfidenceLevel.HIGH,
            anchor=ClaimAnchor(),
            source_id="SRC_001",
            verbatim_excerpt="This is the verbatim excerpt.",
        )
        assert claim1.has_evidence() is True

        # Claim with excerpt in line_range
        claim2 = Claim(
            claim_id="CLM_002",
            text="Test claim",
            claim_type=ClaimType.EXPLICIT,
            confidence=ConfidenceLevel.HIGH,
            anchor=ClaimAnchor(
                line_range=LineRangeAnchor(
                    start_line=1,
                    end_line=1,
                    excerpt="Excerpt from anchor.",
                ),
            ),
            source_id="SRC_001",
        )
        assert claim2.has_evidence() is True

        # Claim without evidence
        claim3 = Claim(
            claim_id="CLM_003",
            text="Test claim",
            claim_type=ClaimType.EXPLICIT,
            confidence=ConfidenceLevel.HIGH,
            anchor=ClaimAnchor(
                line_range=LineRangeAnchor(start_line=1, end_line=1),
            ),
            source_id="SRC_001",
        )
        assert claim3.has_evidence() is False


class TestWarningCodes:
    """Tests for warning codes."""

    def test_warning_codes_exist(self):
        """Test all expected warning codes exist."""
        expected_codes = [
            "TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS",
            "TIMESTAMP_OUT_OF_BOUNDS",
            "TIMESTAMP_COERCED_TO_LINE",
            "ENTITY_MISSING_EVIDENCE",
            "COREFERENCE_UNRESOLVED",
            "CLAIM_MISSING_ANCHOR",
            "EMPTY_EXTRACTION",
        ]

        for code in expected_codes:
            assert hasattr(WarningCode, code), f"Missing warning code: {code}"

    def test_extraction_warning_creation(self):
        """Test creating extraction warnings."""
        warning = ExtractionWarning(
            code=WarningCode.TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS,
            message="Transcript timing unavailable for video; using line anchors",
            source_id="SRC_001",
            details={"original_url": "https://youtube.com/watch?v=abc"},
        )

        assert warning.code == WarningCode.TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS
        assert warning.source_id == "SRC_001"
        assert warning.details is not None


class TestClaimExtractionHelpers:
    """Tests for claim extraction helper functions."""

    def test_number_lines(self):
        """Test line numbering function."""
        from backend.pipeline.claim_extraction import number_lines

        text = "Line one\nLine two\nLine three"
        numbered = number_lines(text)

        assert "1: Line one" in numbered
        assert "2: Line two" in numbered
        assert "3: Line three" in numbered

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        from backend.pipeline.claim_extraction import format_timestamp

        assert format_timestamp(0) == "0:00"
        assert format_timestamp(65) == "1:05"
        assert format_timestamp(3661) == "1:01:01"

    def test_parse_transcript_segments_with_timing(self):
        """Test parsing transcript with timing."""
        from backend.pipeline.claim_extraction import parse_transcript_segments

        # Simulated Supadata response with timing
        data = {
            "content": [
                {"text": "Hello world", "start": 0, "end": 2},
                {"text": "This is a test", "start": 2, "end": 5},
            ]
        }

        segments, timing_available = parse_transcript_segments(data)

        assert timing_available is True
        assert len(segments) == 2
        assert segments[0]["start_ms"] == 0
        assert segments[1]["end_ms"] == 5000

    def test_parse_transcript_segments_without_timing(self):
        """Test parsing transcript without timing."""
        from backend.pipeline.claim_extraction import parse_transcript_segments

        # Simulated response without timing
        data = {"text": "This is just plain text without timing."}

        segments, timing_available = parse_transcript_segments(data)

        assert timing_available is False
        assert len(segments) == 1
        assert segments[0]["text"] == "This is just plain text without timing."


class TestRunClaimsDoc:
    """Tests for run-scoped claims doc model."""

    def test_run_claims_doc_creation(self):
        """Test creating RunClaimsDoc model."""
        from backend.models.run_models import RunClaimsDoc, RunStatus

        claims_doc = RunClaimsDoc(
            status=RunStatus.QUEUED,
            total_claims=0,
            total_entities=0,
        )

        assert claims_doc.status == RunStatus.QUEUED
        assert claims_doc.path is None
        assert claims_doc.total_claims == 0

    def test_run_has_claims_doc(self):
        """Test Run.has_claims_doc() method."""
        from backend.models.run_models import Run, RunType, RunStatus, RunRequest, RunClaimsDoc

        # Create a run without claims_doc
        run = Run(
            run_id="run_0",
            run_index=0,
            run_type=RunType.BASELINE,
            status=RunStatus.COMPLETED,
            request=RunRequest(requested_by="user-1"),
        )
        assert run.has_claims_doc() is False

        # Add completed claims_doc
        run.claims_doc = RunClaimsDoc(
            status=RunStatus.COMPLETED,
            path="job-123/run_0_claims_doc.json",
            total_claims=25,
            total_entities=10,
        )
        assert run.has_claims_doc() is True

        # Queued claims_doc should not count as "has"
        run.claims_doc.status = RunStatus.QUEUED
        assert run.has_claims_doc() is False
