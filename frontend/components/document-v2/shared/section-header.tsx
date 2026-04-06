/**
 * section-header — Flex row with optional icon + title + count Badge + ConfidenceBadge.
 * Designed to sit inside AccordionTrigger or as standalone section label.
 */

import { Badge } from '@/components/ui/badge';
import { ConfidenceBadge } from './confidence-badge';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  title: string;
  icon?: React.ReactNode;
  count?: number;
  confidence?: string;
  className?: string;
}

export function SectionHeader({ title, icon, count, confidence, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {icon && <span className="flex-shrink-0 text-muted-foreground">{icon}</span>}
      <span className="font-medium text-sm text-foreground">{title}</span>
      {count !== undefined && (
        <Badge variant="secondary" className="text-caption px-1.5 py-0 bg-card text-muted-foreground">
          {count}
        </Badge>
      )}
      {confidence && <ConfidenceBadge level={confidence} />}
    </div>
  );
}
