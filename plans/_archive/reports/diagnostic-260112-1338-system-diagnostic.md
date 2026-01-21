# DIAGNOSTIC REPORT - Research Agent System
**Generated:** 2026-01-12 13:38
**Branch:** feature/vision-alignment-v1

---

## SECTION 1: FILE TREE

### Backend Python Files (find backend -name "*.py" | head -100)

```
backend/worker.py
backend/pipeline/transcript_acquisition.py
backend/pipeline/dual_output.py
backend/pipeline/search_router.py
backend/pipeline/timeline.py
backend/pipeline/cost_tracker.py
backend/pipeline/formats/json_export.py
backend/pipeline/formats/chapter_export.py
backend/pipeline/formats/social_export.py
backend/pipeline/formats/clip_export.py
backend/pipeline/formats/__init__.py
backend/pipeline/formats/export_manager.py
backend/pipeline/formats/citation_export.py
backend/pipeline/formats/brief_export.py
backend/pipeline/stages/youtube.py
backend/pipeline/stages/analysis.py
backend/pipeline/stages/discovery.py
backend/pipeline/stages/source_identity.py
backend/pipeline/stages/__init__.py
backend/pipeline/stages/document_assembly.py
backend/pipeline/stages/initialization.py
backend/pipeline/stages/web_capture.py
backend/pipeline/stages/planning.py
backend/pipeline/stages/helpers.py
backend/pipeline/stages/extraction_stages.py
backend/pipeline/stages/output.py
backend/pipeline/stages/semantic_extraction.py
backend/pipeline/validation_v2.py
backend/pipeline/content_extraction.py
backend/pipeline/__init__.py
backend/pipeline/documentary_intelligence.py
backend/pipeline/angle_discovery.py
backend/pipeline/semantic_validation.py
backend/pipeline/context.py
backend/pipeline/stage_runner.py
backend/pipeline/extraction.py
backend/pipeline/parallel_executor.py
backend/pipeline/prompts/gap_analysis_prompt.py
backend/pipeline/prompts/structure_analysis_prompt.py
backend/pipeline/prompts/semantic_extraction_prompt.py
backend/pipeline/prompts/__init__.py
backend/pipeline/prompts/research_starter_prompt.py
backend/pipeline/prompts/semantic_synthesis_prompt.py
backend/pipeline/search.py
backend/pipeline/quality_gate.py
backend/pipeline/entities.py
backend/pipeline/document_helpers.py
backend/pipeline/_stages_deprecated.py
backend/pipeline/video_export_formatter.py
backend/pipeline/niche_loader.py
backend/pipeline/validation.py
backend/migrations/run_migrations.py
backend/config.py
backend/app/rate_limiter.py
backend/app/__init__.py
backend/app/main.py
backend/app/routes/transcripts_routes.py
backend/app/routes/jobs_routes.py
backend/app/routes/settings_routes.py
backend/app/routes/slack_routes.py
backend/app/routes/admin_routes.py
backend/app/routes/__init__.py
backend/app/routes/export_routes.py
backend/auth/__init__.py
backend/auth/ban_check.py
backend/auth/admin.py
backend/auth/dependencies.py
backend/tests/test_document_helpers.py
backend/tests/conftest.py
backend/tests/test_auth.py
backend/tests/test_jobs_routes.py
backend/tests/test_error_handling.py
backend/tests/test_datetime_utils.py
backend/tests/__init__.py
backend/tests/test_state.py
backend/tests/test_validators.py
backend/tests/test_phase3_pipeline.py
backend/tests/test_pipeline_stages.py
backend/tests/test_rate_limiter.py
backend/legacy/transcripts.py
backend/legacy/__init__.py
backend/legacy/extraction.py
backend/__init__.py
backend/utils/validators.py
backend/utils/rate_limiter.py
backend/utils/cache.py
backend/utils/__init__.py
backend/utils/error_handling.py
backend/utils/llm_validation.py
backend/utils/datetime_utils.py
backend/models/user_settings.py
backend/models/job.py
backend/models/__init__.py
backend/models/transcript_job.py
backend/models/job_record.py
backend/models/claim.py
backend/models/document_outputs.py
backend/models/job_config.py
backend/models/source.py
backend/models/fixtures.py
```

### Pipeline Stages Directory (ls -la backend/pipeline/stages/)

```
total 240
-rw-r--r--@  1 maz  staff   1576 Jan 12 00:16 __init__.py
drwxr-xr-x@ 25 maz  staff    800 Jan 11 23:44 __pycache__
drwxr-xr-x@ 16 maz  staff    512 Jan 12 00:16 .
drwxr-xr-x@ 30 maz  staff    960 Jan 12 00:19 ..
-rw-r--r--@  1 maz  staff   7246 Dec 30 17:38 analysis.py
-rw-r--r--@  1 maz  staff  12638 Dec 30 02:39 discovery.py
-rw-r--r--@  1 maz  staff  15201 Jan 11 23:43 document_assembly.py
-rw-r--r--@  1 maz  staff   6807 Jan  1 21:10 extraction_stages.py
-rw-r--r--@  1 maz  staff    574 Dec 30 01:41 helpers.py
-rw-r--r--@  1 maz  staff   2628 Dec 30 01:41 initialization.py
-rw-r--r--@  1 maz  staff   4429 Jan  1 00:50 output.py
-rw-r--r--@  1 maz  staff   6582 Dec 30 22:37 planning.py
-rw-r--r--@  1 maz  staff  12105 Jan 11 23:36 semantic_extraction.py
-rw-r--r--@  1 maz  staff  15224 Jan 11 23:35 source_identity.py
-rw-r--r--@  1 maz  staff   6501 Dec 30 19:55 web_capture.py
-rw-r--r--@  1 maz  staff   4586 Dec 30 03:24 youtube.py
```

