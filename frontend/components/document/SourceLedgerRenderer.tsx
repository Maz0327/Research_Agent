/**
 * SourceLedgerRenderer — Typed renderer for Doc 0 (Source Ledger).
 *
 * Renders each source as a card with status, type, transcript provenance,
 * and key findings. Replaces the flat markdown list with structured cards.
 */

import type { SourceLedgerData, SourceEntry } from '@/types/documents';
import { SectionHeader } from './shared/SectionHeader';
import { CardWrapper } from './shared/CardWrapper';
import { SectionActions } from './SectionActions';
import { formatInternalId } from '@/lib/document-formatters';
import { useState } from 'react';

interface SourceLedgerRendererProps {
  data: SourceLedgerData;
  showDetails?: boolean;
}

const statusStyles: Record<string, { dot: string; label: string }> = {
  ingested: { dot: 'bg-green-400', label: 'Ingested' },
  partial: { dot: 'bg-yellow-400', label: 'Partial' },
  failed: { dot: 'bg-red-400', label: 'Failed' },
};

const typeIcons: Record<string, string> = {
  youtube: '📺',
  article: '📄',
  reddit: '💬',
  screenshot: '🖼️',
  text: '📝',
};

function SourceCard({ source, showDetails }: { source: SourceEntry; showDetails: boolean }) {
  const [showFullText, setShowFullText] = useState(false);
  const status = statusStyles[source.status] || statusStyles.ingested;
  const icon = typeIcons[source.source_type?.toLowerCase()] || '📄';
  const sourceText = [source.title, ...(source.skim_summary || [])].join('\n');
  return (
    <div className="group">
    <CardWrapper accentColor={source.status === 'failed' ? 'bg-red-500' : source.status === 'partial' ? 'bg-yellow-500' : 'bg-green-500'}>
      <div className="absolute top-2 right-2">
        <SectionActions content={sourceText} sectionTitle={source.title} />
      </div>
      {/* Header row */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg flex-shrink-0">{icon}</span>
          {showDetails && (
            <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider flex-shrink-0">
              {formatInternalId(source.source_id)} ({source.source_id})
            </span>
          )}
          <span className="text-[11px] font-medium text-gray-600 flex-shrink-0">
            {source.source_type}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className={`w-2 h-2 rounded-full ${status.dot}`} />
          <span className="text-[11px] font-medium text-gray-400">{status.label}</span>
        </div>
      </div>

      {/* Title */}
      {source.url ? (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[14px] sm:text-[15px] font-medium text-blue-400 hover:text-blue-300 transition leading-snug block mb-2"
        >
          {source.title}
          <svg className="h-3 w-3 inline-block ml-1 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      ) : (
        <p className="text-[15px] font-medium text-gray-200 leading-snug mb-2">{source.title}</p>
      )}

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-2 sm:gap-x-4 gap-y-1 text-[12px] text-gray-500 mb-3">
        {source.creator && <span>{source.creator}</span>}
        {source.published && <span>{source.published}</span>}
        {source.duration && <span>{source.duration}</span>}
        {source.word_count && <span>{source.word_count.toLocaleString()} words</span>}
      </div>

      {/* Skim summary */}
      {source.skim_summary && source.skim_summary.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">Key Findings</p>
          <ul className="space-y-1">
            {source.skim_summary.map((item, i) => (
              <li key={i} className="text-[14px] text-gray-300 leading-relaxed flex gap-2">
                <span className="text-gray-600 flex-shrink-0 mt-0.5">&#8226;</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Transcript provenance */}
      {source.transcript_provenance && (
        <div className="flex flex-wrap gap-2 text-[11px] mt-2 pt-2 border-t border-gray-700/30">
          <span className="text-gray-500">Transcript:</span>
          <span className="text-gray-400">{source.transcript_provenance.transcript_source}</span>
          <span className={source.transcript_provenance.transcript_status === 'success' ? 'text-green-500' : 'text-yellow-500'}>
            {source.transcript_provenance.transcript_status === 'success' ? '✓' : '⚠'} {source.transcript_provenance.transcript_status}
          </span>
          {source.transcript_provenance.notes && (
            <span className="text-gray-600">({source.transcript_provenance.notes})</span>
          )}
        </div>
      )}

      {/* Failure reason */}
      {source.failure_reason && (
        <div className="mt-2 pt-2 border-t border-red-900/30">
          <p className="text-[12px] text-red-400">{source.failure_reason}</p>
        </div>
      )}

      {/* Full text toggle */}
      {source.full_text && (
        <div className="mt-3 pt-2 border-t border-gray-700/30">
          <button
            onClick={() => setShowFullText(!showFullText)}
            className="text-[12px] text-blue-400/70 hover:text-blue-300 transition flex items-center gap-1.5 cursor-pointer"
          >
            <span
              className="text-gray-500 transition-transform duration-200 text-[10px]"
              style={{ transform: showFullText ? 'rotate(90deg)' : 'rotate(0deg)' }}
            >
              &#9654;
            </span>
            {showFullText ? 'Hide full text' : 'Show full text'}
          </button>
          {showFullText && (
            <pre className="mt-2 text-[12px] sm:text-[13px] text-gray-400 leading-relaxed whitespace-pre-wrap max-h-[300px] sm:max-h-[400px] overflow-y-auto bg-gray-900/50 rounded p-2 sm:p-3 border border-gray-700/30">
              {source.full_text}
            </pre>
          )}
        </div>
      )}
      {source.full_text_unavailable_reason && !source.full_text && (
        <p className="mt-2 text-[11px] text-gray-600 italic">
          Full text unavailable: {source.full_text_unavailable_reason}
        </p>
      )}
    </CardWrapper>
    </div>
  );
}

export function SourceLedgerRenderer({ data, showDetails = false }: SourceLedgerRendererProps) {
  const totalSources = data.sources?.length || 0;
  const ingested = data.sources?.filter(s => s.status === 'ingested').length || 0;
  const failed = data.sources?.filter(s => s.status === 'failed').length || 0;

  return (
    <div className="space-y-5 sm:space-y-8">
      {/* Topic header */}
      {data.topic && (
        <div className="text-center pb-4 border-b border-gray-700/30">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Research Topic</p>
          <p className="text-lg font-semibold text-gray-100">{data.topic}</p>
        </div>
      )}

      {/* Stats bar */}
      <div className="flex flex-wrap gap-4 justify-center">
        <Stat label="Total Sources" value={totalSources} />
        <Stat label="Ingested" value={ingested} color="text-green-400" />
        {failed > 0 && <Stat label="Failed" value={failed} color="text-red-400" />}
      </div>

      {/* Source cards */}
      <div>
        <SectionHeader
          title="Sources Analyzed"
          count={totalSources}
          accentColor="bg-gray-500"
        />
        <div className="mt-4 space-y-4">
          {data.sources?.map((source) => (
            <SourceCard key={source.source_id} source={source} showDetails={showDetails} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color = 'text-gray-100' }: { label: string; value: number; color?: string }) {
  return (
    <div className="text-center px-3 sm:px-4">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-[11px] text-gray-500 uppercase tracking-wider">{label}</p>
    </div>
  );
}
