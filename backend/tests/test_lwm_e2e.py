"""The Phase 1 end-to-end state machine: new → RECORD, every touchpoint, no loops.

Real control flow and real code paths; model calls, search, and research are
mocked. Asserts the correction-pass contract: no gate loops, no research
rerun, no repeated C after approval, the locked script's SHA carries through
10b and 11, no reviewer flag becomes Maz homework, and the machine parks at
RECORD.
"""

import json
import re
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"
JOB = "0f7e0818-5def-49dd-bec9-a16b1b534979"


def _writer():
    c = MagicMock()
    def answer(prompt, schema, system, max_tokens):
        if "build the episode outline" in system.lower():
            return {"text": "# Outline\n\nMovement 1: the walk out.\nMovement 2: the trials.\n"}, {}
        m = re.search(r"Draft MOVEMENT (\d)", prompt)
        n = m.group(1) if m else "1"
        if n == "1":
            return {"text": ("He walked out of the mountains alone on April 16, 1874, "
                             "and the first thing he asked for was whiskey. "
                             + "The winter had held the pass shut for weeks on end. " * 10)}, {}
        return {"text": ("The trials came later, and the years wore every version of "
                         "his story thinner. " + "The record grew stranger each decade. " * 10)}, {}
    c.generate_structured.side_effect = answer
    return c


def _reader(gripped=True):
    c = MagicMock()
    c.generate_structured.return_value = (
        {"gripped": gripped, "held_best": "the whiskey line",
         "drop_off_point": "" if gripped else "the parole stretch", "note": "n"}, {})
    return c


def _editor():
    c = MagicMock()
    c.generate_structured.return_value = ({"pairs": [
        {"old": "the first thing he asked for was whiskey.",
         "new": "the first thing he asked for was whiskey — not food.",
         "why": "register"}]}, {})
    return c


def _judge():
    """Extraction + one verdict per claim, all supported with verifiable quotes."""
    c = MagicMock()
    def answer(prompt, schema, system, max_tokens):
        props = set(schema.get("properties", {}))
        if "claims" in props:
            return {"claims": [{"claim": "He walked out of the mountains alone on April 16, 1874",
                                "script_line": "He walked out of the mountains alone on April 16, 1874"}]}, {}
        if "rows" in props:  # registry judgment pass
            ns = [int(m) for m in re.findall(r"^(\d+)\.", prompt, re.M)]
            return {"rows": [{"n": n, "class": "REALITY", "lb": n <= 2,
                              "allowed": "state plainly", "prohibited": "", "anchor": ""}
                             for n in ns]}, {}
        return {"verdict": "SUPPORTED", "url": "https://hist.example/p",
                "quote": "walked out of the mountains alone on April 16, 1874"}, {}
    c.generate_structured.side_effect = answer
    return c


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


