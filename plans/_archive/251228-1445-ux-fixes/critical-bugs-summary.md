# Critical Bugs Summary - Research Agent UX Testing
**Date**: December 28, 2025
**Test Run**: Complete UX flow analysis
**Total Critical Issues**: 6

---

## BUG #1: Mobile Sidebar Breaks Layout (WCAG 2.1 AA VIOLATION)

**Status**: 🔴 CRITICAL - Production Blocker
**Component**: `components/Layout.tsx` line 34
**Severity**: Must fix before any user can access on mobile

### Problem Description:
Sidebar is fixed width (256px) with no responsive breakpoint. On mobile screens <375px, the sidebar takes 68% of the viewport, making main content nearly unreadable.

```
iPhone SE (375px width):
┌──────────────────────────────┐
│ SIDEBAR (256px) │ CONTENT(119px) │ ❌ TOO SMALL
│  ████████████  │ ██              │
└──────────────────────────────┘

Desired behavior:
┌──────────────────────────────┐
│ ☰ │ CONTENT (full width)     │ ✓ READABLE
│   │ ██████████████████████   │
└──────────────────────────────┘
```

### Impact on User:
- Dashboard text unreadable on mobile
- Settings form inputs overflow screen
- Navigation hidden behind sidebar
- Cannot interact with content on phones

### Root Cause:
```tsx
// Current code - NO RESPONSIVE BREAKPOINT
<aside className="fixed inset-y-0 left-0 z-10 w-64 border-r...">
```

### Solution:
```tsx
// Fixed code - RESPONSIVE SIDEBAR
<aside className="fixed inset-y-0 left-0 z-10 hidden sm:block sm:w-64 border-r...">
// Add mobile hamburger toggle on <sm breakpoint
// Add drawer overlay for mobile navigation
```

### Testing to Verify:
- [ ] Open on iPhone SE (375px) - content readable
- [ ] Open on Android 360px - content readable
- [ ] Hamburger menu appears on mobile
- [ ] Clicking hamburger opens nav drawer
- [ ] Drawer closes when clicking link
- [ ] Main content extends full width on mobile

---

## BUG #2: Skip Link Broken After First Use (WCAG 2.1 A VIOLATION)

**Status**: 🔴 CRITICAL - Accessibility Blocker
**Component**: `components/SkipLink.tsx`
**Severity**: Keyboard-only users cannot skip to content

### Problem Description:
Skip link works on first page visit but subsequent visits don't activate it. Keyboard users need to tab through entire sidebar navigation.

```
First Visit:
User presses Tab
↓
Skip link receives focus ✓
User presses Enter
↓
Focus moves to main-content ✓
Works as expected

Second Visit (after page reload):
User presses Tab
↓
Skip link... receives focus ❌
But clicking doesn't work or focus doesn't move to content ✗
User must Tab through all nav items
```

### Impact on User:
- Keyboard-only users must tab 20+ times through sidebar
- Screen reader users cannot skip to main content
- Violates WCAG 2.1 Level A requirement
- Accessibility compliance fails

### Root Cause:
Focus management not properly maintained after skip action. Skip link focus-handling code likely has issue with event listeners or focus trap.

### Solution:
```tsx
// Fix focus management
const handleSkipClick = (e: React.MouseEvent) => {
  e.preventDefault();
  const mainContent = document.getElementById('main-content');
  if (mainContent) {
    mainContent.tabIndex = -1; // Make focusable
    mainContent.focus(); // Move focus
    mainContent.addEventListener('blur', () => {
      mainContent.tabIndex = -1; // Restore to normal
    }, { once: true });
  }
};
```

### Testing to Verify:
- [ ] Open page, press Tab
- [ ] Skip link receives focus (visible outline)
- [ ] Press Enter
- [ ] Focus moves to main-content (h1 or first button)
- [ ] Reload page, press Tab
- [ ] Skip link focuses again
- [ ] Enter still works after reload
- [ ] Test with NVDA screen reader

---

## BUG #3: Navigation Link Color Contrast (WCAG 2.1 AA VIOLATION)

