# Platform OCR Guide: Generic Forums

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14
**OCR Model:** Gemini 2.5 Pro (direct vision)

---

## 1. Platform Overview

This guide covers forums and discussion platforms not covered by specific guides. Includes: traditional forums (phpBB, vBulletin, Discourse), Q&A sites (Stack Exchange, Quora), niche communities, news comment sections, and any threaded discussion format.

---

## 2. Common Forum Patterns

### 2.1 Traditional Forums (phpBB, vBulletin, XenForo)

| Element | Typical Location | Required | Format |
|---------|------------------|----------|--------|
| Username | Left of post or top | YES | Display name |
| Post Content | Main area | YES | Full text |
| Post Date | Near username | If visible | Date/time |
| Post Number | Top right or header | If visible | #123 |
| User Rank | Below username | Note | Title/level |
| Post Count | User info area | Note | Number |
| Join Date | User info area | Note | Date |
| Signature | Below post | Note | User signature |
| Quote Blocks | In post | Extract | Quoted text |

### 2.2 Modern Forums (Discourse, NodeBB)

| Element | Typical Location | Required | Format |
|---------|------------------|----------|--------|
| Username | Top of post | YES | Display name |
| Avatar | Left of post | Note | User image |
| Post Content | Main area | YES | Full text |
| Timestamp | Below username | If visible | Relative or absolute |
| Likes/Hearts | Below post | If visible | Count |
| Replies | Below post | If visible | "X replies" |
| Topic Title | Page header | If visible | Thread title |
| Category | Near title | If visible | Forum section |

### 2.3 Q&A Sites (Stack Exchange, Quora)

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Question | Top, prominent | YES | Full question text |
| Asker | Below question | YES | Username |
| Answers | Below question | YES | Full answer text |
| Answer Author | With answer | YES | Username |
| Vote Count | Left of post | If visible | Number (may be negative) |
| Accepted Answer | Green checkmark | Note | Asker's choice |
| Timestamps | Near content | If visible | Asked/answered dates |
| Tags | Below question | If visible | Topic tags |

### 2.4 News Site Comments

| Element | Location | Required | Format |
|---------|----------|----------|--------|
| Commenter Name | Start of comment | YES | Display name or "Guest" |
| Comment Text | After name | YES | Full text |
| Timestamp | Near name | If visible | Date/time |
| Likes/Dislikes | Below comment | If visible | Counts |
| Replies | Indented/threaded | If visible | Nested comments |
| Verified | Badge near name | Note | Staff/verified |

---

## 3. Extraction Prompt Template

```
Analyze this forum/discussion screenshot and extract structured information.

PLATFORM: [Identify platform if possible, otherwise "unknown_forum"]
EXTRACTION MODE: ocr_extracted

First identify:
- Platform type (traditional_forum, modern_forum, qa_site, news_comments, other)
- Thread/topic title if visible
- Forum/category if visible

Extract the following:

1. THREAD CONTEXT:
   - topic_title (if visible)
   - forum_category (if visible)
   - platform_name (if identifiable)
   - is_locked/closed (if indicated)

2. FOR EACH POST/COMMENT:
   - username
   - post_text (full text, preserve formatting)
   - timestamp
   - post_number (if shown)
   - user_rank/title (if shown)
   - vote_count (if Q&A style)
   - is_accepted (for Q&A accepted answers)
   - is_op (if original poster)
   - is_moderator/staff
   - quoted_content (if quoting another post)

3. FOR Q&A SITES:
   - question_text
   - question_author
   - question_votes
   - tags
   - For each answer:
     - answer_text
     - author
     - votes
     - is_accepted

4. CONTEXT CHECK:
   - Is this mid-thread (earlier posts not visible)?
   - Are there pagination indicators?
   - Is content moderated/hidden?
   - Are there "load more" indicators?

Return as structured JSON.
```

---

## 4. Output Schema

```json
{
  "platform": "discourse" | "phpbb" | "stack_exchange" | "quora" | "news_comments" | "unknown_forum",
  "content_type": "thread" | "qa" | "comments",
  "thread_context": {
    "title": "Thread Title" | null,
    "category": "Forum Section" | null,
    "url_visible": false,
    "is_locked": false,
    "page_number": 1
  },
  "posts": [
    {
      "post_id": "P1",
      "username": "User123",
      "user_rank": "Senior Member" | null,
      "join_date": "2020" | null,
      "post_count": 1542 | null,
      "text": "Full post text here",
      "timestamp": "Jan 14, 2026 at 3:45 PM",
      "post_number": 45 | null,
      "votes": null,
      "is_op": false,
      "is_moderator": false,
      "is_staff": false,
      "quotes": [
        {
          "quoted_user": "OtherUser",
          "quoted_text": "The text being quoted"
        }
      ],
      "signature": "User signature if visible" | null
    }
  ],
  "qa_context": {
    "question": {
      "text": "Question text",
      "author": "Asker",
      "votes": 45,
      "tags": ["tag1", "tag2"],
      "timestamp": "Asked 2 days ago"
    },
    "answers": [
      {
        "text": "Answer text",
        "author": "Answerer",
        "votes": 123,
        "is_accepted": true,
        "timestamp": "Answered 1 day ago"
      }
    ]
  },
  "context": {
    "posts_truncated": true,
    "missing_earlier": true,
    "pagination_visible": true,
    "total_pages": "5"
  },
  "extraction_notes": []
}
```

---

## 5. Platform Identification

### 5.1 Visual Cues for Platform Type

