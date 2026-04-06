/**
 * ScriptRenderer — Typed renderer for Script (Doc 5).
 *
 * Renders spoken text with beat labels, stage directions in grey italics,
 * duration markers per section, total word count.
 */

import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { SectionHeader } from './shared/SectionHeader';
import { CardWrapper } from './shared/CardWrapper';
import { CollapsibleSection } from './shared/CollapsibleSection';
import { CitationPill } from './shared/CitationPill';
import { EditableSection } from './shared/EditableSection';
import type { ScriptData, ScriptSection } from '@/types/documents';

export interface ScriptRendererProps {
  data: ScriptData;
  showDetails?: boolean;
  jobId?: string;
}

function ScriptSectionCard({ section, showDetails }: { section: ScriptSection; showDetails?: boolean }) {
  return (
    <CardWrapper accentColor="cyan">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-caption px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/20 font-medium">
            {section.beat_label}
          </span>
          <span className="text-caption text-white/30 font-mono">{section.section_id}</span>
        </div>
        <span className="text-caption text-white/30">{section.duration_estimate}</span>
      </div>

      {section.stage_direction && (
        <p className="text-xs text-white/30 italic mb-2">{section.stage_direction}</p>
      )}

      <div className="prose prose-invert prose-sm max-w-none">
        <p className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">{section.spoken_text}</p>
      </div>

      {showDetails && section.source_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {section.source_ids.map((id) => (
            <CitationPill key={id} sourceId={id} />
          ))}
        </div>
      )}
    </CardWrapper>
  );
}

export function ScriptRenderer({ data, showDetails = false, jobId }: ScriptRendererProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white/95 leading-tight">{data.title}</h1>
        <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-white/40">
          <span className="capitalize">{data.tone}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>{data.estimated_duration}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>{data.total_word_count.toLocaleString()} words</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>{data.source_count} source{data.source_count !== 1 ? 's' : ''}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>Doc 5</span>
        </div>
      </div>

      {/* Story Arc */}
      <div className="bg-cyan-900/15 border border-cyan-700/20 rounded-lg p-3">
        <p className="text-xs font-medium text-cyan-400/70 mb-1">Story Arc</p>
        <p className="text-sm text-white/70 capitalize">{data.story_arc}</p>
      </div>

      {/* Hook */}
      <SectionHeader title="Opening Hook" accentColor="cyan" />
      <CardWrapper accentColor="cyan">
        <div className="bg-cyan-500/5 rounded-lg p-4 border border-cyan-500/10">
          <p className="text-base text-white/90 font-medium leading-relaxed">{data.hook.text}</p>
          <p className="text-xs text-white/40 mt-2">
            Type: {data.hook.hook_type} · Source: {data.hook.source_id}
          </p>
        </div>
      </CardWrapper>

      {/* Script Sections */}
      <SectionHeader title="Script" count={data.sections.length} accentColor="cyan" />
      <div className="space-y-3">
        {data.sections.map((section) => (
          jobId ? (
            <EditableSection key={section.section_id} sectionId={section.section_id} docType="doc_5" jobId={jobId}>
              <ScriptSectionCard section={section} showDetails={showDetails} />
            </EditableSection>
          ) : (
            <ScriptSectionCard key={section.section_id} section={section} showDetails={showDetails} />
          )
        ))}
      </div>

      {/* Outro */}
      <SectionHeader title="Outro" accentColor="cyan" />
      <CardWrapper>
        <p className="text-sm text-white/80 leading-relaxed">{data.outro.text}</p>
        {data.outro.call_to_action && (
          <p className="text-sm font-medium text-amber-300/80 mt-3">{data.outro.call_to_action}</p>
        )}
      </CardWrapper>

      {/* Sources */}
      {data.description_sources.length > 0 && (
        <CollapsibleSection label="Sources" itemCount={data.description_sources.length}>
          <div className="space-y-2">
            {data.description_sources.map((ds) => (
              <div key={ds.source_id} className="text-sm text-white/60">
                <span className="font-medium text-white/80">{ds.title}</span>
                {ds.creator && <span className="text-white/40"> by {ds.creator}</span>}
                {ds.url && (
                  <>
                    {' — '}
                    <a href={ds.url} target="_blank" rel="noopener noreferrer"
                      className="text-cyan-400/70 hover:text-cyan-400 underline">
                      {ds.url}
                    </a>
                  </>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
}

export default ScriptRenderer;
