# Platform OCR Guide: YouTube Comments

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

YouTube comment sections have threaded discussions, pinned comments, creator hearts, and various engagement indicators. Screenshots may capture comment sections, community posts, or live chat archives.

**Note:** This guide is specifically for YouTube **comment screenshots** analyzed via OCR. For YouTube video content with transcripts, use `transcript_grounded` or `caption_grounded` modes instead.

---

## 2. UI Elements to Extract

### 2.1 Comment Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Channel Name | Start of comment | YES | Display name |
| Handle | Below/beside name (newer UI) | If visible | `@handle` |
| Comment Text | Below name | YES | Full text |
| Timestamp | After name | If visible | "X hours/days ago" or "edited" |
| Likes | Below comment | If visible | Thumbs up + number |
| Replies | Below comment | If visible | "X replies" link |
| Creator Heart | Near comment | Note | Heart icon from creator |
| Pinned Status | Above comment | Note | "Pinned by [channel]" |
| Verified Badge | Next to name | Note | Gray checkmark |

### 2.2 Reply Thread Elements

| Element | Location | Required | Notes |
|---------|----------|----------|-------|
| Parent Comment | Top of thread | YES | Context for replies |
| Reply Count | "X replies" link | Note | Total replies |
| Visible Replies | Indented below | Extract | May be partial |
| "Show more replies" | Bottom of thread | Note | Indicates truncation |

### 2.3 Community Post Elements

| Element | Location | Notes |
|---------|----------|-------|
| Channel Name | Top | Post author |
| Post Type | Content area | Text, image, poll, video link |
| Post Text | Main body | May be long |
| Poll Options | If poll | Options and percentages |
| Engagement | Below post | Likes, comments count |

### 2.4 Live Chat Archive Elements

| Element | Location | Notes |
|---------|----------|-------|
| "Live chat replay" | Header | Indicates archived chat |
| Timestamps | Before messages | Sync with video |
| Usernames | Before message | Chatter names |
| Superchat | Highlighted messages | Paid highlights |
| Membership | Badge by name | Channel members |

---

## 3. Extraction Prompt Template

```
Analyze this YouTube screenshot and extract structured information.

PLATFORM: YouTube
EXTRACTION MODE: ocr_extracted
CONTENT TYPE: comments (not video transcripts)

Identify screenshot type: comment_section | community_post | live_chat | reply_thread

Extract the following:

FOR COMMENT SECTIONS:
- Video title (if visible)
- Video channel (if visible)
- For each comment:
  - channel_name
  - handle (@... if visible)
  - comment_text (full text)
  - timestamp
  - likes
  - reply_count
  - is_pinned
  - has_creator_heart
  - is_verified
  - is_creator (if channel owner)

FOR COMMUNITY POSTS:
- channel_name
- post_text
- post_type (text, image, poll)
- poll_options (if poll)
- likes
- comments_count

FOR LIVE CHAT:
- Note it's archived chat
- Extract visible messages
- Note timestamps if synced to video

FOR REPLY THREADS:
- Parent comment (full)
- Visible replies
- Total reply count
- Are more replies hidden?

CONTEXT CHECK:
- Is this a sorted view (Top comments vs Newest)?
- Is the video title visible for context?
- Are comments filtered or limited?
- Is this creator's own channel?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "youtube",
  "content_type": "comment_section" | "community_post" | "live_chat" | "reply_thread",
  "video_context": {
    "title": "Video Title" | null,
    "channel": "Channel Name" | null,
    "url_visible": false
  },
  "sort_order": "top_comments" | "newest" | "unknown",
  "comments": [
    {
      "comment_id": "C1",
      "channel_name": "Commenter Name",
      "handle": "@handle" | null,
      "text": "Full comment text here",
      "timestamp": "2 days ago",
      "edited": false,
      "likes": 1542,
      "reply_count": 23,
      "is_pinned": false,
      "has_creator_heart": false,
      "is_verified": false,
      "is_creator": false,
      "is_member": false,
      "membership_level": null
    }
  ],
  "replies": [
    {
      "reply_id": "R1",
      "parent_id": "C1",
      "channel_name": "Replier",
      "handle": "@replier",
      "text": "Reply text",
      "timestamp": "1 day ago",
      "likes": 45,
      "is_creator": true
    }
  ],
  "community_post": {
    "channel_name": "Channel",
    "text": "Post text",
    "type": "text" | "image" | "poll" | "video_link",
    "poll": {
      "question": "Poll question",
      "options": [
        {"text": "Option 1", "percentage": 45},
        {"text": "Option 2", "percentage": 55}
      ],
      "total_votes": 12500
    },
    "likes": 5400,
    "comments": 234
  },
  "context": {
    "comments_truncated": true,
    "total_comments": "1.2K",
    "replies_hidden": true
  },
  "extraction_notes": []
}
```

---

## 5. Common UI Variations

### 5.1 Old vs New YouTube UI

| Aspect | Old UI | New UI |
|--------|--------|--------|
| Handles | Not shown | @handle visible |
| Hearts | Same | Same |
| Layout | Compact | More whitespace |

