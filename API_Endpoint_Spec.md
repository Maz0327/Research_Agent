# API Endpoint Specification

**Purpose:** Authoritative definition of all REST API endpoints for the Research Agent.

**Status:** PRESCRIPTIVE — Claude Code implements to this spec.

**Base URL:** `/api/v1`

---

## 1. Overview

### Authentication

All endpoints require JWT authentication via Supabase Auth.

```
Authorization: Bearer <jwt_token>
```

Unauthenticated requests return `401 Unauthorized`.

### Response Format

All responses follow this envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Or on error:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { ... }
  }
}
```

### Content Type

- Request: `application/json`
- Response: `application/json`

---

## 2. Jobs Endpoints

### 2.1 Create Job

**POST** `/api/v1/jobs`

Creates a new research job with one or more sources.

**Request Body:**

```json
{
  "sources": [
    {
      "type": "youtube",
      "url": "https://youtube.com/watch?v=..."
    },
    {
      "type": "youtube",
      "url": "https://youtube.com/watch?v=..."
    },
    {
      "type": "article",
      "url": "https://example.com/article"
    },
    {
      "type": "text",
      "content": "User-provided text content..."
    },
    {
      "type": "screenshot",
      "image_base64": "data:image/png;base64,..."
    }
  ],
  "options": {
    "skip_booster": false,
    "skip_producer": false
  }
}
```

**Source Types:**

| Type | Required Fields | Description |
|------|-----------------|-------------|
| `youtube` | `url` | YouTube video URL |
| `article` | `url` | Article/webpage URL |
| `text` | `content` | User-pasted text |
| `screenshot` | `image_base64` | Base64-encoded image |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "pending",
    "source_count": 4,
    "created_at": "2026-01-13T14:30:00Z",
    "estimated_duration_seconds": 120
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `INVALID_SOURCE_TYPE` | 400 | Unknown source type |
| `INVALID_URL` | 400 | Malformed URL |
| `NO_SOURCES` | 400 | Empty sources array |
| `TOO_MANY_SOURCES` | 400 | More than 20 sources |
| `INVALID_IMAGE` | 400 | Cannot decode base64 image |

---

### 2.2 Get Job

**GET** `/api/v1/jobs/{job_id}`

Retrieves job status and metadata. Used for polling.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "extracting",
    "created_at": "2026-01-13T14:30:00Z",
    "started_at": "2026-01-13T14:30:01Z",
    "completed_at": null,
    "processing_time_seconds": null,
    "source_count": 4,
    "sources_acquired": 4,
    "sources_extracted": 2,
    "sources_validated": 0,
    "warning_count": 1,
    "progress": {
      "stage": "extracting",
      "percent": 50,
      "message": "Extracting source 2 of 4"
    },
    "has_artifacts": false,
    "has_producer_packet": false,
    "has_booster": false
  },
  "error": null
}
```

**Status Values:**

| Status | Description | Terminal? |
|--------|-------------|-----------|
| `pending` | Job created, queued | No |
| `acquiring_sources` | Fetching metadata/transcripts | No |
| `extracting` | Running Gemini extraction | No |
| `validating` | Validating extractions | No |
| `synthesizing` | Cross-source synthesis | No |
| `assembling` | Building documents | No |
| `completed` | Done, artifacts ready | Yes |
| `completed_with_warnings` | Done with degradation | Yes |
| `failed` | Infrastructure failure | Yes |
| `running_booster` | Booster in progress | No |
| `running_producer` | Producer in progress | No |

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `ACCESS_DENIED` | 403 | Job belongs to another user |

---

### 2.3 List Jobs

**GET** `/api/v1/jobs`

