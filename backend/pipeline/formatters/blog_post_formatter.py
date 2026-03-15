"""Blog Post Markdown Formatter — Doc 7.

Produces polished, copy-paste-ready markdown from a BlogPostDocument.
"""

from datetime import datetime, timezone

from backend.models.blog_post_models import BlogPostDocument


def format_blog_post(
    blog_post: BlogPostDocument,
    *,
    include_provenance_footer: bool = True,
) -> str:
    """Convert a BlogPostDocument to polished markdown.

    Args:
        blog_post: Validated BlogPostDocument.
        include_provenance_footer: Whether to add provenance chain footer.

    Returns:
        Polished markdown string.
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    lines: list[str] = []

    # Header
    lines += [
        f"# {blog_post.title}",
        "",
    ]
    if blog_post.subtitle:
        lines += [f"*{blog_post.subtitle}*", ""]

    lines += [
        f"*{now} · {blog_post.source_count} source{'s' if blog_post.source_count != 1 else ''} · {blog_post.estimated_reading_time} · Doc 7*",
        "",
        f"> {blog_post.meta_description}",
        "",
        "---",
        "",
    ]

    # SEO Keywords
    if blog_post.seo_keywords:
        keywords = ", ".join(blog_post.seo_keywords)
        lines += [
            f"**Keywords:** {keywords}",
            "",
        ]

    # Sections
    for section in blog_post.sections:
        lines += [
            f"## {section.heading}",
            "",
            section.body,
            "",
        ]
        # Source citations
        if section.source_ids:
            refs = ", ".join(section.source_ids)
            lines += [f"*Sources: {refs}*", ""]

    # Conclusion
    lines += [
        "## Conclusion",
        "",
        blog_post.conclusion,
        "",
    ]

    # Call to Action
    if blog_post.call_to_action:
        lines += [
            "---",
            "",
            f"**{blog_post.call_to_action}**",
            "",
        ]

    # Sources
    if blog_post.description_sources:
        lines += [
            "---",
            "",
            "## Sources",
            "",
        ]
        for ds in blog_post.description_sources:
            title = ds.get("title", "Unknown")
            url = ds.get("url", "")
            creator = ds.get("creator", "")
            source_id = ds.get("source_id", "")

            line = f"- **{title}**"
            if creator:
                line += f" by {creator}"
            if url:
                line += f" — [{url}]({url})"
            if source_id:
                line += f" ({source_id})"
            lines.append(line)
        lines.append("")

    # Provenance footer
    if include_provenance_footer:
        lines += [
            "---",
            "",
            "*Every factual claim traces to a Doc 2 key point and a Doc 0 source.*",
            "",
        ]

    return "\n".join(lines)


def format_blog_post_from_dict(blog_post_dict: dict, **kwargs: object) -> str:
    """Convenience wrapper — parse dict then format.

    Args:
        blog_post_dict: BlogPostDocument as dict.
        **kwargs: Passed to format_blog_post().

    Returns:
        Polished markdown string.
    """
    blog_post = BlogPostDocument(**blog_post_dict)
    return format_blog_post(blog_post, **kwargs)
