"""Generate the Source Vault: every source's raw text, by code alone.

D-025 makes this a companion to the Briefing and puts it entirely in code's
hands: no model reads, cleans, or summarizes anything here. Whatever the
pipeline captured is what the page shows, including a source's own typos, its
filler, and its sponsor reads. The Briefing's SRC ids link into it, so any
claim can be traced to the text it came from in one hop.

The vault is private by default (work order I.27): a paywalled source is
flagged and rendered as an excerpt plus a link instead of full text.
"""

import html
from typing import Optional

VAULT_CSS = r"""  :root { --ground:#EFEEE8; --panel:#E7E5DC; --ink:#20231F; --ink-soft:#5A5E56; --accent:#175E66; --rule:#CFCDC2; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --ground:#15181A; --panel:#1D2124; --ink:#E6E3D8; --ink-soft:#9AA097; --accent:#63B8BC; --rule:#33383B; } }
  :root[data-theme="dark"] { --ground:#15181A; --panel:#1D2124; --ink:#E6E3D8; --ink-soft:#9AA097; --accent:#63B8BC; --rule:#33383B; }
  * { box-sizing: border-box; }
  body { background:var(--ground); color:var(--ink); font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif; font-size:16.5px; line-height:1.62; margin:0; padding:0 20px 96px; }
  .page { max-width:78ch; margin:0 auto; }
  .kicker { font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-soft); margin:36px 0 10px; }
  h1 { font-size:34px; line-height:1.15; font-weight:600; margin:0 0 14px; }
  .intro { font-size:15.5px; color:var(--ink-soft); border-top:1px solid var(--rule); border-bottom:1px solid var(--rule); padding:12px 0; margin-bottom:34px; }
  .toc { font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:13px; line-height:2; margin-bottom:44px; column-count:2; column-gap:32px; }
  @media (max-width:560px){ .toc { column-count:1; } }
  .toc a { color:var(--accent); text-decoration:none; }
  .toc a:hover, .toc a:focus { text-decoration:underline; }
  .toc .t { color:var(--ink); }
  .src-block { border-top:3px solid var(--ink); padding-top:14px; margin-top:44px; }
  .sid { font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px; letter-spacing:.12em; color:var(--accent); }
  h2 { font-size:22px; font-weight:600; margin:4px 0 6px; text-wrap:balance; }
  .meta { font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px; color:var(--ink-soft); margin-bottom:12px; overflow-wrap:break-word; }
  .meta a { color:var(--accent); }
  details { border:1px solid var(--rule); border-radius:4px; background:var(--panel); }
  summary { cursor:pointer; padding:10px 14px; font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12.5px; color:var(--accent); }
  summary:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  .fulltext { padding:4px 18px 16px; font-size:15px; line-height:1.68; white-space:pre-wrap; overflow-wrap:break-word; }
  .none { font-style:italic; color:var(--ink-soft); }
  footer { margin-top:64px; padding-top:14px; border-top:3px solid var(--ink); font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12px; color:var(--ink-soft); line-height:1.7; }
"""

# Markers that a capture is a paywalled or metered page rather than the article
PAYWALL_MARKERS = (
    "subscribe to continue",
    "subscribers only",
    "this article is for subscribers",
    "create an account to keep reading",
    "you have reached your article limit",
    "register to continue reading",
    "sign in to read",
)

# How much of a flagged source the vault will show
EXCERPT_CHARS = 600


def _esc(text: Optional[str]) -> str:
    """HTML-escape a value, treating None as empty."""
    return html.escape(text or "", quote=True)


def looks_paywalled(text: str) -> bool:
    """Does this capture look like a paywall page rather than the article?

    Args:
        text: The captured text.

    Returns:
        True when a paywall marker is present.
    """
    lowered = (text or "").lower()
    return any(marker in lowered for marker in PAYWALL_MARKERS)


def render_source_vault(
    title: str,
    sources: list[dict],
    job_id: str = "",
    generated_on: str = "",
    product_mode: bool = False,
) -> str:
    """Render the raw-source companion page.

    Args:
        title: Page title, usually "The <topic> Sources".
        sources: Source dicts with `source_id`, `title`, `url`, `full_text`,
            and optionally `source_type`, `creator`, `published`,
            `duplicate_of`, `full_text_unavailable_reason`.
        job_id: Job the vault belongs to, shown in the footer.
        generated_on: ISO date, shown in the footer.
        product_mode: When True, sources that look paywalled render as an
            excerpt plus a link instead of their full text.

    Returns:
        A complete HTML document.
    """
    toc = []
    blocks = []

    for source in sources:
        source_id = source.get("source_id", "SRC_?")
        anchor = source_id.lower()
        source_title = source.get("title") or "Untitled"
        text = source.get("full_text") or ""
        words = len(text.split())

        toc.append(
            f'<div><a href="#{_esc(anchor)}">{_esc(source_id)}</a> '
            f'<span class="t">{_esc(source_title[:52])}</span></div>'
        )

        descriptors = [source.get("source_type") or "source"]
        if words:
            descriptors.append(f"{words:,} words")
        if source.get("creator"):
            descriptors.append(str(source["creator"]))
        if source.get("published"):
            descriptors.append(str(source["published"]))
        if source.get("duplicate_of"):
            descriptors.append(f"republication of {source['duplicate_of']}")

        url = source.get("url") or ""
        meta = (
            f'<p class="meta"><a href="{_esc(url)}">{_esc(url)}</a></p>' if url else ""
        )

        if not text.strip():
            reason = source.get("full_text_unavailable_reason") or "No text captured"
            body = f'<p class="none">{_esc(reason)}</p>'
        elif product_mode and looks_paywalled(text):
            body = (
                '<p class="none">This source is paywalled; the vault shows an '
                "excerpt and links to the original.</p>"
                f'<div class="fulltext">{_esc(text[:EXCERPT_CHARS])}&hellip;</div>'
            )
        else:
            body = (
                "<details><summary>Full raw text &mdash; click to expand</summary>"
                f'<div class="fulltext">{_esc(text)}</div></details>'
            )

        blocks.append(
            f'<section class="src-block" id="{_esc(anchor)}">'
            f'<span class="sid">{_esc(source_id)} &middot; '
            f'{_esc(" &middot; ".join(str(d) for d in descriptors))}</span>'
            f"<h2>{_esc(source_title)}</h2>{meta}{body}</section>"
        )

    captured = sum(1 for s in sources if (s.get("full_text") or "").strip())
    total_words = sum(len((s.get("full_text") or "").split()) for s in sources)
    footer_bits = [
        f"{len(sources)} sources, {captured} with captured text, {total_words:,} words"
    ]
    if job_id:
        footer_bits.append(f"job {job_id}")
    if generated_on:
        footer_bits.append(generated_on)

    return (
        f"<title>{_esc(title)}</title>\n"
        f"<style>{VAULT_CSS}</style>\n"
        '<div class="page">'
        '<p class="kicker">Doc 0 companion &middot; raw source vault</p>'
        f"<h1>{_esc(title)}</h1>"
        '<p class="intro">The unedited full text of every source behind the '
        "Briefing, exactly as ingested. Nothing here is summarized or cleaned. "
        "Every SRC id cited in the Briefing links to its entry on this page.</p>"
        f'<nav class="toc">{"".join(toc)}</nav>'
        f'{"".join(blocks)}'
        f'<footer>{_esc(" &middot; ".join(footer_bits))}</footer>'
        "</div>\n"
    )
