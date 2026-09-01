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
        # D-V1-6: research precedes the angle, so a fresh episode's next state
        # is RESEARCH — the story is not guessed before the evidence exists.
        assert s["macro_state"] == "RESEARCH"

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
        assert s["macro_state"] == "RESEARCH"
        assert s["maz_needed"] is False  # research is the system's move, not Maz's
        assert s["sources"][0]["type"] == "youtube"

    def test_research_source_count_is_separate_from_intake(self, workspace):
        """A creator who supplied nothing must not be told the research found nothing."""
        import json
        from backend.lwm import episode as ep
        r = ep.create("Packer", offline=True)
        d = Path(r["path"])
        assert ep.status()["sources"] == []
        assert ep.status()["research_sources"] is None      # no job yet
        (d / "research").mkdir(exist_ok=True)
        (d / "research" / "ra-job.json").write_text(json.dumps(
            {"jobs": [{"job_id": "JOB-A", "status": "completed", "sources": 11}],
             "current": "JOB-A"}))
        s = ep.status()
        assert s["sources"] == [], "intake is still empty — he supplied none"
        assert s["research_sources"] == 11, "…but the research found eleven"

    def test_macro_state_tracks_ledger(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger
        r = ep.create("Vela", offline=True)
        d = Path(r["path"])
        # The pre-patch keys still resolve through ledger.ALIASES.
        for stage in ("1 angle + packaging", "2 feasibility + format"):
            ledger.update_row(d, stage, status="decided", gate="KILL gate: pass")
        for stage in ("3 brief", "4 fact-check the brief", "4b briefing"):
            ledger.update_row(d, stage, status="done")
        assert ep.status()["macro_state"] == "PACKAGING"

    def test_stage_14_never_regresses_published(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger
        r = ep.create("Done one", offline=True)
        d = Path(r["path"])
        for stage, _ in ledger.STAGES:
            ledger.update_row(d, stage, status="done", gate="—")
        assert ep.status()["macro_state"] == "PUBLISHED"


class TestContinueStops:
    def test_continue_runs_research_first_not_an_angle_decision(self, workspace):
        """D-V1-6: a fresh episode's first internal work is research.

        The old flow stopped here for touchpoint A and made Maz guess a story
        before any evidence existed. Now `continue` goes to research, and the
        creative decision waits until the Brief is in.
        """
        from backend.lwm import episode as ep
        from backend.lwm import orchestrate
        ep.create("Vela", offline=True)
        log = orchestrate.step()
        stop = log[-1]["stop"]
        assert log[-1]["stage"] == "3 brief"
        assert stop["reason"] == "failure"  # no network in tests; the point is WHICH stage ran

    def test_continue_stops_at_the_angle_touchpoint_once_options_exist(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger, orchestrate
        r = ep.create("Vela", offline=True)
        d = Path(r["path"])
        for stage in ("3 brief", "4 fact-check the brief", "4b briefing"):
            ledger.update_row(d, stage, status="done")
        ledger.update_row(d, "1 angle", status="options ready",
                          notes="baseline + 3 alternative(s)")
        log = orchestrate.step()
        stop = log[-1]["stop"]
        assert stop["reason"] == "touchpoint" and stop["maz_needed"]
        assert "ANGLE" in stop["detail"]

    def test_continue_stops_at_the_story_touchpoint_after_the_angle(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import ledger, orchestrate
        r = ep.create("Vela", offline=True)
        d = Path(r["path"])
        for stage in ("3 brief", "4 fact-check the brief", "4b briefing"):
            ledger.update_row(d, stage, status="done")
        ledger.update_row(d, "1 angle", status="chosen", notes="baseline")
        for stage in ("1b packaging", "2 feasibility + format"):
            ledger.update_row(d, stage, status="done")
        log = orchestrate.step()
        assert "STORY" in log[-1]["stop"]["detail"]


class TestList:
    def test_list_enumerates_with_active_first_and_derived_state(self, workspace):
        from backend.lwm import episode as ep
        ep.create("First video", offline=True)
        ep.create("Second video", offline=True)
        rows = ep.list_all()
        assert [r["episode"] for r in rows][0] == "02-second-video"  # active first
        assert rows[0]["active"] is True and rows[1]["active"] is False
        assert all(r["macro_state"] == "RESEARCH" for r in rows)

    def test_list_survives_a_broken_episode(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import paths
        ep.create("Good one", offline=True)
        bad = paths.episodes_dir() / "07-broken"
        bad.mkdir()
        rows = ep.list_all()
        broken = next(r for r in rows if r["episode"] == "07-broken")
        assert broken["macro_state"] == "UNKNOWN"
