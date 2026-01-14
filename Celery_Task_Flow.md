# Celery Task Flow Specification

**Purpose:** Authoritative definition of all Celery tasks, their orchestration, and failure handling.

**Status:** PRESCRIPTIVE — Claude Code implements to this spec.

---

## 1. Overview

### Task Queue Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Redis Broker                            │
└─────────────────────────────────────────────────────────────────┘
                    │                         │
         ┌──────────┴──────────┐    ┌────────┴────────┐
         │   default queue     │    │  priority queue │
         │  (standard jobs)    │    │ (booster/producer) │
         └──────────┬──────────┘    └────────┬────────┘
                    │                         │
         ┌──────────┴──────────────────────────┴──────────┐
         │                  Celery Workers                 │
         │            (2-4 concurrent workers)            │
         └─────────────────────────────────────────────────┘
```

### Queue Configuration

```python
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'priority': {
        'exchange': 'priority',
        'routing_key': 'priority',
    },
}

CELERY_TASK_ROUTES = {
    'tasks.run_semantic_job': {'queue': 'default'},
    'tasks.run_booster': {'queue': 'priority'},
    'tasks.run_producer': {'queue': 'priority'},
}
```

---

## 2. Task Inventory

| Task | Purpose | Triggered By | Queue |
|------|---------|--------------|-------|
| `run_semantic_job` | Main job orchestrator | API: POST /jobs | default |
| `acquire_source` | Fetch metadata + transcript | run_semantic_job | default |
| `extract_source` | Run Gemini extraction | run_semantic_job | default |
| `validate_extraction` | Run V1-V9 checks | run_semantic_job | default |
| `run_synthesis` | Cross-source synthesis | run_semantic_job | default |
| `assemble_documents` | Build Doc 0/1/2 | run_semantic_job | default |
| `run_booster` | 4-stage booster pipeline | API: POST /jobs/{id}/booster | priority |
| `run_producer` | 4-stage producer pipeline | API: POST /jobs/{id}/producer | priority |
| `add_source_to_job` | Evolving job handler | API: POST /jobs/{id}/sources | default |

---

## 3. Main Job Task

### 3.1 `run_semantic_job`

**Purpose:** Orchestrates the entire semantic pipeline for a job.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=0,  # No retry at orchestrator level
    soft_time_limit=600,  # 10 minutes
    hard_time_limit=660,  # 11 minutes
)
def run_semantic_job(self, job_id: str) -> dict:
    """
    Main job orchestrator. Runs all pipeline stages in sequence.
    
    Args:
        job_id: UUID of the job to process
        
    Returns:
        dict with 'status', 'warnings', 'artifacts'
    """
```

**Flow:**

```python
def run_semantic_job(self, job_id: str) -> dict:
    job = get_job(job_id)
    warnings = []
    
    try:
        # Stage 1: Acquire sources
        update_job_status(job_id, 'acquiring_sources')
        source_results = []
        for source in job.sources:
            result = acquire_source(job_id, source.source_id)
            source_results.append(result)
            if result.get('warning'):
                warnings.append(result['warning'])
        
        # Check: At least 1 source acquired
        acquired = [r for r in source_results if r['status'] == 'acquired']
        if len(acquired) == 0:
            return fail_job(job_id, 'All sources failed acquisition')
        
        # Stage 2: Extract sources
        update_job_status(job_id, 'extracting')
        extraction_results = []
        for source in acquired:
            result = extract_source(job_id, source['source_id'])
            extraction_results.append(result)
            if result.get('warning'):
                warnings.append(result['warning'])
        
        # Check: At least 1 extraction succeeded
        extracted = [r for r in extraction_results if r['status'] == 'extracted']
        if len(extracted) == 0:
            return fail_job(job_id, 'All extractions failed')
        
        # Stage 3: Validate extractions
        update_job_status(job_id, 'validating')
        for extraction in extracted:
            result = validate_extraction(job_id, extraction['source_id'])
            if result.get('warnings'):
                warnings.extend(result['warnings'])
        
        # Stage 4: Synthesis (skip if single source)
        if len(extracted) > 1:
            update_job_status(job_id, 'synthesizing')
            synthesis_result = run_synthesis(job_id)
            if synthesis_result.get('warning'):
                warnings.append(synthesis_result['warning'])
        
        # Stage 5: Assemble documents
        update_job_status(job_id, 'assembling')
        artifacts = assemble_documents(job_id)
        
        # Complete job
        final_status = 'completed' if len(warnings) == 0 else 'completed_with_warnings'
        complete_job(job_id, final_status, warnings, artifacts)
        
        return {
            'status': final_status,
            'warnings': warnings,
            'artifacts': list(artifacts.keys())
        }
        
    except Exception as e:
        logger.exception(f"Job {job_id} failed with exception")
        return fail_job(job_id, str(e))
```

