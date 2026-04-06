/**
 * script-renderer — Doc 5 renderer. Sequential beat sections with timeline-style left border.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from '@/components/ui/accordion';
import { CitationPill } from './shared/citation-pill';
import { SectionHeader } from './shared/section-header';
import type { ScriptData, ScriptSection } from '@/types/documents';

function ScriptSectionCard({ section, showDetails }: { section: ScriptSection; showDetails?: boolean }) {
  return (
    <Card className="border-l-2 border-l-cyan-500/60 border-border bg-background/60">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-caption px-2 py-0 bg-cyan-500/10 text-cyan-300 border-cyan-500/20 font-medium">
              {section.beat_label}
            </Badge>
            <span className="text-caption text-muted-foreground/60 font-mono">{section.section_id}</span>
          </div>
          {section.duration_estimate && (
            <span className="text-caption text-muted-foreground/70">{section.duration_estimate}</span>
          )}
        </div>
        {section.stage_direction && (
          <p className="text-xs text-muted-foreground/70 italic">{section.stage_direction}</p>
        )}
        <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{section.spoken_text}</p>
        {showDetails && section.source_ids?.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {section.source_ids.map((id) => <CitationPill key={id} id={id} />)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ScriptRendererProps {
  content: any;
  showDetails?: boolean;
}

export function ScriptRenderer({ content, showDetails = false }: ScriptRendererProps) {
  const data = content as ScriptData;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground leading-tight">{data?.title}</h1>
        <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground/70">
          {data?.tone && <span className="capitalize">{data.tone}</span>}
          <span className="w-1 h-1 rounded-full bg-secondary" />
          {data?.estimated_duration && <span>{data.estimated_duration}</span>}
          <span className="w-1 h-1 rounded-full bg-secondary" />
          {data?.total_word_count != null && <span>{data.total_word_count.toLocaleString()} words</span>}
          {data?.source_count != null && (
            <><span className="w-1 h-1 rounded-full bg-secondary" /><span>{data.source_count} source{data.source_count !== 1 ? 's' : ''}</span></>
          )}
        </div>
      </div>

      {/* Story Arc */}
      {data?.story_arc && (
        <div className="bg-cyan-900/10 border border-cyan-700/20 rounded-lg p-3">
          <p className="text-xs font-medium text-cyan-400/70 mb-1">Story Arc</p>
          <p className="text-sm text-muted-foreground capitalize">{data.story_arc}</p>
        </div>
      )}

      {/* Opening Hook */}
      {data?.hook && (
        <div>
          <SectionHeader title="Opening Hook" className="mb-2" />
          <Card className="bg-cyan-900/10 border-cyan-700/20">
            <CardContent className="p-4">
              <p className="text-base text-foreground font-medium leading-relaxed">{data.hook.text}</p>
              <p className="text-xs text-muted-foreground/70 mt-2">
                {data.hook.hook_type} · {data.hook.source_id}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Script sections */}
      {data?.sections?.length > 0 && (
        <div>
          <SectionHeader title="Script" count={data.sections.length} className="mb-3" />
          <div className="space-y-3">
            {data.sections.map((section) => (
              <ScriptSectionCard key={section.section_id} section={section} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Outro */}
      {data?.outro && (
        <div>
          <SectionHeader title="Outro" className="mb-2" />
          <Card className="bg-background/40 border-border">
            <CardContent className="p-4 space-y-2">
              <p className="text-sm text-foreground leading-relaxed">{data.outro.text}</p>
              {data.outro.call_to_action && (
                <p className="text-sm font-medium text-amber-300/80">{data.outro.call_to_action}</p>
              )}
            </CardContent>
          </Card>
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
                      <> — <a href={ds.url} target="_blank" rel="noopener noreferrer" className="text-cyan-400/70 hover:text-cyan-400 underline">{ds.url}</a></>
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
