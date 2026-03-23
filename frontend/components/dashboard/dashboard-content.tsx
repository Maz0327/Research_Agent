'use client';

/**
 * Main dashboard page orchestrator.
 * Combines DashboardStats + New Research button (wizard Dialog) + RecentJobsList.
 */
import { useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
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

export function DashboardContent() {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const { data: jobs = [], isLoading, error } = useJobs();

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
      {/* Header row */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Your research hub</p>
        </div>
        <button
          onClick={handleNewResearch}
          disabled={isNavigating}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-purple-500 text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isNavigating ? (
            <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
          ) : (
            <span className="text-base leading-none">+</span>
          )}
          New Research
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
            <DialogTitle className="text-foreground">New Research Job</DialogTitle>
          </DialogHeader>
          <JobCreationWizard onClose={() => setWizardOpen(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
