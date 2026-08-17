"""Download the fixture's stored documents from Supabase Storage."""
import json
import sys

from dotenv import load_dotenv

load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")

from backend.integrations.supabase_storage import get_storage_client

JOB_ID = "51c97825-4840-44e8-b93a-593688b31a07"
SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"

client = get_storage_client()
print("storage client:", type(client).__name__)
print("methods:", [m for m in dir(client) if not m.startswith("_")])

for n in range(4):
    path = f"{JOB_ID}/doc_{n}.json"
    try:
        raw = client.download_document(path)
    except Exception as e:
        print(f"doc_{n}: FAIL {type(e).__name__}: {e}")
        continue
    out = f"{SCRATCH}/doc_{n}.json"
    with open(out, "w") as f:
        json.dump(raw, f, indent=2, default=str)
    top = list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__
    print(f"doc_{n}: OK  {len(json.dumps(raw, default=str))} chars  keys={top}")
