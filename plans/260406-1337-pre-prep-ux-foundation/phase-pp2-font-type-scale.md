# Phase PP-2: Font & Type Scale

## Overview
- **Priority:** P0
- **Status:** completed
- **Effort:** 1-2 days
- **Description:** Migrate from Inter to Plus Jakarta Sans. Establish consistent type scale. Remove all arbitrary pixel sizes.

## Key Insights
- Design spec says Plus Jakarta Sans; code uses Inter
- 7 arbitrary pixel sizes: `text-[10px]`, `text-[11px]`, `text-[12px]`, `text-[13px]`, `text-[14px]`, `text-[15px]`
- `text-[10px]` fails readability guidelines (minimum 11px)
- No defined type scale — mix of Tailwind defaults and arbitrary values

## Requirements

### Functional
- Plus Jakarta Sans as primary font (all weights: 300-700)
- Defined type scale used consistently:
  - `text-caption` (11px/0.6875rem) — meta, timestamps
  - `text-body-sm` (13px/0.8125rem) — secondary content
  - `text-body` (14px/0.875rem) — primary body text
  - `text-body-lg` (15px/0.9375rem) — emphasized body
  - Tailwind defaults for headings (text-lg, text-xl, text-2xl)
- Zero `text-[Npx]` arbitrary values in components
- Minimum 11px for any visible text

## Related Code Files

| File | Change |
|------|--------|
| `app/layout.tsx` | Swap Inter → Plus Jakarta Sans import |
| `tailwind.config.js` | Update fontFamily, add type scale |
| `app/globals.css` | Add @font-face or Google Fonts import |
| `components/document-v2/**` | Replace arbitrary pixel sizes |

## Implementation Steps

### Task PP-2.1: Install Plus Jakarta Sans
1. In `app/layout.tsx`: replace `import { Inter } from 'next/font/google'` with `import { Plus_Jakarta_Sans } from 'next/font/google'`
2. Configure: `const plusJakarta = Plus_Jakarta_Sans({ subsets: ['latin'], variable: '--font-sans', display: 'swap', weight: ['300', '400', '500', '600', '700'] })`
3. Update `<body className={plusJakarta.variable}>` (or however Inter is applied)
4. In `tailwind.config.js`: update `fontFamily.sans` to reference `--font-sans`

### Task PP-2.2: Define type scale in Tailwind config
1. Add to `tailwind.config.js` theme.extend.fontSize:
```js
fontSize: {
  'caption': ['0.6875rem', { lineHeight: '1rem' }],      // 11px
  'body-sm': ['0.8125rem', { lineHeight: '1.25rem' }],   // 13px
  'body': ['0.875rem', { lineHeight: '1.375rem' }],      // 14px
  'body-lg': ['0.9375rem', { lineHeight: '1.5rem' }],    // 15px
}
```

### Task PP-2.3: Replace arbitrary pixel sizes
1. `grep -rn "text-\[1[0-5]px\]" components/` — find all instances
2. Map replacements:
   - `text-[10px]` → `text-caption` (bump from 10 to 11px)
   - `text-[11px]` → `text-caption`
   - `text-[12px]` → `text-body-sm` (bump to 13px)
   - `text-[13px]` → `text-body-sm`
   - `text-[14px]` → `text-body`
   - `text-[15px]` → `text-body-lg`
3. Review each change for visual appropriateness

### Task PP-2.4: Verify
1. `npm run build` passes
2. Visual check: font renders correctly, sizes consistent
3. No `text-[` arbitrary values remaining in components

## Todo Checklist
- [x] PP-2.1 Install Plus Jakarta Sans, update layout + tailwind config
- [x] PP-2.2 Define type scale in tailwind config
- [x] PP-2.3 Replace all arbitrary pixel font sizes
- [x] PP-2.4 Build passes, visual check

## Success Criteria
- `grep -rn "text-\[.*px\]" components/` returns 0 results (for font sizes)
- Plus Jakarta Sans renders in browser
- Minimum text size is 11px
- Build passes
