/**
 * BlogPostRenderer — Typed renderer for Blog Post (Doc 7).
 *
 * Renders sections with headings, markdown body, source citation pills,
 * SEO metadata, and conclusion. Follows CreatorBriefRenderer design patterns.
 */

import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { SectionHeader } from './shared/SectionHeader';
import { CardWrapper } from './shared/CardWrapper';
import { CollapsibleSection } from './shared/CollapsibleSection';
import { CitationPill } from './shared/CitationPill';
import { EditableSection } from './shared/EditableSection';
import type { BlogPostData, BlogSection } from '@/types/documents';

export interface BlogPostRendererProps {
  data: BlogPostData;
  showDetails?: boolean;
  jobId?: string;
}

function SectionCard({ section, showDetails }: { section: BlogSection; showDetails?: boolean }) {
  return (
    <CardWrapper accentColor="emerald">
      <h3 className="text-base font-semibold text-white/90 mb-2">{section.heading}</h3>
      <div className="prose prose-invert prose-sm max-w-none">
        <MarkdownRenderer content={section.body} />
      </div>
      {showDetails && (section.claim_ids.length > 0 || section.source_ids.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {section.source_ids.map((id) => (
            <CitationPill key={id} sourceId={id} />
          ))}
        </div>
      )}
    </CardWrapper>
  );
}

export function BlogPostRenderer({ data, showDetails = false, jobId }: BlogPostRendererProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white/95 leading-tight">{data.title}</h1>
        {data.subtitle && (
          <p className="text-base text-white/50 mt-1">{data.subtitle}</p>
        )}
        <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-white/40">
          <span>{data.estimated_reading_time}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>{data.source_count} source{data.source_count !== 1 ? 's' : ''}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span>Doc 7</span>
        </div>
      </div>

      {/* Meta Description (SEO) */}
      <div className="bg-emerald-900/15 border border-emerald-700/20 rounded-lg p-3">
        <p className="text-xs font-medium text-emerald-400/70 mb-1">Meta Description</p>
        <p className="text-sm text-white/70">{data.meta_description}</p>
      </div>

      {/* SEO Keywords */}
      {data.seo_keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {data.seo_keywords.map((kw) => (
            <span
              key={kw}
              className="text-caption px-2 py-0.5 rounded-full bg-white/[0.06] text-white/50 border border-white/[0.06]"
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Sections */}
      <SectionHeader title="Article" count={data.sections.length} accentColor="emerald" />
      <div className="space-y-4">
        {data.sections.map((section) => (
          jobId ? (
            <EditableSection key={section.section_id} sectionId={section.section_id} docType="doc_7" jobId={jobId}>
              <SectionCard section={section} showDetails={showDetails} />
            </EditableSection>
          ) : (
            <SectionCard key={section.section_id} section={section} showDetails={showDetails} />
          )
        ))}
      </div>

      {/* Conclusion */}
      <SectionHeader title="Conclusion" accentColor="emerald" />
      <CardWrapper>
        <div className="prose prose-invert prose-sm max-w-none">
          <MarkdownRenderer content={data.conclusion} />
        </div>
      </CardWrapper>

      {/* Call to Action */}
      {data.call_to_action && (
        <div className="bg-amber-900/15 border border-amber-700/20 rounded-lg p-4 text-center">
          <p className="text-sm font-medium text-amber-300/80">{data.call_to_action}</p>
        </div>
      )}

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
                    <a
                      href={ds.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-400/70 hover:text-emerald-400 underline"
                    >
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

export default BlogPostRenderer;