---

## SECTION 2: WORKER.PY - run_gemini_video_job

**File:** `backend/worker.py`
**Lines:** 621-877

```python
   621 @celery_app.task(
   622     name="backend.worker.run_gemini_video_job",
   623     time_limit=1800,  # 30 min hard limit
   624     soft_time_limit=1500,  # 25 min soft limit
   625 )
   626 def run_gemini_video_job(job_id: str) -> dict:
   627     """
   628     Celery task for Full Research Assistant Pipeline.
   629
   630     Phase 3 (Jan 2026) - 4-Pass Analysis:
   631     - Pass 1: Extraction (clips, quotes) → ProducerPacket
   632     - Pass 2: Structure Analysis → ContentBlueprint per video
   633     - Pass 3: Gap Analysis → Missing perspectives, unanswered questions
   634     - Pass 4: Research Starter → Actionable search queries, source suggestions
   635
   636     Features:
   637     - Per-video error handling (partial failures don't kill job)
   638     - Per-pass progress updates (frontend shows "Pass 2/4: Analyzing structure...")
   639     - Extended timeout (30 min for long videos)
   640
   641     Args:
   642         job_id: Unique identifier for the video extraction job
   643
   644     Returns:
   645         Dict with job_id, status, all pipeline outputs, and errors
   646     """
   647     from backend.integrations.gemini_client import GeminiClient
   648
   649     logger.info(f"[{job_id}] Starting Full Research Assistant Pipeline")
   650
   651     job = get_job(job_id)
   652     if not job:
   653         logger.error(f"[{job_id}] Job not found")
   654         return {"job_id": job_id, "status": "failed", "error": "Job not found"}
   655
   656     video_urls = job.config_json.get("video_urls", [])
   657     model = job.config_json.get("model", "gemini-2.5-flash")
   658     research_topic = job.config_json.get("title", "Video Research")
   659
   660     if not video_urls:
   661         logger.error(f"[{job_id}] No video URLs provided")
   662         update_job(job_id, status="failed", stage="error")
   663         return {"job_id": job_id, "status": "failed", "error": "No video URLs"}
   664
   665     total = len(video_urls)
   666     logger.info(f"[{job_id}] Processing {total} videos with {model}")
   667
   668     # Update status to running
   669     update_job(
   670         job_id,
   671         status="running",
   672         stage="pass_1_extraction",
   673         progress_percent=5,
   674     )
   675
   676     # H-007: Progress callback with error handling
   677     # H-003: Progress updated per video within each pass
   678     def progress_callback(pass_num: int, total_passes: int, status: str, detail: str):
   679         """Safe progress callback that won't crash the worker."""
   680         try:
   681             # Map progress: Pass 1 = 5-25%, Pass 2 = 25-50%, Pass 3 = 50-75%, Pass 4 = 75-95%
   682             base_progress = 5 + ((pass_num - 1) / total_passes) * 90
   683             progress = int(base_progress)
   684
   685             stage_names = {
   686                 1: "pass_1_extraction",
   687                 2: "pass_2_structure",
   688                 3: "pass_3_gaps",
   689                 4: "pass_4_research",
   690             }
   691
   692             update_job(
   693                 job_id,
   694                 stage=stage_names.get(pass_num, f"pass_{pass_num}"),
   695                 progress_percent=progress,
   696                 config_json={
   697                     **job.config_json,
   698                     "current_pass": pass_num,
   699                     "total_passes": total_passes,
   700                     "pass_status": status,
   701                     "pass_detail": detail,
   702                 },
   703             )
   704             logger.info(f"[{job_id}] Pass {pass_num}/{total_passes}: {detail}")
   705         except Exception as e:
   706             # H-007: Log but don't crash the worker
   707             logger.warning(f"[{job_id}] Progress update failed: {e}")
   708
   709     try:
   710         client = GeminiClient()
   711         result = client.run_full_analysis_pipeline(
   712             video_urls=video_urls,
   713             research_topic=research_topic,
   714             model=model,
   715             progress_callback=progress_callback,
   716         )
   717
   718         # Update job with results
   719         if result["status"] == "failed":
   720             # H-013: Include pipeline_errors in warnings for visibility
   721             all_warnings = [result.get("error", "Pipeline failed")]
   722             all_warnings.extend(result.get("pipeline_errors", []))
   723             update_job(
   724                 job_id,
   725                 status="failed",
   726                 stage="error",
   727                 warnings=all_warnings,
   728             )
   729             return {"job_id": job_id, "status": "failed", "error": result.get("error")}
   730
   731         # Generate ProducerPacket with quality gate
   732         from backend.pipeline.dual_output import create_producer_packet_from_gemini, TriageLevel
   733         from backend.models.job_record import Artifacts
   734
   735         title = job.config_json.get("title", f"Video Analysis {job_id[:8]}")
   736
   737         # Build batch result format for ProducerPacket
   738         batch_result = {
   739             "clips": result.get("clips", []),
   740             "quotes": result.get("quotes", []),
   741             "results": result.get("results", []),  # Pass through video metadata
   742             "total_cost": result.get("total_cost", 0),
   743         }
   744
   745         producer_packet = create_producer_packet_from_gemini(
   746             gemini_results=batch_result,
   747             title=title,
   748             transcripts=None,
   749         )
   750
   751         # Check quality gate and triage level
   752         passes_gate, gate_issues = producer_packet.passes_quality_gate()
   753         triage_level, triage_reasons = producer_packet.triage()
   754         warnings = []
   755
   756         if result.get("extraction_errors"):
   757             warnings.extend([e.get("error", str(e)) for e in result["extraction_errors"]])
   758
   759         # H-013: Include pipeline_errors in warnings
   760         if result.get("pipeline_errors"):
   761             warnings.extend(result["pipeline_errors"])
   762
   763         if not passes_gate:
   764             warnings.extend([f"Quality gate: {issue}" for issue in gate_issues])
   765             logger.warning(f"[{job_id}] Quality gate not passed: {gate_issues}")
   766             logger.info(f"[{job_id}] Triage level: {triage_level.value}, reasons: {triage_reasons}")
   767
   768         # M-008: Consistent dataclass serialization pattern using safe_to_dict
   769         from backend.integrations.gemini_client import safe_to_dict
   770
   771         content_blueprints_dicts = [
   772             safe_to_dict(bp) for bp in result.get("content_blueprints", [])
   773         ]
   774         gap_analysis_dict = safe_to_dict(result.get("gap_analysis"))
   775         research_starter_dict = safe_to_dict(result.get("research_starter"))
   776
   777         # Build artifacts with all pipeline outputs
   778         # Use processed clips/quotes from producer_packet (has video_url, verification_level)
   779         # NOT raw clips from result (missing required fields for frontend display)
   780         artifacts = Artifacts(
   781             clips=[c.to_dict() for c in producer_packet.clips],
   782             quotes=[q.to_dict() for q in producer_packet.quotes],
   783             producer_packet=producer_packet.to_dict(),
   784             quality_gate_passed=passes_gate,
   785             # Phase 3 additions
   786             content_blueprints=content_blueprints_dicts,
   787             gap_analysis=gap_analysis_dict,
   788             research_starter=research_starter_dict,
   789         )
   790
   791         # Determine appropriate final status based on triage and warnings
   792         final_status = "completed"
   793
   794         # Use failed_insufficient for FAILED triage (nothing usable)
   795         if triage_level == TriageLevel.FAILED:
   796             final_status = "failed_insufficient"
   797             logger.warning(f"[{job_id}] Triage FAILED - marking as failed_insufficient")
   798         elif result.get("status") == "completed_with_errors":
   799             final_status = "completed_with_warnings"  # Downgrade to partial success
   800         elif result.get("status") == "completed_with_warnings":
   801             final_status = "completed_with_warnings"
   802         elif warnings or triage_level in (TriageLevel.THIN, TriageLevel.USABLE):
   803             final_status = "completed_with_warnings"
   804
   805         # Set error message for failed_insufficient
   806         error_msg = None
   807         if final_status == "failed_insufficient":
   808             error_msg = f"Insufficient extraction: {'; '.join(triage_reasons + gate_issues)}"
   809
   810         update_job(
   811             job_id,
   812             status=final_status,
   813             stage="completed",
   814             progress_percent=100,
   815             artifacts=artifacts,
   816             warnings=warnings if warnings else None,
   817             error=error_msg,
   818         )
   819
   820         videos_processed = result.get("videos_processed", 0)
   821         videos_failed = result.get("videos_failed", 0)
   822         total_cost = result.get("total_cost", 0)
   823
   824         logger.info(
   825             f"[{job_id}] Full pipeline completed: "
   826             f"status={final_status}, "
   827             f"{videos_processed} videos, "
   828             f"{len(result.get('clips', []))} clips, "
   829             f"{len(producer_packet.quotes)} quotes, "
   830             f"{len(content_blueprints_dicts)} blueprints, "
   831             f"triage={triage_level.value}, "
   832             f"quality_gate={'PASS' if passes_gate else 'FAIL'}, "
   833             f"${total_cost:.4f}"
   834         )
   835
   836         return {
   837             "job_id": job_id,
   838             "status": final_status,
   839             "clips": len(result.get("clips", [])),
   840             "quotes": len(producer_packet.quotes),
   841             "content_blueprints": len(content_blueprints_dicts),
   842             "has_gap_analysis": gap_analysis_dict is not None,
   843             "has_research_starter": research_starter_dict is not None,
   844             "videos_processed": videos_processed,
   845             "videos_failed": videos_failed,
   846             "total_cost": total_cost,
   847             "quality_gate_passed": passes_gate,
   848             "triage_level": triage_level.value,
   849         }
   850
   851     except SoftTimeLimitExceeded:
   852         # C-005: Handle Celery soft timeout (25 min) gracefully
   853         logger.error(f"[{job_id}] Pipeline timed out after 25 minutes")
   854         update_job(
   855             job_id,
   856             status="failed",
   857             stage="timeout",
   858             error="Pipeline timed out. Try processing fewer videos or shorter videos.",
   859             warnings=["Task exceeded 25 minute time limit"],
   860         )
   861         return {
   862             "job_id": job_id,
   863             "status": "failed",
   864             "error": "Pipeline timed out after 25 minutes",
   865         }
   866
   867     except Exception as e:
   868         logger.exception(f"[{job_id}] Full pipeline failed: {e}")
   869         update_job(
   870             job_id,
   871             status="failed",
   872             stage="error",
   873             error=str(e),
   874             warnings=[f"Pipeline failed: {str(e)}"],
   875         )
   876         return {"job_id": job_id, "status": "failed", "error": str(e)}
```

