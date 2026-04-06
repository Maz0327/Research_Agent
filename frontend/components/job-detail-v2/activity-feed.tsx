'use client';

/**
 * ActivityFeed — Timeline of job events derived from job data.
 * Shows: created, stage transitions, doc generated, iterations.
 */
import { useEffect, useRef } from 'react';
import { CheckCircle2, Clock, Loader2, XCircle, FileText, RefreshCw } from 'lucide-react';
import { formatTimestampWithRelative } from '@/lib/document-formatters';
import type { Job } from '@/store/jobs';

interface FeedEvent {
  id: string;
  icon: React.ReactNode;
  label: string;
  time?: string;
}

function buildEvents(job: Job): FeedEvent[] {
  const events: FeedEvent[] = [];

  // Job created
  events.push({
    id: 'created',
    icon: <Clock className="h-3.5 w-3.5 text-muted-foreground" />,
    label: 'Job created',
    time: job.created_at,
  });

  // Current stage (running)
  if (job.status === 'running' && job.stage) {
    events.push({
      id: 'stage',
      icon: <Loader2 className="h-3.5 w-3.5 text-accent-green animate-spin" />,
      label: `Running: ${job.stage.replace(/_/g, ' ')}`,
    });
  }

  // Docs generated
  const a = job.artifacts;
  if (a) {
    if (a.doc_0_path || a.source_ledger) {
      events.push({ id: 'doc0', icon: <FileText className="h-3.5 w-3.5 text-muted-foreground" />, label: 'Source Ledger generated' });
    }
    if (a.doc_1_path || a.jump_start) {
      events.push({ id: 'doc1', icon: <FileText className="h-3.5 w-3.5 text-blue-400" />, label: 'Jump-Start generated' });
    }
    if (a.doc_2_path || a.semantic_brief) {
      events.push({ id: 'doc2', icon: <FileText className="h-3.5 w-3.5 text-purple-400" />, label: 'Semantic Brief generated' });
    }
    if (a.doc_3_path || a.creator_brief_md) {
      events.push({ id: 'doc3', icon: <FileText className="h-3.5 w-3.5 text-amber-400" />, label: 'Creator Brief generated' });
    }
    if (a.doc_4_path || a.producer_packet_md) {
      events.push({ id: 'doc4', icon: <FileText className="h-3.5 w-3.5 text-green-400" />, label: 'Producer Packet generated' });
    }

    // Iterations
    a.iterations?.forEach((it) => {
      const label = it.status === 'completed'
        ? `Iteration ${it.index + 1} completed`
        : it.status === 'failed'
        ? `Iteration ${it.index + 1} failed`
        : `Iteration ${it.index + 1} running`;
      events.push({
        id: `iter-${it.iteration_id}`,
        icon: <RefreshCw className={`h-3.5 w-3.5 ${it.status === 'failed' ? 'text-destructive' : 'text-indigo-400'}`} />,
        label,
        time: it.completed_at ?? it.started_at,
      });
    });
  }

  // Terminal status
  if (job.status === 'completed' || job.status === 'completed_with_warnings') {
    events.push({
      id: 'done',
      icon: <CheckCircle2 className="h-3.5 w-3.5 text-accent-green" />,
      label: job.status === 'completed' ? 'Job completed' : 'Completed with warnings',
    });
  } else if (job.status === 'failed' || job.status === 'failed_insufficient') {
    events.push({
      id: 'failed',
      icon: <XCircle className="h-3.5 w-3.5 text-destructive" />,
      label: job.error ?? 'Job failed',
    });
  }

  return events;
}

interface ActivityFeedProps {
  job: Job;
}

export function ActivityFeed({ job }: ActivityFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const events = buildEvents(job);

  // Auto-scroll to latest event
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Activity
      </p>
      <ol className="space-y-3">
        {events.map((ev) => (
          <li key={ev.id} className="flex items-start gap-2.5">
            <span className="flex-shrink-0 mt-0.5">{ev.icon}</span>
            <div className="min-w-0">
              <p className="text-xs text-foreground leading-snug">{ev.label}</p>
              {ev.time && (
                <p className="text-caption text-muted-foreground mt-0.5">
                  {formatTimestampWithRelative(ev.time)}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
      <div ref={bottomRef} />
    </div>
  );
}
