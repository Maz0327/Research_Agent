'use client';

/**
 * PipelineStatusBar — terminal-style header showing current pipeline stage.
 * Variants: running (pulsing green dot + progress), completed, failed, queued.
 * Uses STAGE_LABELS from lib/constants.ts for human-readable stage names.
 */

import { CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { STAGE_LABELS } from '@/lib/constants';
import { cn } from '@/lib/utils';

/** Resolve stage description from STAGE_LABELS */
function resolveDescription(stage: string): string | null {
  const entry = STAGE_LABELS[stage as keyof typeof STAGE_LABELS];
  return entry?.description ?? null;
}

type PipelineStatus = 'running' | 'completed' | 'failed' | 'queued';

interface PipelineStatusBarProps {
  /** Backend stage key (e.g. "semantic_extraction") */
  stage: string;
  /** Progress percentage 0–100 */
  progress: number;
  /** Current pipeline status */
  status: PipelineStatus;
  /** Optional ETA string e.g. "~2 min" */
  eta?: string;
  /** Optional error message for failed state */
  errorMessage?: string;
  className?: string;
}

/** Resolve human-readable label from STAGE_LABELS, fallback to raw stage key */
function resolveLabel(stage: string): string {
  const entry = STAGE_LABELS[stage as keyof typeof STAGE_LABELS];
  return entry ? entry.label : stage.replace(/_/g, ' ');
}

export function PipelineStatusBar({
  stage,
  progress,
  status,
  eta,
  errorMessage,
  className,
}: PipelineStatusBarProps) {
  const label = resolveLabel(stage);
  const description = resolveDescription(stage);
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-2 bg-card font-mono text-xs',
        className
      )}
      role="status"
      aria-live="polite"
      aria-label={`Pipeline status: ${label}`}
    >
      {/* Status indicator */}
      {status === 'running' && (
        <>
          {/* Pulsing green dot */}
          <span className="relative flex h-2 w-2 flex-shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-green" />
          </span>
          <span className="flex flex-col min-w-0">
            <span className="text-foreground font-medium truncate">{label}</span>
            {description && (
              <span className="text-muted-foreground font-normal truncate" style={{ fontSize: '0.65rem', lineHeight: '1rem' }}>
                {description}
              </span>
            )}
          </span>
        </>
      )}

      {status === 'completed' && (
        <>
          <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-accent-green" aria-hidden="true" />
          <span className="text-accent-green font-medium">Complete</span>
        </>
      )}

      {status === 'failed' && (
        <>
          <XCircle className="h-3.5 w-3.5 flex-shrink-0 text-destructive" aria-hidden="true" />
          <span className="text-destructive font-medium truncate">
            {errorMessage ?? 'Pipeline failed'}
          </span>
        </>
      )}

      {status === 'queued' && (
        <>
          <Clock className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="text-muted-foreground">Waiting…</span>
        </>
      )}

      {/* Progress bar — only when running */}
      {status === 'running' && (
        <>
          <div
            className="flex-1 h-1 rounded-full bg-muted overflow-hidden min-w-[60px] max-w-[200px]"
            aria-hidden="true"
          >
            <div
              className="h-full bg-accent-green rounded-full transition-all duration-500 ease-out"
              style={{ width: `${clampedProgress}%` }}
            />
          </div>

          <span className="text-muted-foreground tabular-nums flex-shrink-0">
            {clampedProgress}%
          </span>

          {eta && (
            <span className="text-muted-foreground flex-shrink-0 hidden sm:inline">
              <Loader2 className="inline h-3 w-3 mr-1 animate-spin" aria-hidden="true" />
              {eta}
            </span>
          )}
        </>
      )}
    </div>
  );
}
