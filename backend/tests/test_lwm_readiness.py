"""Acceptance tests for the PACKER READINESS PATCH (2026-09-01).

One test per bullet of the plan's §20, plus the three disciplines the patch
exists to enforce: research precedes the angle · a THIN movement never reaches
the writer · fact + evidence status + allowed/prohibited wording travel
together at every handoff.
"""

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
    monkeypatch.setenv("LWM_WORKSPACE", str(ws))
    return ws


@pytest.fixture
def episode(workspace):
    from backend.lwm import episode as ep
    d = Path(ep.create("The Colorado Cannibal", offline=True)["path"])
    (d / "research").mkdir(exist_ok=True)
    for name in ("doc_0", "doc_1", "doc_2"):
        shutil.copy(FIXTURES / f"{name}.json", d / "research" / f"{name}.json")
    return d


def _registry(d, n=8):
    rows = "\n".join(
        f"| {i} | sourced claim number {i} about the walk out | REALITY | CONFIRMED | SRC_1 | "
        f"{'y' if i < 3 else 'n'} | say it plainly | do not overstate it | — |"
        for i in range(1, n + 1))
    (d / "04-sources-registry.md").write_text(
        "| # | claim | class | status | source | LB | allowed wording | prohibited wording | anchor |\n"
        "|---|---|---|---|---|---|---|---|---|\n" + rows + "\n")


ANGLE_ANSWER = {
    "story_already_told": {
        "dominant_story": "a man walked out alone", "driving_question": "did he kill them",
        "typical_beginning": "six set off", "typical_middle": "one returns",
        "typical_ending": "he is convicted", "common_conclusion": "he probably did it",
        "repeated_facts": ["five men died"], "disagreements": ["self-defence"],
        "missed_by_sources": ["the exhumation"]},
    "baseline": {"name": "The man who came back",
                 "central_story": "a survivor accused of killing and eating his companions",
                 "driving_question": "did he murder them or outlive them",
                 "viewer_payoff": "what the evidence settles", "strongest_evidence": "the dig",
                 "strongest_reveal": "the bones", "stakes": "a name",
                 "difference_from_baseline": "—", "weaknesses": "familiar"},
    "alternatives": [
        {"name": "The town that needed a monster",
         "central_story": "a frontier community inventing a villain it could hang",
         "driving_question": "why did Colorado need this man guilty",
         "viewer_payoff": "how a place makes a monster", "strongest_evidence": "the press record",
         "strongest_reveal": "the second trial", "stakes": "who gets believed",
         "difference_from_baseline": "the town is the subject", "weaknesses": "thinner sources"},
        {"name": "The forensic argument that never closed",
         "central_story": "a century of scientists arguing over five skeletons",
         "driving_question": "can bones answer a question this old",
         "viewer_payoff": "the limits of proof", "strongest_evidence": "the 1989 dig",
         "strongest_reveal": "their disagreement", "stakes": "what proof means",
         "difference_from_baseline": "science is the subject", "weaknesses": "no ending"},
        {"name": "The pardon machine",
         "central_story": "a newspaper campaign that freed a convicted man",
         "driving_question": "who decides when a sentence ends",
         "viewer_payoff": "how opinion moved a state", "strongest_evidence": "parole papers",
         "strongest_reveal": "the release", "stakes": "the machinery of mercy",
         "difference_from_baseline": "the press is the subject", "weaknesses": "less visceral"}],
    "baseline_is_strongest": False,
    "strongest_why": "the town angle uses material the others skip",
}


def _client(answer):
    c = MagicMock()
    c.generate_structured.return_value = (answer, {})
    return c