**Current Call Order:**
1. `GeminiClient()` instantiation
2. `client.run_full_analysis_pipeline()` - contains:
   - Pass 1: `analyze_youtube_videos_batch()` - clips/quotes extraction
   - Pass 2: `analyze_video_structure()` - ContentBlueprint per video
   - Pass 3: `analyze_gaps()` - GapAnalysis
   - Pass 4: `generate_research_starter()` - ResearchStarter
3. `create_producer_packet_from_gemini()` - produces ProducerPacket
4. Quality gate & triage checks
5. `Artifacts` creation and `update_job()`

**CRITICAL OBSERVATION:**
- `run_gemini_video_job` does NOT call `stage_source_identity`, `stage_semantic_extraction`, or `stage_document_assembly`
- These are new pipeline stages that exist in files but are **NOT INTEGRATED** into the worker

---

## SECTION 3: PIPELINE CONTEXT

**File:** `backend/pipeline/context.py`
**Lines:** 1-103

```python
     1 """Pipeline context for research job execution."""
     2 from dataclasses import dataclass, field
     3 from typing import Optional, TYPE_CHECKING
     4
     5 from backend.models.job_config import JobConfig
     6
     7 if TYPE_CHECKING:
     8     from backend.pipeline.cost_tracker import CostTracker
     9
    10
    11 @dataclass
    12 class PipelineContext:
    13     """
    14     Shared context passed through all pipeline stages.
    15
    16     Holds all intermediate results and accumulates outputs/warnings.
    17     """
    18     # Input
    19     job_id: str
    20     topic: str
    21     slack_payload: Optional[dict] = None
    22
    23     # Configuration (set in Stage 1)
    24     job_config: Optional[JobConfig] = None
    25     short_title: str = ""
    26
    27     # Disambiguation (set when processing multiple interpretations)
    28     interpretation_index: Optional[int] = None  # 1-based index (1, 2, 3...)
    29     interpretation_label: Optional[str] = None  # Short label like "Barney & Friends"
    30
    31     # Cost tracking (initialized in Stage 0)
    32     cost_tracker: Optional["CostTracker"] = None
    33
    34     # Niche configuration (set in Stage 1 if niche specified)
    35     # Default to empty dict to prevent NoneType errors in downstream stages
    36     niche_config: dict = field(default_factory=dict)
    37
    38     # Stage 2: Research mapping
    39     angles: list = field(default_factory=list)
    40     key_terms: list = field(default_factory=list)
    41
    42     # Stage 3: Source shortlist
    43     web_sources: list = field(default_factory=list)
    44
    45     # Stage 4: YouTube
    46     youtube_videos: list = field(default_factory=list)
    47
    48     # Stage 5: Transcripts
    49     transcripts: list = field(default_factory=list)
    50
    51     # Stage 6.5: Reddit
    52     reddit_posts: list = field(default_factory=list)
    53
    54     # Stage 7: Claims
    55     claims: list = field(default_factory=list)
    56
    57     # Stage 7.5: Timeline
    58     timeline_events: list = field(default_factory=list)
    59
    60     # Stage 7.6: Entities
    61     entities: dict = field(default_factory=dict)
    62
    63     # Stage 8: Validation
    64     evidence_records: list = field(default_factory=list)
    65
    66     # Stage 8.5: Angle discovery
    67     discovered_angles: dict = field(default_factory=dict)
    68
    69     # Stage 8.6: Documentary analysis
    70     documentary_analysis: dict = field(default_factory=dict)
    71
    72     # Stage 9: Drive
    73     folder_url: Optional[str] = None
    74     doc_urls: dict = field(default_factory=dict)
    75
    76     # Quality Gate stats (set after Stage 3)
    77     quality_gate_stats: Optional[dict] = None
    78
    79     # Accumulated outputs (markdown documents)
    80     outputs: dict = field(default_factory=dict)
    81
    82     # Accumulated warnings
    83     warnings: list = field(default_factory=list)
    84
    85     def add_warning(self, warning: str) -> None:
    86         """Add a warning message."""
    87         self.warnings.append(warning)
    88
    89     def set_output(self, key: str, value: str) -> None:
    90         """Set an output markdown document."""
    91         self.outputs[key] = value
    92
    93     def add_cost(self, api_name: str, amount: float, units: int = 1) -> None:
    94         """Track cost for an API call."""
    95         if self.cost_tracker:
    96             self.cost_tracker.add_cost(api_name, amount, units)
    97
    98     def get_cost_summary(self) -> dict:
    99         """Get cost tracking summary."""
   100         if self.cost_tracker:
   101             return self.cost_tracker.get_summary()
   102         return {}
```

