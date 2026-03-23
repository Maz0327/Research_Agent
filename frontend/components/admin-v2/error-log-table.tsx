'use client';

/**
 * ErrorLogTable — mockup-aligned error cards with colored borders.
 * Critical errors (api_error, memory, database): red border + icon.
 * Warnings (timeout, validation, external_service): orange border + icon.
 * Each card shows: icon, title, timestamp, description, stack trace (pre), Retry Job + Dismiss.
 */
import { useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle } from 'lucide-react';
import { useAdminStore, type ErrorLog } from '@/store/admin';

const CRITICAL_CATEGORIES = new Set(['api_error', 'memory', 'database', 'auth']);

function isCritical(category: string): boolean {
  return CRITICAL_CATEGORIES.has(category);
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function ErrorCard({ error, onResolve }: { error: ErrorLog; onResolve: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const critical = isCritical(error.error_category);

  const handleResolve = async () => {
    setBusy(true);
    try { await onResolve(); } finally { setBusy(false); }
  };

  return (
    <div
      className={`bg-card rounded-xl p-4 border ${
        error.resolved
          ? 'border-border opacity-60'
          : critical
            ? 'border-red-500/20'
            : 'border-orange-500/20'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
            critical ? 'bg-red-500/10' : 'bg-orange-500/10'
          }`}
        >
          {critical ? (
            <AlertCircle className={`w-4 h-4 text-red-400`} aria-hidden="true" />
          ) : (
            <AlertTriangle className={`w-4 h-4 text-orange-400`} aria-hidden="true" />
          )}
        </div>

        {/* Body */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`text-sm font-medium ${critical ? 'text-red-400' : 'text-orange-400'}`}>
              {error.user_message}
            </h3>
            <span className="text-[10px] text-muted-foreground flex-shrink-0">
              {relativeTime(error.created_at)}
            </span>
          </div>

          <p className="text-xs text-muted-foreground mb-2">
            {error.technical_message}
            {error.stage ? ` — stage: ${error.stage}` : ''}
            {error.user_email ? ` — ${error.user_email}` : ''}
          </p>

          {error.stack_trace && (
            <pre className="text-[10px] bg-muted/40 rounded-lg p-2 text-muted-foreground overflow-x-auto mb-2 whitespace-pre-wrap break-all">
              {error.stack_trace.slice(0, 200)}{error.stack_trace.length > 200 ? '…' : ''}
            </pre>
          )}

          <div className="flex items-center gap-3">
            {!error.resolved && error.job_id && (
              <button
                onClick={handleResolve}
                disabled={busy}
                className="text-[10px] text-blue-400 hover:underline disabled:opacity-50 cursor-pointer"
              >
                {busy ? '…' : 'Retry Job'}
              </button>
            )}
            {!error.resolved && !error.job_id && (
              <button
                onClick={handleResolve}
                disabled={busy}
                className="text-[10px] text-blue-400 hover:underline disabled:opacity-50 cursor-pointer"
              >
                {busy ? '…' : 'Resolve'}
              </button>
            )}
            {!error.resolved && (
              <button
                onClick={handleResolve}
                disabled={busy}
                className="text-[10px] text-muted-foreground hover:underline disabled:opacity-50 cursor-pointer"
              >
                Dismiss
              </button>
            )}
            {error.resolved && (
              <span className="text-[10px] text-green-400">Resolved</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function ErrorLogTable({ initialResolvedFilter = '' }: { initialResolvedFilter?: string }) {
  const { errorLogs, isLoadingErrors, errorsPage, totalErrors, pageSize, fetchErrorLogs, resolveError, error } = useAdminStore();
  const [resolvedFilter, setResolvedFilter] = useState(initialResolvedFilter);

  useEffect(() => {
    const filters: { resolved?: boolean } = {};
    if (resolvedFilter) filters.resolved = resolvedFilter === 'true';
    fetchErrorLogs(1, filters);
  }, [fetchErrorLogs, resolvedFilter]);

  if (error && !isLoadingErrors && errorLogs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center p-6">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-foreground">Failed to load error logs</p>
        <p className="text-xs text-muted-foreground mt-1">{error}</p>
        <button
          onClick={() => fetchErrorLogs(1, {})}
          className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  const totalPages = Math.ceil(totalErrors / pageSize);

  if (isLoadingErrors && errorLogs.length === 0) {
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
        <h1 className="text-lg font-bold">Errors</h1>
        <div className="flex items-center gap-2">
          <select
            value={resolvedFilter}
            onChange={(e) => setResolvedFilter(e.target.value)}
            className="bg-muted/40 text-xs rounded-lg px-3 py-1.5 border border-border cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">All</option>
            <option value="false">Unresolved</option>
            <option value="true">Resolved</option>
          </select>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-muted border border-border text-muted-foreground hover:bg-accent transition-colors">
            Clear All
          </button>
        </div>
      </div>

      {/* Cards */}
      {isLoadingErrors ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-4 motion-safe:animate-pulse">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-40 rounded bg-muted" />
                  <div className="h-3 w-full rounded bg-muted" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : errorLogs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <CheckCircle className="h-8 w-8 text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground">No errors — all clear!</p>
          <p className="text-xs text-muted-foreground/60 mt-1">Error logs will appear here when issues occur</p>
        </div>
      ) : (
        <div className="space-y-3">
          {errorLogs.map((error) => (
            <ErrorCard key={error.id} error={error} onResolve={() => resolveError(error.id)} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => fetchErrorLogs(errorsPage - 1, {})}
            disabled={errorsPage === 1}
            className="text-xs px-3 py-1 rounded text-muted-foreground hover:bg-accent disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-xs text-muted-foreground">Page {errorsPage} of {totalPages}</span>
          <button
            onClick={() => fetchErrorLogs(errorsPage + 1, {})}
            disabled={errorsPage === totalPages}
            className="text-xs px-3 py-1 rounded text-muted-foreground hover:bg-accent disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