Lists all jobs for the authenticated user.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | (all) | Filter by status |
| `limit` | int | 20 | Max results (1-100) |
| `offset` | int | 0 | Pagination offset |
| `sort` | string | `created_at:desc` | Sort field and direction |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "job_abc123",
        "status": "completed",
        "source_count": 4,
        "warning_count": 0,
        "created_at": "2026-01-13T14:30:00Z",
        "completed_at": "2026-01-13T14:32:15Z"
      },
      {
        "job_id": "job_def456",
        "status": "extracting",
        "source_count": 2,
        "warning_count": 1,
        "created_at": "2026-01-13T14:35:00Z",
        "completed_at": null
      }
    ],
    "total": 47,
    "limit": 20,
    "offset": 0
  },
  "error": null
}
```

---

### 2.4 Cancel Job

**POST** `/api/v1/jobs/{job_id}/cancel`

Cancels a job in progress. Only works for non-terminal statuses.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "failed",
    "cancelled": true,
    "cancelled_at": "2026-01-13T14:31:00Z"
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `JOB_ALREADY_COMPLETE` | 400 | Cannot cancel completed job |
| `JOB_ALREADY_FAILED` | 400 | Job already failed |

---

### 2.5 Delete Job

**DELETE** `/api/v1/jobs/{job_id}`

Permanently deletes a job and all associated data.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "deleted": true
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `JOB_IN_PROGRESS` | 400 | Cannot delete while processing |

---

### 2.6 Create Text Input Job

**POST** `/api/v1/jobs/text-input`

Creates a job from user-provided text content.

**Request Body:**

```json
{
  "title": "My Research Notes",
  "content": "The full text content to analyze...",
  "platform_hint": "reddit"
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Title for the text source |
| `content` | string | Yes | Text content (max 50,000 chars) |
| `platform_hint` | string | No | Source platform hint |

**Platform Hints:** `reddit`, `twitter`, `forum`, `article`, `notes`, `other`

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "pending",
    "analysis_mode": "text_provided",
    "confidence_ceiling": "medium"
  },
  "error": null
}
```

---

### 2.7 Create Screenshot Input Job

**POST** `/api/v1/jobs/screenshot-input`

Creates a job from a screenshot image (OCR extraction).

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Image file (PNG, JPG, max 10MB) |
| `platform_hint` | string | No | Platform hint for context |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "pending",
    "analysis_mode": "ocr_extracted",
    "confidence_ceiling": "medium",
    "ocr_preview": "First 200 chars of extracted text..."
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `INVALID_IMAGE` | 400 | Cannot decode image |
| `FILE_TOO_LARGE` | 400 | Exceeds 10MB limit |
| `UNSUPPORTED_FORMAT` | 400 | Not PNG/JPG/JPEG |

---

### 2.8 Create Mixed Input Job

**POST** `/api/v1/jobs/mixed-input`

Creates a job with multiple source types in one request.

**Request Body:**

```json
{
  "video_urls": ["https://youtube.com/watch?v=..."],
  "article_urls": ["https://example.com/article"],
  "text_inputs": [
    {"title": "Notes", "content": "..."}
  ]
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "pending",
    "sources_queued": 3
  },
  "error": null
}
```

---

### 2.9 Process Pending Sources

**POST** `/api/v1/jobs/{job_id}/process-pending`

Triggers processing of pending sources added to a completed job.

**Preconditions:**
- Job has pending sources (added via POST /jobs/{job_id}/sources)

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "processing",
    "pending_sources": 3,
    "message": "Processing started"
  },
  "error": null
}
```

---

## 3. Sources Endpoints

### 3.1 List Job Sources

**GET** `/api/v1/jobs/{job_id}/sources`

Lists all sources for a job with their individual status.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "sources": [
      {
        "source_id": "SRC_1",
        "type": "youtube",
        "url": "https://youtube.com/watch?v=...",
        "title": "Video Title",
        "creator": "Channel Name",
        "published_date": "2025-12-01",
        "duration": "14:32",
        "analysis_mode": "transcript_grounded",
        "confidence_ceiling": "high",
        "transcript_source": "supadata",
        "status": "extracted",
        "warnings": []
      },
      {
        "source_id": "SRC_2",
        "type": "youtube",
        "url": "https://youtube.com/watch?v=...",
        "title": "Another Video",
        "creator": "Other Channel",
        "published_date": "2025-11-15",
        "duration": "22:10",
        "analysis_mode": "video_only",
        "confidence_ceiling": "low",
        "transcript_source": "none",
        "status": "extracted",
        "warnings": [
          {
            "code": "transcript_unavailable",
            "message": "No transcript available, using video_only mode"
          }
        ]
      }
    ]
  },
  "error": null
}
```

**Source Status Values:**

| Status | Description |
|--------|-------------|
| `pending` | Not yet processed |
| `acquiring` | Fetching metadata/transcript |
| `acquired` | Metadata and transcript ready |
| `extracting` | Gemini extraction in progress |
| `extracted` | Extraction complete |
| `validated` | Validation passed |
| `failed` | Source processing failed |

---

### 3.2 Add Source to Job

**POST** `/api/v1/jobs/{job_id}/sources`

Adds a new source to an existing completed job (evolving jobs pattern).

**Preconditions:**
- Job must be in `completed` or `completed_with_warnings` status

**Request Body:**

```json
{
  "source": {
    "type": "youtube",
    "url": "https://youtube.com/watch?v=..."
  }
}
```

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "source_id": "SRC_5",
    "status": "acquiring_sources",
    "message": "Source added, reprocessing job"
  },
  "error": null
}
```