**MISSING FIELDS for Semantic Pipeline:**
- `source_identity_packages: list` - NOT PRESENT
- `semantic_extractions: list` - NOT PRESENT
- `semantic_extraction_results: list` - NOT PRESENT
- `source_ledger: dict` - NOT PRESENT
- `jump_start: dict` - NOT PRESENT
- `semantic_brief: dict` - NOT PRESENT
- `identified_gaps: list` - NOT PRESENT
- `scope_in: list` - NOT PRESENT
- `scope_out: list` - NOT PRESENT

---

## SECTION 4: ARTIFACTS MODEL

**File:** `backend/models/job_record.py`
**Lines:** 8-32

```python
     8 class Artifacts(BaseModel):
     9     """Artifacts associated with a job (Drive folder, docs, etc.)."""
    10     drive_folder_url: Optional[str] = Field(None, description="Google Drive folder URL")
    11     doc_urls: Optional[list[str]] = Field(None, description="List of Google Doc URLs")
    12
    13     # Video analysis artifacts (Gemini pivot)
    14     clips: Optional[list[dict[str, Any]]] = Field(None, description="Extracted video clips")
    15     quotes: Optional[list[dict[str, Any]]] = Field(None, description="Extracted quotes with timestamps")
    16     producer_packet: Optional[dict[str, Any]] = Field(None, description="Full ProducerPacket for video production")
    17     quality_gate_passed: Optional[bool] = Field(None, description="Whether ProducerPacket passed quality gate")
    18
    19     # Phase 3: Full Research Assistant Pipeline (Jan 2026)
    20     # Pass 2: Content Blueprints - structure analysis per video
    21     content_blueprints: Optional[list[dict[str, Any]]] = Field(
    22         None, description="ContentBlueprint per video (hook, structure, open loops, sources)"
    23     )
    24     # Pass 3: Gap Analysis - cross-video gaps
    25     gap_analysis: Optional[dict[str, Any]] = Field(
    26         None, description="GapAnalysis (missing perspectives, unanswered questions, contradictions)"
    27     )
    28     # Pass 4: Research Starter - actionable next steps
    29     research_starter: Optional[dict[str, Any]] = Field(
    30         None, description="ResearchStarter (search queries, source suggestions, content angles)"
    31     )
```