class TestAngleStage:
    def test_baseline_three_alternatives_and_the_custom_path(self, episode):
        from backend.lwm import angle
        o = angle.build(episode, client=_client(ANGLE_ANSWER))
        assert o["baseline"]["name"]
        assert len(o["alternatives"]) == 3
        assert o["chosen"] is None, "no agent chooses an angle for Maz"
        assert o["custom_option"]
        assert (episode / "01-angle-options.md").exists()

    def test_alternatives_must_differ_at_the_story_level(self, episode):
        """New detail ≠ new story: three emphases of one story are caught."""
        from backend.lwm import angle
        same = dict(ANGLE_ANSWER)
        base = ANGLE_ANSWER["baseline"]
        same["alternatives"] = [
            {**base, "name": f"same story, {flavour} detail",
             "difference_from_baseline": f"more {flavour} detail"}
            for flavour in ("forensic", "trial", "parole")]
        o = angle.build(episode, client=_client(same))
        assert not any(c["story_level"] for c in o["distinctness"])
        md = (episode / "01-angle-options.md").read_text()
        assert "Not a story-level alternative" in md

    def test_the_familiar_story_being_strongest_is_expressible(self, episode):
        from backend.lwm import angle
        o = angle.build(episode, client=_client({**ANGLE_ANSWER,
                                                 "baseline_is_strongest": True,
                                                 "strongest_why": "nothing beats it here"}))
        assert o["baseline_is_strongest"] is True
        assert "the familiar story is still the strongest" in \
               (episode / "01-angle-options.md").read_text()

    def test_supplied_source_baseline_is_named_honestly(self, episode):
        """Packer supplied no sources. The artifact must not pretend otherwise,
        and must never call source consensus 'the mainstream story'."""
        from backend.lwm import angle
        o = angle.build(episode, client=_client(ANGLE_ANSWER))
        assert o["supplied_sources"] == 0
        assert "research corpus" in o["basis"]
        md = (episode / "01-angle-options.md").read_text().lower()
        assert "mainstream" not in md
        assert "you supplied no sources" in md

    def test_previous_maz_idea_is_carried_as_an_input_not_a_lock(self, episode):
        from backend.lwm import angle, ledger
        ledger.update_row(episode, "1 angle", status="open",
                          notes="spine chosen: tell it as it happened, buried-evidence twist lands late.")
        o = angle.build(episode, client=_client(ANGLE_ANSWER))
        assert "buried-evidence twist" in o["previous_maz_idea"]
        assert o["chosen"] is None
        md = (episode / "01-angle-options.md").read_text()
        assert "Your previous idea" in md and "nothing has locked it" in md

    @pytest.mark.parametrize("verdict", [
        "strongly supported", "workable but thin", "conflicts with evidence",
        "needs targeted research"])
    def test_custom_angle_returns_one_of_the_four_verdicts(self, episode, verdict):
        from backend.lwm import angle
        r = angle.assess_custom(episode, "tell it from the town's side",
                                client=_client({"verdict": verdict, "why": "because"}))
        assert r["verdict"] == verdict
        assert "override" in r and "stands" in r["override"]

    def test_an_unrecognised_verdict_falls_back_safely(self, episode):
        from backend.lwm import angle
        r = angle.assess_custom(episode, "x", client=_client({"verdict": "great!", "why": "w"}))
        assert r["verdict"] in angle.CUSTOM_VERDICTS

    def test_choosing_records_the_angle_and_never_invents_one(self, episode):
        from backend.lwm import angle, decisions, ledger
        angle.build(episode, client=_client(ANGLE_ANSWER))
        r = decisions.decide_angle(episode, choice="alt-2")
        assert r["chosen"]["kind"] == "alt-2"
        assert ledger.read_rows(episode)["1 angle"].complete
        with pytest.raises(ValueError):
            decisions.decide_angle(episode, choice="alt-9")

    def test_a_custom_angle_is_assessed_but_never_overruled(self, episode):
        from backend.lwm import angle, decisions
        angle.build(episode, client=_client(ANGLE_ANSWER))
        r = decisions.decide_angle(
            episode, custom="the town needed a monster",
            client=_client({"verdict": "conflicts with evidence", "why": "the record disagrees"}))
        assert r["chosen"]["kind"] == "custom"
        assert r["assessment"]["verdict"] == "conflicts with evidence"
        saved = json.loads((episode / "outputs" / "angle-options.json").read_text())
        assert saved["chosen"]["central_story"] == "the town needed a monster"