def test_full_state_machine_new_to_record(workspace, monkeypatch):
    from backend.lwm import decisions, ledger, orchestrate
    from backend.lwm import episode as ep

    research_calls = []
    def fake_round(ep_dir, topic):
        research_calls.append(topic)
        (ep_dir / "research").mkdir(exist_ok=True)
        (ep_dir / "research" / "ra-job.json").write_text(json.dumps({"jobs": [], "current": JOB}))
        return {"job_id": JOB, "status": "completed", "claims_count": 119, "sources_count": 11}
    monkeypatch.setattr(orchestrate.research, "run_round", fake_round)
    monkeypatch.setattr(orchestrate.research, "run_gap_rounds",
                        lambda *a, **k: [{"round": 1, "added": ["https://x"], "job_id": JOB}])

    harvest = json.loads((FIXTURES / "harvest.json").read_text())
    hooks = dict(
        docs_dir=FIXTURES, harvest=harvest, judgment_client=_judge(),
        writer_client=_writer(), editor_client=_editor(),
        reader_clients=[_reader(True), _reader(True), _reader(False)],
        judge_client=_judge(),
        search=lambda q, max_results=5: [{"url": "https://hist.example/p", "title": "t", "snippet": ""}],
        fetch=lambda u: ("Records show he walked out of the mountains alone on April 16, 1874, "
                         "and asked first for whiskey."),
    )

    # NEW → stop at A
    r = ep.create("The Colorado Cannibal", sources=["https://youtu.be/TlAXZVdAhIo"], offline=True)
    d = Path(r["path"])
    log = orchestrate.step(**hooks)
    assert log[-1]["stop"]["detail"].startswith("Maz touchpoint A")

    # decide A → research (once) → handoff → stop at B
    decisions.decide_a(d, "tell it as it happened", "title: The Man Who Walked Out",
                       "on camera + archival")
    log = orchestrate.step(**hooks)
    assert research_calls == ["The Colorado Cannibal"], "one research run, ledger advanced"
    assert ledger.read_rows(d)["3 brief"].complete
    assert ledger.read_rows(d)["4 fact-check the brief"].complete
    assert log[-1]["stop"]["detail"].startswith("Maz touchpoint B")

    # A rerun of continue must not repeat research or handoff.
    log = orchestrate.step(**hooks)
    assert research_calls == ["The Colorado Cannibal"]
    assert log[-1]["stop"]["detail"].startswith("Maz touchpoint B")

    # decide B → outline → gate A internal → M1 → stop at C
    decisions.decide_b(d, notes="open at the agency door; hold the trials for movement 2")
    log = orchestrate.step(**hooks)
    assert ledger.read_rows(d)["5 outline"].complete
    assert ledger.read_rows(d)["6 grip gate A"].complete  # internal, no Maz
    stop = log[-1]["stop"]
    assert stop["reason"] == "touchpoint" and stop["detail"].startswith("C —")

    # decide C approve → M2 drafted → REAL edit train → gate B (grip map) →
    # pace edit → one candidate → stop at D. C never repeats.
    decisions.decide_c(d, approve=True)
    log = orchestrate.step(**hooks)
    details = [e.get("stop", {}).get("detail", "") for e in log]
    assert not any(x.startswith("C —") for x in details), "C must not repeat after approval"
    rows = ledger.read_rows(d)
    assert rows["7 draft"].complete
    assert rows["8 edit"].complete and "pairs applied" in rows["8 edit"].notes
    assert (d / "08-edit-log.md").exists() and "APPLIED" in (d / "08-edit-log.md").read_text()
    assert rows["9 grip gate B"].complete
    assert "held: “the whiskey line”" in (d / "09-grip-gate-b.md").read_text()
    assert rows["9b pace edit"].complete
    assert log[-1]["stop"]["detail"].startswith("D —")
    assert (d / "10-final-candidate.md").exists()

    # decide D approve → LOCK. 10b checks the locked sha; 11 packages the same sha.
    locked_result = decisions.decide_d(d, approve=True)
    sha = locked_result["sha"]
    log = orchestrate.step(**hooks)
    rows = ledger.read_rows(d)
    assert rows["10b script fact-check (D-SFC-1)"].complete
    assert sha in rows["10b script fact-check (D-SFC-1)"].notes, "10b checked the LOCKED script"
    assert rows["11 production package"].complete
    pkg = json.loads((d / "editing" / "production-package.json").read_text())
    assert pkg["script"]["sha"] == sha, "the packaged sha IS the locked sha"
    assert pkg["script"]["path"].endswith("outputs/final-script-locked.md")

    # Machine parks at RECORD; nothing internal became Maz homework.
    assert log[-1]["stop"]["detail"].startswith("Maz touchpoint record")
    from backend.lwm import episode as ep2
    s = ep2.status(d.name)
    assert s["macro_state"] == "RECORDED"
    assert s["final_script"]["sha"] == sha
    decision_log = (d / "DECISION-LOG.md").read_text()
    assert "lint" not in decision_log.lower(), "no reviewer flags in Maz's decision log"


def test_c_correction_path_regenerates_once_then_returns_to_the_ear(workspace, monkeypatch):
    from backend.lwm import decisions, ledger, orchestrate
    from backend.lwm import episode as ep
    d = Path(ep.create("Correction path", offline=True)["path"])
    for s in ("1 angle + packaging", "2 feasibility + format", "3 brief",
              "4 fact-check the brief", "4b briefing + structure session",
              "5 outline", "6 grip gate A"):
        ledger.update_row(d, s, status="done", gate="—")
    hooks = dict(writer_client=_writer())
    log = orchestrate.step(**hooks)          # drafts M1, stops at C
    assert log[-1]["stop"]["detail"].startswith("C —")
    decisions.decide_c(d, correction="hold the reveal; the door opens too early")
    log = orchestrate.step(**hooks)          # regenerates M1 once, back to the ear
    assert log[-1]["stop"]["detail"].startswith("C —")
    assert "redraft used" in ledger.read_rows(d)["7 draft"].notes
    text = (d / "07-dispatch-notes.md").read_text()
    assert "door opens too early" in text


def _fc_judge(verdict_by_run):
    """Judge whose 10b verdicts change between runs (run index → answers)."""
    state = {"run": 0}
    c = MagicMock()
    def answer(prompt, schema, system, max_tokens):
        props = set(schema.get("properties", {}))
        if "claims" in props:
            state["run"] += 1
            return {"claims": [{"claim": "The jury deliberated for three hours",
                                "script_line": "The jury deliberated for three hours."}]}, {}
        return verdict_by_run[min(state["run"], len(verdict_by_run)) - 1], {}
    c.generate_structured.side_effect = answer
    return c


