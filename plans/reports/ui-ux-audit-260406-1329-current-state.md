# UI/UX Audit Report: Research Agent Frontend

**Date:** 2026-04-06
**Auditor:** UI/UX Designer Agent
**Scope:** Full frontend audit across 10 areas
**Positioning:** "Turn any collection of videos and articles into a verified, source-cited script -- with the angle nobody else covered."
**Target Users:** YouTube content creators (video essayists, true crime, tech reviewers, pop culture commentators)

---

## Executive Summary

The frontend has solid architectural bones -- clean component decomposition, proper shadcn/ui integration, semantic CSS variable theming, good accessibility groundwork (SkipLink, ARIA labels, focus states, reduced-motion). However, it reads as a **developer prototype, not a creator tool**. The biggest gaps: no emotional hook on first contact, wrong font (Inter instead of Plus Jakarta Sans), massive color token drift (998 hardcoded gray/zinc references), missing onboarding, and an iteration system that speaks backend language instead of creator language.

**Overall Score: 5.2/10** -- Functional but not sellable. Needs ~2 weeks focused work to feel like a real product.

---

## 1. First Impressions (Login -> Dashboard)

**Score: 4/10**

### What's Good
- Login page has gradient blobs, polished card, Google OAuth + magic link -- professional auth flow
- Dashboard has stats bar, search/filter, card grid -- all functional
- Completion banner with auto-dismiss is thoughtful
- `role="alert"` and `aria-live` on login messages -- good a11y

### What's Broken
- **No value proposition anywhere.** Login says "Research Agent / Sign in to your account" -- could be literally any SaaS. Zero mention of YouTube, creators, research, scripts. The positioning line ("Turn any collection...") appears nowhere in the UI.
- **Dashboard title is "Dashboard / Your research hub"** -- the most generic SaaS copy possible. No personality, no creator-speak.
- **"API Spend" stat card** -- shows a dash with "Coming soon". Half-built features scream prototype. Either ship it or remove it.
- **Empty state is weak.** "Start Your First Research / Extract insights from YouTube videos, web articles, and documents." -- This is feature-speak, not benefit-speak. Should say something like "What's your next video about?"
- **No onboarding flow.** New user hits dashboard cold with zero guidance.

### What's Missing
- **Hero welcome section** for first-time users with value prop + example topics
- **Personality/brand voice** -- everything is written in engineer-speak
- **Logo** -- the sidebar icon is a generic chemistry flask SVG, not a branded mark
- **Illustration or visual hook** on login page -- just blobs + form

### Files Needing Attention
- `components/auth/login-form.tsx` -- needs value prop copy, branding
- `components/dashboard/dashboard-content.tsx` -- needs welcome hero for new users
- `components/dashboard/dashboard-stats.tsx` -- remove or complete API Spend card
- `components/dashboard/recent-jobs-list.tsx` -- empty state copy rewrite

---

## 2. Job Creation Flow (The Wizard)

**Score: 5/10**

### What's Good
- 4-step wizard with progress bar is standard and learnable
- Step labels (Topic, Sources, Mode, Preview) are clear
- Ambiguity detection with interpretation cards is genuinely clever
- Preview step shows summary before commit
- `autoFocus` on topic input is good UX
- Character counter on topic input

### What's Broken
- **Step 2 (Sources) is confusing.** "Add sources (optional) / Leave empty to let the system auto-discover sources." -- OK, but what does "auto-discover" mean? Creators don't think in terms of source types (youtube/article/text dropdown).
- **Step 3 (Mode) is dev-facing.** 6 pipeline options (quick, full, breaking_news, investigation, profile, controversy) are backend pipeline names dressed up. Creators think: "I need a quick overview" vs "I need deep research." The difference between "Full Research" and "Investigation" is unclear without backend knowledge.
- **"Niche" selector is odd.** Why would a creator pick "Tech" or "Finance" when the topic already implies it? If auto-detect works, don't show the selector.
- **Wizard is in a Dialog** -- small modal (max-w-lg). For the most important action in the product, this feels cramped. No breathing room.
- **No visual feedback between steps** -- instant swap, no transition animation.

