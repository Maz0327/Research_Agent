'use client';

/**
 * StageProgress — horizontal pipeline stepper.
 * Stages: INGESTION → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY
 * States: completed (solid green), active (pulsing blue), pending (gray dashed)
 * Compact variant strips labels for use in headers/status bars.
 */

import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const PIPELINE_STAGES = [
  { key: 'ingestion',   label: 'Ingestion' },
  { key: 'extraction',  label: 'Extraction' },
  { key: 'validation',  label: 'Validation' },
  { key: 'synthesis',   label: 'Synthesis' },
  { key: 'assembly',    label: 'Assembly' },
] as const;

type StageKey = typeof PIPELINE_STAGES[number]['key'];

type StepState = 'completed' | 'active' | 'pending';

interface StageProgressProps {
  /** Current active stage key */
  currentStage: string;
  /** List of already-completed stage keys */
  completedStages?: string[];
  /** Compact mode — dots only, no labels */
  compact?: boolean;
  className?: string;
}

function resolveState(
  stageKey: StageKey,
  currentStage: string,
  completedStages: string[]
): StepState {
  if (completedStages.includes(stageKey)) return 'completed';
  if (stageKey === currentStage) return 'active';
  return 'pending';
}

interface StepDotProps {
  state: StepState;
  compact: boolean;
}

function StepDot({ state, compact }: StepDotProps) {
  const size = compact ? 'h-2.5 w-2.5' : 'h-4 w-4';

  if (state === 'completed') {
    return (
      <span
        className={cn(
          'flex items-center justify-center rounded-full bg-accent-green flex-shrink-0',
          size
        )}
        aria-hidden="true"
      >
        {!compact && <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
      </span>
    );
  }

  if (state === 'active') {
    return (
      <span className={cn('relative flex flex-shrink-0', size)} aria-hidden="true">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-blue/60" />
        <span className={cn('relative inline-flex rounded-full bg-accent-blue', size)} />
      </span>
    );
  }

  // pending
  return (
    <span
      className={cn(
        'rounded-full border-2 border-dashed border-muted flex-shrink-0 bg-transparent',
        size
      )}
      aria-hidden="true"
    />
  );
}

interface ConnectorProps {
  state: StepState; // state of the PRECEDING step
  compact: boolean;
}

function Connector({ state, compact }: ConnectorProps) {
  return (
    <div
      className={cn(
        'flex-1 h-px mx-1',
        state === 'completed' ? 'bg-accent-green' : 'border-t border-dashed border-muted'
      )}
      aria-hidden="true"
    />
  );
}

export function StageProgress({
  currentStage,
  completedStages = [],
  compact = false,
  className,
}: StageProgressProps) {
  return (
    <div
      className={cn('flex items-center w-full', className)}
      role="list"
      aria-label="Pipeline stages"
    >
      {PIPELINE_STAGES.map((stage, idx) => {
        const state = resolveState(stage.key, currentStage, completedStages);
        const isLast = idx === PIPELINE_STAGES.length - 1;

        return (
          <div
            key={stage.key}
            className={cn('flex items-center', !isLast && 'flex-1')}
            role="listitem"
            aria-label={`${stage.label}: ${state}`}
          >
            {/* Step */}
            <div className={cn('flex flex-col items-center gap-1', compact ? '' : 'min-w-[60px]')}>
              <StepDot state={state} compact={compact} />
              {!compact && (
                <span
                  className={cn(
                    'text-[10px] font-medium text-center leading-tight',
                    state === 'active' && 'text-accent-blue',
                    state === 'completed' && 'text-accent-green',
                    state === 'pending' && 'text-muted-foreground'
                  )}
                >
                  {stage.label}
                </span>
              )}
            </div>

            {/* Connector line between steps */}
            {!isLast && (
              <Connector state={state} compact={compact} />
            )}
          </div>
        );
      })}
    </div>
  );
}