---

## 4. Source Acquisition Tasks

### 4.1 `acquire_source`

**Purpose:** Fetches metadata and transcript for a single source.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    soft_time_limit=120,
    hard_time_limit=150,
)
def acquire_source(self, job_id: str, source_id: str) -> dict:
    """
    Acquires metadata and transcript for a source.
    
    Returns:
        {
            'source_id': str,
            'status': 'acquired' | 'failed',
            'analysis_mode': str,
            'confidence_ceiling': str,
            'warning': Optional[dict]
        }
    """
```

**Implementation:**

```python
def acquire_source(self, job_id: str, source_id: str) -> dict:
    source = get_source(job_id, source_id)
    
    try:
        # Step 1: Fetch metadata
        if source.type == 'youtube':
            metadata = supadata_client.get_video_metadata(source.url)
        elif source.type == 'article':
            metadata = fetch_article_metadata(source.url)
        else:
            metadata = {'title': 'User-provided content'}
        
        update_source_metadata(job_id, source_id, metadata)
        
        # Step 2: Acquire transcript (D1 chain)
        transcript_result = acquire_transcript(source)
        
        update_source_provenance(
            job_id, 
            source_id,
            transcript_source=transcript_result['source'],
            analysis_mode=transcript_result['mode'],
            confidence_ceiling=transcript_result['ceiling'],
            transcript_text=transcript_result.get('text')
        )
        
        warning = None
        if transcript_result['mode'] == 'video_only':
            warning = {
                'code': 'transcript_unavailable',
                'stage': 'acquiring_sources',
                'source_id': source_id,
                'message': f'No transcript available for {source_id}, using video_only mode'
            }
        
        return {
            'source_id': source_id,
            'status': 'acquired',
            'analysis_mode': transcript_result['mode'],
            'confidence_ceiling': transcript_result['ceiling'],
            'warning': warning
        }
        
    except SupadataError as e:
        # Retry on transient errors
        if e.is_transient:
            raise self.retry(exc=e)
        # Permanent failure
        return {
            'source_id': source_id,
            'status': 'failed',
            'warning': {
                'code': 'source_metadata_failed',
                'stage': 'acquiring_sources',
                'source_id': source_id,
                'message': str(e)
            }
        }
```

### 4.2 `acquire_transcript` (Helper)

**Purpose:** Implements D1 fallback chain for transcript acquisition.

```python
def acquire_transcript(source: Source) -> dict:
    """
    D1 Fallback Chain:
    1. Supadata → transcript_grounded
    2. Whisper → transcript_grounded
    3. YouTube captions → caption_grounded
    4. None → video_only
    """
    
    if source.type != 'youtube':
        # Non-YouTube sources
        if source.type == 'article':
            return {
                'source': 'article_fetch',
                'mode': 'article_fetched',
                'ceiling': 'high',
                'text': fetch_article_text(source.url)
            }
        elif source.type == 'text':
            return {
                'source': 'user_provided',
                'mode': 'text_provided',
                'ceiling': 'medium',
                'text': source.content
            }
        elif source.type == 'screenshot':
            return {
                'source': 'ocr',
                'mode': 'ocr_extracted',
                'ceiling': 'medium',
                'text': run_ocr(source.image_base64)
            }
    
    # YouTube: D1 fallback chain
    video_id = extract_video_id(source.url)
    
    # Try 1: Supadata
    try:
        transcript = supadata_client.get_transcript(video_id)
        if transcript:
            return {
                'source': 'supadata',
                'mode': 'transcript_grounded',
                'ceiling': 'high',
                'text': transcript
            }
    except Exception as e:
        logger.warning(f"Supadata failed for {video_id}: {e}")
    
    # Try 2: Whisper
    try:
        transcript = whisper_client.transcribe(source.url)
        if transcript:
            return {
                'source': 'whisper',
                'mode': 'transcript_grounded',
                'ceiling': 'high',
                'text': transcript
            }
    except Exception as e:
        logger.warning(f"Whisper failed for {video_id}: {e}")
    
    # Try 3: YouTube captions
    try:
        captions = youtube_client.get_captions(video_id)
        if captions:
            return {
                'source': 'youtube_captions',
                'mode': 'caption_grounded',
                'ceiling': 'medium',
                'text': captions
            }
    except Exception as e:
        logger.warning(f"YouTube captions failed for {video_id}: {e}")
    
    # Fallback: video_only
    return {
        'source': 'none',
        'mode': 'video_only',
        'ceiling': 'low',
        'text': None
    }
