"""Regenerate the Packer briefing's Disputes and Record sections.

Not a patch of the stored file: this re-runs the real selection and passes
against the stored key points, tensions and harvest, so what lands is what the
pipeline now produces rather than a hand-edit that would drift from the code.
"""
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, "/Users/mazbot/Research_Agent-v3work")

from backend.config import get_settings
from backend.integrations.structured_client import get_structured_client
from backend.models.briefing import Briefing, Dispute
from backend.pipeline.briefing_passes import (
    build_record_entries,
    run_blurb_pass,
    run_dispute_pass,
    run_opposition_pass,
)
from backend.pipeline.briefing_routing import (
    collapse_same_event,
    evidence_chip,
    route_facts,
    select_disputes,
    source_display_name,
    strip_source_voice,
)
from backend.pipeline.formatters.briefing_renderer import (
    render_briefing_html,
    render_briefing_markdown,
)

BASE = "/Users/mazbot/Research_Agent-v3work/scratchpad/e2e_films"

doc0 = json.load(open(f"{BASE}/packer_r3_doc_0.json"))["data"]
doc1 = json.load(open(f"{BASE}/packer_r3_doc_1.json"))["data"]
doc2 = json.load(open(f"{BASE}/packer_r3_doc_2.json"))
briefing = Briefing.model_validate(doc2["data"])

source_names = {
    s["source_id"]: source_display_name(s) for s in doc0["sources"]
}
key_points = {kp["key_point_id"]: kp for kp in doc1["key_points"]}
tensions = [SimpleNamespace(**t) for t in doc1["tensions"]]

raw = json.load(open(f"{BASE}/packer_r3_harvest.json"))["harvest"]
inventory = [
    {"fact_id": f"{src}:F_{i}", "source_id": src, "text": strip_source_voice(text)}
    for src, facts in raw.items()
    for i, text in enumerate(facts, 1)
]
print(f"{len(inventory)} facts, {len(tensions)} tensions, {len(key_points)} key points")

client = get_structured_client(get_settings().model_distill)

# --- Disputes ---------------------------------------------------------------
specs = select_disputes(
    tensions=tensions,
    inventory=inventory,
    key_points=key_points,
    source_names=source_names,
    opposition_check=lambda pairs: run_opposition_pass(client, pairs),
)
print(f"\ndisputes selected: {len(specs)} (was 8)")

disputes = []
for spec in specs:
    try:
        case_for, case_against = run_dispute_pass(
            client,
            claim=spec["claim"],
            holders=spec["holders"],
            evidence_for=spec["evidence_for"],
            evidence_against=spec["evidence_against"],
            source_ids_for=spec["source_ids_for"],
            source_ids_against=spec["source_ids_against"],
        )
    except ValueError as e:
        print(f"  skipped: {e}")
        continue
    disputes.append(
        Dispute(
            claim=spec["claim"],
            holders=spec["holders"],
            chip=evidence_chip(
                spec["source_ids_for"] + spec["source_ids_against"],
                contested=bool(spec["evidence_against"]),
                verifiable=spec.get("verifiable", True),
            ),
            case_for=case_for,
            case_against=case_against,
        )
    )
    print(f"  [{disputes[-1].chip.label}] {spec['claim'][:66]}")
    print(f"      {spec['holders'][:90]}")

# --- Record -----------------------------------------------------------------
routed = route_facts(inventory, [d.claim for d in disputes])
dated, collapsed = collapse_same_event(routed["record"])
print(f"\nrecord: {len(routed['record'])} dated -> {len(dated)} entries")
for fact in collapsed:
    print(f"  collapsed ({fact['dropped_because']}): {fact['text'][:74]}")

blurbs = run_blurb_pass(client, [f["text"] for f in dated])
record = build_record_entries(dated, blurbs)

briefing.disputes = disputes
briefing.record = record

doc2["data"] = briefing.model_dump(mode="json")
markdown = render_briefing_markdown(briefing)
doc2["markdown"] = markdown
json.dump(doc2, open(f"{BASE}/packer_r3_doc_2.json", "w"), indent=1)
open(f"{BASE}/PACKER-BRIEFING.md", "w").write(markdown)
open(f"{BASE}/PACKER-BRIEFING.html", "w").write(render_briefing_html(briefing))
print(f"\nwrote doc_2, .md ({len(markdown.split()):,} words) and .html")
