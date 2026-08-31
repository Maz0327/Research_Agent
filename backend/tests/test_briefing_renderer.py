"""Tests for the deterministic Briefing renderer and the Source Vault.

Cover for P3 work-order item 15. Rendering is code's job end to end (D-025):
the JSON is canonical, the HTML is a function of it, and no model is involved.
These tests pin what the page must always carry - the nine sections in order,
chips with their tone, citations linked into the vault, and raw text that is
never cleaned up.
"""
import re

from backend.models.briefing import (
    Anecdote,
    Briefing,
    BriefingMeta,
    Dispute,
    DisputeSide,
    File,
    InfoGap,
    Place,
    Player,
    Read,
    ReadParagraph,
    RecordEntry,
    SourceTrailEntry,
    chip,
)
from backend.pipeline.formatters.briefing_renderer import (
    render_briefing_html,
    render_briefing_markdown,
)
from backend.pipeline.formatters.source_vault import looks_paywalled, render_source_vault


def _briefing() -> Briefing:
    """A Briefing with every section populated."""
    return Briefing(
        job_id="job-1",
        topic="The lost labyrinth of Hawara",
        meta=BriefingMeta(
            source_count=3,
            independent_source_count=2,
            raw_words=42263,
            quote_verification_rate=0.97,
            confidence="MEDIUM",
            generated_on="2026-08-19",
        ),
        read=Read(
            lede="Read all three.",
            paragraphs=[
                ReadParagraph(label="What you've got", text="Two videos and an article."),
                ReadParagraph(text="The story, assembled."),
            ],
        ),
        players=[
            Player(
                name="Flinders Petrie",
                role="excavated Hawara in 1888",
                body="Found the stone bed and called it a foundation.",
                source_ids=["SRC_1"],
            )
        ],
        places=[
            Place(
                name="Hawara",
                line="the pyramid site at the Fayum entrance",
                body="Every dig and every scan in the pile happened here.",
                source_ids=["SRC_1"],
            )
        ],
        record=[
            RecordEntry(
                when="1888",
                what="Petrie finds the stone bed.",
                source_ids=["SRC_1"],
                context="He read the chip stratum as demolition debris.",
            )
        ],
        files=[
            File(
                title="The 2008 scans",
                chips=[chip("single source")],
                body="Two overlapping missions.\n\nThe second reported a grid.",
                source_ids=["SRC_2"],
                fact_ids=["SRC_2:F_1"],
            )
        ],
        disputes=[
            Dispute(
                claim="The labyrinth survives under the bed.",
                holders="For: the scan network. Against: Petrie.",
                chip=chip("contested"),
                case_for=DisputeSide(
                    heading="The case for", text="Three authors describe a roof.", source_ids=["SRC_2"]
                ),
                case_against=DisputeSide(
                    heading="The case against", text="A chip stratum sits above it.", source_ids=["SRC_1"]
                ),
            )
        ],
        anecdotes=[
            Anecdote(
                text="Petrie got stuck in a collapsing tunnel.",
                source_ids=["SRC_3"],
                context="He freed himself by matchlight and went back in.",
            )
        ],
        info_gaps=[
            InfoGap(
                question="Where is the actual scan data?",
                why="The pile describes evidence nobody shows.",
                go_get="pull the whitepaper PDF and the two NRIAG papers",
            )
        ],
        source_trail=[
            SourceTrailEntry(
                source_id="SRC_1",
                title="Wikipedia - Hawara",
                kind="article",
                contribution="the orthodox baseline.",
            ),
            SourceTrailEntry(source_id="SRC_2", title="A scan write-up", kind="article"),
            SourceTrailEntry(
                source_id="SRC_3",
                title="A syndicated copy",
                kind="article",
                duplicate_of="SRC_2",
            ),
        ],
    )


