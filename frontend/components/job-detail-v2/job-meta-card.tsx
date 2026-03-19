'use client';

/**
 * JobMetaCard — Left panel card showing job title, status, mode, and timestamps.
 */
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/job/status-badge';
import { formatTimestampWithRelative } from '@/lib/document-formatters';
import type { Job } from '@/store/jobs';

interface JobMetaCardProps {
  job: Job;
}

export function JobMetaCard({ job }: JobMetaCardProps) {
  const title = job.title || job.prompt;
  const pipeline = job.pipeline?.replace(/_/g, ' ') ?? 'Standard';

  return (
    <Card className="bg-surface-1 border-border">
      <CardHeader className="pb-3 pt-4 px-4">
        <h1 className="text-base font-bold text-foreground leading-snug line-clamp-3">
          {title}
        </h1>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-3">
        {/* Status + pipeline row */}
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={job.status} />
          <Badge variant="outline" className="text-xs text-muted-foreground capitalize border-border">
            {pipeline}
          </Badge>
        </div>

        {/* Source count if available */}
        {job.artifacts?.semantic_extractions && (
          <p className="text-xs text-muted-foreground">
            {job.artifacts.semantic_extractions.length} source
            {job.artifacts.semantic_extractions.length !== 1 ? 's' : ''} analyzed
          </p>
        )}

        {/* Timestamps */}
        <div className="space-y-1 text-xs text-muted-foreground border-t border-border pt-3">
          <p>Created: {formatTimestampWithRelative(job.created_at)}</p>
          {job.stage && job.status === 'running' && (
            <p className="text-accent-green">Stage: {job.stage.replace(/_/g, ' ')}</p>
          )}
          {job.status === 'running' && job.progress_percent > 0 && (
            <p>{job.progress_percent}% complete</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
