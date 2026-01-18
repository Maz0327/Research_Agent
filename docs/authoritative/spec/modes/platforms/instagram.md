# Platform OCR Guide: Instagram

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

Instagram has multiple content types: feed posts, Stories, Reels, comments, DMs, and carousel posts. Each has distinct UI patterns.

---

## 2. UI Elements to Extract

### 2.1 Feed Post Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Username | Top left, below profile pic | YES | `@username` |
| Verified Badge | Next to username | Note | Blue checkmark |
| Location Tag | Below username | If visible | Location name |
| Caption | Below image/video | YES | Full text |
| Likes | Below caption | If visible | "X likes" or usernames |
| Comments Count | Below likes | If visible | "View all X comments" |
| Timestamp | Below comments | If visible | Relative or absolute |
| Hashtags | In caption | Extract | List separately |
| Mentions | In caption | Extract | `@mentions` |

### 2.2 Story Elements

| Element | Location | Required | Notes |
|---------|----------|----------|-------|
| Username | Top left | YES | Story owner |
| Timestamp | Top, small text | If visible | "Xh ago" |
| Text Overlays | Anywhere on image | Extract | All visible text |
| Stickers | Various | Note | Poll, question, link stickers |
| Music | Bottom | If visible | Song name/artist |

### 2.3 Reel Elements

| Element | Location | Required | Notes |
|---------|----------|----------|-------|
| Username | Bottom left | YES | Creator |
| Caption | Bottom, expandable | If visible | May be truncated |
| Audio | Bottom left | If visible | Original/song name |
| Likes | Right side | If visible | Heart icon + count |
| Comments | Right side | If visible | Bubble icon + count |
| Shares | Right side | If visible | Paper plane icon |

### 2.4 Comment Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Username | Start of comment | YES | Bold username |
| Comment Text | After username | YES | Full text |
| Timestamp | After text | If visible | Relative time |
| Likes | Below comment | If visible | Heart + number |
| Replies | Below comment | If visible | "View X replies" |

---

## 3. Extraction Prompt Template

```
Analyze this Instagram screenshot and extract structured information.

PLATFORM: Instagram
EXTRACTION MODE: ocr_extracted

Identify content type: feed_post | story | reel | comment_section | dm

Extract the following based on type:

FOR FEED POSTS:
- username (with verification status)
- location_tag
- caption (full text)
- hashtags (list)
- mentions (list @users)
- likes_count or liked_by usernames
- comments_count
- timestamp

FOR STORIES:
- username
- timestamp
- all_text_overlays
- stickers (type and content)
- music (if shown)

FOR REELS:
- username
- caption (if visible)
- audio_source
- engagement (likes, comments, shares)

FOR COMMENTS:
- For each comment:
  - username
  - comment_text
  - timestamp
  - likes
  - reply_count
  - is_creator_reply

CONTEXT CHECK:
- Is caption truncated ("...more")?
- Are comments limited ("View all X comments")?
- Is this a carousel (dots indicator)?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "instagram",
  "content_type": "feed_post" | "story" | "reel" | "comments" | "dm",
  "post": {
    "username": "@creator",
    "verified": true | false,
    "location": "New York, NY" | null,
    "caption": "Full caption text here #hashtag @mention",
    "hashtags": ["#example", "#research"],
    "mentions": ["@user1", "@user2"],
    "likes": {
      "count": 15420,
      "display": "15.4K likes",
      "liked_by_visible": ["user1", "user2"]
    },
    "comments_count": 234,
    "timestamp": "2 hours ago",
    "is_carousel": true,
    "carousel_position": "1/5"
  },
  "comments": [
    {
      "comment_id": "C1",
      "username": "@commenter",
      "text": "Comment text",
      "timestamp": "1h",
      "likes": 45,
      "is_creator": false,
      "replies_count": 3,
      "is_pinned": false
    }
  ],
  "story_elements": {
    "text_overlays": ["Text 1", "Text 2"],
    "stickers": [
      {"type": "poll", "question": "Yes or No?", "options": ["Yes", "No"]}
    ],
    "music": {"song": "Song Name", "artist": "Artist"}
  },
  "context": {
    "caption_truncated": true,
    "comments_truncated": true,
    "total_comments": 234
  },
  "extraction_notes": []
}
```