```

---

## 5. Extraction Tasks

### 5.1 `extract_source`

**Purpose:** Runs Gemini semantic extraction for a single source.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    soft_time_limit=180,
    hard_time_limit=210,
)
def extract_source(self, job_id: str, source_id: str) -> dict:
    """
    Runs semantic extraction for a source.
    
    Returns:
        {
            'source_id': str,
            'status': 'extracted' | 'failed',
            'key_points_count': int,
            'warning': Optional[dict]
        }
    """
```

**Implementation:**

```python
def extract_source(self, job_id: str, source_id: str) -> dict:
    source = get_source(job_id, source_id)
    provenance = get_source_provenance(job_id, source_id)
    
    try:
        # Build mode-specific prompt
        prompt = build_extraction_prompt(
            source=source,
            provenance=provenance,
            mode=provenance.analysis_mode
        )
        
        # Call Gemini
        response = gemini_client.generate_json(
            prompt=prompt,
            temperature=0.1,
            max_tokens=8000
        )
        
        if response.get('error'):
            raise ExtractionError(response['error'])
        
        extraction = response['data']
        
        # Store extraction result
        store_extraction(job_id, source_id, extraction)
        
        return {
            'source_id': source_id,
            'status': 'extracted',
            'key_points_count': len(extraction.get('key_points', [])),
            'claims_count': len(extraction.get('claims', [])),
            'warning': None
        }
        
    except GeminiRateLimitError as e:
        # Retry on rate limit
        raise self.retry(exc=e, countdown=30)
        
    except GeminiError as e:
        # Retry once on other Gemini errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # Give up after retry
        return {
            'source_id': source_id,
            'status': 'failed',
            'warning': {
                'code': 'extraction_failed',
                'stage': 'extracting',
                'source_id': source_id,
                'message': f'Extraction failed after retry: {e}'
            }
        }
```

---

## 6. Validation Tasks

### 6.1 `validate_extraction`

**Purpose:** Runs validation checks V1-V9 on an extraction.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=0,  # Validation doesn't retry
    soft_time_limit=30,
    hard_time_limit=60,
)
def validate_extraction(self, job_id: str, source_id: str) -> dict:
    """
    Validates extraction result against V1-V9 checks.
    
    Returns:
        {
            'source_id': str,
            'status': 'validated' | 'degraded',
            'checks_passed': List[str],
            'checks_failed': List[str],
            'warnings': List[dict],
            'modifications': List[str]
        }
    """
