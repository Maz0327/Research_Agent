# Platform OCR Guide: Facebook

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

Facebook has complex UI with posts, comments, reactions, groups, pages, and various privacy contexts. Content visibility varies by privacy settings.

---

## 2. UI Elements to Extract

### 2.1 Post Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Author Name | Top, bold | YES | Full name |
| Profile Type | Below name | Note | Person/Page/Group |
| Timestamp | Below name | If visible | Relative or absolute |
| Privacy Icon | Near timestamp | Note | Public/Friends/etc. |
| Post Text | Main body | YES | Full text |
| Reactions | Below post | If visible | Emoji + count |
| Comments | Below reactions | If visible | Count |
| Shares | Below reactions | If visible | Count |
| Media | In post body | Note | Photo/video/link |

### 2.2 Comment Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Name | Start of comment | YES | Full name |
| Comment Text | After name | YES | Full text |
| Timestamp | After text | If visible | Relative |
| Reactions | Below comment | If visible | Emoji + count |
| Replies | Below comment | If visible | "X replies" |
| Author Tag | After name | Note | "Author" badge |

### 2.3 Group Context

| Element | Location | Notes |
|---------|----------|-------|
| Group Name | Top or header | Container for post |
| Group Type | Below name | Public/Private |
| Admin/Mod Badge | Near author | Authority indicator |
| Group Rules Link | Various | Context for norms |

### 2.4 Page Context

| Element | Location | Notes |
|---------|----------|-------|
| Page Name | Post author | Business/public figure |
| Page Category | Below name | Type of page |
| Verified Badge | Next to name | Blue checkmark |
| Follower Count | Page header | If visible |

---

## 3. Extraction Prompt Template

```
Analyze this Facebook screenshot and extract structured information.

PLATFORM: Facebook
EXTRACTION MODE: ocr_extracted

Identify context: personal_post | page_post | group_post | comment_thread

Extract the following:

1. POST CONTEXT:
   - author_name
   - author_type (person, page, group admin)
   - verified (if checkmark visible)
   - timestamp
   - privacy_level (public, friends, group members)
   - group_name (if in group)
   - page_name (if page post)

2. POST CONTENT:
   - post_text (full text)
   - has_media (photo, video, link, poll)
   - link_preview (title, domain if shared link)
   - feeling/activity (if "feeling happy" etc.)
   - location (if tagged)
   - with_tags (if "with John Doe")

3. ENGAGEMENT:
   - reactions (total and breakdown if visible: like, love, haha, wow, sad, angry)
   - comments_count
   - shares_count

4. COMMENTS (for each visible):
   - name
   - text
   - timestamp
   - reactions
   - is_author (true if post author)
   - is_admin (true if admin/mod badge)
   - reply_count

5. MISSING CONTEXT:
   - Are earlier comments hidden?
   - Is "See more" truncating content?
   - Is post in a group we can't see full context of?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "facebook",
  "content_type": "personal_post" | "page_post" | "group_post" | "comment_thread",
  "context": {
    "group_name": "Group Name" | null,
    "page_name": "Page Name" | null,
    "privacy_level": "public" | "friends" | "group" | "unknown"
  },
  "post": {
    "author_name": "John Doe",
    "author_type": "person" | "page" | "group_member",
    "verified": false,
    "admin_badge": false,
    "timestamp": "Yesterday at 3:45 PM",
    "text": "Full post text here",
    "feeling": "feeling frustrated" | null,
    "location": "New York" | null,
    "with_tags": ["Jane Doe"] | [],
    "media": {
      "type": "photo" | "video" | "link" | "poll" | "none",
      "link_preview": {
        "title": "Article Title",
        "domain": "example.com"
      }
    },
    "engagement": {
      "reactions": {
        "total": 234,
        "breakdown": {
          "like": 150,
          "love": 50,
          "haha": 20,
          "wow": 10,
          "sad": 3,
          "angry": 1
        }
      },
      "comments": 45,
      "shares": 12
    }
  },
  "comments": [
    {
      "comment_id": "C1",
      "name": "Jane Doe",
      "text": "Comment text",
      "timestamp": "2h",
      "reactions": 15,
      "is_author": false,
      "is_admin": false,
      "is_top_fan": false,
      "replies_count": 3
    }
  ],
  "extraction_notes": []
}
```