PACKAGING_ANSWER = {
    "titles": [{"title": f"T{i}", "why_it_fits": "fits", "risk": "low"} for i in range(5)],
    "thumbnails": [{"concept": f"C{i}", "why_it_fits": "fits", "risk": "low"} for i in range(3)],
    "viewer_promise": "you will see how a town made a monster",
    "mismatch_risk": "never promise a confession",
}


class TestPackaging:
    def test_concepts_only_and_the_angle_is_untouched(self, episode):
        from backend.lwm import angle, decisions, packaging
        angle.build(episode, client=_client(ANGLE_ANSWER))
        decisions.decide_angle(episode, choice="alt-1")
        before = json.loads((episode / "outputs" / "angle-options.json").read_text())["chosen"]
        p = packaging.build(episode, client=_client(PACKAGING_ANSWER))
        after = json.loads((episode / "outputs" / "angle-options.json").read_text())["chosen"]
        assert after == before, "packaging may sell the story, never change it"
        assert len(p["titles"]) == 5 and len(p["thumbnails"]) == 3
        assert p["viewer_promise"]
        md = (episode / "01b-packaging.md").read_text()
        assert "nothing is generated" in md

    def test_packaging_refuses_to_run_before_an_angle_is_chosen(self, episode):
        from backend.lwm import angle, packaging
        angle.build(episode, client=_client(ANGLE_ANSWER))
        with pytest.raises(RuntimeError):
            packaging.build(episode, client=_client(PACKAGING_ANSWER))


ARCH_ANSWER = {
    "macro_shape": "investigation", "why_this_shape": "evidence arrives in stages",
    "audience_belief_entering": "he was a cannibal",
    "what_changes_that_belief": "the record is thinner than the legend",
    "information_order_rationale": "hold the dig",
    "movements": [{"n": 1, "story_job": "the walk out", "what_changes": "doubt"},
                  {"n": 2, "story_job": "the trials", "what_changes": "the record"}],
    "legitimate_withholding": "the exhumation", "human_stakes": "five families",
    "ending": "what the bones could not settle", "unresolved_uncertainty": "who struck first",
    "compressed_vs_full_scene": "the walk out is a full scene",
    "techniques_used": ["plant/payoff"],
}


class TestStoryArchitecture:
    def test_structure_only_and_liftable_prose_is_flagged(self, episode):
        from backend.lwm import angle, architecture, decisions
        angle.build(episode, client=_client(ANGLE_ANSWER))
        decisions.decide_angle(episode, choice="baseline")
        a = architecture.build(episode, client=_client(ARCH_ANSWER))
        assert a["macro_shape_known"] is True
        assert a["liftable_prose"] == []

        leaky = {**ARCH_ANSWER, "ending":
                 "“He walked out of those mountains alone and the first thing he asked for was "
                 "whiskey, not food, and that is the detail that never stopped mattering.”"}
        a2 = architecture.build(episode, client=_client(leaky))
        assert a2["liftable_prose"], "an outline/architecture must not supply liftable lines"


def _outline_answer(rows_m1, rows_m2=None, coverage="SOLID"):
    def movement(n, rows):
        return {"n": n, "story_job": f"job {n}", "events": [f"event {n}"],
                "audience_state_entering": "in", "what_changes": "out",
                "names": ["Packer"], "dates": ["1874"], "actions": ["walked"],
                "documents": ["the report"], "numbers": ["five"], "quotes": [],
                "registry_claim_ids": rows, "brief_references": [],
                "contradictions": ["accounts differ"], "setup_payoff_reveal": "plant",
                "forward_pull": "then", "coverage": coverage, "coverage_reason": "r",
                "missing_material": []}
    ms = [movement(1, rows_m1)]
    if rows_m2:
        ms.append(movement(2, rows_m2))
    return {"movements": ms}