### What's Missing
- **Suggested topics / recent topics** on Step 1 to reduce blank-canvas anxiety
- **URL validation feedback** on Step 2 (paste YouTube URL, see thumbnail + title preview)
- **Visual mode selector** -- cards with icons instead of a dropdown for Step 3
- **Estimated time / what you'll get** -- "Full Research: ~5 min, 4 documents"
- **Step transitions** -- `framer-motion` is installed but not used in wizard

### Files Needing Attention
- `components/dashboard/job-creation-wizard.tsx` -- consider full-page or larger modal
- `components/dashboard/wizard-step-mode.tsx` -- redesign as visual card selector
- `components/dashboard/wizard-step-sources.tsx` -- URL preview, simplify type picker
- `components/dashboard/wizard-step-topic.tsx` -- add suggested topics

---

## 3. Progress/Waiting Experience

**Score: 5/10**

### What's Good
- `PipelineStatusBar` has pulsing green dot, progress %, stage label -- functional
- `STAGE_LABELS` map is comprehensive with human-readable names + descriptions
- 2-second polling interval is responsive
- `DashboardJobCard` shows inline progress bar with stage name + percentage
- ETA field exists (though apparently unused)

### What's Broken
- **Stage descriptions are wasted.** STAGE_LABELS has great descriptions ("Pulling key points, claims, and quotes from each source...") but only the short label is shown. The descriptions are defined but never rendered.
- **No estimated time.** Polling at 2s but user has no idea if this is 30 seconds or 10 minutes. The `eta` prop exists on PipelineStatusBar but is never passed.
- **Waiting on job detail page is passive.** Just a progress bar and an activity feed that says "Running: semantic_extraction". No preview of partial results, no animation to hold attention.
- **Completion banner on dashboard** auto-dismisses after 5 seconds -- easy to miss.

### What's Missing
- **Skeleton preview of documents** during generation -- show grayed-out section headers
- **Stage description** shown below the stage label ("Pulling key points and quotes from each source...")
- **Estimated time per pipeline mode** (even rough: "usually 2-5 minutes")
- **Partial results rendering** -- show Doc 0 (Source Ledger) as soon as ingestion completes, don't wait for full pipeline
- **Push notification** option for long-running jobs

### Files Needing Attention
- `components/layout/pipeline-status-bar.tsx` -- show stage description, wire ETA
- `components/job-detail-v2/job-center-panel.tsx` -- show partial results earlier
- `components/dashboard/DashboardJobCard.tsx` -- show stage description
- `lib/constants.ts` -- STAGE_LABELS descriptions are already written, just unused

---

## 4. Results Page (Job Detail)

**Score: 6/10**

### What's Good
- **Three-column layout** is well-architected: left (meta + nav), center (documents), right (activity + actions)
- **Responsive behavior** is genuinely good: desktop 3-col, tablet 2-col + sheet, mobile single-col + collapsible
- DocumentNav with accent colors per doc type is visually clear
- Default doc selection logic (`getDefaultDoc`) smartly picks the highest-value doc
- Version selector appears only when multiple versions exist -- good progressive disclosure

### What's Broken
- **Document navigation labels are dev-speak.** "Source Ledger", "Jump-Start", "Semantic Brief" -- a creator would call these "My Sources", "Where to Go Next", "Key Findings". Only "Creator Brief" is somewhat clear.
- **The "hero document" (Creator Brief) doesn't feel heroic.** It's the same visual treatment as every other doc. No special prominence, no "Start here" indicator.
- **Right panel is underutilized.** Just an activity feed (timeline of events) and an "AI Actions" button. The activity feed is useful for devs, not creators.
- **"AI Actions (Iterate / Brainstorm)" button** -- purple accent, sparkles icon. But "Iterate" and "Brainstorm" are developer terms.
- **Error state uses an emoji** (warning triangle emoji) inside a div -- not an icon component. Inconsistent with rest of UI using Lucide icons.