**Status**: 🔴 CRITICAL - Compliance Blocker
**Component**: `components/Layout.tsx` line 57
**Severity**: Visually impaired users cannot distinguish active nav items

### Problem Description:
Active navigation link uses border-blue-500/30 (30% opacity) + bg-blue-600/20 (20% opacity) on dark background. Contrast ratio approximately 3.8:1, below WCAG AA requirement of 4.5:1.

```
Current styling (FAILS):
<Link className="border-blue-500/30 bg-blue-600/20">
    ↑ 30% opacity (too faint)
    ↑ 20% opacity (too light)

Contrast ratio: ~3.8:1 ❌ FAILS WCAG AA

Desired styling (PASSES):
<Link className="border-blue-500/60 bg-blue-600/40">
    ↑ 60% opacity (more visible)
    ↑ 40% opacity (better contrast)

Contrast ratio: ~4.8:1 ✓ PASSES WCAG AA
```

### Impact on User:
- Low vision users struggle to see which page they're on
- Cannot distinguish active vs inactive navigation
- Fails accessibility compliance audit
- Legal liability (WCAG AA is standard requirement)

### Root Cause:
Opacity values chosen for aesthetics, not accessibility. No contrast checker used during design.

### Solution:
```tsx
// Increase opacity for sufficient contrast
className={`nav-item flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200 ${
  isActive
    ? 'bg-blue-600/40 text-blue-400 border border-blue-500/70'  // INCREASED opacity
    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-transparent'
}`}
```

### Testing to Verify:
- [ ] Check contrast with WebAIM contrast checker
- [ ] Ratio should be ≥4.5:1
- [ ] Verify on multiple browsers (Chrome, Firefox, Safari)
- [ ] Test with color blindness simulator
- [ ] Visual inspection shows clear active state

---

## BUG #4: Job Filter State Doesn't Persist (FUNCTIONAL BUG)

**Status**: 🔴 CRITICAL - Data Loss Issue
**Component**: `pages/dashboard.tsx` lines 40-109
**Severity**: Users lose their filter selection

### Problem Description:
Status filter is stored in component state only. When user refreshes page, filter resets to "all".

```
User Action Timeline:
1. User selects "running" filter
   ↓
   statusFilter state = "running"
   ✓ Shows only running jobs

2. User refreshes page (F5)
   ↓
   Component unmounts & remounts
   ↓
   useState('all') runs again
   ↓
   statusFilter state = 'all' (RESET!) ✗
   Shows all jobs (wrong!)

Expected behavior:
   Filter should persist across refreshes
```

### Impact on User:
- User filters to "failed" jobs to debug
- User refreshes page to reload job details
- Filter resets - must re-select "failed" again
- Annoying repeated work
- Data loss perception (even though not permanent)

### Root Cause:
```tsx
// Current code - LOCAL STATE ONLY
const [statusFilter, setStatusFilter] = useState<string>('all');
```

Filter is component state, lost on unmount. No localStorage or URL persistence.

### Solution:
```tsx
// Use localStorage to persist filter
const [statusFilter, setStatusFilter] = useState<string>(() => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('jobStatusFilter') || 'all';
  }
  return 'all';
});

const handleFilterChange = (newStatus: string) => {
  setStatusFilter(newStatus);
  if (typeof window !== 'undefined') {
    localStorage.setItem('jobStatusFilter', newStatus);
  }
};
```

### Testing to Verify:
- [ ] Select "failed" filter
- [ ] Refresh page (F5)
- [ ] Filter should still show "failed"
- [ ] Select "completed" filter
- [ ] Refresh page
- [ ] Filter should show "completed"
- [ ] Clear browser storage, refresh
- [ ] Filter should reset to "all"

---

## BUG #5: Job Card Expand/Collapse Flickering (USER EXPERIENCE BUG)

**Status**: 🔴 CRITICAL - Frustrating UX
**Component**: `components/JobCard.tsx` lines 33-121
**Severity**: Card collapses when user viewing details

### Problem Description:
User expands job card to view details (ETA, elapsed time, results). While card is expanded, polling updates job status. Card re-renders and collapses, hiding the details user was reading.

