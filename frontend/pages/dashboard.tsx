/**
 * Dashboard page showing job list and creation form.
 * Features dark mode design with modern UI/UX.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import JobCard from '../components/JobCard';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import { useJobsStore, JobPreview, VideoAnalysisResponse, TextInputRequest, TextInputResponse, ScreenshotInputResponse, MixedInputRequest, MixedInputResponse, MixedTextInput } from '../store/jobs';
import { POLLING_INTERVALS, VALIDATION_LIMITS, PLATFORM_HINTS, SCREENSHOT_PLATFORM_HINTS } from '../lib/constants';
import { UnifiedInputPanel } from '../components/unified-input';

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

  // Topic Research state (LEGACY - kept for backward compatibility)
  const [prompt, setPrompt] = useState('');
  const [researchDepth, setResearchDepth] = useState('investigation');
  const [category, setCategory] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showPreview, setShowPreview] = useState(false);
  // Bulk delete confirmation
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [isBulkArchiving, setIsBulkArchiving] = useState(false);
  // Editable preview state
  const [editableSources, setEditableSources] = useState<string[]>([]);
  const [editableSubreddits, setEditableSubreddits] = useState<string[]>([]);
  const [newSubreddit, setNewSubreddit] = useState('');
  const {
    jobs, isLoading, preview, isPreviewLoading, fetchJobs, previewJob, createJob, createVideoAnalysisJob, createMixedInputJob, refreshJob, clearPreview,
    // Bulk selection
    isEditMode, selectedJobIds, bulkErrors, toggleEditMode, selectJob, deselectJob, selectAll, deselectAll, bulkDelete, bulkArchive, clearBulkErrors,
  } = useJobsStore();
  const { user } = useAuth();

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

  // Polling for running jobs
  useEffect(() => {
    const runningJobs = jobs.filter((job) => job.status === 'running' || job.status === 'queued');
    if (runningJobs.length === 0) return;

    const interval = setInterval(() => {
      batchRefreshJobs(runningJobs.map((job) => job.id));
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

  const handleRefresh = () => {
    fetchJobs();
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
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create mixed input job:', error);
      }
    } finally {
      setIsMixedSubmitting(false);
    }
  };

  // Memoize filtered jobs to prevent unnecessary recalculations
  // Group related statuses for filtering (completed includes completed_with_warnings, failed includes failed_insufficient)
  const filteredJobs = useMemo(() => {
    if (statusFilter === 'all') return jobs;
    return jobs.filter((job) => {
      if (statusFilter === 'completed') {
        return job.status === 'completed' || job.status === 'completed_with_warnings';
      }
      if (statusFilter === 'failed') {
        return job.status === 'failed' || job.status === 'failed_insufficient';
      }
      return job.status === statusFilter;
    });
  }, [jobs, statusFilter]);

  return (
    <Layout>
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="mt-2 text-gray-400">Create and manage your research jobs</p>
        </motion.div>

        {/* Create Job Form */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          {/* Mode Toggle */}
          <div className="mb-6 flex items-center gap-4 flex-wrap">
            <h2 className="text-lg font-semibold text-gray-100">New Job</h2>
            <div className="flex rounded-lg bg-gray-800 p-1">
              <button
                type="button"
                onClick={() => setJobMode('research')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
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
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
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
        </motion.div>

        {/* Jobs List */}
        <div>
          {/* Bulk errors display */}
          {bulkErrors.length > 0 && (
            <div className="mb-4 rounded-lg border border-red-800 bg-red-900/30 p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-red-400">Some jobs failed:</p>
                <button
                  onClick={clearBulkErrors}
                  className="text-red-400 hover:text-red-300 text-sm"
                >
                  Dismiss
                </button>
              </div>
              {bulkErrors.map(({ jobId, error }) => (
                <p key={jobId} className="text-xs text-red-300">{jobId.slice(0, 8)}...: {error}</p>
              ))}
            </div>
          )}

          <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-100">Your Jobs</h2>
              {/* Edit Mode Toggle */}
              <button
                onClick={toggleEditMode}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
                  isEditMode
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
                }`}
              >
                {isEditMode ? 'Done' : 'Select'}
              </button>
            </div>

            {/* Edit Mode Controls */}
            {isEditMode ? (
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={selectedJobIds.size > 0 ? deselectAll : selectAll}
                  className="rounded-lg bg-gray-800 px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-700"
                >
                  {selectedJobIds.size > 0 ? 'Deselect All' : 'Select All'}
                </button>
                <span className="text-sm text-gray-500">{selectedJobIds.size} selected</span>
                <button
                  onClick={async () => {
                    if (selectedJobIds.size === 0) return;
                    setIsBulkArchiving(true);
                    await bulkArchive();
                    setIsBulkArchiving(false);
                  }}
                  disabled={selectedJobIds.size === 0 || isBulkArchiving}
                  className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isBulkArchiving ? 'Archiving...' : 'Archive'}
                </button>
                <button
                  onClick={() => setShowBulkDeleteConfirm(true)}
                  disabled={selectedJobIds.size === 0}
                  className="rounded-lg border border-red-700 px-3 py-1.5 text-sm text-red-400 hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Delete
                </button>
              </div>
            ) : (
              /* Status Filter - only show when not in edit mode */
              <div className="flex flex-wrap gap-2">
                {['all', 'running', 'completed', 'failed', 'cancelled'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
                      statusFilter === status
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
                    }`}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Bulk Delete Confirmation Modal */}
          {showBulkDeleteConfirm && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="rounded-lg border border-gray-700 bg-gray-900 p-6 max-w-sm shadow-xl">
                <h3 className="text-lg font-medium text-gray-100 mb-2">Delete {selectedJobIds.size} jobs?</h3>
                <p className="text-sm text-gray-400 mb-4">This action cannot be undone.</p>
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setShowBulkDeleteConfirm(false)}
                    className="rounded-lg px-4 py-2 text-gray-400 hover:text-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      setIsBulkDeleting(true);
                      await bulkDelete();
                      setIsBulkDeleting(false);
                      setShowBulkDeleteConfirm(false);
                    }}
                    disabled={isBulkDeleting}
                    className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-500 disabled:opacity-50"
                  >
                    {isBulkDeleting ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="space-y-4">
              <JobSkeleton />
              <JobSkeleton />
              <JobSkeleton />
            </div>
          ) : filteredJobs.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-xl border border-dashed border-gray-700 py-16 text-center"
            >
              <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-gray-800 p-4">
                <svg
                  className="h-8 w-8 text-gray-500"
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
              <h3 className="text-lg font-medium text-gray-300">No jobs yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Create your first research job above to get started.
              </p>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              {filteredJobs.map((job, index) => (
                <motion.div
                  key={job.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <JobCard
                    job={job}
                    onRefresh={handleRefresh}
                    isEditMode={isEditMode}
                    isSelected={selectedJobIds.has(job.id)}
                    onToggleSelect={() => {
                      if (selectedJobIds.has(job.id)) {
                        deselectJob(job.id);
                      } else {
                        selectJob(job.id);
                      }
                    }}
                  />
                </motion.div>
              ))}
            </motion.div>
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
