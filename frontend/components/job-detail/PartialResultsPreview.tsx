/**
 * PartialResultsPreview — Shows preview cards as pipeline stages complete.
 *
 * Phase 3C: Progressive reveal of partial results during job execution.
 * - After source_identity: Source summary (X sources found: types breakdown)
 * - After semantic_extraction: Top 3 claims preview
 * - After semantic_synthesis: Theme preview
 * - After creator_brief: Hook preview
 */

import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Job } from '../../store/jobs';

interface PartialResultsPreviewProps {
  job: Job;
}

const STAGE_ORDER = [
  'source_identity',
  'semantic_extraction',
  'semantic_validation',
  'gap_analysis',
  'semantic_synthesis',
  'document_assembly',
  'creator_brief_assembly',
  'completion',
];

function stageIndex(stage: string | undefined): number {
  if (!stage) return -1;
  return STAGE_ORDER.indexOf(stage);
}

/** Source summary card — shown after source_identity completes */
function SourceSummary({ job }: { job: Job }) {
  const extractions = job.artifacts?.semantic_extractions;
  if (!extractions || extractions.length === 0) return null;

  // Count source types
  const types: Record<string, number> = {};
  for (const ext of extractions) {
    const t = (ext as any).source_type || (ext as any).analysis_mode || 'unknown';
    const label = t.includes('youtube') || t.includes('video') ? 'YouTube'
      : t.includes('article') ? 'Article'
      : t.includes('text') ? 'Text'
      : t.includes('reddit') ? 'Reddit'
      : 'Source';
    types[label] = (types[label] || 0) + 1;
  }

  const typeStr = Object.entries(types)
    .map(([label, count]) => `${count} ${label}`)
    .join(', ');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/[0.06] border border-emerald-500/10"
    >
      <svg className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
      <p className="text-[12px] text-emerald-300/80">
        {extractions.length} source{extractions.length !== 1 ? 's' : ''} found: {typeStr}
      </p>
    </motion.div>
  );
}

/** Top claims preview — shown after semantic_extraction completes */
function ClaimsPreview({ job }: { job: Job }) {
  const extractions = job.artifacts?.semantic_extractions;
  if (!extractions || extractions.length === 0) return null;

  // Collect top claims across all extractions
  const allClaims: Array<{ statement: string; confidence: string }> = [];
  for (const ext of extractions) {
    const claims = (ext as any).claims || [];
    for (const claim of claims) {
      if (claim.statement && allClaims.length < 3) {
        allClaims.push({
          statement: claim.statement,
          confidence: claim.confidence || 'medium',
        });
      }
    }
  }

  if (allClaims.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="px-3 py-2.5 rounded-lg bg-blue-500/[0.04] border border-blue-500/10"
    >
      <p className="text-[11px] text-blue-400/70 font-medium uppercase tracking-wider mb-1.5">Top Claims</p>
      <div className="space-y-1.5">
        {allClaims.map((claim, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={`text-[10px] px-1 py-0.5 rounded flex-shrink-0 mt-0.5 ${
              claim.confidence === 'high' ? 'bg-green-900/30 text-green-400' :
              claim.confidence === 'low' ? 'bg-yellow-900/30 text-yellow-400' :
              'bg-blue-900/30 text-blue-400'
            }`}>
              {claim.confidence}
            </span>
            <p className="text-[12px] text-white/40 line-clamp-1">{claim.statement}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

/** Theme preview — shown after semantic_synthesis completes */
function ThemePreview({ job }: { job: Job }) {
  const brief = job.artifacts?.semantic_brief as any;
  if (!brief?.themes || brief.themes.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="px-3 py-2.5 rounded-lg bg-purple-500/[0.04] border border-purple-500/10"
    >
      <p className="text-[11px] text-purple-400/70 font-medium uppercase tracking-wider mb-1.5">
        {brief.themes.length} theme{brief.themes.length !== 1 ? 's' : ''} found
      </p>
      <div className="flex flex-wrap gap-1.5">
        {brief.themes.slice(0, 4).map((theme: any, i: number) => (
          <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-purple-900/20 text-purple-300/70 border border-purple-700/20">
            {theme.label || theme.theme_id}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

/** Hook preview — shown after creator_brief completes */
function HookPreview({ job }: { job: Job }) {
  // creator_brief data may be in doc_3 inline data or legacy creator_brief_md
  const brief = (job.artifacts as any)?.creator_brief || (job.artifacts as any)?.doc_3_inline;
  if (!brief?.hook_options || brief.hook_options.length === 0) return null;

  const topHook = brief.hook_options[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="px-3 py-2.5 rounded-lg bg-amber-500/[0.04] border border-amber-500/10"
    >
      <p className="text-[11px] text-amber-400/70 font-medium uppercase tracking-wider mb-1.5">Hook Preview</p>
      <p className="text-[12px] text-white/50 italic line-clamp-2">
        &ldquo;{topHook.text}&rdquo;
      </p>
    </motion.div>
  );
}

export function PartialResultsPreview({ job }: PartialResultsPreviewProps) {
  const currentStageIdx = stageIndex(job.stage);

  const showSourceSummary = currentStageIdx > 0;
  const showClaims = currentStageIdx > 1;
  const showThemes = currentStageIdx > 4;
  const showHook = currentStageIdx > 5 || (job.artifacts as any)?.creator_brief;

  // Don't show anything if we're at the very beginning
  if (currentStageIdx <= 0) return null;

  return (
    <AnimatePresence>
      <div className="mt-4 space-y-2">
        {showSourceSummary && <SourceSummary job={job} />}
        {showClaims && <ClaimsPreview job={job} />}
        {showThemes && <ThemePreview job={job} />}
        {showHook && <HookPreview job={job} />}
      </div>
    </AnimatePresence>
  );
}
