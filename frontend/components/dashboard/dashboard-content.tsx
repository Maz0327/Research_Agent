'use client';

/**
 * Main dashboard page orchestrator.
 * Combines DashboardStats + New Research button (wizard Dialog) + RecentJobsList.
 */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
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
  const { data: jobs = [], isLoading } = useJobs();

  return (
    <div className="flex flex-col gap-8 p-6 max-w-7xl mx-auto w-full">
      {/* Header row */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#f5f5f5]">Dashboard</h1>
          <p className="text-sm text-[#71717a] mt-0.5">Your research hub</p>
        </div>
        <button
          onClick={() => setWizardOpen(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-[#3b82f6] to-[#8b5cf6] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <span className="text-base leading-none">+</span>
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
      />

      {/* Job creation wizard dialog */}
      <Dialog open={wizardOpen} onOpenChange={setWizardOpen}>
        <DialogContent className="bg-[#12121a] border-[#27272a] max-w-lg w-full">
          <DialogHeader>
            <DialogTitle className="text-[#f5f5f5]">New Research Job</DialogTitle>
          </DialogHeader>
          <JobCreationWizard onClose={() => setWizardOpen(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
