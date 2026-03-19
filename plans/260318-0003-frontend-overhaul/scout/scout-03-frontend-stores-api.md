# Scout: Frontend Stores, API & Types

## Zustand Stores (6)

| Store | Key State | Actions |
|-------|-----------|---------|
| `jobs.ts` (59KB) | jobs, jobDetails, isLoading, error, sortOrder, searchQuery | fetchJobs, getJobDetails, createJob, deleteJob, cancelJob, iterate |
| `settings.ts` | settings: UserSettings, folderValidation, usernameCheck | fetchSettings, updateSettings, validateFolder |
| `admin.ts` | stats, users, jobs, errorLogs, pagination | fetchStats, fetchUsers, banUser, deleteJob |
| `style-guides.ts` | guides[], templates{} | CRUD + setDefault |
| `voice-profiles.ts` | profiles[] | CRUD |
| `ui-preferences.ts` | createPanelCollapsed, jobListView | toggle/set (localStorage persisted) |

## API Layer

- `lib/api-client.ts`: `apiFetch()` (base), `authFetch()` (+Bearer), `parseJsonResponse()`
- Base URL: `NEXT_PUBLIC_API_URL` (default localhost:8000)
- HTTPS enforced in prod
- 30s default timeout via AbortController
- No React Query/SWR — pure Zustand polling

## Auth: `lib/supabase.ts`

Magic link, email/password, Google OAuth. `getAccessToken()` → Bearer token.

## Key Types (`types/documents.ts`, 473 lines)

- KeyPoint, Theme, Gap, Tension, SpeculativeObservation
- Doc 0: SourceLedgerData, Doc 1: JumpStartData, Doc 2: SemanticBriefData
- Doc 3: ProducerPacketData, Doc 5: ScriptData, Doc 6: SocialKitData, Doc 7: BlogPostData
- Union: `DocumentData`

## Hooks

- `useETA.ts` — dynamic job ETA calc, stage-based estimation, 1s updates

## Utilities

| File | Purpose |
|------|---------|
| `lib/constants.ts` | API_URL, polling intervals, stage labels (40+), validation limits |
| `lib/error-utils.ts` | formatError, formatApiError (Pydantic errors) |
| `lib/validation.ts` | prompt, username, folder URL, email validators |
| `lib/document-formatters.ts` (16.8KB) | Markdown/JSON doc rendering |
| `lib/pdf-export.ts` | PDF generation |
| `lib/docx-export.ts` | DOCX generation |
| `lib/intent-router.ts` | Navigation logic for job actions |
| `lib/iterate-intent.ts` | Iterate mode selection |
| `contexts/ThemeContext.tsx` | light/dark/system theme, localStorage |

## Data Flow

```
Component → useStore(Zustand) → getAccessToken(Supabase) → authFetch(Bearer) → Backend API → parseJsonResponse → set(state) → re-render
```

## API Endpoints

| Store | Endpoints |
|-------|-----------|
| Jobs | `/jobs`, `/jobs/{id}`, `/jobs/{id}/iterate` |
| Settings | `/settings`, `/settings/validate-folder`, `/settings/check-username` |
| Admin | `/admin/stats`, `/admin/users`, `/admin/jobs`, `/admin/errors` |
| Style Guides | `/style-guides`, `/style-guides/{id}`, `/style-guides/templates` |
| Voice Profiles | `/voice-profiles`, `/voice-profiles/{id}` |
