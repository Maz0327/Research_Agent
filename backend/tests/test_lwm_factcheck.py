"""Stage 10b — the D-SFC-1 checker's safety contract, failure mode by failure mode."""

import json
from unittest.mock import MagicMock

SCRIPT = """# Movement 1

Alferd Packer walked out of the San Juan Mountains alone on April 16, 1874, after 65 days.
He was not convicted of murder — the charge that stuck in 1886 was manslaughter.
Packer said he shot Shannon Bell in self-defense.
The jury deliberated for three hours.
"""

PAGE_TRUE = ("Historical record: Packer emerged at the Los Pinos Agency on April 16, 1874. "
             "In 1886 Packer was convicted of manslaughter, not murder, and sentenced to 40 years. "
             "In his account, Packer said he shot Shannon Bell in self-defense.")
PAGE_CONTRA = "Court records state the jury deliberated for three days before returning its verdict."


def _extract_client(claims):
    c = MagicMock()
    c.generate_structured.return_value = ({"claims": claims}, {})
    return c


def _verdict_client(answers):
    c = MagicMock()
    c.generate_structured.side_effect = [(a, {}) for a in answers]
    return c


def _search(url="https://history.example/packer"):
    return lambda q, max_results=5: [{"url": url, "title": "t", "snippet": "s"}]


class TestExtraction:
    def test_entities_are_preserved_or_the_claim_is_dropped(self):
        from backend.lwm.factcheck import extract_claims
        client = _extract_client([
            {"claim": "Packer emerged on April 16, 1874", "script_line": "Alferd Packer walked out"},
            {"claim": "Gerald Packer emerged in 1875", "script_line": "Alferd Packer walked out"},
        ])
        kept = extract_claims(SCRIPT, client)
        assert len(kept) == 1
        assert "Gerald" not in kept[0]["claim"]  # invented entity never reaches the verifier

    def test_attributed_claims_carry_the_flag(self):
        from backend.lwm.factcheck import extract_claims
        client = _extract_client([{"claim": "Packer said he shot Shannon Bell in self-defense",
                                   "script_line": "Packer said he shot Shannon Bell in self-defense.",
                                   "attributed": True}])
        assert extract_claims(SCRIPT, client)[0]["attributed"] is True


class TestVerdicts:
    def _claim(self, text, attributed=False):
        return {"claim": text, "script_line": text, "attributed": attributed}

    def test_supported_with_real_quote_passes(self):
        from backend.lwm.factcheck import check_claim
        f = check_claim(self._claim("Packer was convicted of manslaughter in 1886"),
                        _verdict_client([{"verdict": "SUPPORTED", "url": "https://history.example/packer",
                                          "quote": "Packer was convicted of manslaughter, not murder"}]),
                        _search(), lambda url: PAGE_TRUE)
        assert f.verdict == "SUPPORTED" and f.quote_verified

    def test_fabricated_quote_is_downgraded_by_code(self):
        from backend.lwm.factcheck import check_claim
        f = check_claim(self._claim("The jury found Packer innocent"),
                        _verdict_client([{"verdict": "SUPPORTED", "url": "https://history.example/packer",
                                          "quote": "the jury found Packer entirely innocent of all charges"}]),
                        _search(), lambda url: PAGE_TRUE)
        assert f.verdict == "NOT ENOUGH EVIDENCE"
        assert f.downgraded_from == "SUPPORTED"
        assert "not found in fetched source" in f.notes

    def test_polarity_mismatch_never_supports(self):
        from backend.lwm.factcheck import check_claim
        page = "In 1886 Packer was convicted of murder by the Lake City jury."
        f = check_claim(self._claim("Packer was not convicted of murder"),
                        _verdict_client([{"verdict": "SUPPORTED", "url": "https://history.example/packer",
                                          "quote": "Packer was convicted of murder"}]),
                        _search(), lambda url: page)
        assert f.verdict == "NOT ENOUGH EVIDENCE"
        assert "negated claim" in f.notes

    def test_refuted_is_material(self):
        from backend.lwm.factcheck import check_claim
        f = check_claim(self._claim("The jury deliberated for three hours"),
                        _verdict_client([{"verdict": "REFUTED", "url": "https://history.example/packer",
                                          "quote": "the jury deliberated for three days"}]),
                        _search(), lambda url: PAGE_CONTRA)
        assert f.verdict == "REFUTED" and f.quote_verified  # materiality is run()'s job

    def test_conflicting_and_insufficient(self):
        from backend.lwm.factcheck import check_claim
        f1 = check_claim(self._claim("x y z claim"),
                         _verdict_client([{"verdict": "CONFLICTING", "notes": "sources disagree"}]),
                         _search(), lambda url: PAGE_TRUE)
        assert f1.verdict == "CONFLICTING"
        f2 = check_claim(self._claim("unfindable claim"),
                         _verdict_client([{"verdict": "NOT ENOUGH EVIDENCE"}]),
                         _search(), lambda url: PAGE_TRUE)
        assert f2.verdict == "NOT ENOUGH EVIDENCE" and not f2.material

    def test_fetch_failure_is_insufficient_not_a_crash(self):
        from backend.lwm.factcheck import check_claim
        def bad_fetch(url):
            raise OSError("timeout")
        f = check_claim(self._claim("anything"), MagicMock(), _search(), bad_fetch)
        assert f.verdict == "NOT ENOUGH EVIDENCE"
        assert "no source page" in f.notes

    def test_search_failure_is_insufficient(self):
        from backend.lwm.factcheck import check_claim
        def bad_search(q, max_results=5):
            raise OSError("429")
        f = check_claim(self._claim("anything"), MagicMock(), bad_search, lambda u: "")
        assert f.verdict == "NOT ENOUGH EVIDENCE" and "search failed" in f.notes


class TestRun:
    def test_never_edits_the_script_and_writes_both_artifacts(self, tmp_path):
        from backend.lwm import factcheck
        script = tmp_path / "07-draft.md"
        script.write_text(SCRIPT)
        before = script.read_text()
        client = _extract_client([{"claim": "Packer said he shot Shannon Bell in self-defense",
                                   "script_line": "Packer said he shot Shannon Bell in self-defense.",
                                   "attributed": True}])
        # one verdict call follows the extraction call on the same mock
        client.generate_structured.side_effect = [
            ({"claims": [{"claim": "Packer said he shot Shannon Bell in self-defense",
                          "script_line": "Packer said he shot Shannon Bell in self-defense.",
                          "attributed": True}]}, {}),
            ({"verdict": "SUPPORTED", "url": "https://history.example/packer",
              "quote": "Packer said he shot Shannon Bell in self-defense"}, {}),
        ]
        report = factcheck.run(script, tmp_path, client, search=_search(), fetch=lambda u: PAGE_TRUE)
        assert script.read_text() == before  # NEVER edited
        assert report["counts"]["SUPPORTED"] == 1
        assert not report["blocks_recording"]
        data = json.loads((tmp_path / "10b-fact-check.json").read_text())
        assert data["findings"][0]["quote_verified"] is True
        assert "Nothing blocks recording" in (tmp_path / "10b-fact-check.md").read_text()
