/**
 * JumpStartRenderer — Typed renderer for Doc 1 (Jump-Start Directions).
 *
 * The most complex and most-used document. Renders research threads as
 * themed cards with key points, gaps, and booster directions.
 */

import type {
  JumpStartData,
  ResearchThread,
  KeyPoint,
  Gap,
  Tension,
  BoosterItem,
  CrossCuttingAnalysis,
} from '@/types/documents';
import { SectionHeader } from './shared/SectionHeader';
import { CardWrapper } from './shared/CardWrapper';
import { ConfidenceBadge } from './shared/ConfidenceBadge';
import { CitationPill } from './shared/CitationPill';
import { SectionActions } from './SectionActions';
import { formatInternalId } from '@/lib/document-formatters';

interface JumpStartRendererProps {
  data: JumpStartData;
  showDetails?: boolean;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function KeyPointItem({ kp, showDetails }: { kp: KeyPoint; showDetails: boolean }) {
  return (
    <li className="flex gap-3 items-start">
      <span className="text-blue-500/60 mt-1 flex-shrink-0">&#8226;</span>
      <div className="flex-1 min-w-0">
        <p className="text-[14px] text-gray-200 leading-relaxed">{kp.statement}</p>
        <div className="flex flex-wrap items-center gap-1.5 mt-1">
          {kp.source_ids?.map(sid => (
            <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
          ))}
          {kp.confidence && <ConfidenceBadge level={kp.confidence} />}
        </div>
      </div>
    </li>
  );
}

function GapCard({ gap, showDetails }: { gap: Gap; showDetails: boolean }) {
  return (
    <div className="bg-amber-900/10 border border-amber-800/20 rounded-lg p-3 sm:p-4 relative overflow-hidden">
      <div className="absolute top-0 left-0 bottom-0 w-1 bg-amber-500/60 rounded-l-lg" />
      <div className="pl-3">
        {showDetails && (
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-medium text-amber-500/70 uppercase tracking-wider">{formatInternalId(gap.gap_id)} ({gap.gap_id})</span>
          </div>
        )}
        <p className="text-[14px] font-medium text-gray-200 mb-1">{gap.label}</p>
        <p className="text-[13px] text-gray-400 leading-relaxed">{gap.description}</p>
        {gap.why_expected && (
          <p className="text-[12px] text-gray-500 mt-1.5 italic">Why: {gap.why_expected}</p>
        )}
        {gap.suggested_research_direction && (
          <div className="mt-2 flex items-start gap-1.5">
            <span className="text-[11px] text-green-500 flex-shrink-0 mt-0.5">→</span>
            <span className="text-[12px] text-green-400/80">{gap.suggested_research_direction}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function TensionItem({ tension, showDetails }: { tension: Tension; showDetails: boolean }) {
  return (
    <CardWrapper accentColor="bg-red-500/60">
      <div className="flex items-center gap-2 mb-2">
        {showDetails && (
          <span className="text-[11px] font-medium text-red-400/70 uppercase tracking-wider">
            {formatInternalId(tension.tension_id)} ({tension.tension_id})
          </span>
        )}
        {tension.is_cross_source && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/30">Cross-source</span>
        )}
        {tension.confidence && <ConfidenceBadge level={tension.confidence} />}
      </div>
      <p className="text-[14px] font-medium text-gray-200 mb-1">{tension.label}</p>
      <p className="text-[13px] text-gray-400 leading-relaxed mb-2">{tension.description}</p>
      {/* Two-column positions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 mt-2">
        {tension.sources_position_a?.length > 0 && (
          <div className="bg-gray-800/30 rounded p-2 sm:p-2.5">
            <p className="text-[11px] font-medium text-gray-500 uppercase mb-1">Position A</p>
            <div className="flex flex-wrap gap-1">
              {tension.sources_position_a.map(sid => (
                <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
              ))}
            </div>
          </div>
        )}
        {tension.sources_position_b?.length > 0 && (
          <div className="bg-gray-800/30 rounded p-2 sm:p-2.5">
            <p className="text-[11px] font-medium text-gray-500 uppercase mb-1">Position B</p>
            <div className="flex flex-wrap gap-1">
              {tension.sources_position_b.map(sid => (
                <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
              ))}
            </div>
          </div>
        )}
      </div>
    </CardWrapper>
  );
}

function BoosterDirectionItem({ item, type }: { item: BoosterItem; type: string }) {
  const impactColors: Record<string, string> = {
    critical: 'bg-red-500',
    important: 'bg-yellow-500',
    nice_to_have: 'bg-green-500',
  };
  const impactDot = impactColors[item.impact_level || ''] || 'bg-gray-500';
  const prefixLabels: Record<string, string> = {
    search: 'Search',
    question: 'Research Q',
    primary_source: 'Find',
    missing_perspective: 'Missing Voice',
  };
  const prefix = prefixLabels[type] || '';

  const mainText = item.query || item.question || item.description || '';

  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <span className={`w-2 h-2 rounded-full ${impactDot} flex-shrink-0 mt-1.5`} />
      <div className="flex-1 min-w-0">
        {prefix && <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mr-2">{prefix}</span>}
        <span className="text-[13px] text-gray-300">{mainText}</span>
        {item.why_it_matters && (
          <p className="text-[12px] text-gray-500 mt-0.5">{item.why_it_matters}</p>
        )}
      </div>
    </div>
  );
}

function ResearchThreadCard({ thread, showDetails }: { thread: ResearchThread; showDetails: boolean }) {
  const theme = thread.theme;

  const allBoosters = [
    ...(thread.booster_search_queries || []).map(b => ({ ...b, _type: 'search' })),
    ...(thread.booster_research_questions || []).map(b => ({ ...b, _type: 'question' })),
    ...(thread.booster_primary_sources || []).map(b => ({ ...b, _type: 'primary_source' })),
    ...(thread.booster_missing_perspectives || []).map(b => ({ ...b, _type: 'missing_perspective' })),
  ];

  return (
    <CardWrapper accentColor="bg-blue-500">
      {/* Theme header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          {showDetails && (
            <span className="text-[11px] font-medium text-blue-400/70 uppercase tracking-wider">{formatInternalId(theme.theme_id)} ({theme.theme_id})</span>
          )}
          {theme.is_consensus && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-800/30">Multiple sources agree</span>
          )}
          {theme.confidence && <ConfidenceBadge level={theme.confidence} />}
        </div>
        <h3 className="text-[16px] font-semibold text-gray-100 mb-1">{theme.label}</h3>
        <p className="text-[14px] text-gray-400 leading-relaxed">{theme.description}</p>
        {theme.sources_supporting?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {theme.sources_supporting.map(sid => (
              <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
            ))}
          </div>
        )}
      </div>

      {/* Key Points */}
      {thread.key_points?.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">Key Points</p>
          <ul className="space-y-2">
            {thread.key_points.map(kp => (
              <KeyPointItem key={kp.key_point_id} kp={kp} showDetails={showDetails} />
            ))}
          </ul>
        </div>
      )}

      {/* Gaps */}
      {thread.gaps?.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">Open Questions</p>
          <div className="space-y-3">
            {thread.gaps.map(gap => (
              <GapCard key={gap.gap_id} gap={gap} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Booster directions */}
      {allBoosters.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">Deep Research Directions</p>
          <div className="space-y-0.5">
            {allBoosters.map((b, i) => (
              <BoosterDirectionItem key={i} item={b} type={(b as any)._type} />
            ))}
          </div>
        </div>
      )}
    </CardWrapper>
  );
}

function CrossCuttingSection({ analysis, showDetails }: { analysis: CrossCuttingAnalysis; showDetails: boolean }) {
  const hasConfirmed = analysis.confirmed?.length > 0;
  const hasConflicts = analysis.conflicts?.length > 0;
  const hasSingleSource = analysis.single_source?.length > 0;

  if (!hasConfirmed && !hasConflicts && !hasSingleSource) return null;

  return (
    <div className="space-y-4">
      <SectionHeader title="What Multiple Sources Agree On" accentColor="bg-purple-500" />

      {hasConfirmed && (
        <div className="space-y-2">
          <p className="text-[12px] font-medium text-green-400 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Confirmed Across Sources
          </p>
          {analysis.confirmed.map((item, i) => (
            <CardWrapper key={i} accentColor="bg-green-500/60" className="py-3">
              <p className="text-[14px] text-gray-200 leading-relaxed">{item.statement}</p>
              <div className="flex flex-wrap gap-1 mt-1.5">
                {item.sources?.map(sid => (
                  <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
                ))}
              </div>
            </CardWrapper>
          ))}
        </div>
      )}

      {hasConflicts && (
        <div className="space-y-2">
          <p className="text-[12px] font-medium text-red-400 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Conflicts
          </p>
          {analysis.conflicts.map((item, i) => (
            <CardWrapper key={i} accentColor="bg-red-500/60" className="py-3">
              <p className="text-[14px] text-gray-200 leading-relaxed mb-2">{item.description}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div className="flex flex-wrap gap-1 items-center">
                  <span className="text-[11px] text-gray-500 mr-1">Side A:</span>
                  {item.sources_a?.map(sid => (
                    <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
                  ))}
                </div>
                <div className="flex flex-wrap gap-1 items-center">
                  <span className="text-[11px] text-gray-500 mr-1">Side B:</span>
                  {item.sources_b?.map(sid => (
                    <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
                  ))}
                </div>
              </div>
            </CardWrapper>
          ))}
        </div>
      )}

      {hasSingleSource && (
        <div className="space-y-2">
          <p className="text-[12px] font-medium text-yellow-400 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-yellow-500" /> Single-Source Claims
          </p>
          {analysis.single_source.map((item, i) => (
            <CardWrapper key={i} accentColor="bg-yellow-500/60" className="py-3">
              <p className="text-[14px] text-gray-200 leading-relaxed">{item.statement}</p>
              <div className="mt-1.5">
                <CitationPill sourceId={item.source} showDetails={showDetails} />
              </div>
            </CardWrapper>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function JumpStartRenderer({ data, showDetails = false }: JumpStartRendererProps) {
  const threadCount = data.research_threads?.length || 0;
  const kpCount = data.key_points?.length || 0;
  const gapCount = data.gaps?.length || 0;
  const tensionCount = data.tensions?.length || 0;

  return (
    <div className="space-y-6 sm:space-y-10">
      {/* Summary header */}
      <div className="text-center pb-4 border-b border-gray-700/30">
        <div className="flex items-center justify-center gap-2 mb-2">
          <ConfidenceBadge level={data.confidence} size="md" />
        </div>
        <div className="flex flex-wrap gap-x-2 sm:gap-x-4 gap-y-1 justify-center text-[13px] text-gray-400">
          <span>{data.current_corpus?.source_count || 0} sources</span>
          <span className="text-gray-600">&#183;</span>
          <span>{threadCount} patterns</span>
          <span className="text-gray-600">&#183;</span>
          <span>{kpCount} findings</span>
          {gapCount > 0 && (
            <>
              <span className="text-gray-600">&#183;</span>
              <span>{gapCount} open questions</span>
            </>
          )}
        </div>
        {data.scope_lock && (
          <div className="mt-3 text-[12px] text-gray-500">
            <span className="text-gray-600">Scope:</span>{' '}
            {data.scope_lock.in?.join(', ')}
          </div>
        )}
      </div>

      {/* Warnings */}
      {data.warnings?.length > 0 && (
        <div className="space-y-2">
          {data.warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-[13px] text-yellow-400/80 bg-yellow-900/10 border border-yellow-800/20 rounded-lg px-3 sm:px-4 py-2 sm:py-2.5">
              <span className="flex-shrink-0 mt-0.5">⚠</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Next Steps */}
      {data.next_steps?.length > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Next Steps" accentColor="bg-green-500" count={data.next_steps.length} />
            <SectionActions content={data.next_steps.join('\n')} sectionTitle="Next Steps" />
          </div>
          <ol className="mt-4 space-y-2">
            {data.next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="w-6 h-6 rounded-full bg-green-900/40 text-green-400 text-[12px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-[14px] text-gray-200 leading-relaxed">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Research Threads */}
      {data.research_threads?.length > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="What We Found" accentColor="bg-blue-500" count={threadCount} />
            <SectionActions content={data.research_threads.map(t => `${t.theme?.label}: ${t.theme?.description}`).join('\n\n')} sectionTitle="What We Found" />
          </div>
          <div className="mt-4 space-y-5">
            {data.research_threads.map((thread, i) => (
              <ResearchThreadCard key={thread.theme?.theme_id || i} thread={thread} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Standalone tensions (not in threads) */}
      {tensionCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Conflicting Views" accentColor="bg-red-500" count={tensionCount} />
            <SectionActions content={data.tensions.map(t => `${t.label}: ${t.description}`).join('\n\n')} sectionTitle="Conflicting Views" />
          </div>
          <div className="mt-4 space-y-4">
            {data.tensions.map(t => (
              <TensionItem key={t.tension_id} tension={t} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Cross-cutting analysis */}
      {data.cross_cutting && (
        <CrossCuttingSection analysis={data.cross_cutting} showDetails={showDetails} />
      )}
    </div>
  );
}
