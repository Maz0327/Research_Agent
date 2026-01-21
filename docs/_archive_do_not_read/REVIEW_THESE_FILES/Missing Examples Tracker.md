# Missing Example Artifacts — Tracker

This document tracks all remaining example artifacts required to fully specify the Research Agent system and prevent output drift.

---

## Completed Example Artifacts

- [x] Doc 0 — Source Ledger (conceptual + structure)
- [x] Doc 1 — Jump-Start Research Directions
- [x] Doc 2 — Semantic Research Brief
- [x] Producer Packet — Creative Activation Output
- [x] Content Blueprint — SOC-Ready Execution Output

---

## Still Missing (To Be Created)

### 1. Degraded Output Example (CRITICAL)
**Purpose:** Show correct behavior when transcripts are unavailable.

**Must Demonstrate:**
- Supadata failure
- Captions unavailable
- Gemini video-only analysis
- Explicit degradation disclosure
- Reduced confidence without collapse

---

### 2. Thin-but-Acceptable Output Example (CRITICAL)
**Purpose:** Teach system that sparse output is valid when sources are weak.

**Must Demonstrate:**
- Few sources, same POV
- No padding or forced themes
- Confidence downgraded
- Strong next steps despite thin data

---

### 3. Conflicting Sources Example (IMPORTANT)
**Purpose:** Demonstrate how contradictions are surfaced but not resolved.

**Must Demonstrate:**
- Direct contradiction between sources
- Tension clearly labeled
- No synthesis or forced resolution

---

### 4. Artifact Index / Confidence Summary Example (IMPORTANT)
**Purpose:** Show how artifacts are presented to user with trust signals.

**Must Demonstrate:**
- Artifact list
- Confidence indicators
- Warnings surfaced clearly

---

### 5. Minimal API Response Example (IMPORTANT)
**Purpose:** Anchor frontend/backend contract.

**Must Demonstrate:**
- Job status
- Artifact availability
- Warning surface

---

## Next Steps

Priority order:
1. Degraded Output Example
2. Thin-but-Acceptable Output Example
3. Conflicting Sources Example
4. Artifact Index Example
5. Minimal API Response Example

---

**End of Tracker**

