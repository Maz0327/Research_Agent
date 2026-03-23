'use client';

/**
 * Recent jobs list with search filter and sort controls.
 * Shows max 12 jobs with a "View all" link to /queue.
 * Uses DashboardJobCard (polished mockup-style cards).
 */
import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Search, AlertCircle } from 'lucide-react';
import { DashboardJobCard } from '@/components/dashboard/DashboardJobCard';
import { Skeleton } from '@/components/ui/Skeleton';
import type { Job } from '@/store/jobs';

type SortOrder = 'newest' | 'oldest';
type StatusFilter = 'all' | 'running' | 'completed';

interface RecentJobsListProps {
  jobs: Job[];
  isLoading?: boolean;
  onNewJob?: () => void;
  error?: Error | null;
}

export function RecentJobsList({ jobs, isLoading, onNewJob, error }: RecentJobsListProps) {
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortOrder>('newest');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const filtered = useMemo(() => {
    let result = [...jobs];
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((j) => (j.title || j.prompt).toLowerCase().includes(q));
    }
    if (statusFilter === 'running') {
      result = result.filter((j) => j.status === 'running');
    } else if (statusFilter === 'completed') {
      result = result.filter(
        (j) => j.status === 'completed' || j.status === 'completed_with_warnings'
      );
    }
    result.sort((a, b) => {
      const diff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      return sort === 'newest' ? diff : -diff;
    });
    return result.slice(0, 12);
  }, [jobs, search, sort, statusFilter]);

  const filterButtons: { label: string; value: StatusFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'Running', value: 'running' },
    { label: 'Completed', value: 'completed' },
  ];

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-foreground">Failed to load jobs</p>
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
    <div className="flex flex-col gap-4">
      {/* Section header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-semibold text-foreground">Recent Jobs</h2>
        <div className="flex items-center gap-2">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setStatusFilter(btn.value)}
              className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
                statusFilter === btn.value
                  ? 'bg-secondary text-muted-foreground border-border'
                  : 'text-muted-foreground border-transparent hover:bg-secondary'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search + sort bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search jobs..."
            aria-label="Search jobs"
            className="w-full bg-secondary text-sm rounded-lg pl-9 pr-3 py-1.5 border border-border focus:border-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors placeholder:text-muted-foreground/60 text-foreground"
          />
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOrder)}
          aria-label="Sort jobs"
          className="text-xs bg-secondary border border-border text-muted-foreground rounded-lg px-2 py-1.5 focus:outline-none focus:border-primary focus-visible:ring-2 focus-visible:ring-ring transition-colors"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
        </select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl bg-card border border-border" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
          <p className="text-muted-foreground text-sm">No jobs found</p>
          {onNewJob && jobs.length === 0 && (
            <button
              onClick={onNewJob}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-purple-500 text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Start your first research
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((job) => (
            <DashboardJobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {jobs.length > 12 && !search && (
        <div className="text-center">
          <Link
            href="/queue"
            className="text-xs text-muted-foreground hover:text-muted-foreground transition-colors"
          >
            View all {jobs.length} jobs →
          </Link>
        </div>
      )}
    </div>
  );
}
