'use client';

/**
 * JobManagementTable — admin jobs table with status filter, search, and pagination.
 * Delegates row rendering to JobRow component.
 */
import { useEffect, useState } from 'react';
import { AlertCircle, FileText } from 'lucide-react';
import { useAdminStore } from '@/store/admin';
import { JobRow } from './job-row';

export function JobManagementTable({ initialStatusFilter = '' }: { initialStatusFilter?: string }) {
  const { jobs, isLoadingJobs, jobsPage, totalJobs, pageSize, fetchJobs, cancelJob, deleteJob, error } = useAdminStore();
  const [statusFilter, setStatusFilter] = useState(initialStatusFilter);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchJobs(1, { status: statusFilter || undefined });
  }, [fetchJobs, statusFilter]);

  const totalPages = Math.ceil(totalJobs / pageSize);

  if (error && !isLoadingJobs && jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center p-6">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-foreground">Failed to load jobs</p>
        <p className="text-xs text-muted-foreground mt-1">{error}</p>
        <button
          onClick={() => fetchJobs(1, { status: statusFilter || undefined })}
          className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  const visible = search
    ? jobs.filter((j) => j.prompt.toLowerCase().includes(search.toLowerCase()) || j.user_email.includes(search))
    : jobs;

  if (isLoadingJobs && jobs.length === 0) {
    return (
      <div className="p-6 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 rounded-lg bg-muted motion-safe:animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-bold">All Jobs</h1>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search jobs…"
            aria-label="Search jobs"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-muted/40 text-xs rounded-lg px-3 py-1.5 border border-border focus:border-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-ring w-48"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
            className="bg-muted/40 text-xs rounded-lg px-3 py-1.5 border border-border cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">All Status</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {['ID', 'Title', 'User', 'Status', 'Cost', 'Created', ''].map((h) => (
                  <th key={h} className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoadingJobs ? (
                [...Array(4)].map((_, i) => (
                  <tr key={i} className="border-b border-border">
                    {[...Array(7)].map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-3 rounded bg-muted motion-safe:animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : visible.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <FileText className="h-8 w-8 text-muted-foreground/40 mb-3" />
                      <p className="text-sm text-muted-foreground">No jobs found</p>
                      <p className="text-xs text-muted-foreground/60 mt-1">Jobs will appear here when created</p>
                    </div>
                  </td>
                </tr>
              ) : (
                visible.map((job) => (
                  <JobRow
                    key={job.id}
                    job={job}
                    onCancel={() => cancelJob(job.id)}
                    onDelete={() => deleteJob(job.id)}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 p-4 border-t border-border">
            <button
              onClick={() => fetchJobs(jobsPage - 1, { status: statusFilter || undefined })}
              disabled={jobsPage === 1}
              className="text-xs px-3 py-1 rounded text-muted-foreground hover:bg-accent disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs text-muted-foreground">Page {jobsPage} of {totalPages}</span>
            <button
              onClick={() => fetchJobs(jobsPage + 1, { status: statusFilter || undefined })}
              disabled={jobsPage === totalPages}
              className="text-xs px-3 py-1 rounded text-muted-foreground hover:bg-accent disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
