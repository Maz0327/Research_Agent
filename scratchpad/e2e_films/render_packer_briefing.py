"""Read-only adapter: stored doc_2 JSON -> PACKER-BRIEFING.md via the
production renderer (render_briefing_markdown). Appends the corpus-balance
section the markdown renderer omits by design (D-025). No production code
is touched."""
import json
import sys

sys.path.insert(0, "/Users/mazbot/Research_Agent-v3work")

from backend.models.briefing import Briefing
from backend.pipeline.formatters.briefing_renderer import render_briefing_markdown

BASE = "/Users/mazbot/Research_Agent-v3work/scratchpad/e2e_films"

doc2 = json.load(open(f"{BASE}/packer_r3_doc_2.json"))
briefing = Briefing.model_validate(doc2["data"])
md = render_briefing_markdown(briefing)

stored = doc2.get("markdown") or ""
print("re-render matches stored markdown:", md == stored)

# Corpus balance: the markdown export drops it; add it so nothing in doc_2
# is silently missing from the readable document.
bal = doc2["data"].get("corpus_balance") or {}
extra = []
if bal:
    extra += ["## 9. Corpus Balance", ""]
    if bal.get("date_range"):
        extra.append(f"- Sources span **{bal['date_range']}**.")
    stances = bal.get("stance_counts") or {}
    if stances:
        parts = ", ".join(f"{n} {stance}" for stance, n in stances.items())
        extra.append(f"- Stance mix across the corpus: {parts}.")
    if bal.get("network_note"):
        extra.append(f"- {bal['network_note']}")
    extra.append("")

out = md.rstrip() + "\n\n" + "\n".join(extra) if extra else md
open(f"{BASE}/PACKER-BRIEFING.md", "w").write(out.rstrip() + "\n")
print("wrote PACKER-BRIEFING.md,", len(out.split()), "words")
