"""Tests for code-only byline capture.

Cover for P3 work-order item A3: every source in both fixture runs carried
`creator=None`, so no document could attribute anything by name. Bylines now
come from page metadata (meta tags, JSON-LD, byline markup) and, for videos,
from YouTube oEmbed, with no LLM in the path.
"""
from unittest.mock import MagicMock, patch

from backend.integrations.web_capture import _clean_byline, extract_byline_from_html
from backend.integrations.youtube import fetch_oembed_metadata
from backend.pipeline.stages.source_identity import build_source_identity_from_article


class TestCleanByline:
    """Author strings are normalized, and junk is rejected outright."""

    def test_strips_by_prefix_and_punctuation(self):
        """"By Jane Doe |" becomes "Jane Doe"."""
        assert _clean_byline("By Jane Doe |") == "Jane Doe"
        assert _clean_byline("  by Sam Reed  ") == "Sam Reed"

    def test_keeps_ordinary_names(self):
        """A plain name passes through unchanged."""
        assert _clean_byline("Kara Swisher") == "Kara Swisher"

    def test_rejects_unusable_values(self):
        """Emails, URLs, placeholders, and empty strings yield None."""
        assert _clean_byline(None) is None
        assert _clean_byline("") is None
        assert _clean_byline("news@example.com") is None
        assert _clean_byline("https://example.com/author/jane") is None
        assert _clean_byline("Staff") is None
        assert _clean_byline("anonymous") is None
        assert _clean_byline("x" * 200) is None


class TestExtractBylineFromHtml:
    """Publishers spread bylines across meta tags, JSON-LD, and markup."""

    def test_meta_author_tag(self):
        """`<meta name="author">` is read."""
        html = (
            '<html><head><meta name="author" content="Jane Doe">'
            "<title>T</title></head><body><p>real body text here</p></body></html>"
        )
        result = extract_byline_from_html(html, "https://example.com/a")
        assert result["creator"] == "Jane Doe"

    def test_json_ld_author_and_date(self):
        """schema.org JSON-LD supplies both author and publication date."""
        html = """<html><head><title>T</title>
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"NewsArticle","headline":"H",
         "author":{"@type":"Person","name":"Kara Swisher"},
         "datePublished":"2026-03-04T10:00:00Z"}
        </script></head><body><p>body text long enough to matter</p></body></html>"""
        result = extract_byline_from_html(html, "https://example.com/b")
        assert result["creator"] == "Kara Swisher"
        assert result["published"].startswith("2026-03-04")

    def test_article_author_property(self):
        """OpenGraph-style `article:author` is read."""
        html = (
            '<html><head><meta property="article:author" content="Ada Lovelace">'
            '<meta property="article:published_time" content="2026-01-02">'
            "</head><body><p>text text text</p></body></html>"
        )
        result = extract_byline_from_html(html, "https://example.com/c")
        assert result["creator"] == "Ada Lovelace"
        assert result["published"] == "2026-01-02"

    def test_no_byline_is_an_honest_hole(self):
        """A page with no author yields None, never a guess."""
        html = "<html><head><title>T</title></head><body><p>text text</p></body></html>"
        result = extract_byline_from_html(html, "https://example.com/d")
        assert result["creator"] is None

    def test_malformed_html_does_not_raise(self):
        """Garbage in, no author out (trafilatura still names the host)."""
        result = extract_byline_from_html("<<<not html", "https://example.com/e")
        assert result["creator"] is None
        assert result["published"] is None


