/**
 * confidence-badge — shadcn Badge-based confidence level indicator.
 * HIGH = green, MEDIUM = orange, LOW = red.
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ConfidenceBadgeProps {
  level: string;
  className?: string;
}

const STYLES: Record<string, string> = {
  high:   'bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/10',
  medium: 'bg-orange-500/10 text-orange-400 border-orange-500/20 hover:bg-orange-500/10',
  low:    'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/10',
};

export function ConfidenceBadge({ level, className }: ConfidenceBadgeProps) {
  const normalized = (level ?? '').toLowerCase();
  const style = STYLES[normalized] ?? 'bg-card text-muted-foreground border-border/20 hover:bg-card';

  return (
    <Badge
      variant="outline"
      className={cn('text-caption px-1.5 py-0.5 font-medium', style, className)}
    >
      {normalized.charAt(0).toUpperCase() + normalized.slice(1)}
    </Badge>
  );
}
