# Phase 3 Handoff Document — Creator Power Tools

**Generated:** 2026-03-15
**Branch:** `feature/kimi-visual-analysis-and-optimizations`
**Project:** `/Users/maz/Documents/github/Research_Agent`

---

## What's Been Done (Phase 1 & Phase 2 — ALL COMPLETE)

### Phase 1 ✅ (Frontend-only, no new endpoints)
- **1A** Unified Smart Input — `StartInput.tsx` + `intent-router.ts` (rotating placeholders, intent detection)
- **1B** Reading Guide — `ReadingGuide.tsx` banner, numbered badges on artifact cards (Doc 3 = "1 · Start Here")
- **1C** Natural Language Iterations — `RefinePanel.tsx` replaces `IterateDialog`, `iterate-intent.ts` infers mode
- **1D** Inline Document Actions — `InlineActionBar.tsx` with "Dig deeper" / "Copy for script" / "Different angle"
- **1E** Batch Source Entry — Batch URL paste in `AddSourceModal.tsx`
- **1F** Auto-Trigger Quick Brief — `SearchApprovalView.tsx` auto-calls `fetchQuickBrief`

### Phase 2 ✅ (1 new endpoint, 1 Supabase table, CRUD endpoints)

**Implementation order was: 2E → 2D → 2C → 2B → 2A**

- **2E** Hook Options as Visual Cards — `HookOptionCard.tsx` with hook type badges (Question=blue, Contradiction=red, Stat-Lead=green, Story-Open=purple), copy button, selectable state
- **2D** "Why It Matters" Prominence — Standalone `WhyItMattersSection` with amber accent in Creator Brief. "So what?" labels in Semantic Brief theme cards
- **2C** ADHD Document Formatting — `BoldFirstSentence.tsx`, `CollapsibleSection.tsx`, section progress indicators ("Section X of Y"), progressive disclosure (non-essential sections collapsed by default)
- **2B** Style Guide System — Full CRUD backend (`style_guide_routes.py`), Supabase table (`style_guides`), Zustand store (`style-guides.ts`), Settings UI with 3 templates (Deep Dive Explainer, Investigative Storyteller, Casual Conversationalist)
- **2A** Brainstorm Pre-Stage — `POST /jobs/brainstorm` endpoint (synchronous Gemini Flash), `BrainstormPanel.tsx` with angle cards, vocabulary pills, key questions. Dashboard routes topic intent through brainstorm first.

**Pending from Phase 2:**
- ⚠️ Supabase migration `025_add_style_guides.sql` needs to be run against the database
- ⚠️ Backend CORS allows `localhost:3000` but frontend runs on port 3002 — may need updating

---

## Phase 3: Creator Power Tools — THE WORK TO DO

### Implementation Order: 3A → 3B → 3C → 3D → 3E

**3F (Inline Edit) is explicitly marked as v2 — do NOT implement it.**

---

### Task 3A: Creator Analysis Mode

**What it is:** When StartInput detects a creator analysis intent (e.g., "analyze Johnny Harris's style"), accept 3-5 YouTube URLs from the target creator, run through pipeline with specialized extraction prompt, and output a "Creator Style Profile" document.