class TestBriefingRenderer:
    """The page is a pure function of the JSON."""

    def test_all_nine_sections_render_in_order(self):
        """Order is the format; a reader learns where things are."""
        html = render_briefing_html(_briefing())

        positions = [
            html.index(title)
            for title in [
                "The Read",
                "The Players",
                "The Places",
                "The Record",
                "The Files",
                "Disputed &amp; Uncertain",
                "Details &amp; Anecdotes",
                "Info Gaps",
                "Source Trail",
            ]
        ]
        assert positions == sorted(positions)

    def test_masthead_carries_the_counted_facts(self):
        """Every number in the strip is one code counted."""
        html = render_briefing_html(_briefing())

        assert "<b>3</b> sources" in html
        assert "<b>2</b> independent" in html
        assert "42,263" in html
        assert "97%" in html

    def test_chips_render_with_their_tone(self):
        """Tone is derived from the label, so the colour cannot lie."""
        html = render_briefing_html(_briefing())

        assert '<span class="chip network">single source</span>' in html
        assert '<span class="chip contested">contested</span>' in html

    def test_citations_link_into_the_vault(self):
        """Any claim traces to its raw text in one hop."""
        html = render_briefing_html(_briefing(), vault_url="https://vault.example/x")

        assert 'href="https://vault.example/x#src_1"' in html
        assert 'href="https://vault.example/x#src_2"' in html

    def test_without_a_vault_ids_are_plain_text(self):
        """No vault means no dead links."""
        html = render_briefing_html(_briefing())

        assert "#src_1" not in html
        assert "SRC_1" in html

    def test_prose_is_escaped_not_interpreted(self):
        """Source text with markup in it cannot break or inject the page."""
        briefing = _briefing()
        briefing.read.paragraphs[0].text = '<script>alert("x")</script> & more'

        html = render_briefing_html(briefing)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_context_dropdowns_are_rendered(self):
        """Record and anecdote context live behind More, per the format."""
        html = render_briefing_html(_briefing())

        assert "<summary>More</summary>" in html
        assert "<summary>Context</summary>" in html
        assert "Full case, both sides" in html

    def test_republication_is_visible_in_the_trail(self):
        """A syndicated copy stays listed and says what it copies."""
        html = render_briefing_html(_briefing())

        assert "republication of SRC_2" in html

    def test_section_numbers_never_skip_when_a_section_is_empty(self):
        """Numbers follow what is emitted. They used to be hardcoded, so a
        briefing with no places rendered "2. The Players" into "4. The
        Record" — a number the reader never sees (2026-08-31)."""
        briefing = _briefing()
        briefing.places = []

        numbers = [
            int(match) for match in re.findall(
                r"^## (\d+)\. ", render_briefing_markdown(briefing), re.M
            )
        ]

        assert numbers == list(range(1, len(numbers) + 1))

    def test_empty_sections_are_omitted_not_faked(self):
        """A thin document says less rather than showing empty furniture."""
        briefing = _briefing()
        briefing.players = []
        briefing.anecdotes = []

        html = render_briefing_html(briefing)

        assert "The Players" not in html
        assert "Details &amp; Anecdotes" not in html
        assert "The Read" in html


class TestSourceVault:
    """Raw text, unedited, by code alone."""

    def _sources(self):
        return [
            {
                "source_id": "SRC_1",
                "title": "A video",
                "url": "https://youtu.be/abc",
                "source_type": "youtube",
                "full_text": "the transcript with its own typos and  spacing",
            },
            {
                "source_id": "SRC_2",
                "title": "A failed fetch",
                "url": "https://example.com/x",
                "full_text": "",
                "full_text_unavailable_reason": "Fetch returned 503",
            },
        ]

    def test_every_source_gets_an_anchor(self):
        """The Briefing's links have somewhere to land."""
        html = render_source_vault("The Sources", self._sources())

        assert 'id="src_1"' in html
        assert 'id="src_2"' in html
        assert 'href="#src_1"' in html

    def test_raw_text_is_shown_unedited(self):
        """Whatever was captured is what the page shows."""
        html = render_source_vault("The Sources", self._sources())

        assert "the transcript with its own typos and  spacing" in html

    def test_missing_text_says_why(self):
        """A failed fetch is stated, not hidden."""
        html = render_source_vault("The Sources", self._sources())

        assert "Fetch returned 503" in html

    def test_paywalled_sources_are_flagged_in_product_mode(self):
        """Private by default; product mode shows an excerpt and a link."""
        sources = [
            {
                "source_id": "SRC_1",
                "title": "A paywalled piece",
                "url": "https://example.com/x",
                "full_text": "Subscribe to continue reading this article. " + "body " * 300,
            }
        ]

        private = render_source_vault("The Sources", sources)
        product = render_source_vault("The Sources", sources, product_mode=True)

        assert "Full raw text" in private
        assert "paywalled" in product
        assert "Full raw text" not in product

    def test_paywall_detection(self):
        """The marker check is a plain string test, not a judgment."""
        assert looks_paywalled("Subscribers only. Sign in to read.")
        assert not looks_paywalled("An ordinary article about the labyrinth.")

    def test_footer_counts_what_was_captured(self):
        """The page says how much of the corpus it actually holds."""
        html = render_source_vault("The Sources", self._sources(), job_id="job-1")

        assert "2 sources, 1 with captured text" in html
        assert "job job-1" in html
