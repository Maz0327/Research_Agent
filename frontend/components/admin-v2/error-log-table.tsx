'use client';

/**
 * ErrorLogTable — renders error log cards with filter and pagination.
 * Delegates card rendering to ErrorCard component.
 */
import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { useAdminStore } from '@/store/admin';
import { ErrorCard } from './error-card';

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
          {errorLogs.map((errorItem) => (
            <ErrorCard
              key={errorItem.id}
              error={errorItem}
              onDismiss={() => resolveError(errorItem.id)}
              onRetry={errorItem.job_id ? () => resolveError(errorItem.id) : undefined}
            />
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
