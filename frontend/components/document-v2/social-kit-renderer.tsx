'use client';

/**
 * social-kit-renderer — Doc 6 renderer. shadcn Tabs per platform, copy buttons, hashtag badges.
 */

import { useState, useCallback } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CitationPill } from './shared/citation-pill';
import type { SocialKitData, PlatformPost } from '@/types/documents';

const PLATFORM_LABELS: Record<string, string> = {
  twitter_thread:      'Twitter',
  linkedin:            'LinkedIn',
  instagram:           'Instagram',
  youtube_description: 'YouTube',
  tiktok:              'TikTok',
  newsletter:          'Newsletter',
};

const PLATFORM_STYLES: Record<string, string> = {
  twitter_thread:      'data-[state=active]:text-sky-300',
  linkedin:            'data-[state=active]:text-blue-300',
  instagram:           'data-[state=active]:text-pink-300',
  youtube_description: 'data-[state=active]:text-red-300',
  tiktok:              'data-[state=active]:text-purple-300',
  newsletter:          'data-[state=active]:text-amber-300',
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(async () => {
    try { await navigator.clipboard.writeText(text); } catch { /* ignore */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [text]);
  return (
    <button
      onClick={handleCopy}
      className="text-caption px-2 py-0.5 rounded bg-card text-muted-foreground border border-border/40 hover:text-foreground transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function getPostText(post: PlatformPost): string {
  if (post.platform === 'twitter_thread' && post.tweets) {
    return post.tweets.map((t: any) => t.text).join('\n\n');
  }
  if (post.platform === 'youtube_description') {
    let text = post.description_body ?? '';
    if (post.timestamps?.length) {
      text += '\n\n' + post.timestamps.map((ts: any) => `${ts.timestamp} ${ts.label}`).join('\n');
    }
    return text;
  }
  return post.body ?? '';
}

function PlatformContent({ post, showDetails }: { post: PlatformPost; showDetails?: boolean }) {
  return (
    <Card className="bg-background/40 border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-caption text-muted-foreground/70">{post.char_count} chars</span>
          <CopyButton text={getPostText(post)} />
        </div>

        {/* Twitter thread */}
        {post.platform === 'twitter_thread' && post.tweets && (
          <div className="space-y-2">
            {post.tweets.map((tweet: any) => (
              <div key={tweet.tweet_number} className="bg-card/40 rounded-lg p-3 border border-border">
                <div className="flex items-start gap-2">
                  <span className="text-caption text-muted-foreground/70 font-mono flex-shrink-0">{tweet.tweet_number}.</span>
                  <p className="text-sm text-foreground">{tweet.text}</p>
                </div>
                <p className="text-caption text-muted-foreground/60 mt-1 text-right">{tweet.text.length}/280</p>
              </div>
            ))}
          </div>
        )}

        {/* YouTube description */}
        {post.platform === 'youtube_description' && (
          <div className="space-y-3">
            {post.description_body && <p className="text-sm text-foreground whitespace-pre-wrap">{post.description_body}</p>}
            {(post.timestamps?.length ?? 0) > 0 && (
              <div className="bg-card/30 rounded-lg p-3 border border-border">
                <p className="text-xs font-medium text-muted-foreground/70 mb-2">Timestamps</p>
                {(post.timestamps ?? []).map((ts: any, i: number) => (
                  <div key={i} className="flex gap-3 text-sm text-muted-foreground">
                    <span className="font-mono text-muted-foreground/70 w-12">{ts.timestamp}</span>
                    <span>{ts.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Single-body platforms */}
        {post.body && post.platform !== 'twitter_thread' && post.platform !== 'youtube_description' && (
          <p className="text-sm text-foreground whitespace-pre-wrap">{post.body}</p>
        )}

        {/* Hashtags */}
        {post.hashtags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {post.hashtags.map((tag: string) => (
              <Badge key={tag} variant="outline" className="text-caption px-1.5 py-0 text-muted-foreground/70 border-border/40 bg-card/60">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Citations */}
        {showDetails && post.source_ids?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {post.source_ids.map((id: string) => <CitationPill key={id} id={id} />)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface SocialKitRendererProps {
  content: any;
  showDetails?: boolean;
}

export function SocialKitRenderer({ content, showDetails = false }: SocialKitRendererProps) {
  const data = content as SocialKitData;
  const platforms = data?.platforms ?? [];

  if (!platforms.length) {
    return <p className="text-sm text-muted-foreground/70">No platform content available.</p>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">Social Media Kit</h1>
        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground/70">
          <span>{platforms.length} platform{platforms.length !== 1 ? 's' : ''}</span>
          {data?.source_count != null && (
            <><span className="w-1 h-1 rounded-full bg-secondary" /><span>{data.source_count} source{data.source_count !== 1 ? 's' : ''}</span></>
          )}
        </div>
      </div>

      <Tabs defaultValue={platforms[0]?.platform}>
        <TabsList className="bg-background/60 border border-border flex-wrap h-auto gap-1 p-1">
          {platforms.map((post: PlatformPost) => (
            <TabsTrigger
              key={post.platform}
              value={post.platform}
              className={`text-xs ${PLATFORM_STYLES[post.platform] ?? ''}`}
            >
              {PLATFORM_LABELS[post.platform] ?? post.platform}
            </TabsTrigger>
          ))}
        </TabsList>
        {platforms.map((post: PlatformPost) => (
          <TabsContent key={post.platform} value={post.platform} className="mt-3">
            <PlatformContent post={post} showDetails={showDetails} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
