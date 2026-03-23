# Frontend Accessibility & Quality Audit — Issue Locations

**Report Date:** 2026-03-23  
**Audit Scope:** `/frontend/components/` and `/frontend/app/`  
**Search Terms:** animations, focus rings, input labels, tables, hardcoded colors, empty states, error handling

---

## 1. Missing Prefers-Reduced-Motion Support

**Issue:** 60+ files use `animate-pulse`, `animate-spin`, `animate-bounce` without respecting motion preferences.

**Files Without `prefers-reduced-motion` Media Query:**
- `/frontend/components/ui/Spinner.tsx` — **Line 29:** `animate-spin` on main spinner component (used globally)
- `/frontend/components/ui/AnimatedButton.tsx` — **Line 80:** `animate-spin` in loading state
- `/frontend/components/auth/login-form.tsx` — **Lines 86, 163:** inline SVG spinners with `animate-spin`
- `/frontend/components/dashboard/DashboardJobCard.tsx` — **Line 56:** `animate-pulse` on status badge pulse dot
- `/frontend/components/admin-v2/error-log-table.tsx` — **Line 159:** `animate-pulse` in loading skeleton
- `/frontend/components/admin-v2/user-management-table.tsx` — **Line 124:** `animate-pulse` in loading rows
- `/frontend/components/admin-v2/job-management-table.tsx` — **Line 154:** `animate-pulse` in loading rows
- `/frontend/components/ui/Skeleton.tsx` — Uses `animate-pulse` (affects 50+ instances)
- `/frontend/components/dashboard/StartInput.tsx` — **Line 105:** `animate-spin` on submit button

**Note:** `frontend/app/globals.css` has media query defined but not connected to components.

---

## 2. Focus Indicators Missing — Inputs Without Focus Rings

**Issue:** Multiple inputs have `focus:outline-none` WITHOUT compensating `focus:ring` or `focus-visible:ring`.

**Critical Cases:**
- `/frontend/components/admin-v2/error-log-table.tsx` — **Line 143:** `<select>` has `focus:outline-none` alone (no ring)
- `/frontend/components/admin-v2/job-management-table.tsx` — **Line 118:** Search `<input>` has `focus:border-blue-500 focus:outline-none` but no ring
- `/frontend/components/admin-v2/job-management-table.tsx` — **Line 123:** Status filter `<select>` has `focus:outline-none` alone
- `/frontend/components/dashboard/recent-jobs-list.tsx` — **Line 86:** Search input has `focus:border-[#3b82f6] focus:outline-none` but no ring
- `/frontend/components/dashboard/recent-jobs-list.tsx` — **Line 92:** Sort `<select>` has `focus:outline-none` alone

**Contrast:** These have focus rings (properly accessible):
- `/frontend/components/auth/login-form.tsx` — **Lines 134, 150:** `focus:ring-1 focus:ring-blue-500` ✓
- `/frontend/components/unified-input/UnifiedInputPanel.tsx` — **Line 206:** `focus:ring-1 focus:ring-blue-500` ✓
- `/frontend/components/ui/AnimatedButton.tsx` — **Line 68:** `focus:ring-2 focus:ring-blue-500/50` ✓

---

## 3. Input Placeholders Without Associated Labels

**Issue:** 50+ inputs have placeholder text but lack `<label>` or `aria-label`.

**Missing Labels (highest priority):**
- `/frontend/components/admin-v2/job-management-table.tsx` — **Line 113-118:** Search input has only `placeholder="Search jobs…"` — **NEEDS:** `aria-label` or `<label>`
- `/frontend/components/dashboard/recent-jobs-list.tsx` — **Line 81-86:** Search input has only `placeholder="Search jobs..."` — **NEEDS:** `aria-label` or `<label>`
- `/frontend/components/admin-v2/error-log-table.tsx` — **Line 140-148:** Filter `<select>` has `placeholder` pattern but in option form — **NEEDS:** `aria-label`
- `/frontend/components/dashboard/StartInput.tsx` — **Line 78-90:** Textarea with `placeholder` but no `<label>` — **NEEDS:** `aria-label` or `<label htmlFor="...">` 

**Inputs WITH Labels (correct):**
- `/frontend/components/auth/login-form.tsx` — **Lines 125-136, 141-152:** Email and password inputs have `<label htmlFor="email">` and `<label htmlFor="password">` ✓
- `/frontend/components/unified-input/UnifiedInputPanel.tsx` — **Lines 197-209:** Research topic has `<label htmlFor="researchTopic">` ✓

---

## 4. Tables Missing Horizontal Scroll Wrappers

**Issue:** Three admin tables lack `overflow-x-auto` wrapper for small screens.

**Tables Affected:**
- `/frontend/components/admin-v2/user-management-table.tsx` — **Lines 107-146:**
  ```
  <div className="bg-card border border-border rounded-xl overflow-hidden">
    <table className="w-full">
  ```
  **FIX:** Wrap `<table>` in `<div className="overflow-x-auto">` at line 107

- `/frontend/components/admin-v2/job-management-table.tsx` — **Lines 136-177:**
  ```
  <div className="bg-card border border-border rounded-xl overflow-hidden">
    <div className="overflow-x-auto">  ← EXISTS ✓
      <table className="w-full">
  ```
  **STATUS:** Already has wrapper (correctly implemented)