class TestArticleIdentityUsesByline:
    """The identity package carries the captured byline."""

    def test_author_becomes_creator(self):
        """An `author` field lands on the package as `creator`."""
        pkg = build_source_identity_from_article(
            {
                "url": "https://example.com/a",
                "title": "A piece",
                "content": "some words here",
                "author": "Jane Doe",
                "published": "2026-03-04",
            },
            source_index=0,
        )
        assert pkg.creator == "Jane Doe"
        assert pkg.published == "2026-03-04"

    def test_sitename_is_the_fallback(self):
        """With no person credited, the publication name attributes the source."""
        pkg = build_source_identity_from_article(
            {
                "url": "https://example.com/a",
                "content": "some words here",
                "sitename": "The Guardian",
            },
            source_index=0,
        )
        assert pkg.creator == "The Guardian"

    def test_person_beats_sitename(self):
        """A named author wins over the publication name."""
        pkg = build_source_identity_from_article(
            {
                "url": "https://example.com/a",
                "content": "some words here",
                "author": "Jane Doe",
                "sitename": "The Guardian",
            },
            source_index=0,
        )
        assert pkg.creator == "Jane Doe"


class TestYouTubeOEmbed:
    """oEmbed attributes videos when Supadata metadata is unavailable."""

    def test_returns_title_and_creator(self):
        """A successful lookup yields the video title and channel name."""
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "title": "The Hawara Labyrinth",
            "author_name": "Ancient Architects",
        }
        with patch("backend.integrations.youtube.httpx.get", return_value=response):
            result = fetch_oembed_metadata("https://youtu.be/abc")

        assert result == {
            "title": "The Hawara Labyrinth",
            "creator": "Ancient Architects",
        }

    def test_non_200_returns_none(self):
        """Private or deleted videos return None, not an exception."""
        with patch(
            "backend.integrations.youtube.httpx.get",
            return_value=MagicMock(status_code=404),
        ):
            assert fetch_oembed_metadata("https://youtu.be/gone") is None

    def test_network_failure_returns_none(self):
        """A transport error is swallowed: byline capture is never fatal."""
        with patch(
            "backend.integrations.youtube.httpx.get", side_effect=OSError("no route")
        ):
            assert fetch_oembed_metadata("https://youtu.be/abc") is None


class TestVideoIdentityUsesOEmbed:
    """The video identity builder fills a missing channel from oEmbed."""

    def _run(self, video_data, oembed_result):
        from backend.pipeline.stages import source_identity

        acquired = MagicMock()
        acquired.text = "transcript words"
        acquired.transcript_source = MagicMock(value="supadata")
        acquired.analysis_mode = source_identity.AnalysisMode.TRANSCRIPT_GROUNDED
        acquired.to_provenance.return_value = None

        with patch.object(
            source_identity, "fetch_oembed_metadata", return_value=oembed_result
        ) as mock_oembed, patch.object(
            source_identity, "acquire_transcript", return_value=acquired
        ), patch.object(
            source_identity, "is_transcript_available", return_value=True
        ):
            pkg = source_identity.build_source_identity_from_video(video_data, 0)
        return pkg, mock_oembed

    def test_bare_url_gets_channel_and_title(self):
        """Mixed-input jobs pass only a URL; oEmbed supplies the rest."""
        pkg, mock_oembed = self._run(
            {"url": "https://youtu.be/abc"},
            {"title": "The Hawara Labyrinth", "creator": "Ancient Architects"},
        )

        assert pkg.creator == "Ancient Architects"
        assert pkg.title == "The Hawara Labyrinth"
        mock_oembed.assert_called_once()

    def test_existing_metadata_skips_the_lookup(self):
        """Nothing is fetched when the caller already knows the channel."""
        pkg, mock_oembed = self._run(
            {
                "url": "https://youtu.be/abc",
                "title": "Known title",
                "channel": "Known channel",
            },
            None,
        )

        assert pkg.creator == "Known channel"
        assert pkg.title == "Known title"
        mock_oembed.assert_not_called()

    def test_oembed_failure_leaves_fields_empty(self):
        """A failed lookup is an honest hole, not a crash."""
        pkg, _ = self._run({"url": "https://youtu.be/abc"}, None)

        assert pkg.creator is None
        assert pkg.title == "Untitled Video"