```

**Implementation:**

```python
def validate_extraction(self, job_id: str, source_id: str) -> dict:
    extraction = get_extraction(job_id, source_id)
    provenance = get_source_provenance(job_id, source_id)
    
    checks_passed = []
    checks_failed = []
    warnings = []
    modifications = []
    
    # V1: JSON Schema
    v1_result = validate_schema(extraction)
    if v1_result['passed']:
        checks_passed.append('V1')
    else:
        checks_failed.append('V1')
        warnings.append({
            'code': 'validation_schema_failed',
            'stage': 'validating',
            'source_id': source_id,
            'message': v1_result['message']
        })
    
    # V2: Source ID Consistency
    v2_result = validate_source_id_consistency(extraction, source_id)
    if v2_result['passed']:
        checks_passed.append('V2')
    else:
        checks_failed.append('V2')
        # Auto-fix: correct source_ids
        extraction = fix_source_ids(extraction, source_id)
        modifications.append('source_ids_corrected')
    
    # V3: Confidence Ceiling
    v3_result = validate_confidence_ceiling(extraction, provenance.confidence_ceiling)
    if v3_result['passed']:
        checks_passed.append('V3')
    else:
        checks_failed.append('V3')
        # Auto-fix: clamp confidence values
        extraction = clamp_confidence(extraction, provenance.confidence_ceiling)
        modifications.append('confidence_clamped')
        warnings.append({
            'code': 'confidence_clamped',
            'stage': 'validating',
            'source_id': source_id,
            'message': f'Confidence values clamped to ceiling ({provenance.confidence_ceiling})'
        })
    
    # V4: Quote Verification (only for grounded modes)
    if provenance.analysis_mode in ['transcript_grounded', 'caption_grounded']:
        v4_result = verify_quotes(extraction, provenance.transcript_text)
        if v4_result['passed']:
            checks_passed.append('V4')
        else:
            checks_failed.append('V4')
            # Auto-fix: remove invalid quotes
            extraction = remove_invalid_quotes(extraction, v4_result['invalid_quotes'])
            modifications.append(f"removed_{len(v4_result['invalid_quotes'])}_invalid_quotes")
            warnings.append({
                'code': 'validation_quotes_removed',
                'stage': 'validating',
                'source_id': source_id,
                'message': f"{len(v4_result['invalid_quotes'])} quotes failed verification",
                'details': {'removed_count': len(v4_result['invalid_quotes'])}
            })
    else:
        checks_passed.append('V4')  # N/A for video_only
    
    # V5: Quote Permission Check
    v5_result = validate_quote_permission(extraction, provenance.analysis_mode)
    if v5_result['passed']:
        checks_passed.append('V5')
    else:
        checks_failed.append('V5')
        # Auto-fix: remove all quotes in video_only mode
        extraction['supporting_quotes'] = []
        modifications.append('quotes_removed_for_video_only')
    
    # V6: Timestamp Validation
    v6_result = validate_timestamps(extraction)
    if v6_result['passed']:
        checks_passed.append('V6')
    else:
        checks_failed.append('V6')
        # Auto-fix: mark timestamps as approximate
        extraction = mark_timestamps_approximate(extraction)
        modifications.append('timestamps_marked_approximate')
    
    # V7: Empty Output Check
    v7_result = check_empty_output(extraction)
    if v7_result['passed']:
        checks_passed.append('V7')
    else:
        checks_failed.append('V7')
        warnings.append({
            'code': 'extraction_thin',
            'stage': 'validating',
            'source_id': source_id,
            'message': 'Extraction produced minimal output'
        })
    
    # V8: Provenance Chain
    v8_result = validate_provenance_chain(extraction)
    if v8_result['passed']:
        checks_passed.append('V8')
    else:
        checks_failed.append('V8')
        warnings.append({
            'code': 'validation_grounding_failed',
            'stage': 'validating',
            'source_id': source_id,
            'message': 'Some key points missing source attribution'
        })
    
    # V9: Cardinality Check
    v9_result = validate_cardinality(extraction)
    if v9_result['passed']:
        checks_passed.append('V9')
    else:
        checks_failed.append('V9')
        # Just a warning, no modification
        warnings.append({
            'code': 'cardinality_below_target',
            'stage': 'validating',
            'source_id': source_id,
            'message': v9_result['message']
        })
    
    # Store validated/modified extraction
    store_validated_extraction(job_id, source_id, extraction)
    
    status = 'validated' if len(checks_failed) == 0 else 'degraded'
    
    return {
        'source_id': source_id,
        'status': status,
        'checks_passed': checks_passed,
        'checks_failed': checks_failed,
        'warnings': warnings,
        'modifications': modifications
    }
```

---

## 7. Synthesis Task

### 7.1 `run_synthesis`

**Purpose:** Performs cross-source synthesis for multi-source jobs.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    soft_time_limit=180,
    hard_time_limit=210,
)
def run_synthesis(self, job_id: str) -> dict:
    """
    Runs cross-source synthesis.
    
    Returns:
        {
            'status': 'completed' | 'failed',
            'themes_count': int,
            'tensions_count': int,
            'warning': Optional[dict]
        }
    """
```

**Implementation:**

