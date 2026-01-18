# Platform OCR Guides — Index

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## Overview

These guides specify how to extract structured information from screenshots of various social media platforms and forums. All guides use **Gemini 2.5 Pro** for direct vision analysis (no separate OCR step).

---

## Platform Guide Quick Reference

| Platform | Guide File | Content Types |
|----------|------------|---------------|
| Reddit | [reddit.md](./reddit.md) | Posts, comments, threads |
| Twitter/X | [twitter.md](./twitter.md) | Tweets, threads, quote tweets, replies |
| Instagram | [instagram.md](./instagram.md) | Feed posts, Stories, Reels, comments |
| Facebook | [facebook.md](./facebook.md) | Posts, comments, groups, pages |
| TikTok | [tiktok.md](./tiktok.md) | Video posts, comments, duets, stitches |
| YouTube Comments | [youtube-comments.md](./youtube-comments.md) | Comments, community posts, live chat |
| Generic Forums | [generic-forum.md](./generic-forum.md) | Traditional forums, Q&A sites, news comments |

---

## Platform Selection Logic

```
Screenshot provided → Identify platform

1. Check for platform-specific UI elements:
   ├── Reddit UI (r/, u/, upvotes) → reddit.md
   ├── Twitter/X UI (@handles, retweets) → twitter.md
   ├── Instagram UI (stories, reels) → instagram.md
   ├── Facebook UI (reactions, share) → facebook.md
   ├── TikTok UI (FYP, sounds) → tiktok.md
   ├── YouTube comments → youtube-comments.md
   └── Other forum/discussion → generic-forum.md

2. If platform unclear:
   └── Use generic-forum.md patterns
```

---

## Common Elements Across All Platforms

### Required for ALL Screenshots

| Element | Extraction | Notes |
|---------|------------|-------|
| Author/Username | Always extract | Primary attribution |
| Content Text | Always extract | Main body text |
| Timestamp | If visible | Temporal context |
| Engagement | If visible | Likes, comments, shares |

### Platform-Specific Additions

| Platform | Unique Elements |
|----------|-----------------|
| Reddit | Subreddit, upvotes, nesting level, awards |
| Twitter/X | Handle, verification badge, retweets, views |
| Instagram | Location tag, hashtags, carousel, Story stickers |
| Facebook | Privacy level, reactions breakdown, group context |
| TikTok | Sound/audio, duet/stitch indicators, saves |
| YouTube | Creator heart, pinned status, membership badges |
| Forums | User rank, post count, quotes, signatures |

---

## OCR Confidence Guidelines

All `ocr_extracted` content has a **MEDIUM confidence ceiling** regardless of platform.

### Factors That Raise OCR Confidence

| Factor | Confidence Effect |
|--------|-------------------|
| Clear, high-resolution screenshot | Higher |
| Full content visible (not truncated) | Higher |
| Visible timestamps | Higher |
| Multiple corroborating comments | Higher |
| Platform clearly identifiable | Higher |

### Factors That Lower OCR Confidence

| Factor | Confidence Effect |
|--------|-------------------|
| Blurry or low-resolution image | Lower |
| Truncated content ("See more") | Lower |
| Missing context (replies without parent) | Lower |
| Screenshot manipulation possible | Lower |
| Engagement numbers hard to read | Lower |

---

## Edge Case Handling (Universal)

### 1. Truncated Content

**All Platforms:** If "See more", "...", or similar:
- Extract visible portion
- Note truncation in `extraction_notes`
- Do NOT invent missing content

### 2. Missing Context

**All Platforms:** If reply without parent, mid-thread, etc.:
- Extract what's visible
- Note missing context
- Flag with appropriate warning

### 3. Multiple Posts in Screenshot

**All Platforms:** Extract each post separately with unique IDs.

### 4. Mixed Platform Content

**Example:** Twitter screenshot shared on Facebook

**Handling:**
- Note the screenshot-within-screenshot
- Extract outer platform context (Facebook post)
- Extract inner platform content (Twitter screenshot)
- Note: Inner content is double-removed from source

---

## Observation Format (Universal)

All platforms output observations in this format:

```json
{
  "observation_id": "OBS_X",
  "description": "Clear description of what was observed",
  "platform": "platform_name",
  "platform_elements": {
    "username": "@user or u/user",
    "context": "Platform-specific context",
    "engagement": "Summary of engagement metrics"
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high" | "medium" | "low"
}
```

---

## Integration with Parent Mode

### `ocr_extracted` Mode Rules

These platform guides support the `ocr_extracted` analysis mode:

1. **No verbatim quotes** — All content becomes observations
2. **MEDIUM confidence ceiling** — Cannot exceed regardless of clarity
3. **Screenshot provenance** — Always note this is image-extracted
4. **Platform context required** — Must identify source platform

### Workflow

```
Screenshot → Platform Identification → Platform-Specific Extraction
                                           ↓
                              Structured JSON Output
                                           ↓
                              Observation Generation
                                           ↓
                              Integration with Doc 0/1/2
```

---

## Gemini 2.5 Pro Configuration

### Model Selection

**Model:** `gemini-2.5-pro`

**Rationale:**
- Direct vision analysis (no OCR preprocessing)
- Strong UI element recognition
- Context-aware text extraction
- Handles multiple languages
- Understands platform-specific layouts

### Prompt Structure

All platform extractions use:

```
System: You are analyzing a screenshot from [PLATFORM].
Extract structured information according to the platform guide.

PLATFORM: [platform_name]
EXTRACTION MODE: ocr_extracted

[Platform-specific extraction instructions]

Return as structured JSON.
```

### Temperature Setting

- **Temperature: 0.1** — Low for consistent extraction
- Deterministic output preferred
- Avoid creative interpretation

---

## Quality Assurance

### Validation Checks

| Check | Applies To | Action on Fail |
|-------|------------|----------------|
| Platform identified | All | Use generic-forum |
| Username extracted | All | Warning |
| Content extracted | All | Hard fail if empty |
| Valid JSON output | All | Retry |
| Confidence ≤ MEDIUM | All | Auto-downgrade |

### Human Review Triggers

| Trigger | Reason |
|---------|--------|
| OCR confidence: low | May need manual verification |
| Platform: unknown | Guide may be incomplete |
| Truncation: significant | Context may be critical |
| Manipulation suspected | Integrity concern |

---

## Future Platform Additions

To add a new platform guide:

1. Create `[platform].md` in this directory
2. Follow the existing guide structure:
   - Platform Overview
   - UI Elements to Extract
   - Extraction Prompt Template
   - Output Schema
   - Common UI Variations
   - Edge Cases
   - Observation Format
   - Platform-Specific Warnings
3. Add to this INDEX.md
4. Update parent `ocr_extracted.md` if needed

---

## Cross-References

- **Parent Mode:** `../ocr_extracted.md`
- **Mode Index:** `../INDEX.md`
- **Validation Rules:** `../../Validation_and_Retry_Rules.md`
- **Main Spec:** `../../RASS.md`

---

**END OF INDEX**