---

## 5. Common UI Variations

### 5.1 Classic vs New Facebook

| Aspect | Classic | New (Current) |
|--------|---------|---------------|
| Layout | Compact | More whitespace |
| Reactions | Text counts | Emoji row |
| Comments | Inline | Expandable |

### 5.2 Mobile vs Desktop

| Aspect | Mobile | Desktop |
|--------|--------|---------|
| Layout | Full width | Center column |
| Sidebar | Hidden | Friends, groups |
| Reactions | Tap and hold | Hover |

### 5.3 Light vs Dark Mode

Both extract correctly. Note if affecting readability.

---

## 6. Edge Cases

### 6.1 "See More" Truncation

**Visual:** Post text ends with "... See More"

**Handling:**
- Extract visible portion
- Add note: "Post text truncated"

### 6.2 Hidden Comments

**Visual:** "View X more comments" or "Most relevant"

**Handling:**
- Extract visible comments
- Note total count
- Add note: "Showing most relevant, X comments hidden"

### 6.3 Shared Posts

**Visual:** Post contains another embedded post

**Handling:**
- Extract both the share commentary AND original post
- Mark which is share vs original
- Note original author

### 6.4 Memory/On This Day

**Visual:** "X years ago" memory frame

**Handling:**
- Note it's a memory repost
- Extract original date
- Note current share date

### 6.5 Group Posts with Limited Visibility

**Visual:** "Post from [Private Group]"

**Handling:**
- Note group privacy level
- Extract what's visible
- Add note: "Content from private group"

### 6.6 Reactions Breakdown

**Visual:** Emoji reactions with numbers

**Handling:**
- Extract total count
- Extract breakdown if individual counts visible
- Note which reaction types shown

### 6.7 Live Video/Event

**Visual:** "Live" or "Event" indicator

**Handling:**
- Note content type
- Extract event details if visible
- Note live status

---

## 7. Observation Format for Facebook

```json
{
  "observation_id": "OBS_1",
  "description": "Post in r/LocalNews group claims city council meeting was contentious, receiving angry reactions",
  "platform": "facebook",
  "platform_elements": {
    "author": "John Doe",
    "context": "Public group: Local News",
    "engagement": "234 reactions (45 angry), 89 comments",
    "post_type": "group_post"
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. Privacy Level Indicators

| Visual Indicator | Meaning | Extraction Note |
|------------------|---------|-----------------|
| Globe icon | Public | Anyone can see |
| Two people icon | Friends | Limited audience |
| Lock icon | Only me | Very limited |
| Group icon | Group members | Group context |
| Friends+ | Friends of friends | Extended network |

**Note:** Privacy level affects who could have seen this content. Document for context.

---

## 9. Page vs Profile Posts

### 9.1 Page Indicators
- Page name instead of personal name
- Category below name (Restaurant, Public Figure, etc.)
- "Like" and "Follow" buttons visible
- May have verified badge

### 9.2 Profile Indicators
- Personal name
- "Friends" or "Add Friend" button
- Personal profile picture style
- May show mutual friends

---

## 10. Facebook-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `text_truncated` | "See More" visible | "Post text truncated" |
| `comments_filtered` | "Most relevant" visible | "Comments filtered, not all shown" |
| `shared_content` | Embedded post | "This is a shared post" |
| `private_group` | Private group indicator | "Content from private group" |
| `memory_repost` | "On This Day" frame | "Memory/repost of older content" |
| `limited_visibility` | Friends-only indicator | "Original visibility was restricted" |
| `page_content` | Page post | "Official page post, not personal" |

---

**END OF PLATFORM GUIDE**
