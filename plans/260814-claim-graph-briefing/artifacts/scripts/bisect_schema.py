"""Find what actually blows up the structured-output grammar."""
import copy
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")

import anthropic

from backend.models.claim_graph import api_json_schema

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def probe(label, schema):
    size = len(json.dumps(schema))
    try:
        client.messages.create(
            model="claude-sonnet-5",
            max_tokens=16,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": "hi"}],
        )
        print(f"  OK    ({size:>5} chars)  {label}")
        return True
    except anthropic.APIStatusError as e:
        msg = str(e.message)
        short = "grammar too large" if "grammar is too large" in msg else msg[:110]
        print(f"  FAIL  ({size:>5} chars)  {label}  -> {short}")
        return False


full = api_json_schema()
probe("full ClaimGraph", full)

# Drop one top-level property at a time.
print("\n-- drop one top-level property --")
for prop in list(full["properties"].keys()):
    s = copy.deepcopy(full)
    del s["properties"][prop]
    s["required"] = [r for r in s["required"] if r != prop]
    probe(f"without {prop}", s)

# Claims only, then claims with fields removed.
print("\n-- claims-only, shedding claim fields --")
base = copy.deepcopy(full)
base["properties"] = {"claims": full["properties"]["claims"]}
base["required"] = ["claims"]
probe("claims only", base)

claim_props = list(full["$defs"]["Claim"]["properties"].keys())
for prop in claim_props:
    s = copy.deepcopy(base)
    del s["$defs"]["Claim"]["properties"][prop]
    s["$defs"]["Claim"]["required"] = [
        r for r in s["$defs"]["Claim"]["required"] if r != prop
    ]
    probe(f"claims only, no Claim.{prop}", s)

# How many string fields can one flat object carry?
print("\n-- flat object scaling --")
for n in (5, 10, 20, 40):
    s = {
        "type": "object",
        "additionalProperties": False,
        "properties": {f"f{i}": {"type": "string"} for i in range(n)},
        "required": [f"f{i}" for i in range(n)],
    }
    probe(f"{n} plain string fields", s)

print("\n-- nullable union scaling --")
for n in (5, 10, 20):
    s = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            f"f{i}": {"anyOf": [{"type": "string"}, {"type": "null"}]} for i in range(n)
        },
        "required": [f"f{i}" for i in range(n)],
    }
    probe(f"{n} nullable string fields", s)

print("\n-- enum scaling --")
for n in (2, 5, 10):
    s = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            f"f{i}": {"enum": ["alpha", "beta", "gamma", "delta"]} for i in range(n)
        },
        "required": [f"f{i}" for i in range(n)],
    }
    probe(f"{n} enum fields", s)
