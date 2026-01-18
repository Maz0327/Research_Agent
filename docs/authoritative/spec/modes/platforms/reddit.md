# Platform OCR Guide: Reddit

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

Reddit has multiple UI contexts: posts, comments, awards, vote counts, and nested reply threads. Screenshots may capture any combination.

---

## 2. UI Elements to Extract

### 2.1 Post Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Subreddit | Top, prefixed "r/" | YES | `r/subreddit_name` |
| Username | Below subreddit or inline | YES | `u/username` |
| Post Title | Prominent, larger text | YES | Full text |
| Post Body | Below title | If visible | Full text |
| Timestamp | Near username | If visible | "X hours ago" / date |
| Upvotes | Left side or below | If visible | Number |
| Awards | Near title/votes | If visible | Award names/counts |
| Flair | Near username | If visible | Flair text |

### 2.2 Comment Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Username | Start of comment | YES | `u/username` |
| Comment Text | Below username | YES | Full text |
| Timestamp | After username | If visible | Relative time |
| Upvotes | Below comment | If visible | Number |
| Reply Depth | Indentation level | Note | Nesting level 0-N |
| Awards | Near comment | If visible | Award names |

### 2.3 Thread Context

| Element | Importance | Notes |
|---------|------------|-------|
| Parent comment | HIGH | Context for replies |
| OP indicator | HIGH | "[OP]" tag matters |
| Mod indicator | MEDIUM | "[MOD]" or green highlight |
| Stickied status | LOW | "Stickied comment" |

---

## 3. Extraction Prompt Template

```
Analyze this Reddit screenshot and extract structured information.

PLATFORM: Reddit
EXTRACTION MODE: ocr_extracted

Extract the following if visible:

1. CONTEXT
   - Subreddit name (r/...)
   - Is this a post or comment thread?
   - Thread topic (if post title visible)

2. FOR EACH VISIBLE POST:
   - username (u/...)
   - post_title
   - post_body (if visible)
   - timestamp
   - upvotes (number only)
   - awards (list)
   - flair

3. FOR EACH VISIBLE COMMENT:
   - username (u/...)
   - comment_text (full text)
   - timestamp
   - upvotes
   - nesting_level (0 = top-level, 1+ = replies)
   - is_op (true if marked [OP])
   - is_mod (true if mod indicator)

4. MISSING CONTEXT CHECK
   - Does any comment appear to be replying to invisible content?
   - Is the post title cut off?
   - Are earlier comments in thread missing?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "reddit",
  "screenshot_type": "post" | "comment_thread" | "mixed",
  "subreddit": "r/example",
  "context": {
    "post_title": "string or null",
    "thread_topic": "inferred topic",
    "missing_context": true | false,
    "missing_context_note": "Earlier comments not visible"
  },
  "posts": [
    {
      "username": "u/poster",
      "title": "Post title",
      "body": "Post body text or null",
      "timestamp": "2 hours ago",
      "upvotes": 1542,
      "awards": ["Gold", "Helpful"],
      "flair": "Discussion"
    }
  ],
  "comments": [
    {
      "comment_id": "C1",
      "username": "u/commenter",
      "text": "Comment full text",
      "timestamp": "45 minutes ago",
      "upvotes": 234,
      "nesting_level": 0,
      "is_op": false,
      "is_mod": false,
      "replying_to": null | "C0"
    }
  ],
  "extraction_notes": [
    "Some text appears cut off at bottom"
  ]
}
```

---

## 5. Common UI Variations

### 5.1 Old Reddit vs New Reddit

| Aspect | Old Reddit | New Reddit |
|--------|-----------|------------|
| Layout | Dense, text-heavy | Card-based |
| Username location | Inline with timestamp | Below subreddit |
| Vote display | Left column | Bottom or left |

**Handling:** Gemini should recognize both layouts. Note in extraction which version detected.

### 5.2 Mobile vs Desktop

| Aspect | Mobile | Desktop |
|--------|--------|---------|
| Layout | Single column | Multi-column possible |
| Navigation | Hidden | Visible sidebar |
| Vote buttons | Compact | Expanded |

### 5.3 Dark Mode vs Light Mode

Both should extract correctly. Note if colors affect readability.

---

## 6. Edge Cases

### 6.1 Collapsed Comments

**Visual:** "[+] username (X children)"

**Handling:**
- Note as collapsed, not missing
- Extract username if visible
- Add note: "X collapsed replies not visible"

### 6.2 Deleted/Removed Content

**Visual:** "[deleted]" or "[removed]"

**Handling:**
- Extract as-is
- Note: "Content was deleted/removed"
- Username may show as "[deleted]"

### 6.3 Long Comment Threads

**Visual:** "Continue this thread →" or "View more replies"

**Handling:**
- Extract what's visible
- Add note: "Thread continues beyond screenshot"
- Flag as incomplete context

### 6.4 Crosspost Indicators

**Visual:** "Crossposted from r/other"

**Handling:**
- Note original subreddit
- Extract crosspost metadata if visible

### 6.5 Awards Overflow

**Visual:** Multiple awards with "+X more"

**Handling:**
- List visible awards
- Note: "X additional awards not shown"

---

## 7. Observation Format for Reddit

```json
{
  "observation_id": "OBS_1",
  "description": "User u/throwaway123 claims in r/technology that the company knew about the issue for months",
  "platform": "reddit",
  "platform_elements": {
    "subreddit": "r/technology",
    "username": "u/throwaway123",
    "engagement": "234 upvotes"
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. Quality Indicators

### High Quality Screenshot
- Full post/comment visible
- Clear text
- Context visible (subreddit, parent if reply)

### Medium Quality Screenshot
- Partial content cut off
- Some text blurry
- Missing parent context

### Low Quality Screenshot
- Significant content cut off
- Multiple unclear areas
- No context visible

---

## 9. Reddit-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `missing_parent` | Reply without visible parent | "Comment appears to be a reply to hidden content" |
| `collapsed_thread` | Collapsed comments visible | "X collapsed comments not extracted" |
| `partial_content` | Text cut off | "Content appears truncated" |
| `deleted_content` | [deleted]/[removed] | "Original content was deleted" |
| `low_engagement` | No votes visible | "Engagement metrics not captured" |

---

**END OF PLATFORM GUIDE**