---

## 5. Common UI Variations

### 5.1 Feed vs Explore

| Aspect | Feed | Explore |
|--------|------|---------|
| Context | Full post details | May be cropped preview |
| Engagement | Always shown | Sometimes hidden |

### 5.2 Mobile vs Desktop Web

| Aspect | Mobile App | Desktop Web |
|--------|------------|-------------|
| Layout | Single column | Three-column |
| Stories | Top carousel | Top bar |
| Comments | Slide-up sheet | Side panel |

### 5.3 Creator vs Viewer View

| Aspect | Creator | Viewer |
|--------|---------|--------|
| Insights | Visible | Hidden |
| Edit option | Visible | Hidden |
| Analytics | Shown | Not shown |

---

## 6. Edge Cases

### 6.1 Carousel Posts

**Visual:** Dots below image indicating multiple slides

**Handling:**
- Note carousel indicator
- Extract visible slide content
- Note: "Carousel post, showing slide X of Y"
- Other slides not captured

### 6.2 Truncated Captions

**Visual:** Caption ends with "...more"

**Handling:**
- Extract visible portion
- Add note: "Caption truncated, tap to expand not captured"

### 6.3 Limited Comments View

**Visual:** "View all X comments"

**Handling:**
- Extract visible comments
- Note total count
- Add note: "X additional comments not visible"

### 6.4 Pinned Comments

**Visual:** "Pinned by @creator" label

**Handling:**
- Mark comment as pinned
- Note creator emphasis

### 6.5 Sponsored/Paid Partnership

**Visual:** "Paid partnership with @brand"

**Handling:**
- Extract partnership label
- Note: "Sponsored content"
- Include brand name

### 6.6 Story Expired Reference

**Visual:** Screenshot shows "Story unavailable"

**Handling:**
- Note story is no longer available
- Extract any visible context
- Limited extraction possible

---

## 7. Observation Format for Instagram

```json
{
  "observation_id": "OBS_1",
  "description": "@influencer posted about product issues, receiving significant negative engagement",
  "platform": "instagram",
  "platform_elements": {
    "username": "@influencer",
    "content_type": "feed_post",
    "engagement": "15.4K likes, 234 comments",
    "hashtags": ["#sponsored", "#review"]
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. Story-Specific Extraction

Stories have unique ephemeral elements:

### 8.1 Interactive Stickers

| Sticker Type | Extract | Notes |
|--------------|---------|-------|
| Poll | Question + options + results | If results visible |
| Question | Question text | Response not visible |
| Quiz | Question + options | Results if shown |
| Emoji Slider | Prompt | Response avg if shown |
| Link | URL or button text | Destination if visible |
| Mention | @username | |
| Location | Place name | |
| Hashtag | #hashtag | |

### 8.2 Story Text Overlays

- Extract ALL visible text
- Note position (top, center, bottom)
- Note styling if relevant (color, size)

---

## 9. Instagram-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `caption_truncated` | "...more" visible | "Caption truncated, full text not captured" |
| `comments_limited` | "View all" visible | "Only X of Y comments visible" |
| `carousel_partial` | Dot indicator | "Carousel post, only current slide captured" |
| `story_ephemeral` | Story content | "Story content may no longer be available" |
| `sponsored_content` | Partnership label | "Paid partnership content" |
| `verification_status` | Blue check | "Verified account" |

---

## 10. DM Screenshots (Special Handling)

Instagram DM screenshots require extra care:

**Privacy Considerations:**
- May contain private conversations
- Other party may not have consented to sharing
- Handle with explicit user acknowledgment

**Extraction:**
- Note it's a DM screenshot
- Extract message content
- Note participants
- Add warning: "Private message content"

---

**END OF PLATFORM GUIDE**