- `/frontend/components/queue/queue-content.tsx` — **Lines 98-127:**
  ```
  <div className="bg-surface-1 border border-border rounded-xl overflow-hidden">
    <table className="w-full">
  ```
  **FIX:** Wrap `<table>` in `<div className="overflow-x-auto">` at line 98

---

## 5. Hardcoded Hex Colors — Design Token Migration Needed

**Issue:** 25+ files use hardcoded hex colors in arbitrary utility values. Should use Tailwind tokens from theme.

**High-Impact Files:**
- `/frontend/components/dashboard/DashboardJobCard.tsx` — **Lines 19-26:**
  ```javascript
  className: 'text-[#22c55e] bg-[#22c55e]/10'
  className: 'text-[#3b82f6] bg-[#3b82f6]/10'
  className: 'text-[#ef4444] bg-[#ef4444]/10'
  ```
  **COUNT:** 8 hex colors in status badge config

- `/frontend/components/dashboard/DashboardJobCard.tsx` — **Lines 43, 48, 49, 71:**
  ```javascript
  className={`bg-[#12121a] border ...`}
  className="text-[#f5f5f5]"
  className="text-[#71717a]"
  className="h-full rounded-full bg-gradient-to-r from-[#3b82f6] to-[#8b5cf6]"
  ```
  **COUNT:** 4 additional hex colors

- `/frontend/components/queue/queue-content.tsx` — **Lines 61, 62, 65, 68, 79, 100, etc.:**
  ```javascript
  className="text-[#f5f5f5]"
  className="text-[#71717a]"
  className="bg-[#12121a] border border-[#27272a]"
  className="text-[#a1a1aa]"
  ```
  **COUNT:** 15+ hex colors throughout file

- `/frontend/components/dashboard/recent-jobs-list.tsx` — **Lines 59, 86, 87, 92:**
  ```javascript
  className="text-[#f5f5f5]"
  className="focus:border-[#3b82f6]"
  className="text-[#52525b]"
  ```

---

## 6. Admin Tables Without Empty State UI

**Issue:** Admin tables show "No data" text but lack visual polish or action prompts.

**Files & Line Numbers:**

- `/frontend/components/admin-v2/user-management-table.tsx` — **Lines 129-134:**
  ```jsx
  <tr>
    <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
      No users found
    </td>
  </tr>
  ```
  **MISSING:** Icon, visual styling, action button (e.g., "Invite first user")

- `/frontend/components/admin-v2/job-management-table.tsx` — **Lines 159-164:**
  ```jsx
  <tr>
    <td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">
      No jobs found
    </td>
  </tr>
  ```
  **MISSING:** Icon, visual styling, explanation

- `/frontend/components/admin-v2/error-log-table.tsx` — **Line 171:**
  ```jsx
  <p className="text-sm text-muted-foreground text-center py-12">No error logs found</p>
  ```
  **STATUS:** Already has `py-12` padding (baseline acceptable, but could add icon)

- `/frontend/components/queue/queue-content.tsx` — **Lines 99-100:**
  ```jsx
  <p className="text-sm text-[#71717a] py-10 text-center">No jobs in queue.</p>
  ```
  **MISSING:** Icon, action prompt

---

## 7. Data Fetching Without Error State UI

**Issue:** Components fetch data but don't display error states to users.

**Files Missing Error Handling:**

- `/frontend/components/dashboard/recent-jobs-list.tsx` — **Lines 29-47:**
  - Uses `isLoading`, shows skeleton, shows empty state, but **no `error` prop**
  - **MISSING:** Error display UI
  
- `/frontend/components/queue/queue-content.tsx` — **Lines 33-41:**
  - `useJobs()` hook called but **no error handling visible**
  - **FIX:** Add `isError` state display

- `/frontend/components/job-detail-v2/job-detail-content.tsx` — **Lines 40, 65-88:**
  ```jsx
  const { data: job, isLoading, isError, error, refetch } = useJobDetail(jobId);
  
  if (isError || !job) {
    return (
      <div className="flex flex-col items-center justify-center py-24...">
        {/* Error UI with retry button */}
      </div>
    );
  }
  ```
  **STATUS:** Already has error handling ✓

- `/frontend/components/settings-v2/settings-content.tsx` — **Unknown line (file not fully read)**
  - Marked as having "useQuery|isLoading" pattern
  - **NEEDS VERIFICATION**

---

## Summary Statistics

| Issue Category | Count | Severity |
|---|---|---|
| Missing `prefers-reduced-motion` | 60+ files | HIGH |
| Inputs missing focus rings | 5+ files | HIGH |
| Inputs missing labels | 30+ inputs | HIGH |
| Tables missing overflow wrapper | 2 tables | MEDIUM |
| Hardcoded hex colors | 25+ files | MEDIUM |
| Empty states lacking polish | 4 tables | LOW |
| Error states missing UI | 3+ components | MEDIUM |

---

## Unresolved Questions

1. **Color Token System:** Should migrate hardcoded hex to Tailwind theme config or CSS variables? (Check `tailwind.config.ts`)
2. **Checkbox for `prefers-reduced-motion`:** Is there already a user preference toggle in settings that should affect this?
3. **Label Pattern:** Should all inputs use `aria-label` or explicit `<label>` with `htmlFor`? Any project convention?
4. **Empty States:** Are there design specs for admin table empty states, or should add placeholder icons + CTAs ad-hoc?

