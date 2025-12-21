/**
 * Dashboard page showing job list and creation form.
 */
import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import JobCard from '../components/JobCard';
import { ProtectedRoute } from '../components/AuthProvider';
import { useJobsStore, Job } from '../store/jobs';

const pipelines = [
  { value: 'quick', label: 'Quick', description: 'Fast research with basic coverage' },
  { value: 'full', label: 'Full', description: 'Comprehensive research with full coverage' },
  { value: 'breaking_news', label: 'Breaking News', description: 'Fast-turnaround current events' },
  { value: 'investigation', label: 'Investigation', description: 'Deep-dive investigative research' },
  { value: 'profile', label: 'Profile', description: 'Character-driven biographical research' },
  { value: 'controversy', label: 'Controversy', description: 'Balanced multi-perspective analysis' },
];

function DashboardContent() {
  const [prompt, setPrompt] = useState('');
  const [pipeline, setPipeline] = useState('investigation');
  const [isCreating, setIsCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const { jobs, isLoading, createJob, refreshJob } = useJobsStore();

  // Polling for running jobs
  useEffect(() => {
    const runningJobs = jobs.filter((job) => job.status === 'running' || job.status === 'queued');
    if (runningJobs.length === 0) return;

    const interval = setInterval(() => {
      runningJobs.forEach((job) => refreshJob(job.id));
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [jobs, refreshJob]);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsCreating(true);
    try {
      await createJob(prompt, pipeline);
      setPrompt('');
    } catch (error) {
      console.error('Failed to create job:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    if (statusFilter === 'all') return true;
    return job.status === statusFilter;
  });

  return (
    <Layout>
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-gray-600">Create and manage your research jobs</p>
        </div>

        {/* Create Job Form */}
        <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-900">New Research Job</h2>
          <form onSubmit={handleCreateJob}>
            <div className="mb-4">
              <label htmlFor="prompt" className="mb-1 block text-sm font-medium text-gray-700">
                Research Topic
              </label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter your research topic or question..."
                rows={3}
                className="w-full rounded-md border border-gray-300 px-4 py-3 text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                disabled={isCreating}
              />
            </div>

            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Pipeline Mode
              </label>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {pipelines.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setPipeline(p.value)}
                    className={`rounded-lg border p-3 text-left transition ${
                      pipeline === p.value
                        ? 'border-blue-600 bg-blue-50 ring-1 ring-blue-600'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="block text-sm font-medium text-gray-900">
                      {p.label}
                    </span>
                    <span className="mt-0.5 block text-xs text-gray-500">
                      {p.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isCreating || !prompt.trim()}
              className="rounded-md bg-blue-600 px-6 py-3 font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isCreating ? 'Creating...' : 'Start Research'}
            </button>
          </form>
        </div>

        {/* Jobs List */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Your Jobs</h2>

            {/* Status Filter */}
            <div className="flex flex-wrap gap-2">
              {['all', 'running', 'completed', 'failed', 'cancelled'].map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    statusFilter === status
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <div className="py-12 text-center text-gray-500">Loading jobs...</div>
          ) : filteredJobs.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No jobs yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Create your first research job above to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredJobs.map((job) => (
                <JobCard
                  key={job.id}
                  id={job.id}
                  prompt={job.prompt}
                  pipeline={job.pipeline}
                  status={job.status}
                  progress={job.progress_percent}
                  createdAt={job.created_at}
                  artifacts={job.artifacts}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
