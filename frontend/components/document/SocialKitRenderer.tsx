/**
 * SocialKitRenderer — Typed renderer for Social Media Kit (Doc 6).
 *
 * Tabbed interface with one tab per platform.
 * Copy button per post, character count badge, hashtag pills.
 */

import { useState, useCallback } from 'react';
import { CardWrapper } from './shared/CardWrapper';
import { CitationPill } from './shared/CitationPill';
import type { SocialKitData, PlatformPost } from '@/types/documents';

export interface SocialKitRendererProps {
  data: SocialKitData;
  showDetails?: boolean;
}

const PLATFORM_LABELS: Record<string, string> = {
  twitter_thread: 'Twitter',
  linkedin: 'LinkedIn',
  instagram: 'Instagram',
  youtube_description: 'YouTube',
  tiktok: 'TikTok',
  newsletter: 'Newsletter',
};

const PLATFORM_COLORS: Record<string, string> = {
  twitter_thread: 'bg-sky-500/15 text-sky-300 border-sky-500/20',
  linkedin: 'bg-blue-500/15 text-blue-300 border-blue-500/20',
  instagram: 'bg-pink-500/15 text-pink-300 border-pink-500/20',
  youtube_description: 'bg-red-500/15 text-red-300 border-red-500/20',
  tiktok: 'bg-purple-500/15 text-purple-300 border-purple-500/20',
  newsletter: 'bg-amber-500/15 text-amber-300 border-amber-500/20',
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="text-[11px] px-2 py-0.5 rounded bg-white/[0.06] text-white/50 hover:text-white/70 hover:bg-white/[0.1] transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function PlatformPostCard({ post, showDetails }: { post: PlatformPost; showDetails?: boolean }) {
  const label = PLATFORM_LABELS[post.platform] || post.platform;
  const colorClass = PLATFORM_COLORS[post.platform] || 'bg-white/[0.06] text-white/50 border-white/[0.06]';

  const getPostText = (): string => {
    if (post.platform === 'twitter_thread' && post.tweets) {
      return post.tweets.map((t) => t.text).join('\n\n');
    }
    if (post.platform === 'youtube_description') {
      let text = post.description_body || '';
      if (post.timestamps) {
        text += '\n\n' + post.timestamps.map((ts) => `${ts.timestamp} ${ts.label}`).join('\n');
      }
      return text;
    }
    return post.body || '';
  };

  return (
    <CardWrapper>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium border ${colorClass}`}>
            {label}
          </span>
          <span className="text-[11px] text-white/30">{post.char_count} chars</span>
        </div>
        <CopyButton text={getPostText()} />
      </div>

      {/* Twitter thread */}
      {post.platform === 'twitter_thread' && post.tweets && (
        <div className="space-y-2">
          {post.tweets.map((tweet) => (
            <div key={tweet.tweet_number} className="bg-white/[0.03] rounded-lg p-3 border border-white/[0.06]">
              <div className="flex items-start gap-2">
                <span className="text-[11px] text-white/30 font-mono flex-shrink-0">{tweet.tweet_number}.</span>
                <p className="text-sm text-white/80">{tweet.text}</p>
              </div>
              <p className="text-[10px] text-white/25 mt-1 text-right">{tweet.text.length}/280</p>
            </div>
          ))}
        </div>
      )}

      {/* YouTube description */}
      {post.platform === 'youtube_description' && (
        <div className="space-y-3">
          {post.description_body && (
            <p className="text-sm text-white/80 whitespace-pre-wrap">{post.description_body}</p>
          )}
          {post.timestamps && post.timestamps.length > 0 && (
            <div className="bg-white/[0.03] rounded-lg p-3 border border-white/[0.06]">
              <p className="text-xs font-medium text-white/50 mb-2">Timestamps</p>
              {post.timestamps.map((ts, i) => (
                <div key={i} className="flex gap-3 text-sm text-white/70">
                  <span className="font-mono text-white/40 w-12">{ts.timestamp}</span>
                  <span>{ts.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Single-body platforms */}
      {post.body && post.platform !== 'twitter_thread' && post.platform !== 'youtube_description' && (
        <p className="text-sm text-white/80 whitespace-pre-wrap">{post.body}</p>
      )}

      {/* Hashtags */}
      {post.hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {post.hashtags.map((tag) => (
            <span key={tag} className="text-[11px] px-1.5 py-0.5 rounded bg-white/[0.06] text-white/40">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Source citations */}
      {showDetails && post.source_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {post.source_ids.map((id) => (
            <CitationPill key={id} sourceId={id} />
          ))}
        </div>
      )}
    </CardWrapper>
  );
}

export function SocialKitRenderer({ data, showDetails = false }: SocialKitRendererProps) {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white/95">Social Media Kit</h1>
        <div className="flex items-center gap-3 mt-2 text-xs text-white/40">
          <span>{data.platforms.length} platform{data.platforms.length !== 1 ? 's' : ''}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>{data.source_count} source{data.source_count !== 1 ? 's' : ''}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>Doc 6</span>
        </div>
      </div>

      {/* Platform tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {data.platforms.map((post, i) => {
          const label = PLATFORM_LABELS[post.platform] || post.platform;
          return (
            <button
              key={post.platform}
              onClick={() => setActiveTab(i)}
              className={`
                text-xs px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors
                ${activeTab === i
                  ? 'bg-white/[0.1] text-white/90 font-medium'
                  : 'bg-white/[0.03] text-white/40 hover:text-white/60 hover:bg-white/[0.06]'
                }
              `}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Active platform content */}
      {data.platforms[activeTab] && (
        <PlatformPostCard post={data.platforms[activeTab]} showDetails={showDetails} />
      )}

      {/* All platforms (collapsed) */}
      {data.platforms.length > 1 && (
        <details className="group">
          <summary className="text-xs text-white/30 cursor-pointer hover:text-white/50 transition-colors">
            View all platforms
          </summary>
          <div className="mt-4 space-y-4">
            {data.platforms.map((post) => (
              <PlatformPostCard key={post.platform} post={post} showDetails={showDetails} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export default SocialKitRenderer;
