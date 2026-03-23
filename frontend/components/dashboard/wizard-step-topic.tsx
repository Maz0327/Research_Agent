'use client';

/**
 * Wizard Step 1 — Topic input.
 * User enters the research topic (required, max 2000 chars).
 */
import { Input } from '@/components/ui/input';
import { VALIDATION_LIMITS } from '@/lib/constants';

interface WizardStepTopicProps {
  topic: string;
  onChange: (value: string) => void;
}

export function WizardStepTopic({ topic, onChange }: WizardStepTopicProps) {
  const remaining = VALIDATION_LIMITS.MAX_PROMPT_LENGTH - topic.length;
  const isNearLimit = remaining < 200;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-foreground mb-1">What would you like to research?</h2>
        <p className="text-sm text-muted-foreground">Enter a topic, question, or subject to investigate.</p>
      </div>
      <Input
        value={topic}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. The impact of AI on journalism"
        maxLength={VALIDATION_LIMITS.MAX_PROMPT_LENGTH}
        className="bg-secondary border-border text-foreground placeholder:text-muted-foreground"
        autoFocus
      />
      <p className={`text-xs text-right ${isNearLimit ? 'text-orange-400' : 'text-muted-foreground'}`}>
        {topic.length} / {VALIDATION_LIMITS.MAX_PROMPT_LENGTH}
      </p>
    </div>
  );
}