### What's Missing
- **"Start here" callout** pointing to Creator Brief for new jobs
- **Quick summary panel** -- before diving into docs, show: topic, source count, key stat, recommended doc
- **Breadcrumb** -- no way back to dashboard except browser back or sidebar
- **Keyboard shortcuts** -- `j/k` to navigate docs, `c` to open chat, etc.
- **Reading time estimate** per document

### Files Needing Attention
- `components/job-detail-v2/document-nav.tsx` -- rename doc labels to creator language
- `components/job-detail-v2/job-right-panel.tsx` -- redesign with more useful content
- `components/job-detail-v2/job-detail-content.tsx` -- add "start here" for Creator Brief
- `components/job-detail-v2/document-viewer.tsx` -- hero treatment for Doc 3

---

## 5. Document Rendering

**Score: 7/10**

### What's Good
- **Rich typed renderers** for each document type -- not just raw JSON/markdown dump
- **Creator Brief renderer** is well-structured: Story Core, Narrative Angles, Opening Hooks, Title Options, Thumbnail Concepts, Key Moments, Interview Suggestions, Risk Assessment
- **Semantic Brief** SCQA framework is excellent for creators -- situation/complication/question/answer
- **Source Ledger** has type-coded badges (YouTube red, Article blue), status dots, clickable URLs
- **Citation pills** (monospace badges with source IDs) provide provenance throughout
- **Accordion pattern** for secondary content (Key Moments, Thumbnails) is good progressive disclosure
- **ProseBlock** uses proper markdown rendering with prose-invert

### What's Broken
- **Massive hardcoded color problem.** 998 instances of `text-zinc-*`, `bg-zinc-*`, `text-gray-*`, `bg-gray-*` across components. These bypass the CSS variable system entirely. Examples: `text-zinc-100`, `bg-zinc-800/30`, `text-zinc-500`, `bg-zinc-900/40`. If the design system colors change, all 998 references need manual updating.
- **Font sizes use pixel-like syntax** (`text-[10px]`, `text-[11px]`, `text-[12px]`, `text-[13px]`, `text-[14px]`, `text-[15px]`). This is arbitrary -- no type scale. Some text is literally 10px which is too small for readability.
- **Citation pills are not clickable links.** They show source IDs but don't navigate to the source URL. `onClick` prop exists but is never wired.
- **Source Ledger URLs open in new tab** but have no external-link icon indicator.
- **Title Options grid** doesn't indicate which title is recommended (if any).

### What's Missing
- **Copy-to-clipboard** on key content blocks (hooks, title options, quotes)
- **Highlight/bookmark** individual sections for script writing
- **Source link on citation pills** -- click SRC_1 to jump to the source in Source Ledger
- **Visual hierarchy improvement** -- Story Core section should be more prominent (larger text, more spacing)
- **Print/export styles** -- document renderers need print-friendly CSS

### Files Needing Attention
- ALL files in `components/document-v2/` -- replace hardcoded zinc/gray with CSS variable classes
- `components/document-v2/shared/citation-pill.tsx` -- wire onClick to navigate to source
- `components/document-v2/creator-brief-renderer.tsx` -- hero styling for story core
- `components/document-v2/shared/section-header.tsx` -- consistent type scale

---

## 6. Iteration/Chat Experience

**Score: 4/10**

### What's Good
- Sheet-based side panel is a good pattern -- doesn't replace current view
- Two tabs (Iterate + Brainstorm) separate concerns
- Mode selector with 6 options covers the backend capability
- Error handling with inline messages
- Sheet auto-closes on successful iteration

### What's Broken
- **Terminology is backend-facing.** "Deep Dive", "Expand Sources", "Go Deeper", "Different Angle", "Custom", "Inline Edit" -- a creator would not know the difference between "Deep Dive" and "Go Deeper". These map to backend pipeline modes, not user mental models.
- **No mode descriptions.** The mode select dropdown shows labels only -- no hint about what each mode does. Wizard Step 3 at least has descriptions per option; ChatSheet does not.
- **Sheet is only 320px wide** (w-80) -- very narrow for a text input + mode selector. Feels cramped.
- **No history.** Previous iterations are not visible. User can't see what they asked before or compare versions.
- **Brainstorm tab context is disconnected.** It takes a freeform topic but doesn't pre-fill from the current job's topic.
- **"Run Iteration" button** -- sounds like a CLI command, not a creator action.

