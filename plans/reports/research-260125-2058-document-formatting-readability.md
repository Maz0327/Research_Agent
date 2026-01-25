# Research Report: Document Output Formatting for Readability

**Date:** 2026-01-25
**Focus:** Improving Doc 0, Doc 1, Doc 2 markdown output for better readability

---

## Executive Summary

Current document formatting is functional but dense. Research indicates applying modern UX writing principles, visual hierarchy, and scannability techniques can significantly improve comprehension. Key opportunities: GitHub alerts, summary cards, better whitespace, progressive disclosure.

---

## Current State Analysis

### Strengths
- Clear heading hierarchy (H1 → H2 → H3)
- Uses tables for structured data
- Collapsible `<details>` for full text
- Status indicators present

### Weaknesses
- Dense text blocks without breathing room
- No callout/admonition boxes for key info
- Lists lack visual separation
- No TL;DR or executive summary sections
- Confidence/warnings buried in flow

---

## Recommendations

### 1. GitHub Alerts for Key Information

**Current:**
```markdown
> **Warning:** This brief is based on limited sources.
```

**Recommended:**
```markdown
> [!WARNING]
> This brief is based on limited or one-sided sources.
> Confidence ceiling: MEDIUM
```

**Available alert types:**
- `[!NOTE]` - Background info
- `[!TIP]` - Helpful suggestions
- `[!IMPORTANT]` - Key information users need
- `[!WARNING]` - Potential issues
- `[!CAUTION]` - Critical warnings

**Apply to:**
- Degraded output warnings (Doc 2)
- Failed source notices (Doc 0)
- Confidence assessments
- Verification status

### 2. Executive Summary Cards at Top

**Add to each document:**

```markdown
# SOURCE LEDGER

> [!NOTE]
> **Quick Stats:** 5 sources | 4 ingested | 1 failed | Confidence: HIGH

| Metric | Value |
|--------|-------|
| Total Sources | 5 |
| Transcript Quality | 3 HIGH, 1 MEDIUM, 1 FAILED |
| Coverage | YouTube (3), Articles (2) |
```

### 3. Better Whitespace & Visual Chunking

**Problem:** Sections run together without clear separation.

**Solutions:**

a) **Add blank lines around sections:**
```markdown
---

## SECTION TITLE

Content here...

---
```

b) **Use horizontal rules strategically** (not excessively)

c) **Add section numbering for navigation:**
```markdown
## 1. Source Manifest
## 2. Detailed Analysis
## 3. Quality Assessment
```

### 4. Scannability Improvements

**a) Bold key terms in flowing text:**
```markdown
- KP_1: **Transcript accuracy** impacts downstream claim verification.
  Sources: SRC_1, SRC_2
```

**b) Lead with the most important info:**
```markdown
## KEY POINTS

| ID | Statement | Confidence | Sources |
|----|-----------|------------|---------|
| KP_1 | Main claim here... | HIGH | SRC_1, SRC_2 |
```

**c) Use emoji sparingly for status:**
- ✅ Ingested
- ⚠️ Partial
- ❌ Failed

### 5. Progressive Disclosure

**Already using `<details>` for full text. Extend to:**

```markdown
<details>
<summary><strong>View all 12 key points</strong></summary>

| ID | Statement | Confidence |
|----|-----------|------------|
...

</details>
```

**Apply to:**
- Key points (show top 5, collapse rest)
- Claims list
- Verification items
- Entity lists

### 6. Confidence & Quality Callouts

**Replace:**
```markdown
Overall Confidence: Medium

Reasoning:
- Multiple sources available
- 1 source failed
```

**With:**
```markdown
> [!IMPORTANT]
> **Confidence: MEDIUM**
>
> | Factor | Impact |
> |--------|--------|
> | Multiple sources | +Positive |
> | 1 failed source | -Negative |
> | No expert sources | -Negative |
```

### 7. Source Entry Cards (Doc 0)

**Current format is good but add:**

```markdown
### SRC_1: Video Title Here

> 📺 **YOUTUBE** | ✅ INGESTED | ⏱️ 12:34 | 📅 2024-06-15

| Field | Value |
|-------|-------|
| Creator | Channel Name |
| Transcript | Supadata (HIGH confidence) |
| Word Count | 2,450 |

#### Quick Summary
- Point one
- Point two
- Point three
```

### 8. Table of Contents for Long Documents

**Add at top of Doc 0 and Doc 2:**

