/**
 * Hook for calculating dynamic ETA for job completion.
 * Uses stage-based estimation for more accurate predictions.
 */
import { useState, useEffect, useMemo } from 'react';

interface UseETAOptions {
  progress: number;
  status: string;
  stage?: string;
  stageStartedAt?: string;
  pipeline: string;
  createdAt: string;
}

interface ETAResult {
  eta: string | null;
  elapsed: string;
  stageDescription: string;
  isCalculating: boolean;
}

// Stage order for progress calculation (must match worker.py stages)
const STAGE_ORDER = [
  'initializing',
  'planning',
  'research_mapping',
  'source_discovery',
  'youtube_enumeration',
  'transcript_fetching',
  'web_capture',
  'reddit_collection',
  'claim_extraction',
  'timeline_extraction',
  'entity_extraction',
  'claim_validation',
  'angle_discovery',
  'documentary_analysis',
  'drive_upload',
];

// Stage-based duration estimates in seconds (per pipeline type)
// Stage names must match worker.py stages exactly
const STAGE_DURATIONS: Record<string, Record<string, number>> = {
  quick: {
    initializing: 5,
    planning: 15,
    research_mapping: 30,
    source_discovery: 45,
    youtube_enumeration: 20,
    transcript_fetching: 40,
    web_capture: 30,
    reddit_collection: 10,
    claim_extraction: 15,
    timeline_extraction: 10,
    entity_extraction: 10,
    claim_validation: 20,
    angle_discovery: 10,
    documentary_analysis: 10,
    drive_upload: 10,
  },
  full: {
    initializing: 5,
    planning: 20,
    research_mapping: 60,
    source_discovery: 90,
    youtube_enumeration: 40,
    transcript_fetching: 120,
    web_capture: 90,
    reddit_collection: 20,
    claim_extraction: 45,
    timeline_extraction: 20,
    entity_extraction: 20,
    claim_validation: 60,
    angle_discovery: 20,
    documentary_analysis: 20,
    drive_upload: 20,
  },
  breaking_news: {
    initializing: 5,
    planning: 10,
    research_mapping: 20,
    source_discovery: 30,
    youtube_enumeration: 15,
    transcript_fetching: 30,
    web_capture: 20,
    reddit_collection: 10,
    claim_extraction: 10,
    timeline_extraction: 5,
    entity_extraction: 5,
    claim_validation: 15,
    angle_discovery: 5,
    documentary_analysis: 10,
    drive_upload: 10,
  },
  investigation: {
    initializing: 5,
    planning: 25,
    research_mapping: 60,
    source_discovery: 90,
    youtube_enumeration: 45,
    transcript_fetching: 90,
    web_capture: 60,
    reddit_collection: 20,
    claim_extraction: 30,
    timeline_extraction: 20,
    entity_extraction: 20,
    claim_validation: 45,
    angle_discovery: 20,
    documentary_analysis: 25,
    drive_upload: 15,
  },
  profile: {
    initializing: 5,
    planning: 20,
    research_mapping: 45,
    source_discovery: 60,
    youtube_enumeration: 30,
    transcript_fetching: 60,
    web_capture: 45,
    reddit_collection: 15,
    claim_extraction: 25,
    timeline_extraction: 15,
    entity_extraction: 20,
    claim_validation: 30,
    angle_discovery: 15,
    documentary_analysis: 20,
    drive_upload: 15,
  },
  controversy: {
    initializing: 5,
    planning: 20,
    research_mapping: 50,
    source_discovery: 75,
    youtube_enumeration: 35,
    transcript_fetching: 75,
    web_capture: 50,
    reddit_collection: 20,
    claim_extraction: 30,
    timeline_extraction: 20,
    entity_extraction: 20,
    claim_validation: 40,
    angle_discovery: 20,
    documentary_analysis: 25,
    drive_upload: 15,
  },
};

