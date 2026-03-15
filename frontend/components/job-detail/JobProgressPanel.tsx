/**
 * JobProgressPanel - Premium pipeline progress visualization
 *
 * Phase 3C: Active Wait with Narrated Loading States
 * - Narrated stage descriptions that tell the user what's happening
 * - Partial result previews as stages complete
 * - "While you wait" suggestions
 *
 * Design language: Linear/Vercel-inspired dark theme
 */
import { motion, AnimatePresence } from 'framer-motion';
import useETA from '../../hooks/useETA';
import { getStageLabel } from '../../lib/constants';
import type { Job } from '../../store/jobs';
import { PartialResultsPreview } from './PartialResultsPreview';

export interface JobProgressPanelProps {
  job: Job;
}

// ─── Narrated Stage Descriptions ──────────────────────────────────────────────

const NARRATED_DESCRIPTIONS: Record<string, string> = {
  source_identity: 'Analyzing your sources... identifying content types and fetching transcripts',
  semantic_extraction: 'Reading each source carefully... extracting claims, key points, and quotes',
  semantic_validation: 'Verifying claims... checking confidence levels against source quality',
  gap_analysis: 'Looking for gaps in the research... what angles are missing?',
  semantic_synthesis: 'Finding patterns across all sources... connecting themes and tensions',
  document_assembly: 'Building your documents... formatting for readability',
  creator_brief_assembly: 'Writing your Creator Brief... crafting hooks and story angles',
  completion: 'Final checks... polishing and saving your research',
};

/** Get a narrated description with dynamic details from the job */
function getNarratedDescription(job: Job): string {
  const stage = job.stage || '';

  // Dynamic descriptions based on actual job data
  if (stage === 'semantic_extraction' && job.artifacts?.semantic_extractions) {
    const count = job.artifacts.semantic_extractions.length;
    const totalSources = (job.artifacts as any)?.source_count || count;
    return `Reading source ${count} of ${totalSources}... extracting claims and key points`;
  }

  if (stage === 'semantic_synthesis' && job.artifacts?.semantic_brief) {
    const themes = (job.artifacts.semantic_brief as any)?.themes;
    if (themes?.length) {
      return `Finding patterns across sources... ${themes.length} theme${themes.length !== 1 ? 's' : ''} emerging`;
    }
  }

  return job.pass_detail || NARRATED_DESCRIPTIONS[stage] || 'Processing your research...';
}

// ─── Stage Definitions ──────────────────────────────────────────────────────────

const SEMANTIC_STAGES: Array<{ key: string; label: string; narrated: string }> = [
  { key: 'source_identity', label: 'Identifying Sources', narrated: 'Analyzing your sources' },
  { key: 'semantic_extraction', label: 'Extracting Claims', narrated: 'Reading each source' },
  { key: 'semantic_validation', label: 'Validating Claims', narrated: 'Verifying accuracy' },
  { key: 'gap_analysis', label: 'Finding Gaps', narrated: 'Checking for blind spots' },
  { key: 'semantic_synthesis', label: 'Connecting Themes', narrated: 'Finding patterns' },
  { key: 'document_assembly', label: 'Assembling Documents', narrated: 'Building your docs' },
  { key: 'completion', label: 'Finalizing', narrated: 'Almost ready' },
];

const GEMINI_STAGES: Array<{ key: string; label: string; narrated: string }> = [
  { key: 'pass_1_extraction', label: 'Pass 1: Extracting clips & quotes', narrated: 'Pulling clips' },
  { key: 'pass_2_structure', label: 'Pass 2: Analyzing video structure', narrated: 'Analyzing structure' },
  { key: 'pass_3_gaps', label: 'Pass 3: Identifying research gaps', narrated: 'Finding gaps' },
  { key: 'pass_4_research', label: 'Pass 4: Generating research starter', narrated: 'Building starter' },
];

const TRANSCRIPT_STAGES: Array<{ key: string; label: string; narrated: string }> = [
  { key: 'extracting_transcripts', label: 'Extracting Transcripts', narrated: 'Getting transcripts' },
  { key: 'storing_transcripts', label: 'Saving Transcripts', narrated: 'Saving' },
];

function resolveStageList(pipeline: string, stage?: string): Array<{ key: string; label: string; narrated: string }> | null {
  if (pipeline === 'gemini_video' || stage?.startsWith('pass_')) return GEMINI_STAGES;
  if (pipeline === 'transcript') return TRANSCRIPT_STAGES;
  const isSemanticStage = SEMANTIC_STAGES.some((s) => s.key === stage);
  const isSemanticPipeline = ['mixed_input', 'text_provided', 'ocr_extracted', 'video_analysis'].includes(pipeline);
  if (isSemanticStage || isSemanticPipeline) return SEMANTIC_STAGES;
  return null;
}

// ─── While You Wait Suggestions ─────────────────────────────────────────────

const WHILE_YOU_WAIT_TIPS = [
  'Pro tip: Start with the Creator Brief when results are ready — it has your hooks and story angles.',
  'The Semantic Brief (Doc 2) has the deep analysis. Great for fact-checking your script.',
  'You can iterate on results after they are done. Try "Different angle" for fresh perspectives.',
];

function WhileYouWait() {
  // Pick a tip based on current minute to rotate them
  const tipIndex = Math.floor(Date.now() / 60000) % WHILE_YOU_WAIT_TIPS.length;

  return (
    <div className="mt-4 px-3 py-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
      <p className="text-[11px] text-white/30 uppercase tracking-wider font-medium mb-1">While you wait</p>
      <p className="text-[12px] text-white/40 leading-relaxed">{WHILE_YOU_WAIT_TIPS[tipIndex]}</p>
    </div>
  );
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
  stages: Array<{ key: string; label: string; narrated: string }>;
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

            {/* Label + narrated description for active stage */}
            <div className="pb-3 min-w-0">
              <span
                className={`
                  text-sm transition-all duration-300
                  ${done ? 'text-white/35 font-normal' : ''}
                  ${active ? 'text-white/90 font-medium' : ''}
                  ${!done && !active ? 'text-white/25 font-normal' : ''}
                `}
              >
                {stage.label}
              </span>
              {active && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-[11px] text-white/30 mt-0.5"
                >
                  {stage.narrated}
                </motion.p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function JobProgressPanel({ job }: JobProgressPanelProps) {
  const { eta, elapsed } = useETA({
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
      : getNarratedDescription(job);

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
            <AnimatePresence mode="wait">
              <motion.p
                key={description}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.3 }}
                className="text-sm text-white/40 mt-0.5"
              >
                {description}
              </motion.p>
            </AnimatePresence>
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

      {/* Partial result previews */}
      <PartialResultsPreview job={job} />

      {/* While you wait suggestion */}
      {clampedProgress > 10 && clampedProgress < 80 && <WhileYouWait />}
    </motion.div>
  );
}
