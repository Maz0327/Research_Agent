'use client';

/**
 * Responsive grid of JobCards with loading skeletons and empty state.
 * 1 col mobile → 2 col md → 3 col lg
 */
import Link from 'next/link';
import { JobCard } from './job-card';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/button';
import type { Job } from '@/store/jobs';

interface JobCardGridProps {
  jobs: Job[];
  isLoading?: boolean;
  onNewJob?: () => void;
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-32 rounded-xl bg-card border border-border" />
      ))}
    </div>
  );
}

function EmptyState({ onNewJob }: { onNewJob?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <div className="text-4xl text-muted-foreground/40">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      </div>
      <p className="text-muted-foreground text-sm">No research jobs yet</p>
      {onNewJob && (
        <button
          onClick={onNewJob}
          className="mt-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-purple-500 text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Start your first research
        </button>
      )}
    </div>
  );
}

export function JobCardGrid({ jobs, isLoading, onNewJob }: JobCardGridProps) {
  if (isLoading) return <LoadingSkeleton />;

  if (jobs.length === 0) return <EmptyState onNewJob={onNewJob} />;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
