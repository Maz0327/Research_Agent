/**
 * claim-card — Card with claim statement, ConfidenceBadge, verification status, citation pills.
 */

import { Card, CardContent } from '@/components/ui/card';
import { ConfidenceBadge } from './confidence-badge';
import { CitationPill } from './citation-pill';
import { cn } from '@/lib/utils';

interface ClaimCardProps {
  statement: string;
  confidence: string;
  verified?: boolean;
  sourceIds?: string[];
  className?: string;
}

export function ClaimCard({ statement, confidence, verified, sourceIds, className }: ClaimCardProps) {
  return (
    <Card className={cn('bg-zinc-900/40 border-border', className)}>
      <CardContent className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-zinc-200 leading-relaxed flex-1">{statement}</p>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {verified !== undefined && (
              <span className={cn('text-[11px]', verified ? 'text-green-400' : 'text-zinc-400')}>
                {verified ? '✓' : '—'}
              </span>
            )}
            <ConfidenceBadge level={confidence} />
          </div>
        </div>
        {sourceIds && sourceIds.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {sourceIds.map((id) => (
              <CitationPill key={id} id={id} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
