"""Do embedding-similarity pairs surface the brief's connections, or just restatements?"""
import json, sys
from dotenv import load_dotenv
load_dotenv("/Users/mazbot/Documents/GitHub/Research_Agent/.env")
sys.path.insert(0, "/Users/mazbot/Documents/GitHub/Research_Agent")
from openai import OpenAI
import numpy as np

SCRATCH = "/private/tmp/claude-502/-Users-mazbot/b4d89ac3-5bf5-48df-927e-e6ef800f4cd2/scratchpad"
doc2 = json.load(open(f"{SCRATCH}/doc_2.json"))["data"]
kps = [(kp["source_ids"][0] if kp["source_ids"] else "?", kp["statement"]) for kp in doc2["key_points"]]

client = OpenAI()
resp = client.embeddings.create(model="text-embedding-3-small", input=[s for _, s in kps])
vecs = np.array([d.embedding for d in resp.data])
vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
sim = vecs @ vecs.T

# Top cross-source pairs (exclude same source, exclude the known dup pair 7/8)
pairs = []
for i in range(len(kps)):
    for j in range(i + 1, len(kps)):
        si, sj = kps[i][0], kps[j][0]
        if si == sj or {si, sj} == {"SRC_7", "SRC_8"}:
            continue
        pairs.append((sim[i, j], i, j))
pairs.sort(reverse=True)

print("TOP 8 cross-source pairs by embedding similarity:")
for s, i, j in pairs[:8]:
    print(f"\n  {s:.2f}  [{kps[i][0]}] {kps[i][1][:95]}")
    print(f"        [{kps[j][0]}] {kps[j][1][:95]}")

# Where does the brief's best connection rank? (post-production commitment x JP practical approach)
import re
post = [k for k, (_, t) in enumerate(kps) if re.search(r"post-production|in post|intentionality", t, re.I)]
jp = [k for k, (_, t) in enumerate(kps) if re.search(r"animatronic|practical", t, re.I)]
best, rank_of = None, None
ranked = [(s, i, j) for s, i, j in pairs]
for r, (s, i, j) in enumerate(ranked):
    if (i in post and j in jp) or (j in post and i in jp):
        best, rank_of = s, r + 1
        break
print(f"\nBrief's key connection (fix-it-in-post x JP practical): rank {rank_of} of {len(ranked)}, sim {best:.2f}" if best else "\nconnection pair not present in key points")
