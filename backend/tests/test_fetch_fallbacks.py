"""Tests for fetch-fallback detection and the Internet Archive route.

Cover for P3 work-order item A5. On 2026-08-17 a Perseus 503 was saved as a
source because the fetch succeeded and the extractor returned the site's
navigation; a Substack fetch returned a shell with no article. Both looked
like content to everything downstream.
"""
from unittest.mock import MagicMock, patch

from backend.integrations.web_capture import fetch_via_wayback
from backend.utils.content_filter import (
    is_thin_content,
    looks_like_navigation_chrome,
    needs_fetch_fallback,
    prose_density,
)

NAV_CHROME = """Skip to main content
Home
About
Browse
Search
Sign in
Subscribe
Privacy Policy
Terms of Service
All rights reserved
Back to top
"""

REAL_ARTICLE = """The Hawara labyrinth has been described by ancient writers for two thousand years,
and every account disagrees with the next about what was actually under the sand.
Herodotus wrote that he walked its upper chambers himself and was refused entry to the lower ones,
which he was told held the tombs of the kings who built the place.
Strabo, writing centuries later, gave measurements that do not match the site as it is understood today,
and the discrepancy has never been resolved to anyone's satisfaction.
"""


class TestProseDensity:
    """Long lines are prose; short lines are furniture."""

    def test_article_scores_high(self):
        """Body text is almost entirely prose-length lines."""
        assert prose_density(REAL_ARTICLE) > 0.85

    def test_navigation_scores_zero(self):
        """A menu has no prose-length lines at all."""
        assert prose_density(NAV_CHROME) == 0.0

    def test_empty_text(self):
        """Empty input scores zero rather than dividing by zero."""
        assert prose_density("") == 0.0


class TestNavigationChrome:
    """The Perseus failure: a successful fetch that captured the menus."""

    def test_navigation_only_page_is_chrome(self):
        """Menu items plus site furniture, no prose."""
        assert looks_like_navigation_chrome(NAV_CHROME) is True

    def test_real_article_is_not_chrome(self):
        """Body text is never mistaken for furniture."""
        assert looks_like_navigation_chrome(REAL_ARTICLE) is False

    def test_article_with_a_menu_attached_is_not_chrome(self):
        """A page that carries both keeps its article."""
        assert looks_like_navigation_chrome(NAV_CHROME + REAL_ARTICLE * 3) is False

    def test_empty_text_is_not_chrome(self):
        """Emptiness is its own failure, reported separately."""
        assert looks_like_navigation_chrome("") is False


class TestThinContent:
    """The Substack failure: a shell with a title and a subscribe box."""

    def test_short_shell_is_thin(self):
        """Under the word floor counts as thin."""
        assert is_thin_content("Subscribe to read the rest of this post.") is True

    def test_real_article_is_not_thin(self):
        """A full article clears the floor."""
        assert is_thin_content(REAL_ARTICLE * 4) is False

    def test_empty_is_thin(self):
        """No text is thin by definition."""
        assert is_thin_content("") is True


class TestNeedsFetchFallback:
    """One call decides whether another route is worth trying."""

    def test_usable_text_needs_nothing(self):
        """Good content returns False and an empty reason."""
        assert needs_fetch_fallback(REAL_ARTICLE * 4) == (False, "")

    def test_empty_text_reports_no_text(self):
        """Nothing extracted is named as such."""
        needed, reason = needs_fetch_fallback("")
        assert needed is True
        assert "no text" in reason

    def test_chrome_reports_navigation(self):
        """The navigation case names itself in the reason."""
        needed, reason = needs_fetch_fallback(NAV_CHROME)
        assert needed is True
        assert "navigation" in reason

    def test_thin_reports_word_count(self):
        """The thin case reports how little came back."""
        needed, reason = needs_fetch_fallback("A short post about nothing much at all.")
        assert needed is True
        assert "thin extraction" in reason


class TestWaybackFallback:
    """The archive holds what the live page lost."""

    def _cdx_response(self, rows):
        response = MagicMock(status_code=200)
        response.json.return_value = rows
        return response

    def test_returns_snapshot_html(self):
        """The most recent successful capture is fetched and returned."""
        cdx = self._cdx_response(
            [
                ["timestamp", "original"],
                ["20230612094500", "https://example.com/a"],
            ]
        )
        snapshot = MagicMock(status_code=200, text="<html>archived body</html>")

        with patch(
            "backend.integrations.web_capture.httpx.get", side_effect=[cdx, snapshot]
        ):
            html, snapshot_url = fetch_via_wayback("https://example.com/a")

        assert html == "<html>archived body</html>"
        assert snapshot_url == (
            "https://web.archive.org/web/20230612094500id_/https://example.com/a"
        )

    def test_no_snapshot_returns_none(self):
        """A URL the archive never saw returns nothing, not an error."""
        with patch(
            "backend.integrations.web_capture.httpx.get",
            return_value=self._cdx_response([]),
        ):
            assert fetch_via_wayback("https://example.com/never") == (None, None)

    def test_rate_limited_index_returns_none(self):
        """A 429 from the archive is a miss, never a crash."""
        with patch(
            "backend.integrations.web_capture.httpx.get",
            return_value=MagicMock(status_code=429),
        ):
            assert fetch_via_wayback("https://example.com/a") == (None, None)

    def test_failed_snapshot_fetch_returns_none(self):
        """An index hit whose snapshot 404s yields nothing."""
        cdx = self._cdx_response(
            [["timestamp", "original"], ["20230612094500", "https://example.com/a"]]
        )
        with patch(
            "backend.integrations.web_capture.httpx.get",
            side_effect=[cdx, MagicMock(status_code=404)],
        ):
            assert fetch_via_wayback("https://example.com/a") == (None, None)

    def test_network_failure_returns_none(self):
        """The archive being down never breaks a job."""
        with patch(
            "backend.integrations.web_capture.httpx.get", side_effect=OSError("no route")
        ):
            assert fetch_via_wayback("https://example.com/a") == (None, None)
