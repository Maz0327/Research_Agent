/**
 * creator-brief-story-core — Story Core + Why It Matters sections for Creator Brief (Doc 3).
 */

import { Card, CardContent } from '@/components/ui/card';
import type { ProducerPacketData } from '@/types/documents';

interface StoryCoreProps {
  data: ProducerPacketData;
}

export function StoryCoreSection({ data }: StoryCoreProps) {
  const core = data.story_core;
  if (!core) return null;

  return (
    <Card className="bg-amber-900/10 border-amber-700/30">
      <CardContent className="p-4 space-y-3">
        <p className="text-caption font-medium text-amber-400 uppercase tracking-wider">Story Core</p>
        <div>
          <p className="text-caption font-semibold text-muted-foreground/70 uppercase tracking-wider">Central Question</p>
          <p className="text-body-lg font-medium text-foreground leading-relaxed mt-0.5">{core.central_question}</p>
        </div>
        <div>
          <p className="text-caption font-semibold text-muted-foreground/70 uppercase tracking-wider">One-Sentence Pitch</p>
          <p className="text-body text-foreground leading-relaxed mt-0.5 italic">{core.one_sentence_pitch}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          {core.target_audience && (
            <div>
              <p className="text-caption font-semibold text-muted-foreground/70 uppercase tracking-wider">Target Audience</p>
              <p className="text-body-sm text-muted-foreground mt-0.5">{core.target_audience}</p>
            </div>
          )}
          {core.emotional_arc && (
            <div>
              <p className="text-caption font-semibold text-muted-foreground/70 uppercase tracking-wider">Emotional Arc</p>
              <p className="text-body-sm text-muted-foreground mt-0.5">{core.emotional_arc}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function WhyItMattersSection({ text }: { text: string }) {
  return (
    <div className="relative bg-card/40 rounded-lg border border-amber-700/30 p-4 overflow-hidden">
      <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-lg bg-amber-500" />
      <div className="pl-3">
        <p className="text-caption font-semibold text-amber-400 uppercase tracking-wider mb-2">
          What this means for your audience
        </p>
        <p className="text-body-lg text-foreground leading-relaxed font-medium">{text}</p>
      </div>
    </div>
  );
}
