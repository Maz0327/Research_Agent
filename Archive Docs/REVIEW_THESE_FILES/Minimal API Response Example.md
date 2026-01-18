# Minimal API Response Example

```json
{
  "job_id": "job_12345",
  "status": "completed_with_warnings",
  "artifacts": [
    {"type": "doc0", "confidence": "high"},
    {"type": "doc1", "confidence": "medium"},
    {"type": "doc2", "confidence": "medium"},
    {"type": "producer_packet"},
    {"type": "content_blueprint"}
  ],
  "warnings": [
    "Transcript unavailable for Source 2",
    "Limited source diversity"
  ]
}
```

---

**End of Minimal API Response Example**


---

## Canonical Example Artifacts (Authoritative References)

The following example artifacts are **canonical**. They define correct system behavior and MUST be used as reference patterns during implementation, testing, and future iteration. These examples are not illustrative — they are normative.

### Core Creative Outputs
- **Producer Packet — Example Output**
  - Defines creative activation without collapsing research layers
  - Demonstrates safe semi-creative reasoning grounded in prior docs

- **Content Blueprint — Example Output**
  - Defines SOC-ready execution framing
  - Shows how research activates strategy without becoming prescriptive

### Trust & Failure-Mode Outputs (Critical)
- **Degraded Output Example**
  - Supadata transcript failure
  - No captions available
  - Gemini video-only analysis
  - Explicit confidence downgrade and user disclosure

- **Thin-but-Acceptable Output Example**
  - Limited and one-sided sources
  - Intentionally sparse output
  - No padding, no hallucinated depth

- **Conflicting Sources Example**
  - Direct contradiction surfaced
  - No forced resolution
  - Contradiction treated as research asset

### System & UX Anchors
- **Artifact Index / Confidence Summary Example**
  - Defines how artifacts are surfaced to users
  - Establishes confidence signaling and warnings

- **Minimal API Response Example**
  - Anchors frontend/backend contract
  - Defines job status, artifacts, and warning surfaces

### Implementation Rule
If an implementation decision conflicts with one of the above examples, **the example wins**. Update the spec only after updating or replacing the example artifact.

---

**End of Context Handoff Update**
