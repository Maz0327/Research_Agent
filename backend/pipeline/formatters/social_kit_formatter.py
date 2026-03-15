"""Social Media Kit Markdown Formatter — Doc 6."""

from datetime import datetime, timezone

from backend.models.social_kit_models import SocialKitDocument


def format_social_kit(
    kit: SocialKitDocument,
    *,
    include_provenance_footer: bool = True,
) -> str:
    """Convert a SocialKitDocument to polished markdown.

    Args:
        kit: Validated SocialKitDocument.
        include_provenance_footer: Whether to add provenance footer.

    Returns:
        Polished markdown string.
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    lines: list[str] = []

    lines += [
        "# Social Media Kit",
        f"**{kit.topic}**",
        "",
        f"*{now} · {kit.source_count} source{'s' if kit.source_count != 1 else ''} · Doc 6*",
        "",
        "---",
        "",
    ]

    for post in kit.platforms:
        platform_title = post.platform.replace("_", " ").title()
        lines += [f"## {platform_title}", ""]

        if post.platform == "twitter_thread" and post.tweets:
            for tweet in post.tweets:
                lines += [
                    f"**Tweet {tweet.tweet_number}** ({len(tweet.text)} chars)",
                    f"> {tweet.text}",
                    "",
                ]
        elif post.platform == "youtube_description":
            if post.description_body:
                lines += [post.description_body, ""]
            if post.timestamps:
                lines += ["**Timestamps:**"]
                for ts in post.timestamps:
                    lines.append(f"- {ts.timestamp} — {ts.label}")
                lines.append("")
        elif post.body:
            lines += [post.body, ""]

        if post.hashtags:
            lines.append(f"**Hashtags:** {' '.join(post.hashtags)}")
            lines.append("")

        lines += [f"*Character count: {post.char_count}*", "", "---", ""]

    if include_provenance_footer:
        lines += [
            "*Every factual claim traces to a Doc 2 key point and a Doc 0 source.*",
            "",
        ]

    return "\n".join(lines)


def format_social_kit_from_dict(kit_dict: dict, **kwargs: object) -> str:
    """Convenience wrapper."""
    kit = SocialKitDocument(**kit_dict)
    return format_social_kit(kit, **kwargs)
