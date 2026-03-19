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
        <p className="text-[10px] font-medium text-amber-400 uppercase tracking-wider">Story Core</p>
        <div>
          <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Central Question</p>
          <p className="text-[15px] font-medium text-zinc-100 leading-relaxed mt-0.5">{core.central_question}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">One-Sentence Pitch</p>
          <p className="text-[14px] text-zinc-200 leading-relaxed mt-0.5 italic">{core.one_sentence_pitch}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          {core.target_audience && (
            <div>
              <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Target Audience</p>
              <p className="text-[13px] text-zinc-300 mt-0.5">{core.target_audience}</p>
            </div>
          )}
          {core.emotional_arc && (
            <div>
              <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Emotional Arc</p>
              <p className="text-[13px] text-zinc-300 mt-0.5">{core.emotional_arc}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function WhyItMattersSection({ text }: { text: string }) {
  return (
    <div className="relative bg-zinc-800/40 rounded-lg border border-amber-700/30 p-4 overflow-hidden">
      <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-lg bg-amber-500" />
      <div className="pl-3">
        <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-2">
          What this means for your audience
        </p>
        <p className="text-[15px] text-zinc-100 leading-relaxed font-medium">{text}</p>
      </div>
    </div>
  );
}
