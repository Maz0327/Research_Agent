"""Tests for the Doc 0 raw-text preservation contract.

Cover for P3 work-order item A4. Doc 0's `full_text` is the canonical raw
layer: the Briefing's Section 1 is generated from it, the Source Vault is
rendered from it, and the grounding gate matches hard atoms against it.
Losing it silently is the failure this contract makes impossible.
"""
import pytest

from backend.models.document_outputs import SourceEntry, SourceLedger, SourceStatus
from backend.pipeline.stages.document_assembly import (
    RawTextContractError,
    build_source_ledger,
    verify_raw_text_preserved,
)


def _source(source_id: str, content: str, **overrides) -> dict:
    """Build a source dict of the shape document assembly receives."""
    data = {
        "source_id": source_id,
        "source_type": "article",
        "title": f"Title {source_id}",
        "url": f"https://example.com/{source_id}",
        "creator": "Jane Doe",
        "content": content,
        "word_count": len(content.split()),
    }
    data.update(overrides)
    return data


class TestBuildSourceLedgerPreservesText:
    """Raw text reaches Doc 0 whole."""

    def test_full_text_survives_assembly(self):
        """Every source's content lands in its ledger entry byte for byte."""
        sources = [_source("SRC_1", "first source body " * 50), _source("SRC_2", "second body")]

        ledger = build_source_ledger("A topic", sources, [])

        assert ledger.sources[0].full_text == sources[0]["content"]
        assert ledger.sources[1].full_text == sources[1]["content"]

    def test_missing_text_gets_a_stated_reason(self):
        """A source with no text says why, instead of reading as empty."""
        sources = [_source("SRC_1", "", failed=True, failure_reason="Fetch returned 403")]

        ledger = build_source_ledger("A topic", sources, [])

        assert ledger.sources[0].full_text is None
        assert ledger.sources[0].full_text_unavailable_reason == "Fetch returned 403"

    def test_missing_text_and_missing_reason_still_says_something(self):
        """An unexplained hole is named, never left blank."""
        sources = [_source("SRC_1", "")]

        ledger = build_source_ledger("A topic", sources, [])

        assert ledger.sources[0].full_text_unavailable_reason == (
            "No text was captured for this source"
        )


class TestVerifyRawTextPreserved:
    """The verifier catches both loss and truncation."""

    def _ledger(self, full_text):
        ledger = SourceLedger(topic="A topic")
        ledger.sources.append(
            SourceEntry(
                source_id="SRC_1",
                source_type="article",
                title="T",
                url="https://example.com/a",
                status=SourceStatus.INGESTED,
                full_text=full_text,
            )
        )
        return ledger

    def test_dropped_text_raises(self):
        """Content in, nothing out, is a hard failure."""
        with pytest.raises(RawTextContractError, match="none in Doc 0"):
            verify_raw_text_preserved(self._ledger(None), [_source("SRC_1", "real body text")])

    def test_truncated_text_raises(self):
        """Silent truncation is a hard failure too."""
        with pytest.raises(RawTextContractError, match="truncated"):
            verify_raw_text_preserved(
                self._ledger("real body"), [_source("SRC_1", "real body text, much longer")]
            )

    def test_intact_text_passes(self):
        """Matching text raises nothing."""
        verify_raw_text_preserved(
            self._ledger("real body text"), [_source("SRC_1", "real body text")]
        )

    def test_error_names_every_lost_source(self):
        """The message lists all offenders, so one run finds them all."""
        ledger = SourceLedger(topic="A topic")
        for source_id in ("SRC_1", "SRC_2"):
            ledger.sources.append(
                SourceEntry(
                    source_id=source_id,
                    source_type="article",
                    title="T",
                    url="https://example.com/a",
                    status=SourceStatus.INGESTED,
                    full_text=None,
                )
            )

        with pytest.raises(RawTextContractError) as excinfo:
            verify_raw_text_preserved(
                ledger, [_source("SRC_1", "body one"), _source("SRC_2", "body two")]
            )

        assert "SRC_1" in str(excinfo.value)
        assert "SRC_2" in str(excinfo.value)