**Behavior:**
1. Job status changes to `acquiring_sources`
2. New source is processed through full pipeline
3. Synthesis re-runs with all sources
4. Documents are regenerated (addendum pattern)
5. Job returns to completed status

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `JOB_NOT_COMPLETE` | 400 | Can only add sources to completed jobs |
| `MAX_SOURCES_REACHED` | 400 | Already at 20 sources |

---

### 3.3 Get Source Details

**GET** `/api/v1/jobs/{job_id}/sources/{source_id}`

Gets detailed information about a specific source.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "source_id": "SRC_1",
    "type": "youtube",
    "url": "https://youtube.com/watch?v=...",
    "metadata": {
      "title": "Video Title",
      "creator": "Channel Name",
      "published_date": "2025-12-01",
      "duration": "14:32",
      "description": "Video description text..."
    },
    "provenance": {
      "transcript_source": "supadata",
      "analysis_mode": "transcript_grounded",
      "confidence_ceiling": "high",
      "transcript_length": 8542
    },
    "extraction": {
      "key_points_count": 12,
      "claims_count": 8,
      "themes_count": 4,
      "quotes_count": 15,
      "observations_count": 0
    },
    "validation": {
      "passed": true,
      "checks_run": ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9"],
      "checks_failed": [],
      "warnings": []
    }
  },
  "error": null
}
```

---

## 4. Documents Endpoints

### 4.1 Get All Documents

**GET** `/api/v1/jobs/{job_id}/documents`

Retrieves all generated documents for a completed job.

**Preconditions:**
- Job must be in `completed` or `completed_with_warnings` status

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "documents": {
      "doc_0": {
        "name": "Source Ledger",
        "available": true,
        "format": "json",
        "size_bytes": 45230
      },
      "doc_1": {
        "name": "Jump-Start Directions",
        "available": true,
        "format": "json",
        "size_bytes": 12450
      },
      "doc_2": {
        "name": "Semantic Brief",
        "available": true,
        "format": "json",
        "size_bytes": 28900
      },
      "doc_3": {
        "name": "Producer Packet",
        "available": false,
        "gating_met": false,
        "gating_reason": "Requires 4+ sources (have 2)"
      }
    },
    "markdown_available": true
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `JOB_NOT_COMPLETE` | 400 | Documents not yet available |

---

### 4.2 Get Document (JSON)

**GET** `/api/v1/jobs/{job_id}/documents/{doc_type}`

Retrieves a specific document in JSON format.

**Path Parameters:**
- `doc_type`: One of `doc_0`, `doc_1`, `doc_2`, `doc_3`

**Response (200 OK):**

For Doc 0 (Source Ledger):
```json
{
  "success": true,
  "data": {
    "document_type": "source_ledger",
    "version": "1.0",
    "generated_at": "2026-01-13T14:32:15Z",
    "job_id": "job_abc123",
    "content": {
      "sources": [
        {
          "source_id": "SRC_1",
          "url": "https://youtube.com/watch?v=...",
          "title": "Video Title",
          "creator": "Channel Name",
          "published_date": "2025-12-01",
          "duration": "14:32",
          "transcript_provenance": {
            "source": "supadata",
            "mode": "transcript_grounded",
            "confidence_ceiling": "high"
          },
          "transcript_text": "Full transcript content...",
          "skim_summary": "Brief factual summary...",
          "entity_index": ["Person A", "Company X", "Event Y"],
          "timestamp_index": [
            {"time": "02:15", "description": "Discussion of X begins"},
            {"time": "08:42", "description": "Key claim about Y"}
          ]
        }
      ],
      "metadata": {
        "total_sources": 2,
        "sources_with_transcript": 1,
        "sources_video_only": 1
      }
    }
  },
  "error": null
}
```

For Doc 1 (Jump-Start Directions):
```json
{
  "success": true,
  "data": {
    "document_type": "jump_start_directions",
    "version": "1.0",
    "generated_at": "2026-01-13T14:32:15Z",
    "job_id": "job_abc123",
    "content": {
      "scope_lock": {
        "covers": ["Topic A", "Event B", "Person C's involvement"],
        "does_not_cover": ["Unrelated topic X", "Historical background Y"]
      },
      "what_is_known": [
        "Fact 1 with source attribution [SRC_1]",
        "Fact 2 with source attribution [SRC_1, SRC_2]"
      ],
      "gaps": [
        {
          "gap_id": "GAP_1",
          "description": "Missing primary source documentation",
          "impact": "Cannot verify timeline claims",
          "priority": "high"
        }
      ],
      "research_directions": [
        {
          "direction_id": "DIR_1",
          "description": "Locate original announcement",
          "suggested_queries": ["query 1", "query 2"],
          "expected_source_types": ["press release", "archived page"]
        }
      ],
      "top_3_next_steps": [
        "Step 1: Do this specific thing",
        "Step 2: Then do this",
        "Step 3: Finally, verify with this"
      ],
      "verification_checklist": [
        "[ ] Verify date of Event X",
        "[ ] Confirm Person A's role",
        "[ ] Cross-reference with Source Z"
      ]
    }
  },
  "error": null
}
```

For Doc 2 (Semantic Brief):
```json
{
  "success": true,
  "data": {
    "document_type": "semantic_brief",
    "version": "1.0",
    "generated_at": "2026-01-13T14:32:15Z",
    "job_id": "job_abc123",
    "content": {
      "semantic_core": "2-4 sentence description of what this is really about",
      "confidence_assessment": {
        "overall": "medium",
        "limiting_factors": ["Single high-confidence source", "Timeline gaps"],
        "strongest_claims": ["Claim X", "Claim Y"],
        "weakest_claims": ["Claim Z"]
      },
      "themes": [
        {
          "theme_id": "THEME_1",
          "label": "Theme Name",
          "description": "What this theme represents",
          "related_key_points": ["KP_1", "KP_3", "KP_5"],
          "cross_source_support": true
        }
      ],
      "key_points": [
        {
          "key_point_id": "KP_1",
          "statement": "The key point statement",
          "source_ids": ["SRC_1"],
          "confidence": "high",
          "supporting_quotes": [
            {
              "quote_id": "Q_1",
              "text": "Verbatim quote from source",
              "timestamp": "04:32",
              "source_id": "SRC_1"
            }
          ]
        }
      ],
      "tensions": [
        {
          "tension_id": "TEN_1",
          "description": "Description of contradiction or conflict",
          "involved_key_points": ["KP_2", "KP_7"],
          "resolution_status": "unresolved"
        }
      ],
      "speculation": {
        "permitted": true,
        "items": [
          {
            "speculation_id": "SPEC_1",
            "statement": "Speculative interpretation",
            "basis": "Based on KP_1 and KP_3",
            "confidence": "low",
            "clearly_labeled": true
          }
        ]
      }
    }
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `DOCUMENT_NOT_FOUND` | 404 | Document type doesn't exist |
| `DOCUMENT_NOT_AVAILABLE` | 400 | Document not yet generated |
| `GATING_NOT_MET` | 400 | Doc 3 gating requirements not met |

---

### 4.3 Get Document (Markdown)

**GET** `/api/v1/jobs/{job_id}/documents/{doc_type}/markdown`

Retrieves a specific document in Markdown format for human reading.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "document_type": "semantic_brief",
    "format": "markdown",
    "content": "# Semantic Research Brief\n\n## Overview\n\n..."
  },
  "error": null
}
```

---

### 4.4 Export Documents

**GET** `/api/v1/jobs/{job_id}/documents/export`

Exports all documents in specified format.

**Query Parameters:**

| Param | Type | Default | Options |
|-------|------|---------|---------|
| `format` | string | `json` | `json`, `markdown`, `zip` |
| `include` | string | `all` | `all`, `doc_0`, `doc_1`, `doc_2`, `doc_3` |

**Response (200 OK) for `format=zip`:**

Returns binary ZIP file with `Content-Type: application/zip`.

**Response (200 OK) for `format=json`:**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "exported_at": "2026-01-13T14:35:00Z",
    "documents": {
      "doc_0": { ... },
      "doc_1": { ... },
      "doc_2": { ... }
    }
  },
  "error": null
}
```

