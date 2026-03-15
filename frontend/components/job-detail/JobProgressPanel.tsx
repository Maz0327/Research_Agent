/**
 * JobProgressPanel - Premium pipeline progress visualization
 *
 * Design language: Linear/Vercel-inspired dark theme
 * - Neutral surface (no colored alert boxes)
 * - Vertical timeline with connecting track line
 * - SVG spinner (no CSS border hack)
 * - Thin gradient progress bar with glow
 * - Opacity-based text hierarchy
 * - Spring animations
 */
import { motion } from 'framer-motion';
import useETA from '../../hooks/useETA';
import { getStageLabel, getStageDescription } from '../../lib/constants';
import type { Job } from '../../store/jobs';

export interface JobProgressPanelProps {
  job: Job;
}

// ─── Stage Definitions ──────────────────────────────────────────────────────────

const SEMANTIC_STAGES: Array<{ key: string; label: string }> = [
  { key: 'source_identity', label: 'Identifying Sources' },
  { key: 'semantic_extraction', label: 'Extracting Claims' },
  { key: 'semantic_validation', label: 'Validating Claims' },
  { key: 'gap_analysis', label: 'Finding Gaps' },
  { key: 'semantic_synthesis', label: 'Connecting Themes' },
  { key: 'document_assembly', label: 'Assembling Documents' },
  { key: 'completion', label: 'Finalizing' },
];

const GEMINI_STAGES: Array<{ key: string; label: string }> = [
  { key: 'pass_1_extraction', label: 'Pass 1: Extracting clips & quotes' },
  { key: 'pass_2_structure', label: 'Pass 2: Analyzing video structure' },
  { key: 'pass_3_gaps', label: 'Pass 3: Identifying research gaps' },
  { key: 'pass_4_research', label: 'Pass 4: Generating research starter' },
];

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
  return null;
}

// ─── SVG Spinner ────────────────────────────────────────────────────────────────

function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="animate-spin">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.12" />
      <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

// ─── Stage Timeline ─────────────────────────────────────────────────────────────

function StageTimeline({
  stages,
  currentStage,
}: {
  stages: Array<{ key: string; label: string }>;
  currentStage?: string;
}) {
  const currentIdx = stages.findIndex((s) => s.key === currentStage);

  return (
    <div className="mt-4 relative">
      {stages.map((stage, idx) => {
        const done = currentIdx >= 0 && idx < currentIdx;
        const active = stage.key === currentStage;
        const isLast = idx === stages.length - 1;

        return (
          <div key={stage.key} className="relative flex items-start gap-3">
            {/* Vertical track line */}
            {!isLast && (
              <div
                className={`
                  absolute left-[7px] top-[18px] w-[2px] h-[calc(100%-4px)]
                  transition-colors duration-500
                  ${done ? 'bg-emerald-500/40' : 'bg-white/[0.06]'}
                `}
              />
            )}

            {/* Step indicator */}
            <div className="relative z-10 flex-shrink-0 mt-[3px]">
              {done ? (
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className="w-4 h-4 rounded-full flex items-center justify-center bg-emerald-500/20"
                >
                  <svg className="w-2.5 h-2.5 text-emerald-400" viewBox="0 0 12 12" fill="none">
                    <path d="M2.5 6 L5 8.5 L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </motion.div>
              ) : active ? (
                <motion.div
                  animate={{ boxShadow: ['0 0 0 0 rgba(59,130,246,0)', '0 0 0 4px rgba(59,130,246,0.15)', '0 0 0 0 rgba(59,130,246,0)'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  className="w-4 h-4 rounded-full bg-blue-500/20 flex items-center justify-center"
                >
                  <div className="w-2 h-2 rounded-full bg-blue-400" />
                </motion.div>
              ) : (
                <div className="w-4 h-4 rounded-full flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/15" />
                </div>
              )}
            </div>

            {/* Label */}
            <span
              className={`
                text-sm pb-3 transition-all duration-300
                ${done ? 'text-white/35 font-normal' : ''}
                ${active ? 'text-white/90 font-medium' : ''}
                ${!done && !active ? 'text-white/25 font-normal' : ''}
              `}
            >
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Component ──────────────────────────────────────────────────────────────────

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

  const clampedProgress = Math.min(100, Math.max(0, job.progress_percent ?? 0));
  const stageList = resolveStageList(job.pipeline, job.stage);
  const stageLabel =
    job.status === 'queued'
      ? 'Waiting in queue'
      : getStageLabel(job.stage);
  const description =
    job.status === 'queued'
      ? 'Your job will start shortly.'
      : job.pass_detail || stageDescription || getStageDescription(job.stage) || 'Processing your research';

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-5 mb-6"
    >
      {/* Header: spinner + stage label + elapsed/ETA */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 text-white/50 mt-0.5">
            <Spinner size={18} />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-white/90 tracking-tight truncate">{stageLabel}</p>
            <p className="text-sm text-white/40 mt-0.5">{description}</p>
          </div>
        </div>

        {/* Timing block */}
        <div className="flex-shrink-0 text-right space-y-0.5">
          <p className="text-sm font-mono text-white/50 tabular-nums">{clampedProgress}%</p>
          {elapsed && (
            <p className="text-[11px] text-white/25 font-mono tabular-nums">{elapsed}</p>
          )}
          {eta && (
            <p className="text-[11px] text-emerald-400/70 font-mono tabular-nums">ETA {eta}</p>
          )}
        </div>
      </div>

      {/* Progress bar — thin gradient with glow */}
      <div className="mt-4 h-[3px] rounded-full bg-white/[0.06] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ type: 'spring', stiffness: 100, damping: 20 }}
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400"
          style={{ boxShadow: '0 0 8px rgba(59,130,246,0.4), 0 0 2px rgba(59,130,246,0.8)' }}
        />
      </div>

      {/* Source count */}
      {job.artifacts?.semantic_extractions && job.artifacts.semantic_extractions.length > 0 && (
        <p className="text-[11px] text-white/25 mt-2">
          {job.artifacts.semantic_extractions.length} source{job.artifacts.semantic_extractions.length !== 1 ? 's' : ''} being analyzed
        </p>
      )}

      {/* Stage timeline */}
      {stageList && <StageTimeline stages={stageList} currentStage={job.stage} />}
    </motion.div>
  );
}