### 5.2 Mobile vs Desktop

| Aspect | Mobile | Desktop |
|--------|--------|---------|
| Comments | Below video | Right side or below |
| Replies | Expandable | Expandable |
| Sort | Dropdown | Tabs |

### 5.3 Comment Sort Order

| Sort | Behavior | Note |
|------|----------|------|
| Top Comments | Engagement-weighted | Default view |
| Newest First | Chronological | More complete timeline |

**Important:** Sort order affects which comments are visible. Note if detected.

---

## 6. Edge Cases

### 6.1 Pinned Comments

**Visual:** "Pinned by [Channel Name]" above comment

**Handling:**
- Mark as pinned
- Note: Creator chose to highlight this
- May indicate creator's position on topic

### 6.2 Creator Hearts

**Visual:** Small heart icon near comment

**Handling:**
- Mark: `has_creator_heart: true`
- Note: Creator acknowledged this comment
- May indicate endorsement

### 6.3 Creator Replies

**Visual:** Channel name with special highlight/badge

**Handling:**
- Mark: `is_creator: true`
- Note: Official response from channel
- Higher significance for context

### 6.4 Edited Comments

**Visual:** "(edited)" after timestamp

**Handling:**
- Mark: `edited: true`
- Note: Original text may have been different
- Content may have changed

### 6.5 Collapsed/Hidden Replies

**Visual:** "View X replies" or "Show more replies"

**Handling:**
- Extract visible replies
- Note total count
- Add note: "X replies not visible"

### 6.6 Membership Badges

**Visual:** Badge icon next to name

**Handling:**
- Note membership status
- May indicate engagement level
- Note badge level if visible (e.g., "Member for 2 years")

### 6.7 Superchat/Super Thanks

**Visual:** Highlighted message with color/amount

**Handling:**
- Extract message text
- Note it was paid highlight
- Include amount if visible

### 6.8 Held for Review

**Visual:** "Held for review" or similar indicator

**Handling:**
- Note the status
- Content may be flagged
- Limited visibility to others

### 6.9 Community Post Polls

**Visual:** Poll with options and percentages

**Handling:**
- Extract question
- Extract all options
- Include percentages if shown
- Note if voting is closed

---

## 7. Observation Format for YouTube Comments

```json
{
  "observation_id": "OBS_1",
  "description": "Top comment on video claims insider knowledge of situation, received creator heart",
  "platform": "youtube",
  "platform_elements": {
    "channel_name": "Commenter Name",
    "context": "Comment on 'Video Title'",
    "engagement": "1.5K likes",
    "special_status": ["pinned", "creator_heart"]
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. YouTube Comment-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `pinned_comment` | Pinned indicator | "Creator-pinned comment, may reflect channel position" |
| `creator_heart` | Heart visible | "Comment received creator acknowledgment" |
| `creator_reply` | Creator responded | "Official channel response" |
| `edited_comment` | "(edited)" visible | "Comment was edited after posting" |
| `replies_hidden` | "View X replies" | "X replies not visible in screenshot" |
| `sort_unknown` | Can't determine | "Comment sort order unclear" |
| `membership_comment` | Membership badge | "Comment from channel member" |
| `superchat` | Paid highlight | "Paid highlight message" |
| `live_chat` | Chat replay | "Live chat archive, context may be fragmented" |

---

## 9. Comment Credibility Indicators

### High Credibility Signals
- Creator heart + creator reply = strong acknowledgment
- Pinned by creator = creator endorsement
- High likes + many positive replies = community agreement
- Verified badge (rare for commenters)

### Lower Credibility Signals
- No engagement (new/ignored)
- Edited comment (content may have changed)
- Generic username patterns
- Copy-paste style comments

### Neutral
- Membership badge (engagement ≠ accuracy)
- Reply depth (conversation ≠ truth)

**Note:** These are signals, not proof. Document but don't over-weight.

---

## 10. Distinguishing Comment OCR from Video Analysis

| Scenario | Mode | Why |
|----------|------|-----|
| Screenshot of comments | `ocr_extracted` | No transcript, image only |
| YouTube video URL | `transcript_grounded` | Full transcript available |
| Video with captions only | `caption_grounded` | Captions but no transcript |
| Video with no text | `video_only` | Visual analysis only |

**Rule:** If processing a screenshot of YouTube comments (not the video itself), use `ocr_extracted` mode even though it's YouTube content.

---

## 11. Community Posts

Community posts are separate from video comments:

### 11.1 Post Types

| Type | Visual | Extract |
|------|--------|---------|
| Text | Plain text post | Full text |
| Image | Image with optional text | Text + image description |
| Poll | Voting options | Question + options + results |
| Video Link | Embedded video preview | Title + any text |

### 11.2 Community Post Context

- Usually from subscribed channels
- May contain announcements, questions, or discussions
- Comments are separate from video comments
- Engagement typically lower than video comments

---

**END OF PLATFORM GUIDE**
