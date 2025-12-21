import { useState, FormEvent, useEffect } from "react";
import Head from "next/head";
import Link from "next/link";

interface TranscriptResult {
  video_id: string;
  video_url: string;
  status: "available" | "missing" | "error";
  source: string;
  text?: string;
  error_message?: string;
}

interface SyncResponse {
  success: boolean;
  doc_url: string;
  folder_url: string;
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
  status: "queued" | "running" | "completed" | "failed";
  progress_percent: number;
  transcripts_completed: number;
  transcripts_total: number;
  doc_url?: string;
  folder_url?: string;
  warnings: string[];
  error?: string;
}

export default function TranscriptsPage() {
  const [videoUrls, setVideoUrls] = useState("");
  const [useWhisperFallback, setUseWhisperFallback] = useState(true);
  const [docTitle, setDocTitle] = useState("");
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
      .filter((url) => url.length > 0 && (url.includes("youtube") || url.includes("youtu.be")));
  };

  const urlCount = parseUrls(videoUrls).length;

  // Poll for job status
  useEffect(() => {
    if (!jobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/transcripts/${jobId}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const status: JobStatus = await response.json();
        setJobStatus(status);

        if (status.status === "completed" || status.status === "failed") {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const urls = parseUrls(videoUrls);

    if (urls.length === 0) {
      setError("Please enter at least one valid YouTube URL");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSyncResult(null);
    setJobId(null);
    setJobStatus(null);

    try {
      const response = await fetch("/api/transcripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_urls: urls,
          use_whisper_fallback: useWhisperFallback,
          doc_title: docTitle || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.job_id && !data.doc_url) {
        // Async job - start polling
        setJobId(data.job_id);
        setJobStatus({
          job_id: data.job_id,
          status: "queued",
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
      setError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setIsSubmitting(false);
    }
  };

  const isComplete = syncResult?.success || jobStatus?.status === "completed";
  const docUrl = syncResult?.doc_url || jobStatus?.doc_url;
  const folderUrl = syncResult?.folder_url || jobStatus?.folder_url;

  return (
    <>
      <Head>
        <title>YouTube Transcript Extractor - Research Agent</title>
        <meta name="description" content="Extract transcripts from YouTube videos" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white shadow-md rounded-lg p-8">
            {/* Header with back link */}
            <div className="flex items-center justify-between mb-8">
              <h1 className="text-3xl font-bold text-gray-900">YouTube Transcript Extractor</h1>
              <Link href="/" className="text-sm text-blue-600 hover:text-blue-800">
                Back to Research
              </Link>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* URL Textarea */}
              <div>
                <label htmlFor="urls" className="block text-sm font-medium text-gray-700 mb-2">
                  YouTube Video URLs (one per line)
                </label>
                <textarea
                  id="urls"
                  name="urls"
                  rows={8}
                  value={videoUrls}
                  onChange={(e) => setVideoUrls(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                  placeholder="https://www.youtube.com/watch?v=...&#10;https://youtu.be/...&#10;..."
                />
                <p className="mt-1 text-sm text-gray-500">
                  {urlCount} valid YouTube URL{urlCount !== 1 ? "s" : ""} detected
                  {urlCount > 5 && " (will process in background)"}
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
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="whisper" className="ml-2 text-sm text-gray-700">
                    Use Whisper AI for videos without captions ($0.006/min)
                  </label>
                </div>

                <div>
                  <label htmlFor="docTitle" className="block text-sm font-medium text-gray-700 mb-2">
                    Document Title (optional)
                  </label>
                  <input
                    type="text"
                    id="docTitle"
                    value={docTitle}
                    onChange={(e) => setDocTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="My Transcripts"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting || urlCount === 0}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? "Processing..." : `Extract Transcripts (${urlCount} video${urlCount !== 1 ? "s" : ""})`}
              </button>
            </form>

            {/* Error Display */}
            {error && (
              <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </p>
              </div>
            )}

            {/* Progress Bar for Async Jobs */}
            {jobStatus && !isComplete && (
              <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-md">
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    {jobStatus.status === "queued" ? "Queued..." : "Processing..."}
                  </span>
                  <span className="text-sm text-gray-600">{jobStatus.progress_percent}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${jobStatus.progress_percent}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  {jobStatus.transcripts_completed} of {jobStatus.transcripts_total} videos processed
                </p>
              </div>
            )}

            {/* Success Result */}
            {isComplete && docUrl && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
                <h2 className="text-lg font-semibold text-green-800 mb-3">Transcripts Ready!</h2>
                <div className="space-y-2">
                  <a
                    href={docUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:text-blue-800 underline"
                  >
                    Open Google Doc
                  </a>
                  {folderUrl && (
                    <a
                      href={folderUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-blue-600 hover:text-blue-800 underline text-sm"
                    >
                      Open Drive Folder
                    </a>
                  )}
                </div>

                {syncResult && (
                  <div className="mt-4 pt-4 border-t border-green-200">
                    <p className="text-sm text-green-700">
                      Successfully extracted: {syncResult.successful_count} / {syncResult.total_videos}
                    </p>
                    {syncResult.failed_count > 0 && (
                      <p className="text-sm text-yellow-700">
                        Failed/Missing: {syncResult.failed_count}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Failed Job */}
            {jobStatus?.status === "failed" && (
              <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
                <h2 className="text-lg font-semibold text-red-800 mb-2">Job Failed</h2>
                <p className="text-sm text-red-700">{jobStatus.error || "Unknown error occurred"}</p>
              </div>
            )}

            {/* Warnings */}
            {((syncResult?.warnings && syncResult.warnings.length > 0) ||
              (jobStatus?.warnings && jobStatus.warnings.length > 0)) && (
              <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <h3 className="text-sm font-semibold text-yellow-800 mb-2">Warnings</h3>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {(syncResult?.warnings || jobStatus?.warnings || []).map((w, i) => (
                    <li key={i}>• {w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
