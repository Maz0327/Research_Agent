"""Inline-introduction repair (§J pass 8's repair round).

The D-025 cast cap put every name below the fourteenth card on the one-off
rule: introduced wherever the reader meets them. The lint enforces it. This is
the half that fixes it.

It works by pairs applied by code, never by re-emission (D-024). The model is
asked for one gloss per name — four or five words, no sentence — and code
splices it in after the name. The model never sees the document back and never
rewrites a line it already wrote, so a repair cannot quietly change a fact
somewhere else in the paragraph while fixing a name.

One round only. A name the round could not introduce stays flagged, which is
the correct outcome: a lint error is a thing to look at, and inventing a
credential to clear it would be the worse failure by a wide margin.
"""
import re
from typing import Any, Optional

from loguru import logger

from backend.models.briefing import Briefing
from backend.pipeline.briefing_lint import _is_introduced, _sections_of
from backend.pipeline.briefing_passes import classify_people, write_introductions
from backend.pipeline.briefing_routing import MAX_PLAYER_CARDS, below_the_line
from backend.pipeline.text_similarity import content_tokens

# Fields that carry prose a name can appear in, by section.
_EDITABLE = (
    ("read", "lede"),
    ("read", "paragraphs"),
    ("record", "what"),
    ("record", "context"),
    ("files", "body"),
    ("disputes", None),
    ("anecdotes", "text"),
    ("anecdotes", "context"),
)


# Characters of context handed to the gloss writer on each side of the name.
_WINDOW = 400


def first_appearance(briefing: Briefing, name: str) -> Optional[str]:
    """Find the passage where the reader first meets a name.

    Returns a window AROUND the name, not the head of the section. Handing over
    the section's first 600 characters was the original bug: a name appearing
    three thousand characters in produced a passage that never mentioned them,
    and the model correctly declined to invent a credential — so six of ten
    names came back empty and stayed flagged.

    Args:
        briefing: The assembled Briefing.
        name: The name to locate.

    Returns:
        Text around the first appearance, or None when the name never appears.
    """
    for _section, text in _sections_of(briefing).items():
        position = (text or "").find(name)
        if position >= 0:
            return text[max(0, position - _WINDOW) : position + len(name) + _WINDOW]
    return None


# A name inside a comma-separated run of other names. Splicing an appositive
# there corrupts the list: the gloss's commas become list separators, so
# "Miller, James Humphrey, and Bell" reads as an extra person. Found live in
# the 2026-08-31 Packer briefing, where a five-man roster read as six.
_LIST_BEFORE = re.compile(r",\s*[A-Z][\w'\u2019-]+(?:\s+[A-Z][\w'\u2019-]+)*,\s*$")
# A capitalised sibling right after the name is signal enough; the list need
# not end there ("..., and Shannon Wilson Bell left camp").
_LIST_AFTER = re.compile(r"^\s*,\s*(?:and\s+)?[A-Z][\w'\u2019-]+")


def _in_name_list(text: str, position: int, name: str) -> bool:
    """Does this appearance sit inside a comma-separated run of names?

    Both sides must look like siblings before this fires: one capitalised
    neighbour on its own is ordinary prose ("Packer, Israel Swan said ...").

    Args:
        text: The passage.
        position: Where the name starts.
        name: The name itself.

    Returns:
        True when the name is one item of a list.
    """
    before = text[max(0, position - 120):position]
    after = text[position + len(name): position + len(name) + 120]
    return bool(_LIST_BEFORE.search(before) and _LIST_AFTER.match(after))


def _restates_sentence(text: str, position: int, introduction: str) -> bool:
    """Would this gloss just repeat the sentence it lands in?

    A gloss that restates the predicate reads as a stutter: "Robert McGrue,
    leader of the larger prospecting party, led the larger party." The lint
    cannot see it because the appositive is well-formed, so it is caught here.

    Args:
        text: The passage.
        position: Where the name starts.
        introduction: The proposed gloss.

    Returns:
        True when most of the gloss's content words are already in the sentence.
    """
    start = max(text.rfind(". ", 0, position) + 1, 0)
    end = text.find(". ", position)
    sentence = text[start: end if end != -1 else len(text)]
    gloss_words = content_tokens(introduction)
    if not gloss_words:
        return False
    shared = gloss_words & content_tokens(sentence)
    # Half the gloss already present, and more than one word of it. One shared
    # word is coincidence; two or more is the gloss repeating the sentence
    # ("leader of the larger prospecting party" beside "led the larger party").
    return len(shared) >= 2 and len(shared) / len(gloss_words) >= 0.5


