/**
 * YouTube Transcript Extractor page.
 * Dark mode design with modern styling.
 */
import { useState, FormEvent, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';

interface TranscriptResult {
  video_id: string;
  video_url: string;
  status: 'available' | 'missing' | 'error';
  source: string;
  text?: string;
  error_message?: string;
}

interface SyncResponse {
  success: boolean;
  doc_url: string; // DEPRECATED: always empty since Drive removal (2026-01-19)
  folder_url: string; // DEPRECATED: always empty since Drive removal (2026-01-19)
  transcripts: TranscriptResult[];
  warnings: string[];
  total_videos: number;
  successful_count: number;
  failed_count: number;
}

interface AsyncResponse {
  job_id: string;
  status: string;
  message: string;
  total_videos: number;
}

interface JobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  transcripts_completed: number;
  transcripts_total: number;
  doc_url?: string; // Supabase Storage signed URL (async jobs only)
  warnings: string[];
  error?: string;
}

export default function TranscriptsPage() {
  const [videoUrls, setVideoUrls] = useState('');
  const [useWhisperFallback, setUseWhisperFallback] = useState(true);
  const [docTitle, setDocTitle] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Parse URLs from textarea
  const parseUrls = (input: string): string[] => {
    return input
      .split(/[\n,]/)
      .map((url) => url.trim())
      .filter((url) => url.length > 0 && (url.includes('youtube') || url.includes('youtu.be')));
  };

  const urlCount = parseUrls(videoUrls).length;

  // Poll for job status with error limits
  useEffect(() => {
    if (!jobId) return;

    let errorCount = 0;
    const MAX_POLL_ERRORS = 5;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/transcripts/${jobId}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const status: JobStatus = await response.json();
        setJobStatus(status);
        errorCount = 0; // Reset error count on success

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        errorCount++;
        if (process.env.NODE_ENV === 'development') {
          console.error('Polling error:', err);
        }
        if (errorCount >= MAX_POLL_ERRORS) {
          clearInterval(pollInterval);
          setError('Failed to fetch job status after multiple attempts. Please refresh the page.');
        }
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const urls = parseUrls(videoUrls);

    if (urls.length === 0) {
      setError('Please enter at least one valid YouTube URL');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSyncResult(null);
    setJobId(null);
    setJobStatus(null);

    try {
      const response = await fetch('/api/transcripts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_urls: urls,
          use_whisper_fallback: useWhisperFallback,
          doc_title: docTitle || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.job_id && !data.doc_url) {
        // Async job - start polling
        setJobId(data.job_id);
        setJobStatus({
          job_id: data.job_id,
          status: 'queued',
          progress_percent: 0,
          transcripts_completed: 0,
          transcripts_total: data.total_videos,
          warnings: [],
        });
      } else {
        // Sync result
        setSyncResult(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isComplete = syncResult?.success || jobStatus?.status === 'completed';
  // Sync responses return transcripts inline (doc_url is always empty since Drive removal).
  // Async responses may have a Supabase Storage signed URL in doc_url.
  const docUrl = jobStatus?.doc_url || '';
  const hasTranscripts = syncResult?.transcripts?.some(t => t.status === 'available');

  return (
    <>
      <Head>
        <title>YouTube Transcript Extractor - Research Agent</title>
        <meta name="description" content="Extract transcripts from YouTube videos" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <Layout>
        <div className="mx-auto max-w-3xl">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              YouTube Transcript Extractor
            </h1>
            <p className="mt-2 text-gray-400">
              Extract transcripts from YouTube videos
            </p>
          </motion.div>

          {/* Form Card */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
          >
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* URL Textarea */}
              <div>
                <label htmlFor="urls" className="block text-sm font-medium text-gray-400 mb-2">
                  YouTube Video URLs (one per line)
                </label>
                <textarea
                  id="urls"
                  name="urls"
                  rows={8}
                  value={videoUrls}
                  onChange={(e) => setVideoUrls(e.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 font-mono text-sm transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="https://www.youtube.com/watch?v=...&#10;https://youtu.be/...&#10;..."
                />
                <p className="mt-2 text-sm text-gray-500">
                  {urlCount} valid YouTube URL{urlCount !== 1 ? 's' : ''} detected
                  {urlCount > 5 && ' (will process in background)'}
                </p>
              </div>

              {/* Options */}
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="whisper"
                    checked={useWhisperFallback}
                    onChange={(e) => setUseWhisperFallback(e.target.checked)}
                    className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
                  />
                  <label htmlFor="whisper" className="ml-3 text-sm text-gray-300">
                    Use Whisper AI for videos without captions ($0.006/min)
                  </label>
                </div>

                <div>
                  <label htmlFor="docTitle" className="block text-sm font-medium text-gray-400 mb-2">
                    Document Title (optional)
                  </label>
                  <input
                    type="text"
                    id="docTitle"
                    value={docTitle}
                    onChange={(e) => setDocTitle(e.target.value)}
                    className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="My Transcripts"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting || urlCount === 0}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Processing...
                  </>
                ) : (
                  `Extract Transcripts (${urlCount} video${urlCount !== 1 ? 's' : ''})`
                )}
              </button>
            </form>
          </motion.div>

          {/* Error Display */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 rounded-xl border border-red-500/30 bg-red-900/30 p-4"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500/20">
                  <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <p className="text-sm text-red-300">
                  <strong>Error:</strong> {error}
                </p>
              </div>
            </motion.div>
          )}

          {/* Progress Bar for Async Jobs */}
          {jobStatus && !isComplete && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-6"
            >
              <div className="flex justify-between mb-3">
                <span className="text-sm font-medium text-gray-300">
                  {jobStatus.status === 'queued' ? 'Queued...' : 'Processing...'}
                </span>
                <span className="text-sm font-medium text-blue-400">{jobStatus.progress_percent}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-gray-800 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${jobStatus.progress_percent}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
              <p className="text-sm text-gray-500 mt-3">
                {jobStatus.transcripts_completed} of {jobStatus.transcripts_total} videos processed
              </p>
            </motion.div>
          )}

          {/* Success Result */}
          {isComplete && (hasTranscripts || docUrl) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 rounded-xl border border-green-500/30 bg-green-900/30 p-6"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-500/20 rounded-lg">
                    <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-green-300">Transcripts Ready!</p>
                    <p className="text-sm text-green-400/70">
                      {syncResult ? 'Transcripts extracted successfully' : 'Your transcript document is ready'}
                    </p>
                  </div>
                </div>
                {docUrl && (
                  <a
                    href={docUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500"
                  >
                    Download Transcript
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </a>
                )}
              </div>

              {syncResult && (
                <div className="mt-4 pt-4 border-t border-green-500/30">
                  <p className="text-sm text-green-300">
                    Successfully extracted: {syncResult.successful_count} / {syncResult.total_videos}
                  </p>
                  {syncResult.failed_count > 0 && (
                    <p className="text-sm text-yellow-400 mt-1">
                      Failed/Missing: {syncResult.failed_count}
                    </p>
                  )}
                </div>
              )}

              {/* Inline transcript display for sync results */}
              {syncResult?.transcripts && syncResult.transcripts.filter(t => t.text).length > 0 && (
                <div className="mt-4 space-y-4">
                  {syncResult.transcripts.filter(t => t.text).map((t, idx) => (
                    <div key={idx} className="rounded-lg border border-gray-700 bg-gray-800/50 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium text-gray-300 truncate">{t.video_url}</p>
                        <button
                          onClick={() => navigator.clipboard.writeText(t.text || '')}
                          className="text-xs text-blue-400 hover:text-blue-300 transition shrink-0 ml-2"
                        >
                          Copy
                        </button>
                      </div>
                      <pre className="text-sm text-gray-400 whitespace-pre-wrap max-h-60 overflow-y-auto">
                        {t.text}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Failed Job */}
          {jobStatus?.status === 'failed' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 rounded-xl border border-red-500/30 bg-red-900/30 p-6"
            >
              <h2 className="text-lg font-semibold text-red-300 mb-2">Job Failed</h2>
              <p className="text-sm text-red-400">{jobStatus.error || 'Unknown error occurred'}</p>
            </motion.div>
          )}

          {/* Warnings */}
          {((syncResult?.warnings && syncResult.warnings.length > 0) ||
            (jobStatus?.warnings && jobStatus.warnings.length > 0)) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 rounded-xl border border-yellow-500/30 bg-yellow-900/30 p-6"
            >
              <h3 className="text-sm font-semibold text-yellow-300 mb-2">Warnings</h3>
              <ul className="text-sm text-yellow-400 space-y-1">
                {(syncResult?.warnings || jobStatus?.warnings || []).map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </motion.div>
          )}
        </div>
      </Layout>
    </>
  );
}
