"""Packaging selection is real state, and the recorded transition exists.

The UI audit found packaging showing five titles and three thumbnail concepts
with nowhere to record which one Maz picked, and stage 12 with no way to say
"I recorded it" outside the CLI. These are the two contracts that close that.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"

CONCEPTS = {
    "titles": [{"title": "The Man Who Walked Out Alone", "why_it_fits": "the survivor is the story",
                "risk": "low"},
               {"title": "Five Went In. One Came Back.", "why_it_fits": "verified arithmetic",
                "risk": "low"}],
    "thumbnails": [{"concept": "One set of footprints leaving a snowbound pass",
                    "why_it_fits": "the whole story, no gore", "risk": "low"},
                   {"concept": "Split frame: portrait / excavation trench",
                    "why_it_fits": "the century-long argument", "risk": "low"}],
    "viewer_promise": "You will find out what the evidence can and cannot settle.",
    "mismatch_risk": "Do not promise a confession.",
}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


@pytest.fixture
def episode(workspace):
    """An episode with a chosen angle and packaging concepts on the table."""
    from backend.lwm import decisions, episode as ep, ledger, packaging
    d = Path(ep.create("Packaging choice", offline=True)["path"])
    for s in ("3 brief", "4 fact-check the brief", "4b briefing"):
        ledger.update_row(d, s, status="done", gate="—")
    (d / "outputs").mkdir(exist_ok=True)
    (d / "outputs" / "angle-options.json").write_text(json.dumps({
        "baseline": {"name": "b", "central_story": "s", "driving_question": "q",
                     "viewer_payoff": "p"},
        "alternatives": [], "previous_maz_idea": "", "chosen": None}))
    decisions.decide_angle(d, choice="baseline")
    c = MagicMock()
    c.generate_structured.return_value = (CONCEPTS, {})
    packaging.build(d, client=c)
    return d


class TestPackagingSelection:
    def test_concepts_alone_do_not_complete_the_stage(self, episode):
        """Nothing is chosen automatically, and STORY stays locked."""
        from backend.lwm import episode as ep, ledger, packaging
        assert packaging.selection(episode) is None
        row = ledger.read_rows(episode)["1b packaging"]
        assert row.status == "concepts ready" and not row.complete
        s = ep.status(episode.name)
        assert s["macro_state"] == "PACKAGING"
        assert s["maz_needed"] is True, "the pick is his, and the machine waits for it"

    def test_a_generated_title_and_thumbnail_persist(self, episode):
        from backend.lwm import decisions, packaging
        r = decisions.decide_packaging(
            episode, title=CONCEPTS["titles"][1]["title"],
            thumbnail=CONCEPTS["thumbnails"][0]["concept"])
        assert r["chosen"]["title"] == "Five Went In. One Came Back."
        assert r["chosen"]["title_source"] == "generated"
        assert r["chosen"]["thumbnail_source"] == "generated"
        assert r["chosen"]["promise"] == CONCEPTS["viewer_promise"]
        assert r["chosen"]["chosen_at"]
        # survives a fresh read from disk — it is state, not a return value
        again = packaging.selection(episode)
        assert again == r["chosen"]

    def test_a_custom_title_and_thumbnail_persist_with_their_source(self, episode):
        from backend.lwm import decisions, packaging
        decisions.decide_packaging(episode, title="My own title", title_source="custom",
                                   thumbnail="My own thumbnail idea", thumbnail_source="custom")
        sel = packaging.selection(episode)
        assert sel["title"] == "My own title" and sel["title_source"] == "custom"
        assert sel["thumbnail"] == "My own thumbnail idea" and sel["thumbnail_source"] == "custom"

    def test_a_mixed_selection_is_allowed(self, episode):
        from backend.lwm import decisions, packaging
        decisions.decide_packaging(episode, title=CONCEPTS["titles"][0]["title"],
                                   thumbnail="something of my own", thumbnail_source="custom")
        sel = packaging.selection(episode)
        assert sel["title_source"] == "generated" and sel["thumbnail_source"] == "custom"

    def test_both_are_required(self, episode):
        from backend.lwm import decisions
        with pytest.raises(ValueError):
            decisions.decide_packaging(episode, title="only a title", thumbnail="")
        with pytest.raises(ValueError):
            decisions.decide_packaging(episode, title="", thumbnail="only a thumbnail")

    def test_an_unknown_source_is_refused(self, episode):
        from backend.lwm import decisions
        with pytest.raises(ValueError):
            decisions.decide_packaging(episode, title="t", thumbnail="c", title_source="magic")

    def test_choosing_unlocks_story_and_only_then(self, episode):
        from backend.lwm import decisions, episode as ep, ledger
        assert ep.status(episode.name)["macro_state"] == "PACKAGING"
        decisions.decide_packaging(episode, title="t", thumbnail="c")
        ledger.update_row(episode, "2 feasibility + format", status="decided", gate="—")
        assert ledger.read_rows(episode)["1b packaging"].complete
        assert ep.status(episode.name)["macro_state"] == "STORY"

    def test_the_selection_reaches_the_api_payload(self, episode):
        from backend.lwm import decisions, episode as ep
        decisions.decide_packaging(episode, title="A picked title", thumbnail="a picked thumbnail")
        s = ep.status(episode.name)
        assert s["artifacts"]["packaging_json"]
        saved = json.loads(Path(s["artifacts"]["packaging_json"]).read_text())
        assert saved["chosen"]["title"] == "A picked title"

    def test_packaging_never_touches_the_chosen_angle(self, episode):
        from backend.lwm import decisions
        before = json.loads((episode / "outputs" / "angle-options.json").read_text())["chosen"]
        decisions.decide_packaging(episode, title="t", thumbnail="c")
        after = json.loads((episode / "outputs" / "angle-options.json").read_text())["chosen"]
        assert after == before

    def test_the_choice_is_recorded_in_the_decision_log(self, episode):
        from backend.lwm import decisions
        decisions.decide_packaging(episode, title="Logged title", thumbnail="Logged thumbnail",
                                   title_source="custom")
        log = (episode / "DECISION-LOG.md").read_text()
        assert "PACKAGING CHOSEN" in log and "Logged title" in log and "custom" in log


class TestPromiseReachesDownstream:
    def test_one_authoritative_promise(self, episode):
        from backend.lwm import decisions, packaging
        assert packaging.promise(episode) == CONCEPTS["viewer_promise"]
        decisions.decide_packaging(episode, title="t", thumbnail="c")
        assert packaging.promise(episode) == CONCEPTS["viewer_promise"]

    def test_story_architecture_receives_the_chosen_packaging(self, episode):
        from backend.lwm import architecture, decisions
        decisions.decide_packaging(episode, title="The title he picked", thumbnail="c")
        seen = {}
        c = MagicMock()

        def answer(prompt, schema, system, max_tokens):
            seen["prompt"] = prompt
            return {"macro_shape": "investigation", "why_this_shape": "w",
                    "audience_belief_entering": "a", "what_changes_that_belief": "b",
                    "movements": [{"n": 1, "story_job": "j", "what_changes": "c"}],
                    "ending": "e"}, {}
        c.generate_structured.side_effect = answer
        arch = architecture.build(episode, client=c)
        assert CONCEPTS["viewer_promise"] in seen["prompt"]
        assert "The title he picked" in seen["prompt"], "the structure must earn the title"
        assert arch["packaging_promise"] == CONCEPTS["viewer_promise"]
        assert arch["packaging_title"] == "The title he picked"

    def test_the_draft_packet_carries_the_same_promise_and_title(self, episode):
        from backend.lwm import decisions, outline, packet
        decisions.decide_packaging(episode, title="The title he picked", thumbnail="c")
        rows = "\n".join(
            f"| {i} | sourced claim {i} | REALITY | CONFIRMED | SRC_1 | n | say it | not that | — |"
            for i in range(1, 7))
        (episode / "04-sources-registry.md").write_text(
            "| # | claim | class | status | source | LB | allowed wording | prohibited wording | anchor |\n"
            "|---|---|---|---|---|---|---|---|---|\n" + rows + "\n")
        # the shape architecture.build() actually writes — the outline reads all of it
        (episode / "outputs" / "story-architecture.json").write_text(json.dumps({
            "macro_shape": "investigation", "why_this_shape": "w",
            "audience_belief_entering": "a", "what_changes_that_belief": "b",
            "information_order_rationale": "r",
            "movements": [{"n": 1, "story_job": "j", "what_changes": "c"}],
            "legitimate_withholding": "", "human_stakes": "", "ending": "e",
            "unresolved_uncertainty": "", "compressed_vs_full_scene": ""}))
        c = MagicMock()
        c.generate_structured.return_value = ({"movements": [{
            "n": 1, "story_job": "the walk out", "events": ["e"],
            "registry_claim_ids": [1, 2, 3, 4, 5], "coverage": "SOLID"}]}, {})
        outline.build(episode, client=c)
        pk = packet.build(episode, 1)
        assert pk["packaging_promise"] == CONCEPTS["viewer_promise"]
        assert pk["packaging_title"] == "The title he picked"
        prompt = packet.render_prompt(pk, rules="RULES")
        assert CONCEPTS["viewer_promise"] in prompt
        assert "it goes out titled: The title he picked" in prompt


class TestRecordedTransition:
    @pytest.fixture
    def ready_to_record(self, episode):
        from backend.lwm import decisions, ledger
        decisions.decide_packaging(episode, title="t", thumbnail="c")
        for s in ("2 feasibility + format", "4c story architecture", "5 outline", "6 grip gate A",
                  "7 draft", "8 edit", "9 grip gate B", "9b pace edit"):
            ledger.update_row(episode, s, status="done", gate="—")
        (episode / "10-final-candidate.md").write_text("The final telling.")
        decisions.decide_d(episode, approve=True)
        ledger.update_row(episode, "10b script fact-check (D-SFC-1)", status="done", gate="—")
        ledger.update_row(episode, "11 production package", status="done", gate="—")
        return episode

    def test_the_control_is_offered_only_at_the_recording_stage(self, ready_to_record, episode):
        from backend.lwm import episode as ep
        s = ep.status(episode.name)
        assert s["detailed_stage"] == "12 record + booth diff"
        assert s["maz_needed"] is True

    def test_marking_recorded_moves_the_episode_on(self, ready_to_record, episode):
        from backend.lwm import decisions, episode as ep, ledger
        r = decisions.decide_recorded(episode)
        assert r["recorded"] is True
        row = ledger.read_rows(episode)["12 record + booth diff"]
        assert row.complete and row.status == "recorded"
        s = ep.status(episode.name)
        assert s["macro_state"] == "PUBLISHED"          # stage 13 is the publish step
        assert s["detailed_stage"] == "13 assemble + final review"

    def test_it_survives_a_fresh_read(self, ready_to_record, episode):
        from backend.lwm import decisions, ledger
        decisions.decide_recorded(episode, notes="recorded in one take")
        assert ledger.read_rows(episode)["12 record + booth diff"].notes == "recorded in one take"

    def test_the_booth_diff_hook_is_preserved_not_consumed(self, ready_to_record, episode):
        from backend.lwm import decisions, ledger
        decisions.decide_recorded(episode)
        assert "booth diff" in ledger.read_rows(episode)["12 record + booth diff"].gate

    def test_recording_twice_is_refused(self, ready_to_record, episode):
        from backend.lwm import decisions
        decisions.decide_recorded(episode)
        with pytest.raises(RuntimeError):
            decisions.decide_recorded(episode)

    def test_nothing_can_be_marked_recorded_without_a_locked_script(self, episode):
        from backend.lwm import decisions
        with pytest.raises(RuntimeError):
            decisions.decide_recorded(episode)