def splice(text: str, name: str, introduction: str) -> tuple[str, bool]:
    """Insert a gloss after the first unintroduced appearance of a name.

    Only the first appearance in a passage is touched: a reader who has been
    told who someone is does not need telling again two sentences later, and
    the lint agrees — it reports one finding per name per section.

    Args:
        text: The passage.
        name: The name to introduce.
        introduction: The gloss, without the surrounding commas.

    Returns:
        Tuple of (text, whether anything changed).
    """
    if not text or not introduction:
        return text, False

    possessive = None
    for match in re.finditer(re.escape(name), text):
        if _is_introduced(text, match.start(), name):
            continue
        if _in_name_list(text, match.start(), name):
            continue
        if _restates_sentence(text, match.start(), introduction):
            continue
        # "Alan Lloyd's argument" cannot take an appositive after the name —
        # splicing there produces "Alan Lloyd, the scholar,'s argument". Hold
        # it aside and prefer a later plain occurrence.
        if text[match.end() : match.end() + 2] in ("'s", "\u2019s") or text[
            match.end() : match.end() + 1
        ] in ("'", "\u2019"):
            possessive = possessive if possessive is not None else match.start()
            continue
        end = match.end()
        tail = text[end:]
        # The target shape is "Name, gloss, rest" — the opening comma is what
        # makes it an appositive and is what the lint looks for. When the text
        # already has a comma after the name, that comma closes the gloss
        # instead of a second one being added.
        closing = "" if tail.lstrip().startswith(",") else ","
        return f"{text[:end]}, {introduction}{closing}{tail}", True

    if possessive is not None:
        # Every appearance is possessive, so lead with the gloss instead:
        # "the scholar who read Herodotus, Alan Lloyd's argument ...".
        return f"{text[:possessive]}{introduction}, {text[possessive:]}", True
    return text, False


def _repair_field(obj: Any, field: str, name: str, introduction: str) -> bool:
    """Splice into one model field in place. Returns whether it changed."""
    current = getattr(obj, field, None)
    if not isinstance(current, str) or name not in current:
        return False
    repaired, changed = splice(current, name, introduction)
    if changed:
        setattr(obj, field, repaired)
    return changed


def apply_introductions(briefing: Briefing, introductions: dict[str, str]) -> list[dict]:
    """Splice every gloss into the first place its name appears unintroduced.

    Args:
        briefing: The assembled Briefing, edited in place.
        introductions: Name to gloss.

    Returns:
        One record per applied pair, for the repair log.
    """
    applied: list[dict] = []

    for name, introduction in introductions.items():
        # Once per SECTION, not once per document: the lint reports a finding
        # for every section a name arrives in cold, because a reader jumping
        # straight to The Files never saw the introduction in The Record.
        if not _repair_field(briefing.read, "lede", name, introduction):
            for index, paragraph in enumerate(briefing.read.paragraphs):
                if _repair_field(paragraph, "text", name, introduction):
                    applied.append({"name": name, "where": f"read.paragraphs[{index}]"})
                    break
        else:
            applied.append({"name": name, "where": "read.lede"})

        for section, collection, fields in (
            ("record", briefing.record, ("what", "context")),
            ("files", briefing.files, ("body",)),
            ("anecdotes", briefing.anecdotes, ("text", "context")),
        ):
            for index, item in enumerate(collection):
                if any(_repair_field(item, field, name, introduction) for field in fields):
                    applied.append({"name": name, "where": f"{section}[{index}]"})
                    break

        for index, dispute in enumerate(briefing.disputes):
            if any(
                _repair_field(side, "text", name, introduction)
                for side in (dispute.case_for, dispute.case_against)
            ):
                applied.append({"name": name, "where": f"disputes[{index}]"})
                break

    return applied


def repair_inline_introductions(
    briefing: Briefing,
    client: Any,
    topic: str = "",
    maximum: int = MAX_PLAYER_CARDS,
) -> dict:
    """Run one repair round over the names the one-off rule covers.

    Args:
        briefing: The assembled Briefing, edited in place.
        client: A structured client.
        topic: The job topic, for context.
        maximum: The card cap; names ranked below it follow the one-off rule.

    Returns:
        A record of the round: who was classified as a person, what was
        written, what was applied, and what is still outstanding.
    """
    ranked = below_the_line(_sections_of(briefing), maximum=maximum)
    if not ranked:
        return {"ran": False, "reason": "no names below the cap"}

    people = classify_people(ranked, client, topic)
    not_people = [name for name in ranked if name not in people]
    if not_people:
        logger.info(
            f"Intro repair: {len(not_people)} of {len(ranked)} ranked names are not "
            f"people and are exempt from the one-off rule ({', '.join(not_people[:5])})"
        )

    needed: dict[str, str] = {}
    for name in ranked:
        if name not in people:
            continue
        passage = first_appearance(briefing, name)
        if passage:
            needed[name] = passage

    introductions = write_introductions(needed, client, topic)
    applied = apply_introductions(briefing, introductions)

    return {
        "ran": True,
        "people": sorted(people),
        "exempt": not_people,
        "needed": sorted(needed),
        "written": sorted(introductions),
        "applied": applied,
        "unresolved": sorted(set(needed) - set(introductions)),
    }
