'use client';

/**
 * TranscriptsContent — Cached transcript browser with source type badges,
 * analysis mode display, List/Grid toggle, and search. Extract form below table.
 */
import { useState, useEffect, FormEvent } from 'react';
import { Search, LayoutList, LayoutGrid } from 'lucide-react';
import {
  SyncResponse, JobStatus, CachedTranscript,
  TYPE_CONFIG, parseUrls, buildCached,
} from './transcript-types';

type ViewMode = 'list' | 'grid';

export function TranscriptsContent() {
  const [videoUrls, setVideoUrls] = useState('');
  const [useWhisperFallback, setUseWhisperFallback] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [search, setSearch] = useState('');

  const urlCount = parseUrls(videoUrls).length;
  const isComplete = syncResult?.success || jobStatus?.status === 'completed';
  const cached: CachedTranscript[] = buildCached(syncResult);
  const filtered = cached.filter(
    (t) => search === '' || t.title.toLowerCase().includes(search.toLowerCase()) || t.job_id.includes(search)
  );

  useEffect(() => {
    if (!jobId) return;
    let errorCount = 0;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/transcripts/${jobId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const status: JobStatus = await res.json();
        setJobStatus(status);
        errorCount = 0;
        if (status.status === 'completed' || status.status === 'failed') clearInterval(interval);
      } catch {
        if (++errorCount >= 5) { clearInterval(interval); setError('Failed to fetch job status.'); }
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const urls = parseUrls(videoUrls);
    if (urls.length === 0) { setError('Enter at least one valid YouTube URL'); return; }
    setIsSubmitting(true); setError(null); setSyncResult(null); setJobId(null); setJobStatus(null);
    try {
      const res = await fetch('/api/transcripts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_urls: urls, use_whisper_fallback: useWhisperFallback }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.job_id && !data.doc_url) {
        setJobId(data.job_id);
        setJobStatus({ job_id: data.job_id, status: 'queued', progress_percent: 0, transcripts_completed: 0, transcripts_total: data.total_videos, warnings: [] });
      } else { setSyncResult(data); }
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to submit'); }
    finally { setIsSubmitting(false); }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Transcripts</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Cached transcripts from YouTube, uploaded text, and OCR results</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="flex items-center bg-secondary rounded-lg p-0.5">
            {(['list', 'grid'] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors cursor-pointer capitalize ${viewMode === mode ? 'bg-accent-blue/10 text-accent-blue' : 'text-muted-foreground hover:text-foreground'}`}
              >
                {mode === 'list' ? <LayoutList className="w-3 h-3" /> : <LayoutGrid className="w-3 h-3" />}
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder="Search transcripts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search transcripts"
              className="bg-secondary text-xs rounded-lg pl-7 pr-3 py-1.5 border border-border focus:border-accent-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-ring w-40 sm:w-48 text-foreground placeholder:text-muted-foreground"
            />
          </div>
        </div>
      </div>

      {/* Transcript table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full min-w-[600px]">
          <thead>
            <tr className="border-b border-border">
              {['Source', 'Type', 'Mode', 'Length', 'Job', 'Cached'].map((h) => (
                <th key={h} className="text-left text-caption font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-muted-foreground">
                {search ? 'No transcripts match your search.' : 'No cached transcripts yet. Extract some below.'}
              </td></tr>
            )}
            {filtered.map((t) => {
              const cfg = TYPE_CONFIG[t.type];
              const Icon = cfg.icon;
              return (
                <tr key={t.id} className="border-b border-border hover:bg-muted/30 transition-colors cursor-pointer last:border-0">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-6 h-6 rounded ${cfg.iconBg} flex items-center justify-center shrink-0`}>
                        <Icon className={`w-3 h-3 ${cfg.iconColor}`} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm text-foreground truncate max-w-[250px]">{t.title}</p>
                        <p className="text-caption text-muted-foreground truncate">{t.url}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-caption px-1.5 py-0.5 rounded font-medium ${cfg.bg} ${cfg.text}`}>{cfg.label}</span>
                  </td>
                  <td className="px-4 py-3"><span className="text-xs text-muted-foreground">{t.mode}</span></td>
                  <td className="px-4 py-3"><span className="text-xs text-muted-foreground">{t.length}</span></td>
                  <td className="px-4 py-3"><span className="text-caption font-mono text-accent-blue">{t.job_id}</span></td>
                  <td className="px-4 py-3"><span className="text-xs text-muted-foreground">{t.cached_at}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>

      {/* Extract form */}
      <div className="bg-card border border-border rounded-xl p-6">
        <h2 className="text-sm font-semibold mb-4 text-foreground">Extract New Transcripts</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            rows={4}
            value={videoUrls}
            onChange={(e) => setVideoUrls(e.target.value)}
            aria-label="YouTube video URLs"
            className="w-full rounded-lg border border-border bg-secondary px-4 py-3 text-foreground placeholder:text-muted-foreground font-mono text-sm focus:border-accent-blue focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder={"https://www.youtube.com/watch?v=...\nhttps://youtu.be/..."}
          />
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
              <input type="checkbox" checked={useWhisperFallback} onChange={(e) => setUseWhisperFallback(e.target.checked)} className="rounded" />
              Whisper fallback ($0.006/min)
            </label>
            <p className="text-xs text-muted-foreground">{urlCount} URL{urlCount !== 1 ? 's' : ''} detected</p>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          {jobStatus && !isComplete && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{jobStatus.status === 'queued' ? 'Queued…' : 'Processing…'}</span>
                <span className="text-accent-blue">{jobStatus.progress_percent}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-accent-blue transition-all duration-500" style={{ width: `${jobStatus.progress_percent}%` }} />
              </div>
            </div>
          )}
          <button
            type="submit"
            disabled={isSubmitting || urlCount === 0}
            className="w-full rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-blue/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Extracting…' : `Extract${urlCount > 0 ? ` ${urlCount}` : ''} Transcript${urlCount !== 1 ? 's' : ''}`}
          </button>
        </form>
      </div>
    </div>
  );
}
