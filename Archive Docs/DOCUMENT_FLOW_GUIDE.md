# Document Flow Guide - Where Finished Documents Go

## Overview

When research jobs complete, all output documents are automatically uploaded to **Google Drive** using the Google Drive and Docs API integration.

---

## Google Drive Structure

### Root Folder Location

Documents are stored in the Google Drive folder specified by:
```bash
GOOGLE_DRIVE_ROOT_FOLDER_ID=1xkrPgQSRwtlmqLsqdH3l0_YRNNVtySdH
```

**View this folder at:**
https://drive.google.com/drive/folders/1xkrPgQSRwtlmqLsqdH3l0_YRNNVtySdH

---

## Research Job Document Output

### When a Research Job Completes

**Location in Code:** `backend/worker.py:639-656`

```python
folder_name = job_config.output.drive_folder_name or f"Research: {job_config.topic}"
drive_result = create_research_packet(folder_name, doc_contents)
```

### Folder Structure Created

For each completed research job, a NEW FOLDER is created with this structure:

```
Google Drive Root Folder
└── Research: [Your Topic]
    ├── 00_MASTER_INDEX (Google Doc)
    ├── 01_RESEARCH_MAP (Google Doc)
    ├── 02_SOURCE_SHORTLIST (Google Doc)
    ├── 03_YOUTUBE_INDEX (Google Doc)
    ├── 04_TRANSCRIPTS (Google Doc)
    ├── 05_WEB_EXTRACTS (Google Doc)
    ├── 06_QUOTE_BANK (Google Doc)
    ├── 07_CLAIMS_LEDGER (Google Doc)
    ├── 08_EVIDENCE_TABLE (Google Doc)
    ├── 09_MISSING_ANGLES (Google Doc)
    └── manifest.json
```

### Document Contents

| Document | Content |
|----------|---------|
| 00_MASTER_INDEX | Overview and links to all other documents |
| 01_RESEARCH_MAP | Research angles and key terms (from Perplexity) |
| 02_SOURCE_SHORTLIST | Curated list of relevant URLs (from Perplexity) |
| 03_YOUTUBE_INDEX | List of relevant YouTube videos with metadata |
| 04_TRANSCRIPTS | Extracted video transcripts |
| 05_WEB_EXTRACTS | Scraped content from web articles (Playwright + Trafilatura) |
| 06_QUOTE_BANK | Extracted quotes from all sources |
| 07_CLAIMS_LEDGER | Extracted factual claims from content (OpenAI) |
| 08_EVIDENCE_TABLE | Validation results for claims (Perplexity) |
| 09_MISSING_ANGLES | Identified gaps in research coverage |
| manifest.json | Metadata with URLs to all documents |

---

## Transcript Job Document Output

### When a Transcript Job Completes

**Location in Code:** `backend/worker.py:845-920`

```python
drive_result = create_transcript_doc(doc_title, transcript_content)
```

### Folder Structure Created

For each transcript extraction job, a NEW FOLDER is created:

```
Google Drive Root Folder
└── Transcripts - [YYYY-MM-DD HH:MM]
    └── [Custom Title or "YouTube Transcripts"] (Google Doc)
```

The document contains all extracted transcripts formatted as:

```
=== Video 1: [Video Title] ===
URL: [Video URL]

[Transcript text...]

=== Video 2: [Video Title] ===
URL: [Video URL]

[Transcript text...]
```

---

## How URLs Are Stored and Accessed

### In the Database (Supabase)

When a job completes, the `artifacts` field in the `jobs` table is updated:

```json
{
  "drive_folder_url": "https://drive.google.com/drive/folders/ABC123",
  "doc_urls": {
    "00_MASTER_INDEX": "https://docs.google.com/document/d/XYZ789/edit",
    "01_RESEARCH_MAP": "https://docs.google.com/document/d/DEF456/edit",
    ...
  }
}
```

**Location in Code:** `backend/worker.py:650-656`

```python
update_job(
    job_id,
    status="completed",
    progress_percent=100,
    partial_artifacts={
        "drive_folder_url": folder_url,
        "doc_urls": list(doc_urls.values()),
    },
)
```