---

## 5. Booster Endpoints

### 5.1 Trigger Booster

**POST** `/api/v1/jobs/{job_id}/booster`

Triggers the Deep Research Booster pipeline.

**Preconditions:**
- Job must be in `completed` or `completed_with_warnings` status
- Booster not already run for this job

**Request Body:**

```json
{
  "options": {
    "depth": "standard",
    "focus_areas": ["timeline", "claims"]
  }
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `depth` | string | `standard` | `quick`, `standard`, `deep` |
| `focus_areas` | array | (all) | Areas to focus on |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "booster_id": "boost_xyz789",
    "status": "running_booster",
    "estimated_duration_seconds": 60
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `JOB_NOT_COMPLETE` | 400 | Job must be complete first |
| `BOOSTER_ALREADY_RUN` | 400 | Booster already executed |

---

### 5.2 Get Booster Status

**GET** `/api/v1/jobs/{job_id}/booster`

Gets booster status and results.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "booster_id": "boost_xyz789",
    "status": "completed",
    "started_at": "2026-01-13T14:35:00Z",
    "completed_at": "2026-01-13T14:36:15Z",
    "stages_completed": 4,
    "doc_1_augmented": true,
    "new_directions_count": 8,
    "new_queries_count": 24
  },
  "error": null
}
```

