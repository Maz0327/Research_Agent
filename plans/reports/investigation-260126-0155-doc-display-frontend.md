# Investigation: Document Display on Frontend

**Date:** 2026-01-26
**Branch:** `claude/investigate-doc-display-aa05B`
**Status:** ✅ VERIFIED - Documents display as styled HTML, not raw markdown

---

## Summary

Output documents are **NOT displayed in raw markdown format**. They are converted to styled HTML before rendering. Users see properly formatted content (headings, bold text, lists) - not markdown syntax like `# Heading` or `**bold**`.

Downloads available: PDF, Markdown, JSON, Clipboard.

---

## Current Implementation

### Display Flow

```
Stored Markdown → transformMarkdownWithDetails() → MarkdownRenderer() → Styled HTML
```

1. **Storage**: Documents stored as markdown in cloud storage
2. **Transform**: Internal IDs converted to friendly labels (`SRC_1` → "Source 1")
3. **Render**: Markdown parsed to HTML with Tailwind CSS styling
4. **Output**: User sees formatted content, NOT raw markdown

### Key Components

| File | Purpose |
|------|---------|
| `DocumentViewerModal.tsx` | Full-screen document viewer with MarkdownRenderer |
| `DocumentCard.tsx` | Card display with download options (PDF/MD/JSON) |
| `document-formatters.ts` | Transforms IDs + heading labels |
| `pdf-export.ts` | Client-side PDF generation |
| `pages/shared/[token].tsx` | Public shared document view |

### MarkdownRenderer Function

Located in `DocumentViewerModal.tsx:293-330` and `[token].tsx:284-321`:

```tsx
function MarkdownRenderer({ content }: { content: string }) {
  const parseMarkdown = (text: string): string => {
    return text
      .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold...">$1</h1>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold...">$1</strong>')
      // ... more transformations
  };

  const sanitizedHtml = DOMPurify.sanitize(parseMarkdown(content));
  return <div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />;
}
```

**Result**: User sees "Key Takeaways" as a styled heading, not `## Key Takeaways`

### Download Options

| Format | How Generated | File |
|--------|---------------|------|
| **PDF** | html2pdf.js client-side | `DocumentCard.tsx:118-168` |
| **Markdown** | Raw .md blob download | `DocumentCard.tsx:97-108` |
| **JSON** | Raw JSON blob download | `DocumentCard.tsx:85-95` |
| **Clipboard** | navigator.clipboard API | `DocumentCard.tsx:111-115` |

### Presentation Layer Transforms

`document-formatters.ts` applies user-friendly labels:

| Internal ID | Display Label |
|-------------|---------------|
| `SRC_1` | Source 1 |
| `KP_12` | Key Point 12 |
| `THEME_2` | Theme 2 |
| `GAP_3` | Open Question 3 |

Section headings also normalized:
- `Key Points` → "Key Takeaways"
- `Research Gaps` → "Open Questions"
- `Cross-Source Themes` → "Common Themes"

---

## Verification

### What Users SEE (Display)

```
┌────────────────────────────────────────────┐
│  Key Takeaways                      (h2)   │
│                                            │
│  • Source 1 reveals that AI adoption...    │
│  • Theme 2 shows conflicting views...      │
│                                            │
│  Open Questions                     (h2)   │
│                                            │
│  1. What are the long-term effects...      │
└────────────────────────────────────────────┘
```

### What Users DON'T SEE

```
## Key Points

- **SRC_1** reveals that AI adoption...
- **THEME_2** shows conflicting views...

## Research Gaps

1. What are the long-term effects...
```

---

## Conclusion

✅ **Display**: Rendered as styled HTML (headings, bold, lists) - NOT raw markdown
✅ **PDF Download**: Available via html2pdf.js
✅ **Markdown Download**: Available as .md file
✅ **JSON Download**: Available for raw data

The implementation matches user requirements.

---

## Files Reviewed

- `frontend/components/job-card/DocumentViewerModal.tsx`
- `frontend/components/job-card/DocumentCard.tsx`
- `frontend/components/job-card/DocumentCardGrid.tsx`
- `frontend/lib/document-formatters.ts`
- `frontend/lib/pdf-export.ts`
- `frontend/pages/shared/[token].tsx`
