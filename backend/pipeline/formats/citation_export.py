"""Citation Export: BibTeX and RIS formats for academic workflows.

Converts research sources to standard academic citation formats
for import into reference managers (Zotero, Mendeley, EndNote).
"""
import re
from datetime import datetime
from typing import Any, Optional
from loguru import logger


class CitationExporter:
    """Generate BibTeX and RIS citations from research sources."""

    def to_bibtex(self, sources: list) -> str:
        """
        Convert sources to BibTeX format.

        Args:
            sources: List of source dicts with url, title, author, published_at, type

        Returns:
            BibTeX formatted string
        """
        logger.info(f"Generating BibTeX for {len(sources)} sources")
        entries = []

        for i, source in enumerate(sources):
            entry = self._source_to_bibtex(source, i + 1)
            if entry:
                entries.append(entry)

        return "\n\n".join(entries)

    def to_ris(self, sources: list) -> str:
        """
        Convert sources to RIS format.

        Args:
            sources: List of source dicts with url, title, author, published_at, type

        Returns:
            RIS formatted string
        """
        logger.info(f"Generating RIS for {len(sources)} sources")
        entries = []

        for source in sources:
            entry = self._source_to_ris(source)
            if entry:
                entries.append(entry)

        return "\n\n".join(entries)

    def _source_to_bibtex(self, source: dict, index: int) -> Optional[str]:
        """Convert single source to BibTeX entry."""
        url = self._get_attr(source, "url") or ""
        title = self._get_attr(source, "title") or "Untitled"
        author = self._get_attr(source, "author") or "Unknown"
        published_at = self._get_attr(source, "published_at") or self._get_attr(source, "date")
        source_type = self._get_attr(source, "type") or self._infer_type(url)

        # Generate citation key
        key = self._generate_key(author, published_at, index)

        # Parse year
        year = self._extract_year(published_at) or str(datetime.now().year)

        # Select entry type based on source type
        if source_type == "video":
            entry_type = "misc"
            extra = f"  howpublished = {{YouTube video}},\n"
        elif source_type == "social":
            entry_type = "misc"
            extra = f"  howpublished = {{Social media}},\n"
        elif source_type == "academic":
            entry_type = "article"
            extra = ""
        else:
            entry_type = "online"
            extra = ""

        # Build entry
        lines = [
            f"@{entry_type}{{{key},",
            f"  title = {{{self._escape_bibtex(title)}}},",
            f"  author = {{{self._escape_bibtex(author)}}},",
            f"  year = {{{year}}},",
            f"  url = {{{url}}},",
        ]

        if extra:
            lines.append(extra.rstrip(",\n") + ",")

        # Add access date
        lines.append(f"  urldate = {{{datetime.now().strftime('%Y-%m-%d')}}}")
        lines.append("}")

        return "\n".join(lines)

    def _source_to_ris(self, source: dict) -> Optional[str]:
        """Convert single source to RIS entry."""
        url = self._get_attr(source, "url") or ""
        title = self._get_attr(source, "title") or "Untitled"
        author = self._get_attr(source, "author") or "Unknown"
        published_at = self._get_attr(source, "published_at") or self._get_attr(source, "date")
        source_type = self._get_attr(source, "type") or self._infer_type(url)

        # Select type
        if source_type == "video":
            ris_type = "VIDEO"
        elif source_type == "academic":
            ris_type = "JOUR"
        else:
            ris_type = "ELEC"  # Electronic resource

        # Parse year
        year = self._extract_year(published_at) or str(datetime.now().year)

        # Build entry
        lines = [
            f"TY  - {ris_type}",
            f"TI  - {title}",
            f"AU  - {author}",
            f"PY  - {year}",
            f"UR  - {url}",
            f"Y2  - {datetime.now().strftime('%Y/%m/%d')}",
            "ER  -",
        ]

        return "\n".join(lines)

    def _generate_key(self, author: str, published_at: Optional[str], index: int) -> str:
        """Generate BibTeX citation key."""
        # Extract first author's last name
        author_clean = re.sub(r'[^a-zA-Z\s]', '', author)
        parts = author_clean.split()
        last_name = parts[-1] if parts else "unknown"

        # Extract year
        year = self._extract_year(published_at) or str(datetime.now().year)

        # Combine
        key = f"{last_name.lower()}{year}_{index}"
        return re.sub(r'[^a-zA-Z0-9_]', '', key)

    def _extract_year(self, date_str: Optional[str]) -> Optional[str]:
        """Extract year from date string."""
        if not date_str:
            return None

        # Try to find 4-digit year
        match = re.search(r'(\d{4})', str(date_str))
        if match:
            return match.group(1)

        return None

    def _escape_bibtex(self, text: str) -> str:
        """Escape special characters for BibTeX."""
        if not text:
            return ""
        # Escape special LaTeX characters
        replacements = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text

    def _infer_type(self, url: str) -> str:
        """Infer source type from URL."""
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "video"
        if "reddit.com" in url_lower or "twitter.com" in url_lower or "x.com" in url_lower:
            return "social"
        if any(domain in url_lower for domain in [".edu", "arxiv.org", "scholar.google"]):
            return "academic"
        return "web"

    def _get_attr(self, obj: Any, attr: str) -> Any:
        """Get attribute from object or dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)
