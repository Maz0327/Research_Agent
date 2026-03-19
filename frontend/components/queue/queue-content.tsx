'use client';

/**
 * Queue page — worker status cards + full table view matching mockup.
 * Workers derived from running jobs; idle slots fill remaining capacity.
 */
import { useMemo } from 'react';
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
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-xl bg-[#12121a] border border-[#27272a]" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl bg-[#12121a] border border-[#27272a]" />
    </div>
  );
}

export function QueueContent() {
  const { data: jobs = [], isLoading } = useJobs();

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

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-[#f5f5f5]">Job Queue</h1>
          <p className="text-xs text-[#71717a] mt-0.5">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 rounded-lg text-xs bg-surface-2 border border-border text-[#a1a1aa] hover:bg-surface-3 transition-colors">
            Pause Queue
          </button>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-surface-2 border border-border text-[#a1a1aa] hover:bg-surface-3 transition-colors">
            Clear Completed
          </button>
        </div>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : (
        <>
          {/* Worker status cards */}
          <div className="grid grid-cols-3 gap-3">
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
              <p className="text-sm text-[#71717a] py-10 text-center">No jobs in queue.</p>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="w-8" />
                    <th className="text-left text-[10px] font-medium text-[#71717a] uppercase tracking-wider px-4 py-3">Job</th>
                    <th className="text-left text-[10px] font-medium text-[#71717a] uppercase tracking-wider px-4 py-3">Mode</th>
                    <th className="text-left text-[10px] font-medium text-[#71717a] uppercase tracking-wider px-4 py-3">Stage</th>
                    <th className="text-left text-[10px] font-medium text-[#71717a] uppercase tracking-wider px-4 py-3">Progress</th>
                    <th className="text-left text-[10px] font-medium text-[#71717a] uppercase tracking-wider px-4 py-3">Status</th>
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
            )}
          </div>
        </>
      )}
    </div>
  );
}
