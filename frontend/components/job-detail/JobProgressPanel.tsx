/**
 * JobProgressPanel - Rich progress display for running jobs.
 *
 * Replaces the plain spinner+bar with:
 * - Elapsed time (ticking every second via useETA)
 * - ETA (stage-based estimate from useETA)
 * - Stage checklist (completed ✓ / active ● / pending ○)
 * - Animated progress bar
 */
import { motion } from 'framer-motion';
import useETA from '../../hooks/useETA';
import { getStageLabel, getStageDescription } from '../../lib/constants';
import type { Job } from '../../store/jobs';

export interface JobProgressPanelProps {
  job: Job;
}

// Ordered stage list for semantic pipeline (matches worker.py emit order)
const SEMANTIC_STAGES: Array<{ key: string; label: string }> = [
  { key: 'source_identity', label: 'Identifying Sources' },
  { key: 'semantic_extraction', label: 'Extracting Claims' },
  { key: 'semantic_validation', label: 'Validating Claims' },
  { key: 'gap_analysis', label: 'Finding Gaps' },
  { key: 'semantic_synthesis', label: 'Connecting Themes' },
  { key: 'document_assembly', label: 'Assembling Documents' },
  { key: 'completion', label: 'Finalizing' },
];

// 4-pass video analysis pipeline
const GEMINI_STAGES: Array<{ key: string; label: string }> = [
  { key: 'pass_1_extraction', label: 'Pass 1: Extracting clips & quotes' },
  { key: 'pass_2_structure', label: 'Pass 2: Analyzing video structure' },
  { key: 'pass_3_gaps', label: 'Pass 3: Identifying research gaps' },
  { key: 'pass_4_research', label: 'Pass 4: Generating research starter' },
];

// Transcript pipeline
const TRANSCRIPT_STAGES: Array<{ key: string; label: string }> = [
  { key: 'extracting_transcripts', label: 'Extracting Transcripts' },
  { key: 'storing_transcripts', label: 'Saving Transcripts' },
];

function resolveStageList(pipeline: string, stage?: string): Array<{ key: string; label: string }> | null {
  if (pipeline === 'gemini_video' || stage?.startsWith('pass_')) return GEMINI_STAGES;
  if (pipeline === 'transcript') return TRANSCRIPT_STAGES;
  const isSemanticStage = SEMANTIC_STAGES.some((s) => s.key === stage);
  const isSemanticPipeline = ['mixed_input', 'text_provided', 'ocr_extracted', 'video_analysis'].includes(pipeline);
  if (isSemanticStage || isSemanticPipeline) return SEMANTIC_STAGES;
  return null; // Unknown pipeline — no checklist
}

function StageChecklist({
  stages,
  currentStage,
}: {
  stages: Array<{ key: string; label: string }>;
  currentStage?: string;
}) {
  const currentIdx = stages.findIndex((s) => s.key === currentStage);

  return (
    <div className="mt-4 space-y-1">
      {stages.map((stage, idx) => {
        const done = currentIdx >= 0 && idx < currentIdx;
        const active = stage.key === currentStage;
        const pending = !done && !active;

        return (
          <div key={stage.key} className="flex items-center gap-2.5 text-sm">
            {/* State indicator */}
            <span className="w-4 flex-shrink-0 text-center">
              {done ? (
                <svg className="w-4 h-4 text-emerald-400 inline" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              ) : active ? (
                <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              ) : (
                <span className="inline-block w-2 h-2 rounded-full bg-gray-600" />
              )}
            </span>

            {/* Stage label */}
            <span
              className={
                done
                  ? 'text-gray-500 line-through'
                  : active
                  ? 'text-blue-300 font-medium'
                  : 'text-gray-500'
              }
            >
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function JobProgressPanel({ job }: JobProgressPanelProps) {
  const { eta, elapsed, stageDescription } = useETA({
    progress: job.progress_percent,
    status: job.status,
    stage: job.stage,
    stageStartedAt: job.stage_started_at,
    passDetail: job.pass_detail,
    pipeline: job.pipeline,
    createdAt: job.created_at,
  });

  const stageList = resolveStageList(job.pipeline, job.stage);
  const stageLabel =
    job.status === 'queued'
      ? 'Waiting in queue…'
      : getStageLabel(job.stage);
  const description =
    job.status === 'queued'
      ? 'Your job will start shortly.'
      : job.pass_detail || stageDescription || getStageDescription(job.stage) || 'Processing your research…';

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-blue-700 bg-blue-900/30 p-4 mb-6"
    >
      {/* Header row: spinner + stage label + elapsed/ETA */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-5 h-5 flex-shrink-0 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mt-0.5" />
          <div className="min-w-0">
            <p className="font-medium text-blue-300 truncate">{stageLabel}</p>
            <p className="text-sm text-gray-400 mt-0.5">{description}</p>
          </div>
        </div>

        {/* Timing block */}
        <div className="flex-shrink-0 text-right">
          <p className="text-sm font-mono text-blue-300">{job.progress_percent}%</p>
          {elapsed && (
            <p className="text-xs text-gray-500 mt-0.5">{elapsed} elapsed</p>
          )}
          {eta && (
            <p className="text-xs text-emerald-400 mt-0.5">ETA {eta}</p>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-2 bg-gray-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${job.progress_percent}%` }}
          transition={{ duration: 0.3 }}
          className="h-full bg-blue-500 rounded-full"
        />
      </div>

      {/* Source count hint */}
      {job.artifacts?.semantic_extractions && job.artifacts.semantic_extractions.length > 0 && (
        <p className="text-xs text-gray-500 mt-2">
          {job.artifacts.semantic_extractions.length} source{job.artifacts.semantic_extractions.length !== 1 ? 's' : ''} being analyzed
        </p>
      )}

      {/* Stage checklist — only for known multi-stage pipelines */}
      {stageList && <StageChecklist stages={stageList} currentStage={job.stage} />}
    </motion.div>
  );
}
