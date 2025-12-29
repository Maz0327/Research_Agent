# UX Testing Action Plan
**Sprint**: Immediate (Critical Issues)
**Timeline**: Estimated 5-7 days for Phase 1

---

## PHASE 1: CRITICAL FIXES (Before Production)

### Issue #1: Responsive Sidebar Breaking Mobile Layout
**Severity**: CRITICAL (WCAG 2.1 AA Violation)
**Impact**: Mobile users <375px cannot use app (68% of screen hidden)
**Root Cause**: Fixed `w-64` (256px) sidebar with no responsive breakpoint

**Fix Strategy**:
1. Add `sm:` breakpoint to hide sidebar on mobile
2. Implement hamburger menu toggle on mobile
3. Test on iPhone SE (375px), iPhone 12 (390px), Android (360px)

**Files to Modify**:
- `/frontend/components/Layout.tsx` lines 29-44
  - Change: `w-64` → `hidden sm:block sm:w-64`
  - Add mobile hamburger toggle state
  - Add overlay drawer for mobile nav

**Estimated Effort**: 2-3 hours (including testing)

**Acceptance Criteria**:
- [ ] Sidebar hidden on <640px screens
- [ ] Hamburger menu visible on mobile
- [ ] Main content takes full width on mobile
- [ ] Navigation links accessible on mobile
- [ ] Pass WCAG mobile viewport test

---

### Issue #2: Skip Link Broken After First Use
**Severity**: CRITICAL (WCAG 2.1 A Violation)
**Impact**: Keyboard-only users cannot skip to content on repeat visits
**Root Cause**: Skip link focus not managed correctly

**Fix Strategy**:
1. Ensure skip link focus management persists
2. Test with screen readers (NVDA, JAWS)
3. Verify tabindex management

**Files to Modify**:
- `/frontend/components/SkipLink.tsx`
  - Fix focus management after skip
  - Ensure main-content gets focus

**Estimated Effort**: 1-2 hours

**Acceptance Criteria**:
- [ ] Skip link works on every page visit
- [ ] Focus moves to main-content on skip
- [ ] NVDA announces "main content" after skip
- [ ] No focus trap occurs

---

### Issue #3: Navigation Link Color Contrast
**Severity**: CRITICAL (WCAG 2.1 AA Violation)
**Impact**: Visually impaired users cannot distinguish active nav items
**Root Cause**: Border/background combination <4.5:1 contrast ratio

**Fix Strategy**:
1. Increase border brightness (move from `/30` to `/50`)
2. Adjust background opacity for better contrast
3. Use WebAIM contrast checker to verify

**Files to Modify**:
- `/frontend/components/Layout.tsx` line 57
  - Change: `border-blue-500/30` → `border-blue-500/60` or `border-blue-600`
  - Adjust: `bg-blue-600/20` → `bg-blue-600/30`

**Estimated Effort**: 30 minutes (+ testing)

**Acceptance Criteria**:
- [ ] Active nav link contrast ≥4.5:1
- [ ] Pass WebAIM contrast checker
- [ ] Visual distinction clear in all browsers

---

### Issue #4: Job Filter State Not Persisting
**Severity**: CRITICAL (Functional Bug)
**Impact**: Users lose filter selection on page refresh
**Root Cause**: Filter state is local component state only

**Fix Strategy**:
1. Move filter state to localStorage
2. Initialize filter from localStorage on mount
3. Sync updates to localStorage

**Files to Modify**:
- `/frontend/pages/dashboard.tsx` lines 40-109
  - Replace: `const [statusFilter, setStatusFilter] = useState<string>('all');`
  - With: localStorage-backed state
  - Use custom hook: `useLocalStorage('jobStatusFilter', 'all')`

**Implementation**:
```typescript
// Create custom hook in /frontend/hooks/useLocalStorage.ts
export function useLocalStorage(key: string, initialValue: string) {
  const [value, setValue] = useState(() => {
    try {
      const item = typeof window !== 'undefined' ? window.localStorage.getItem(key) : null;
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setStoredValue = (val: string) => {
    setValue(val);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(key, JSON.stringify(val));
    }
  };

  return [value, setStoredValue] as const;
}
```

**Estimated Effort**: 1-2 hours

**Acceptance Criteria**:
- [ ] Filter persists on page refresh
- [ ] Filter persists across browser tabs
- [ ] Filter resets on manual clear
- [ ] No localStorage errors in console

---

### Issue #5: Job Card Expand/Collapse Flickering on Polling
**Severity**: CRITICAL (User Experience)
**Impact**: User expands card to view details, card auto-collapses on polling update
**Root Cause**: Job polling updates trigger re-render without preserving expand state

**Fix Strategy**:
1. Prevent re-render of expanded content during polling
2. Use `useMemo` to memoize expanded content
3. Only update card header info, not full card state

**Files to Modify**:
- `/frontend/components/JobCard.tsx` lines 33-121
  - Wrap expanded content in `useMemo`
  - Separate polling state from expand state
  - Use `React.memo` to prevent parent re-renders