```markdown
## Contents
1. [Overview](#overview)
2. [Source Manifest](#source-manifest)
3. [Detailed Analysis](#detailed-analysis)
   - [SRC_1: Title](#src_1-title)
   - [SRC_2: Title](#src_2-title)
```

### 9. Color-Coded Confidence Badges

**In tables, use inline formatting:**

```markdown
| Claim | Confidence |
|-------|------------|
| Statement... | **🟢 HIGH** |
| Statement... | **🟡 MEDIUM** |
| Statement... | **🔴 LOW** |
```

### 10. Gap/Tension Severity Indicators

```markdown
## GAPS & WEAKNESSES

> [!CAUTION]
> **Critical Gap:** No primary source verification available

### GAP_1: Missing Expert Perspective
**Severity:** High
**Impact:** Limits claim confidence
**Suggested Action:** Search for academic sources
```

---

## Implementation Priority

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| 1 | GitHub alerts for warnings | Low | High |
| 2 | Executive summary at top | Medium | High |
| 3 | Better whitespace/spacing | Low | Medium |
| 4 | Confidence callout boxes | Low | Medium |
| 5 | Progressive disclosure for lists | Medium | Medium |
| 6 | Table of contents | Low | Medium |
| 7 | Emoji status indicators | Low | Low |
| 8 | Source entry cards | Medium | Medium |

---

## Code Changes Required

### Files to Modify

1. **`backend/models/document_outputs.py`**
   - `SourceEntry.to_markdown()` - Add emoji badges, card format
   - `SourceLedger.to_markdown()` - Add TOC, executive summary, alerts
   - `JumpStartDirections.to_markdown()` - Add alerts, better spacing
   - `SemanticBrief.to_markdown()` - Add alerts, confidence cards

2. **Helper functions to add:**
   - `_render_github_alert(type, content)`
   - `_render_confidence_badge(level)`
   - `_render_summary_card(stats)`
   - `_render_toc(sections)`

---

## Example: Improved Doc 0 Header

```markdown
# SOURCE LEDGER

> [!NOTE]
> **Research Topic:** Impact of AI on software development
>
> **Quick Stats:** 5 sources | 4 ingested | 1 failed

| Metric | Count | Details |
|--------|-------|---------|
| Total Sources | 5 | 3 YouTube, 2 Articles |
| Successfully Ingested | 4 | ✅ |
| Failed | 1 | ❌ Network timeout |
| Transcript Quality | - | 2 HIGH, 1 MEDIUM, 1 VIDEO_ONLY |

> [!WARNING]
> 1 source failed to process. Results may be incomplete.

---

## Contents
1. [Source Manifest](#source-manifest)
2. [Detailed Analysis](#detailed-analysis)

---

## Source Manifest

| # | ID | Type | Title | Status | Confidence |
|---|-----|------|-------|--------|------------|
| 1 | SRC_1 | YouTube | Video Title... | ✅ Ingested | 🟢 HIGH |
| 2 | SRC_2 | Article | Article Title... | ✅ Ingested | 🟡 MEDIUM |
| 3 | SRC_3 | YouTube | Another Video... | ❌ Failed | - |
```

---

## Sources

- [Markdown Best Practices - ToMarkdown](https://www.tomarkdown.org/guides/markdown-best-practice)
- [Google Markdown Style Guide](https://google.github.io/styleguide/docguide/style.html)
- [10 Markdown Tips for Documentation 2025 - DEV](https://dev.to/auden/10-markdown-tips-for-creating-beautiful-product-documentation-in-2025-5ek4)
- [Typography Best Practices 2025 - adoc Studio](https://www.adoc-studio.app/blog/typography-guide)
- [Scannability UX Guide - CareerFoundry](https://careerfoundry.com/en/blog/ux-design/scannability/)
- [Admonitions & Callouts - Splunk Docs](https://docs.splunk.com/Documentation/StyleGuide/current/StyleGuide/Notesandcautions)
- [GitHub Alerts Syntax - MarkdownTools](https://blog.markdowntools.com/posts/markdown-admonitions-callouts-complete-guide)
- [Card UI Design - Justinmind](https://www.justinmind.com/ui-design/cards)

---

## Unresolved Questions

1. **Emoji compatibility:** Do all target platforms (GitHub, Notion, VS Code) render emoji consistently?
2. **GitHub alerts:** Does the frontend markdown renderer support `[!NOTE]` syntax? May need fallback to blockquotes.
3. **TOC links:** Auto-generate or manual? Auto-gen adds complexity but stays in sync.
4. **Performance:** Does adding more formatting significantly impact document generation time?
