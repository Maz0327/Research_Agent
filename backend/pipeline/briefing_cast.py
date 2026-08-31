"""Build the briefing's cast: who is a person, an organisation, or a place.

The cast is read out of the *finished* briefing, because that is the document
a reader looks a name up in. What this replaces was a capitalisation
heuristic that required a space in a name, so on the Packer briefing it never
saw the 601 mentions of "Packer" and left the subject of the document out of
his own cast list, while filling "The Players" with agencies and rivers.

The split of labour is the same as everywhere else in the pipeline: a model
reads and writes, code decides. The model says who is in the document and
what kind of thing each one is; code checks every name against the text,
counts the mentions, ranks them, and drops anything it cannot support.
"""

import re
from typing import Any

from loguru import logger

from backend.models.briefing import Place, Player
from backend.pipeline.briefing_passes import (
    run_cast_pass,
    run_places_pass,
    run_players_pass,
)
from backend.pipeline.text_similarity import content_tokens

# How much text a single card is written from.
MATERIAL_PER_NAME = 12


def build_cast(
    client: Any,
    brief_text: str,
    inventory: list[dict],
    job_id: str = "",
) -> tuple[list[Player], list[Player], list[Place]]:
    """Read the cast out of a finished briefing and write its three sections.

    Args:
        client: A structured-output client.
        brief_text: The briefing's prose, all sections joined.
        inventory: Harvested facts, each with a `text` key.
        job_id: For logging only.

    Returns:
        `(players, organisations, places)` — people, then organisations, then
        the places that earned a card. Each list is ordered by how often the
        briefing mentions the name.
    """
    tag = f"[{job_id}] " if job_id else ""
    cast = run_cast_pass(client, brief_text)
    sentences = re.split(r"(?<=[.!?])\s+", brief_text)

    forms_by_name = {
        entry["name"]: [tokens for tokens in map(content_tokens, entry["forms"]) if tokens]
        for entry in cast
    }
    mentions_by_name = {
        entry["name"]: sum(brief_text.count(form) for form in entry["forms"])
        for entry in cast
    }

    def best_match(name: str, tokens: set) -> set | None:
        """The most specific form of `name` the text contains, if any.

        Specificity is what keeps two people with one surname apart: "Alfred
        Packer" is a better match than the bare "Packer", and the longer form
        is the one that decides who a line belongs to.
        """
        matched = [form for form in forms_by_name[name] if form <= tokens]
        return max(matched, key=len) if matched else None

    def material_for(name: str, texts: list[str]) -> list[str]:
        """Lines about this name, and not about someone who shares a word with it.

        A form matches only when every word of it is present. Matching on any
        word instead filed twelve facts about Alfred Packer under his mother
        Esther, and the card that came back said, correctly, that it had been
        given nothing about her.

        The reverse case needs the second rule: Alfred is also called just
        "Packer", so a line about Esther Packer matches him too. It is withheld
        when another name in the cast matches the same line by a longer form
        containing his — the line is about her, and she is the one who gets it.

        And a tie needs the third: Alferd and his father James are BOTH called
        just "Packer", so on a line matching only that surname neither outranks
        the other, and letting both keep it wrote the father a card out of his
        son's biography — an invented confessed cannibal, on the page. A line
        matched only by a form that several cast members share goes to the one
        the briefing mentions most; the rest get nothing from it.
        """
        kept = []
        for text in texts:
            tokens = content_tokens(text)
            mine = best_match(name, tokens)
            if mine is None:
                continue
            rivals = {
                other: theirs
                for other in forms_by_name
                if other != name
                and (theirs := best_match(other, tokens)) is not None
            }
            outranked = any(mine < theirs for theirs in rivals.values())
            loses_tie = any(
                theirs == mine and mentions_by_name[other] > mentions_by_name[name]
                for other, theirs in rivals.items()
            )
            if not outranked and not loses_tie:
                kept.append(text)
            if len(kept) == MATERIAL_PER_NAME:
                break
        return kept

    fact_texts = [fact["text"] for fact in inventory]
    material = {}
    for entry in cast:
        # Harvested facts are the first source; the briefing's own sentences
        # are the fallback, because the cast is read out of that document and
        # a name is in it by definition.
        found = material_for(entry["name"], fact_texts)
        material[entry["name"]] = found or material_for(entry["name"], sentences)

    # A name with nothing behind it produces a card that says so. Code drops it
    # rather than shipping the apology as an entry the owner has to read past.
    unsupported = sorted(name for name, text in material.items() if not text)
    if unsupported:
        logger.info(
            f"{tag}cast: dropped {len(unsupported)} name(s) with no material "
            f"behind them: {unsupported}"
        )
        cast = [entry for entry in cast if material[entry["name"]]]

    def named(kind: str) -> list[str]:
        """Cast of one kind, most-mentioned first — code counts, not the model."""
        rows = [entry for entry in cast if entry["kind"] == kind]
        rows.sort(
            key=lambda entry: (
                -sum(brief_text.count(form) for form in entry["forms"]),
                entry["name"],
            )
        )
        return [entry["name"] for entry in rows]

    people, orgs, place_names = named("person"), named("organisation"), named("place")
    logger.info(
        f"{tag}Briefing pass 6: {len(people)} people, {len(orgs)} organisations, "
        f"{len(place_names)} places"
    )

    players = run_players_pass(client, people, material)
    organisations = run_players_pass(client, orgs, material)
    places = run_places_pass(client, place_names, material)

    # A card batch that fails is skipped rather than raised, so say plainly how
    # many of the names asked for came back with a card. Places are expected to
    # fall short — that pass declines a backdrop by design.
    for label, asked, written in (
        ("people", people, players),
        ("organisations", orgs, organisations),
    ):
        if len(written) < len(asked):
            missing = sorted(set(asked) - {card.name for card in written})
            logger.warning(
                f"{tag}{label}: {len(written)} of {len(asked)} cards written; "
                f"no card for {missing}"
            )

    return players, organisations, places
