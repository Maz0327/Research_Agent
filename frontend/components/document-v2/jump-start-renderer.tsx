/**
 * jump-start-renderer — Doc 1 renderer using shadcn Accordion.
 * Groups: Research Threads (themes+key points), Tensions, Cross-Cutting Analysis.
 */

import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from '@/components/ui/accordion';
import { Card, CardContent } from '@/components/ui/card';
import { ConfidenceBadge } from './shared/confidence-badge';
import { CitationPill } from './shared/citation-pill';
import { SectionHeader } from './shared/section-header';
import type {
  JumpStartData, ResearchThread, Tension, Gap,
} from '@/types/documents';

// ── Sub-components ────────────────────────────────────────────────────────────

function ThreadCard({ thread }: { thread: ResearchThread }) {
  const theme = thread.theme;
  const allBoosters = [
    ...(thread.booster_search_queries ?? []).map((b: any) => ({ ...b, _type: 'Search' })),
    ...(thread.booster_research_questions ?? []).map((b: any) => ({ ...b, _type: 'Research Q' })),
    ...(thread.booster_primary_sources ?? []).map((b: any) => ({ ...b, _type: 'Find' })),
    ...(thread.booster_missing_perspectives ?? []).map((b: any) => ({ ...b, _type: 'Missing Voice' })),
  ];

  return (
    <Card className="bg-background/60 border-l-2 border-l-blue-500/60 border-border">
      <CardContent className="p-4 space-y-3">
        {/* Theme header */}
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {theme?.is_consensus && (
              <span className="text-caption px-1.5 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-800/30">
                Multiple sources agree
              </span>
            )}
            {theme?.confidence && <ConfidenceBadge level={theme.confidence} />}
          </div>
          <h3 className="text-body-lg font-semibold text-foreground mb-0.5">{theme?.label}</h3>
          <p className="text-body-sm text-muted-foreground leading-relaxed">{theme?.description}</p>
          {theme?.sources_supporting?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {theme.sources_supporting.map((sid: string) => <CitationPill key={sid} id={sid} />)}
            </div>
          )}
        </div>

        {/* Key points */}
        {thread.key_points?.length > 0 && (
          <div>
            <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-1.5">Key Points</p>
            <ul className="space-y-1.5">
              {thread.key_points.map((kp) => (
                <li key={kp.key_point_id} className="flex gap-2 items-start">
                  <span className="text-blue-500/50 mt-1 flex-shrink-0">•</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-body-sm text-foreground leading-relaxed">{kp.statement}</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {kp.source_ids?.map((sid) => <CitationPill key={sid} id={sid} />)}
                      {kp.confidence && <ConfidenceBadge level={kp.confidence} />}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Gaps */}
        {thread.gaps?.length > 0 && (
          <div>
            <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-1.5">Open Questions</p>
            <div className="space-y-2">
              {thread.gaps.map((gap: Gap) => (
                <div key={gap.gap_id} className="bg-amber-900/10 border border-amber-800/20 rounded-lg p-3 pl-4 relative overflow-hidden">
                  <div className="absolute top-0 left-0 bottom-0 w-1 bg-amber-500/60 rounded-l-lg" />
                  <p className="text-body-sm font-medium text-foreground">{gap.label}</p>
                  <p className="text-body-sm text-muted-foreground mt-0.5">{gap.description}</p>
                  {gap.suggested_research_direction && (
                    <p className="text-caption text-green-400/80 mt-1">→ {gap.suggested_research_direction}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Booster directions */}
        {allBoosters.length > 0 && (
          <div>
            <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-1.5">Deep Research Directions</p>
            <div className="space-y-1">
              {allBoosters.map((b: any, i: number) => (
                <div key={i} className="flex items-start gap-2 py-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-secondary flex-shrink-0 mt-1.5" />
                  <div className="flex-1 min-w-0">
                    <span className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mr-2">{b._type}</span>
                    <span className="text-body-sm text-muted-foreground">{b.query || b.question || b.description || ''}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TensionCard({ tension }: { tension: Tension }) {
  return (
    <Card className="bg-background/60 border-l-2 border-l-red-500/60 border-border">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {tension.is_cross_source && (
            <span className="text-caption px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/30">Cross-source</span>
          )}
          {tension.confidence && <ConfidenceBadge level={tension.confidence} />}
        </div>
        <p className="text-body font-medium text-foreground">{tension.label}</p>
        <p className="text-body-sm text-muted-foreground leading-relaxed">{tension.description}</p>
        <div className="grid grid-cols-2 gap-2 mt-2">
          {tension.sources_position_a?.length > 0 && (
            <div className="bg-card/30 rounded p-2">
              <p className="text-caption font-medium text-muted-foreground/70 uppercase mb-1">Position A</p>
              <div className="flex flex-wrap gap-1">
                {tension.sources_position_a.map((sid) => <CitationPill key={sid} id={sid} />)}
              </div>
            </div>
          )}
          {tension.sources_position_b?.length > 0 && (
            <div className="bg-card/30 rounded p-2">
              <p className="text-caption font-medium text-muted-foreground/70 uppercase mb-1">Position B</p>
              <div className="flex flex-wrap gap-1">
                {tension.sources_position_b.map((sid) => <CitationPill key={sid} id={sid} />)}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

interface JumpStartRendererProps {
  content: any;
}

export function JumpStartRenderer({ content }: JumpStartRendererProps) {
  const data = content as JumpStartData;
  const threads = data?.research_threads ?? [];
  const tensions = data?.tensions ?? [];
  const cross = data?.cross_cutting;

  // Default open: first 3 thread items
  const defaultOpen = threads.slice(0, 3).map((_: any, i: number) => `thread-${i}`);

  return (
    <div className="space-y-6">
      {/* Stats bar */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-body-sm text-muted-foreground">
        <span>{data?.current_corpus?.source_count ?? 0} sources</span>
        <span className="text-muted-foreground/60">·</span>
        <span>{threads.length} patterns</span>
        {data?.key_points?.length > 0 && (
          <><span className="text-muted-foreground/60">·</span><span>{data.key_points.length} findings</span></>
        )}
        {tensions.length > 0 && (
          <><span className="text-muted-foreground/60">·</span><span>{tensions.length} tensions</span></>
        )}
      </div>

      {/* Warnings */}
      {data?.warnings?.length > 0 && (
        <div className="space-y-1.5">
          {data.warnings.map((w: string, i: number) => (
            <div key={i} className="flex gap-2 text-body-sm text-yellow-400/80 bg-yellow-900/10 border border-yellow-800/20 rounded-lg px-3 py-2">
              <span>⚠</span><span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Next steps */}
      {data?.next_steps?.length > 0 && (
        <div>
          <SectionHeader title="Next Steps" count={data.next_steps.length} className="mb-3" />
          <ol className="space-y-2">
            {data.next_steps.map((step: string, i: number) => (
              <li key={i} className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-full bg-green-900/40 text-green-400 text-caption font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-body-sm text-foreground leading-relaxed">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Research Threads */}
      {threads.length > 0 && (
        <div>
          <SectionHeader title="What We Found" count={threads.length} className="mb-3" />
          <Accordion type="multiple" defaultValue={defaultOpen} className="space-y-2">
            {threads.map((thread: ResearchThread, i: number) => (
              <AccordionItem key={thread.theme?.theme_id ?? i} value={`thread-${i}`} className="border-0">
                <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
                  <SectionHeader
                    title={thread.theme?.label ?? `Thread ${i + 1}`}
                    count={thread.key_points?.length}
                    confidence={thread.theme?.confidence}
                  />
                </AccordionTrigger>
                <AccordionContent className="pt-0 pb-0">
                  <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
                    <ThreadCard thread={thread} />
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      )}

      {/* Tensions */}
      {tensions.length > 0 && (
        <div>
          <SectionHeader title="Conflicting Views" count={tensions.length} className="mb-3" />
          <Accordion type="multiple" className="space-y-2">
            {tensions.map((t: Tension, i: number) => (
              <AccordionItem key={t.tension_id} value={`tension-${i}`} className="border-0">
                <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
                  <SectionHeader title={t.label} confidence={t.confidence} />
                </AccordionTrigger>
                <AccordionContent className="pt-0 pb-0">
                  <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
                    <TensionCard tension={t} />
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      )}

      {/* Cross-cutting analysis */}
      {cross && (cross.confirmed?.length > 0 || cross.conflicts?.length > 0 || cross.single_source?.length > 0) && (
        <div>
          <SectionHeader title="Cross-Source Analysis" className="mb-3" />
          <div className="space-y-3">
            {cross.confirmed?.map((item: any, i: number) => (
              <Card key={i} className="bg-green-900/10 border-green-800/20">
                <CardContent className="p-3">
                  <p className="text-caption font-medium text-green-400 uppercase mb-1">Confirmed across sources</p>
                  <p className="text-body-sm text-foreground">{item.statement}</p>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {item.sources?.map((sid: string) => <CitationPill key={sid} id={sid} />)}
                  </div>
                </CardContent>
              </Card>
            ))}
            {cross.conflicts?.map((item: any, i: number) => (
              <Card key={i} className="bg-red-900/10 border-red-800/20">
                <CardContent className="p-3">
                  <p className="text-caption font-medium text-red-400 uppercase mb-1">Conflict</p>
                  <p className="text-body-sm text-foreground">{item.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
