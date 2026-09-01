"""RA → v4 handoff and Stage 4 population, against the REAL Packer job docs.

The Phase 0 lesson is the contract here: two of three hand-written registry
rows mis-attributed their sources, so provenance is validated by code against
actual RA evidence — never trusted from any author.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "lwm"
JOB = "0f7e0818-5def-49dd-bec9-a16b1b534979"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURES / "workspace", ws)
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


@pytest.fixture
def episode(workspace):
    from backend.lwm import episode as ep
    from backend.lwm import ledger
    r = ep.create("The Colorado Cannibal", offline=True)
    d = Path(r["path"])
    for stage in ("1 angle + packaging", "2 feasibility + format"):
        ledger.update_row(d, stage, status="decided", gate="KILL gate: pass")
    (d / "research").mkdir(exist_ok=True)
    (d / "research" / "ra-job.json").write_text(json.dumps({"jobs": [], "current": JOB}))
    return d


def _harvest():
    return json.loads((FIXTURES / "harvest.json").read_text())


class TestHandoff:
    def test_full_handoff_produces_every_artifact(self, episode):
        from backend.lwm import handoff, ledger
        result = handoff.run_handoff(episode, JOB, docs_dir=FIXTURES, harvest=_harvest())
        assert result["registry_rows"] > 10
        for name in ("03-brief.md", "04-sources-registry.md", "04b-briefing.md",
                     "04b-briefing.html", "04b-briefing.json",
                     "research/doc_0.json", "research/doc_2.json"):
            assert (episode / name).exists(), name
        rows = ledger.read_rows(episode)
        assert rows["3 brief"].complete
        assert "PENDING" in rows["4b briefing + structure session"].notes

    def test_briefing_json_round_trips_through_the_production_model(self, episode):
        from backend.lwm import handoff
        from backend.models.briefing import Briefing
        handoff.run_handoff(episode, JOB, docs_dir=FIXTURES, harvest=_harvest())
        data = json.loads((episode / "04b-briefing.json").read_text())
        Briefing.model_validate(data["data"])  # provenance survives, schema holds

    def test_missing_doc_rejected_loudly_and_no_half_state(self, episode, tmp_path):
        from backend.lwm import handoff, ledger
        broken = tmp_path / "docs"
        broken.mkdir()
        shutil.copy(FIXTURES / "doc_0.json", broken / "doc_0.json")  # doc_1/2 missing
        before = ledger.read_rows(episode)["3 brief"].status
        with pytest.raises(FileNotFoundError):
            handoff.run_handoff(episode, JOB, docs_dir=broken)
        assert not (episode / "04b-briefing.md").exists()
        assert ledger.read_rows(episode)["3 brief"].status == before

    def test_rerun_is_idempotent(self, episode):
        from backend.lwm import handoff
        handoff.run_handoff(episode, JOB, docs_dir=FIXTURES, harvest=_harvest())
        first = (episode / "04-sources-registry.md").read_text()
        handoff.run_handoff(episode, JOB, docs_dir=FIXTURES, harvest=_harvest())
        second = (episode / "04-sources-registry.md").read_text()
        assert first == second  # regenerated, never appended twice

    def test_handoff_refused_once_the_outline_is_written(self, episode):
        from backend.lwm import handoff, ledger
        handoff.run_handoff(episode, JOB, docs_dir=FIXTURES, harvest=_harvest())
        ledger.update_row(episode, "4b briefing + structure session", status="done")
        ledger.update_row(episode, "5 outline", status="done")
        with pytest.raises(RuntimeError, match="drift"):
            handoff.run_handoff(episode, JOB, docs_dir=FIXTURES, harvest=_harvest())

    def test_manifest_entries_linked_to_ra_source_ids(self, workspace):
        from backend.lwm import episode as ep
        from backend.lwm import handoff, ledger, manifest
        d0 = json.loads((FIXTURES / "doc_0.json").read_text())["data"]
        a_url = next(s["url"] for s in d0["sources"] if s.get("url"))
        r = ep.create("Packer", sources=[a_url], offline=True)
        d = Path(r["path"])
        for stage in ("1 angle + packaging", "2 feasibility + format"):
            ledger.update_row(d, stage, status="decided")
        handoff.run_handoff(d, JOB, docs_dir=FIXTURES, harvest=_harvest())
        entry = manifest.load(d)["sources"][0]
        assert entry["ra_source_id"] is not None
        assert entry["ingestion_status"] == "ingested"


class TestRegistryProvenance:
    def test_rows_cite_only_sources_whose_evidence_supports_them(self):
        from backend.lwm import registry
        d0 = json.loads((FIXTURES / "doc_0.json").read_text())["data"]
        d1 = json.loads((FIXTURES / "doc_1.json").read_text())["data"]
        reg = registry.build(d0, d1, harvest=_harvest())
        valid = {s["source_id"] for s in d0["sources"]}
        for row in reg["rows"]:
            if row["status"] == "MISSING-SOURCE":
                continue
            for sid in row["source"].split(" · "):
                assert sid in valid, f"row {row['n']} cites unknown {sid}"

    def test_a_fabricated_source_attribution_is_stripped_by_code(self):
        from backend.lwm import registry
        d0 = json.loads((FIXTURES / "doc_0.json").read_text())["data"]
        d1 = {"key_points": [{
            "key_point_id": "SRC_5:KP_X",
            "statement": "Packer personally met President Grant in Washington in 1875",
            "source_ids": ["SRC_5"], "confidence": "high"}], "tensions": []}
        reg = registry.build(d0, d1, harvest=_harvest())
        assert reg["rows"][0]["status"] == "MISSING-SOURCE"
        assert reg["rows"][0]["source"] == "—"

    def test_contested_key_points_get_contested_status(self):
        from backend.lwm import registry
        d0 = json.loads((FIXTURES / "doc_0.json").read_text())["data"]
        d1 = json.loads((FIXTURES / "doc_1.json").read_text())["data"]
        reg = registry.build(d0, d1, harvest=_harvest())
        contested = {k for t in d1["tensions"] for k in t["involved_key_points"]}
        hits = [r for r in reg["rows"] if r["kp_id"] in contested and r["status"] != "MISSING-SOURCE"]
        assert hits and all(r["status"] == "CONTESTED" for r in hits)

    def test_judgment_pass_applies_only_wellformed_answers(self):
        from backend.lwm import registry
        d0 = json.loads((FIXTURES / "doc_0.json").read_text())["data"]
        d1 = json.loads((FIXTURES / "doc_1.json").read_text())["data"]
        client = MagicMock()
        def answer(prompt, schema, system, max_tokens):
            ns = [int(line.split(".")[0]) for line in prompt.splitlines() if line and line[0].isdigit()]
            rows = []
            for n in ns:
                rows.append({"n": n, "class": "REALITY", "lb": n == ns[0],
                             "allowed": "state plainly", "prohibited": "",
                             "anchor": "worth 90 million today"})  # invented number
            rows.append({"n": 9999, "class": "STORY", "lb": True, "allowed": "x"})  # unknown row
            rows.append({"n": ns[0], "class": "NONSENSE", "lb": True, "allowed": "y"})  # bad class -> dropped
            return {"rows": rows}, {}
        client.generate_structured.side_effect = answer
        reg = registry.build(d0, d1, harvest=_harvest(), judgment_client=client)
        judged = [r for r in reg["rows"] if r["class"]]
        assert judged, "well-formed answers applied"
        # The invented anchor number never survives code validation (D-21).
        assert all(r["anchor"] == "—" or "90 million" not in r["anchor"] for r in reg["rows"])

    def test_validate_catches_shape_problems(self):
        from backend.lwm import registry
        rows = [{"n": 1, "claim": "x", "class": "REALITY", "status": "CONFIRMED",
                 "source": "—", "kp_id": "a", "lb": "y", "allowed": "", "prohibited": "", "anchor": "—"}]
        problems = registry.validate(rows)
        assert any("no source" in p for p in problems)
