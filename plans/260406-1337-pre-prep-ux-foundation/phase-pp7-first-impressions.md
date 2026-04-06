# Phase PP-7: First Impressions & Onboarding

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 2-3 days
- **Depends on:** PP-2 (font), PP-3 (copy)
- **Description:** Make the login page and empty dashboard communicate "this is for YouTube creators" in the first 5 seconds.

## Key Insights
- Login page says "Research Agent / Sign in to your account" — most generic SaaS copy possible
- Empty dashboard says "Start Your First Research / Extract insights from YouTube videos, web articles, and documents" — feature-speak
- No onboarding flow for new users
- No visual identity beyond a flask icon
- Positioning statement appears nowhere in UI

## Requirements

### Login Page
- Positioning statement prominent: "Turn any collection of videos and articles into a verified, source-cited script — with the angle nobody else covered."
- 3 brief benefit bullets:
  - "Drop YouTube links — we watch them for you"
  - "Get the angle nobody else covered"
  - "Source-cited scripts, not AI fluff"
- Keep Google OAuth + magic link auth (already working)

### Empty Dashboard (First-Time User)
- Welcome message: "What's your next video about?"
- 3 example use cases as clickable cards:
  - "Research a trending topic" → pre-fills wizard with example
  - "Analyze competitor videos" → pre-fills with example
  - "Deep dive into a story" → pre-fills with example
- Each card: icon + title + one-line description

### Returning User Dashboard
- Keep current layout (stats + job list)
- But rename stats (from PP-3)

## Related Code Files

| File | Change |
|------|--------|
| `components/auth/login-form.tsx` | Add positioning statement, benefit bullets |
| `components/dashboard/dashboard-content.tsx` | New first-time user welcome |
| `components/dashboard/recent-jobs-list.tsx` | Redesign empty state |
| `store/jobs.ts` | Check if user has zero jobs (for first-time detection) |

## Implementation Steps

### Task PP-7.1: Redesign login page
1. In `login-form.tsx`:
   - Add h1 with positioning statement (or a shorter variant)
   - Add 3 benefit bullets below the heading
   - Keep existing auth form below
   - Style: bold heading (text-2xl font-bold), bullets with Lucide icons
2. Optional: add a subtle background pattern or illustration

### Task PP-7.2: Create first-time user welcome
1. In `dashboard-content.tsx`: detect if user has 0 jobs
2. If first time: show welcome hero instead of stats + empty job list
3. Welcome hero:
   - "What's your next video about?" (large heading)
   - 3 example cards in a grid
   - Each card clicks to open wizard with pre-filled topic
4. If returning: show normal dashboard

### Task PP-7.3: Redesign empty state
1. In `recent-jobs-list.tsx`: if job list is empty after initial load:
   - Show "No projects yet" with an illustration or Lucide icon
   - "Start by pasting some YouTube links" with arrow pointing to New Project button
2. Keep it brief — the first-time welcome handles the heavy lifting

### Task PP-7.4: Remove "API Spend" stat card
1. In `dashboard-stats.tsx`: remove the "API Spend" card with "Coming soon" dash
2. Keep: Projects, Completed, In Progress (renamed from PP-3)
3. Or replace with "Credits Remaining" placeholder for future credit system

### Task PP-7.5: Verify
1. New user login → sees positioning statement
2. First dashboard visit → sees welcome with examples
3. After creating first job → sees normal dashboard with stats
4. No "Coming soon" placeholders visible
5. `npm run build` passes

## Todo Checklist
- [ ] PP-7.1 Redesign login page with positioning + benefits
- [ ] PP-7.2 Create first-time user welcome hero
- [ ] PP-7.3 Redesign empty state for job list
- [ ] PP-7.4 Remove "API Spend" stat card
- [ ] PP-7.5 Verify first-time + returning user flows + build

## Success Criteria
- New user sees positioning statement within 5 seconds of landing on login
- First dashboard visit has clear call-to-action with examples
- No "Coming soon" or half-built features visible
- Build passes
