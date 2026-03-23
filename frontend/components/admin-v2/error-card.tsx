'use client';

/**
 * ErrorCard — single error log card with colored border, icons, and actions.
 * Critical (api_error, memory, database, auth): red border.
 * Warning (timeout, validation, external_service): orange border.
 * Retry Job: triggers job retry then resolves the error.
 * Dismiss: resolves the error without retry.
 */
import { useState } from 'react';
import { AlertCircle, AlertTriangle } from 'lucide-react';
import type { ErrorLog } from '@/store/admin';

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

interface ErrorCardProps {
  error: ErrorLog;
  /** Marks the error as resolved (dismiss). */
  onDismiss: () => Promise<void>;
  /** Retries the associated job, then marks the error resolved. */
  onRetry?: () => Promise<void>;
}

export function ErrorCard({ error, onDismiss, onRetry }: ErrorCardProps) {
  const [busyRetry, setBusyRetry] = useState(false);
  const [busyDismiss, setBusyDismiss] = useState(false);
  const critical = isCritical(error.error_category);

  const handleRetry = async () => {
    if (!onRetry) return;
    setBusyRetry(true);
    try { await onRetry(); } finally { setBusyRetry(false); }
  };

  const handleDismiss = async () => {
    setBusyDismiss(true);
    try { await onDismiss(); } finally { setBusyDismiss(false); }
  };

  const busy = busyRetry || busyDismiss;

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
            critical ? 'bg-destructive/10' : 'bg-orange-500/10'
          }`}
        >
          {critical ? (
            <AlertCircle className="w-4 h-4 text-destructive" aria-hidden="true" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-orange-400" aria-hidden="true" />
          )}
        </div>

        {/* Body */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`text-sm font-medium ${critical ? 'text-destructive' : 'text-orange-400'}`}>
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
            {!error.resolved && error.job_id && onRetry && (
              <button
                onClick={handleRetry}
                disabled={busy}
                className="text-[10px] text-primary hover:underline disabled:opacity-50 cursor-pointer"
              >
                {busyRetry ? '…' : 'Retry Job'}
              </button>
            )}
            {!error.resolved && !error.job_id && (
              <button
                onClick={handleDismiss}
                disabled={busy}
                className="text-[10px] text-primary hover:underline disabled:opacity-50 cursor-pointer"
              >
                {busyDismiss ? '…' : 'Resolve'}
              </button>
            )}
            {!error.resolved && (
              <button
                onClick={handleDismiss}
                disabled={busy}
                className="text-[10px] text-muted-foreground hover:underline disabled:opacity-50 cursor-pointer"
              >
                {busyDismiss ? '…' : 'Dismiss'}
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
