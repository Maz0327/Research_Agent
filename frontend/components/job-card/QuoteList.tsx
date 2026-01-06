/**
 * QuoteList component for displaying quotes from Gemini extraction.
 * Shows timestamps, verification status, and copy functionality.
 */
import { useState } from 'react';

/**
 * Quote data structure matching backend ProducerQuote
 */
export interface Quote {
  quote_id: string;
  video_url: string;
  text: string;
  speaker: string;
  timestamp: string;
  quote_verified: boolean;
  match_score: number;
}

interface QuoteListProps {
  quotes: Quote[];
  showVerifiedOnly?: boolean;
}

function getYouTubeTimestampUrl(videoUrl: string, timestamp: string): string {
  // Convert MM:SS to seconds
  const parts = timestamp.split(':').map(Number);
  let seconds = 0;
  if (parts.length === 2) {
    seconds = parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
  }

  // Add timestamp to YouTube URL
  if (videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')) {
    const separator = videoUrl.includes('?') ? '&' : '?';
    return `${videoUrl}${separator}t=${seconds}`;
  }
  return videoUrl;
}

function QuoteCard({ quote }: { quote: Quote }) {
  const [copied, setCopied] = useState(false);

  const isVerified = quote.quote_verified;
  const isProbable = !quote.quote_verified && quote.match_score >= 0.8;

  const handleCopy = async () => {
    const text = `"${quote.text}" - ${quote.speaker} [${quote.timestamp}]`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const timestampUrl = getYouTubeTimestampUrl(quote.video_url, quote.timestamp);

  return (
    <div
      className={`group flex items-start gap-3 rounded-lg border p-3 transition-all ${
        isVerified
          ? 'border-green-700/50 bg-green-900/20 hover:border-green-600'
          : isProbable
            ? 'border-yellow-700/50 bg-yellow-900/20 hover:border-yellow-600'
            : 'border-gray-700/50 bg-gray-800/30 hover:border-gray-600'
      }`}
    >
      {/* Verification indicator */}
      <div className="flex-shrink-0 mt-1">
        {isVerified ? (
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-green-600 text-xs text-white" title="Verified">
            ✓
          </span>
        ) : isProbable ? (
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-yellow-600 text-xs text-white" title="Probable match">
            ~
          </span>
        ) : (
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-600 text-xs text-white" title="Unverified">
            ?
          </span>
        )}
      </div>

      {/* Quote content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <a
            href={timestampUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-xs text-blue-400 hover:text-blue-300 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            [{quote.timestamp}]
          </a>
          <span className="text-sm font-medium text-gray-300">{quote.speaker}</span>
        </div>

        <p className="text-gray-200 text-sm leading-relaxed">
          &ldquo;{quote.text}&rdquo;
        </p>

        {/* Match score indicator for unverified quotes */}
        {!isVerified && quote.match_score > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <div className="h-1 flex-1 rounded-full bg-gray-700 max-w-[100px]">
              <div
                className={`h-1 rounded-full ${
                  quote.match_score >= 0.8
                    ? 'bg-yellow-500'
                    : quote.match_score >= 0.5
                      ? 'bg-orange-500'
                      : 'bg-red-500'
                }`}
                style={{ width: `${quote.match_score * 100}%` }}
              />
            </div>
            <span className="text-xs text-gray-500">
              {Math.round(quote.match_score * 100)}% match
            </span>
          </div>
        )}
      </div>

      {/* Copy button */}
      <button
        onClick={handleCopy}
        className={`flex-shrink-0 opacity-0 group-hover:opacity-100 inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition ${
          copied
            ? 'bg-green-600 text-white opacity-100'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        {copied ? (
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
            />
          </svg>
        )}
      </button>
    </div>
  );
}

export function QuoteList({ quotes, showVerifiedOnly = false }: QuoteListProps) {
  const [filter, setFilter] = useState<'all' | 'verified' | 'unverified'>('all');

  // Sort quotes: verified first, then by timestamp
  const sortedQuotes = [...quotes].sort((a, b) => {
    // Verified first
    if (a.quote_verified !== b.quote_verified) {
      return a.quote_verified ? -1 : 1;
    }
    // Then by match score
    if (a.match_score !== b.match_score) {
      return b.match_score - a.match_score;
    }
    // Then by timestamp
    return a.timestamp.localeCompare(b.timestamp);
  });

  // Apply filter
  const filteredQuotes = sortedQuotes.filter((quote) => {
    if (showVerifiedOnly && !quote.quote_verified && quote.match_score < 0.8) return false;
    if (filter === 'all') return true;
    if (filter === 'verified') return quote.quote_verified;
    return !quote.quote_verified;
  });

  // Count verified
  const verifiedCount = quotes.filter((q) => q.quote_verified).length;
  const probableCount = quotes.filter((q) => !q.quote_verified && q.match_score >= 0.8).length;

  if (quotes.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        No quotes extracted from videos.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with filter */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">
          Quotes ({quotes.length})
        </h4>

        <div className="flex items-center gap-1 text-xs">
          <button
            onClick={() => setFilter('all')}
            className={`rounded px-2 py-1 transition ${
              filter === 'all' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('verified')}
            className={`rounded px-2 py-1 transition ${
              filter === 'verified' ? 'bg-green-700 text-white' : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            Verified ({verifiedCount})
          </button>
          {probableCount > 0 && (
            <span className="text-gray-500 px-1">
              +{probableCount} probable
            </span>
          )}
        </div>
      </div>

      {/* Quotes list */}
      <div className="space-y-2">
        {filteredQuotes.map((quote) => (
          <QuoteCard key={quote.quote_id} quote={quote} />
        ))}
      </div>

      {filteredQuotes.length === 0 && filter !== 'all' && (
        <div className="text-center py-4 text-gray-500 text-sm">
          No quotes match the selected filter.
        </div>
      )}
    </div>
  );
}

export default QuoteList;
