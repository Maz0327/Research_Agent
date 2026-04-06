'use client';

/**
 * SourceSummary — Left panel collapsible list of sources from job inputs.
 * Shows title, type badge, mode badge, confidence ceiling.
 * Auto-collapses when >5 sources.
 */
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { Job } from '@/store/jobs';

interface SourceSummaryProps {
  job: Job;
}

interface SourceEntry {
  id: string;
  title?: string;
  url?: string;
  type?: string;
  mode?: string;
  confidence_ceiling?: string;
}

function extractSources(job: Job): SourceEntry[] {
  // Try semantic_extractions first
  if (job.artifacts?.semantic_extractions?.length) {
    return job.artifacts.semantic_extractions.map((s: any, i: number) => ({
      id: s.source_id ?? `SRC_${i + 1}`,
      title: s.title ?? s.url ?? `Source ${i + 1}`,
      url: s.url,
      type: s.source_type ?? s.type,
      mode: s.analysis_mode ?? s.mode,
      confidence_ceiling: s.confidence_ceiling,
    }));
  }
  return [];
}

const TYPE_COLORS: Record<string, string> = {
  youtube: 'bg-red-900/40 text-red-300 border-red-700/40',
  article: 'bg-blue-900/40 text-blue-300 border-blue-700/40',
  reddit: 'bg-orange-900/40 text-orange-300 border-orange-700/40',
  text: 'bg-card text-muted-foreground border-border',
  screenshot: 'bg-purple-900/40 text-purple-300 border-purple-700/40',
};

export function SourceSummary({ job }: SourceSummaryProps) {
  const [open, setOpen] = useState(false);
  const sources = extractSources(job);
  if (!sources.length) return null;

  const THRESHOLD = 5;
  const needsCollapse = sources.length > THRESHOLD;
  const visible = needsCollapse && !open ? sources.slice(0, THRESHOLD) : sources;

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Sources ({sources.length})
      </p>
      <ul className="space-y-1.5">
        {visible.map((src) => {
          const typeKey = (src.type ?? '').toLowerCase();
          const typeClass = TYPE_COLORS[typeKey] ?? 'bg-card text-muted-foreground border-border';
          return (
            <li key={src.id} className="rounded-md border border-border bg-secondary px-2 py-1.5 space-y-1">
              <p className="text-xs text-foreground truncate" title={src.title}>
                {src.title ?? src.id}
              </p>
              <div className="flex flex-wrap gap-1">
                {src.type && (
                  <Badge variant="outline" className={`text-caption px-1 py-0 ${typeClass}`}>
                    {src.type}
                  </Badge>
                )}
                {src.confidence_ceiling && (
                  <Badge variant="outline" className="text-caption px-1 py-0 text-muted-foreground border-border">
                    {src.confidence_ceiling}
                  </Badge>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {needsCollapse && (
        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
            {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {open ? 'Show less' : `+${sources.length - THRESHOLD} more`}
          </CollapsibleTrigger>
          <CollapsibleContent />
        </Collapsible>
      )}
    </div>
  );
}
