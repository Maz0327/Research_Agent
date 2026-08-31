"""The cast build: whose name goes where, and what each card is written from."""

from unittest.mock import MagicMock

from backend.pipeline.briefing_cast import build_cast

BRIEF = (
    "Alfred Packer emerged at the agency in 1874. Packer was the only one who "
    "came out. Esther Packer buried her son in Littleton years later. "
    "The Denver Post ran the campaign. Lake City sits below the bluff."
)


def _client(cast, cards_by_name=None):
    """A client that returns a fixed cast and writes a card for whatever it is asked."""
    seen_material = {}
    client = MagicMock()

    def answer(prompt, schema, system, max_tokens=8000, model=None):
        keys = set(schema.get("properties", {}))
        if keys == {"cast"}:
            return ({"cast": cast}, {})
        # A card pass. Record the material each name was handed.
        body = prompt.split("NAMES AND THEIR MATERIAL", 1)[-1]
        asked, current = [], None
        for line in body.splitlines():
            if not line.strip():
                continue
            if line.startswith("  - "):
                seen_material.setdefault(current, []).append(line[4:])
            else:
                current = line.strip()
                asked.append(current)
                seen_material.setdefault(current, [])
        key = "places" if keys == {"places"} else "players"
        field = "line" if key == "places" else "role"
        return (
            {key: [{"name": n, field: "x", "body": "y"} for n in asked]},
            {},
        )

    client.generate_structured.side_effect = answer
    return client, seen_material


class TestMaterialMatching:
    def test_a_shared_surname_does_not_borrow_the_other_persons_facts(self):
        """Esther Packer must not be written from facts about Alfred Packer.

        Any-token matching filed twelve Alfred facts under Esther, and the
        card came back saying it had been given nothing about her.
        """
        cast = [
            {"name": "Alfred Packer", "kind": "person",
             "forms": ["Alfred Packer", "Packer"]},
            {"name": "Esther Packer", "kind": "person", "forms": ["Esther Packer"]},
        ]
        inventory = [
            {"text": "Alfred Packer confessed twice."},
            {"text": "Esther Packer outlived her son."},
        ]
        client, material = _client(cast)
        build_cast(client, BRIEF, inventory)
        assert material["Esther Packer"] == ["Esther Packer outlived her son."]
        assert "Esther Packer outlived her son." not in material["Alfred Packer"]

    def test_a_name_with_no_fact_is_written_from_the_briefing_itself(self):
        """The cast is read out of the brief, so the brief always has a line."""
        cast = [{"name": "Lake City", "kind": "place", "forms": ["Lake City"]}]
        client, material = _client(cast)
        build_cast(client, BRIEF, [{"text": "Nothing relevant here."}])
        assert material["Lake City"] == ["Lake City sits below the bluff."]

    def test_a_name_with_nothing_behind_it_is_dropped(self):
        """No material anywhere means no card, rather than a card that apologises."""
        cast = [
            {"name": "Alfred Packer", "kind": "person", "forms": ["Alfred Packer"]},
            {"name": "Ghost Name", "kind": "person", "forms": ["Ghost Name"]},
        ]
        client, _ = _client(cast)
        players, _orgs, _places = build_cast(client, BRIEF, [])
        assert [p.name for p in players] == ["Alfred Packer"]


class TestRanking:
    def test_the_most_mentioned_person_leads_the_section(self):
        """Code counts mentions across every form; the model does not rank."""
        cast = [
            {"name": "Esther Packer", "kind": "person", "forms": ["Esther Packer"]},
            {"name": "Alfred Packer", "kind": "person",
             "forms": ["Alfred Packer", "Packer"]},
        ]
        inventory = [
            {"text": "Alfred Packer confessed twice."},
            {"text": "Esther Packer outlived her son."},
        ]
        client, _ = _client(cast)
        players, _orgs, _places = build_cast(client, BRIEF, inventory)
        assert players[0].name == "Alfred Packer"


class TestKindsGoToTheirOwnSection:
    def test_people_organisations_and_places_are_kept_apart(self):
        cast = [
            {"name": "Alfred Packer", "kind": "person", "forms": ["Alfred Packer"]},
            {"name": "The Denver Post", "kind": "organisation",
             "forms": ["The Denver Post"]},
            {"name": "Lake City", "kind": "place", "forms": ["Lake City"]},
        ]
        client, _ = _client(cast)
        players, orgs, places = build_cast(client, BRIEF, [])
        assert [p.name for p in players] == ["Alfred Packer"]
        assert [o.name for o in orgs] == ["The Denver Post"]
        assert [p.name for p in places] == ["Lake City"]


class TestSpecificityWins:
    """A line goes to the name that matches it most specifically."""

    def test_a_bare_surname_does_not_claim_a_relatives_line(self):
        cast = [
            {"name": "Alfred Packer", "kind": "person",
             "forms": ["Alfred Packer", "Packer"]},
            {"name": "Esther Packer", "kind": "person", "forms": ["Esther Packer"]},
        ]
        inventory = [
            {"text": "Alfred Packer confessed twice."},
            {"text": "Esther Packer outlived her son."},
            {"text": "Packer walked out of the mountains alone."},
        ]
        client, material = _client(cast)
        build_cast(client, BRIEF, inventory)
        # Esther's line is hers alone; the unqualified "Packer" line is his,
        # because nothing else in the cast matches it more specifically.
        assert material["Esther Packer"] == ["Esther Packer outlived her son."]
        assert material["Alfred Packer"] == [
            "Alfred Packer confessed twice.",
            "Packer walked out of the mountains alone.",
        ]