**Implementation**:
```typescript
// Memoize expanded content to prevent collapse
const expandedContent = useMemo(() => (
  isExpanded ? (
    <ExpandedJobDetails job={job} onRefresh={onRefresh} />
  ) : null
), [isExpanded, job, onRefresh]);
```

**Estimated Effort**: 2-3 hours (including testing)

**Acceptance Criteria**:
- [ ] Card stays expanded during polling update
- [ ] Card doesn't flicker when job status updates
- [ ] Job info updates smoothly without collapse
- [ ] Polling continues normally

---

### Issue #6: Full Job Prompt Not Showing in Expanded View
**Severity**: CRITICAL (Functional Bug)
**Impact**: User cannot see complete job prompt if job.title === job.prompt
**Root Cause**: Conditional logic hides prompt when title matches

**Fix Strategy**:
1. Always show full prompt in expanded view
2. Show both title and prompt separately
3. Improve information hierarchy

**Files to Modify**:
- `/frontend/components/JobCard.tsx` lines 135-141
  - Remove conditional: `if (job.title && job.prompt !== job.title)`
  - Always show: `<FullPromptDisplay prompt={job.prompt} />`

**Implementation**:
```typescript
// Always show full prompt
{job.prompt && (
  <div>
    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
      Full Prompt
    </h4>
    <p className="text-sm text-gray-300 whitespace-pre-wrap">{job.prompt}</p>
  </div>
)}
```

**Estimated Effort**: 1 hour

**Acceptance Criteria**:
- [ ] Full prompt always visible when expanded
- [ ] Prompt text wraps correctly
- [ ] No truncation of long prompts
- [ ] Readable formatting maintained

---

## PHASE 2: HIGH-PRIORITY FIXES (Within 1 Week)

### Issue #7: Job Prompt Validation Too Lenient
**Severity**: HIGH
**Impact**: 1-character prompts accepted, causing poor research quality
**Files**: `/frontend/pages/dashboard.tsx` line 87

**Fix**:
```typescript
// Change from:
if (!prompt.trim()) return;

// To:
if (prompt.trim().length < 10) {
  setMessage({ type: 'error', text: 'Please enter at least 10 characters' });
  return;
}
```

**Estimated Effort**: 30 minutes

---

### Issue #8: Folder Validation Race Condition
**Severity**: HIGH
**Impact**: Multiple submit attempts during async validation
**Files**: `/frontend/pages/settings.tsx` lines 111-118

**Fix**: Add submission lock during validation
```typescript
const [isValidatingFolder, setIsValidatingFolder] = useState(false);

const handleValidateFolder = async () => {
  if (isValidatingFolder || !folderUrl.trim()) return;
  setIsValidatingFolder(true);
  try {
    const result = await validateFolder(folderUrl.trim());
    if (result.valid) {
      addFolder(result);
      setFolderUrl('');
    }
  } finally {
    setIsValidatingFolder(false);
  }
};
```

**Estimated Effort**: 1 hour

---

### Issue #9: Username Check Stale Closure
**Severity**: HIGH
**Impact**: Race condition in username availability check
**Files**: `/frontend/pages/settings.tsx` lines 101-109

**Fix**: Use `useEffect` cleanup for debounce
```typescript
useEffect(() => {
  if (username.length >= 3 && username !== settings?.username) {
    const timer = setTimeout(() => {
      checkUsername(username); // Captures current username
    }, 500);
    return () => clearTimeout(timer);
  }
}, [username, settings?.username, checkUsername]);
```

**Estimated Effort**: 1 hour

---

### Issue #10: Transcript Polling Silent Failure
**Severity**: HIGH
**Impact**: User thinks job is running when it actually failed
**Files**: `/frontend/pages/transcripts.tsx` lines 74-98

**Fix**: Show error toast when polling fails
```typescript
if (errorCount >= MAX_POLL_ERRORS) {
  clearInterval(pollInterval);
  setError('Failed to fetch job status after multiple attempts. Please refresh the page.');
  // Show error toast
}
```

**Estimated Effort**: 1 hour

---

### Issue #11: Pipeline Buttons Wrong Semantics
**Severity**: HIGH (A11y)
**Impact**: Screen reader users confused by button role="radio"
**Files**: `/frontend/pages/dashboard.tsx` line 159

**Fix**: Use actual radio inputs or convert to fieldset
```typescript
// Option 1: Use fieldset with radio inputs
<fieldset>
  <legend>Select Pipeline Mode</legend>
  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
    {pipelines.map((p) => (
      <label key={p.value}>
        <input
          type="radio"
          name="pipeline"
          value={p.value}
          checked={pipeline === p.value}
          onChange={(e) => setPipeline(e.target.value)}
          className="sr-only"
        />
        <span className="...">...</span>
      </label>
    ))}
  </div>
</fieldset>
```

**Estimated Effort**: 1-2 hours

---

### Issue #12: Settings Cancel Button Wrong Behavior
**Severity**: HIGH
**Impact**: "Cancel" reloads from server instead of discarding changes
**Files**: `/frontend/pages/settings.tsx` lines 325-331