def _seed_for_outline(episode, n_rows=8):
    from backend.lwm import angle, architecture, decisions
    _registry(episode, n_rows)
    angle.build(episode, client=_client(ANGLE_ANSWER))
    decisions.decide_angle(episode, choice="baseline")
    from backend.lwm import packaging
    packaging.build(episode, client=_client(PACKAGING_ANSWER))
    architecture.build(episode, client=_client(ARCH_ANSWER))


class TestDenseOutline:
    def test_every_required_field_and_a_coverage_class(self, episode):
        from backend.lwm import outline
        _seed_for_outline(episode)
        o = outline.build(episode, client=_client(_outline_answer([1, 2, 3, 4, 5])))
        m = o["movements"][0]
        for field in ("story_job", "events", "names", "dates", "actions", "documents",
                      "numbers", "contradictions", "setup_payoff_reveal", "forward_pull",
                      "registry_claim_ids", "coverage", "allowed_wording", "resolved_rows"):
            assert field in m, field
        assert m["coverage"] in outline.COVERAGE
        assert m["allowed_wording"], "wording travels with the facts into the outline"

    def test_code_overrides_an_optimistic_model_classification(self, episode):
        """code decides, a model advises, a model never gates."""
        from backend.lwm import outline
        _seed_for_outline(episode)
        o = outline.build(episode, client=_client(_outline_answer([1])))   # one row, "SOLID"
        m = o["movements"][0]
        assert m["coverage_model"] == "SOLID"
        assert m["coverage"] == "THIN"
        assert m["missing_material"], "a THIN movement names what is missing"

    def test_the_stricter_classification_always_wins(self):
        from backend.lwm import outline
        assert outline.stricter("SOLID", "THIN") == "THIN"
        assert outline.stricter("PRECISION-RISK", "SOLID") == "PRECISION-RISK"

    def test_contested_rows_make_a_movement_precision_risk(self, episode):
        from backend.lwm import outline
        _seed_for_outline(episode)
        text = (episode / "04-sources-registry.md").read_text()
        (episode / "04-sources-registry.md").write_text(text.replace(
            "| 2 | sourced claim number 2 about the walk out | REALITY | CONFIRMED |",
            "| 2 | sourced claim number 2 about the walk out | STORY | CONTESTED |"))
        o = outline.build(episode, client=_client(_outline_answer([1, 2, 3, 4, 5])))
        assert o["movements"][0]["coverage"] == "PRECISION-RISK"