| Cue | Likely Platform |
|-----|-----------------|
| User info sidebar (avatar, rank, post count) | Traditional forum (phpBB, vBulletin) |
| Clean, modern cards | Discourse, modern forum |
| Vote arrows left of content | Stack Exchange, Reddit-style |
| "Answer" button, accepted checkmark | Q&A site |
| Disqus logo | Disqus comments |
| News site branding | News comments |

### 5.2 Platform-Specific Notes

| Platform | Key Feature | Note |
|----------|-------------|------|
| Stack Exchange | Accepted answer (green check) | High signal for quality |
| Quora | "Answer requested" | Expert answers |
| Discourse | Trust levels | User reputation |
| Traditional forums | Post counts, join dates | Longevity indicators |
| Disqus | Cross-site comments | Same user across sites |

---

## 6. Edge Cases

### 6.1 Quoted Content

**Visual:** Indented block with "Originally posted by" or similar

**Handling:**
- Extract quoted text separately
- Note who is being quoted
- Distinguish quote from poster's own words
- Handle nested quotes carefully

### 6.2 Multi-Page Threads

**Visual:** Page numbers, "Page 3 of 7"

**Handling:**
- Note current page
- Note total pages
- Add note: "Page X of Y, earlier/later posts not visible"
- Context may be incomplete

### 6.3 Locked/Archived Threads

**Visual:** Lock icon, "This thread is closed"

**Handling:**
- Note locked status
- Discussion ended, no new replies
- May be locked for various reasons

### 6.4 Moderated/Hidden Content

**Visual:** "[Post hidden by moderator]" or similar

**Handling:**
- Note content was removed
- Don't speculate on original content
- Flag as incomplete context

### 6.5 User Signatures

**Visual:** Consistent text/images below posts

**Handling:**
- Separate from post content
- Note it's a signature
- May contain links or quotes

### 6.6 Code Blocks

**Visual:** Formatted code, syntax highlighting

**Handling:**
- Extract code as-is
- Note it's code content
- Preserve formatting if possible
- May be relevant technical evidence

### 6.7 Embedded Images/Links

**Visual:** Images in post or [IMAGE] placeholders

**Handling:**
- Note presence of media
- Describe if visible
- Note if crucial context is in image

### 6.8 Split Posts ("Post too long")

**Visual:** "Continued in next post" or multi-part

**Handling:**
- Note it's continued
- Extract available parts
- Flag if continuation not visible

---

## 7. Observation Format for Forums

```json
{
  "observation_id": "OBS_1",
  "description": "Senior forum member with 5+ years claims firsthand experience with the issue",
  "platform": "phpbb_forum",
  "platform_elements": {
    "forum_name": "TechForum",
    "username": "ExpertUser",
    "user_rank": "Senior Member",
    "post_count": "3,542 posts",
    "context": "Thread: 'Known Issues Discussion'"
  },
  "type": "observation",
  "approximate": true,
  "ocr_confidence": "high"
}
```

---

## 8. Forum-Specific Warnings

| Warning | Trigger | Message |
|---------|---------|---------|
| `mid_thread` | Missing earlier posts | "Thread context incomplete, earlier posts not visible" |
| `paginated` | Page numbers visible | "Page X of Y, other pages not captured" |
| `locked_thread` | Lock indicator | "Thread is locked, no new discussion" |
| `moderated_content` | Hidden post indicator | "Some content removed by moderators" |
| `quoted_context` | Quotes present | "Post quotes another user's content" |
| `unknown_platform` | Can't identify | "Forum platform not identified" |
| `user_signature` | Signature visible | "Contains user signature content" |
| `qa_accepted` | Accepted answer | "Answer marked as accepted by asker" |

---

## 9. Credibility Signals (Forum-Specific)

### Higher Credibility Signals
- Long tenure (join date years ago)
- High post count (active community member)
- Moderator/Admin badge
- Accepted answer (Q&A sites)
- High vote count
- "Verified" or staff badges
- Quoted by others with agreement

### Lower Credibility Signals
- New account
- Very low post count
- Contradicted by high-tenure users
- Heavily downvoted (Q&A sites)
- Generic usernames
- No replies/engagement

### Contextual
- User rank titles (may indicate reputation)
- Signature content (personal site, credentials)
- Response patterns (defensive vs informative)

**Note:** These are heuristics. Document signals but don't auto-trust based on tenure alone.

---

## 10. Common Forum Types

### 10.1 Enthusiast/Hobby Forums

- Deep domain knowledge
- Technical discussions
- Long-term community members
- Valuable for niche topics

### 10.2 Support Forums

- Official product support
- Staff/employee responses
- Bug reports and solutions
- May have official positions

### 10.3 Local/Regional Forums

- Geographic focus
- Local knowledge
- May have privacy considerations
- Language variations

### 10.4 Professional Forums

- Industry discussions
- Career/business topics
- May reveal insider perspectives
- Higher accountability expectations

---

## 11. Privacy Considerations

Forums may contain:
- Real names (if forum uses them)
- Personal details in posts
- Contact information
- Location information

**Handling:**
- Extract content as visible
- Note if personal info present
- Don't assume public forum = public person
- Handle with appropriate care

---

## 12. Historical Context

Forum posts may be from:
- Many years ago
- Different context/era
- Before events being researched
- Archived/read-only state

**Handling:**
- Note timestamps carefully
- Consider if context has changed
- Historical posts ≠ current views
- Archived forums may be incomplete

---

**END OF PLATFORM GUIDE**