### What's Missing
- **Mode descriptions** with expected outcome ("Deep Dive: Finds gaps and gives you new research directions")
- **Quick-action buttons** instead of dropdown: "Find what's missing", "Add more sources", "Try a different angle"
- **Iteration history** -- show previous iterations with timestamps and what changed
- **Pre-fill brainstorm topic** from current job topic
- **Suggested prompts** per mode to reduce blank-text-area anxiety
- **Progress indication** after submitting iteration (currently just closes sheet)

### Files Needing Attention
- `components/job-detail-v2/chat-sheet.tsx` -- complete redesign needed
- `components/job-detail-v2/job-right-panel.tsx` -- quick action buttons
- `components/job-detail-v2/version-selector.tsx` -- surface iteration history

---

## 7. Mobile Responsiveness

**Score: 7/10**

### What's Good
- **Proper breakpoint handling**: mobile (<768), tablet (768-1279), desktop (1280+)
- **ThreeColumnLayout** is genuinely well-built: collapsible left panel, bottom sheet for right panel, FAB trigger
- **Mobile header** with hamburger + logo + avatar -- standard pattern done correctly
- **Sheet-based mobile sidebar** auto-closes on navigation
- **iOS zoom prevention** (`font-size: 16px !important` on inputs below 640px)
- **Safe area insets** for notched devices
- **Touch target minimum** 44x44px on mobile nav buttons
- **Tap highlight** using primary token

### What's Broken
- **Wizard dialog on mobile** -- `max-w-lg` Dialog is not mobile-optimized. The 4-step wizard in a modal on a phone screen is cramped.
- **Dashboard stat cards** grid `grid-cols-2` on mobile -- 4 cards in 2x2 with labels like "TOTAL JOBS" in 10px uppercase is very small.
- **Source entry cards in wizard Step 2** -- nested inputs inside cards inside a modal is deep nesting on mobile.
- **Document viewer ScrollArea** `h-[calc(100vh-280px)]` -- magic number that may not work on all mobile viewports (address bar, bottom nav, keyboard).

### What's Missing
- **Swipe gestures** between documents on mobile
- **Bottom navigation** for mobile instead of relying on hamburger menu
- **Pull-to-refresh** on dashboard
- **Mobile-specific empty states** (smaller illustrations, more concise copy)
- **Document viewer full-screen mode** on mobile

### Files Needing Attention
- `components/dashboard/job-creation-wizard.tsx` -- full-screen on mobile instead of Dialog
- `components/dashboard/dashboard-stats.tsx` -- simplify for mobile (2 most important stats)
- `components/job-detail-v2/document-viewer.tsx` -- replace magic calc with proper layout
- `components/layout/three-column-layout.tsx` -- consider swipe for doc navigation

---

## 8. Accessibility

**Score: 7/10**

### What's Good
- **SkipLink** to #main-content -- WCAG 2.4.1 compliance
- **Focus-visible styles** defined globally with ring token
- **`prefers-reduced-motion`** respected globally (animation-duration: 0.01ms)
- **`role="alert"` and `aria-live`** on login error/success messages
- **`role="status"` and `aria-live="polite"`** on pipeline status bar
- **`role="button"` + `tabIndex={0}` + `onKeyDown`** on DashboardJobCard -- keyboard navigable cards
- **`aria-label`** on hamburger menu, search inputs, sort selects, dismiss buttons
- **`aria-hidden="true"`** on decorative icons (Lucide)
- **`.motion-safe:animate-*`** used for non-essential animations (pulse dots)
- **`focus-visible:ring-2`** on interactive elements