### In the Frontend

**Job Detail Page** (`frontend/pages/jobs/[id].tsx`):
- Shows "Google Drive Folder" button linking to `artifacts.drive_folder_url`
- Lists individual documents from `artifacts.doc_urls`

**Dashboard** (`frontend/pages/dashboard.tsx`):
- JobCard shows "Open in Drive" link if `artifacts.drive_folder_url` exists

---

## API Access to Document URLs

### Get Single Job Documents

```bash
GET /jobs/{job_id}
```

**Response:**
```json
{
  "id": "abc-123",
  "prompt": "AI safety research",
  "status": "completed",
  "progress_percent": 100,
  "artifacts": {
    "drive_folder_url": "https://drive.google.com/drive/folders/ABC123",
    "doc_urls": [
      "https://docs.google.com/document/d/XYZ789/edit",
      "https://docs.google.com/document/d/DEF456/edit"
    ]
  }
}
```

### List All Jobs with Document URLs

```bash
GET /jobs?limit=50&offset=0
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "abc-123",
      "prompt": "AI safety research",
      "status": "completed",
      "artifacts": {
        "drive_folder_url": "https://drive.google.com/...",
        "doc_urls": ["https://docs.google.com/..."]
      }
    }
  ]
}
```

---

## Document Access Control

### Google Drive Permissions

By default, documents are created with:
- **Owner:** The Google account associated with the OAuth credentials
- **Visibility:** Private (only accessible to the owner)

**To share documents:**
1. Click the Drive folder link from the job detail page
2. Click "Share" in Google Drive
3. Add collaborators or make public

### Future Enhancement: Per-User Drive Folders

Currently, all jobs use the same Google Drive root folder. For multi-user production deployment, consider:

1. **Option A:** Create per-user subfolders:
   ```
   Root Folder
   ├── user-abc123/
   │   └── Research: Topic 1
   └── user-def456/
       └── Research: Topic 2
   ```

2. **Option B:** Use user-specific OAuth tokens (requires re-architecture)

---

## Testing Document Output

### Quick Test

1. Create a test job:
   ```bash
   POST /jobs
   {
     "prompt": "test topic",
     "pipeline": "quick"
   }
   ```

2. Wait for completion (check `GET /jobs/{id}`)

3. When `status: "completed"`, check `artifacts.drive_folder_url`

4. Open the URL in your browser - you should see the folder with 10 Google Docs + manifest.json

---

## Troubleshooting

### No Documents Created

**Symptom:** Job completes but no `artifacts.drive_folder_url`

**Possible Causes:**
1. Google OAuth credentials not configured
2. OAuth token expired/invalid
3. Drive API quota exceeded
4. Network error during upload

**Check Logs:**
```bash
# Look for errors from google_drive_docs.py
grep "Google" /path/to/celery.log
```

### Documents Created but Empty

**Symptom:** Documents exist but have no content

**Possible Cause:** Content insertion API call failed (non-fatal error)

**Solution:** Check worker logs for warnings:
```
WARNING - Failed to insert content into 01_RESEARCH_MAP: [error]
```

### Permission Denied Accessing Documents

**Symptom:** Frontend shows URL but clicking gives "Access Denied"

**Cause:** Documents are private to the service account

**Solution:**
1. Go to Drive folder
2. Share with your personal Google account
3. Or make folder publicly accessible (not recommended for production)

---

## Summary

**Where documents go:**
✅ Google Drive folder: `1xkrPgQSRwtlmqLsqdH3l0_YRNNVtySdH`

**How to access:**
✅ Click "Open in Drive" button in the dashboard
✅ Click document links in job detail page
✅ Directly via `artifacts.drive_folder_url` from API

**What gets created:**
✅ Research Jobs: 10 Google Docs + manifest.json
✅ Transcript Jobs: 1 Google Doc with all transcripts

**How it's stored:**
✅ Database: `jobs.artifacts.drive_folder_url` and `doc_urls`
✅ Google Drive: Real files accessible via browser