```python
def run_synthesis(self, job_id: str) -> dict:
    extractions = get_all_extractions(job_id)
    
    if len(extractions) < 2:
        # Single source, skip synthesis
        return {
            'status': 'skipped',
            'themes_count': 0,
            'tensions_count': 0,
            'warning': None
        }
    
    try:
        # Build synthesis prompt
        prompt = build_synthesis_prompt(extractions)
        
        # Call Gemini
        response = gemini_client.generate_json(
            prompt=prompt,
            temperature=0.2,
            max_tokens=8000
        )
        
        if response.get('error'):
            raise SynthesisError(response['error'])
        
        synthesis = response['data']
        
        # Store synthesis result
        store_synthesis(job_id, synthesis)
        
        return {
            'status': 'completed',
            'themes_count': len(synthesis.get('cross_source_themes', [])),
            'tensions_count': len(synthesis.get('cross_source_tensions', [])),
            'warning': None
        }
        
    except GeminiError as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # Synthesis failed, continue without it
        return {
            'status': 'failed',
            'themes_count': 0,
            'tensions_count': 0,
            'warning': {
                'code': 'synthesis_failed',
                'stage': 'synthesizing',
                'source_id': None,
                'message': f'Cross-source synthesis failed: {e}'
            }
        }
```

---

## 8. Document Assembly Task

### 8.1 `assemble_documents`

**Purpose:** Builds Doc 0, Doc 1, and Doc 2 from extractions and synthesis.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=0,
    soft_time_limit=60,
    hard_time_limit=90,
)
def assemble_documents(self, job_id: str) -> dict:
    """
    Assembles all output documents.
    
    Returns:
        {
            'doc_0': {...},
            'doc_1': {...},
            'doc_2': {...}
        }
    """
```

**Implementation:**

```python
def assemble_documents(self, job_id: str) -> dict:
    job = get_job(job_id)
    sources = get_all_sources(job_id)
    extractions = get_all_extractions(job_id)
    synthesis = get_synthesis(job_id)  # May be None for single-source
    
    # Build Doc 0: Source Ledger
    doc_0 = build_source_ledger(sources, extractions)
    
    # Build Doc 1: Jump-Start Directions
    doc_1 = build_jump_start(extractions, synthesis)
    
    # Build Doc 2: Semantic Brief
    doc_2 = build_semantic_brief(extractions, synthesis)
    
    # Generate markdown versions
    doc_0_md = render_markdown(doc_0, 'source_ledger')
    doc_1_md = render_markdown(doc_1, 'jump_start')
    doc_2_md = render_markdown(doc_2, 'semantic_brief')
    
    # Store all documents
    artifacts = {
        'doc_0': doc_0,
        'doc_0_md': doc_0_md,
        'doc_1': doc_1,
        'doc_1_md': doc_1_md,
        'doc_2': doc_2,
        'doc_2_md': doc_2_md,
    }
    
    store_artifacts(job_id, artifacts)
    
    return artifacts
```

---

## 9. Booster Task

### 9.1 `run_booster`

**Purpose:** Runs the 4-stage Deep Research Booster pipeline.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    soft_time_limit=300,
    hard_time_limit=360,
    queue='priority',
)
def run_booster(self, job_id: str, options: dict = None) -> dict:
    """
    Runs the Deep Research Booster pipeline.
    
    Args:
        job_id: Job to run booster on
        options: {depth, focus_areas}
        
    Returns:
        {
            'status': 'completed' | 'failed',
            'new_directions': int,
            'new_queries': int,
            'warning': Optional[dict]
        }
    """
```

**Implementation:**

```python
def run_booster(self, job_id: str, options: dict = None) -> dict:
    options = options or {}
    previous_status = get_job_status(job_id)
    
    try:
        update_job_status(job_id, 'running_booster')
        
        doc_1 = get_document(job_id, 'doc_1')
        synthesis = get_synthesis(job_id)
        
        # Stage 1: Deep Gap Analysis
        stage_1 = run_booster_stage_1(doc_1, synthesis, options)
        
        # Stage 2: Research Path Generation
        stage_2 = run_booster_stage_2(stage_1, options)
        
        # Stage 3: Query Expansion
        stage_3 = run_booster_stage_3(stage_2, options)
        
        # Stage 4: Prioritization
        stage_4 = run_booster_stage_4(stage_1, stage_2, stage_3, options)
        
        # Augment Doc 1
        augmented_doc_1 = augment_doc_1_with_booster(doc_1, stage_4)
        store_document(job_id, 'doc_1', augmented_doc_1)
        
        # Store booster result
        store_booster_result(job_id, {
            'stage_1': stage_1,
            'stage_2': stage_2,
            'stage_3': stage_3,
            'stage_4': stage_4,
        })
        
        # Return to previous status
        update_job_status(job_id, previous_status)
        
        return {
            'status': 'completed',
            'new_directions': len(stage_2.get('research_paths', [])),
            'new_queries': len(stage_3.get('expanded_queries', [])),
            'warning': None
        }
        
    except Exception as e:
        logger.exception(f"Booster failed for job {job_id}")
        update_job_status(job_id, previous_status)
        
        return {
            'status': 'failed',
            'new_directions': 0,
            'new_queries': 0,
            'warning': {
                'code': 'booster_failed',
                'stage': 'running_booster',
                'source_id': None,
                'message': str(e)
            }
        }
```