**Output document sections:**
- Hook patterns (question hooks, stat hooks, story hooks — with frequency counts)
- Narrative structure (Hero's Journey? 5-act? Problem-solution? — mapped to the Kova framework)
- Vocabulary fingerprint (most-used phrases, unique expressions, filler words)
- Aesthetic keywords (typography, color palette, B-roll style, music tone, pacing descriptors)
- Tone descriptors (formal/casual spectrum, humor usage, emotional range)

**Key feature:** One-click "Save as style guide" — saves the Creator Style Profile as a new personal style guide in the `style_guides` table from Phase 2B.

**Backend work:**
- New extraction prompt focused on style analysis (pacing, hooks, structure, vocabulary)
- New route or mode in existing pipeline for creator analysis jobs
- Uses existing transcription infrastructure (Supadata → Whisper fallback chain)

**Frontend work:**
- Creator analysis intent already detected by `intent-router.ts` — needs to route to a URL input view (accept 3-5 YouTube URLs)
- New renderer for Creator Style Profile document
- "Save as Style Guide" button that calls the style guide CRUD API

**Integration with existing systems:**
- The `style_guides` table and CRUD endpoints from Phase 2B are already built
- The dashboard `handleStartInputSubmit` already has a `creator_analysis` intent case
- Transcription already works via Supadata/Whisper

---

### Task 3B: Content Structure Suggestions (Five-Act Story Arc)

**What it is:** Add a "Suggested Structure" section to Creator Brief based on topic type, using the Five-Act Story Arc framework.

**Structure mapping:**
- Investigation topics → **Cold Open arc:** Single damning detail → Surface story → Evidence trail → The pattern → What happens next
- Controversy topics → **Multiple Perspectives arc:** The claim → Side A evidence → Side B evidence → What's actually true → Why it matters
- Profile topics → **Hero's Journey arc:** Hook (show the payoff) → Origin/conflict → The build/process → Resolution/transformation → CTA
- Explainer topics → **Discovery arc:** The question → Why it's hard to answer → The mechanism → Implications → Open thread

**Each structure suggestion includes:**
- The arc name and 5 beat descriptions customized to the topic
- Which Doc 2 claims/themes map to each beat
- A one-paragraph "if you were scripting this" preview

**Files:**
- Modified: `backend/pipeline/stages/creator_brief_stage.py` (structure inference logic — note: the plan says `creator_brief_assembly.py` but the actual file is `creator_brief_stage.py`)
- New: `frontend/components/document/StoryArcCard.tsx`
- Modified: `frontend/components/document/CreatorBriefRenderer.tsx`

---

### Task 3C: Active Wait with Narrated Loading States

**What it is:** Replace passive spinners with real-time narrated pipeline stages showing what's actually happening.

**Narrated stage labels:**
- `source_identity` (5%): "Analyzing your sources... identifying content types"
- `semantic_extraction` (20%): "Reading source 3 of 6... extracting claims and key points"
- `semantic_validation` (35%): "Verifying claims... checking confidence levels"
- `gap_analysis` (50%): "Looking for gaps in the research... what's missing?"
- `semantic_synthesis` (65%): "Finding patterns across sources... 4 themes emerging"
- `document_assembly` (80%): "Building your documents... formatting for readability"
- `creator_brief` (87%): "Writing your Creator Brief... crafting hooks and story angles"
- `completion` (95%): "Final checks... almost ready"

**Partial result previews (progressive reveal as stages complete):**
- After `source_identity`: Source summary card — "6 sources found: 3 YouTube, 2 articles, 1 research paper"
- After `semantic_extraction`: Top 3 claims preview with significance indicators
- After `semantic_synthesis`: Theme preview — "3 themes found" with one-line summaries
- After `creator_brief`: Hook preview — show the top hook option before full doc loads

**"While you wait" suggestions:**
- Related topics the user might want to explore next
- Tips for using the output ("Pro tip: start with the Creator Brief")

**Current state of progress tracking:**
- `JobProgressPanel.tsx` already has a vertical timeline with stage labels and ETA counter
- `SEMANTIC_STAGES` array already defines the pipeline stage order
- `ArtifactCardGrid.tsx` already maps stages to per-card progress
- The backend already emits `stage` and `progress` fields via `update_job()`

**Files:**
- Modified: `frontend/components/job-detail/JobProgressPanel.tsx` (narrated labels, partial results)
- New: `frontend/components/job-detail/PartialResultsPreview.tsx`
- Modified: `frontend/pages/jobs/[id].tsx` (integrate partial results)

**Note:** The narrated labels may partially overlap with what `getStageLabel()` and `getStageDescription()` in `lib/constants.ts` already provide. Check those first.

---

### Task 3D: Progressive Document Reveal

**What it is:** When a job completes, show Creator Brief (Doc 3) as the hero document at the top, with supporting documents in a collapsed accordion below.

**Layout:**
- **Hero view:** Creator Brief (Doc 3) renders full-width at the top, expanded by default
- **Supporting documents** appear below in collapsed accordion:
  - "Deep Research" (Doc 2) — expandable
  - "Next Steps" (Doc 1) — expandable
  - "All Sources" (Doc 0) — expandable
  - "Production Notes" (Doc 4) — expandable, if available
- Current grid view remains as option ("View all documents" toggle)
- Reading Guide banner (Phase 1B) reinforces hierarchy

**Current state:**
- `ArtifactCardGrid.tsx` renders all docs in a grid with reading order badges (Doc 3 = "1 · Start Here")
- `CreatorBriefView.tsx` already exists as a standalone full-page view of Doc 3
- `ReadingGuide.tsx` banner already exists above the artifact grid
- `CollapsibleSection.tsx` (from Phase 2C) can be reused for accordion behavior

**Files:**
- Modified: `frontend/pages/jobs/[id].tsx` (hero + accordion layout)
- Modified: `frontend/components/job-detail/ArtifactCardGrid.tsx` (add toggle)
- New: `frontend/components/job-detail/DocumentAccordion.tsx`

---

### Task 3E: Export & Sharing Redesign

**What it is:**
- Persistent export toolbar at top of document viewer (not buried in dropdown)
- Section-level copy buttons
- "Share snippet" per section (formats for social media, truncated to 280 chars)
- Quick share link generation

**Current state:**
- Export routes already exist (`backend/app/routes/export_routes.py` — 15KB)
- Share routes already exist (`backend/app/routes/share_routes.py` — 16KB)
- These just need better frontend integration

---

### Task 3F: Inline Edit / Targeted Changes — DO NOT IMPLEMENT

Explicitly marked as v2. Requires:
- Backend support for section-level iteration (currently whole-document only)
- Diffing logic to merge section updates
- Complex frontend selection + floating toolbar UX

---

## Critical Architecture Rules

These are NON-NEGOTIABLE. Read `/Users/maz/Documents/github/Research_Agent/.claude/rules/architecture.md` for full details.

1. **Source Isolation** — Each source extracted in SEPARATE LLM call. Never combine.
2. **Confidence Ceilings** — transcript_grounded=HIGH, caption_grounded=MEDIUM, video_only=LOW, article_fetched=HIGH
3. **Pipeline Order** — INGESTION → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY. Never skip/reorder.
4. **Gemini JSON Mode** — All Gemini calls use `response_mime_type: "application/json"` with `response_schema: PydanticModel`
5. **Temperature** — Extraction: 0.1, Synthesis: 0.2, Creator Brief: 0.3, Brainstorm: 0.4
6. **Pydantic models for Gemini response_schema MUST have NO default values** — Gemini rejects schemas with defaults
7. **Provenance chain** — Every fact must trace: Doc 3 → Doc 2 → Doc 0 → source_id. Broken chain = validation failure.

---

## Implementation Rules

Read `/Users/maz/Documents/github/Research_Agent/.claude/rules/implementation.md` for full details.

1. **Sequential phases only** — Complete all tasks in order within phase
2. **Get approval before starting new phase**
3. **Commit after each task** with format: `Phase X.Y: [description]`
4. **Run tests after changes**: `pytest` (backend), `npm run lint && npm run build` (frontend)
5. **Update PROGRESS.md** after each task
6. **Archive, don't delete** — Dead code goes to `backend/archive/`

---

## Key Technical Patterns (Learned From Phase 2)

### Backend API Endpoints
```python
from fastapi import APIRouter, Depends
from backend.auth.supabase import get_active_user
from slowapi import Limiter

router = APIRouter(prefix="/style-guides", tags=["style-guides"])
limiter = Limiter(key_func=lambda request: request.state.user_id)

@router.get("/", response_model=list[StyleGuideResponse])
@limiter.limit("30/minute")
async def list_guides(request: Request, user=Depends(get_active_user)):
    ...
```

### Registering New Routes
```python
# backend/app/routes/__init__.py — add import + export
# backend/app/main.py — add app.include_router(new_router)
```

### Supabase Data Access (Backend)
```python
# Uses PostgREST via httpx — see backend/state/style_guide_store.py for pattern
from backend.config import settings

def _rest_base_url() -> str:
    return f"{settings.SUPABASE_URL}/rest/v1"

def _headers() -> dict:
    return {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
```

### Gemini Client Usage
```python
from backend.integrations.gemini_client import GeminiClient

client = GeminiClient()
result = client.generate_json(
    prompt=prompt_text,
    model="gemini-2.0-flash",
    temperature=0.4,
    response_schema=MyPydanticModel,  # NO default values in fields!
)
# result = {"data": {...}, "cost": float, "error": str|None}
```

### Zustand Store Pattern
```typescript
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';

interface MyStore {
  items: Item[];
  isLoading: boolean;
  fetchItems: () => Promise<void>;
}

export const useMyStore = create<MyStore>((set, get) => ({
  items: [],
  isLoading: false,
  fetchItems: async () => {
    set({ isLoading: true });
    const token = await getAccessToken();
    const res = await fetch(`${API_URL}/my-endpoint`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    set({ items: data, isLoading: false });
  },
}));
```

### Frontend Auth in Dev Mode
- `NEXT_PUBLIC_DISABLE_AUTH=true` auto-authenticates — no login needed for dev
- Frontend uses Supabase ONLY for auth tokens, all data flows through backend API

### Dev Server
- Config name: `research-agent-frontend` in `.claude/launch.json`
- Frontend port: 3002
- Backend: `uvicorn backend.app.main:app --reload`

---

## Existing File Structure Reference

### Document Renderers (`frontend/components/document/`)
```
CreatorBriefRenderer.tsx     — Doc 3 renderer (story core, hooks, key moments, titles, thumbnails, risk)
SemanticBriefRenderer.tsx    — Doc 2 renderer (themes, tensions, confidence, gaps)
JumpStartRenderer.tsx        — Doc 1 renderer (search directions, next steps)
SourceLedgerRenderer.tsx     — Doc 0 renderer (source list, metadata)
ResearchDocumentRenderer.tsx — Generic wrapper that routes to correct renderer
HookOptionCard.tsx           — Visual card for opening hooks (Phase 2E)
shared/
  SectionHeader.tsx          — Section header with optional "Section X of Y" progress
  CardWrapper.tsx            — Card container with colored left border
  CitationPill.tsx           — Source attribution pill
  BoldFirstSentence.tsx      — Bolds first sentence of text blocks (Phase 2C)
  CollapsibleSection.tsx     — Progressive disclosure wrapper (Phase 2C)
```

### Job Detail Components (`frontend/components/job-detail/`)
```
ArtifactCardGrid.tsx  — Grid layout with stage-to-card mapping, reading order badges
ArtifactCard.tsx      — Individual artifact card with loading states
JobProgressPanel.tsx  — Vertical timeline with stage labels, ETA counter
JobDetailHeader.tsx   — Job header with title/metadata
ReadingGuide.tsx      — "Start with Creator Brief" banner
RunSelector.tsx       — Iteration/version selector
SourceReviewPanel.tsx — Panel for reviewing sources
```

### Pipeline Stages (`backend/pipeline/stages/`)
```
source_identity.py          — Identify source types, fetch content
semantic_extraction.py      — Extract claims/key points per source (ISOLATED)
semantic_validation_stage.py — Validate confidence, enforce ceilings
gap_analysis.py             — Find research gaps
semantic_synthesis.py       — Cross-source themes and tensions
document_assembly.py        — Assemble Doc 0, 1, 2
creator_brief_stage.py      — Assemble Doc 3 (Creator Brief)
producer_stage.py           — Assemble Doc 4 (Producer Packet, optional)
quick_brief_stage.py        — Quick brief generation
booster_stage.py            — Deep dive iteration logic
cross_reference.py          — Cross-reference validation
quote_verification.py       — Verify quote accuracy
ocr_extraction.py           — OCR for image-based sources
initialization.py           — Pipeline initialization
output.py                   — Final output formatting
```

### Stores (`frontend/store/`)
```
jobs.ts             — Primary store (54KB): job CRUD, brainstorm, search, iterations, polling
settings.ts         — User settings store
style-guides.ts     — Style guide CRUD store (Phase 2B)
admin.ts            — Admin panel store
ui-preferences.ts   — UI preferences
```

### Routes (`backend/app/routes/`)
```
jobs_routes.py         — 120KB, primary job API (create, read, update, iterate, search)
search_routes.py       — Search/discovery endpoints
brainstorm_routes.py   — POST /jobs/brainstorm (Phase 2A)
style_guide_routes.py  — Style guide CRUD (Phase 2B)
settings_routes.py     — User settings
admin_routes.py        — Admin panel
export_routes.py       — Export documents (already exists — 15KB)
share_routes.py        — Share documents (already exists — 16KB)
transcripts_routes.py  — Transcript management
```

---

## Pipeline Stage Order & Progress Mapping

```
source_identity       →  5%   → "Identifying Sources"
semantic_extraction   → 20%   → "Extracting Claims"
semantic_validation   → 35%   → "Validating Claims"
gap_analysis          → 50%   → "Finding Gaps"
semantic_synthesis    → 65%   → "Connecting Themes"
document_assembly     → 80%   → "Assembling Documents"
completion            → 95%   → "Finalizing"
```

These are defined in `ArtifactCardGrid.tsx` (STAGE_ORDER, STAGE_PROGRESS) and `JobProgressPanel.tsx` (SEMANTIC_STAGES).

---

## 4 Core Documents

| Doc | Name | Hero? | Content |
|-----|------|-------|---------|
| Doc 0 | Source Ledger | No | All sources with metadata, URLs, analysis mode |
| Doc 1 | Jump-Start Directions | No | Search directions, next steps, gap-based suggestions |
| Doc 2 | Semantic Brief | No | Themes, tensions, confidence assessment, gaps |
| Doc 3 | Creator Brief | **YES** | Story core, hooks, key moments, titles, thumbnails, structure |
| Doc 4 | Producer Packet | Optional | Production notes (requires 4+ sources, 1+ HIGH ceiling) |

**Reading order for users:** Doc 3 → Doc 2 → Doc 1 → Doc 0 → Doc 4

---

## Style Guide Templates (from Phase 2B)

3 templates already exist in `backend/models/style_guide.py` → `DEFAULT_TEMPLATES`:

1. **Deep Dive Explainer** — Kurzgesagt, Wendover, MKBHD, Ali Abdaal, Veritasium style
2. **Investigative Storyteller** — Coffeezilla, Philip DeFranco, SomeOrdinaryGamers style
3. **Casual Conversationalist** — Emma Chamberlain, MrBeast narration, podcast hosts

Each has: voice, audience, vocabulary_use, vocabulary_avoid, structure, hook_style, example_tone.

---

## Brainstorm Flow (from Phase 2A)

```
Topic input → brainstormTopic() → POST /jobs/brainstorm → BrainstormPanel
  → User selects angles, vocabulary, questions
  → "Find Sources →" button
  → searchTopicAction() → SearchApprovalView → Pipeline
```

If brainstorm fails, falls back directly to `searchTopicAction()`.

---

## Five-Act Story Structure (Core Framework)

Used throughout the system (brainstorm angles, creator brief structure suggestions):

```
Hook → Conflict/Stakes → Build → Resolution → CTA
```

Brainstorm angles include full `StoryArc` objects with these 5 beats customized per angle.

---

## Verification Commands

```bash
# Frontend
cd /Users/maz/Documents/github/Research_Agent/frontend
npm run lint
npm run build

# Backend
cd /Users/maz/Documents/github/Research_Agent
source venv/bin/activate
pytest backend/tests/ -v

# Dev server
cd frontend && npm run dev  # runs on port 3002
uvicorn backend.app.main:app --reload
```