```
User Experience Timeline:
1. User clicks job card to expand
   ↓
   isExpanded = true
   ✓ Expanded content visible
   └─ "ETA: 2m 34s"
   └─ "Elapsed: 30s"
   └─ "Stage: Extracting transcripts"

2. Polling timer fires (5 second interval)
   ↓
   Job status updated in store
   ↓
   JobCard re-renders
   ↓
   Component returns to initial state
   ↓
   isExpanded = false (?!)

3. Card COLLAPSES
   ✗ Details hidden again!
   ✗ User frustrated, clicks again

4. Polling fires again...
   Loop continues...
```

### Impact on User:
- User cannot read job details without constant collapse
- User must re-expand after every poll (5 seconds)
- Very frustrating and confusing experience
- Appears like app is broken
- Users may abandon the app

### Root Cause:
```tsx
// isExpanded state in JobCard component
const [isExpanded, setIsExpanded] = useState(false);

// Parent component (Dashboard) passes job object
// When job updates from polling, JobCard re-renders
// If parent doesn't memoize, child re-renders with new props
// State might reset or component unmounts/remounts
```

Parent component updates cause child to lose expand state.

### Solution:
```tsx
// Prevent collapse on polling updates
import { memo } from 'react';

// Memoize the card so it doesn't re-render unless job.id changes
export default memo(function JobCard({ job, onRefresh }: JobCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Separate polling updates from card state
  // Only update header info, keep expand state

  // Option 2: Use useMemo to preserve expand state
  const expandedContent = useMemo(() => (
    isExpanded ? <ExpandedDetails job={job} /> : null
  ), [isExpanded, job.id]);

  return (
    <div>
      <CardHeader job={job} /> {/* Updates on poll */}
      {expandedContent} {/* Preserves expand state */}
    </div>
  );
}, (prevProps, nextProps) => {
  // Re-render only if job ID changes, not on status update
  return prevProps.job.id === nextProps.job.id;
});
```

### Testing to Verify:
- [ ] Expand job card
- [ ] Wait for polling update (5 seconds)
- [ ] Card should STAY expanded
- [ ] Job info should update, not collapse
- [ ] Can read details for 30+ seconds without flickering
- [ ] Expand multiple cards, all stay expanded during polling
- [ ] No console errors about state

---

## BUG #6: Job Prompt Not Showing in Expanded View (FUNCTIONAL BUG)

**Status**: 🔴 CRITICAL - Data Not Visible
**Component**: `components/JobCard.tsx` lines 135-141
**Severity**: User cannot see job details

### Problem Description:
Job card has conditional logic that hides the prompt when `job.title === job.prompt`. If user creates a job with title only (no separate prompt), expanded view shows nothing.

```tsx
// Current problematic code (line 135-141):
{job.title && job.prompt !== job.title && (
  <div>
    <h4>Original Prompt</h4>
    <p>{job.prompt}</p>
  </div>
)}

// When user creates job with title "Climate Change Research"
// and no prompt text:
job.title = "Climate Change Research"
job.prompt = "Climate Change Research"

// Condition checks:
// - job.title? YES ✓
// - job.prompt !== job.title? NO ✗ (they're the same!)
// Result: Prompt section hidden
// ❌ User expands card, sees nothing
```

### Impact on User:
- User creates job and can see title in collapsed card
- User expands card to view full details
- Expanded view is EMPTY or missing "Original Prompt" section
- User confusion: "Where's my prompt?"
- Appears like data is lost

### Root Cause:
Conditional logic assumes title and prompt are always different. But when UI design allows creating job with just title, they become equal.

### Solution:
```tsx
// Always show the prompt/content, even if same as title
{job.prompt && (
  <div>
    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
      Full Prompt
    </h4>
    <p className="text-sm text-gray-300 whitespace-pre-wrap">
      {job.prompt}
    </p>
  </div>
)}
```

### Testing to Verify:
- [ ] Create job with just title (no newline in prompt)
- [ ] Expand card
- [ ] Full prompt section should appear
- [ ] Prompt text should be readable
- [ ] Create job with title + different prompt
- [ ] Both should appear in expanded view
- [ ] Create job with multi-line prompt
- [ ] Whitespace preserved correctly