class TestDraftPacketsAndThinMovements:
    def test_a_thin_movement_never_reaches_the_writer(self, episode):
        from backend.lwm import outline, packet
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1])))
        with pytest.raises(packet.ThinMovement) as e:
            packet.build(episode, 1)
        assert e.value.movement == 1

    def test_draft_remaining_holds_thin_movements_instead_of_writing_them(self, episode):
        from backend.lwm import ledger, outline, writing
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1, 2, 3, 4, 5], [6])))
        (episode / "07-draft.md").write_text("## Movement 1\n\nalready drafted\n")
        writer = _client({"text": "prose"})
        writing.draft_remaining(episode, client=writer)
        row = ledger.read_rows(episode)["7 draft"]
        assert row.status.startswith("held")
        assert "targeted backfill" in row.notes
        assert "## Movement 2" not in (episode / "07-draft.md").read_text()

    def test_the_packet_is_movement_scoped_and_wording_travels_with_each_fact(self, episode):
        from backend.lwm import outline, packet
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1, 2, 3, 4], [5, 6, 7, 8])))
        p1 = packet.build(episode, 1)
        assert [f["row"] for f in p1["facts"]] == [1, 2, 3, 4], "scoped, not the whole registry"
        for f in p1["facts"]:
            assert f["allowed_wording"] and f["prohibited_wording"]
        assert p1["angle"] and p1["packaging_promise"]
        prompt = packet.render_prompt(p1, rules="RULES CARD")
        assert "say:" in prompt and "never:" in prompt
        assert "sourced claim number 5" not in prompt, "movement 2's facts stay out"

    def test_the_packet_carries_brief_material_the_drafter_never_used_to_get(self, episode):
        from backend.lwm import outline, packet, registry
        _seed_for_outline(episode)
        # Point a registry row at a real research key point so the Brief link resolves.
        doc_1 = json.loads((episode / "research" / "doc_1.json").read_text())
        doc_1 = doc_1.get("data", doc_1)
        statement = doc_1["key_points"][0]["statement"]
        text = (episode / "04-sources-registry.md").read_text()
        (episode / "04-sources-registry.md").write_text(
            text.replace("sourced claim number 1 about the walk out", statement.replace("|", "/")))
        assert registry.read_table(episode)[0]["claim"].startswith(statement[:20])
        outline.build(episode, client=_client(_outline_answer([1, 2, 3, 4])))
        p = packet.build(episode, 1)
        assert p["brief_material"], "the drafter now receives Brief material"

    def test_the_packet_carries_continuity_from_the_previous_movement(self, episode):
        from backend.lwm import outline, packet
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1, 2, 3, 4], [5, 6, 7, 8])))
        (episode / "07-draft.md").write_text(
            "## Movement 1\n\nHe asked first for whiskey, not food.\n")
        p2 = packet.build(episode, 2)
        assert "whiskey" in p2["continuity_from_previous"]

    def test_no_arbitrary_truncation_survives_on_the_writer_path(self):
        """The verified 2026-09-01 defect: [:8000] / [:20000] / [:60000] slices."""
        import re
        from backend.lwm import edit, packet, writing
        for module in (writing, edit, packet):
            src = Path(module.__file__).read_text()
            code = "\n".join(line for line in src.splitlines()
                             if not line.strip().startswith("#"))
            # Display-side trims (log lines, artifact rendering) are fine; context
            # slices of whole documents are the defect.
            assert not re.search(r"cargo\[.[a-z_]+.\]\[:\d+\]", code)
            assert not re.search(r"(registry|briefing|outline|grip_map|structure|voice)\[:\d+\]",
                                 code)


class TestTargetedBackfill:
    def test_backfill_appends_rows_and_never_reruns_the_research_job(self, episode):
        from backend.lwm import backfill, outline, registry
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1])))
        before = len(registry.read_table(episode))
        job_before = (episode / "research" / "ra-job.json")
        job_before.write_text(json.dumps({"jobs": [], "current": "JOB-A"}))

        r = backfill.run(
            episode, 1, ["what the coroner actually recorded"],
            client=_client({"facts": [{"claim": "the coroner recorded blunt force trauma",
                                       "answers": "what the coroner recorded",
                                       "allowed": "the coroner recorded", "prohibited": "proved",
                                       "quote": "blunt force trauma"}]}),
            search=lambda doc0, prompt, existing_urls, max_results=8: [
                {"url": "https://arch.example/coroner", "title": "Coroner report"}],
            fetch=lambda url: "The coroner recorded blunt force trauma to the head.")

        after = registry.read_table(episode)
        assert len(after) == before + 1
        assert r["registry_rows_appended"] and r["full_ra_job_rerun"] is False
        assert json.loads(job_before.read_text())["current"] == "JOB-A", "no RA job rerun"
        appended = after[-1]
        assert "backfill M1" in appended["source"] and appended["allowed"]

    def test_backfill_reclassifies_the_movement_it_filled(self, episode):
        from backend.lwm import backfill, outline
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1])))
        assert json.loads((episode / "outputs" / "outline.json").read_text())["thin_movements"] == [1]
        facts = [{"claim": f"backfilled claim {i}", "answers": "gap",
                  "allowed": "say it carefully", "prohibited": "overstate"} for i in range(4)]
        backfill.run(episode, 1, ["missing"],
                     client=_client({"facts": facts}),
                     search=lambda doc0, prompt, existing_urls, max_results=8: [
                         {"url": "https://arch.example/x", "title": "x"}],
                     fetch=lambda url: "text")
        after = backfill.reclassify(episode, 1)
        assert after["coverage"] != "THIN"

    def test_a_backfill_that_finds_nothing_says_so_and_changes_nothing(self, episode):
        from backend.lwm import backfill, outline, registry
        _seed_for_outline(episode)
        outline.build(episode, client=_client(_outline_answer([1])))
        before = len(registry.read_table(episode))
        r = backfill.run(episode, 1, ["something nobody wrote down"],
                         client=_client({"facts": []}),
                         search=lambda *a, **k: [],
                         fetch=lambda url: "")
        assert r["facts_found"] == 0 and r["registry_rows_appended"] == []
        assert len(registry.read_table(episode)) == before
        assert backfill.reclassify(episode, 1)["coverage"] == "THIN"