**CURRENT FIELDS:**
```
['drive_folder_url', 'doc_urls', 'clips', 'quotes', 'producer_packet',
 'quality_gate_passed', 'content_blueprints', 'gap_analysis', 'research_starter']
```

**MISSING FIELDS for 3-Document Model:**
- `source_ledger: Optional[dict]` - NOT PRESENT
- `jump_start: Optional[dict]` - NOT PRESENT
- `semantic_brief: Optional[dict]` - NOT PRESENT
- `transcript_provenance: Optional[dict]` - NOT PRESENT (per-source metadata)

---

## SECTION 5: STAGE FILES

### backend/pipeline/stages/__init__.py

**Lines:** 1-46

```python
     1 """Pipeline stages module - split for maintainability.
     2
     3 Each stage function takes a PipelineContext and modifies it in place.
     4 Import all stages from this module for backward compatibility.
     5 """
     6 from .helpers import post_slack_message
     7 from .initialization import stage_0_initialize, stage_10_completion
     8 from .planning import stage_1_planning, stage_2_research_mapping
     9 from .discovery import stage_3_source_shortlist, stage_3_5_quality_gate
    10 from .youtube import stage_4_youtube_enumeration, stage_5_transcripts
    11 from .web_capture import stage_6_web_capture, stage_6_5_reddit
    12 from .extraction_stages import stage_7_extraction, stage_7_5_timeline, stage_7_6_entities
    13 from .analysis import stage_8_validation, stage_8_5_angle_discovery, stage_8_6_documentary_intelligence
    14 from .output import stage_9_drive_upload
    15
    16 __all__ = [
    17     # Helpers
    18     "post_slack_message",
    19     # Stage 0: Initialization
    20     "stage_0_initialize",
    21     # Stage 1-2: Planning
    22     "stage_1_planning",
    23     "stage_2_research_mapping",
    24     # Stage 3: Discovery
    25     "stage_3_source_shortlist",
    26     "stage_3_5_quality_gate",
    27     # Stage 4-5: YouTube
    28     "stage_4_youtube_enumeration",
    29     "stage_5_transcripts",
    30     # Stage 6: Web
    31     "stage_6_web_capture",
    32     "stage_6_5_reddit",
    33     # Stage 7: Extraction
    34     "stage_7_extraction",
    35     "stage_7_5_timeline",
    36     "stage_7_6_entities",
    37     # Stage 8: Analysis
    38     "stage_8_validation",
    39     "stage_8_5_angle_discovery",
    40     "stage_8_6_documentary_intelligence",
    41     # Stage 9: Output
    42     "stage_9_drive_upload",
    43     # Stage 10: Completion
    44     "stage_10_completion",
    45 ]
```

