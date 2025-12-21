# Settings Page Design Document

**Date:** December 20, 2024
**Status:** Ready for Implementation

---

## Overview

The Research Agent needs a functional settings page where users can configure:
1. **Google Drive Output Folder** - Where research documents are saved
2. **Default Pipeline** - Preferred research mode
3. **Notification Preferences** - Email on job completion
4. **Display Preferences** - UI customization

---

## Settings Categories

### 1. Google Drive Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `drive_folder_id` | string | null (uses system default) | Custom Google Drive folder ID |
| `drive_folder_url` | string | null | Derived URL for display |
| `use_custom_folder` | boolean | false | Toggle custom vs system folder |

**How Folder ID Works:**
- Users paste a Google Drive folder URL
- We extract the folder ID from the URL pattern: `https://drive.google.com/drive/folders/{FOLDER_ID}`
- The folder must be shared with the service account email (or user authorizes)

**User Flow:**
1. User creates/selects a folder in their Google Drive
2. Clicks "Share" and adds the service account email (or clicks our auth button)
3. Pastes the folder URL into settings
4. We validate the folder is accessible
5. Future jobs go to this folder

---

### 2. Research Pipeline Settings

| Setting | Type | Default | Options |
|---------|------|---------|---------|
| `default_pipeline` | enum | "investigation" | quick, full, breaking_news, investigation, profile, controversy |
| `auto_extract_claims` | boolean | true | Enable/disable claim extraction |
| `max_sources` | number | 25 | Limit sources per job (5-50) |

**Pipeline Descriptions:**
- **Quick** - Fast turnaround, fewer sources (5-10 min)
- **Full** - Comprehensive research (15-20 min)
- **Breaking News** - Current events, rapid coverage
- **Investigation** - Deep-dive investigative reporting
- **Profile** - Character-driven biographical research
- **Controversy** - Balanced multi-perspective analysis

---

### 3. Notification Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `email_on_complete` | boolean | true | Email when job finishes |
| `email_on_failure` | boolean | true | Email when job fails |
| `email_summary` | boolean | false | Daily summary of completed jobs |

---

### 4. Display Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `jobs_per_page` | number | 10 | Jobs shown on dashboard (5-25) |
| `default_sort` | enum | "newest" | newest, oldest, status |
| `show_progress_details` | boolean | true | Show stage names during progress |

---

## Database Schema

### Option A: Dedicated Settings Table (Recommended)

```sql
-- Migration: 007_add_user_settings.sql

CREATE TABLE user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Google Drive Settings
    drive_folder_id TEXT,
    use_custom_folder BOOLEAN DEFAULT false,

    -- Pipeline Settings
    default_pipeline TEXT DEFAULT 'investigation',
    auto_extract_claims BOOLEAN DEFAULT true,
    max_sources INTEGER DEFAULT 25,

    -- Notification Settings
    email_on_complete BOOLEAN DEFAULT true,
    email_on_failure BOOLEAN DEFAULT true,
    email_summary BOOLEAN DEFAULT false,

    -- Display Settings
    jobs_per_page INTEGER DEFAULT 10,
    default_sort TEXT DEFAULT 'newest',
    show_progress_details BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one settings row per user
    UNIQUE(user_id)
);

-- Row-Level Security
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Users can only view/edit their own settings
CREATE POLICY "Users can view own settings"
    ON user_settings FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own settings"
    ON user_settings FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own settings"
    ON user_settings FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Service role can do anything (for backend operations)
CREATE POLICY "Service role bypass"
    ON user_settings FOR ALL
    USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Index for fast lookups
CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_user_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_settings_updated_at();
```

---

## API Endpoints

### GET /settings

Get current user's settings (creates default if none exist).

**Response:**
```json
{
  "drive_folder_id": null,
  "drive_folder_url": null,
  "use_custom_folder": false,
  "default_pipeline": "investigation",
  "auto_extract_claims": true,
  "max_sources": 25,
  "email_on_complete": true,
  "email_on_failure": true,
  "email_summary": false,
  "jobs_per_page": 10,
  "default_sort": "newest",
  "show_progress_details": true
}
```

### PUT /settings

Update user's settings.

