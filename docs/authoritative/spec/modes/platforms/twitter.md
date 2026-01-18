# Platform OCR Guide: Twitter/X

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

Twitter/X has tweets, threads, quote tweets, replies, and various engagement metrics. UI changed significantly with X rebrand but core elements remain.

---

## 2. UI Elements to Extract

### 2.1 Tweet Elements

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Display Name | Top, bold | YES | Full name |
| Handle | Below/beside name, @prefix | YES | `@handle` |
| Tweet Text | Main body | YES | Full text |
| Timestamp | Below text or top right | If visible | Date/time |
| Retweets | Below tweet | If visible | Number |
| Likes | Below tweet | If visible | Number |
| Replies | Below tweet | If visible | Number |
| Views | Below tweet | If visible | Number |
| Verified Badge | Next to name | Note | Blue/gold/gray checkmark |
| Media | Below text | Note | Image/video indicator |

### 2.2 Thread Elements

| Element | Location | Required | Notes |
|---------|----------|----------|-------|
| Thread indicator | Vertical line connecting tweets | Note | Shows thread continuity |
| "Show this thread" | Below tweet | Note | More content available |
| Reply chain | Indented or connected | Note | Response structure |

### 2.3 Quote Tweet Elements

| Element | Location | Notes |
|---------|----------|-------|
| Original tweet | Embedded box | Has its own author info |
| Quote text | Above embedded tweet | Author's commentary |

---

## 3. Extraction Prompt Template

```
Analyze this Twitter/X screenshot and extract structured information.

PLATFORM: Twitter/X
EXTRACTION MODE: ocr_extracted

Extract the following if visible:

1. FOR EACH VISIBLE TWEET:
   - display_name
   - handle (@...)
   - tweet_text (full text, including line breaks)
   - timestamp
   - engagement (retweets, likes, replies, views)
   - verified_status (none, blue, gold, gray, government)
   - has_media (true/false, type if identifiable)

2. THREAD DETECTION:
   - Is this a thread? (connected tweets by same author)
   - Thread position (1/5, 2/5, etc. if indicated)
   - Is "Show more" or continuation indicator visible?

3. QUOTE TWEETS:
   - If quote tweet, extract BOTH the quote and original tweet
   - Mark which is quote vs original

4. REPLIES:
   - Is this a reply? (look for "Replying to @...")
   - Who is being replied to?

5. MISSING CONTEXT:
   - Is this mid-thread?
   - Are earlier tweets cut off?
   - Is the tweet being replied to visible?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "twitter",
  "screenshot_type": "single_tweet" | "thread" | "reply_chain" | "quote_tweet",
  "tweets": [
    {
      "tweet_id": "T1",
      "display_name": "John Doe",
      "handle": "@johndoe",
      "text": "Full tweet text here\nWith line breaks preserved",
      "timestamp": "Jan 14, 2026",
      "engagement": {
        "retweets": 1200,
        "likes": 5400,
        "replies": 234,
        "views": 125000
      },
      "verified": "blue" | "gold" | "gray" | "government" | "none",
      "has_media": true,
      "media_type": "image" | "video" | "poll" | "link_preview",
      "is_thread_part": true,
      "thread_position": "2/5",
      "is_reply": false,
      "replying_to": null | "@otheruser",
      "is_quote_tweet": false,
      "quoted_tweet": null | { ... }
    }
  ],
  "context": {
    "thread_complete": false,
    "missing_earlier_tweets": true,
    "continuation_available": true
  },
  "extraction_notes": []
}
```

---

## 5. Common UI Variations

### 5.1 Twitter vs X Branding

| Aspect | Twitter (Old) | X (Current) |
|--------|---------------|-------------|
| Logo | Bird icon | X icon |
| Verified | Blue check only | Blue/gold/gray/gov |
| Views | Not shown | Shown on most tweets |

**Handling:** Extract same data regardless of branding version.

### 5.2 Mobile vs Desktop

| Aspect | Mobile | Desktop |
|--------|--------|---------|
| Layout | Full width | Center column |
| Sidebar | Hidden | Trending/Who to follow |
| Compose | Floating button | Top of timeline |

### 5.3 Dark Mode vs Light Mode

Both extract correctly. Note if contrast affects readability.

---

## 6. Edge Cases

### 6.1 Long Tweets (Twitter Blue/X Premium)

**Visual:** Tweets longer than 280 characters

**Handling:**
- Extract full visible text
- Note if "Show more" truncation visible
- Add note: "Tweet may be truncated"

### 6.2 Threads with "Show this thread"

**Visual:** Blue text "Show this thread" below tweet

**Handling:**
- Note thread continuation exists
- Extract what's visible
- Add note: "Additional thread content not in screenshot"

### 6.3 Quote Tweet of Quote Tweet

**Visual:** Nested embedded tweets

**Handling:**
- Extract all visible levels
- Mark nesting: original → quote → re-quote

### 6.4 Deleted/Suspended Account Tweets

**Visual:** "This Tweet is from a suspended account"

**Handling:**
- Note the status
- Extract any visible text
- Add warning: "Account suspended, tweet may be unreliable"

### 6.5 Community Notes

**Visual:** Gray box below tweet with "Readers added context"

**Handling:**
- Extract community note separately
- Mark as community-added context
- Note this is crowd-sourced fact-check

### 6.6 Polls

**Visual:** Poll options with percentages

**Handling:**
- Extract question and options
- Note percentages if visible
- Note if poll is open or closed

---

## 7. Observation Format for Twitter

```json
{
  "observation_id": "OBS_1",
  "description": "@techreporter claims the company is planning layoffs affecting 500 employees",
  "platform": "twitter",
  "platform_elements": {
    "handle": "@techreporter",
    "display_name": "Tech Reporter",
    "verified": "blue",
    "engagement": "5.4K likes, 1.2K retweets"
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. Verification Badge Types

| Badge | Visual | Meaning | Credibility Note |
|-------|--------|---------|------------------|
| Blue | Blue checkmark | Paid subscription | Lower than before paid era |
| Gold | Gold checkmark | Verified organization | Higher credibility indicator |
| Gray | Gray checkmark | Government/multilateral | Official entity |
| Government | Special label | Government account | Note jurisdiction |
| None | No badge | Not verified | Neutral |

**Important:** Blue checkmarks no longer indicate identity verification since paid subscriptions began. Note this in extraction.

---

## 9. Twitter-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `incomplete_thread` | Thread indicator but not all visible | "Thread continues beyond screenshot" |
| `reply_without_parent` | "Replying to" but parent not shown | "Original tweet not visible" |
| `suspended_account` | Suspension notice | "Account suspended, content may be unreliable" |
| `community_note` | Fact-check visible | "Community Notes context added" |
| `paid_verification` | Blue check present | "Blue check indicates subscription, not identity verification" |
| `truncated_tweet` | "Show more" visible | "Tweet text may be truncated" |

---

## 10. Thread Reconstruction

When multiple screenshots show a thread:
1. Note tweet positions (1/5, 2/5, etc.)
2. Match by handle and timestamps
3. Do NOT invent missing tweets
4. Flag gaps: "Tweets 3-4 not captured"

---

**END OF PLATFORM GUIDE**