**CRITICAL: MISSING EXPORTS:**
- `stage_source_identity` - EXISTS in source_identity.py but NOT EXPORTED
- `stage_semantic_extraction` - EXISTS in semantic_extraction.py but NOT EXPORTED
- `stage_document_assembly` - EXISTS in document_assembly.py but NOT EXPORTED


### backend/pipeline/stages/source_identity.py

**Lines:** 1-429 (COMPLETE FILE)**

```python
"""
Source Identity Builder Stage - Pre-LLM deterministic identity resolution.

This stage runs BEFORE any LLM call to ensure Gemini receives:
- Resolved source_id (SRC_1, SRC_2, etc.)
- Determined transcript_source and analysis_mode
- Built TranscriptProvenance metadata
- Validated source accessibility

Based on: docs/authoritative/spec/RASS.md Section 4.2
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel
from backend.models.document_outputs import TranscriptProvenance
from backend.pipeline.context import PipelineContext
from backend.pipeline.transcript_acquisition import (
    TranscriptResult,
    acquire_transcript,
    is_transcript_available,
)
from backend.state import update_job


@dataclass
class SourceIdentityPackage:
    """
    Deterministic identity resolved BEFORE any LLM sees the data.

    This package contains everything needed for semantic extraction
    without requiring the LLM to guess or infer source identity.
    """
    # Stable identifiers
    source_id: str  # SRC_1, SRC_2, etc.
    source_type: str  # "youtube", "article", "reddit"

    # Canonical metadata
    url: str
    title: str
    creator: Optional[str] = None
    published: Optional[str] = None
    duration_seconds: Optional[int] = None

    # Transcript provenance (REQUIRED for video sources)
    transcript_source: Optional[str] = None  # "supadata", "whisper", "youtube_captions", "none"
    analysis_mode: AnalysisMode = AnalysisMode.VIDEO_ONLY

    # Content (resolved BEFORE LLM)
    content: Optional[str] = None  # Transcript text or web content
    content_word_count: Optional[int] = None

    # Validation status
    is_accessible: bool = True
    failure_reason: Optional[str] = None

    # Provenance metadata (full object)
    provenance: Optional[TranscriptProvenance] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "url": self.url,
            "title": self.title,
            "creator": self.creator,
            "published": self.published,
            "duration_seconds": self.duration_seconds,
            "transcript_source": self.transcript_source,
            "analysis_mode": self.analysis_mode.value,
            "content_word_count": self.content_word_count,
            "is_accessible": self.is_accessible,
            "failure_reason": self.failure_reason,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @property
    def confidence_ceiling(self) -> ConfidenceLevel:
        """Return max allowed confidence based on analysis mode."""
        ceilings = {
            AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
            AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
            AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
        }
        return ceilings.get(self.analysis_mode, ConfidenceLevel.LOW)


def build_source_identity_from_video(
    video_data: dict,
    source_index: int,
) -> SourceIdentityPackage:
    # ... (implementation lines 92-181)
    pass


def build_source_identity_from_article(
    article_data: dict,
    source_index: int,
) -> SourceIdentityPackage:
    # ... (implementation lines 184-241)
    pass


def build_source_identity_from_reddit(
    post_data: dict,
    source_index: int,
) -> SourceIdentityPackage:
    # ... (implementation lines 244-306)
    pass


def stage_source_identity(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Build source identity packages BEFORE any LLM call.

    This stage:
    1. Collects all sources from previous stages (videos, articles, reddit)
    2. Acquires transcripts for video sources
    3. Assigns stable source_id (SRC_1, SRC_2, ...)
    4. Builds TranscriptProvenance metadata
    5. Stores packages in ctx.source_identity_packages

    The output ctx.source_identity_packages is consumed by semantic_extraction.
    """
    logger.info(f"[{ctx.job_id}] Stage: Source Identity Builder")

    update_job(
        ctx.job_id,
        stage="source_identity",
        progress_percent=30,
    )

    packages: list[SourceIdentityPackage] = []
    source_index = 0

    # Process YouTube videos
    for video in ctx.youtube_videos:
        # ... processing logic

    # Process web articles
    for article in ctx.web_sources:
        # ... processing logic

    # Process Reddit posts
    for post in ctx.reddit_posts:
        # ... processing logic

    # Store packages in context for downstream stages
    ctx.source_identity_packages = packages  # <-- REQUIRES PipelineContext UPDATE
```

**NOTE:** This stage writes to `ctx.source_identity_packages` which does NOT exist in PipelineContext.


### backend/pipeline/stages/semantic_extraction.py

**Lines:** 1-338 (COMPLETE FILE - key portions shown)**

