# Platform OCR Guide: TikTok

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

TikTok has video-centric UI with comments, duets, stitches, and live streams. Screenshots may capture video frames with text overlays, comment sections, or creator profiles.

---

## 2. UI Elements to Extract

### 2.1 Video Post Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Username | Bottom left, @prefix | YES | `@username` |
| Video Caption | Bottom left, below username | If visible | May be truncated |
| Sound/Audio | Bottom left, scrolling text | If visible | Song/original audio |
| Likes | Right side | If visible | Heart icon + count |
| Comments | Right side | If visible | Bubble icon + count |
| Shares | Right side | If visible | Arrow icon + count |
| Saves | Right side | If visible | Bookmark icon + count |
| Hashtags | In caption | Extract | List separately |
| Mentions | In caption | Extract | `@mentions` |

### 2.2 Comment Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Username | Start of comment | YES | `@username` |
| Comment Text | After username | YES | Full text |
| Timestamp | After text | If visible | Relative time |
| Likes | Right of comment | If visible | Heart + number |
| Replies | Below comment | If visible | "View X replies" |
| Creator Badge | Near username | Note | "Creator" label |
| Pinned Status | Above comment | Note | "Pinned by creator" |

### 2.3 Duet/Stitch Elements

| Element | Location | Notes |
|---------|----------|-------|
| Original Creator | Split screen or reference | Duet = side-by-side |
| Stitch Indicator | Start of video | "Stitch with @user" |
| Original Context | Embedded content | May show partial original |

### 2.4 Live Stream Elements

| Element | Location | Notes |
|---------|----------|-------|
| "LIVE" Badge | Top left | Red live indicator |
| Viewer Count | Top area | Number watching |
| Gift Animations | Throughout | Virtual gifts |
| Live Comments | Scrolling overlay | Real-time chat |

---

## 3. Extraction Prompt Template

```
Analyze this TikTok screenshot and extract structured information.

PLATFORM: TikTok
EXTRACTION MODE: ocr_extracted

Identify content type: video_post | comment_section | duet | stitch | live | profile

Extract the following based on type:

FOR VIDEO POSTS:
- username (@...)
- caption (full text if visible)
- hashtags (list)
- mentions (list)
- sound/audio (song name, "original audio", etc.)
- engagement (likes, comments, shares, saves)
- is_duet (true/false)
- is_stitch (true/false)
- original_creator (if duet/stitch)

FOR COMMENTS:
- For each comment:
  - username
  - comment_text
  - timestamp
  - likes
  - is_creator (true if creator badge)
  - is_pinned (true if pinned)
  - reply_count

FOR LIVE STREAMS:
- username
- viewer_count
- visible_comments (list)
- gifts_visible (list if shown)

CONTEXT CHECK:
- Is caption truncated ("...more")?
- Are comments limited ("View more comments")?
- Is this a screenshot of a duet/stitch?
- What portion of video timeline is this from?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "tiktok",
  "content_type": "video_post" | "comment_section" | "duet" | "stitch" | "live" | "profile",
  "post": {
    "username": "@creator",
    "verified": true | false,
    "caption": "Full caption text #hashtag @mention",
    "hashtags": ["#fyp", "#viral"],
    "mentions": ["@user1"],
    "sound": {
      "name": "Original audio - @creator" | "Song Name - Artist",
      "is_original": true | false
    },
    "engagement": {
      "likes": 125000,
      "likes_display": "125K",
      "comments": 3400,
      "shares": 890,
      "saves": 12000
    },
    "is_duet": false,
    "is_stitch": false,
    "original_creator": null | "@originaluser"
  },
  "comments": [
    {
      "comment_id": "C1",
      "username": "@commenter",
      "text": "Comment text",
      "timestamp": "2d",
      "likes": 450,
      "is_creator": false,
      "is_pinned": false,
      "replies_count": 12
    }
  ],
  "live_context": {
    "viewer_count": 15420,
    "is_live": true,
    "scrolling_comments": ["comment 1", "comment 2"]
  },
  "context": {
    "caption_truncated": true,
    "comments_truncated": true,
    "video_timestamp": "unknown"
  },
  "extraction_notes": []
}
```

---

## 5. Common UI Variations

### 5.1 For You Page vs Following

| Aspect | For You | Following |
|--------|---------|-----------|
| Context | Algorithmic, may lack context | From followed creators |
| Discovery | Random content | Curated by user |