---

## 6. Producer Packet Endpoints

### 6.1 Check Producer Eligibility

**GET** `/api/v1/jobs/{job_id}/producer/eligibility`

Checks if job meets Doc 3 gating requirements.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "eligible": false,
    "requirements": {
      "min_sources": {
        "required": 4,
        "actual": 2,
        "met": false
      },
      "high_confidence_source": {
        "required": 1,
        "actual": 1,
        "met": true
      }
    },
    "message": "Need 2 more sources to generate Producer Packet"
  },
  "error": null
}
```

---

### 6.2 Trigger Producer Packet

**POST** `/api/v1/jobs/{job_id}/producer`

Triggers the Producer Packet pipeline (Doc 3).

**Preconditions:**
- Job must be in `completed` or `completed_with_warnings` status
- Must meet gating requirements (V10)
- Producer packet not already generated

**Request Body:**

```json
{
  "options": {
    "content_type": "documentary",
    "tone": "investigative",
    "include_risk_assessment": true
  }
}
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `content_type` | string | `documentary` | `documentary`, `explainer`, `opinion`, `livestream` |
| `tone` | string | `neutral` | `neutral`, `investigative`, `educational` |
| `include_risk_assessment` | bool | `true` | Include landmines section |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "producer_id": "prod_abc123",
    "status": "running_producer",
    "estimated_duration_seconds": 90
  },
  "error": null
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `JOB_NOT_FOUND` | 404 | Job doesn't exist |
| `JOB_NOT_COMPLETE` | 400 | Job must be complete first |
| `GATING_NOT_MET` | 400 | Requirements not satisfied |
| `PRODUCER_ALREADY_RUN` | 400 | Doc 3 already generated |

---

### 6.3 Get Producer Status

**GET** `/api/v1/jobs/{job_id}/producer`

Gets producer packet status and results.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "producer_id": "prod_abc123",
    "status": "completed",
    "started_at": "2026-01-13T14:40:00Z",
    "completed_at": "2026-01-13T14:42:30Z",
    "stages_completed": 4,
    "doc_3_available": true,
    "angles_generated": 4,
    "structures_generated": 3
  },
  "error": null
}
```

---

## 7. Warnings Endpoints

### 7.1 Get Job Warnings

**GET** `/api/v1/jobs/{job_id}/warnings`

Gets all warnings for a job.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "warning_count": 3,
    "warnings": [
      {
        "code": "transcript_unavailable",
        "stage": "acquiring_sources",
        "source_id": "SRC_2",
        "message": "No transcript available for source, using video_only mode",
        "timestamp": "2026-01-13T14:30:15Z",
        "details": {
          "tried": ["supadata", "whisper", "youtube_captions"],
          "fallback_mode": "video_only"
        }
      },
      {
        "code": "validation_quotes_removed",
        "stage": "validating",
        "source_id": "SRC_1",
        "message": "2 quotes failed verification and were removed",
        "timestamp": "2026-01-13T14:31:45Z",
        "details": {
          "removed_count": 2,
          "remaining_count": 13
        }
      },
      {
        "code": "confidence_clamped",
        "stage": "validating",
        "source_id": "SRC_2",
        "message": "Confidence values clamped to ceiling (low)",
        "timestamp": "2026-01-13T14:31:50Z",
        "details": {
          "ceiling": "low",
          "clamped_fields": ["key_points", "claims"]
        }
      }
    ]
  },
  "error": null
}
```