---

## 10. Producer Task

### 10.1 `run_producer`

**Purpose:** Runs the 4-stage Producer Packet pipeline (Doc 3).

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    soft_time_limit=300,
    hard_time_limit=360,
    queue='priority',
)
def run_producer(self, job_id: str, options: dict = None) -> dict:
    """
    Runs the Producer Packet pipeline.
    
    Args:
        job_id: Job to run producer on
        options: {content_type, tone, include_risk_assessment}
        
    Returns:
        {
            'status': 'completed' | 'failed' | 'gating_failed',
            'angles_count': int,
            'structures_count': int,
            'warning': Optional[dict]
        }
    """
```

**Implementation:**

```python
def run_producer(self, job_id: str, options: dict = None) -> dict:
    options = options or {}
    previous_status = get_job_status(job_id)
    
    # V10: Gating check
    gating = check_producer_gating(job_id)
    if not gating['eligible']:
        return {
            'status': 'gating_failed',
            'angles_count': 0,
            'structures_count': 0,
            'warning': {
                'code': 'producer_gating_failed',
                'stage': 'running_producer',
                'source_id': None,
                'message': gating['message']
            }
        }
    
    try:
        update_job_status(job_id, 'running_producer')
        
        doc_0 = get_document(job_id, 'doc_0')
        doc_1 = get_document(job_id, 'doc_1')
        doc_2 = get_document(job_id, 'doc_2')
        
        # Stage 1: Story Core Extraction
        stage_1 = run_producer_stage_1(doc_0, doc_1, doc_2, options)
        
        # Stage 2: Structure Generation
        stage_2 = run_producer_stage_2(stage_1, options)
        
        # Stage 3: Creative Elements
        stage_3 = run_producer_stage_3(stage_1, stage_2, options)
        
        # Stage 4: Risk Assessment
        stage_4 = run_producer_stage_4(stage_1, stage_2, stage_3, options)
        
        # Assemble Doc 3
        doc_3 = assemble_producer_packet(stage_1, stage_2, stage_3, stage_4)
        doc_3_md = render_markdown(doc_3, 'producer_packet')
        
        store_document(job_id, 'doc_3', doc_3)
        store_document(job_id, 'doc_3_md', doc_3_md)
        
        # Return to previous status
        update_job_status(job_id, previous_status)
        
        return {
            'status': 'completed',
            'angles_count': len(stage_1.get('angles', [])),
            'structures_count': len(stage_2.get('structures', [])),
            'warning': None
        }
        
    except Exception as e:
        logger.exception(f"Producer failed for job {job_id}")
        update_job_status(job_id, previous_status)
        
        return {
            'status': 'failed',
            'angles_count': 0,
            'structures_count': 0,
            'warning': {
                'code': 'producer_failed',
                'stage': 'running_producer',
                'source_id': None,
                'message': str(e)
            }
        }
```

---

## 11. Evolving Jobs Task

### 11.1 `add_source_to_job`

**Purpose:** Adds a new source to a completed job and re-runs pipeline.

**Signature:**

```python
@celery.task(
    bind=True,
    max_retries=0,
    soft_time_limit=600,
    hard_time_limit=660,
)
def add_source_to_job(self, job_id: str, source_data: dict) -> dict:
    """
    Adds a source to existing job and re-processes.
    
    Args:
        job_id: Existing completed job
        source_data: {type, url/content}
        
    Returns:
        {
            'status': str,
            'new_source_id': str,
            'warnings': List[dict]
        }
    """