**Fix**: Separate cancel (discard) from reset (reload)
```typescript
const handleCancel = () => {
  // Reset form to initial settings state
  setUsername(settings?.username || '');
  setDriveFolders(settings?.drive_folders || []);
  // ... reset all other fields
};
```

**Estimated Effort**: 1 hour

---

### Issue #13: Missing Admin Sidebar Link
**Severity**: HIGH
**Impact**: Admin users can't easily navigate to admin panel
**Files**: `/frontend/components/Layout.tsx` lines 15-19

**Fix**: Add conditional admin link
```typescript
const navItems = [
  // ... existing items
  ...(isAdmin ? [{
    href: '/admin',
    label: 'Admin',
    icon: '...'
  }] : []),
];
```

**Estimated Effort**: 30 minutes

---

## PHASE 3: MEDIUM-PRIORITY IMPROVEMENTS (2 Weeks)

### Issue #14: Add Pagination for Job Lists
**Files**: `/frontend/pages/dashboard.tsx`
**Effort**: 2-3 hours
**Impact**: Improves performance with 50+ jobs

### Issue #15: Add Job Title Tooltips
**Files**: `/frontend/components/JobCard.tsx`
**Effort**: 1 hour
**Impact**: Users see full title on hover

### Issue #16: Form Character Limits Display
**Files**: `/frontend/pages/dashboard.tsx`, `/frontend/pages/transcripts.tsx`
**Effort**: 1 hour
**Impact**: Users know input constraints

### Issue #17: Improve Loading State Clarity
**Files**: `/frontend/pages/login.tsx`, `/frontend/pages/settings.tsx`
**Effort**: 1-2 hours
**Impact**: Users understand what's loading

### Issue #18: Add Retry Buttons for Errors
**Files**: `/frontend/components/ErrorDisplay.tsx`
**Effort**: 2 hours
**Impact**: Users can retry failed operations

---

## TESTING STRATEGY

### Unit Tests to Add:
1. Job filter persistence with localStorage
2. Job prompt validation (min length)
3. Folder validation race condition
4. Username debounce behavior
5. Transcript polling error handling

### Integration Tests:
1. Full dashboard flow (create job, filter, expand card)
2. Settings save/cancel flow
3. Transcript submission and polling
4. Auth flow with error recovery

### E2E Tests (Recommended):
1. Mobile responsive navigation
2. Keyboard-only navigation
3. Screen reader testing (NVDA)
4. Error recovery flows

### Manual Testing Checklist:
- [ ] Test on iPhone SE (375px)
- [ ] Test on iPhone 12 (390px)
- [ ] Test on Android 360px device
- [ ] Test keyboard-only navigation
- [ ] Test with NVDA screen reader
- [ ] Test with Firefox accessibility inspector
- [ ] Test on Chrome, Safari, Firefox
- [ ] Verify WebAIM contrast ratios

---

## ESTIMATED TIMELINE

| Phase | Issues | Estimated Hours | Real-world Time | Priority |
|-------|--------|-----------------|-----------------|----------|
| 1 (Critical) | 6 | 10-14 | 2-3 days | MUST FIX |
| 2 (High) | 7 | 8-10 | 2-3 days | SHOULD FIX |
| 3 (Medium) | 5+ | 8-12 | 1-2 weeks | NICE TO HAVE |

**Total Critical Path**: 5-7 days for production readiness

---

## DEPENDENCIES

**Before Starting Phase 1**:
- Ensure testing environment set up (axe DevTools, NVDA, WebAIM)
- Create git branch: `fix/ux-critical-issues`
- Set up PR template with A11y checklist

**For Phase 2**:
- Implement custom `useLocalStorage` hook (shared across components)
- Update error handling patterns for consistency

**For Phase 3**:
- Establish pagination library (react-paginate or custom)
- Design tooltip component for reuse

---

## ACCEPTANCE CRITERIA

**Phase 1 Complete When**:
- [ ] All 6 critical issues fixed
- [ ] Mobile responsive test passes
- [ ] WCAG 2.1 AA compliance verified
- [ ] All tests passing
- [ ] No console errors
- [ ] Manual testing on 3 devices passing

**Phase 2 Complete When**:
- [ ] All 7 high-priority issues fixed
- [ ] A11y semantic HTML verified
- [ ] New unit tests added and passing
- [ ] Integration tests passing

**Ready for Production**:
- [ ] All Phase 1 issues complete
- [ ] Phase 2 majority complete
- [ ] No critical/high severity issues remaining
- [ ] Mobile responsive verified
- [ ] A11y audit passed

---

## ROLLOUT PLAN

1. **Code Review**: Each PR reviewed for A11y and responsive design
2. **Testing**: Manual mobile + keyboard testing before merge
3. **Staging Deploy**: Test on staging with real mobile devices
4. **Beta Release**: Deploy to 10% of users first
5. **Full Release**: Monitor error rates and user feedback

---

## MONITORING AFTER FIXES

- Track error rates for fixed issues
- Monitor mobile user experience metrics
- Collect A11y-related support tickets
- Set up accessibility monitoring alerts

---

**Last Updated**: December 28, 2025
**Owner**: QA/Frontend Team
**Review Cycle**: Weekly until all Phase 1 issues complete