class TestReviewStackAndLint:
    def test_three_reviewers_produce_findings_without_summoning_maz(self, episode):
        from backend.lwm import review
        _registry(episode)
        (episode / "07-draft.md").write_text("## Movement 1\n\nHe walked out alone.\n")
        c = _client({"findings": [{"quote": "He walked out alone.", "problem": "unsourced",
                                   "severity": "material"}]})
        r = review.run(episode, client=c)
        assert set(r["by_reviewer"]) == set(review.REVIEWERS)
        assert r["counts"]["fact-integrity"] == 1
        assert all(f["reviewer"] in review.REVIEWERS for f in r["findings"])
        md = review.render(r, {"summary": {"flagCount": 0}, "flags": [], "counters": []})
        assert "none of them is homework for Maz" in md

    def test_a_reviewer_that_fails_is_recorded_not_swallowed(self, episode):
        from backend.lwm import review
        _registry(episode)
        (episode / "07-draft.md").write_text("## Movement 1\n\ntext\n")
        c = MagicMock()
        c.generate_structured.side_effect = RuntimeError("seat unreachable")
        r = review.run(episode, client=c)
        assert set(r["failed_reviewers"]) == set(review.REVIEWERS)

    def test_lint_findings_survive_structured(self, episode, workspace):
        """§12: the detector is untouched; its findings stop being truncated."""
        import shutil as _shutil

        from backend.lwm import edit
        real = Path.home() / ".openclaw/workspace/pipeline/lint/regression-tier1.mjs"
        if not real.exists():
            pytest.skip("the tier-1 detector lives in the pipeline workspace; not present here")
        (workspace / "pipeline" / "lint").mkdir(parents=True, exist_ok=True)
        _shutil.copy(real, workspace / "pipeline" / "lint" / "regression-tier1.mjs")
        draft = episode / "07-draft.md"
        draft.write_text(
            "## Movement 1\n\n" + ("It didn't just change the case, it changed everything. "
                                   "In other words, this was not merely a trial. ") * 6)
        out = edit.run_lint(draft)
        assert isinstance(out, dict)
        assert out["ran"] is True
        assert "flags" in out and "counters" in out and "summary" in out
        assert out["summary"]["flagCount"] >= 1
        assert any(f.get("line") and f.get("id") for f in out["flags"])


class TestTwoCycleTripwire:
    def test_the_tripwire_stops_writing_and_names_the_upstream_owner(self, episode):
        from backend.lwm import edit
        _registry(episode)
        (episode / "07-draft.md").write_text("## Movement 1\n\nHe walked out alone.\n")

        def structured(prompt, schema, system, max_tokens):
            props = set(schema.get("properties", {}))
            if "findings" in props:
                return {"findings": [
                    {"quote": "He walked out alone.", "problem": "nothing supports this",
                     "severity": "material"}]}, {}
            return {"pairs": []}, {}
        c = MagicMock()
        c.generate_structured.side_effect = structured

        r = edit.edit_train(episode, c)
        assert r["cycles"] <= edit.EDIT_CYCLE_CAP
        t = r["tripwire"]
        assert t and t["stop_writing"] is True
        assert any(route["owner"] for route in t["routes"])
        assert "Draft 7" in t["rule"]
        assert (episode / "outputs" / "tripwire.json").exists()
        assert "STOP WRITING" in (episode / "08-edit-log.md").read_text()

    def test_a_clean_draft_does_not_trip_the_wire(self, episode):
        from backend.lwm import edit
        _registry(episode)
        (episode / "07-draft.md").write_text("## Movement 1\n\nHe walked out alone.\n")
        c = _client({"findings": []})
        c.generate_structured.side_effect = lambda prompt, schema, system, max_tokens: (
            {"findings": []} if "findings" in schema.get("properties", {}) else {"pairs": []}, {})
        r = edit.edit_train(episode, c)
        assert r["tripwire"] is None
        assert r["cycles"] == 1, "a clean cycle stops; the cap is for the other case"


