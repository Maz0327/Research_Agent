'use client';

/**
 * Recent jobs list with search filter and sort controls.
 * Shows max 12 jobs with a "View all" link to /queue.
 */
import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Search } from 'lucide-react';
import { JobCardGrid } from '@/components/job/job-card-grid';
import type { Job } from '@/store/jobs';

type SortOrder = 'newest' | 'oldest';
type StatusFilter = 'all' | 'running' | 'completed';

interface RecentJobsListProps {
  jobs: Job[];
  isLoading?: boolean;
  onNewJob?: () => void;
}

export function RecentJobsList({ jobs, isLoading, onNewJob }: RecentJobsListProps) {
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

  return (
    <div className="flex flex-col gap-4">
      {/* Section header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-semibold text-[#f5f5f5]">Recent Jobs</h2>
        <div className="flex items-center gap-2">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setStatusFilter(btn.value)}
              className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
                statusFilter === btn.value
                  ? 'bg-[#1a1a25] text-[#a1a1aa] border-[#27272a]'
                  : 'text-[#71717a] border-transparent hover:bg-[#1a1a25]'
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
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#71717a]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search jobs..."
            className="w-full bg-[#1a1a25] text-sm rounded-lg pl-9 pr-3 py-1.5 border border-[#27272a] focus:border-[#3b82f6] focus:outline-none transition-colors placeholder:text-[#52525b] text-[#f5f5f5]"
          />
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOrder)}
          className="text-xs bg-[#1a1a25] border border-[#27272a] text-[#a1a1aa] rounded-lg px-2 py-1.5 focus:outline-none focus:border-[#3b82f6] transition-colors"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
        </select>
      </div>

      <JobCardGrid jobs={filtered} isLoading={isLoading} onNewJob={onNewJob} />

      {jobs.length > 12 && !search && (
        <div className="text-center">
          <Link
            href="/queue"
            className="text-xs text-[#71717a] hover:text-[#a1a1aa] transition-colors"
          >
            View all {jobs.length} jobs →
          </Link>
        </div>
      )}
    </div>
  );
}
