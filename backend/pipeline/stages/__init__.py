"""Pipeline stages module - split for maintainability.

Each stage function takes a PipelineContext and modifies it in place.
Import all stages from this module for backward compatibility.
"""
from .helpers import post_slack_message
from .initialization import stage_0_initialize, stage_10_completion
from .planning import stage_1_planning, stage_2_research_mapping
from .discovery import stage_3_source_shortlist, stage_3_5_quality_gate
from .youtube import stage_4_youtube_enumeration, stage_5_transcripts
from .web_capture import stage_6_web_capture, stage_6_5_reddit
from .extraction_stages import stage_7_extraction, stage_7_5_timeline, stage_7_6_entities
from .analysis import stage_8_validation, stage_8_5_angle_discovery, stage_8_6_documentary_intelligence
from .output import stage_9_drive_upload

__all__ = [
    # Helpers
    "post_slack_message",
    # Stage 0: Initialization
    "stage_0_initialize",
    # Stage 1-2: Planning
    "stage_1_planning",
    "stage_2_research_mapping",
    # Stage 3: Discovery
    "stage_3_source_shortlist",
    "stage_3_5_quality_gate",
    # Stage 4-5: YouTube
    "stage_4_youtube_enumeration",
    "stage_5_transcripts",
    # Stage 6: Web
    "stage_6_web_capture",
    "stage_6_5_reddit",
    # Stage 7: Extraction
    "stage_7_extraction",
    "stage_7_5_timeline",
    "stage_7_6_entities",
    # Stage 8: Analysis
    "stage_8_validation",
    "stage_8_5_angle_discovery",
    "stage_8_6_documentary_intelligence",
    # Stage 9: Output
    "stage_9_drive_upload",
    # Stage 10: Completion
    "stage_10_completion",
]
