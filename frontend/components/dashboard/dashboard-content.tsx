'use client';

/**
 * Main dashboard page orchestrator.
 * Combines DashboardStats + New Research button (wizard Dialog) + RecentJobsList.
 */
import { useState, useRef, useEffect } from 'react';
import { AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { DashboardStats } from './dashboard-stats';
import { RecentJobsList } from './recent-jobs-list';
import { JobCreationWizard } from './job-creation-wizard';
import { useJobs } from '@/hooks/use-jobs';
import type { Job } from '@/store/jobs';

/** Inline completion banner — dismisses automatically after 5s. */
function CompletionBanner({ job, onDismiss }: { job: Job; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 5000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  const docCount = (job as Job & { document_count?: number }).document_count;
  const label = job.title || job.prompt?.slice(0, 60) || 'Research';

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 px-4 py-3 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm animate-in fade-in slide-in-from-top-2 duration-300"
    >
      <CheckCircle2 className="h-4 w-4 shrink-0" />
      <span className="flex-1 truncate">
        <span className="font-medium">Research complete</span>
        {' — '}{label}
        {docCount ? ` · ${docCount} documents ready` : ''}
      </span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
      >
        ×
      </button>
    </div>
  );
}

export function DashboardContent() {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [completedJob, setCompletedJob] = useState<Job | null>(null);
  const prevStatusMap = useRef<Map<string, string>>(new Map());
  const { data: jobs = [], isLoading, error } = useJobs();

  // Detect newly-completed jobs across poll cycles
  useEffect(() => {
    if (!jobs.length) return;
    for (const job of jobs) {
      const prev = prevStatusMap.current.get(job.id);
      if (
        prev &&
        prev !== 'completed' &&
        prev !== 'completed_with_warnings' &&
        (job.status === 'completed' || job.status === 'completed_with_warnings')
      ) {
        setCompletedJob(job);
      }
      prevStatusMap.current.set(job.id, job.status);
    }
  }, [jobs]);

  const handleNewResearch = () => {
    setIsNavigating(true);
    setWizardOpen(true);
    // Reset after dialog opens
    setTimeout(() => setIsNavigating(false), 300);
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center p-6">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-foreground">Failed to load data</p>
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
    <div className="flex flex-col gap-8 p-6 max-w-7xl mx-auto w-full">
      {/* Job completion banner */}
      {completedJob && (
        <CompletionBanner
          job={completedJob}
          onDismiss={() => setCompletedJob(null)}
        />
      )}

      {/* Header row */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Your Projects</h1>
        </div>
        <button
          onClick={handleNewResearch}
          disabled={isNavigating}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-purple-500 text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
        >
          {isNavigating ? (
            <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
          ) : (
            <span className="text-base leading-none">+</span>
          )}
          New Project
        </button>
      </div>

      {/* Stats */}
      <DashboardStats />

      {/* Recent jobs */}
      <RecentJobsList
        jobs={jobs}
        isLoading={isLoading}
        onNewJob={() => setWizardOpen(true)}
        error={error}
      />

      {/* Job creation wizard dialog */}
      <Dialog open={wizardOpen} onOpenChange={setWizardOpen}>
        <DialogContent className="bg-card border-border max-w-lg w-full">
          <DialogHeader>
            <DialogTitle className="text-foreground">New Project</DialogTitle>
          </DialogHeader>
          <JobCreationWizard onClose={() => setWizardOpen(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
