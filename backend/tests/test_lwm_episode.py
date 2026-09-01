"""Episode lifecycle, pointer, status projection — 1E/1K contracts."""

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


class TestNewEpisode:
    def test_topic_only(self, workspace):
        from backend.lwm import episode as ep
        r = ep.create("Research the Vela Incident", offline=True)
        assert r["slug"] == "01-research-the-vela-incident"
        assert (Path(r["path"]) / "STAGE-LEDGER.md").exists()

    def test_sources_only_episode_is_possible(self, workspace):
        from backend.lwm import episode as ep
        r = ep.create("", sources=["https://youtu.be/TlAXZVdAhIo"], offline=True)
        assert r["sources"][0]["type"] == "youtube"
        s = ep.status(r["slug"])
        assert s["macro_state"] == "TOPIC"  # angle work is Maz's; the system just made it possible

    def test_nothing_at_all_is_rejected(self, workspace):
        from backend.lwm import episode as ep
        with pytest.raises(ValueError):
            ep.create("")

    def test_numbering_increments_and_reserved_range_ignored(self, workspace):
        from backend.lwm import episode as ep
        (workspace / "pipeline/episodes/12-packer").mkdir()
        (workspace / "pipeline/episodes/99-hawara-grip-test").mkdir()
        r = ep.create("Next one", offline=True)
        assert r["slug"].startswith("13-")

    def test_collision_is_refused_never_overwritten(self, workspace, monkeypatch):
        """Numbering steps past existing dirs, so the only collision is a race
        (or a hand-made dir landing between scan and copy). Simulate it."""
        from backend.lwm import episode as ep
        ep.create("Same Title", offline=True)
        monkeypatch.setattr(ep, "next_number", lambda: 1)  # the taken number
        with pytest.raises(FileExistsError):
            ep.create("Same Title", offline=True)

    def test_pointer_is_set_and_resolution_never_guesses(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import paths
        ep.create("First", offline=True)
        r2 = ep.create("Second", offline=True)
        assert paths.read_active_episode() == r2["slug"]
        # Old dead pointer cannot redirect: only ACTIVE-EPISODE.txt is read.
        (workspace / "pipeline" / "ACTIVE-EPISODE.txt").write_text("# cleared\n")
        with pytest.raises(FileNotFoundError):
            ep.resolve(None)


class TestStatus:
    def test_status_contract_fields(self, workspace):
        from backend.lwm import episode as ep
        ep.create("The Vela Incident", sources=["https://youtu.be/TlAXZVdAhIo"], offline=True)
        s = ep.status()
        for key in ("episode", "topic", "macro_state", "detailed_stage", "next_action",
                    "maz_needed", "sources", "artifacts", "blockers", "active"):
            assert key in s
        assert s["macro_state"] == "TOPIC"
        assert s["maz_needed"] is True  # touchpoint A
        assert s["sources"][0]["type"] == "youtube"

    def test_macro_state_tracks_ledger(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger
        r = ep.create("Vela", offline=True)
        d = Path(r["path"])
        for stage in ("1 angle + packaging", "2 feasibility + format"):
            ledger.update_row(d, stage, status="decided", gate="KILL gate: pass")
        assert ep.status()["macro_state"] == "RESEARCH"

    def test_stage_14_never_regresses_published(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger
        r = ep.create("Done one", offline=True)
        d = Path(r["path"])
        for stage, _ in ledger.STAGES:
            ledger.update_row(d, stage, status="done", gate="—")
        assert ep.status()["macro_state"] == "PUBLISHED"


class TestContinueStops:
    def test_continue_stops_at_touchpoint_a_not_at_internal_work(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import orchestrate
        ep.create("Vela", offline=True)
        log = orchestrate.step()
        stop = log[-1]["stop"]
        assert stop["reason"] == "touchpoint" and stop["maz_needed"]
        assert "A —" in stop["detail"]

    def test_continue_stops_at_touchpoint_b_after_briefing_ready(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger, orchestrate
        r = ep.create("Vela", offline=True)
        d = Path(r["path"])
        for stage in ("1 angle + packaging", "2 feasibility + format"):
            ledger.update_row(d, stage, status="decided", gate="KILL gate: pass")
        for stage in ("3 brief", "4 fact-check the brief"):
            ledger.update_row(d, stage, status="done")
        log = orchestrate.step()
        assert log[-1]["stop"]["detail"].startswith("Maz touchpoint B")
