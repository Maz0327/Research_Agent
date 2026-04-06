'use client';

/**
 * JobRow — single row in the admin job management table.
 * Shows: short ID, title, user, status badge, cost, created time, action button.
 * Actions: Cancel (running/queued), Delete (completed/cancelled), Retry (failed — disabled).
 */
import { useState } from 'react';
import type { AdminJob } from '@/store/admin';

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  queued:                  { label: 'Queued',     className: 'bg-muted text-muted-foreground' },
  running:                 { label: 'Running',    className: 'bg-green-500/10 text-green-400' },
  completed:               { label: 'Completed',  className: 'bg-primary/10 text-primary' },
  completed_with_warnings: { label: 'Completed',  className: 'bg-primary/10 text-primary' },
  failed:                  { label: 'Failed',     className: 'bg-destructive/10 text-destructive' },
  failed_insufficient:     { label: 'Failed',     className: 'bg-destructive/10 text-destructive' },
  cancelled:               { label: 'Cancelled',  className: 'bg-muted text-muted-foreground' },
};

function actionLabel(status: string) {
  if (status === 'running' || status === 'queued') return 'cancel';
  if (status === 'failed' || status === 'failed_insufficient') return 'retry';
  return 'delete';
}

interface JobRowProps {
  job: AdminJob;
  onCancel: () => Promise<void>;
  onDelete: () => Promise<void>;
}

export function JobRow({ job, onCancel, onDelete }: JobRowProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const cfg = STATUS_CONFIG[job.status] ?? STATUS_CONFIG.queued;
  const act = actionLabel(job.status);

  const run = async (fn: () => Promise<void>, key: string) => {
    if (act === 'delete' && !confirm('Delete this job?')) return;
    setBusy(key);
    try { await fn(); } finally { setBusy(null); }
  };

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
      <td className="px-4 py-3 text-caption font-mono text-muted-foreground">{shortId}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground max-w-[200px] truncate">{title}</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">{userShort}</td>
      <td className="px-4 py-3">
        <span className={`text-caption px-1.5 py-0.5 rounded font-medium ${cfg.className}`}>
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
            className="text-caption text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
          >
            {busy === 'cancel' ? '…' : 'Cancel'}
          </button>
        )}
        {act === 'delete' && (
          <button
            onClick={() => run(onDelete, 'delete')}
            disabled={busy !== null}
            className="text-caption text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
          >
            {busy === 'delete' ? '…' : 'Delete'}
          </button>
        )}
        {act === 'retry' && (
          <button
            disabled
            className="text-caption text-primary opacity-70 cursor-not-allowed"
          >
            Retry
          </button>
        )}
      </td>
    </tr>
  );
}
