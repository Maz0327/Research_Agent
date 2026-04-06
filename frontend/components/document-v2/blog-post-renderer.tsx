/**
 * blog-post-renderer — Doc 7 renderer. Sections with ProseBlock body, SEO card, keywords.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from '@/components/ui/accordion';
import { ProseBlock } from './shared/prose-block';
import { CitationPill } from './shared/citation-pill';
import { SectionHeader } from './shared/section-header';
import type { BlogPostData, BlogSection } from '@/types/documents';

function SectionCard({ section, showDetails }: { section: BlogSection; showDetails?: boolean }) {
  return (
    <Card className="border-l-2 border-l-emerald-500/60 border-border bg-background/60">
      <CardContent className="p-4 space-y-2">
        <h3 className="text-base font-semibold text-foreground">{section.heading}</h3>
        <ProseBlock content={section.body} />
        {showDetails && (section.source_ids?.length > 0 || section.claim_ids?.length > 0) && (
          <div className="flex flex-wrap gap-1 pt-1">
            {section.source_ids?.map((id) => <CitationPill key={id} id={id} />)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface BlogPostRendererProps {
  content: any;
  showDetails?: boolean;
}

export function BlogPostRenderer({ content, showDetails = false }: BlogPostRendererProps) {
  const data = content as BlogPostData;
  const sections = data?.sections ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground leading-tight">{data?.title}</h1>
        {data?.subtitle && <p className="text-base text-muted-foreground mt-1">{data.subtitle}</p>}
        <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground/70">
          {data?.estimated_reading_time && <span>{data.estimated_reading_time}</span>}
          {data?.source_count != null && (
            <><span className="w-1 h-1 rounded-full bg-secondary" /><span>{data.source_count} source{data.source_count !== 1 ? 's' : ''}</span></>
          )}
        </div>
      </div>

      {/* SEO meta */}
      {data?.meta_description && (
        <div className="bg-emerald-900/10 border border-emerald-700/20 rounded-lg p-3">
          <p className="text-xs font-medium text-emerald-400/70 mb-1">Meta Description</p>
          <p className="text-sm text-muted-foreground">{data.meta_description}</p>
        </div>
      )}

      {/* SEO keywords */}
      {data?.seo_keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {data.seo_keywords.map((kw: string) => (
            <Badge key={kw} variant="outline" className="text-caption px-2 py-0 text-muted-foreground border-border/40 bg-card/60">
              {kw}
            </Badge>
          ))}
        </div>
      )}

      {/* Article sections */}
      {sections.length > 0 && (
        <div>
          <SectionHeader title="Article" count={sections.length} className="mb-3" />
          <div className="space-y-4">
            {sections.map((section) => (
              <SectionCard key={section.section_id} section={section} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Conclusion */}
      {data?.conclusion && (
        <div>
          <SectionHeader title="Conclusion" className="mb-2" />
          <Card className="bg-background/40 border-border">
            <CardContent className="p-4">
              <ProseBlock content={data.conclusion} />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Call to action */}
      {data?.call_to_action && (
        <div className="bg-amber-900/10 border border-amber-700/20 rounded-lg p-4 text-center">
          <p className="text-sm font-medium text-amber-300/80">{data.call_to_action}</p>
        </div>
      )}

      {/* Sources */}
      {data?.description_sources?.length > 0 && (
        <Accordion type="single" collapsible>
          <AccordionItem value="sources" className="border-0">
            <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline">
              <SectionHeader title="Sources" count={data.description_sources.length} />
            </AccordionTrigger>
            <AccordionContent className="pt-0 pb-0">
              <div className="border border-t-0 border-border rounded-b-lg p-4 space-y-2">
                {data.description_sources.map((ds: any) => (
                  <div key={ds.source_id} className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{ds.title}</span>
                    {ds.creator && <span className="text-muted-foreground/70"> by {ds.creator}</span>}
                    {ds.url && (
                      <> — <a href={ds.url} target="_blank" rel="noopener noreferrer" className="text-emerald-400/70 hover:text-emerald-400 underline">{ds.url}</a></>
                    )}
                  </div>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
    </div>
  );
}
