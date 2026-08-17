"""Fact-harvest pass: re-extract each fixture source into dense concrete facts."""
import json, sys, time
from dotenv import load_dotenv
load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")
from backend.integrations.anthropic_client import get_anthropic_client

SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"
doc0 = json.load(open(f"{SCRATCH}/doc_0.json"))["data"]

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"facts": {"type": "array", "items": {"type": "string"}}},
    "required": ["facts"],
}
SYSTEM = """You extract the concrete content of a text as dense, self-contained fact statements.

Each fact is ONE sentence that survives being read alone. Preserve every
specific: numbers with what they measure, names of people/films/companies and
what they did, dates, events in order, causal claims as the text makes them.

NEVER write meta-statements ("the article argues", "a perceived decline is
characterized by"). Write the content itself: "Jurassic Park contains about 50
fully digital dinosaur shots" not "the article discusses the film's limited
CGI use". If the text argues something, state the argument's content: "Deep
focus matches human vision because both eyes keep the whole scene sharp."

Extract 10 to 40 facts depending on how much the text actually contains.
Opinions and arguments in the text ARE content - state them as what they
claim. Skip filler, greetings, sponsor reads."""

harvest = {}
total_cost = 0.0
client = get_anthropic_client()
for s in doc0["sources"]:
    text = (s.get("full_text") or "")[:24000]
    if len(text) < 200:
        continue
    t0 = time.time()
    data, usage = client.generate_structured(
        prompt=f"TEXT FROM: {s.get('title')}\n\n{text}",
        schema=SCHEMA, system=SYSTEM, max_tokens=8000,
    )
    harvest[s["source_id"]] = data["facts"]
    total_cost += usage["cost"]
    print(f"{s['source_id']}: {len(data['facts'])} facts, {time.time()-t0:.0f}s")

json.dump(harvest, open(f"{SCRATCH}/harvest.json", "w"), indent=2)
import re
allf = [f for v in harvest.values() for f in v]
nums = sum(bool(re.search(r"\d", f)) for f in allf)
print(f"\nTOTAL: {len(allf)} facts, {nums} with numbers, ${total_cost:.2f}")
print("\nsamples:")
for f in allf[:3] + allf[-3:]:
    print("  -", f[:130])
