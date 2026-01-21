# docs/authoritative/spec/Job_Config_Schema.md

**Purpose:** Canonical JSON schema for `jobs.config_json` and request payloads for job creation and source additions.

**Non‑negotiable:** The system is **mixed-input only**. Even a single source uses mixed-input shape.

---

## 1) Canonical job config (`jobs.config_json`)

### 1.1 Required top-level fields
- `input_mode`: MUST be `"mixed"`
- `research_topic`: string (may be empty, but MUST exist)
- `sources`: object containing arrays for the four user source types

### 1.2 Canonical `sources` object
- `video_urls`: string[]
- `article_urls`: string[]
- `text_inputs`: `TextInput[]`
- `screenshots`: `ScreenshotInput[]`

### 1.3 TextInput
```json
{
  "id": "string (unique within job)",
  "title": "string | null",
  "text": "string (required)",
  "source_label": "user_paste",
  "declared_verbatim": true
}
```

### 1.4 ScreenshotInput
```json
{
  "id": "string (unique within job)",
  "storage_path": "string (Supabase storage path)",
  "source_label": "user_screenshot",
  "declared_verbatim": false
}
```

### 1.5 Invariants
- `input_mode` MUST ALWAYS be `mixed`.
- All four arrays MUST exist even if empty.
- Each item must have stable IDs (no reassign on update).

---

## 2) API payload schemas (frontend-facing)

### 2.1 POST `/jobs/mixed-input` (create job with first source)

The frontend will send **exactly one** new source (first source) or possibly multiple sources if user pasted multiple at once.

Canonical create request:
```json
{
  "research_topic": "string",
  "sources": {
    "video_urls": ["string"],
    "article_urls": ["string"],
    "text_inputs": [
      {
        "id": "string",
        "title": "string | null",
        "text": "string",
        "source_label": "user_paste",
        "declared_verbatim": true
      }
    ],
    "screenshots": [
      {
        "id": "string",
        "storage_path": "string",
        "source_label": "user_screenshot",
        "declared_verbatim": false
      }
    ]
  }
}
```

Backend must transform this into `config_json` with:
- `input_mode="mixed"`
- all four arrays present

### 2.2 POST `/jobs/{job_id}/sources` (append a new source)

This endpoint appends exactly one new source.

Canonical request:
```json
{
  "source_kind": "youtube_url | article_url | text_paste | screenshot",
  "payload": {
    "youtube_url": "string (optional)",
    "article_url": "string (optional)",
    "text_input": {
      "id": "string",
      "title": "string | null",
      "text": "string",
      "source_label": "user_paste",
      "declared_verbatim": true
    },
    "screenshot": {
      "id": "string",
      "storage_path": "string",
      "source_label": "user_screenshot",
      "declared_verbatim": false
    }
  }
}
```

Append rules:
- `youtube_url` → append into `sources.video_urls`
- `article_url` → append into `sources.article_urls`
- `text_input` → append into `sources.text_inputs`
- `screenshot` → append into `sources.screenshots`

Duplicate rules:
- Duplicates MAY be rejected (recommended) with a warning.
- If accepted, they must still receive unique IDs.

### 2.3 POST `/jobs/{job_id}/process-pending`

This endpoint tells the system to process newly added sources.

Canonical request:
```json
{
  "process": "pending_sources",
  "reason": "user_added_source"
}
```

---

## 3) Mode mapping (derived, not user-specified)

User payload does not set analysis_mode.

Backend derives mode:
- video_urls → transcript chain; fallback to `video_only`
- article_urls → `article_fetched`
- text_inputs → `text_provided`
- screenshots → `ocr_extracted`

---

## 4) Machine-checkable JSON Schema for config_json

```json
{
  "type": "object",
  "required": ["input_mode", "research_topic", "sources"],
  "properties": {
    "input_mode": { "const": "mixed" },
    "research_topic": { "type": "string" },
    "sources": {
      "type": "object",
      "required": ["video_urls", "article_urls", "text_inputs", "screenshots"],
      "properties": {
        "video_urls": { "type": "array", "items": { "type": "string" } },
        "article_urls": { "type": "array", "items": { "type": "string" } },
        "text_inputs": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "text", "source_label"],
            "properties": {
              "id": { "type": "string" },
              "title": { "type": "string" },
              "text": { "type": "string" },
              "source_label": { "const": "user_paste" },
              "declared_verbatim": { "type": "boolean" }
            },
            "additionalProperties": false
          }
        },
        "screenshots": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "storage_path", "source_label"],
            "properties": {
              "id": { "type": "string" },
              "storage_path": { "type": "string" },
              "source_label": { "const": "user_screenshot" },
              "declared_verbatim": { "type": "boolean" }
            },
            "additionalProperties": false
          }
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

---

**END**