```python
"""
Semantic Extraction Stage - Extract semantic structure from sources.

This stage processes source content through Gemini to extract:
- Key Points
- Claims
- Themes
- Tensions
- Approximate Observations (for video_only mode)

IMPORTANT: This stage consumes SourceIdentityPackage from the
source_identity stage. It does NOT resolve identity itself.

Based on: docs/authoritative/spec/RASS.md Section 4.3
"""

# ... imports ...

def stage_semantic_extraction(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Extract semantic structure from all sources.

    PREREQUISITE: source_identity stage must run first to populate
    ctx.source_identity_packages with resolved identity data.
    """
    logger.info(f"[{ctx.job_id}] Stage: Semantic Extraction")

    update_job(
        ctx.job_id,
        stage="semantic_extraction",
        progress_percent=40,
    )

    # Initialize storage for extraction results
    if not hasattr(ctx, "semantic_extractions"):
        ctx.semantic_extractions = []  # <-- REQUIRES PipelineContext UPDATE

    # Get identity packages from context (populated by source_identity stage)
    packages = getattr(ctx, "source_identity_packages", [])  # <-- Dynamic attr access
```


### backend/pipeline/stages/document_assembly.py

**Lines:** 1-459 (COMPLETE FILE - key portions shown)**

```python
"""
Document Assembly Stage - Generates the 3 canonical documents.

This stage constructs:
- Doc 0: Source Ledger (Canonical Data Layer)
- Doc 1: Jump-Start (Research Direction Layer)
- Doc 2: Semantic Research Brief (80% Output)

Based on: docs/authoritative/spec/Document_Output_Format.md
"""

# ... imports and helper functions ...

def stage_document_assembly(ctx: PipelineContext) -> dict:
    """
    Pipeline stage: Assemble the 3 canonical documents.

    PREREQUISITE: source_identity and semantic_extraction stages must run first.
    """
    logger.info(f"[{ctx.job_id}] Stage: Document Assembly")

    update_job(
        ctx.job_id,
        stage="document_assembly",
        progress_percent=70,
    )

    # Get source identity packages (from source_identity stage)
    packages = getattr(ctx, "source_identity_packages", [])  # <-- Dynamic attr

    # ... build documents ...

    # Store documents in context (dict format)
    ctx.source_ledger = doc_0.to_dict()      # <-- REQUIRES PipelineContext UPDATE
    ctx.jump_start = doc_1.to_dict()         # <-- REQUIRES PipelineContext UPDATE
    ctx.semantic_brief = doc_2.to_dict()     # <-- REQUIRES PipelineContext UPDATE
```


### backend/pipeline/transcript_acquisition.py

**Lines:** 1-406 (COMPLETE FILE EXISTS)**

This file is complete and properly implements the 4-tier transcript fallback chain:
1. Supadata → `transcript_grounded`
2. Whisper → `transcript_grounded`
3. YouTube captions → `caption_grounded`
4. None → `video_only`

Key exports:
- `TranscriptResult` dataclass
- `TranscriptSource` enum
- `AcquisitionStatus` enum
- `acquire_transcript()` function
- `is_transcript_available()` function
- `get_confidence_ceiling()` function

---

## SECTION 6: GEMINI CLIENT

**File:** `backend/integrations/gemini_client.py`
**Lines:** 1-1659

### Class Definition

```python
class GeminiClient:
    """Client for Google Gemini 2.5 Flash/Pro.

    Uses the new google-genai SDK for better performance and features.

    Used for:
    - Planning with thinking mode (Flash)
    - Query generation (Flash)
    - Vision/PDF analysis (Pro)
    - Validation and synthesis (Pro)
    """

    # Cost per 1M tokens (Dec 2025 verified pricing)
    COSTS = {
        "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    }
```

### Public Methods (SYNC - Not Async)

| Method | Signature | Returns |
|--------|-----------|---------|
| `generate` | `(prompt, model, system_instruction, temperature, max_tokens)` | `dict[str, Any]` |
| `generate_with_thinking` | `(prompt, model, thinking_budget, system_instruction)` | `dict[str, Any]` |
| `analyze_image` | `(image_path, prompt, model)` | `dict[str, Any]` |
| `analyze_pdf` | `(pdf_path, prompt, model)` | `dict[str, Any]` |
| `analyze_youtube_video` | `(video_url, model, max_clips)` | `dict[str, Any]` |
| `analyze_youtube_video_chunked` | `(video_url, duration_seconds, model, chunk_duration_seconds)` | `dict[str, Any]` |
| `analyze_youtube_videos_batch` | `(video_urls, model, progress_callback)` | `dict[str, Any]` |
| `analyze_video_structure` | `(video_url, video_title, model)` | `tuple[ContentBlueprint, float, Optional[str]]` |
| `analyze_gaps` | `(clips_summary, quotes_summary, videos_list, num_videos, model)` | `tuple[GapAnalysis, float, Optional[str]]` |
| `generate_research_starter` | `(gap_analysis, research_topic, num_videos, model)` | `tuple[ResearchStarter, float, Optional[str]]` |
| `run_full_analysis_pipeline` | `(video_urls, research_topic, model, progress_callback)` | `dict[str, Any]` |

**CRITICAL: NO `generate_json` method exists.**

The `semantic_extraction.py` stage calls:
```python
response = await gemini_client.generate_json(
    prompt=prompt,
    system_message=SEMANTIC_EXTRACTION_ROLE,
)
```

But `GeminiClient` does NOT have a `generate_json()` method. This will fail.

---

## SECTION 7: SEMANTIC MODELS

### backend/models/semantic_units.py

**Lines:** 1-405 (COMPLETE FILE EXISTS)**

