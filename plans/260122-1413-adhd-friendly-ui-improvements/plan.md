# Plan: ADHD-Friendly UI Improvements

## Problem
Current job card UI is cramped and overwhelming, especially for users with ADHD. Information density is too high with insufficient visual breathing room.

## Goals
- Increase whitespace and breathing room
- Implement progressive disclosure (collapse by default)
- Add clear visual chunking between sections
- Reduce visual noise
- Improve status visibility with icons
- Simplify progress indicators

## Changes

### Phase 1: Spacing & Breathing Room ✅
**Files:** `JobResults.tsx`, `DocumentAccordion.tsx`, `JobCard.tsx`

- [x] Increase `space-y-2` → `space-y-4` for job list gaps
- [x] Increase card padding `p-3` → `p-5`, `p-4` → `p-6`
- [x] Increase section gaps `space-y-3` → `space-y-6`
- [x] Increase button gaps `gap-2` → `gap-3`

### Phase 2: Progressive Disclosure ✅
**Files:** `JobCard.tsx`, `JobResults.tsx`

- [x] Add collapsed/expanded state to completed job cards (already existed)
- [x] Show only title + status + timestamp when collapsed
- [x] Add expand/collapse toggle button (already existed)
- [x] Documents section hidden until expanded

### Phase 3: Visual Chunking ✅
**Files:** `JobResults.tsx`

- [x] Add section headers with uppercase labels
- [x] Add `border-t` dividers between major sections
- [x] Increase margin between document accordions and action bar

### Phase 4: Status Icons ✅
**Files:** `StatusBadge.tsx`, `JobCard.tsx`

- [x] Add colored status dots (green=complete, blue=running, red=failed)
- [x] Larger dot size (h-2 w-2) with glow effect for running
- [x] Simplified status in results (dot + text instead of boxed banner)

### Phase 5: Progress Simplification ✅
**Files:** `ProgressBar.tsx`, `JobCard.tsx`

- [x] Unified progress bar with stage description
- [x] Removed duplicate stage description from header
- [x] Single human-readable line status

### Phase 6: Reduce Visual Noise ✅
**Files:** Multiple

- [x] Removed borders on DocumentAccordion (using bg color only)
- [x] Removed border on error/cancelled states
- [x] Added `leading-relaxed` to all text content
- [x] Increased max-height for document content (28rem)

## Implementation Order
1. Spacing (lowest risk, highest impact)
2. Visual chunking (builds on spacing)
3. Status icons (independent)
4. Progress simplification (independent)
5. Progressive disclosure (most complex)
6. Visual noise reduction (final polish)

## Testing
- Visual review at 320px, 768px, 1024px, 1440px
- Check dark mode contrast
- Verify no layout shifts on expand/collapse
