'use client';

/**
 * Wizard Step 3 — Research mode + optional niche selector.
 */
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const PIPELINE_OPTIONS: { value: string; label: string; description: string }[] = [
  { value: 'quick', label: 'Quick Brief', description: 'Fast overview — best for breaking news or first look.' },
  { value: 'full', label: 'Full Research', description: 'Deep analysis across all sources with full documents.' },
  { value: 'breaking_news', label: 'Breaking News', description: 'Speed-optimised for rapidly evolving stories.' },
  { value: 'investigation', label: 'Investigation', description: 'Multi-angle deep dive for investigative pieces.' },
  { value: 'profile', label: 'Profile', description: 'Person or organisation background research.' },
  { value: 'controversy', label: 'Controversy', description: 'Balanced view of contested topics and debates.' },
];

const NICHE_OPTIONS = [
  { value: '', label: 'Auto-detect' },
  { value: 'tech', label: 'Technology' },
  { value: 'finance', label: 'Finance' },
  { value: 'health', label: 'Health & Science' },
  { value: 'politics', label: 'Politics' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'sports', label: 'Sports' },
  { value: 'business', label: 'Business' },
];

interface WizardStepModeProps {
  pipeline: string;
  niche: string;
  onPipelineChange: (value: string) => void;
  onNicheChange: (value: string) => void;
}

export function WizardStepMode({
  pipeline,
  niche,
  onPipelineChange,
  onNicheChange,
}: WizardStepModeProps) {
  const selected = PIPELINE_OPTIONS.find((o) => o.value === pipeline);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-base font-semibold text-foreground mb-1">Choose research mode</h2>
        <p className="text-sm text-muted-foreground">Controls depth, speed, and document types generated.</p>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-muted-foreground">Mode</label>
        <Select value={pipeline} onValueChange={onPipelineChange}>
          <SelectTrigger className="bg-secondary border-border text-foreground">
            <SelectValue placeholder="Select mode…" />
          </SelectTrigger>
          <SelectContent className="bg-secondary border-border">
            {PIPELINE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value} className="text-foreground">
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selected && (
          <p className="text-xs text-muted-foreground mt-1">{selected.description}</p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-muted-foreground">Niche (optional)</label>
        <Select value={niche || ''} onValueChange={onNicheChange}>
          <SelectTrigger className="bg-secondary border-border text-foreground">
            <SelectValue placeholder="Auto-detect" />
          </SelectTrigger>
          <SelectContent className="bg-secondary border-border">
            {NICHE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value || '__auto'} value={opt.value || '__auto'} className="text-foreground">
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
