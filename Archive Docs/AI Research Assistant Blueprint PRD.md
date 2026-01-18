

# PART I — RESEARCH AGENT PRD

## 1. Vision & North Star

**Vision:**
Research Agent makes long sources—especially video—**scannable and trustworthy** for documentary production.

**North Star Statement:**
> Make videos scannable, not summarized.

---

## 2. Target User & JTBD

**Primary User:** Documentary Creator / Producer

**JTBD:**
- Find clip-ready moments quickly.
- Trust timestamps and quotes.
- Avoid rewatching long videos.

---

## 3. Output Layers

### Layer 0 — Source Map
- Per-video metadata
- Extraction method + confidence

### Layer 1 — Grounded Research Brief (Phase 2 Ship)
- Clip Sheet (6–12 max)
- Quote Bank
- Claims Ledger (verified vs candidate)
- Timeline
- Contradictions
- Gaps

### Layer 2 — Producer Notes (Phase 3+)
- Quick take
- Suggested structure
- Landmines

All Layer 2 content must cite Layer 1.

---

## 4. Gemini-First Pipeline

### Stage 0 — Input
- 3–10 YouTube URLs

### Stage 1 — Gemini Pass 1 (Per Video)
- Extract clips, quotes, claims
- Persist per-video artifacts

### Stage 2 — Verification
- Transcript-based quote verification
- Timestamp validation

### Stage 3 — Selection & Deduping
- Enforce 6–12 clip limit
- Theme diversity

### Stage 4 — Grounded Brief Assembly

### Stage 5 — Producer Notes (Optional)

---

## 5. Verification Rules

- Quote verified only if transcript match
- Claims verified only if backed by quote
- Unverified items clearly labeled

---

## 6. Job Orchestration & Stability

- Worker-based execution
- Per-video isolation
- Incremental artifacts
- Statuses: completed, completed_with_warnings

---

## 7. Quality Gates

**Layer 1:**
- ≥4 clips
- ≥8 quotes
- ≥2 verified claims OR ≥6 candidate claims

**Layer 2:**
- ≥90% citation coverage

---

## 8. Cost Controls

- Pre-run estimate
- Warn > $5
- Hard cap at $10

---

## 9. Learning Signals (Lightweight)

- Used clips
- Ignored clips
- Export actions

Adjust ranking, not truth.

---

## 10. Out of Scope

- Research vault UI
- Automatic lead following
- Multi-platform discovery as core

---

## 11. Shared Principles (CRT ↔ Research Agent)

- Staged pipelines
- Artifact-first persistence
- Explicit uncertainty
- Human-in-the-loop learning

**Shared Backbone, Separate Brains.**

---

## Appendix A — Acceptance Criteria

A job is successful if:
- Outputs are usable without re-research
- All reasoning is traceable
- Speculation is labeled
- No job completes empty

---

## Appendix B — Definitions Glossary

- Receipt
- Observation
- Tension
- Hypothesis
- PAC
- SOC

