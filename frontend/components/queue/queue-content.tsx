'use client';

/**
 * Queue page — worker status cards + full table view matching mockup.
 * Workers derived from running jobs; idle slots fill remaining capacity.
 */
import { useMemo, useState } from 'react';
import { AlertCircle, FileText, Loader2 } from 'lucide-react';
import { Skeleton } from '@/components/ui/Skeleton';
import { WorkerCard } from './queue-worker-card';
import { QueueTableRow } from './queue-table-row';
import { useJobs } from '@/hooks/use-jobs';
import type { Job } from '@/store/jobs';

const WORKER_SLOTS = 3;

const DONE = new Set(['completed', 'completed_with_warnings']);
const FAILED = new Set(['failed', 'failed_insufficient', 'cancelled']);

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-xl bg-card border border-border" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl bg-card border border-border" />
    </div>
  );
}

export function QueueContent() {
  const { data: jobs = [], isLoading, error } = useJobs();
  const [isPausing, setIsPausing] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  const { running, queued, completed, runningCount, queuedCount, idleWorkers } = useMemo(() => {
    const running = jobs.filter((j) => j.status === 'running');
    const queued = jobs.filter((j) => j.status === 'queued');
    const completed = jobs.filter((j) => DONE.has(j.status));
    const idleWorkers = Math.max(0, WORKER_SLOTS - running.length);
    return { running, queued, completed, runningCount: running.length, queuedCount: queued.length, idleWorkers };
  }, [jobs]);

  // Table shows: running + queued + recent completed (max 5) — failed/cancelled omitted
  const tableJobs: Job[] = useMemo(() => [
    ...running,
    ...queued,
    ...completed.slice(0, 5),
  ], [running, queued, completed]);

  const subtitle = [
    runningCount > 0 && `${runningCount} running`,
    queuedCount > 0 && `${queuedCount} queued`,
    idleWorkers > 0 && `${idleWorkers} worker${idleWorkers > 1 ? 's' : ''} available`,
  ].filter(Boolean).join(' · ') || 'No active jobs';

  const handlePause = async () => {
    setIsPausing(true);
    try {
      // Pause queue action — placeholder for API call
      await new Promise((resolve) => setTimeout(resolve, 500));
    } finally {
      setIsPausing(false);
    }
  };

  const handleClearCompleted = async () => {
    setIsClearing(true);
    try {
      // Clear completed action — placeholder for API call
      await new Promise((resolve) => setTimeout(resolve, 500));
    } finally {
      setIsClearing(false);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center p-6">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-foreground">Failed to load queue</p>
        <p className="text-xs text-muted-foreground mt-1">{error.message || 'Something went wrong'}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-foreground">Job Queue</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePause}
            disabled={isPausing || isClearing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-surface-2 border border-border text-muted-foreground hover:bg-surface-3 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPausing ? (
              <><Loader2 className="h-3 w-3 motion-safe:animate-spin" /> Pausing...</>
            ) : (
              'Pause Queue'
            )}
          </button>
          <button
            onClick={handleClearCompleted}
            disabled={isPausing || isClearing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-surface-2 border border-border text-muted-foreground hover:bg-surface-3 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isClearing ? (
              <><Loader2 className="h-3 w-3 motion-safe:animate-spin" /> Clearing...</>
            ) : (
              'Clear Completed'
            )}
          </button>
        </div>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : (
        <>
          {/* Worker status cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {running.map((job) => (
              <WorkerCard
                key={job.id}
                name={`Worker ${running.indexOf(job) + 1}`}
                jobTitle={job.title || job.prompt}
                progress={job.progress_percent}
              />
            ))}
            {Array.from({ length: idleWorkers }).map((_, i) => (
              <WorkerCard
                key={`idle-${i}`}
                name={`Worker ${running.length + i + 1}`}
                idle
              />
            ))}
          </div>

          {/* Queue table */}
          <div className="bg-surface-1 border border-border rounded-xl overflow-hidden">
            {tableJobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="h-8 w-8 text-muted-foreground/40 mb-3" />
                <p className="text-sm text-muted-foreground">No jobs in queue</p>
                <p className="text-xs text-muted-foreground/60 mt-1">Jobs will appear here when created</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="w-8" />
                    <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Job</th>
                    <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Mode</th>
                    <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Stage</th>
                    <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Progress</th>
                    <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Status</th>
                    <th className="w-10" />
                  </tr>
                </thead>
                <tbody>
                  {tableJobs.map((job) => {
                    const queuePos = queued.indexOf(job);
                    return (
                      <QueueTableRow
                        key={job.id}
                        job={job}
                        queuePosition={queuePos >= 0 ? queuePos + 1 : undefined}
                      />
                    );
                  })}
                </tbody>
              </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
