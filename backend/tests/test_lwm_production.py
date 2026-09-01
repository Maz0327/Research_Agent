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

    def test_missing_assets_become_todo_not_a_crash(self, episode):
        from backend.lwm import production
        pkg = production.build(episode, episode / "07-draft.md")
        assert any("TODO" in m for m in pkg["assets"]["missing"])
        md = (episode / "11-production-package.md").read_text()
        assert "⬜ TODO" in md

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
        from backend.lwm import ledger, orchestrate
        for stage in ("1 angle + packaging", "2 feasibility + format", "3 brief",
                      "4 fact-check the brief"):
            ledger.update_row(episode, stage, status="done", gate="—")
        ledger.update_row(episode, "4b briefing + structure session", status="done",
                          notes="structure session held; decisions in DECISION-LOG")
        (episode / "07-draft.md").unlink()  # fresh draft path

        text_client = MagicMock()
        text_client.generate_structured.return_value = ({"text": "## outline\n- beat"}, {})
        reader = MagicMock()
        reader.generate_structured.return_value = ({"gripped": True, "note": "held"}, {})

        log = orchestrate.step(writer_client=text_client, reader_clients=[reader] * 3)
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
