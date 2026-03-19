/**
 * Shared TypeScript types for the Transcripts feature.
 */
import { PlayCircle, Globe, FileText } from 'lucide-react';

export interface TranscriptResult {
  video_id: string;
  video_url: string;
  status: 'available' | 'missing' | 'error';
  source: string;
  text?: string;
  error_message?: string;
}

export interface SyncResponse {
  success: boolean;
  transcripts: TranscriptResult[];
  warnings: string[];
  total_videos: number;
  successful_count: number;
  failed_count: number;
}

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  transcripts_completed: number;
  transcripts_total: number;
  doc_url?: string;
  warnings: string[];
  error?: string;
}

export interface CachedTranscript {
  id: string;
  title: string;
  url: string;
  type: 'youtube' | 'web' | 'upload';
  mode: string;
  length: string;
  job_id: string;
  cached_at: string;
}

export const TYPE_CONFIG = {
  youtube: { label: 'YouTube', bg: 'bg-[#ef4444]/10', text: 'text-[#ef4444]', icon: PlayCircle, iconBg: 'bg-[#ef4444]/10', iconColor: 'text-[#ef4444]' },
  web:     { label: 'Web',     bg: 'bg-accent-blue/10', text: 'text-accent-blue', icon: Globe, iconBg: 'bg-accent-blue/10', iconColor: 'text-accent-blue' },
  upload:  { label: 'Upload',  bg: 'bg-accent-purple/10', text: 'text-accent-purple', icon: FileText, iconBg: 'bg-accent-purple/10', iconColor: 'text-accent-purple' },
} as const;

export function parseUrls(input: string): string[] {
  return input
    .split(/[\n,]/)
    .map((u) => u.trim())
    .filter((u) => u.length > 0 && (u.includes('youtube') || u.includes('youtu.be')));
}

/** Build cached transcript list from sync results */
export function buildCached(syncResult: SyncResponse | null): CachedTranscript[] {
  if (!syncResult?.transcripts) return [];
  return syncResult.transcripts
    .filter((t) => t.status === 'available')
    .map((t, i) => ({
      id: `tr_${i}`,
      title: t.video_url,
      url: t.video_url,
      type: 'youtube' as const,
      mode: 'transcript_grounded',
      length: t.text ? `${Math.round(t.text.split(' ').length / 130)} min` : '—',
      job_id: 'j_auto',
      cached_at: 'just now',
    }));
}
