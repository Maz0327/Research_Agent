/**
 * citation-pill — Compact source reference badge using shadcn Badge.
 * Shows source ID in monospace font. Clickable with cursor-pointer.
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { formatInternalId } from '@/lib/document-formatters';

interface CitationPillProps {
  id: string;
  label?: string;
  onClick?: () => void;
  className?: string;
}

export function CitationPill({ id, label, onClick, className }: CitationPillProps) {
  const display = label ?? formatInternalId(id);

  return (
    <Badge
      variant="outline"
      onClick={onClick}
      className={cn(
        'text-[11px] px-1.5 py-0 font-mono text-zinc-300 border-zinc-600/40 bg-zinc-800/60',
        onClick && 'cursor-pointer hover:text-zinc-200 hover:border-zinc-500/60',
        className,
      )}
      title={id}
    >
      {display}
    </Badge>
  );
}
