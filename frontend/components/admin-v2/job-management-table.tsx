'use client';

/**
 * JobManagementTable — mockup-aligned jobs table with status badges and action buttons.
 * Columns: ID (mono) | Title | User | Status | Cost | Created | Action (Cancel/Delete/Retry)
 */
import { useEffect, useState } from 'react';
import { AlertCircle, FileText } from 'lucide-react';
import { useAdminStore, type AdminJob } from '@/store/admin';

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  queued:                  { label: 'Queued',     className: 'bg-zinc-700/40 text-zinc-300' },
  running:                 { label: 'Running',    className: 'bg-green-500/10 text-green-400' },
  completed:               { label: 'Completed',  className: 'bg-blue-500/10 text-blue-400' },
  completed_with_warnings: { label: 'Completed',  className: 'bg-blue-500/10 text-blue-400' },
  failed:                  { label: 'Failed',     className: 'bg-red-500/10 text-red-400' },
  failed_insufficient:     { label: 'Failed',     className: 'bg-red-500/10 text-red-400' },
  cancelled:               { label: 'Cancelled',  className: 'bg-zinc-700/40 text-zinc-400' },
};

function actionLabel(status: string) {
  if (status === 'running' || status === 'queued') return 'cancel';
  if (status === 'failed' || status === 'failed_insufficient') return 'retry';
  return 'delete';
}

function JobRow({ job, onCancel, onDelete }: { job: AdminJob; onCancel: () => Promise<void>; onDelete: () => Promise<void> }) {
  const [busy, setBusy] = useState<string | null>(null);
  const cfg = STATUS_CONFIG[job.status] ?? STATUS_CONFIG.queued;
  const act = actionLabel(job.status);

  const run = async (fn: () => Promise<void>, key: string) => {
    if (act === 'delete' && !confirm('Delete this job?')) return;
    setBusy(key);
    try { await fn(); } finally { setBusy(null); }
  };

  // Short ID like j_8a3f
  const shortId = 'j_' + job.id.replace(/-/g, '').slice(0, 4);
  const title = job.prompt.length > 40 ? job.prompt.slice(0, 40) + '…' : job.prompt;
  const userShort = job.user_email.length > 12 ? job.user_email.slice(0, 10) + '…' : job.user_email;
  const created = (() => {
    const diff = Date.now() - new Date(job.created_at).getTime();
    const h = Math.floor(diff / 3600000);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  })();

  return (
    <tr className="border-b border-border hover:bg-accent/30 transition-colors cursor-pointer">
      <td className="px-4 py-3 text-[11px] font-mono text-muted-foreground">{shortId}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground max-w-[200px] truncate">{title}</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">{userShort}</td>
      <td className="px-4 py-3">
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${cfg.className}`}>
          {cfg.label}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">—</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">{created}</td>
      <td className="px-4 py-3">
        {act === 'cancel' && (
          <button
            onClick={() => run(onCancel, 'cancel')}
            disabled={busy !== null}
            className="text-[10px] text-muted-foreground hover:text-red-400 transition-colors disabled:opacity-50"
          >
            {busy === 'cancel' ? '…' : 'Cancel'}
          </button>
        )}
        {act === 'delete' && (
          <button
            onClick={() => run(onDelete, 'delete')}
            disabled={busy !== null}
            className="text-[10px] text-muted-foreground hover:text-red-400 transition-colors disabled:opacity-50"
          >
            {busy === 'delete' ? '…' : 'Delete'}
          </button>
        )}
        {act === 'retry' && (
          <button
            disabled
            className="text-[10px] text-blue-400 opacity-70 cursor-not-allowed"
          >
            Retry
          </button>
        )}
      </td>
    </tr>
  );
}

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
            className="bg-muted/40 text-xs rounded-lg px-3 py-1.5 border border-border focus:border-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring w-48"
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
