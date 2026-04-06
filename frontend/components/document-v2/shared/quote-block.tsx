/**
 * quote-block — Card with left border-accent-blue, italic quote text, source attribution.
 * Shows unverified badge if quote.unverified is true.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface QuoteBlockProps {
  text: string;
  speaker?: string;
  source?: string;
  timestamp?: string;
  unverified?: boolean;
  className?: string;
}

export function QuoteBlock({ text, speaker, source, timestamp, unverified, className }: QuoteBlockProps) {
  return (
    <Card className={cn('border-l-2 border-l-blue-500/60 border-border bg-background/40 rounded-lg', className)}>
      <CardContent className="p-3">
        <p className="text-sm text-foreground italic leading-relaxed">&ldquo;{text}&rdquo;</p>
        {(speaker || source || timestamp || unverified) && (
          <div className="flex flex-wrap items-center gap-2 mt-2">
            {speaker && <span className="text-caption text-muted-foreground/70 font-medium">— {speaker}</span>}
            {source && <span className="text-caption text-muted-foreground/60">{source}</span>}
            {timestamp && <span className="text-caption font-mono text-blue-400/60">{timestamp}</span>}
            {unverified && (
              <Badge variant="outline" className="text-[9px] px-1 py-0 text-amber-400 border-amber-500/30 bg-amber-900/10">
                unverified
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
