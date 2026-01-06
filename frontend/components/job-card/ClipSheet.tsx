/**
 * ClipSheet component for displaying video clips from Gemini extraction.
 * Shows timestamps, quotes, verification status, and copy functionality.
 */
import { useState } from 'react';

/**
 * Clip data structure matching backend ProducerClip
 */
export interface Clip {
  clip_id: string;
  video_url: string;
  timestamp_start: string;
  timestamp_end: string;
  speaker: string;
  quote: string;
  quote_type: string;
  range_verified: boolean;
  quote_verified: boolean;
  verification_level: 'verified' | 'probable' | 'unverified';
}

interface ClipSheetProps {
  clips: Clip[];
  showVerifiedOnly?: boolean;
}

const verificationConfig = {
  verified: {
    icon: '✓',
    label: 'Verified',
    bgColor: 'bg-green-900/30',
    textColor: 'text-green-400',
    borderColor: 'border-green-700',
  },
  probable: {
    icon: '~',
    label: 'Probable',
    bgColor: 'bg-yellow-900/30',
    textColor: 'text-yellow-400',
    borderColor: 'border-yellow-700',
  },
  unverified: {
    icon: '?',
    label: 'Unverified',
    bgColor: 'bg-gray-800/50',
    textColor: 'text-gray-400',
    borderColor: 'border-gray-700',
  },
};

function formatTimestamp(timestamp: string): string {
  // Already in MM:SS or HH:MM:SS format
  return timestamp;
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

function ClipCard({ clip }: { clip: Clip }) {
  const [copied, setCopied] = useState(false);
  const config = verificationConfig[clip.verification_level];

  const handleCopy = async () => {
    const text = `[${clip.timestamp_start}] ${clip.speaker}: "${clip.quote}"`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
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

  const timestampUrl = getYouTubeTimestampUrl(clip.video_url, clip.timestamp_start);

  return (
    <div
      className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-4 transition-all hover:border-opacity-80`}
    >
      {/* Header: Timestamp + Verification Badge */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <a
            href={timestampUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-sm text-blue-400 hover:text-blue-300 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {formatTimestamp(clip.timestamp_start)} - {formatTimestamp(clip.timestamp_end)}
          </a>
          <span className="text-gray-600">|</span>
          <span className="text-xs text-gray-500 capitalize">{clip.quote_type}</span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${config.bgColor} ${config.textColor}`}
            title={config.label}
          >
            <span>{config.icon}</span>
            <span className="hidden sm:inline">{config.label}</span>
          </span>
        </div>
      </div>

      {/* Speaker */}
      <p className="text-sm font-medium text-gray-300 mb-1">{clip.speaker}</p>

      {/* Quote */}
      <blockquote className="text-gray-200 italic border-l-2 border-gray-600 pl-3 mb-3">
        &ldquo;{clip.quote}&rdquo;
      </blockquote>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <a
          href={timestampUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-gray-500 hover:text-gray-400 truncate max-w-[200px]"
          onClick={(e) => e.stopPropagation()}
        >
          {clip.video_url.replace(/https?:\/\/(www\.)?/, '').substring(0, 40)}...
        </a>

        <button
          onClick={handleCopy}
          className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition ${
            copied
              ? 'bg-green-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          {copied ? (
            <>
              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
                />
              </svg>
              Copy
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export function ClipSheet({ clips, showVerifiedOnly = false }: ClipSheetProps) {
  const [filter, setFilter] = useState<'all' | 'verified' | 'probable' | 'unverified'>('all');

  // Sort clips: verified first, then by timestamp
  const sortedClips = [...clips].sort((a, b) => {
    // Verified first
    const levelOrder = { verified: 0, probable: 1, unverified: 2 };
    const levelDiff = levelOrder[a.verification_level] - levelOrder[b.verification_level];
    if (levelDiff !== 0) return levelDiff;

    // Then by timestamp
    return a.timestamp_start.localeCompare(b.timestamp_start);
  });

  // Apply filter
  const filteredClips = sortedClips.filter((clip) => {
    if (showVerifiedOnly && clip.verification_level === 'unverified') return false;
    if (filter === 'all') return true;
    return clip.verification_level === filter;
  });

  // Count by verification level
  const counts = clips.reduce(
    (acc, clip) => {
      acc[clip.verification_level] = (acc[clip.verification_level] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  if (clips.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        No clips extracted from videos.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with filter */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">
          Clips ({clips.length})
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
            Verified ({counts.verified || 0})
          </button>
          <button
            onClick={() => setFilter('probable')}
            className={`rounded px-2 py-1 transition ${
              filter === 'probable' ? 'bg-yellow-700 text-white' : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            Probable ({counts.probable || 0})
          </button>
        </div>
      </div>

      {/* Clips grid */}
      <div className="space-y-3">
        {filteredClips.map((clip) => (
          <ClipCard key={clip.clip_id} clip={clip} />
        ))}
      </div>

      {filteredClips.length === 0 && filter !== 'all' && (
        <div className="text-center py-4 text-gray-500 text-sm">
          No clips match the selected filter.
        </div>
      )}
    </div>
  );
}

export default ClipSheet;
