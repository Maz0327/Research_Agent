"""Phase 1 correction-pass regressions: the defects ChatGPT found stay dead."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    (ws / "pipeline" / "lint").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


@pytest.fixture
def episode(workspace):
    from backend.lwm import episode as ep
    from backend.lwm import ledger
    r = ep.create("Correction pass", offline=True)
    d = Path(r["path"])
    for s in ("1 angle + packaging", "2 feasibility + format"):
        ledger.update_row(d, s, status="decided", gate="KILL gate: pass")
    return d


class TestDefect1ResearchAdvancesLedger:
    def test_successful_research_marks_stage_3_and_never_reruns(self, episode, monkeypatch):
        from backend.lwm import ledger, orchestrate, research
        calls = []
        def fake_round(ep_dir, topic):
            calls.append(topic)
            (ep_dir / "research").mkdir(exist_ok=True)
            (ep_dir / "research" / "ra-job.json").write_text(
                json.dumps({"jobs": [], "current": "job-xyz"}))
            return {"job_id": "job-xyz", "status": "completed",
                    "claims_count": 12, "sources_count": 3}
        monkeypatch.setattr(research, "run_round", fake_round)
        monkeypatch.setattr(research, "run_gap_rounds", lambda *a, **k: [])
        monkeypatch.setattr(orchestrate.research, "run_round", fake_round)
        monkeypatch.setattr(orchestrate.research, "run_gap_rounds", lambda *a, **k: [])

        orchestrate.step(max_steps=1)
        assert calls == ["Correction pass"]
        row = ledger.read_rows(episode)["3 brief"]
        assert row.complete and "job-xyz" in row.notes

        orchestrate.step(max_steps=1)  # a second continue moves ON, no rerun
        assert calls == ["Correction pass"], "research must not rerun after success"

    def test_failed_research_leaves_stage_3_incomplete(self, episode, monkeypatch):
        from backend.lwm import ledger, orchestrate
        monkeypatch.setattr(orchestrate.research, "run_round",
                            lambda *a, **k: {"job_id": "j", "status": "failed"})
        log = orchestrate.step(max_steps=1)
        assert log[-1]["stop"]["reason"] == "failure"
        assert not ledger.read_rows(episode)["3 brief"].complete


class TestDefect2GatesNeverLoop:
    def _reader(self, gripped):
        c = MagicMock()
        c.generate_structured.return_value = (
            {"gripped": gripped, "drop_off_point": "beat 2" if not gripped else "",
             "held_best": "the whiskey line", "note": "n"}, {})
        return c

    def test_pass_completes_the_stage(self, episode):
        from backend.lwm import ledger, writing
        (episode / "05-outline.md").write_text("outline")
        writing.grip_gate(episode, "05-outline.md", "6 grip gate A",
                          clients=[self._reader(True)] * 3)
        assert ledger.read_rows(episode)["6 grip gate A"].complete

    def test_advisory_fail_ALSO_completes_and_does_not_loop_or_summon_maz(self, episode):
        from backend.lwm import ledger, writing
        (episode / "05-outline.md").write_text("outline")
        writing.grip_gate(episode, "05-outline.md", "6 grip gate A",
                          clients=[self._reader(False)] * 3)
        row = ledger.read_rows(episode)["6 grip gate A"]
        assert row.complete, "an executed advisory gate is a completed stage"
        assert "FAIL" in row.gate  # the result stays visible
        assert "not Maz" in row.notes

    def test_gate_b_writes_the_real_grip_map(self, episode):
        from backend.lwm import writing
        (episode / "07-draft.md").write_text("a script")
        writing.grip_gate(episode, "07-draft.md", "9 grip gate B",
                          clients=[self._reader(True)] * 3)
        grip = (episode / "09-grip-gate-b.md").read_text()
        assert "held: “the whiskey line”" in grip


class TestDefect5Routing:
    def test_current_authority_defaults(self, monkeypatch):
        """D-23 survives only where nothing later superseded it (routing audit 09-01)."""
        from backend.lwm.routing import seat_model
        monkeypatch.delenv("LWM_MODEL_JUDGE", raising=False)
        assert seat_model("writer") == "deepseek-v4-pro"       # D-23, unsuperseded
        assert seat_model("editor") == "claude-sonnet-5"        # D-23, UNRESOLVED (dead provider)
        assert seat_model("judge") == "gpt-5.6-terra"           # D-028 supersedes D-23's kimi
        assert seat_model("reader") == "gpt-5.6-terra"          # no locked family → D-028 judge

    def test_kimi_is_never_the_default_judge(self, monkeypatch):
        """D-028: kappa 0.900 (terra) vs 0.550 (kimi); kimi-k2.5 sunset 08-31."""
        from backend.lwm.routing import seat_model
        monkeypatch.delenv("LWM_MODEL_JUDGE", raising=False)
        assert "kimi" not in seat_model("judge")

    def test_env_override_is_deliberate(self, monkeypatch):
        from backend.lwm.routing import seat_model
        monkeypatch.setenv("LWM_MODEL_WRITER", "gpt-5.6-luna")
        assert seat_model("writer") == "gpt-5.6-luna"

    def test_unreachable_seat_fails_loudly_never_substitutes(self, monkeypatch):
        from backend.lwm.routing import seat_client
        # The editor's locked provider (Anthropic) is dead on this machine and
        # its client requires a key we deliberately remove for the test.
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("LWM_MODEL_EDITOR", "kimi-k3-test")  # moonshot: no key
        monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="Silently switching"):
            seat_client("editor")


class TestDefect7Materiality:
    def _run(self, tmp_path, verdict_answers, lb):
        from backend.lwm import factcheck
        script = tmp_path / "s.md"
        script.write_text("The revolver was found in the 1950s on Cannibal Plateau.")
        client = MagicMock()
        client.generate_structured.side_effect = [
            ({"claims": [{"claim": "The revolver was found in the 1950s on Cannibal Plateau",
                          "script_line": "The revolver was found in the 1950s on Cannibal Plateau."}]}, {}),
            *[(a, {}) for a in verdict_answers],
        ]
        return factcheck.run(script, tmp_path, client,
                             search=lambda q, max_results=5: [{"url": "https://x", "title": "t", "snippet": ""}],
                             fetch=lambda u: "page text about the plateau revolver find era",
                             lb_claims=lb)

    def test_load_bearing_not_enough_evidence_blocks(self, tmp_path):
        report = self._run(tmp_path, [{"verdict": "NOT ENOUGH EVIDENCE"}],
                           lb=["A revolver was found in the 1950s on Cannibal Plateau"])
        assert report["blocks_recording"] is True
        assert report["findings"][0]["load_bearing"] is True

    def test_trivial_not_enough_evidence_stays_advisory(self, tmp_path):
        report = self._run(tmp_path, [{"verdict": "NOT ENOUGH EVIDENCE"}],
                           lb=["Packer emerged alone at the agency on April 16, 1874"])
        assert report["blocks_recording"] is False
        assert report["findings"][0]["material"] is False


class TestDefect6LockedScript:
    def test_decide_d_locks_and_downstream_uses_that_sha(self, episode):
        from backend.lwm import decisions
        (episode / "10-final-candidate.md").write_text("The locked final script text.")
        # ledger must have stage 10 row; template does. Approve:
        r = decisions.decide_d(episode, approve=True)
        path, sha = decisions.locked_script(episode)
        assert r["sha"] == sha
        assert path.read_text() == "The locked final script text."
        lineage = json.loads((episode / "outputs" / "final-script.json").read_text())["lineage"]
        assert "07-draft.md" in lineage

    def test_no_candidate_no_lock(self, episode):
        from backend.lwm import decisions
        with pytest.raises(RuntimeError, match="no final candidate"):
            decisions.decide_d(episode, approve=True)


class TestDecide:
    def test_a_records_both_topic_rows(self, workspace):
        from backend.lwm import decisions, ledger
        from backend.lwm import episode as ep
        d = Path(ep.create("fresh", offline=True)["path"])
        decisions.decide_a(d, "the buried-evidence angle", "title: The Man Who Ate His Party",
                           "on camera + archival")
        rows = ledger.read_rows(d)
        assert rows["1 angle + packaging"].complete
        assert rows["2 feasibility + format"].complete
        assert "TOUCHPOINT A" in (d / "DECISION-LOG.md").read_text()

    def test_a_kill_is_terminal(self, workspace):
        from backend.lwm import decisions, orchestrate
        from backend.lwm import episode as ep
        d = Path(ep.create("doomed", offline=True)["path"])
        decisions.decide_a(d, "no story here", "", "", kill=True)
        log = orchestrate.step()
        assert log[-1]["stop"]["reason"] == "kill"

    def test_c_correction_uses_the_one_redraft_cap(self, episode):
        from backend.lwm import decisions, ledger
        ledger.update_row(episode, "7 draft", status="M1 drafted")
        decisions.decide_c(episode, correction="stop giving everything away up front")
        assert "correction issued" in ledger.read_rows(episode)["7 draft"].status
        assert "giving everything away" in (episode / "07-dispatch-notes.md").read_text()
        # the cap: a second correction after the redraft is refused
        ledger.update_row(episode, "7 draft", status="M1 drafted",
                          notes="redraft used (cap 1)")
        with pytest.raises(RuntimeError, match="cap is spent"):
            decisions.decide_c(episode, correction="another one")