### 5.2 Mobile vs Desktop Web

| Aspect | Mobile App | Desktop Web |
|--------|------------|-------------|
| Layout | Full screen vertical | Center column |
| Comments | Slide-up drawer | Side panel |
| Navigation | Swipe up/down | Click |
| Engagement | Right side icons | Similar placement |

### 5.3 Dark Mode vs Light Mode

Both extract correctly. Note if affecting readability.

---

## 6. Edge Cases

### 6.1 Truncated Captions

**Visual:** Caption ends with "...more"

**Handling:**
- Extract visible portion
- Note hashtags may be cut off
- Add note: "Caption truncated, expand not captured"

### 6.2 Duet Videos

**Visual:** Split-screen with two creators

**Handling:**
- Identify both creators
- Note which is original vs reactor
- Extract both usernames
- Mark as `is_duet: true`

### 6.3 Stitch Videos

**Visual:** "Stitch with @user" indicator or embedded clip

**Handling:**
- Note original creator
- Extract stitch context
- Mark as `is_stitch: true`
- Note if original content visible

### 6.4 Text Overlay on Video

**Visual:** Text added by creator over video

**Handling:**
- Extract ALL visible text overlays
- Note position (top, center, bottom)
- Distinguish from UI elements
- May contain key claims

### 6.5 Green Screen/Reply Videos

**Visual:** Creator in front of screenshot or image

**Handling:**
- Extract background content if readable
- Note it's a reaction/reply format
- May reference external content

### 6.6 Live Stream Screenshots

**Visual:** "LIVE" badge, scrolling comments

**Handling:**
- Note ephemeral nature
- Extract visible comments (may be partial)
- Capture viewer count
- Add note: "Live stream content, context may be incomplete"

### 6.7 Comment Reply Threads

**Visual:** Nested "View X replies" expanded

**Handling:**
- Extract parent comment
- Extract visible replies
- Note thread depth
- Flag if replies truncated

---

## 7. Observation Format for TikTok

```json
{
  "observation_id": "OBS_1",
  "description": "@creator posted viral video claiming product causes issues, receiving significant engagement",
  "platform": "tiktok",
  "platform_elements": {
    "username": "@creator",
    "content_type": "video_post",
    "engagement": "125K likes, 3.4K comments",
    "hashtags": ["#storytime", "#product"],
    "sound": "Original audio"
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. TikTok-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `caption_truncated` | "...more" visible | "Caption truncated, full text not captured" |
| `comments_limited` | "View more" visible | "Only X comments visible" |
| `duet_content` | Split screen | "Duet video, showing both creators" |
| `stitch_content` | Stitch indicator | "Stitch video, references original content" |
| `live_ephemeral` | LIVE badge | "Live stream content, no permanent record" |
| `text_overlay` | On-screen text | "Creator added text overlay" |
| `sound_attribution` | Sound name visible | "Uses audio: [sound name]" |
| `viral_indicators` | High engagement | "High engagement suggests viral spread" |

---

## 9. Sound/Audio Context

TikTok audio is significant for context:

### 9.1 Original Audio
- Format: "original audio - @username"
- Indicates creator's own content
- May contain speech to extract

### 9.2 Trending Sounds
- Format: "Song Name - Artist"
- May indicate trend participation
- Context for why video was made

### 9.3 Sound from Another Video
- Format: "@username" only
- References another TikTok
- May need original for context

**Note:** Audio content cannot be extracted from screenshots. Note if sound seems relevant to claims.

---

## 10. Engagement Interpretation

TikTok engagement has specific patterns:

| Metric | Typical Viral | Notes |
|--------|---------------|-------|
| Likes | 100K+ | Primary engagement metric |
| Comments | 1K+ | Often reaction-based |
| Shares | 500+ | Indicates spread |
| Saves | 10K+ | Interest for later |

**Context:** High engagement doesn't indicate accuracy. Note engagement level but don't conflate with credibility.

---

## 11. Creator vs Viewer View

| Aspect | Creator | Viewer |
|--------|---------|--------|
| Analytics | Visible (views, demographics) | Hidden |
| Edit option | Three dots menu expanded | Limited |
| Comment moderation | Delete/pin options | Just reply |
| Sound | Can see who used sound | Limited info |

If screenshot shows creator analytics, note this provides insider view.

---

**END OF PLATFORM GUIDE**
