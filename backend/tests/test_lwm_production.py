"""Stage 11 package + writing orchestration stops (1N/1L contracts)."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"

SCRIPT = """## Movement 1

Alferd Packer emerged alone at the Los Pinos Agency on April 16, 1874, after 65 days in the
mountains. Six had gone in. One walked out, asking first not for food but for whiskey.

## Movement 2

In 1886 Packer was resentenced to 40 years. The spectrograph work on the bullet lead under
Shannon Bell's remains came almost a century later — and it supported Packer's claim of
self-defense.
"""

REGISTRY = """| # | claim | class | status | source | LB | allowed wording | prohibited wording | anchor |
|---|---|---|---|---|---|---|---|---|
| 1 | Packer emerged alone at the Los Pinos Agency on April 16, 1874, after 65 days | REALITY | CONFIRMED | SRC_1 · SRC_3 | y | sixty-five days | any other count | 65 days ≈ two months alone |
| 2 | Spectrograph matching tied bullet lead under Bell's remains to Packer's pistol | THEORY | REPORTED | SRC_3 · SRC_8 | y | the analysis suggested | proved innocent | — |
| 3 | Packer was resentenced in 1886 to 40 years | REALITY | CONFIRMED | SRC_2 | n | — | — | — |
"""


@pytest.fixture
def episode(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    from backend.lwm import episode as ep
    d = Path(ep.create("Packer", sources=["https://youtu.be/TlAXZVdAhIo"], offline=True)["path"])
    head = (FIXTURES / "workspace/pipeline/episodes/_TEMPLATE/04-sources-registry.md").read_text().split("|")[0]
    (d / "04-sources-registry.md").write_text(head + REGISTRY)
    (d / "07-draft.md").write_text(SCRIPT)
    return d


class TestProductionPackage:
    def test_package_from_v4_layout(self, episode):
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        assert (episode / "11-production-package.md").exists()
        assert (episode / "editing" / "production-package.json").exists()
        assert len(pkg["beats"]) == 2
        assert len(pkg["load_bearing"]) == 2

    def test_claims_and_sources_survive_into_cue_cards(self, episode):
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        m1 = pkg["beats"][0]["cue_card"]["load_bearing"]
        assert any("SRC_1" in c["source"] for c in m1)
        assert any("65 days" in (c["anchor"] or "") for c in m1)

    def test_missing_assets_become_search_tasks_not_a_crash(self, episode):
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        assert pkg["assets"]["missing"], "unfound visuals are named sourcing tasks"
        md = (episode / "11-production-package.md").read_text()
        assert "⬜ find:" in md

    def test_beats_carry_real_face_ai_gap_under_real_first(self, episode):
        """§18: every beat is classified, and REAL-FIRST is the default."""
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        for beat in pkg["beats"]:
            assert beat["visual"]["class"] in production.VISUAL_CLASSES
            assert beat["visual"]["licence_note"]
            assert beat["visual"]["real_first"] == (beat["visual"]["class"] != "AI-GAP")
        assert sum(pkg["visual_summary"].values()) == len(pkg["beats"])
        # Nothing is generated here — the package writes the shopping list.
        assert "NONE" in pkg["generation"]

    def test_a_beat_no_camera_could_have_seen_is_the_ai_gap_case(self, episode):
        from backend.lwm import production
        (episode / "07-draft.md").write_text(
            "## Movement 1\n\nIn 1874 he must have felt the cold close in, and imagined "
            "what waited past the ridge.\n")
        pkg = production.build(episode, episode / "07-draft.md")
        assert pkg["beats"][0]["visual"]["class"] == "AI-GAP"

    def test_user_supplied_video_appears_as_candidate_asset(self, episode):
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        assert any(a["type"] == "youtube" for a in pkg["assets"]["available"])
        assert pkg["beats"][0]["matched_assets"]

    def test_script_version_is_pinned(self, episode):
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        assert len(pkg["script"]["sha"]) == 12


class TestWritingStops:
    def test_after_touchpoint_b_continue_runs_to_the_ear(self, episode, monkeypatch):
        """B done → outline → gate A (internal) → M1 draft → STOP at C."""
        import json

        from backend.lwm import ledger, orchestrate
        for stage in ("1 angle", "1b packaging", "2 feasibility + format", "3 brief",
                      "4 fact-check the brief", "4b briefing"):
            ledger.update_row(episode, stage, status="done", gate="—")
        ledger.update_row(episode, "4c story architecture", status="structure decided",
                          notes="structure session held; decisions in DECISION-LOG")
        (episode / "outputs").mkdir(exist_ok=True)
        (episode / "outputs" / "angle-options.json").write_text(json.dumps(
            {"chosen": {"kind": "baseline", "name": "b", "central_story": "s",
                        "driving_question": "q", "viewer_payoff": "p"}}))
        (episode / "07-draft.md").unlink()  # fresh draft path
        # A movement needs real material behind it or the outline holds it back
        # (§7). Three registry rows is thin research, and the machine says so —
        # so this test, whose subject is the STOPS, gives it enough to proceed.
        (episode / "04-sources-registry.md").write_text(
            (episode / "04-sources-registry.md").read_text()
            + "\n".join(f"| {n} | another sourced claim {n} | REALITY | CONFIRMED | SRC_1 | n | "
                        f"state plainly | overstate | — |" for n in range(4, 9)) + "\n")

        def structured(prompt, schema, system, max_tokens):
            props = set(schema.get("properties", {}))
            if "macro_shape" in props:
                return {"macro_shape": "investigation", "why_this_shape": "w",
                        "audience_belief_entering": "a", "what_changes_that_belief": "b",
                        "movements": [{"n": 1, "story_job": "j", "what_changes": "c"}],
                        "ending": "e"}, {}
            if "movements" in props:
                return {"movements": [{
                    "n": 1, "story_job": "the walk out",
                    "events": ["he walked out"], "registry_claim_ids": [1, 2, 3, 4, 5, 6],
                    "coverage": "SOLID"}]}, {}
            if "findings" in props:
                return {"findings": []}, {}
            return {"text": "He walked out of the mountains alone, and asked for whiskey."}, {}

        text_client = MagicMock()
        text_client.generate_structured.side_effect = structured
        reader = MagicMock()
        reader.generate_structured.return_value = ({"gripped": True, "note": "held",
                                                    "answers": []}, {})

        log = orchestrate.step(writer_client=text_client, reader_clients=[reader] * 3,
                               architecture_client=text_client, judge_client=text_client)
        stops = [e["stop"] for e in log if "stop" in e]
        assert stops and stops[-1]["detail"].startswith("C —")
        rows = ledger.read_rows(episode)
        assert rows["5 outline"].complete
        assert rows["6 grip gate A"].complete  # internal, logged, no Maz
        assert "M1 drafted" in rows["7 draft"].status

    def test_gate_failure_is_advisory_not_maz_homework(self, episode):
        from backend.lwm import writing
        (episode / "05-outline.md").write_text("an outline")
        reader = MagicMock()
        reader.generate_structured.return_value = (
            {"gripped": False, "drop_off_point": "beat 2", "note": "lost me"}, {})
        r = writing.grip_gate(episode, "05-outline.md", "6 grip gate A", clients=[reader] * 3)
        assert r["pass"] is False
        from backend.lwm import ledger
        assert "internal" in ledger.read_rows(episode)["6 grip gate A"].notes