class TestGripGates:
    def test_gate_a_asks_the_richer_questions_and_records_the_route(self, episode):
        from backend.lwm import writing
        (episode / "05-outline.md").write_text("an outline")
        reader = _client({"gripped": False, "drop_off_point": "beat 2", "note": "lost me",
                          "route": "evidence", "buried_information": "the dig is late",
                          "answers": [{"question": q, "answer": "a"}
                                      for q in writing.GATE_A_QUESTIONS]})
        r = writing.grip_gate(episode, "05-outline.md", "6 grip gate A", clients=[reader] * 3)
        assert r["pass"] is False and r["routes"] == ["evidence"] * 3
        md = (episode / "06-grip-gate-a.md").read_text()
        for q in writing.GATE_A_QUESTIONS:
            assert q in md
        assert "targeted research" in md

    def test_gate_b_asks_its_own_richer_questions(self, episode):
        from backend.lwm import writing
        (episode / "07-draft.md").write_text("prose")
        reader = _client({"gripped": True, "held_best": "the whiskey line", "note": "n",
                          "felt_invented": "nothing", "spoken_or_written": "spoken",
                          "answers": [{"question": q, "answer": "a"}
                                      for q in writing.GATE_B_QUESTIONS]})
        writing.grip_gate(episode, "07-draft.md", "9 grip gate B", clients=[reader] * 3)
        md = (episode / "09-grip-gate-b.md").read_text()
        for q in writing.GATE_B_QUESTIONS:
            assert q in md
        assert "felt invented" in md and "spoken or written" in md


class TestFlowOrder:
    def test_the_ledger_runs_research_before_the_angle(self):
        from backend.lwm import ledger
        order = [s for s, _ in ledger.STAGES]
        assert order.index("3 brief") < order.index("1 angle")
        assert order.index("4b briefing") < order.index("1 angle")
        assert order.index("1 angle") < order.index("1b packaging")
        assert order.index("1b packaging") < order.index("4c story architecture")
        assert order.index("4c story architecture") < order.index("5 outline")

    def test_macro_states_are_the_creator_flow(self):
        from backend.lwm import ledger
        assert ledger.MACRO_STATES[:9] == ["INPUT", "RESEARCH", "BRIEF", "ANGLE", "PACKAGING",
                                           "STORY", "SCRIPT", "FINAL CHECK", "PRODUCTION"]
        for _stage, macro in ledger.STAGES:
            assert macro in ledger.MACRO_STATES

    def test_pre_patch_stage_keys_still_resolve(self, episode):
        from backend.lwm import ledger
        ledger.update_row(episode, "1 angle + packaging", status="chosen", notes="via old key")
        rows = ledger.read_rows(episode)
        assert rows["1 angle"].status == "chosen"
        assert rows["1 angle + packaging"].notes == "via old key"

    def test_migration_is_idempotent_and_loses_nothing(self, episode):
        from backend.lwm import ledger
        ledger.update_row(episode, "3 brief", status="done", notes="research ran")
        first = ledger.rewrite_table(episode)
        text = (episode / "STAGE-LEDGER.md").read_text()
        second = ledger.rewrite_table(episode)
        assert (episode / "STAGE-LEDGER.md").read_text() == text
        assert second["created"] == 0
        assert ledger.read_rows(episode)["3 brief"].notes == "research ran"
        assert first["carried"] >= 1