### What's Broken
- **Color contrast concern in dark mode.** `text-zinc-500` (#71717a) on `bg-zinc-900` (#18181b) = ~3.8:1 ratio -- fails WCAG AA for normal text (needs 4.5:1). This is used extensively for labels and meta text.
- **`text-[10px]` size** -- 10px text fails readability guidelines. Minimum should be 12px for body text.
- **Select elements** in wizard (source type, sort) use native `<select>` instead of shadcn Select -- inconsistent focus behavior.
- **No `aria-current="page"`** on active sidebar nav items.
- **CitationPill** has `onClick` but no keyboard handler and no `role="button"`.
- **DashboardJobCard** uses `role="button"` but should be a `<Link>` or `<a>` for proper semantics.

### What's Missing
- **Announce route changes** for screen readers (Next.js doesn't do this by default)
- **`aria-describedby`** on form fields linking to help text
- **Error summary** on form validation -- not just inline messages
- **High contrast mode** support
- **`aria-current="page"`** on active nav items

### Files Needing Attention
- `components/document-v2/` -- audit all `text-zinc-500` / `text-[10px]` for contrast
- `components/dashboard/DashboardJobCard.tsx` -- convert to Link component
- `components/document-v2/shared/citation-pill.tsx` -- add keyboard handler
- `components/layout/sidebar-nav.tsx` -- add aria-current

---

## 9. Performance Perception

**Score: 6/10**

### What's Good
- **Skeleton screens** used for job list loading (6 skeleton cards in grid)
- **Loading skeleton** on job detail page (3-column skeleton layout)
- **Smooth progress bar transitions** (`transition-all duration-500 ease-out`)
- **Spinner component** exists and is used for submit buttons
- **TanStack Query** for data fetching with proper loading/error states
- **`display: 'swap'`** on Inter font -- prevents FOIT
- **Loading.tsx** in app/(app) for route-level loading

### What's Broken
- **No skeleton on dashboard stats** -- stats flicker from 0 to actual numbers
- **Wizard step transitions are instant** -- no animation between steps, feels jarring
- **Completion banner** animation uses `animate-in` class but fade-in is very brief
- **Document content has no streaming effect** -- even though the spec mentions "streaming text", documents appear all-at-once after full pipeline completion
- **StartInput placeholder rotation** every 4 seconds is a re-render but no crossfade animation
- **Large document renders** (creator brief with many sections) have no virtualization

### What's Missing
- **Streaming text animation** for document content as it's generated
- **Skeleton screens for stats** cards while loading
- **Step transition animation** in wizard (slide/fade between steps)
- **Placeholder crossfade** on StartInput
- **Optimistic UI** -- show job card immediately on creation before API confirms
- **Virtual scrolling** for large document content

### Files Needing Attention
- `components/dashboard/dashboard-stats.tsx` -- add skeleton loading state
- `components/dashboard/job-creation-wizard.tsx` -- add step transitions
- `components/dashboard/StartInput.tsx` -- animate placeholder changes
- `components/job-detail-v2/document-viewer.tsx` -- streaming text effect

---

## 10. Visual Consistency

**Score: 4/10**

### What's Good
- **CSS variable theming system** is well-structured: surface hierarchy (0-3), semantic tokens (background, foreground, card, etc.)
- **shadcn/ui components** used consistently (Button, Card, Badge, Dialog, Sheet, Tabs, Accordion, ScrollArea, Select)
- **Lucide icons** used as primary icon set
- **Z-index scale** defined in tailwind config (base, sticky, sidebar, header, overlay, modal, toast)
- **Custom glow shadows** defined as design tokens (`shadow-glow-blue`, etc.)
- **Accent color utilities** defined in globals.css (`text-accent-blue`, `bg-accent-green`, etc.)

### What's Broken
- **CRITICAL: 998 hardcoded color references.** Components use `text-zinc-*`, `bg-zinc-*`, `text-gray-*`, `bg-gray-*` instead of semantic CSS variable classes. This is the single biggest design system violation. The entire document-v2/ directory, login form, StartInput, and many others bypass the token system.
- **Font mismatch.** Design spec says Plus Jakarta Sans, code uses Inter. Tailwind config references `--font-inter`.
- **Inconsistent font sizing.** Mix of Tailwind classes (`text-xs`, `text-sm`, `text-base`) and arbitrary values (`text-[10px]`, `text-[11px]`, `text-[13px]`, `text-[14px]`, `text-[15px]`). No type scale.
- **Emoji usage for icons.** Document viewer empty state uses emoji document icon. Error state uses emoji warning. Source ledger uses emoji checkmarks/warnings. Should use Lucide icons.
- **Two CSS systems.** `globals.css` in app/ and `styles/globals.css` for pages/ -- the design-system.md documents different hex values than what globals.css actually uses.
- **CTA orange (#F97316) is barely used.** It appears in only 12 instances across 10 files, mostly for status indicators rather than CTAs. No primary CTA button uses orange.
- **Border inconsistency.** Some components use `border-border` (semantic), others use `border-zinc-600/30`, `border-zinc-700/40`, `border-indigo-800/20` (hardcoded).
- **Gradient inconsistency.** Sidebar and New Research button use `from-accent-blue to-accent-purple`, login uses `from-blue-600 to-blue-500`, dashboard button uses `from-primary to-purple-500`.

### What's Missing
- **Type scale definition** -- establish rem-based scale (e.g., xs: 0.75rem, sm: 0.875rem, base: 1rem, lg: 1.125rem)
- **Font migration** to Plus Jakarta Sans
- **Color token migration** -- replace all 998 hardcoded references
- **Component-level design tokens** -- button sizes, card padding, spacing scale
- **CTA color integration** -- use F97316 orange for primary CTAs
- **Icon consistency audit** -- replace all emoji with Lucide equivalents

### Files Needing Attention
- `app/globals.css` -- add Plus Jakarta Sans, extend token palette
- `app/layout.tsx` -- swap Inter for Plus Jakarta Sans
- `tailwind.config.js` -- add font family, type scale
- `components/document-v2/**` -- all renderers need color token migration (largest effort)
- `components/auth/login-form.tsx` -- replace hardcoded gray/blue with tokens
- `components/dashboard/StartInput.tsx` -- replace hardcoded colors

---

## Priority Fix List (Top 10 by Impact)

### 1. Replace hardcoded colors with CSS variable tokens (Impact: 10/10)
**Effort:** Large (998 instances across ~100 files)
**Why:** The #1 design system debt. Every `text-zinc-*`, `bg-zinc-*`, `text-gray-*`, `bg-gray-*` must map to semantic tokens (`text-foreground`, `text-muted-foreground`, `bg-card`, `bg-secondary`, etc.). Without this, any design system change requires touching every file.
**Key files:** All `components/document-v2/`, `components/auth/`, `components/dashboard/StartInput.tsx`

### 2. Rewrite copy in creator language (Impact: 9/10)
**Effort:** Small-medium
**Why:** The product speaks engineer, not creator. Every user-facing string needs audit: "Research Agent" -> branded name, "Dashboard / Your research hub" -> welcome with personality, "Iterate" -> "Refine", "Deep Dive" -> "Find what's missing", "Semantic Brief" -> "Key Findings", etc.
**Key files:** `dashboard-content.tsx`, `chat-sheet.tsx`, `document-nav.tsx`, `document-viewer.tsx`, `wizard-step-mode.tsx`

### 3. Add value proposition to login and empty states (Impact: 9/10)
**Effort:** Small
**Why:** First impression determines whether a creator signs up. Currently zero indication this is for YouTube creators. Add the positioning statement, example use cases, and social proof.
**Key files:** `login-form.tsx`, `recent-jobs-list.tsx` (empty state), `dashboard-content.tsx`

### 4. Migrate font from Inter to Plus Jakarta Sans (Impact: 7/10)
**Effort:** Small
**Why:** Design spec mandates Plus Jakarta Sans. Inter is a fine font but doesn't match the "vibrant & block-based" personality. Plus Jakarta Sans is bolder, more geometric, more modern.
**Key files:** `app/layout.tsx`, `tailwind.config.js`

### 5. Redesign iteration experience as quick-action cards (Impact: 8/10)
**Effort:** Medium
**Why:** The ChatSheet is the power feature but is hidden behind a small purple button. Replace dropdown+textarea with visual quick-action cards: "Find what's missing", "Add more sources", "Try a different angle" with descriptions and expected outcomes.
**Key files:** `chat-sheet.tsx`, `job-right-panel.tsx`

### 6. Show stage descriptions and ETA during pipeline (Impact: 7/10)
**Effort:** Small
**Why:** The descriptions are already written in STAGE_LABELS but never rendered. Just wire them in. For ETA, even a rough "Usually takes 2-5 minutes" per pipeline mode would dramatically improve wait experience.
**Key files:** `pipeline-status-bar.tsx`, `job-center-panel.tsx`, `DashboardJobCard.tsx`

### 7. Wire citation pills to navigate to source URLs (Impact: 7/10)
**Effort:** Small-medium
**Why:** Citation pills (SRC_1, SRC_2) appear throughout every document but do nothing. Making them clickable to jump to the source in Source Ledger (or open the URL) transforms them from decoration to research tool.
**Key files:** `components/document-v2/shared/citation-pill.tsx`, document renderers

### 8. Establish consistent type scale (Impact: 6/10)
**Effort:** Medium
**Why:** 7 arbitrary pixel sizes (10-15px) create visual noise. Define a scale: caption (11px), body-sm (13px), body (14px/15px), heading (16px+). Remove all `text-[10px]` -- minimum 11px for any visible text.
**Key files:** All `components/document-v2/`, `tailwind.config.js`

### 9. Redesign wizard Step 3 (Mode) as visual card selector (Impact: 6/10)
**Effort:** Medium
**Why:** A dropdown with 6 pipeline modes is cognitive overload. Show 2-3 cards: "Quick Overview" (icon + "~2 min, get the gist"), "Full Research" (icon + "~5 min, everything you need"), "Deep Investigation" (icon + "~10 min, leave no stone unturned"). Hide advanced modes behind "More options".
**Key files:** `wizard-step-mode.tsx`, `wizard-step-preview.tsx`

### 10. Add skeleton loading for dashboard stats + wizard transitions (Impact: 5/10)
**Effort:** Small
**Why:** Stats flicker from 0 to real values. Wizard steps swap instantly. Both make the UI feel unfinished. Add skeleton states for stats and framer-motion transitions for wizard steps.
**Key files:** `dashboard-stats.tsx`, `job-creation-wizard.tsx`

---

## Summary Scoreboard

| Area | Score | Verdict |
|------|-------|---------|
| 1. First Impressions | 4/10 | Generic SaaS, no creator identity |
| 2. Job Creation Wizard | 5/10 | Functional but speaks backend |
| 3. Progress/Waiting | 5/10 | Data exists, not surfaced |
| 4. Results Page | 6/10 | Good architecture, weak content strategy |
| 5. Document Rendering | 7/10 | Rich renderers, massive color debt |
| 6. Iteration/Chat | 4/10 | Needs complete UX rethink |
| 7. Mobile Responsiveness | 7/10 | Well-built, few gaps |
| 8. Accessibility | 7/10 | Strong foundation, contrast issues |
| 9. Performance Perception | 6/10 | Basics covered, streaming missing |
| 10. Visual Consistency | 4/10 | Token system exists but 998 violations |
| **Overall** | **5.2/10** | **Functional prototype, not product** |

---

## Unresolved Questions

1. Is the product name staying "Research Agent" or getting a branded name? Login/sidebar both show "Research Agent" which is generic.
2. Is the `pages/` directory still active alongside `app/`? Two CSS systems (globals.css + styles/globals.css) suggest legacy code. Should be cleaned up.
3. What's the actual pipeline time per mode? Need backend data to show realistic ETAs.
4. Is Doc 4 (Producer Packet) still opt-in or auto-generated? The docExists function only checks docs 0-4 but renderers exist for 5-7 (Script, Social Kit, Blog Post).
5. Is `StartInput.tsx` (the smart input with intent detection) the intended replacement for the wizard? Both exist but seem to serve the same purpose.
6. Are the `components/job-card/`, `components/job-detail/`, and `components/document/` directories legacy? They seem to be older versions of `job-detail-v2/` and `document-v2/`.