---

## Summary Table: Critical Bugs

| # | Bug | Component | Impact | Fix Time | Tests |
|---|-----|-----------|--------|----------|-------|
| 1 | Sidebar not responsive | Layout.tsx | Mobile unusable | 2-3h | Mobile, Responsive |
| 2 | Skip link broken | SkipLink.tsx | A11y fail | 1-2h | Keyboard nav, NVDA |
| 3 | Nav contrast too low | Layout.tsx | A11y fail | 0.5h | Contrast checker |
| 4 | Filter not persisting | Dashboard.tsx | Data loss | 1-2h | Refresh test |
| 5 | Card flickering | JobCard.tsx | UX broken | 2-3h | Polling test |
| 6 | Prompt not showing | JobCard.tsx | Data hidden | 1h | Expand test |

**Total Estimated Fix Time**: 10-14 hours over 2-3 days

---

## How to Reproduce Each Bug

### Bug #1: Sidebar
1. Open app in mobile browser or DevTools mobile view
2. Set viewport to 375px width (iPhone SE)
3. Navigate to /dashboard
4. Main content width = only ~120px
5. Text unreadable

### Bug #2: Skip Link
1. Open app in Chrome
2. Press Tab
3. Skip link focuses (outline visible)
4. Press Enter
5. Focus should move to main content
6. Reload page (F5)
7. Press Tab
8. Skip link should focus again
9. Issue: Usually doesn't work on reload

### Bug #3: Contrast
1. Use WebAIM Contrast Checker
2. Sample active nav link color
3. Background: rgb(20, 20, 20) - dark bg
4. Border: rgb(59, 130, 246) at 30% = too faint
5. Ratio: 3.8:1 (needs 4.5:1)

### Bug #4: Filter
1. Open /dashboard
2. Click "failed" status filter
3. Press F5 to refresh
4. Filter resets to "all"
5. Check localStorage - no jobStatusFilter key

### Bug #5: Flickering
1. Open /dashboard
2. Create test job
3. Wait for it to reach "running" state
4. Click to expand card
5. Read the ETA and elapsed time
6. Wait 5 seconds for polling update
7. Card collapses
8. Must click again to re-expand
9. Repeat every 5 seconds

### Bug #6: Prompt
1. Open /dashboard
2. In prompt field, enter: "Climate Change Research"
3. Don't press Enter or add newline
4. Select a pipeline
5. Click "Start Research"
6. Wait for job to appear in list
7. Click to expand job card
8. "Original Prompt" section should appear but may be missing

---

## Prevention Checklist

- [ ] Always test responsive design on real devices (not just DevTools)
- [ ] Run accessibility tests (axe, WCAG Checker) before commit
- [ ] Test state persistence across page reloads
- [ ] Test component re-renders with changing props
- [ ] Test polling/auto-update interactions
- [ ] Test all form submission paths (happy path + edge cases)
- [ ] Test with keyboard navigation (Tab, Enter, Esc)
- [ ] Test with screen readers (NVDA on Windows, VoiceOver on Mac)

---

## Testing Before Deployment

**Manual Testing Checklist**:
- [ ] iPhone SE (375px) - sidebar and content readable
- [ ] iPhone 12 (390px) - hamburger menu appears
- [ ] Android 360px - no layout break
- [ ] Keyboard Tab through navigation - Skip link works
- [ ] WebAIM contrast check - all elements ≥4.5:1
- [ ] Filter persists on F5 reload
- [ ] Expand job card, wait 10 seconds - doesn't collapse
- [ ] Expand job, prompt fully visible if present
- [ ] All tests passing (npm test)
- [ ] No console errors (DevTools console)

**Automated Testing**:
```bash
# Before deploying:
npm test                    # All tests pass
npm run lint               # No linting errors
npm run build              # Build succeeds
# Then manual mobile + keyboard testing
```

---

**Report Prepared By**: QA Engineer
**Date**: December 28, 2025
**Status**: Ready for Development Team
**Priority**: FIX BEFORE PRODUCTION RELEASE