**Request:**
```json
{
  "drive_folder_id": "1a2b3c4d5e6f",
  "default_pipeline": "investigation",
  "email_on_complete": false
}
```

**Response:**
```json
{
  "success": true,
  "settings": { ... }
}
```

### POST /settings/validate-folder

Validate a Google Drive folder is accessible.

**Request:**
```json
{
  "folder_url": "https://drive.google.com/drive/folders/1a2b3c4d5e6f"
}
```

**Response:**
```json
{
  "valid": true,
  "folder_id": "1a2b3c4d5e6f",
  "folder_name": "My Research Folder",
  "accessible": true
}
```

---

## Frontend Implementation

### Settings Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Settings                                                         │
│ Manage your account and research preferences                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ┌─── Account ───────────────────────────────────────────────┐   │
│ │ Email: user@example.com                                    │   │
│ │ User ID: abc-123-def                                       │   │
│ │ Last Sign In: December 20, 2024 at 2:30 PM                │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─── Google Drive Output ────────────────────────────────────┐   │
│ │                                                            │   │
│ │ ○ Use system default folder                                │   │
│ │ ● Use custom folder                                        │   │
│ │                                                            │   │
│ │ Folder URL:                                                │   │
│ │ ┌──────────────────────────────────────────┐ [Validate]   │   │
│ │ │ https://drive.google.com/drive/folders/..│               │   │
│ │ └──────────────────────────────────────────┘               │   │
│ │ ✓ Folder accessible: "My Research Folder"                  │   │
│ │                                                            │   │
│ │ ℹ️ Research documents will be saved to this folder.         │   │
│ │    Make sure the folder is shared with you.                │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─── Default Pipeline ───────────────────────────────────────┐   │
│ │                                                            │   │
│ │ When creating new research jobs, use:                      │   │
│ │                                                            │   │
│ │ ┌────────────────────────────────────────────────────────┐ │   │
│ │ │ Investigation ▼                                        │ │   │
│ │ └────────────────────────────────────────────────────────┘ │   │
│ │                                                            │   │
│ │ Deep-dive investigative reporting with comprehensive       │   │
│ │ source validation and claim verification.                  │   │
│ │                                                            │   │
│ │ ☑ Auto-extract claims from sources                         │   │
│ │ Max sources: [25] (5-50)                                   │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─── Notifications ──────────────────────────────────────────┐   │
│ │                                                            │   │
│ │ ☑ Email me when a job completes                            │   │
│ │ ☑ Email me when a job fails                                │   │
│ │ ☐ Send daily summary of completed jobs                     │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─── Display ────────────────────────────────────────────────┐   │
│ │                                                            │   │
│ │ Jobs per page: [10] (5-25)                                 │   │
│ │ Default sort: [Newest first ▼]                             │   │
│ │ ☑ Show detailed progress during jobs                       │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│                                           [Cancel] [Save Changes]│
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Files

### Backend Files to Create/Modify

1. **`backend/models/user_settings.py`** (NEW)
   - Pydantic models for settings

2. **`backend/state/settings_store.py`** (NEW)
   - CRUD operations for user_settings table

3. **`backend/app/main.py`** (MODIFY)
   - Add settings endpoints

4. **`backend/migrations/007_add_user_settings.sql`** (NEW)
   - Database migration

5. **`backend/integrations/google_drive_docs.py`** (MODIFY)
   - Read user's custom folder from settings

### Frontend Files to Create/Modify

1. **`frontend/pages/settings.tsx`** (MODIFY)
   - Replace placeholder with full settings UI

2. **`frontend/store/settings.ts`** (NEW)
   - Zustand store for settings state

3. **`frontend/components/settings/`** (NEW)
   - `DriveSettings.tsx` - Google Drive folder config
   - `PipelineSettings.tsx` - Default pipeline config
   - `NotificationSettings.tsx` - Email preferences
   - `DisplaySettings.tsx` - UI preferences

---

## Implementation Priority

### Phase 1 (MVP) - Essential Settings
1. Google Drive folder selection
2. Default pipeline preference
3. Basic UI implementation

### Phase 2 - Enhanced Settings
4. Notification preferences
5. Display preferences
6. Settings validation

