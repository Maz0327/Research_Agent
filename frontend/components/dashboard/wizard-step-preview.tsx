'use client';

/**
 * Wizard Step 4 — Preview & confirm.
 * Shows interpreted topic, handles ambiguity with interpretation cards,
 * then creates the job on confirm.
 */
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Spinner } from '@/components/ui/Spinner';
import { useCreateJob } from '@/hooks/use-create-job';
import { pipelineLabels } from '@/components/job-card/job-card-config';
import type { JobPreview, Interpretation } from '@/store/jobs';
import type { SourceEntry } from './wizard-step-sources';

interface WizardStepPreviewProps {
  topic: string;
  pipeline: string;
  niche: string;
  sources: SourceEntry[];
  preview: JobPreview | null;
  onSelectInterpretation: (topic: string) => void;
}

export function WizardStepPreview({
  topic,
  pipeline,
  niche,
  sources,
  preview,
  onSelectInterpretation,
}: WizardStepPreviewProps) {
  const router = useRouter();
  const { mutateAsync: createJob, isPending, error } = useCreateJob();

  const sourceUrls = sources
    .filter((s) => s.type !== 'text' && s.url.trim())
    .map((s) => s.url.trim());

  const effectiveTopic = preview?.interpreted_topic || topic;
  const modeLabel = pipelineLabels[pipeline] ?? pipeline;

  async function handleConfirm() {
    try {
      const job = await createJob({
        topic: effectiveTopic,
        pipeline,
        source_urls: sourceUrls,
        niche: niche && niche !== '__auto' ? niche : undefined,
      });
      router.push(`/jobs/${job.id}`);
    } catch {
      // error surfaced via hook
    }
  }

  if (preview?.is_ambiguous && preview.interpretations?.length) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#f5f5f5] mb-1">Topic needs clarification</h2>
          <p className="text-sm text-[#71717a]">Which interpretation did you mean?</p>
        </div>
        {preview.interpretations.map((interp: Interpretation) => (
          <Card
            key={interp.topic}
            className="bg-[#1a1a25] border-[#27272a] hover:border-[#3f3f46] cursor-pointer transition-colors"
            onClick={() => onSelectInterpretation(interp.topic)}
          >
            <CardContent className="p-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-[#f5f5f5]">{interp.label}</p>
                <p className="text-xs text-[#71717a] mt-1">{interp.description}</p>
              </div>
              <Button size="sm" variant="outline" className="shrink-0 border-[#27272a]">
                Select
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-base font-semibold text-[#f5f5f5] mb-1">Ready to start research</h2>
        <p className="text-sm text-[#71717a]">Review and confirm your research job.</p>
      </div>

      <Card className="bg-[#1a1a25] border-[#27272a]">
        <CardContent className="p-4 flex flex-col gap-2 text-sm">
          <div className="flex gap-2">
            <span className="text-[#71717a] w-20 shrink-0">Topic</span>
            <span className="text-[#f5f5f5]">{effectiveTopic}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-[#71717a] w-20 shrink-0">Mode</span>
            <span className="text-[#f5f5f5]">{modeLabel}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-[#71717a] w-20 shrink-0">Sources</span>
            <span className="text-[#f5f5f5]">
              {sourceUrls.length > 0 ? `${sourceUrls.length} provided` : 'Auto-discover'}
            </span>
          </div>
          {niche && niche !== '__auto' && (
            <div className="flex gap-2">
              <span className="text-[#71717a] w-20 shrink-0">Niche</span>
              <span className="text-[#f5f5f5]">{niche}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-red-400">{error.message}</p>
      )}

      <Button onClick={handleConfirm} disabled={isPending} className="w-full">
        {isPending ? (
          <span className="flex items-center gap-2">
            <Spinner size="sm" /> Creating job…
          </span>
        ) : (
          'Start Research'
        )}
      </Button>
    </div>
  );
}