---

## 8. Health & Status Endpoints

### 8.1 Health Check

**GET** `/api/v1/health`

Basic health check (no auth required).

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2026-01-13T14:30:00Z"
  },
  "error": null
}
```

---

### 8.2 System Status

**GET** `/api/v1/status`

Detailed system status (auth required).

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "celery": {
      "status": "healthy",
      "workers": 2,
      "queued_tasks": 5
    },
    "integrations": {
      "supadata": "healthy",
      "gemini": "healthy",
      "whisper": "healthy"
    }
  },
  "error": null
}
```

---

## 9. Polling Pattern

### Recommended Polling Strategy

For job status updates:

```javascript
const POLL_INTERVALS = {
  'pending': 2000,           // 2 seconds
  'acquiring_sources': 3000, // 3 seconds
  'extracting': 5000,        // 5 seconds (longest stage)
  'validating': 2000,        // 2 seconds
  'synthesizing': 3000,      // 3 seconds
  'assembling': 2000,        // 2 seconds
  'running_booster': 3000,   // 3 seconds
  'running_producer': 3000,  // 3 seconds
};

async function pollJob(jobId) {
  const response = await fetch(`/api/v1/jobs/${jobId}`);
  const { data } = await response.json();
  
  if (['completed', 'completed_with_warnings', 'failed'].includes(data.status)) {
    return data; // Terminal state, stop polling
  }
  
  const interval = POLL_INTERVALS[data.status] || 3000;
  await sleep(interval);
  return pollJob(jobId);
}
```

### Progress Calculation

```javascript
const STAGE_WEIGHTS = {
  'pending': 0,
  'acquiring_sources': 15,
  'extracting': 50,
  'validating': 65,
  'synthesizing': 80,
  'assembling': 95,
  'completed': 100,
  'completed_with_warnings': 100,
  'failed': 100,
};
```

---

## 10. Error Codes Reference

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async operation started) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (access denied) |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |

### Application Error Codes

| Code | Description |
|------|-------------|
| `INVALID_SOURCE_TYPE` | Unknown source type provided |
| `INVALID_URL` | Malformed URL |
| `NO_SOURCES` | No sources provided |
| `TOO_MANY_SOURCES` | Exceeded source limit |
| `INVALID_IMAGE` | Cannot decode image |
| `JOB_NOT_FOUND` | Job ID doesn't exist |
| `ACCESS_DENIED` | User doesn't own this job |
| `JOB_NOT_COMPLETE` | Operation requires completed job |
| `JOB_ALREADY_COMPLETE` | Cannot modify completed job |
| `JOB_ALREADY_FAILED` | Job already in failed state |
| `JOB_IN_PROGRESS` | Cannot delete while processing |
| `DOCUMENT_NOT_FOUND` | Document type doesn't exist |
| `DOCUMENT_NOT_AVAILABLE` | Document not yet generated |
| `GATING_NOT_MET` | Doc 3 requirements not satisfied |
| `BOOSTER_ALREADY_RUN` | Booster already executed |
| `PRODUCER_ALREADY_RUN` | Producer already executed |
| `MAX_SOURCES_REACHED` | Source limit reached |
| `RATE_LIMITED` | Too many requests |
| `INTERNAL_ERROR` | Unexpected server error |

---

## 11. Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /jobs` | 10 | per minute |
| `GET /jobs/{id}` | 60 | per minute |
| `GET /jobs` | 30 | per minute |
| `POST /jobs/{id}/sources` | 5 | per minute |
| `POST /jobs/{id}/booster` | 5 | per minute |
| `POST /jobs/{id}/producer` | 5 | per minute |
| All other endpoints | 60 | per minute |

---

**END OF SPECIFICATION**
