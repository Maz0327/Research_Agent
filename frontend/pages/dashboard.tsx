/**
 * Dashboard page showing job list and creation form.
 * Features dark mode design with modern UI/UX.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import { useJobsStore, JobPreview, VideoAnalysisResponse, TextInputRequest, TextInputResponse, ScreenshotInputResponse, MixedInputRequest, MixedInputResponse, MixedTextInput } from '../store/jobs';
import { useUIPreferences } from '../store/ui-preferences';
import { POLLING_INTERVALS, VALIDATION_LIMITS, PLATFORM_HINTS, SCREENSHOT_PLATFORM_HINTS } from '../lib/constants';
import { UnifiedInputPanel } from '../components/unified-input';
import { FloatingActionButton } from '../components/ui/FloatingActionButton';
import { DashboardJobCard } from '../components/dashboard/DashboardJobCard';

// Job creation modes: 'research' (unified multi-source) or 'quick' (simple video)
type JobMode = 'research' | 'quick';

// Research depth options (mode)
const researchDepths = [
  { value: 'quick', label: 'Quick Brief', description: 'Fast, surface-level coverage', example: 'What is quantum computing?' },
  { value: 'breaking_news', label: 'Breaking News', description: 'Recent events, fast turnaround', example: 'OpenAI leadership changes December 2024' },
  { value: 'full', label: 'Standard Research', description: 'Balanced depth and coverage', example: 'Electric vehicle market trends 2024' },
  { value: 'investigation', label: 'Deep Investigation', description: 'Thorough verification, multiple sources', example: 'FTX collapse timeline and key players' },
  { value: 'profile', label: 'Entity Profile', description: 'Single person/company focus', example: 'Elon Musk business ventures and controversies' },
];

// Category options (niche) - affects sources, subreddits, search queries
const categories = [
  { value: '', label: 'Auto-detect', description: 'AI determines best category' },
  { value: 'pop_culture', label: 'Entertainment & Pop Culture', description: 'TV, movies, celebrities, fan theories' },
  { value: 'political', label: 'Politics & Policy', description: 'Government, elections, legislation' },
  { value: 'true_crime', label: 'True Crime & Legal', description: 'Cases, investigations, court proceedings' },
  { value: 'mysteries', label: 'Mysteries & Conspiracies', description: 'Evidence analysis, theories, debunking' },
  { value: 'downfalls', label: 'Scandals & Downfalls', description: 'Drama, public reactions, timelines' },
  { value: 'controversy', label: 'Controversy', description: 'Multiple perspectives, balanced views' },
];

// Skeleton loader for jobs
function JobSkeleton() {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="h-5 w-3/4 rounded bg-gray-800" />
          <div className="mt-2 flex gap-2">
            <div className="h-4 w-20 rounded bg-gray-800" />
            <div className="h-4 w-24 rounded bg-gray-800" />
          </div>
        </div>
        <div className="h-6 w-20 rounded-full bg-gray-800" />
      </div>
    </div>
  );
}

// Available source types
const availableSourceTypes = ['web', 'news', 'youtube', 'reddit'];

function DashboardContent() {
  // Job creation mode: 'research' (unified multi-source) or 'quick' (simple video)
  const [jobMode, setJobMode] = useState<JobMode>('research');

  // Quick Video state (simple video analysis)
  const [videoUrls, setVideoUrls] = useState('');
  const [videoTitle, setVideoTitle] = useState('');
  const [geminiModel, setGeminiModel] = useState<'gemini-2.5-flash' | 'gemini-2.5-pro'>('gemini-2.5-flash');
  const [isVideoSubmitting, setIsVideoSubmitting] = useState(false);

  // Unified input state
  const [isMixedSubmitting, setIsMixedSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Topic Research state (LEGACY - kept for backward compatibility)
  const [prompt, setPrompt] = useState('');
  const [researchDepth, setResearchDepth] = useState('investigation');
  const [category, setCategory] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  // Editable preview state
  const [editableSources, setEditableSources] = useState<string[]>([]);
  const [editableSubreddits, setEditableSubreddits] = useState<string[]>([]);
  const [newSubreddit, setNewSubreddit] = useState('');
  const {
    jobs, isLoading, preview, isPreviewLoading, fetchJobs, previewJob, createJob, createVideoAnalysisJob, createMixedInputJob, refreshJob, clearPreview,
  } = useJobsStore();
  const { user } = useAuth();
  const { createPanelCollapsed, toggleCreatePanel } = useUIPreferences();

  // Get current depth config for placeholder example
  const currentDepth = researchDepths.find(d => d.value === researchDepth) || researchDepths[3];

  // Fetch jobs on mount and when user changes
  useEffect(() => {
    if (user) {
      fetchJobs();
    }
  }, [fetchJobs, user]);

  // Debounced batch refresh for running jobs
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const batchRefreshJobs = useCallback((jobIds: string[]) => {
    // Clear any pending refresh
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }
    // Debounce the batch refresh
    refreshTimeoutRef.current = setTimeout(() => {
      jobIds.forEach((id) => refreshJob(id));
    }, 100); // 100ms debounce to batch rapid updates
  }, [refreshJob]);

  // Polling for running jobs (including secondary tasks like booster/producer/iteration)
  useEffect(() => {
    const jobsNeedingPolling = jobs.filter((job) =>
      job.status === 'running' ||
      job.status === 'queued' ||
      job.booster_status === 'running' ||
      job.booster_status === 'queued' ||
      job.producer_status === 'running' ||
      job.producer_status === 'queued' ||
      job.iteration_status === 'running' ||
      job.iteration_status === 'queued'
    );
    if (jobsNeedingPolling.length === 0) return;

    const interval = setInterval(() => {
      batchRefreshJobs(jobsNeedingPolling.map((job) => job.id));
    }, POLLING_INTERVALS.JOB_STATUS);

    return () => {
      clearInterval(interval);
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [jobs, batchRefreshJobs]);

  // Step 1: Preview the job before creating
  const handlePreviewJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    try {
      const result = await previewJob(prompt, researchDepth, category || undefined);
      // Initialize editable state from preview
      setEditableSources(result.source_types || ['web', 'news', 'youtube', 'reddit']);
      setEditableSubreddits(result.subreddits || []);
      setNewSubreddit('');
      setShowPreview(true);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to preview job:', error);
      }
    }
  };

  // Toggle a source type
  const toggleSource = (source: string) => {
    setEditableSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  // Add a subreddit
  const addSubreddit = () => {
    const cleaned = newSubreddit.trim().toLowerCase().replace(/^r\//, '');
    if (cleaned && !editableSubreddits.includes(cleaned)) {
      setEditableSubreddits(prev => [...prev, cleaned]);
      setNewSubreddit('');
    }
  };

  // Remove a subreddit
  const removeSubreddit = (sub: string) => {
    setEditableSubreddits(prev => prev.filter(s => s !== sub));
  };

  // Step 2: Confirm and create the job
  const handleConfirmJob = async () => {
    setIsCreating(true);
    try {
      // Pass custom subreddits if user modified them
      const options = editableSubreddits.length > 0 ? { custom_subreddits: editableSubreddits } : undefined;
      await createJob(prompt, researchDepth, category || undefined, options);
      setPrompt('');
      setShowPreview(false);
      clearPreview();
      setEditableSources([]);
      setEditableSubreddits([]);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create job:', error);
      }
    } finally {
      setIsCreating(false);
    }
  };

  // Cancel preview and go back to editing
  const handleCancelPreview = () => {
    setShowPreview(false);
    clearPreview();
  };

  // Parse video URLs from textarea (one per line or comma-separated)
  const parseVideoUrls = (text: string): string[] => {
    return text
      .split(/[\n,]/)
      .map((url) => url.trim())
      .filter((url) => url.length > 0 && (url.includes('youtube.com') || url.includes('youtu.be')));
  };

  // Video Analysis submission
  const handleVideoAnalysisSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const urls = parseVideoUrls(videoUrls);

    if (urls.length === 0) {
      return;
    }

    if (urls.length > 10) {
      alert('Maximum 10 videos per job. Please reduce the number of URLs.');
      return;
    }

    setIsVideoSubmitting(true);
    try {
      await createVideoAnalysisJob(urls, videoTitle || undefined, geminiModel);
      // Clear form on success
      setVideoUrls('');
      setVideoTitle('');
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create video analysis job:', error);
      }
    } finally {
      setIsVideoSubmitting(false);
    }
  };

  // Count valid URLs for display
  const validUrlCount = parseVideoUrls(videoUrls).length;

  // Mixed Input (Unified Panel) submission
  const handleMixedInputSubmit = async (data: {
    topic: string;
    videoUrls: string[];
    articleUrls: string[];
    textInputs: { title: string; content: string; platform_hint?: string }[];
    screenshots: { filename: string; base64: string; platformHint: string }[];
  }) => {
    setSubmitError(null);
    setIsMixedSubmitting(true);
    try {
      const request: MixedInputRequest = {
        topic: data.topic,
        video_urls: data.videoUrls.length > 0 ? data.videoUrls : undefined,
        article_urls: data.articleUrls.length > 0 ? data.articleUrls : undefined,
        text_inputs: data.textInputs.length > 0 ? data.textInputs : undefined,
        screenshots: data.screenshots.length > 0 ? data.screenshots.map(s => ({
          filename: s.filename,
          base64: s.base64,
          platform_hint: s.platformHint,
        })) : undefined,
      };
      await createMixedInputJob(request);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to create job');
    } finally {
      setIsMixedSubmitting(false);
    }
  };

  // Get 5 most recent jobs for dashboard preview
  const recentJobs = useMemo(() => {
    return [...jobs]
      .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
      .slice(0, 5);
  }, [jobs]);

  // Count active jobs
  const activeJobsCount = useMemo(() => {
    return jobs.filter((job) => job.status === 'running' || job.status === 'queued').length;
  }, [jobs]);

  return (
    <Layout>
      {/* Responsive container with mobile-friendly padding */}
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-0">
        {/* Header - responsive text */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 sm:mb-8"
        >
          <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="mt-1.5 sm:mt-2 text-sm sm:text-base text-gray-400">Create and manage your research jobs</p>
        </motion.div>

        {/* Create Job Form - Collapsible Panel */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6 sm:mb-8 rounded-xl border border-gray-800 bg-gray-900 shadow-lg overflow-hidden"
        >
          {/* Collapsible Header */}
          <button
            onClick={toggleCreatePanel}
            className="w-full flex items-center justify-between p-4 sm:p-6 hover:bg-gray-800/50 transition-colors touch-manipulation"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-purple-600">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div className="text-left">
                <h2 className="text-base sm:text-lg font-semibold text-gray-100">New Research Job</h2>
                <p className="text-xs sm:text-sm text-gray-500">
                  {createPanelCollapsed ? 'Click to expand and create a new job' : 'Analyze videos, articles, and text'}
                </p>
              </div>
            </div>
            <motion.svg
              animate={{ rotate: createPanelCollapsed ? 0 : 180 }}
              transition={{ duration: 0.2 }}
              className="h-5 w-5 text-gray-500 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </motion.svg>
          </button>

          {/* Collapsible Content */}
          <AnimatePresence initial={false}>
            {!createPanelCollapsed && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: 'easeInOut' }}
                className="overflow-hidden"
              >
                <div className="px-4 sm:px-6 pb-4 sm:pb-6 border-t border-gray-800">
                  {/* Mode Toggle - responsive layout */}
                  <div className="pt-4 sm:pt-5 mb-5 sm:mb-6 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                    {/* Toggle buttons - full width on mobile */}
                    <div className="flex rounded-lg bg-gray-800 p-1 w-full sm:w-auto">
                      <button
                        type="button"
                        onClick={() => setJobMode('research')}
                        className={`flex-1 sm:flex-none px-4 py-2 sm:py-1.5 text-sm font-medium rounded-md transition-all touch-manipulation ${
                          jobMode === 'research'
                            ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                      >
                        Research
                      </button>
                      <button
                        type="button"
                        onClick={() => setJobMode('quick')}
                        className={`flex-1 sm:flex-none px-4 py-2 sm:py-1.5 text-sm font-medium rounded-md transition-all touch-manipulation ${
                          jobMode === 'quick'
                            ? 'bg-purple-600 text-white shadow-lg'
                            : 'text-gray-400 hover:text-gray-300'
                        }`}
                      >
                        Quick Video
                      </button>
                    </div>
                  </div>

          <AnimatePresence mode="wait">
            {/* RESEARCH MODE (Unified Multi-Source) */}
            {jobMode === 'research' ? (
              <motion.div
                key="research-form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <UnifiedInputPanel
                  onSubmit={handleMixedInputSubmit}
                  isSubmitting={isMixedSubmitting}
                />
                {submitError && (
                  <div className="mt-4 rounded-lg border border-red-700 bg-red-900/30 p-3 flex items-center justify-between">
                    <p className="text-sm text-red-300">{submitError}</p>
                    <button
                      onClick={() => setSubmitError(null)}
                      className="text-red-400 hover:text-red-300 text-sm ml-4"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
              </motion.div>
            ) : jobMode === 'quick' ? (
              <motion.form
                key="video-form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleVideoAnalysisSubmit}
              >
                <div className="mb-4">
                  <label htmlFor="videoUrls" className="mb-1.5 block text-sm font-medium text-gray-400">
                    YouTube Video URLs
                    {validUrlCount > 0 && (
                      <span className="ml-2 text-purple-400">({validUrlCount} video{validUrlCount !== 1 ? 's' : ''})</span>
                    )}
                  </label>
                  <textarea
                    id="videoUrls"
                    value={videoUrls}
                    onChange={(e) => setVideoUrls(e.target.value)}
                    placeholder={`Paste YouTube URLs (one per line)\n\nhttps://youtube.com/watch?v=...\nhttps://youtu.be/...`}
                    rows={5}
                    className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 font-mono text-sm transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                    disabled={isVideoSubmitting}
                  />
                  <p className="mt-2 text-xs text-gray-500">
                    <strong>Max 10 videos.</strong> AI will extract key moments, quotes, and timestamps from each video.
                  </p>
                </div>

                {/* Optional title and model selector */}
                <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="videoTitle" className="mb-1.5 block text-sm font-medium text-gray-400">
                      Project Title (optional)
                    </label>
                    <input
                      type="text"
                      id="videoTitle"
                      value={videoTitle}
                      onChange={(e) => setVideoTitle(e.target.value)}
                      placeholder="e.g., Joe Rogan UFO Episodes"
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      disabled={isVideoSubmitting}
                    />
                  </div>
                  <div>
                    <label htmlFor="geminiModel" className="mb-1.5 block text-sm font-medium text-gray-400">
                      Analysis Model
                    </label>
                    <select
                      id="geminiModel"
                      value={geminiModel}
                      onChange={(e) => setGeminiModel(e.target.value as 'gemini-2.5-flash' | 'gemini-2.5-pro')}
                      disabled={isVideoSubmitting}
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 cursor-pointer"
                    >
                      <option value="gemini-2.5-flash">Flash - Faster & Cheaper (~$0.15/hr)</option>
                      <option value="gemini-2.5-pro">Pro - More Accurate (~$1.15/hr)</option>
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isVideoSubmitting || validUrlCount === 0}
                  className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 px-6 py-3 font-medium text-white shadow-lg shadow-purple-500/20 transition-all duration-200 hover:from-purple-500 hover:to-purple-400 hover:shadow-purple-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                >
                  {isVideoSubmitting ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Analyze {validUrlCount > 0 ? `${validUrlCount} Video${validUrlCount !== 1 ? 's' : ''}` : 'Videos'}
                    </>
                  )}
                </button>
              </motion.form>
            ) : null}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Active Jobs Quick Link - ADHD-friendly navigation */}
        {activeJobsCount > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Link
              href="/queue?tab=active"
              className="mb-6 flex items-center justify-between px-4 py-3 rounded-xl bg-blue-600/10 border border-blue-500/30 hover:bg-blue-600/20 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 rounded-full bg-blue-500 animate-pulse" />
                <span className="text-sm font-medium text-blue-300">
                  {activeJobsCount} active job{activeJobsCount > 1 ? 's' : ''} in queue
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-blue-400 group-hover:text-blue-300">
                <span>View Queue</span>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          </motion.div>
        )}

        {/* Recent Jobs Section - Compact View */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base sm:text-lg font-semibold text-gray-100">Recent Jobs</h2>
            {jobs.length > 0 && (
              <Link
                href="/queue"
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
              >
                View all
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse p-3 bg-gray-900 rounded-lg border border-gray-800">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-gray-800 rounded-lg" />
                    <div className="flex-1">
                      <div className="h-4 w-3/4 bg-gray-800 rounded mb-2" />
                      <div className="h-3 w-1/2 bg-gray-800 rounded" />
                    </div>
                    <div className="w-12 h-4 bg-gray-800 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : recentJobs.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-xl border border-dashed border-gray-700 py-12 text-center"
            >
              <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-gray-800 p-3">
                <svg
                  className="h-6 w-6 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <h3 className="text-base font-medium text-gray-300">No jobs yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Create your first research job above to get started.
              </p>
              <button
                onClick={() => {
                  if (createPanelCollapsed) {
                    toggleCreatePanel();
                  }
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-purple-500 touch-manipulation"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create Your First Job
              </button>
            </motion.div>
          ) : (
            <div className="space-y-2">
              {recentJobs.map((job, index) => (
                <DashboardJobCard key={job.id} job={job} delay={index} />
              ))}
              
              {/* View All Jobs link - only show if more than 5 jobs */}
              {jobs.length > 5 && (
                <Link
                  href="/queue"
                  className="flex items-center justify-center gap-2 p-3 rounded-lg border border-gray-800 hover:border-gray-700 hover:bg-gray-900/50 text-gray-400 hover:text-gray-300 transition-all group"
                >
                  <span className="text-sm">View all {jobs.length} jobs</span>
                  <svg className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mobile FAB - shows when create panel is collapsed */}
      <FloatingActionButton
        visible={createPanelCollapsed}
        onClick={() => {
          toggleCreatePanel();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />
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