```

**Implementation:**

```python
def add_source_to_job(self, job_id: str, source_data: dict) -> dict:
    job = get_job(job_id)
    
    # Assign new source_id
    existing_count = len(job.sources)
    new_source_id = f"SRC_{existing_count + 1}"
    
    # Add source to job
    new_source = create_source(job_id, new_source_id, source_data)
    
    warnings = []
    
    try:
        # Stage 1: Acquire new source
        update_job_status(job_id, 'acquiring_sources')
        acquire_result = acquire_source(job_id, new_source_id)
        if acquire_result.get('warning'):
            warnings.append(acquire_result['warning'])
        
        if acquire_result['status'] == 'failed':
            return {
                'status': 'source_failed',
                'new_source_id': new_source_id,
                'warnings': warnings
            }
        
        # Stage 2: Extract new source
        update_job_status(job_id, 'extracting')
        extract_result = extract_source(job_id, new_source_id)
        if extract_result.get('warning'):
            warnings.append(extract_result['warning'])
        
        if extract_result['status'] == 'failed':
            return {
                'status': 'extraction_failed',
                'new_source_id': new_source_id,
                'warnings': warnings
            }
        
        # Stage 3: Validate new extraction
        update_job_status(job_id, 'validating')
        validate_result = validate_extraction(job_id, new_source_id)
        if validate_result.get('warnings'):
            warnings.extend(validate_result['warnings'])
        
        # Stage 4: Re-run synthesis with all sources
        update_job_status(job_id, 'synthesizing')
        synthesis_result = run_synthesis(job_id)
        if synthesis_result.get('warning'):
            warnings.append(synthesis_result['warning'])
        
        # Stage 5: Regenerate documents
        update_job_status(job_id, 'assembling')
        assemble_documents(job_id)
        
        # Complete
        final_status = 'completed' if len(warnings) == 0 else 'completed_with_warnings'
        update_job_status(job_id, final_status)
        
        # Add job-level warnings
        add_warnings_to_job(job_id, warnings)
        
        return {
            'status': final_status,
            'new_source_id': new_source_id,
            'warnings': warnings
        }
        
    except Exception as e:
        logger.exception(f"Add source failed for job {job_id}")
        # Restore to completed state (with additional warning)
        update_job_status(job_id, 'completed_with_warnings')
        return {
            'status': 'failed',
            'new_source_id': new_source_id,
            'warnings': warnings + [{
                'code': 'add_source_failed',
                'stage': 'add_source',
                'source_id': new_source_id,
                'message': str(e)
            }]
        }
```

---

## 12. Task Configuration Summary

| Task | Queue | Max Retries | Soft Limit | Hard Limit |
|------|-------|-------------|------------|------------|
| `run_semantic_job` | default | 0 | 600s | 660s |
| `acquire_source` | default | 2 | 120s | 150s |
| `extract_source` | default | 1 | 180s | 210s |
| `validate_extraction` | default | 0 | 30s | 60s |
| `run_synthesis` | default | 1 | 180s | 210s |
| `assemble_documents` | default | 0 | 60s | 90s |
| `run_booster` | priority | 1 | 300s | 360s |
| `run_producer` | priority | 1 | 300s | 360s |
| `add_source_to_job` | default | 0 | 600s | 660s |

---

## 13. Error Handling Summary

| Error Type | Behavior | Retry? |
|------------|----------|--------|
| Supadata transient | Retry task | Yes (2x) |
| Supadata permanent | Mark source failed, continue | No |
| Gemini rate limit | Retry with backoff | Yes |
| Gemini error | Retry once | Yes (1x) |
| Validation failure | Degrade + warning | No |
| Synthesis failure | Skip synthesis, continue | No |
| Assembly failure | Fail job | No |
| Booster failure | Return to completed + warning | No |
| Producer failure | Return to completed + warning | No |

---

## 14. Celery Configuration

```python
# celery_config.py

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERY_TIMEZONE = 'UTC'

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 660  # Global hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 600  # Global soft limit

CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevent task hoarding
CELERY_WORKER_CONCURRENCY = 2  # Conservative for LLM calls

CELERY_TASK_ACKS_LATE = True  # Requeue on worker crash
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'priority': {
        'exchange': 'priority',
        'routing_key': 'priority',
    },
}

CELERY_TASK_DEFAULT_QUEUE = 'default'
```

---

**END OF SPECIFICATION**
