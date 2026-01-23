/**
 * Queue Page - Dedicated view for running and queued jobs.
 * ADHD-friendly: Shows only active jobs with clear status indicators.
 */
import { useEffect, useMemo, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { ProtectedRoute } from '../components/AuthProvider';
import { useJobsStore, type Job } from '../store/jobs';
import { POLLING_INTERVALS } from '../lib/constants';

/** Status badge component */
function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: 'bg-blue-500 animate-pulse',
    queued: 'bg-yellow-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };
  return (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${colors[status] || 'bg-gray-500'}`} />
  );
}

/** Format relative time */
function formatRelativeTime(dateString?: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/** Queue item card */
function QueueItem({ job, position }: { job: Job; position: number }) {
  const router = useRouter();
  const stageDescription = job.pass_detail || job.stage || 'Processing...';
  const progress = job.progress_percent || 0;

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className="group relative flex items-center gap-4 p-4 bg-[#1a1a1a] rounded-xl border border-gray-800 hover:border-gray-700 cursor-pointer transition-all"
    >
      {/* Position indicator */}
      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center text-gray-400 font-mono text-sm">
        #{position}
      </div>

      {/* Job info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <StatusDot status={job.status} />
          <h3 className="text-white font-medium truncate">{job.title || 'Untitled Job'}</h3>
        </div>
        <p className="text-sm text-gray-400 truncate">{stageDescription}</p>

        {/* Progress bar for running jobs */}
        {job.status === 'running' && (
          <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Time info */}
      <div className="flex-shrink-0 text-right text-sm">
        <span className="text-gray-500">{formatRelativeTime(job.stage_started_at || job.created_at)}</span>
      </div>

      {/* Hover arrow */}
      <svg
        className="flex-shrink-0 h-5 w-5 text-gray-600 group-hover:text-gray-400 transition-colors"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  );
}

function QueueContent() {
  const { jobs, fetchJobs, refreshJob } = useJobsStore();
  const [isLoading, setIsLoading] = useState(true);

  // Filter to active jobs only
  const activeJobs = useMemo(() => {
    return jobs
      .filter((job) => job.status === 'running' || job.status === 'queued')
      .sort((a, b) => {
        // Running jobs first, then by created_at
        if (a.status === 'running' && b.status !== 'running') return -1;
        if (b.status === 'running' && a.status !== 'running') return 1;
        return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      });
  }, [jobs]);

  // Running and queued counts
  const runningCount = activeJobs.filter((j) => j.status === 'running').length;
  const queuedCount = activeJobs.filter((j) => j.status === 'queued').length;

  // Initial fetch
  useEffect(() => {
    fetchJobs().finally(() => setIsLoading(false));
  }, [fetchJobs]);

  // Poll active jobs
  useEffect(() => {
    if (activeJobs.length === 0) return;

    const interval = setInterval(() => {
      activeJobs.forEach((job) => {
        refreshJob(job.id);
      });
    }, POLLING_INTERVALS.JOB_STATUS);

    return () => clearInterval(interval);
  }, [activeJobs, refreshJob]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">Jobs Queue</h1>
        <p className="text-gray-400">
          {activeJobs.length === 0
            ? 'No active jobs. Start a new research from the dashboard.'
            : `${runningCount} running, ${queuedCount} queued`}
        </p>
      </div>

      {/* Empty state */}
      {activeJobs.length === 0 && (
        <div className="text-center py-16 bg-[#1a1a1a] rounded-xl border border-gray-800">
          <svg
            className="mx-auto h-12 w-12 text-gray-600 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
            />
          </svg>
          <p className="text-gray-400 mb-4">Queue is empty</p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Start New Research
          </Link>
        </div>
      )}

      {/* Active jobs list */}
      {activeJobs.length > 0 && (
        <div className="space-y-3">
          {/* Running jobs section */}
          {runningCount > 0 && (
            <>
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                Running ({runningCount})
              </h2>
              {activeJobs
                .filter((j) => j.status === 'running')
                .map((job, idx) => (
                  <QueueItem key={job.id} job={job} position={idx + 1} />
                ))}
            </>
          )}

          {/* Queued jobs section */}
          {queuedCount > 0 && (
            <>
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mt-6 mb-2">
                Queued ({queuedCount})
              </h2>
              {activeJobs
                .filter((j) => j.status === 'queued')
                .map((job, idx) => (
                  <QueueItem key={job.id} job={job} position={runningCount + idx + 1} />
                ))}
            </>
          )}
        </div>
      )}

      {/* Link back to dashboard */}
      <div className="mt-8 text-center">
        <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-400 transition-colors">
          View all jobs on Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function QueuePage() {
  return (
    <ProtectedRoute>
      <Layout>
        <Head>
          <title>Jobs Queue | Research Agent</title>
        </Head>
        <QueueContent />
      </Layout>
    </ProtectedRoute>
  );
}
