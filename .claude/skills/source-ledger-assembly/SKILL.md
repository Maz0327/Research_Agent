# Source Ledger Assembly Skill

**Skill ID:** `source-ledger-assembly`
**Auto-Trigger:** When implementing Doc 0 (Source Ledger) functionality
**Purpose:** Ensure canonical data layer integrity and blob storage patterns

---

## When This Skill Activates

- Working on Source Ledger models
- Implementing blob storage for transcripts
- Creating source index assembly
- Working with transcript provenance

---

## Doc 0 Purpose

**Source Ledger is the SINGLE SOURCE OF TRUTH**

- Preserves 100% of full context
- All other documents reference this
- No interpretation allowed here
- Immutable after write

---

## Required Structure

```python
class SourceLedger:
    topic_lock: TopicLock  # Scope definition
    sources: List[SourceEntry]  # With blob_key + metadata
    quotes: List[Quote]  # With verification flags
    claims: List[Claim]  # Descriptive only
    tag_index: Dict[str, List[str]]  # tag -> item IDs
```

### TopicLock (Required)
```python
class TopicLock:
    one_sentence: str       # Topic in one sentence
    in_scope: List[str]     # What's included
    out_of_scope: List[str] # What's excluded
    key_entities: List[str] # Core entities
```

---

## Transcript Provenance (Per Video Source)

Every video source MUST include:

```python
transcript_provenance: TranscriptProvenance = {
    "transcript_source": "supadata | youtube_captions | none",
    "transcript_status": "success | failed",
    "captions_status": "success | missing | failed",
    "gemini_analysis_mode": "transcript_grounded | caption_grounded | video_only",
    "verification_capabilities": {
        "quote_verification": True,
        "timestamp_grounding": True,
        "semantic_precision": "high | medium | low"
    },
    "notes": "Human-readable explanation"
}
```

---

## Blob Storage Pattern

```python
# Store transcript as blob
blob_key = f"transcripts/{job_id}/{source_id}.txt"
await blob_store.upload(blob_key, transcript_text)

# Reference in source entry
source_entry.transcript_blob_key = blob_key

# Retrieve via signed URL
signed_url = await blob_store.get_signed_url(blob_key)
```

---

## Minimum Requirements

| Element | Minimum | Enforcement |
|---------|---------|-------------|
| Sources with transcript | 1 | Warning if 0 |
| Quotes OR Clips | 6 OR 10 | Warning |
| Tags | 3 | Warning |

---

## ID Scheme

- Sources: `SRC_1`, `SRC_2`
- Quotes: `QUOTE_001`, `QUOTE_002`
- Clips: `CLIP_001`
- Claims: `CLM_001`

---

## Forbidden Content in Doc 0

- Interpretation
- Synthesis
- Narrative framing
- Opinions
- Recommendations
- Speculation

Doc 0 is DATA, not analysis.

---

## Checklist Before Commit

- [ ] All video sources have `transcript_provenance`
- [ ] Transcript blobs stored with correct key pattern
- [ ] `topic_lock` populated
- [ ] All IDs follow scheme
- [ ] No interpretation in skim summaries
- [ ] Full source text preserved (blob or inline)

---

## Reference Documents

- `Active Docs/REVIEW THESE FILES/Research Agent System Specification (RASS).md` - Section 3 (Doc 0)
- `Active Docs/REVIEW THESE FILES/Document Output Format Specification.md` - Doc 0 structure
- `backend/models/source.py` - TranscriptProvenance model
