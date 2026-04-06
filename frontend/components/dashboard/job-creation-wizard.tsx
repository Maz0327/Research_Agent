'use client';

/**
 * Multi-step job creation wizard.
 * Steps: 1 Topic → 2 Sources → 3 Mode → 4 Preview
 */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { WizardStepTopic } from './wizard-step-topic';
import { WizardStepSources, type SourceEntry } from './wizard-step-sources';
import { WizardStepMode } from './wizard-step-mode';
import { WizardStepPreview } from './wizard-step-preview';
import { usePreviewJob } from '@/hooks/use-preview-job';
import type { JobPreview } from '@/store/jobs';

const STEP_LABELS = ['What are you researching?', 'Paste your links', 'How deep?', 'Review & start'];
const TOTAL_STEPS = STEP_LABELS.length;

interface WizardState {
  step: number;
  topic: string;
  sources: SourceEntry[];
  pipeline: string;
  niche: string;
  preview: JobPreview | null;
}

function initialState(): WizardState {
  return { step: 1, topic: '', sources: [], pipeline: 'quick', niche: '', preview: null };
}

interface JobCreationWizardProps {
  onClose?: () => void;
}

export function JobCreationWizard({ onClose }: JobCreationWizardProps) {
  const [state, setState] = useState<WizardState>(initialState);
  const { mutateAsync: previewJob, isPending: isPreviewing } = usePreviewJob();

  const set = (patch: Partial<WizardState>) => setState((s) => ({ ...s, ...patch }));

  const canNext =
    state.step === 1 ? state.topic.trim().length > 0 :
    state.step === 2 ? true :
    state.step === 3 ? !!state.pipeline :
    false;

  async function handleNext() {
    if (state.step === 3) {
      // Fetch preview before showing step 4
      try {
        const sourceUrls = state.sources
          .filter((s) => s.type !== 'text' && s.url.trim())
          .map((s) => s.url.trim());
        const preview = await previewJob({
          topic: state.topic,
          pipeline: state.pipeline,
          source_urls: sourceUrls,
          niche: state.niche && state.niche !== '__auto' ? state.niche : undefined,
        });
        set({ preview, step: 4 });
      } catch {
        // Still advance without preview on error
        set({ step: 4 });
      }
    } else {
      set({ step: state.step + 1 });
    }
  }

  const handleBack = () => set({ step: state.step - 1 });

  const progressValue = ((state.step - 1) / (TOTAL_STEPS - 1)) * 100;

  return (
    <div className="flex flex-col gap-6 p-1">
      {/* Step indicator */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between text-xs text-muted-foreground">
          {STEP_LABELS.map((label, i) => (
            <span
              key={label}
              className={i + 1 === state.step ? 'text-foreground font-medium' : ''}
            >
              {label}
            </span>
          ))}
        </div>
        <Progress value={progressValue} className="h-1" />
      </div>

      {/* Step content */}
      <div className="min-h-[200px]">
        {state.step === 1 && (
          <WizardStepTopic topic={state.topic} onChange={(topic) => set({ topic })} />
        )}
        {state.step === 2 && (
          <WizardStepSources sources={state.sources} onChange={(sources) => set({ sources })} />
        )}
        {state.step === 3 && (
          <WizardStepMode
            pipeline={state.pipeline}
            niche={state.niche}
            onPipelineChange={(pipeline) => set({ pipeline })}
            onNicheChange={(niche) => set({ niche })}
          />
        )}
        {state.step === 4 && (
          <WizardStepPreview
            topic={state.topic}
            pipeline={state.pipeline}
            niche={state.niche}
            sources={state.sources}
            preview={state.preview}
            onSelectInterpretation={(topic) => set({ topic, preview: null })}
          />
        )}
      </div>

      {/* Navigation */}
      {state.step < 4 && (
        <div className="flex justify-between gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={state.step === 1 ? onClose : handleBack}
            className="border-border text-muted-foreground"
          >
            {state.step === 1 ? 'Cancel' : 'Back'}
          </Button>
          <Button
            size="sm"
            onClick={handleNext}
            disabled={!canNext || isPreviewing}
          >
            {isPreviewing ? 'Loading…' : state.step === 3 ? 'Preview' : 'Next'}
          </Button>
        </div>
      )}
    </div>
  );
}