// Human-readable stage descriptions (must match worker.py stages)
const STAGE_DESCRIPTIONS: Record<string, string> = {
  initializing: 'Preparing your research job...',
  planning: 'AI is analyzing your topic...',
  research_mapping: 'Discovering research angles...',
  source_discovery: 'Finding relevant sources...',
  youtube_enumeration: 'Searching YouTube content...',
  transcript_fetching: 'Extracting video transcripts...',
  web_capture: 'Capturing web content...',
  reddit_collection: 'Collecting Reddit discussions...',
  claim_extraction: 'Extracting claims and quotes...',
  timeline_extraction: 'Building timeline of events...',
  entity_extraction: 'Identifying key entities...',
  claim_validation: 'Validating claims with evidence...',
  angle_discovery: 'Discovering unique angles...',
  documentary_analysis: 'Analyzing documentary structure...',
  drive_upload: 'Creating your documents...',
  completed: 'Research complete!',
  error: 'Job failed',
};

function formatDuration(seconds: number): string {
  if (seconds < 0) return '< 1m';
  if (seconds < 60) {
    return `~${Math.max(1, Math.round(seconds / 10) * 10)}s`;
  } else if (seconds < 3600) {
    const mins = Math.ceil(seconds / 60);
    return `~${mins}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.ceil((seconds % 3600) / 60);
    return mins > 0 ? `~${hours}h ${mins}m` : `~${hours}h`;
  }
}

export default function useETA({
  progress,
  status,
  stage,
  stageStartedAt,
  pipeline,
  createdAt,
}: UseETAOptions): ETAResult {
  const [elapsed, setElapsed] = useState(0);

  // Update elapsed time every second
  useEffect(() => {
    if (status !== 'running' && status !== 'queued') {
      return;
    }

    const startTime = new Date(createdAt).getTime();

    const updateElapsed = () => {
      const now = Date.now();
      setElapsed(Math.floor((now - startTime) / 1000));
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [createdAt, status]);

  // Calculate ETA using stage-based estimation
  const eta = useMemo(() => {
    if (status !== 'running' || !stage) {
      return null;
    }

    // Get durations for this pipeline type, fallback to investigation
    const durations = STAGE_DURATIONS[pipeline] || STAGE_DURATIONS.investigation;

    // Find current stage index
    const currentStageIndex = STAGE_ORDER.indexOf(stage);
    if (currentStageIndex === -1) {
      return null;
    }

    // Calculate time remaining in current stage
    let remainingInCurrentStage = durations[stage] || 30;
    if (stageStartedAt) {
      const stageElapsed = (Date.now() - new Date(stageStartedAt).getTime()) / 1000;
      remainingInCurrentStage = Math.max(0, remainingInCurrentStage - stageElapsed);
    }

    // Calculate time for remaining stages
    let remainingStagesTime = 0;
    for (let i = currentStageIndex + 1; i < STAGE_ORDER.length; i++) {
      remainingStagesTime += durations[STAGE_ORDER[i]] || 30;
    }

    const totalRemaining = remainingInCurrentStage + remainingStagesTime;
    return formatDuration(totalRemaining);
  }, [status, stage, stageStartedAt, pipeline]);

  // Get stage description
  const stageDescription = useMemo(() => {
    if (status === 'completed') return STAGE_DESCRIPTIONS.completed;
    if (status === 'queued') return 'Waiting to start...';
    if (status === 'failed') return 'Job failed';
    if (status === 'cancelled') return 'Job cancelled';
    return STAGE_DESCRIPTIONS[stage || 'initializing'] || 'Processing...';
  }, [status, stage]);

  // Format elapsed time
  const elapsedFormatted = useMemo(() => {
    if (elapsed < 60) {
      return `${elapsed}s`;
    } else if (elapsed < 3600) {
      const mins = Math.floor(elapsed / 60);
      const secs = elapsed % 60;
      return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
    } else {
      const hours = Math.floor(elapsed / 3600);
      const mins = Math.floor((elapsed % 3600) / 60);
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }
  }, [elapsed]);

  return {
    eta,
    elapsed: elapsedFormatted,
    stageDescription,
    isCalculating: status === 'running' && progress > 0 && progress < 100,
  };
}