def test_adverse_path_material_blocker_correction_new_sha(workspace, monkeypatch):
    """final candidate → D approve → SHA A → 10b material → D correction →
    lock superseded → correction pass changes the candidate → D → SHA B →
    10b reruns on B → passes → 11 packages B → RECORD."""
    from backend.lwm import decisions, ledger, orchestrate
    from backend.lwm import episode as ep

    d = Path(ep.create("Adverse path", offline=True)["path"])
    for s in ("1 angle + packaging", "2 feasibility + format", "3 brief",
              "4 fact-check the brief", "4b briefing + structure session",
              "5 outline", "6 grip gate A", "7 draft", "8 edit",
              "9 grip gate B", "9b pace edit"):
        ledger.update_row(d, s, status="done", gate="—")
    (d / "07-draft.md").write_text(
        "## Movement 1\n\nThe jury deliberated for three hours. The verdict came at dusk.\n")
    # LB registry row matching the claim → NOT ENOUGH EVIDENCE would also block,
    # but this test uses REFUTED for run 1.
    (d / "04-sources-registry.md").write_text(
        "| # | claim | class | status | source | LB | allowed wording | prohibited wording | anchor |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| 1 | The jury deliberated for three hours before the verdict | REALITY | CONFIRMED | SRC_1 | y | — | — | — |\n")

    judge = _fc_judge([
        {"verdict": "REFUTED", "url": "https://court.example/x",
         "quote": "the jury deliberated for three days"},
        {"verdict": "SUPPORTED", "url": "https://court.example/x",
         "quote": "the jury deliberated for three days"},
    ])
    editor = MagicMock()
    editor.generate_structured.return_value = ({"pairs": [
        {"old": "deliberated for three hours", "new": "deliberated for three days",
         "why": "Maz's factual correction"}]}, {})
    hooks = dict(
        editor_client=editor, judge_client=judge,
        search=lambda q, max_results=5: [{"url": "https://court.example/x", "title": "t", "snippet": ""}],
        fetch=lambda u: "Court record: the jury deliberated for three days before returning.",
    )

    # candidate → D approve → SHA A
    log = orchestrate.step(**hooks)
    assert log[-1]["stop"]["detail"].startswith("D —")
    sha_a = decisions.decide_d(d, approve=True)["sha"]

    # 10b run 1: REFUTED on an LB claim → material blocker, stop for ruling
    log = orchestrate.step(**hooks)
    assert log[-1]["stop"]["reason"] == "contradiction"
    assert "material" in ledger.read_rows(d)["10b script fact-check (D-SFC-1)"].status

    # No infinite loop: another continue does NOT rerun the check, same stop.
    calls_before = judge.generate_structured.call_count
    log = orchestrate.step(**hooks)
    assert log[-1]["stop"]["reason"] == "contradiction"
    assert judge.generate_structured.call_count == calls_before, "10b must not rerun on the same sha"

    # Maz rules through the EXISTING D path (no fifth touchpoint).
    r = decisions.decide_d(d, corrections="the jury deliberated for three days, not hours")
    assert r["corrections"]
    meta = json.loads((d / "outputs" / "final-script.json").read_text())
    assert meta["approved"] is False, "old lock no longer counts"
    assert meta["history"][0]["sha"] == sha_a, "old SHA preserved in history"
    assert decisions.locked_script(d) is None

    before = (d / "10-final-candidate.md").read_text()
    log = orchestrate.step(**hooks)   # correction pass runs, stops at D
    after = (d / "10-final-candidate.md").read_text()
    assert log[-1]["stop"]["detail"].startswith("D — REVISED")
    assert after != before and "three days" in after, "the correction actually changed the text"
    assert "three hours" not in after
    assert (d / "10-correction-pass.md").exists()

    # Approve the revised candidate → SHA B ≠ SHA A; 10b reruns on B; 11 packages B.
    sha_b = decisions.decide_d(d, approve=True)["sha"]
    assert sha_b != sha_a
    log = orchestrate.step(**hooks)
    rows = ledger.read_rows(d)
    assert rows["10b script fact-check (D-SFC-1)"].complete
    assert sha_b in rows["10b script fact-check (D-SFC-1)"].notes, "second run checked SHA B"
    pkg = json.loads((d / "editing" / "production-package.json").read_text())
    assert pkg["script"]["sha"] == sha_b, "stage 11 packages the NEW sha, never the superseded one"
    assert log[-1]["stop"]["detail"].startswith("Maz touchpoint record")
    # The checker never edited the locked script itself.
    assert (d / "outputs" / "final-script-locked.md").read_text() == after
