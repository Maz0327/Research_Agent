/**
 * semantic-brief-renderer — Doc 2 renderer using shadcn Accordion + Card.
 * Sections: SCQA (always visible), Themes (Accordion), Tensions, Gaps, Speculative.
 */

import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from '@/components/ui/accordion';
import { Card, CardContent } from '@/components/ui/card';
import { ConfidenceBadge } from './shared/confidence-badge';
import { CitationPill } from './shared/citation-pill';
import { SectionHeader } from './shared/section-header';
import type { SemanticBriefData, Theme, Tension, Gap, KeyPoint } from '@/types/documents';

// ── SCQA ──────────────────────────────────────────────────────────────────────

function SCQASection({ scqa }: { scqa: any }) {
  const items = [
    { label: 'Situation',    value: scqa.situation,   color: 'text-blue-400' },
    { label: 'Complication', value: scqa.complication, color: 'text-amber-400' },
    { label: 'Question',     value: scqa.question,     color: 'text-purple-400' },
    { label: 'Answer',       value: scqa.answer,       color: 'text-green-400' },
  ].filter((i) => i.value);

  return (
    <Card className="bg-indigo-900/10 border-indigo-800/20">
      <CardContent className="p-4 space-y-3">
        <p className="text-[10px] font-medium text-indigo-400 uppercase tracking-wider">The Big Picture</p>
        {items.map((item) => (
          <div key={item.label}>
            <span className={`text-[11px] font-semibold uppercase tracking-wider ${item.color}`}>{item.label}</span>
            <p className="text-[13px] text-zinc-200 leading-relaxed mt-0.5">{item.value}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Theme card ────────────────────────────────────────────────────────────────

function ThemeCard({ theme, keyPoints }: { theme: Theme; keyPoints: KeyPoint[] }) {
  const relatedKPs = theme.related_key_points
    ?.map((id) => keyPoints.find((kp) => kp.key_point_id === id))
    .filter(Boolean) as KeyPoint[];

  return (
    <Card className="bg-zinc-900/60 border-l-2 border-l-purple-500/60 border-border">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {theme.is_consensus && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-800/30">
              Multiple sources agree
            </span>
          )}
          {theme.confidence && <ConfidenceBadge level={theme.confidence} />}
        </div>
        <h3 className="text-[15px] font-semibold text-zinc-100">{theme.label}</h3>
        <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">So what?</p>
        <p className="text-[13px] text-zinc-400 leading-relaxed">{theme.description}</p>
        {theme.sources_supporting?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {theme.sources_supporting.map((sid) => <CitationPill key={sid} id={sid} />)}
          </div>
        )}
        {relatedKPs?.length > 0 && (
          <div className="pt-2 border-t border-border">
            <p className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-1.5">Related Findings</p>
            <ul className="space-y-1">
              {relatedKPs.map((kp) => (
                <li key={kp.key_point_id} className="text-[12px] text-zinc-300 flex gap-2">
                  <span className="text-purple-500/50 flex-shrink-0">•</span>
                  <span>{kp.statement}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Tension card ──────────────────────────────────────────────────────────────

function TensionCard({ tension }: { tension: Tension }) {
  return (
    <Card className="bg-zinc-900/60 border-l-2 border-l-red-500/60 border-border">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {tension.is_cross_source && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/30">Sources disagree</span>
          )}
          {tension.confidence && <ConfidenceBadge level={tension.confidence} />}
        </div>
        <p className="text-[14px] font-medium text-zinc-200">{tension.label}</p>
        <p className="text-[13px] text-zinc-400 leading-relaxed">{tension.description}</p>
        <div className="grid grid-cols-2 gap-2">
          {tension.sources_position_a?.length > 0 && (
            <div className="bg-zinc-800/40 rounded p-2">
              <p className="text-[10px] font-medium text-zinc-500 uppercase mb-1">Position A</p>
              <div className="flex flex-wrap gap-1">{tension.sources_position_a.map((sid) => <CitationPill key={sid} id={sid} />)}</div>
            </div>
          )}
          {tension.sources_position_b?.length > 0 && (
            <div className="bg-zinc-800/40 rounded p-2">
              <p className="text-[10px] font-medium text-zinc-500 uppercase mb-1">Position B</p>
              <div className="flex flex-wrap gap-1">{tension.sources_position_b.map((sid) => <CitationPill key={sid} id={sid} />)}</div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Gap card ──────────────────────────────────────────────────────────────────

function GapCard({ gap }: { gap: Gap }) {
  return (
    <Card className="bg-amber-900/10 border-amber-800/20">
      <CardContent className="p-3">
        <p className="text-[13px] font-medium text-zinc-200">{gap.label}</p>
        <p className="text-[12px] text-zinc-400 mt-0.5">{gap.description}</p>
        {gap.why_expected && <p className="text-[11px] text-zinc-500 mt-1 italic">Why: {gap.why_expected}</p>}
        {gap.suggested_research_direction && (
          <p className="text-[11px] text-green-400/80 mt-1">→ {gap.suggested_research_direction}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface SemanticBriefRendererProps {
  content: any;
}

export function SemanticBriefRenderer({ content }: SemanticBriefRendererProps) {
  const data = content as SemanticBriefData;
  const themes = data?.themes ?? [];
  const tensions = data?.tensions ?? [];
  const gaps = data?.gaps ?? [];
  const speculative = data?.speculative_observations ?? [];
  const keyPoints = data?.key_points ?? [];

  const defaultOpen = themes.slice(0, 3).map((_: any, i: number) => `theme-${i}`);

  return (
    <div className="space-y-6">
      {/* Semantic core quote */}
      {data?.semantic_core?.text && (
        <div className="text-center pb-4 border-b border-border">
          <p className="text-[14px] text-zinc-200 leading-relaxed italic max-w-[680px] mx-auto">
            &ldquo;{data.semantic_core.text}&rdquo;
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 justify-center text-[13px] text-zinc-400">
        <span>{themes.length} patterns</span>
        <span className="text-zinc-600">·</span>
        <span>{keyPoints.length} findings</span>
        {tensions.length > 0 && <><span className="text-zinc-600">·</span><span>{tensions.length} debates</span></>}
        {gaps.length > 0 && <><span className="text-zinc-600">·</span><span>{gaps.length} open questions</span></>}
        {data?.triage && <><span className="text-zinc-600">·</span><span>Triage: <span className="text-zinc-300 font-medium">{data.triage}</span></span></>}
      </div>

      {/* Warnings */}
      {data?.warnings?.length > 0 && (
        <div className="space-y-1.5">
          {data.warnings.map((w: string, i: number) => (
            <div key={i} className="flex gap-2 text-[12px] text-yellow-400/80 bg-yellow-900/10 border border-yellow-800/20 rounded-lg px-3 py-2">
              <span>⚠</span><span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* SCQA — always expanded */}
      {data?.scqa && <SCQASection scqa={data.scqa} />}

      {/* Themes */}
      {themes.length > 0 && (
        <div>
          <SectionHeader title="Patterns & Insights" count={themes.length} className="mb-3" />
          <Accordion type="multiple" defaultValue={defaultOpen} className="space-y-2">
            {themes.map((theme: Theme, i: number) => (
              <AccordionItem key={theme.theme_id} value={`theme-${i}`} className="border-0">
                <AccordionTrigger className="rounded-lg bg-zinc-900/40 border border-border px-4 py-2.5 hover:bg-zinc-900/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
                  <SectionHeader title={theme.label} confidence={theme.confidence} />
                </AccordionTrigger>
                <AccordionContent className="pt-0 pb-0">
                  <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
                    <ThemeCard theme={theme} keyPoints={keyPoints} />
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
          <div className="space-y-3">
            {tensions.map((t: Tension) => <TensionCard key={t.tension_id} tension={t} />)}
          </div>
        </div>
      )}

      {/* Gaps — collapsible accordion */}
      {gaps.length > 0 && (
        <div>
          <Accordion type="single" collapsible>
            <AccordionItem value="gaps" className="border-0">
              <AccordionTrigger className="rounded-lg bg-zinc-900/40 border border-border px-4 py-2.5 hover:bg-zinc-900/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
                <SectionHeader title="Open Questions" count={gaps.length} />
              </AccordionTrigger>
              <AccordionContent className="pt-0 pb-0">
                <div className="border border-t-0 border-border rounded-b-lg p-4 space-y-3">
                  {gaps.map((gap: Gap) => <GapCard key={gap.gap_id} gap={gap} />)}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      )}

      {/* Speculative observations */}
      {speculative.length > 0 && (
        <div>
          <Accordion type="single" collapsible>
            <AccordionItem value="speculative" className="border-0">
              <AccordionTrigger className="rounded-lg bg-zinc-900/40 border border-border px-4 py-2.5 hover:bg-zinc-900/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
                <SectionHeader title="Worth Exploring" count={speculative.length} />
              </AccordionTrigger>
              <AccordionContent className="pt-0 pb-0">
                <div className="border border-t-0 border-border rounded-b-lg p-4 space-y-3">
                  {speculative.map((obs: any, i: number) => (
                    <Card key={i} className="bg-zinc-800/40 border-zinc-700/30">
                      <CardContent className="p-3">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-400 border border-zinc-600/30 italic mr-2">Speculative</span>
                        <p className="text-[13px] text-zinc-300 leading-relaxed italic mt-2">{obs.text}</p>
                        {obs.based_on?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {obs.based_on.map((sid: string) => <CitationPill key={sid} id={sid} />)}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      )}
    </div>
  );
}
