# Dashboard UI/UX Patterns Research
**Date:** 2026-03-18 | **Max Calls:** 5 used

---

## 1. Multi-Column Dashboard Layouts (3-Column Responsive)

**Pattern:** Persistent sidebar (left) + main content (center) + optional right panel → collapses to drawer on mobile.

**Best Practice:**
- Desktop: Fixed left sidebar (sidebar persists), main content scrollable, right panel toggleable
- Tablet: Left sidebar collapses to hamburger/drawer trigger
- Mobile: Sidebar hidden by default (Sheet drawer), main content full-width, right panel → bottom sheet

**shadcn/ui Approach:**
- Use `Sheet` component with `side="left"` for mobile drawer
- Layout wrapper: `flex` grid with responsive `grid-cols-3` → `grid-cols-1`
- Navigation via config-first structure (data → component mapping)
- Popular template: **shadcn-admin** (2,800+ stars; includes responsive patterns across 10+ pages)

**Key Resources:**
- [shadcn/ui Dashboard Examples](https://ui.shadcn.com/examples/dashboard)
- [Build a Dashboard with shadcn/ui: Complete Guide (2026)](https://designrevision.com/blog/shadcn-dashboard-tutorial)

---

## 2. Circular Gauge/Progress Ring Components

**Pattern:** SVG-based circular meters for 0-100 score display (confidence, progress, metrics).

**Implementation:**
- SVG with two circles: background track + progress stroke
- Use `stroke-dasharray` + `stroke-dashoffset` for progress animation
- **Radius 16 trick:** Circumference ≈ 100, so `stroke-dasharray="100 100"` and offset = `100 - percentage`
- CSS for rotation/color, SVG for scalability

**Recommended Approach:**
- Build custom React hook wrapping SVG (lightweight, no dependencies)
- Animate with `@keyframes` or Framer Motion for smooth transitions
- Color coding: green (high), yellow (medium), red (low) confidence/status

**Accessibility:** Include `<text>` element with numeric value inside SVG for screen readers.

**Key Resources:**
- [Building a Progress Ring, Quickly | CSS-Tricks](https://css-tricks.com/building-progress-ring-quickly/)
- [How to build an SVG circular progress component using React and React Hooks](https://blog.logrocket.com/build-svg-circular-progress-component-react-hooks/)

---

## 3. Slide-Out Chat Panels (Persistent, Toggleable)

**Pattern:** Side panel for chat/AI assistant that persists but can be toggled or dismissed.

**shadcn/ui Components:**
- **Sheet** (preferred): Slide from right/left, smooth animations, portal rendering
- **Drawer**: Swipe-friendly alternative for mobile-first designs
- Focus management + ARIA roles included

**Implementation Details:**
- Pair with state hook: `const [chatOpen, setChatOpen] = useState(false)`
- Use `side="right"` for side-by-side layouts on desktop
- Add close trigger (X icon or backdrop click)
- Persistent state: Store in localStorage/URL for UX continuity

**Desktop vs Mobile:**
- Desktop: Sheet slides from right (don't block main content)
- Mobile: Sheet takes full width or bottom sheet behavior
- Never hide critical UI—consider responsive toggle placement

**Key Resources:**
- [shadcn/ui Sheet Documentation](https://ui.shadcn.com/docs/components/radix/sheet)
- [Exploring Drawer and Sheet Components in shadcn UI](https://medium.com/@enayetflweb/exploring-drawer-and-sheet-components-in-shadcn-ui-cf2332e91c40)

---

## 4. Accordion/Collapsible Card Sections (Dense Data)

**Pattern:** Multi-section accordions for condensing large datasets without overwhelming UI.

**Best Practices:**
- Limit to 5-7 sections per accordion (beyond that, show all expanded)
- Use clear chevron icons (↓ expand, ↑ collapse) + descriptive headers
- Allow **multi-active** mode for comparing sections (not forced one-open)
- Each card should be self-contained (clear titles, summary previews)

**Density Strategy:**
- Card header: Metric + status badge (e.g., "Claims: 23 | HIGH confidence")
- Collapsed state: Show summary stats only
- Expanded state: Full content with nested tables/charts
- Use grid inside cards for structured data

**Accessibility:** Keyboard navigation (arrow keys), ARIA roles for expand/collapse state.

**Key Resources:**
- [Accordion UI Examples: Best Practices & Real-World Designs](https://www.eleken.co/blog-posts/accordion-ui)
- [Designing effective accordion UIs: Best practices for UX and implementation](https://blog.logrocket.com/ux-design/accordion-ui-design/)

---

## 5. Real-Time Status Indicators & Pipeline Progress

**Pattern:** Terminal-style headers + live status badges + animated progress bars for pipeline stages.

**Components:**
- **Pulse indicators:** Animated dot (green = running, yellow = queued, red = failed)
- **Stage badges:** Color-coded status (pending, processing, complete, error)
- **Progress bar:** Linear or stepped (for multi-stage pipelines)
- **Live metrics:** Update via WebSocket or polling (show timestamp)

**Implementation:**
- Use Tailwind `animate-pulse` for status indicators
- React Flow for pipeline DAGs (visual stage nodes)
- Framer Motion for smooth status transitions
- WebSocket integration for real-time updates

**Terminal-Style Approach:**
- Monospace font for technical feel
- Dark background, bright text (green/red/yellow)
- Icon + status text (e.g., "⚙️ Processing... [████░░░░] 60%")

**Key Resources:**
- [Building a React dashboard to visualize workflow and job events](https://circleci.com/blog/react-webhook-dashboard/)
- [React Flow Pipeline Flow: Visualizing Data Pipelines](https://azimuahamed.medium.com/react-flow-pipeline-flow-visualizing-data-pipelines-and-etl-processes-b692ff8adf49)

---

## Recommendations

1. **Use shadcn/ui primitives** — Sheet, Accordion, Card, Button, Badge (consistent, accessible)
2. **Custom SVG gauges** — Avoid heavy libraries; radius-16 trick is lightweight
3. **Responsive-first** — Design mobile Sheet/Drawer behavior first, scale to desktop
4. **Limit sections** — Don't exceed 5-7 accordions; use tabs or side navigation if more data
5. **Real-time via WebSocket** — Avoid polling for status updates; reduces server load

---

## Tech Stack Summary

| Feature | Library/Pattern |
|---------|-----------------|
| Layout | shadcn/ui Sidebar + Responsive Grid |
| Gauges | Custom React hook + SVG |
| Chat Panel | shadcn/ui Sheet |
| Accordions | shadcn/ui Collapsible + Tailwind Grid |
| Status Indicators | Tailwind `animate-pulse` + Framer Motion |
| Pipeline Viz | React Flow + Custom Node Components |
