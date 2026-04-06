/**
 * source-ledger-renderer — Doc 0 renderer using shadcn Card + Badge.
 * Table/card layout per source with type color coding and status indicators.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CitationPill } from './shared/citation-pill';
import type { SourceLedgerData, SourceEntry } from '@/types/documents';

const TYPE_STYLES: Record<string, string> = {
  youtube:    'bg-red-500/10 text-red-400 border-red-500/20',
  article:    'bg-blue-500/10 text-blue-400 border-blue-500/20',
  text:       'bg-purple-500/10 text-purple-400 border-purple-500/20',
  ocr:        'bg-orange-500/10 text-orange-400 border-orange-500/20',
  reddit:     'bg-amber-500/10 text-amber-400 border-amber-500/20',
  screenshot: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
};

const STATUS_STYLES: Record<string, { dot: string; label: string }> = {
  ingested: { dot: 'bg-green-400', label: 'Ingested' },
  partial:  { dot: 'bg-yellow-400', label: 'Partial' },
  failed:   { dot: 'bg-red-400', label: 'Failed' },
};

function SourceCard({ source }: { source: SourceEntry }) {
  const typeKey = (source.source_type ?? '').toLowerCase();
  const typeStyle = TYPE_STYLES[typeKey] ?? 'bg-card text-muted-foreground border-border/20';
  const status = STATUS_STYLES[source.status] ?? STATUS_STYLES.ingested;

  return (
    <Card className="bg-card border-border">
      <CardContent className="p-4 space-y-2">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <CitationPill id={source.source_id} />
            <Badge variant="outline" className={`text-caption px-1.5 py-0 ${typeStyle}`}>
              {source.source_type}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span className={`w-2 h-2 rounded-full ${status.dot}`} />
            <span className="text-caption text-muted-foreground/70">{status.label}</span>
          </div>
        </div>

        {/* Title */}
        {source.url ? (
          <a href={source.url} target="_blank" rel="noopener noreferrer"
            className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors leading-snug block">
            {source.title}
          </a>
        ) : (
          <p className="text-sm font-medium text-foreground leading-snug">{source.title}</p>
        )}

        {/* Meta */}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-caption text-muted-foreground/70">
          {source.creator && <span>{source.creator}</span>}
          {source.published && <span>{source.published}</span>}
          {source.duration && <span>{source.duration}</span>}
          {source.word_count && <span>{source.word_count.toLocaleString()} words</span>}
        </div>

        {/* Skim summary */}
        {source.skim_summary && source.skim_summary.length > 0 && (
          <ul className="space-y-1 pt-1">
            {source.skim_summary.map((item, i) => (
              <li key={i} className="text-body-sm text-muted-foreground leading-relaxed flex gap-2">
                <span className="text-muted-foreground/60 flex-shrink-0 mt-0.5">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Transcript provenance */}
        {source.transcript_provenance && (
          <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-caption pt-1 border-t border-border">
            <span className="text-muted-foreground/70">Transcript:</span>
            <span className="text-muted-foreground">{source.transcript_provenance.transcript_source}</span>
            <span className={source.transcript_provenance.transcript_status === 'success' ? 'text-green-500' : 'text-yellow-500'}>
              {source.transcript_provenance.transcript_status === 'success' ? '✓' : '⚠'} {source.transcript_provenance.transcript_status}
            </span>
          </div>
        )}

        {/* Failure reason */}
        {source.failure_reason && (
          <p className="text-body-sm text-red-400 pt-1 border-t border-red-900/20">{source.failure_reason}</p>
        )}
      </CardContent>
    </Card>
  );
}

interface SourceLedgerRendererProps {
  content: any;
}

export function SourceLedgerRenderer({ content }: SourceLedgerRendererProps) {
  const data = content as SourceLedgerData;
  const sources = data?.sources ?? [];
  const ingested = sources.filter((s) => s.status === 'ingested').length;
  const failed = sources.filter((s) => s.status === 'failed').length;

  return (
    <div className="space-y-6">
      {/* Topic */}
      {data?.topic && (
        <div className="text-center pb-4 border-b border-border">
          <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-1">Research Topic</p>
          <p className="text-base font-semibold text-foreground">{data.topic}</p>
        </div>
      )}

      {/* Stats */}
      <div className="flex flex-wrap gap-6 justify-center">
        <div className="text-center">
          <p className="text-2xl font-bold text-foreground">{sources.length}</p>
          <p className="text-caption text-muted-foreground/70 uppercase tracking-wider">Total</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-green-400">{ingested}</p>
          <p className="text-caption text-muted-foreground/70 uppercase tracking-wider">Ingested</p>
        </div>
        {failed > 0 && (
          <div className="text-center">
            <p className="text-2xl font-bold text-red-400">{failed}</p>
            <p className="text-caption text-muted-foreground/70 uppercase tracking-wider">Failed</p>
          </div>
        )}
      </div>

      {/* Source cards */}
      <div className="space-y-3">
        {sources.map((source) => (
          <SourceCard key={source.source_id} source={source} />
        ))}
      </div>
    </div>
  );
}