Key definitions:
- `ConfidenceLevel` enum: `HIGH`, `MEDIUM`, `LOW`
- `AnalysisMode` enum: `TRANSCRIPT_GROUNDED`, `CAPTION_GROUNDED`, `VIDEO_ONLY`
- `Quote` dataclass
- `Claim` dataclass
- `KeyPoint` dataclass
- `Theme` dataclass
- `Tension` dataclass
- `Gap` dataclass
- `ApproximateObservation` dataclass
- `SpeculativeObservation` dataclass
- `SemanticExtractionResult` dataclass


### backend/models/document_outputs.py

**Lines:** 1-641 (COMPLETE FILE EXISTS)**

Key definitions:
- `SourceStatus` enum
- `TriageLevel` enum
- `TranscriptProvenance` dataclass
- `SourceEntry` dataclass
- `SourceLedger` dataclass (Doc 0)
- `ResearchDirection` dataclass
- `VerificationItem` dataclass
- `JumpStartDirections` dataclass (Doc 1)
- `ConfidenceAssessment` dataclass
- `SemanticBrief` dataclass (Doc 2)

---

## SECTION 8: CURRENT ERRORS

### Test 1: Import run_gemini_video_job
```
✓ SUCCESS - imports cleanly
```

### Test 2: Import stage_source_identity
```
✗ FAILED
ImportError: cannot import name 'stage_source_identity' from 'backend.pipeline.stages'
```

**Root Cause:** `stage_source_identity` is not in `__all__` or imports in `__init__.py`

### Test 3: Artifacts model fields
```
✓ SUCCESS
['drive_folder_url', 'doc_urls', 'clips', 'quotes', 'producer_packet',
 'quality_gate_passed', 'content_blueprints', 'gap_analysis', 'research_starter']
```

---

## SECTION 9: GIT STATUS

### Untracked Files (New)
```
?? backend/models/document_outputs.py
?? backend/models/semantic_units.py
?? backend/pipeline/prompts/semantic_extraction_prompt.py
?? backend/pipeline/prompts/semantic_synthesis_prompt.py
?? backend/pipeline/semantic_validation.py
?? backend/pipeline/stages/document_assembly.py
?? backend/pipeline/stages/semantic_extraction.py
?? backend/pipeline/stages/source_identity.py
?? backend/pipeline/transcript_acquisition.py
```

### Recent Changes (git diff --stat HEAD~5)
```
33 files changed, 6084 insertions(+), 11 deletions(-)
```

Major additions:
- Authoritative specs (RASS.md, Document_Output_Format.md, etc.)
- Semantic extraction skills
- Hook files for validation
- New pipeline stage files (untracked)

---

## SECTION 10: DECISIONS FILE

**FILE DOES NOT EXIST:** `docs/DECISIONS.md`

---

## CRITICAL FINDINGS SUMMARY

### Integration Gaps (BLOCKING)

1. **Stages Not Exported**
   - `stage_source_identity` exists but not in `__init__.py` exports
   - `stage_semantic_extraction` exists but not in `__init__.py` exports
   - `stage_document_assembly` exists but not in `__init__.py` exports

2. **PipelineContext Missing Fields**
   - `source_identity_packages: list`
   - `semantic_extractions: list`
   - `semantic_extraction_results: list`
   - `source_ledger: dict`
   - `jump_start: dict`
   - `semantic_brief: dict`
   - `identified_gaps: list`
   - `scope_in: list`
   - `scope_out: list`

3. **Missing GeminiClient Method**
   - `semantic_extraction.py` calls `gemini_client.generate_json()` which does NOT exist
   - Need to either add `generate_json()` or use existing `generate()` + JSON parsing

4. **Artifacts Model Incomplete**
   - Missing `source_ledger`, `jump_start`, `semantic_brief` fields
   - Missing `transcript_provenance` per-source metadata

5. **Worker Not Calling New Stages**
   - `run_gemini_video_job` uses `GeminiClient.run_full_analysis_pipeline()`
   - Does NOT call `stage_source_identity`, `stage_semantic_extraction`, or `stage_document_assembly`
   - The 4-pass pipeline in GeminiClient produces different output format than 3-document model

### Files Status

| File | Status | Integrated |
|------|--------|------------|
| `semantic_units.py` | Untracked | NO |
| `document_outputs.py` | Untracked | NO |
| `source_identity.py` | Untracked | NO |
| `semantic_extraction.py` | Untracked | NO |
| `document_assembly.py` | Untracked | NO |
| `transcript_acquisition.py` | Untracked | NO |
| `semantic_validation.py` | Untracked | NO |

---

## UNRESOLVED QUESTIONS

1. Should the new semantic stages REPLACE the existing 4-pass pipeline in `run_gemini_video_job`, or should they be a PARALLEL pathway?

2. Where should the 3-document model outputs (source_ledger, jump_start, semantic_brief) be stored - in Artifacts, or as separate top-level fields on JobRecord?

3. The `semantic_extraction.py` stage uses `async/await` but GeminiClient methods are SYNC. Which should be changed?

4. Should `run_research_job` (topic-based) also use the semantic pipeline stages, or only `run_gemini_video_job` (URL-based)?
