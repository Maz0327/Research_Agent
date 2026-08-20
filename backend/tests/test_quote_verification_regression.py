"""Regression suites for quote verification: real quotes, and fabrications.

Both halves of the measurement that changed this verifier are kept as tests
(owner requirement, 2026-08-19), so the two failure directions stay pinned:

- **Real quotes** come from the labyrinth corpus, as an extractor actually
  produced them, each with a window of the source it was taken from. They must
  verify. A change that quietly stops confirming real quotations shows up here.
- **Fabrications** are built at test time by recombining words from those same
  windows, which is the hardest case: identical vocabulary, no contiguous run.
  None of them may verify. The old fuzzy measure passed 18 of 144 of these.
"""
import json
import random
from pathlib import Path

import pytest

from backend.pipeline.quote_verification import (
    FLAGGED,
    SPAN_THRESHOLD,
    UNCERTAIN,
    VERIFIED,
    longest_span_ratio,
    normalize_text,
    split_on_ellipsis,
    verify_quote,
    verify_span,
)

FIXTURE = Path(__file__).parent / "fixtures" / "quote_verification_cases.json"


@pytest.fixture(scope="module")
def real_cases():
    """Quotes an extractor produced, with the source window each came from."""
    with open(FIXTURE) as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def fabricated_cases(real_cases):
    """Quotes assembled from each window's own words, in the wrong order."""
    generator = random.Random(11)
    cases = []
    for case in real_cases:
        words = normalize_text(case["window"]).split()
        if len(words) < 40:
            continue
        length = generator.randrange(8, 16)
        cases.append(
            {
                "source_id": case["source_id"],
                "quote": " ".join(generator.sample(words, length)),
                "window": case["window"],
            }
        )
    return cases


class TestRealQuotesStillVerify:
    """The direction that protects real quotations from being thrown away."""

    def test_the_corpus_verifies(self, real_cases):
        """At least 90% of real extracted quotes verify verbatim."""
        verdicts = [verify_quote(c["quote"], c["window"])["status"] for c in real_cases]
        verified = verdicts.count(VERIFIED)

        assert verified / len(real_cases) >= 0.90, (
            f"only {verified}/{len(real_cases)} real quotes verified"
        )

    def test_nothing_real_is_flagged(self, real_cases):
        """A real quotation is never called an invention."""
        flagged = [
            c["quote"][:60]
            for c in real_cases
            if verify_quote(c["quote"], c["window"])["status"] == FLAGGED
        ]

        assert flagged == []

    def test_the_near_misses_land_as_uncertain(self, real_cases):
        """Quotes joined across an unmarked elision are kept and marked."""
        for case in real_cases:
            result = verify_quote(case["quote"], case["window"])
            if result["status"] == UNCERTAIN:
                assert result["fuzzy"] >= 0.7
                assert result["span"] < SPAN_THRESHOLD


class TestFabricationsNeverVerify:
    """The direction the old measure got wrong 18 times in 144."""

    def test_no_fabrication_verifies(self, fabricated_cases):
        """Same vocabulary, no run: never verbatim."""
        passed = [
            c["quote"][:60]
            for c in fabricated_cases
            if verify_quote(c["quote"], c["window"])["status"] == VERIFIED
        ]

        assert passed == [], f"{len(passed)} fabrications passed as verified"

    def test_fabrications_score_far_below_the_threshold(self, fabricated_cases):
        """The separation is a gap, not a boundary."""
        spans = [longest_span_ratio(c["quote"], c["window"]) for c in fabricated_cases]

        assert max(spans) < SPAN_THRESHOLD - 0.2

    def test_most_fabrications_are_flagged_outright(self, fabricated_cases):
        """Most do not even reach the near-miss band."""
        verdicts = [verify_quote(c["quote"], c["window"])["status"] for c in fabricated_cases]

        assert verdicts.count(FLAGGED) / len(verdicts) >= 0.5


class TestTheVerdictComesFromTheSpanAlone:
    """Owner requirement (2026-08-19): fuzzy is advisory forever.

    The measured separation on partial ratio is 6 points (real quotes min 0.77,
    fabrications max 0.71), and a margin that thin moves with corpus, window
    size, and transcription quality. It may never decide whether something is
    VERIFIED.
    """

    def test_a_high_fuzzy_score_cannot_verify_without_a_span(self, real_cases):
        """Every word present, none of them in order: not a quotation.

        Built from a real source window so the fuzzy score is high for the
        same reason it is high in production: the words are all there.
        """
        window = real_cases[0]["window"]
        scrambled = " ".join(reversed(normalize_text(window).split()[:14]))

        result = verify_quote(scrambled, window)

        assert result["fuzzy"] > result["span"]
        assert result["span"] < SPAN_THRESHOLD
        assert result["status"] != VERIFIED

    def test_lowering_the_fuzzy_band_never_creates_a_verified(self, fabricated_cases):
        """Sweeping the advisory threshold moves labels, never verdicts."""
        for band in (0.0, 0.3, 0.5, 0.7, 0.9, 1.0):
            verdicts = [
                verify_quote(c["quote"], c["window"], threshold=band)["status"]
                for c in fabricated_cases
            ]
            assert VERIFIED not in verdicts, f"fuzzy band {band} produced a VERIFIED"

    def test_the_fuzzy_band_only_moves_the_uncertain_flagged_line(self):
        """That is the whole job it is allowed to do."""
        source = "The roof was stone. The priests refused him entry to the lower chambers."
        scrambled = "entry stone priests the refused roof lower chambers the was"

        lenient = verify_quote(scrambled, source, threshold=0.1)["status"]
        strict = verify_quote(scrambled, source, threshold=0.99)["status"]

        assert lenient == UNCERTAIN
        assert strict == FLAGGED

    def test_a_span_match_verifies_even_when_fuzzy_is_poor(self):
        """A short exact quotation inside a long source is still verbatim."""
        source = "x " * 4000 + "the priests refused him entry to the lower chambers " + "y " * 4000

        result = verify_quote("the priests refused him entry to the lower chambers", source)

        assert result["span"] == 1.0
        assert result["status"] == VERIFIED


class TestNormalizationAndEllipsis:
    """The two policies the verdict rests on."""

    def test_typography_never_decides(self):
        """Smart quotes, dashes, and case are folded before matching."""
        source = 'He said "the roof was stone" - and left.'
        quote = "He said “the roof was stone” — and left."

        assert verify_quote(quote, source)["status"] == VERIFIED

    def test_each_elided_fragment_is_verified_on_its_own(self):
        """An ellipsis is several spans, and the weakest one decides."""
        source = "The priests refused him entry. Much later, the roof was quarried away."

        both_real = verify_span("The priests refused him entry ... the roof was quarried away", source)
        one_invented = verify_span("The priests refused him entry ... the gold was carried away", source)

        assert both_real["verbatim"] is True
        assert len(both_real["fragments"]) == 2
        assert one_invented["verbatim"] is False

    def test_ellipsis_forms_all_split(self):
        """Three dots, spaced dots, the character, and a bracketed ellipsis."""
        for form in ("a ... b", "a . . . b", "a … b", "a [...] b"):
            assert len(split_on_ellipsis(form)) == 2

    def test_a_quote_with_no_source_is_flagged(self):
        """Empty inputs are never verified by accident."""
        assert verify_quote("something", "")["status"] == FLAGGED
        assert verify_quote("", "something")["status"] == FLAGGED
