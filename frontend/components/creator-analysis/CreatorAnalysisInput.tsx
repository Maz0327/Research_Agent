/**
 * CreatorAnalysisInput — Accept 3-5 YouTube URLs for creator style analysis.
 *
 * Shown when intent-router detects "creator_analysis" intent.
 * User enters creator name + pastes 3-5 YouTube URLs.
 */

import { useState, useCallback } from 'react';

interface CreatorAnalysisInputProps {
  /** Pre-filled creator name from intent detection */
  initialQuery: string;
  /** Whether analysis is in progress */
  isLoading: boolean;
  /** Submit handler */
  onSubmit: (creatorName: string, videoUrls: string[]) => void;
  /** Back handler */
  onBack: () => void;
}

const YOUTUBE_PATTERN = /(?:youtube\.com|youtu\.be)/i;
const MIN_URLS = 3;
const MAX_URLS = 5;

function isYouTubeUrl(url: string): boolean {
  return YOUTUBE_PATTERN.test(url);
}

function parseUrls(text: string): string[] {
  return text
    .split(/[\n,]/)
    .map((u) => u.trim())
    .filter((u) => u.length > 0 && u.startsWith('http'));
}

export function CreatorAnalysisInput({
  initialQuery,
  isLoading,
  onSubmit,
  onBack,
}: CreatorAnalysisInputProps) {
  const [creatorName, setCreatorName] = useState(initialQuery);
  const [urlText, setUrlText] = useState('');
  const [error, setError] = useState<string | null>(null);

  const parsedUrls = parseUrls(urlText);
  const youtubeUrls = parsedUrls.filter(isYouTubeUrl);
  const nonYoutubeUrls = parsedUrls.filter((u) => !isYouTubeUrl(u));

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);

      if (!creatorName.trim()) {
        setError('Please enter the creator name');
        return;
      }

      if (youtubeUrls.length < MIN_URLS) {
        setError(`Please provide at least ${MIN_URLS} YouTube URLs (found ${youtubeUrls.length})`);
        return;
      }

      if (youtubeUrls.length > MAX_URLS) {
        setError(`Maximum ${MAX_URLS} YouTube URLs allowed (found ${youtubeUrls.length})`);
        return;
      }

      onSubmit(creatorName.trim(), youtubeUrls);
    },
    [creatorName, youtubeUrls, onSubmit]
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Back button */}
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back
      </button>

      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-foreground">Creator Style Analysis</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Paste 3-5 YouTube video URLs from the creator you want to analyze.
          We&apos;ll extract their style patterns, hooks, vocabulary, and narrative structure.
        </p>
      </div>

      {/* Creator name */}
      <div>
        <label htmlFor="creatorName" className="mb-1.5 block text-sm font-medium text-muted-foreground">
          Creator Name
        </label>
        <input
          type="text"
          id="creatorName"
          value={creatorName}
          onChange={(e) => setCreatorName(e.target.value)}
          placeholder="e.g., Johnny Harris, Veritasium, Coffeezilla"
          className="w-full rounded-lg border border-border bg-card px-4 py-3 text-foreground placeholder-gray-500 transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
          disabled={isLoading}
          autoFocus
        />
      </div>

      {/* YouTube URLs */}
      <div>
        <label htmlFor="videoUrls" className="mb-1.5 block text-sm font-medium text-muted-foreground">
          YouTube Video URLs
          <span className="ml-2 text-muted-foreground/70">({MIN_URLS}-{MAX_URLS} required)</span>
          {youtubeUrls.length > 0 && (
            <span className="ml-2 text-purple-400">
              ({youtubeUrls.length} video{youtubeUrls.length !== 1 ? 's' : ''})
            </span>
          )}
        </label>
        <textarea
          id="videoUrls"
          value={urlText}
          onChange={(e) => setUrlText(e.target.value)}
          placeholder={`Paste YouTube URLs (one per line):\nhttps://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...`}
          rows={5}
          className="w-full rounded-lg border border-border bg-card px-4 py-3 text-foreground placeholder-gray-500 font-mono text-sm transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
          disabled={isLoading}
        />
        {nonYoutubeUrls.length > 0 && (
          <p className="text-xs text-yellow-400 mt-1">
            {nonYoutubeUrls.length} non-YouTube URL{nonYoutubeUrls.length !== 1 ? 's' : ''} will be ignored
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-700 bg-red-900/30 p-3">
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Info */}
      <div className="rounded-lg border border-border bg-card/50 p-3">
        <p className="text-xs text-muted-foreground">
          <strong className="text-muted-foreground">How it works:</strong> We fetch transcripts from each video,
          then analyze them to identify the creator&apos;s unique hook patterns, narrative structure,
          vocabulary fingerprint, and tone. The result can be saved as a personal style guide.
        </p>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading || youtubeUrls.length < MIN_URLS || !creatorName.trim()}
        className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 px-6 py-3 font-medium text-white shadow-lg shadow-purple-500/20 transition-all duration-200 hover:from-purple-500 hover:to-purple-400 hover:shadow-purple-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
      >
        {isLoading ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Analyzing Style...
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Analyze Creator Style
          </>
        )}
      </button>
    </form>
  );
}
