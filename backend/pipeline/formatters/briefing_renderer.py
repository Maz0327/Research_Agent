"""Render a Briefing as HTML, deterministically.

The visual spec is the owner-approved mockup pair (D-025), and this module's
stylesheet is that mockup's, verbatim: the format was validated as it looks,
so the renderer reproduces it rather than reinterpreting it.

No model is involved. Structure, ordering, chips, citation tags, and vault
links are all decided before rendering; this turns the JSON into the page.
Markdown and Drive exports are lossy secondary renders of the same JSON.
"""

import html
import itertools
import re

from backend.models.briefing import Briefing

SECTION_TITLES = [
    "The Read",
    "The Players",
    "The Organisations",
    "The Places",
    "The Record",
    "The Files",
    "Disputed & Uncertain",
    "Details & Anecdotes",
    "Info Gaps",
    "Source Trail",
]

BRIEFING_CSS = r"""  :root {
    --ground: #EFEEE8;
    --panel: #E7E5DC;
    --ink: #20231F;
    --ink-soft: #5A5E56;
    --accent: #175E66;
    --accent-soft: #175E661A;
    --rule: #CFCDC2;
    --solid: #2F6E45;
    --solid-bg: #2F6E4518;
    --contested: #9A6414;
    --contested-bg: #9A641418;
    --network: #9C3D22;
    --network-bg: #9C3D2216;
    --anno: #175E66;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --ground: #15181A;
      --panel: #1D2124;
      --ink: #E6E3D8;
      --ink-soft: #9AA097;
      --accent: #63B8BC;
      --accent-soft: #63B8BC1C;
      --rule: #33383B;
      --solid: #6FBE8B;
      --solid-bg: #6FBE8B1A;
      --contested: #D9A84E;
      --contested-bg: #D9A84E1A;
      --network: #E07B5C;
      --network-bg: #E07B5C18;
      --anno: #63B8BC;
    }
  }
  :root[data-theme="dark"] {
    --ground: #15181A;
    --panel: #1D2124;
    --ink: #E6E3D8;
    --ink-soft: #9AA097;
    --accent: #63B8BC;
    --accent-soft: #63B8BC1C;
    --rule: #33383B;
    --solid: #6FBE8B;
    --solid-bg: #6FBE8B1A;
    --contested: #D9A84E;
    --contested-bg: #D9A84E1A;
    --network: #E07B5C;
    --network-bg: #E07B5C18;
    --anno: #63B8BC;
  }

  * { box-sizing: border-box; }
  body {
    background: var(--ground);
    color: var(--ink);
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    font-size: 17px;
    line-height: 1.62;
    margin: 0;
    padding: 0 20px 96px;
  }
  .page { max-width: 74ch; margin: 0 auto; }
  .mono {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }

  /* ---------- masthead ---------- */
  .mockup-band {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 11.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--anno);
    border: 1px dashed var(--anno);
    border-radius: 3px;
    padding: 8px 12px;
    margin: 28px 0 40px;
  }
  header.mast { margin: 0 0 12px; }
  .doc-kicker {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-soft);
    margin: 0 0 10px;
  }
  h1 {
    font-size: 40px;
    line-height: 1.12;
    font-weight: 600;
    margin: 0 0 18px;
    text-wrap: balance;
    letter-spacing: -0.01em;
  }
  .meta-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 22px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12.5px;
    color: var(--ink-soft);
    padding: 12px 0;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    margin-bottom: 8px;
  }
  .meta-strip b { color: var(--ink); font-weight: 600; }

  /* ---------- section scaffolding ---------- */
  section { margin-top: 64px; }
  summary { cursor: pointer; list-style: none; }
  summary::-webkit-details-marker { display: none; }
  summary:focus-visible { outline: 2px solid currentColor; outline-offset: 4px; }
  .sec-head { position: relative; }
  .sec-head::after {
    content: "\\25B8"; position: absolute; right: 0; top: 50%;
    transform: translateY(-50%); opacity: .45; font-size: 20px;
    transition: transform .15s ease;
  }
  details[open] > summary .sec-head::after { transform: translateY(-50%) rotate(90deg); }
  details.file { border-top: 1px solid rgba(128,128,128,.25); padding-top: 12px; }
  details.file > summary .filehead { position: relative; padding-right: 22px; }
  details.file > summary .filehead::after {
    content: "\\25B8"; position: absolute; right: 0; top: 4px; opacity: .45;
    transition: transform .15s ease;
  }
  details.file[open] > summary .filehead::after { transform: rotate(90deg); }
  .sec-head { border-top: 3px solid var(--ink); padding-top: 14px; }
  .sec-num {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    letter-spacing: 0.12em;
    color: var(--ink-soft);
  }
  h2 {
    font-size: 27px;
    font-weight: 600;
    margin: 4px 0 6px;
    text-wrap: balance;
  }
  .anno {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.55;
    color: var(--anno);
    background: var(--accent-soft);
    border-left: 3px solid var(--anno);
    padding: 8px 12px;
    margin: 12px 0 26px;
  }
  /* Work order I.29b: the update note sits above the document, styled from the
     locked palette so it reads as part of the Briefing rather than bolted on. */
  .addendum {
    border: 1px solid var(--anno);
    border-left-width: 4px;
    background: var(--accent-soft);
    padding: 14px 18px 4px;
    margin: 0 0 30px;
  }
  .addendum h2 {
    font-size: 19px;
    margin: 0 0 6px;
  }
  .addendum ul {
    margin: 8px 0 12px 18px;
    padding: 0;
  }
  h3 {
    font-size: 19px;
    font-weight: 600;
    margin: 34px 0 8px;
  }
  p { margin: 0 0 16px; }
  p.tight { margin-bottom: 8px; }

  /* ---------- chips ---------- */
  .chip {
    display: inline-block;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 10.5px;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    border-radius: 3px;
    padding: 2px 7px 1px;
    vertical-align: 2px;
    white-space: nowrap;
  }
  .chip.solid { color: var(--solid); background: var(--solid-bg); }
  .chip.contested { color: var(--contested); background: var(--contested-bg); }
  .chip.network { color: var(--network); background: var(--network-bg); }
  .src {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    color: var(--ink-soft);
  }

  /* ---------- section 1 body ---------- */
  .read p:first-of-type::first-line { letter-spacing: 0.01em; }
  .read .lede { font-size: 18.5px; }

  /* ---------- player cards ---------- */
  .players { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 20px; }
  @media (max-width: 620px) { .players { grid-template-columns: 1fr; } }
  details.player {
    background: var(--panel);
    border-radius: 4px;
    align-self: start;
  }
  details.player summary {
    cursor: pointer;
    list-style: none;
    padding: 14px 16px 12px;
    position: relative;
  }
  details.player summary::-webkit-details-marker { display: none; }
  details.player summary::after {
    content: "+";
    position: absolute;
    top: 12px; right: 14px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 15px;
    color: var(--accent);
  }
  details.player[open] summary::after { content: "\2212"; }
  details.player summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .player .name { display: block; font-weight: 600; font-size: 16.5px; padding-right: 22px; }
  .player .role {
    display: block;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-soft);
    margin-top: 1px;
  }
  details.player p { font-size: 14.5px; line-height: 1.55; margin: 0; padding: 0 16px 14px; }

  /* ---------- timeline ---------- */
  .timeline { list-style: none; margin: 20px 0 0; padding: 0; }
  .timeline li {
    display: grid;
    grid-template-columns: 108px 1fr;
    gap: 16px;
    padding: 10px 0;
    border-bottom: 1px solid var(--rule);
  }
  .timeline .when {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    color: var(--accent);
    padding-top: 2px;
  }
  .timeline .what { font-size: 15.5px; line-height: 1.55; }

  /* ---------- files ---------- */
  .file { border: 1px solid var(--rule); border-radius: 4px; padding: 18px 20px 6px; margin-top: 22px; background: transparent; }
  .file h3 { margin-top: 0; }
  .file .filehead { display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px; margin-bottom: 10px; }
  .file p { font-size: 15.5px; }
  .file-note {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    color: var(--ink-soft);
    margin: 26px 0 0;
  }

  /* ---------- dispute table ---------- */
  .disputes { margin-top: 20px; border-top: 1px solid var(--rule); }
  .dispute {
    display: grid;
    grid-template-columns: 1fr 128px;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid var(--rule);
  }
  @media (max-width: 560px) { .dispute { grid-template-columns: 1fr; gap: 6px; } }
  .dispute p { font-size: 15.5px; margin: 0 0 4px; }
  .dispute .holders { font-size: 13.5px; color: var(--ink-soft); margin: 0; }
  .dispute .verdict { text-align: right; }
  @media (max-width: 560px) { .dispute .verdict { text-align: left; } }

  /* ---------- dropdowns ---------- */
  details.more {
    margin-top: 8px;
    border: 1px solid var(--rule);
    border-radius: 4px;
    background: var(--panel);
  }
  details.more summary {
    cursor: pointer;
    padding: 7px 12px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 11.5px;
    letter-spacing: 0.05em;
    color: var(--accent);
    list-style-position: inside;
  }
  details.more summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  details.more .body { padding: 2px 16px 12px; font-size: 14.5px; line-height: 1.6; }
  details.more .body p { margin: 0 0 10px; }
  details.more .side {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    display: block;
    margin: 10px 0 3px;
  }
  details.more .side.for { color: var(--solid); }
  details.more .side.against { color: var(--network); }

  /* ---------- anecdotes ---------- */
  .anecdotes { list-style: none; margin: 20px 0 0; padding: 0; }
  .anecdotes li {
    padding: 10px 0 10px 18px;
    border-left: 2px solid var(--rule);
    margin-bottom: 10px;
    font-size: 15.5px;
    line-height: 1.55;
  }

  /* ---------- open questions ---------- */
  .oq { counter-reset: oq; list-style: none; margin: 20px 0 0; padding: 0; }
  .oq li { counter-increment: oq; margin-bottom: 20px; padding-left: 40px; position: relative; }
  .oq li::before {
    content: counter(oq, decimal-leading-zero);
    position: absolute; left: 0; top: 3px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 13px;
    color: var(--accent);
  }
  .oq .q { font-weight: 600; }
  .oq .go {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12.5px;
    color: var(--ink-soft);
    display: block;
    margin-top: 3px;
  }

  /* ---------- source trail ---------- */
  .trail { margin-top: 20px; border-top: 1px solid var(--rule); }
  .trail-row {
    display: grid;
    grid-template-columns: 64px 1fr;
    gap: 14px;
    padding: 11px 0;
    border-bottom: 1px solid var(--rule);
    font-size: 14.5px;
    line-height: 1.5;
  }
  .trail-row .sid {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12.5px;
    color: var(--accent);
    padding-top: 2px;
  }
  .trail-row .what b { font-weight: 600; }
  .trail-row .contrib { color: var(--ink-soft); font-size: 13.5px; }

  a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }
  footer {
    margin-top: 72px;
    padding-top: 16px;
    border-top: 3px solid var(--ink);
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    color: var(--ink-soft);
    line-height: 1.7;
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""


def _esc(text: str | None) -> str:
    """HTML-escape a value, treating None as empty."""
    return html.escape(text or "", quote=True)


def _src_tag(source_ids: list[str], vault_url: str = "") -> str:
    """Render a citation tag: bare IDs, linked into the vault when there is one.

    Named citation belongs in the prose (D-025); this is the trailing tag.
    """
    if not source_ids:
        return ""
    parts = []
    for source_id in source_ids:
        label = _esc(source_id)
        if vault_url:
            parts.append(f'<a href="{_esc(vault_url)}#{source_id.lower()}">{label}</a>')
        else:
            parts.append(label)
    return f'<span class="src">{" &middot; ".join(parts)}</span>'


def _section_head(number: int, title: str) -> str:
    """The numbered section header used throughout the document."""
    return (
        '<div class="sec-head">'
        f'<span class="sec-num">SECTION {number}</span>'
        f"<h2>{_esc(title)}</h2>"
        "</div>"
    )


def _chips(chips) -> str:
    """Evidence-status chips, coloured by their tone."""
    return " ".join(
        f'<span class="chip {_esc(c.tone)}">{_esc(c.label)}</span>' for c in chips
    )


def _paragraphs(text: str) -> str:
    """Split model prose into paragraphs without touching its words."""
    blocks = [b.strip() for b in (text or "").split("\n\n") if b.strip()]
    return "".join(f"<p>{_esc(block)}</p>" for block in blocks) or "<p></p>"


def _render_read(briefing: Briefing) -> str:
    parts = [_section_head(1, SECTION_TITLES[0]), '<div class="read">']
    if briefing.read.lede:
        parts.append(f'<p class="lede">{_esc(briefing.read.lede)}</p>')
    for paragraph in briefing.read.paragraphs:
        lead = f"<strong>{_esc(paragraph.label)}:</strong> " if paragraph.label else ""
        parts.append(f"<p>{lead}{_esc(paragraph.text)}</p>")
    parts.append("</div>")
    return "<section>" + "".join(parts) + "</section>"


def _render_players(briefing: Briefing, vault_url: str) -> str:
    if not briefing.players:
        return ""
    cards = []
    for player in briefing.players:
        cards.append(
            '<details class="player"><summary>'
            f'<span class="name">{_esc(player.name)}</span>'
            f'<span class="role">{_esc(player.role)}</span></summary>'
            f"<p>{_esc(player.body)} {_src_tag(player.source_ids, vault_url)}</p>"
            "</details>"
        )
    return (
        "<section>"
        + _section_head(2, SECTION_TITLES[1])
        + '<div class="players">'
        + "".join(cards)
        + "</div></section>"
    )


def _render_organisations(briefing: Briefing, vault_url: str) -> str:
    """Section 3. Same card as a player; a reader looking up a person should
    not have to read past a newspaper to find them."""
    if not briefing.organisations:
        return ""
    cards = []
    for org in briefing.organisations:
        cards.append(
            '<details class="player"><summary>'
            f'<span class="name">{_esc(org.name)}</span>'
            f'<span class="role">{_esc(org.role)}</span></summary>'
            f"<p>{_esc(org.body)} {_src_tag(org.source_ids, vault_url)}</p>"
            "</details>"
        )
    return (
        "<section>"
        + _section_head(3, SECTION_TITLES[2])
        + '<div class="players">'
        + "".join(cards)
        + "</div></section>"
    )


def _render_places(briefing: Briefing, vault_url: str) -> str:
    """Place cards reuse the player card markup on purpose: the stylesheet is
    the owner-approved mockup's verbatim, so a new section borrows a validated
    shape rather than growing its own."""
    if not briefing.places:
        return ""
    cards = []
    for place in briefing.places:
        cards.append(
            '<details class="player"><summary>'
            f'<span class="name">{_esc(place.name)}</span>'
            f'<span class="role">{_esc(place.line)}</span></summary>'
            f"<p>{_esc(place.body)} {_src_tag(place.source_ids, vault_url)}</p>"
            "</details>"
        )
    return (
        "<section>"
        + _section_head(4, SECTION_TITLES[3])
        + '<div class="players">'
        + "".join(cards)
        + "</div></section>"
    )


def _render_record(briefing: Briefing, vault_url: str) -> str:
    if not briefing.record:
        return ""
    rows = []
    for entry in briefing.record:
        more = (
            '<details class="more"><summary>More</summary>'
            f'<div class="body"><p>{_esc(entry.context)}</p></div></details>'
            if entry.context
            else ""
        )
        rows.append(
            f'<li><span class="when">{_esc(entry.when)}</span>'
            f'<span class="what">{_esc(entry.what)} '
            f"{_src_tag(entry.source_ids, vault_url)}{more}</span></li>"
        )
    return (
        "<section>"
        + _section_head(5, SECTION_TITLES[4])
        + '<ul class="timeline">'
        + "".join(rows)
        + "</ul></section>"
    )


def _render_files(briefing: Briefing, vault_url: str) -> str:
    if not briefing.files:
        return ""
    blocks = []
    for file in briefing.files:
        blocks.append(
            '<details class="file">'
            f'<summary><div class="filehead"><h3>File: {_esc(file.title)}</h3> {_chips(file.chips)}</div></summary>'
            f"{_paragraphs(file.body)}"
            f"<p>{_src_tag(file.source_ids, vault_url)}</p>"
            "</details>"
        )
    return "<section>" + _section_head(6, SECTION_TITLES[5]) + "".join(blocks) + "</section>"


def _render_disputes(briefing: Briefing, vault_url: str) -> str:
    if not briefing.disputes:
        return ""
    blocks = []
    for dispute in briefing.disputes:
        blocks.append(
            '<div class="dispute"><div>'
            f"<p>{_esc(dispute.claim)}</p>"
            f'<p class="holders">{_esc(dispute.holders)}</p>'
            '<details class="more"><summary>Full case, both sides</summary>'
            '<div class="body">'
            f'<span class="side for">{_esc(dispute.case_for.heading)}</span>'
            f"<p>{_esc(dispute.case_for.text)} "
            f"{_src_tag(dispute.case_for.source_ids, vault_url)}</p>"
            f'<span class="side against">{_esc(dispute.case_against.heading)}</span>'
            f"<p>{_esc(dispute.case_against.text)} "
            f"{_src_tag(dispute.case_against.source_ids, vault_url)}</p>"
            "</div></details></div>"
            f'<div class="verdict">{_chips([dispute.chip])}</div>'
            "</div>"
        )
    return (
        "<section>"
        + _section_head(7, SECTION_TITLES[6])
        + '<div class="disputes">'
        + "".join(blocks)
        + "</div></section>"
    )


def _render_anecdotes(briefing: Briefing, vault_url: str) -> str:
    if not briefing.anecdotes:
        return ""
    items = []
    for anecdote in briefing.anecdotes:
        more = (
            '<details class="more"><summary>Context</summary>'
            f'<div class="body"><p>{_esc(anecdote.context)}</p></div></details>'
            if anecdote.context
            else ""
        )
        items.append(
            f"<li>{_esc(anecdote.text)} "
            f"{_src_tag(anecdote.source_ids, vault_url)}{more}</li>"
        )
    return (
        "<section>"
        + _section_head(8, SECTION_TITLES[7])
        + '<ul class="anecdotes">'
        + "".join(items)
        + "</ul></section>"
    )


def _render_gaps(briefing: Briefing) -> str:
    if not briefing.info_gaps:
        return ""
    items = []
    for gap in briefing.info_gaps:
        items.append(
            f'<li><span class="q">{_esc(gap.question)}</span> {_esc(gap.why)} '
            f'<span class="go">&rarr; {_esc(gap.go_get)}</span></li>'
        )
    return (
        "<section>"
        + _section_head(9, SECTION_TITLES[8])
        + '<ol class="oq">'
        + "".join(items)
        + "</ol></section>"
    )


def _render_trail(briefing: Briefing, vault_url: str) -> str:
    if not briefing.source_trail:
        return ""
    rows = []
    for entry in briefing.source_trail:
        anchor = (
            f'<a href="{_esc(vault_url)}#{entry.source_id.lower()}">{_esc(entry.source_id)}</a>'
            if vault_url
            else _esc(entry.source_id)
        )
        descriptors = [d for d in (entry.kind, entry.year, entry.creator) if d]
        descriptor = f" ({_esc(', '.join(str(d) for d in descriptors))})" if descriptors else ""
        notes = []
        if entry.duplicate_of:
            notes.append(f"republication of {_esc(entry.duplicate_of)}")
        if entry.note:
            notes.append(_esc(entry.note))
        note = f" [{'; '.join(notes)}]" if notes else ""
        contribution = (
            f'<span class="contrib">&mdash; {_esc(entry.contribution)}</span>'
            if entry.contribution
            else ""
        )
        rows.append(
            f'<div class="trail-row"><span class="sid">{anchor}</span>'
            f'<span class="what"><b>{_esc(entry.title)}</b>{descriptor}{note} '
            f"{contribution}</span></div>"
        )
    return (
        "<section>"
        + _section_head(10, SECTION_TITLES[9])
        + '<div class="trail">'
        + "".join(rows)
        + "</div></section>"
    )


def _render_masthead(briefing: Briefing) -> str:
    meta = briefing.meta
    bits = [f"<span><b>{meta.source_count}</b> sources</span>"]
    if meta.independent_source_count != meta.source_count:
        bits.append(f"<span><b>{meta.independent_source_count}</b> independent</span>")
    bits.append(f"<span><b>{meta.raw_words:,}</b> raw words read</span>")
    if meta.quote_verification_rate is not None:
        bits.append(f"<span>quotes verified <b>{meta.quote_verification_rate:.0%}</b></span>")
    if meta.confidence:
        bits.append(f"<span>confidence <b>{_esc(str(meta.confidence))}</b></span>")
    if meta.generated_on:
        bits.append(f"<span>{_esc(meta.generated_on)}</span>")
    return (
        '<header class="mast">'
        '<p class="doc-kicker">Research Briefing</p>'
        f"<h1>{_esc(briefing.topic)}</h1>"
        f'<div class="meta-strip">{"".join(bits)}</div>'
        "</header>"
    )


def _render_balance(briefing: Briefing) -> str:
    balance = briefing.corpus_balance
    if not balance:
        return ""
    bits = []
    if balance.domains:
        bits.append(
            "domains: "
            + ", ".join(f"{_esc(d)} ({n})" for d, n in sorted(balance.domains.items()))
        )
    if balance.date_range:
        bits.append(f"dates: {_esc(balance.date_range)}")
    if balance.stance_counts:
        bits.append(
            "stance: "
            + ", ".join(f"{_esc(s)} ({n})" for s, n in sorted(balance.stance_counts.items()))
        )
    if balance.network_note:
        bits.append(_esc(balance.network_note))
    return f'<div class="anno">Corpus balance &mdash; {" &middot; ".join(bits)}</div>' if bits else ""


def _render_addendum(briefing: Briefing) -> str:
    """Render the dated update note above everything else (work order I.29b).

    Addendum-first is the whole point: new material arrives as a delta the
    owner can read in a few seconds, and the sections it touched are named so
    a re-read is targeted rather than total.
    """
    addendum = briefing.addendum
    if not addendum:
        return ""

    items = "".join(
        "<li>"
        + (
            f'<a href="{_esc(item.get("url", ""))}">{_esc(item.get("title") or item.get("url", ""))}</a>'
            if item.get("url")
            else _esc(item.get("title", ""))
        )
        + (f" <span class=\"anno\">{_esc(item['published'])}</span>" if item.get("published") else "")
        + "</li>"
        for item in addendum.new_items
    )
    touched = (
        f'<p class="anno">Updated sections: {_esc(", ".join(addendum.changed_sections))} '
        f"&mdash; the rest is unchanged since your last read.</p>"
        if addendum.changed_sections
        else ""
    )
    return (
        '<section class="addendum">'
        f"<h2>Update check &mdash; {_esc(addendum.checked_on)}</h2>"
        f"<p><strong>{_esc(addendum.headline)}</strong></p>"
        + (f"<ul>{items}</ul>" if items else "")
        + touched
        + "</section>"
    )


_SECTION_RE = re.compile(
    r'<section([^>]*)>(<div class="sec-head">.*?</div>)(.*?)</section>', re.S
)


def _collapsible(html: str) -> str:
    """Turn each numbered section into a disclosure.

    A briefing is a reference document, not an essay: nine sections and 28,000
    words open as a wall unless the page starts as an index. The Read stays
    open because that is the part meant to be read straight through; the
    reference sections open on demand.

    Args:
        html: The assembled document body.

    Returns:
        The same document with each numbered section collapsible.
    """

    counter = itertools.count(1)

    def wrap(match: "re.Match[str]") -> str:
        attrs, head, body = match.groups()
        # Numbers follow what is actually emitted. Every section is
        # conditional but each carried a hardcoded number, so an empty one
        # made the numbering skip — and adding Organisations would have made
        # that visible on every briefing without places.
        number = next(counter)
        head = re.sub(r"(<span class=\"sec-num\">SECTION )\d+", rf"\g<1>{number}", head)
        opened = " open" if number == 1 else ""
        return (
            f"<section{attrs}><details{opened}>"
            f"<summary>{head}</summary>{body}</details></section>"
        )

    return _SECTION_RE.sub(wrap, html)


def render_briefing_html(briefing: Briefing, vault_url: str = "") -> str:
    """Render a Briefing as a standalone HTML page.

    Args:
        briefing: The assembled Briefing.
        vault_url: URL of the companion Source Vault; when empty, source IDs
            render as plain text rather than dead links.

    Returns:
        A complete HTML document.
    """
    body = "".join(
        [
            _render_masthead(briefing),
            _render_addendum(briefing),
            _render_balance(briefing),
            _render_read(briefing),
            _render_players(briefing, vault_url),
            _render_organisations(briefing, vault_url),
            _render_places(briefing, vault_url),
            _render_record(briefing, vault_url),
            _render_files(briefing, vault_url),
            _render_disputes(briefing, vault_url),
            _render_anecdotes(briefing, vault_url),
            _render_gaps(briefing),
            _render_trail(briefing, vault_url),
        ]
    )
    footer = (
        "<footer>Briefing generated from job "
        f"{_esc(briefing.job_id)} &middot; every claim traces to raw source text via the "
        "IDs shown &middot; Section 1 is written for reading; Sections 2&ndash;9 are the "
        "reference layer"
        + (
            f' &middot; <a href="{_esc(vault_url)}">raw texts of all sources</a>'
            if vault_url
            else ""
        )
        + "</footer>"
    )
    return (
        # Without this the file is read as Latin-1 when opened directly or
        # served without a charset header, and every curly quote and dash
        # in the prose renders as mojibake (2026-08-31).
        '<meta charset="utf-8">\n'
        f"<title>{_esc(briefing.topic)}</title>\n"
        f"<style>{BRIEFING_CSS}</style>\n"
        f'<div class="page">{_collapsible(body)}{footer}</div>\n'
    )


def _md_escape(text: str | None) -> str:
    """Keep markdown structural characters from reflowing source text."""
    return (text or "").replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")


def render_briefing_markdown(briefing: Briefing) -> str:
    """Render a Briefing as Markdown.

    A lossy secondary export by design (D-025): the format's dropdowns, chips,
    and anchors have no Markdown equivalent, so context notes and both sides of
    a dispute are flattened inline. The JSON stays canonical and the HTML stays
    primary; this exists for Drive and for anything that only reads Markdown.

    Args:
        briefing: The assembled Briefing.

    Returns:
        A Markdown document.
    """
    meta = briefing.meta
    out: list[str] = [f"# {briefing.topic}", ""]

    facts = [f"{meta.source_count} sources"]
    if meta.independent_source_count != meta.source_count:
        facts.append(f"{meta.independent_source_count} independent")
    facts.append(f"{meta.raw_words:,} raw words read")
    if meta.quote_verification_rate is not None:
        facts.append(f"quotes verified {meta.quote_verification_rate:.0%}")
    if meta.confidence:
        facts.append(f"confidence {meta.confidence}")
    if meta.generated_on:
        facts.append(meta.generated_on)
    out += [" · ".join(facts), ""]

    # Numbers follow what is actually emitted. Every section here is
    # conditional, so hardcoded numbers skipped one whenever a section was
    # empty — visible the moment Places arrived and a briefing with no places
    # rendered "2. The Players" straight into "4. The Record" (2026-08-31).
    counter = itertools.count(1)

    def heading(title: str) -> str:
        return f"## {next(counter)}. {title}"

    out += [heading("The Read"), "", _md_escape(briefing.read.lede), ""]
    for paragraph in briefing.read.paragraphs:
        lead = f"**{_md_escape(paragraph.label)}:** " if paragraph.label else ""
        out += [f"{lead}{_md_escape(paragraph.text)}", ""]

    if briefing.players:
        out += [heading("The Players"), ""]
        for player in briefing.players:
            cite = f" ({' · '.join(player.source_ids)})" if player.source_ids else ""
            out += [
                f"**{_md_escape(player.name)}** — {_md_escape(player.role)}",
                "",
                f"{_md_escape(player.body)}{cite}",
                "",
            ]

    if briefing.organisations:
        out += [heading("The Organisations"), ""]
        for org in briefing.organisations:
            cite = f" ({' · '.join(org.source_ids)})" if org.source_ids else ""
            out += [
                f"**{_md_escape(org.name)}** — {_md_escape(org.role)}",
                "",
                f"{_md_escape(org.body)}{cite}",
                "",
            ]

    if briefing.places:
        out += [heading("The Places"), ""]
        for place in briefing.places:
            cite = f" ({' · '.join(place.source_ids)})" if place.source_ids else ""
            out += [
                f"**{_md_escape(place.name)}** — {_md_escape(place.line)}",
                "",
                f"{_md_escape(place.body)}{cite}",
                "",
            ]

    if briefing.record:
        out += [heading("The Record"), ""]
        for entry in briefing.record:
            cite = f" ({' · '.join(entry.source_ids)})" if entry.source_ids else ""
            out.append(f"- **{_md_escape(entry.when)}** — {_md_escape(entry.what)}{cite}")
            if entry.context:
                out.append(f"  - {_md_escape(entry.context)}")
        out.append("")

    if briefing.files:
        out += [heading("The Files"), ""]
        for file in briefing.files:
            chips = " ".join(f"`{c.label}`" for c in file.chips)
            cite = f" ({' · '.join(file.source_ids)})" if file.source_ids else ""
            out += [f"### {_md_escape(file.title)} {chips}".strip(), ""]
            for block in (file.body or "").split("\n\n"):
                if block.strip():
                    out += [_md_escape(block.strip()), ""]
            if cite:
                out += [cite.strip(), ""]

    if briefing.disputes:
        out += [heading("Disputed & Uncertain"), ""]
        for dispute in briefing.disputes:
            out += [
                f"### {_md_escape(dispute.claim)} `{dispute.chip.label}`",
                "",
                f"*{_md_escape(dispute.holders)}*",
                "",
                f"**{_md_escape(dispute.case_for.heading)}** — "
                f"{_md_escape(dispute.case_for.text)}"
                + (f" ({' · '.join(dispute.case_for.source_ids)})" if dispute.case_for.source_ids else ""),
                "",
                f"**{_md_escape(dispute.case_against.heading)}** — "
                f"{_md_escape(dispute.case_against.text)}"
                + (f" ({' · '.join(dispute.case_against.source_ids)})" if dispute.case_against.source_ids else ""),
                "",
            ]

    if briefing.anecdotes:
        out += [heading("Details & Anecdotes"), ""]
        for anecdote in briefing.anecdotes:
            cite = f" ({' · '.join(anecdote.source_ids)})" if anecdote.source_ids else ""
            out.append(f"- {_md_escape(anecdote.text)}{cite}")
            if anecdote.context:
                out.append(f"  - {_md_escape(anecdote.context)}")
        out.append("")

    if briefing.info_gaps:
        out += [heading("Info Gaps"), ""]
        for gap in briefing.info_gaps:
            out.append(
                f"- **{_md_escape(gap.question)}** {_md_escape(gap.why)} "
                f"→ {_md_escape(gap.go_get)}"
            )
        out.append("")

    if briefing.source_trail:
        out += [heading("Source Trail"), ""]
        for entry in briefing.source_trail:
            descriptors = [d for d in (entry.kind, entry.year, entry.creator) if d]
            descriptor = f" ({', '.join(str(d) for d in descriptors)})" if descriptors else ""
            notes = []
            if entry.duplicate_of:
                notes.append(f"republication of {entry.duplicate_of}")
            if entry.note:
                notes.append(entry.note)
            note = f" [{'; '.join(notes)}]" if notes else ""
            contribution = f" — {_md_escape(entry.contribution)}" if entry.contribution else ""
            out.append(
                f"- **{entry.source_id}** {_md_escape(entry.title)}{descriptor}{note}{contribution}"
            )
        out.append("")

    return "\n".join(out).rstrip() + "\n"