### Phase 3 - Advanced Features
7. Folder validation via API
8. Settings import/export
9. Admin override capabilities

---

## Google Drive Folder Selection - User Flow

### Option 1: Paste URL (Simplest)

1. User goes to Google Drive
2. Creates or selects a folder
3. Copies the folder URL from browser
4. Pastes URL into settings
5. We parse folder ID: `https://drive.google.com/drive/folders/{ID}`
6. We validate folder is accessible with service account
7. Save folder ID to user settings

**Pros:** Simple, no OAuth complexity
**Cons:** User must manually share folder with service account

### Option 2: Drive Picker (More Polish)

1. User clicks "Select Folder" button
2. Google Drive Picker opens in popup
3. User browses/selects folder
4. Picker returns folder ID
5. We save to settings

**Pros:** Better UX, folder is automatically shared
**Cons:** Requires Drive Picker API setup, more frontend code

### Recommendation: Start with Option 1

For MVP, paste URL is sufficient. Add Drive Picker in future if needed.

---

## Service Account Sharing

For the paste URL option to work, users need to share their folder with our service account.

**Service Account Email:** (get from Google Cloud Console)
```
research-agent@your-project.iam.gserviceaccount.com
```

**Instructions for Users:**
1. Open your folder in Google Drive
2. Click "Share" button
3. Add: `research-agent@your-project.iam.gserviceaccount.com`
4. Set permission to "Editor"
5. Click "Send" (or "Share")
6. Paste folder URL in settings

---

## Error Handling

### Common Errors

| Error | Cause | User Message |
|-------|-------|--------------|
| Invalid URL | Bad format | "Please enter a valid Google Drive folder URL" |
| Folder not found | Deleted/wrong ID | "Folder not found. Check the URL and try again." |
| Permission denied | Not shared | "Cannot access folder. Please share it with our service account." |
| Network error | API failure | "Could not validate folder. Please try again." |

---

## Validation Rules

### Folder URL Validation

```typescript
const DRIVE_FOLDER_REGEX = /^https:\/\/drive\.google\.com\/drive\/(?:u\/\d+\/)?folders\/([a-zA-Z0-9_-]+)/;

function extractFolderId(url: string): string | null {
  const match = url.match(DRIVE_FOLDER_REGEX);
  return match ? match[1] : null;
}
```

### Settings Validation

| Field | Rules |
|-------|-------|
| `drive_folder_id` | Optional, alphanumeric + underscore + hyphen |
| `default_pipeline` | Enum: quick, full, breaking_news, investigation, profile, controversy |
| `max_sources` | Integer 5-50 |
| `jobs_per_page` | Integer 5-25 |
| `default_sort` | Enum: newest, oldest, status |

---

## Testing Checklist

### Settings API
- [ ] GET /settings returns defaults for new user
- [ ] PUT /settings updates settings correctly
- [ ] PUT /settings validates input
- [ ] Settings persist across sessions
- [ ] RLS prevents access to other users' settings

### Google Drive Integration
- [ ] Folder URL parsing extracts correct ID
- [ ] Invalid URLs are rejected
- [ ] Folder validation checks accessibility
- [ ] Jobs use custom folder when set
- [ ] Jobs use system folder when not set

### Frontend
- [ ] Settings page loads user's settings
- [ ] Form validates input before submit
- [ ] Save shows success/error message
- [ ] Changes reflect immediately after save
- [ ] Settings persist after page refresh

---

## Future Enhancements

1. **OAuth-based folder selection** - Let users authorize their own Drive
2. **Multiple folders** - Different folders for different pipelines
3. **Team settings** - Shared settings for teams
4. **API key management** - User's own OpenAI/Perplexity keys
5. **Usage quotas** - Limit jobs per day/month
6. **Webhook notifications** - POST to user's endpoint on completion

---

## Summary

The settings page should provide:

1. **Google Drive folder** - Custom output location
2. **Default pipeline** - Preferred research mode
3. **Notifications** - Email preferences
4. **Display** - UI customization

Start with Phase 1 (Drive folder + pipeline) for MVP, then add notifications and display settings in Phase 2.
