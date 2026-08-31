"""Rebuild only the cast of the stored Packer briefing.

The prose is already written and paid for; what was wrong was who ended up in
"The Players". This re-runs pass 6 alone against the finished document — the
cast read, then the three card passes — and rewrites doc_2 plus both renders.
Nothing else in the briefing is regenerated.
"""
import json
import sys

sys.path.insert(0, "/Users/mazbot/Research_Agent-v3work")

from backend.config import get_settings
from backend.integrations.structured_client import get_structured_client
from backend.models.briefing import Briefing
from backend.pipeline.briefing_cast import build_cast
from backend.pipeline.formatters.briefing_renderer import (
    render_briefing_html,
    render_briefing_markdown,
)

BASE = "/Users/mazbot/Research_Agent-v3work/scratchpad/e2e_films"

doc2 = json.load(open(f"{BASE}/packer_r3_doc_2.json"))
briefing = Briefing.model_validate(doc2["data"])

raw = json.load(open(f"{BASE}/packer_r3_harvest.json"))["harvest"]
inventory = [
    {"fact_id": f"{src}:F_{i}", "source_id": src, "text": text}
    for src, facts in raw.items()
    for i, text in enumerate(facts, 1)
]
print(f"inventory: {len(inventory)} facts")

# Exactly the text the stage assembles for pass 6.
section_prose = {
    "read": " ".join(
        [briefing.read.lede] + [p.text for p in briefing.read.paragraphs]
    ),
    "files": " ".join(f.body for f in briefing.files),
    "record": " ".join(e.what for e in briefing.record),
    "disputes": " ".join(
        f"{d.claim} {d.holders} {d.case_for.text} {d.case_against.text}"
        for d in briefing.disputes
    ),
}
brief_text = "\n\n".join(section_prose.values())
print(f"brief_text: {len(brief_text.split()):,} words")

client = get_structured_client(get_settings().model_distill)
briefing.players, briefing.organisations, briefing.places = build_cast(
    client, brief_text, inventory, job_id="packer-r3"
)
print(
    f"cards written: {len(briefing.players)} people / "
    f"{len(briefing.organisations)} organisations / {len(briefing.places)} places"
)

doc2["data"] = briefing.model_dump(mode="json")
markdown = render_briefing_markdown(briefing)
doc2["markdown"] = markdown
json.dump(doc2, open(f"{BASE}/packer_r3_doc_2.json", "w"), indent=1)
open(f"{BASE}/PACKER-BRIEFING.md", "w").write(markdown)
open(f"{BASE}/PACKER-BRIEFING.html", "w").write(render_briefing_html(briefing))
print(f"wrote doc_2, .md ({len(markdown.split()):,} words) and .html")
