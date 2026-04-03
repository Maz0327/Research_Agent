/**
 * SemanticBriefRenderer — Typed renderer for Doc 2 (Semantic Brief).
 *
 * Renders themes, key points, tensions, gaps, and the SCQA framework
 * as structured cards with proper visual hierarchy.
 */

import type {
  SemanticBriefData,
  Theme,
  KeyPoint,
  Tension,
  Gap,
  SpeculativeObservation,
  SCQA,
  ConfidenceAssessment,
} from '@/types/documents';
import { SectionHeader } from './shared/SectionHeader';
import { CardWrapper } from './shared/CardWrapper';
import { CollapsibleSection } from './shared/CollapsibleSection';
import { ConfidenceBadge } from './shared/ConfidenceBadge';
import { CitationPill } from './shared/CitationPill';
import { SectionActions } from './SectionActions';
import { formatInternalId } from '@/lib/document-formatters';

interface SemanticBriefRendererProps {
  data: SemanticBriefData;
  showDetails?: boolean;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SCQASection({ scqa }: { scqa: SCQA }) {
  const items = [
    { label: 'Situation', value: scqa.situation, color: 'text-blue-400' },
    { label: 'Complication', value: scqa.complication, color: 'text-amber-400' },
    { label: 'Question', value: scqa.question, color: 'text-purple-400' },
    { label: 'Answer', value: scqa.answer, color: 'text-green-400' },
  ].filter(item => item.value);

  return (
    <CardWrapper accentColor="bg-indigo-500">
      <p className="text-[11px] font-medium text-indigo-400 uppercase tracking-wider mb-3">The Big Picture</p>
      <div className="space-y-3">
        {items.map(item => (
          <div key={item.label}>
            <span className={`text-[12px] font-semibold ${item.color} uppercase tracking-wider`}>{item.label}</span>
            <p className="text-[14px] text-foreground leading-relaxed mt-0.5">{item.value}</p>
          </div>
        ))}
      </div>
    </CardWrapper>
  );
}

function ConfidenceSection({ assessment }: { assessment: ConfidenceAssessment }) {
  return (
    <CardWrapper>
      <div className="flex items-center gap-3 mb-3">
        <p className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Confidence Assessment</p>
        <ConfidenceBadge level={assessment.level} size="md" />
      </div>
      {assessment.reasoning?.length > 0 && (
        <ul className="space-y-1.5">
          {assessment.reasoning.map((r, i) => (
            <li key={i} className="text-[13px] text-muted-foreground leading-relaxed flex gap-2">
              <span className="text-muted-foreground/40 flex-shrink-0 mt-0.5">&#8226;</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      )}
    </CardWrapper>
  );
}

function ThemeCard({ theme, keyPoints, showDetails }: { theme: Theme; keyPoints: KeyPoint[]; showDetails: boolean }) {
  // Resolve related key points by ID
  const relatedKPs = theme.related_key_points
    ?.map(kpId => keyPoints.find(kp => kp.key_point_id === kpId))
    .filter(Boolean) as KeyPoint[];

  return (
    <CardWrapper accentColor="bg-purple-500">
      <div className="flex items-center gap-2 mb-1">
        {showDetails && (
          <span className="text-[11px] font-medium text-purple-400/70 uppercase tracking-wider">{formatInternalId(theme.theme_id)} ({theme.theme_id})</span>
        )}
        {theme.is_consensus && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-800/30">Multiple sources agree</span>
        )}
        {theme.confidence && <ConfidenceBadge level={theme.confidence} />}
      </div>
      <h3 className="text-[16px] font-semibold text-gray-100 mb-1">{theme.label}</h3>
      {/* "So what?" label — makes themes instantly scannable for creators */}
      <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-1 mt-2">So what?</p>
      <p className="text-[14px] text-muted-foreground leading-relaxed">{theme.description}</p>

      {/* Source pills */}
      {theme.sources_supporting?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {theme.sources_supporting.map(sid => (
            <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
          ))}
        </div>
      )}

      {/* Related key points */}
      {relatedKPs?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/30">
          <p className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-2">Related Findings</p>
          <ul className="space-y-1.5">
            {relatedKPs.map(kp => (
              <li key={kp.key_point_id} className="text-[13px] text-muted-foreground leading-relaxed flex gap-2">
                <span className="text-purple-500/50 flex-shrink-0 mt-0.5">&#8226;</span>
                <span>{kp.statement}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </CardWrapper>
  );
}

function TensionCard({ tension, showDetails }: { tension: Tension; showDetails: boolean }) {
  return (
    <CardWrapper accentColor="bg-red-500/60">
      <div className="flex items-center gap-2 mb-2">
        {showDetails && (
          <span className="text-[11px] font-medium text-red-400/70 uppercase tracking-wider">{formatInternalId(tension.tension_id)} ({tension.tension_id})</span>
        )}
        {tension.is_cross_source && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/30">Sources disagree</span>
        )}
        {tension.confidence && <ConfidenceBadge level={tension.confidence} />}
      </div>
      <p className="text-[14px] font-medium text-foreground mb-1">{tension.label}</p>
      <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">{tension.description}</p>

      {/* Two-column positions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {tension.sources_position_a?.length > 0 && (
          <div className="bg-secondary/40 rounded p-2 sm:p-3">
            <p className="text-[11px] font-medium text-muted-foreground/60 uppercase mb-1.5">Position A</p>
            <div className="flex flex-wrap gap-1">
              {tension.sources_position_a.map(sid => (
                <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
              ))}
            </div>
          </div>
        )}
        {tension.sources_position_b?.length > 0 && (
          <div className="bg-secondary/40 rounded p-2 sm:p-3">
            <p className="text-[11px] font-medium text-muted-foreground/60 uppercase mb-1.5">Position B</p>
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

function GapCard({ gap, showDetails }: { gap: Gap; showDetails: boolean }) {
  return (
    <CardWrapper accentColor="bg-amber-500/60">
      {showDetails && (
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[11px] font-medium text-amber-500/70 uppercase tracking-wider">{formatInternalId(gap.gap_id)} ({gap.gap_id})</span>
        </div>
      )}
      <p className="text-[14px] font-medium text-foreground mb-1">{gap.label}</p>
      <p className="text-[13px] text-muted-foreground leading-relaxed">{gap.description}</p>
      {gap.why_expected && (
        <p className="text-[12px] text-muted-foreground/60 mt-1.5 italic">Why expected: {gap.why_expected}</p>
      )}
      {gap.suggested_research_direction && (
        <div className="mt-2 flex items-start gap-1.5">
          <span className="text-[11px] text-green-500 flex-shrink-0 mt-0.5">→</span>
          <span className="text-[12px] text-green-400/80">{gap.suggested_research_direction}</span>
        </div>
      )}
    </CardWrapper>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function SemanticBriefRenderer({ data, showDetails = false }: SemanticBriefRendererProps) {
  const themeCount = data.themes?.length || 0;
  const tensionCount = data.tensions?.length || 0;
  const gapCount = data.gaps?.length || 0;

  // Section count for progress indicator
  const sections: string[] = [];
  if (data.scqa) sections.push('SCQA');
  if (data.confidence_assessment) sections.push('Confidence');
  if (themeCount > 0) sections.push('Themes');
  if (tensionCount > 0) sections.push('Tensions');
  if (gapCount > 0) sections.push('Gaps');
  if (data.speculative_observations?.length) sections.push('Speculative');
  const totalSections = sections.length;
  let sectionIdx = 0;

  return (
    <div className="space-y-6 sm:space-y-10">
      {/* Semantic core */}
      {data.semantic_core?.text && (
        <div className="text-center pb-4 border-b border-border/30">
          <p className="text-[14px] sm:text-[15px] text-foreground leading-relaxed max-w-none sm:max-w-[700px] mx-auto italic">
            &ldquo;{data.semantic_core.text}&rdquo;
          </p>
          {/* based_on contains internal KP_ IDs — only show in debug mode */}
          {showDetails && data.semantic_core.based_on?.length > 0 && (
            <div className="flex flex-wrap gap-1 justify-center mt-2">
              {data.semantic_core.based_on.map(sid => (
                <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats bar */}
      <div className="flex flex-wrap gap-x-2 sm:gap-x-4 gap-y-1 justify-center text-[13px] text-muted-foreground">
        <span>{themeCount} patterns</span>
        <span className="text-muted-foreground/40">&#183;</span>
        <span>{data.key_points?.length || 0} findings</span>
        {tensionCount > 0 && (
          <>
            <span className="text-muted-foreground/40">&#183;</span>
            <span>{tensionCount} debates</span>
          </>
        )}
        {gapCount > 0 && (
          <>
            <span className="text-muted-foreground/40">&#183;</span>
            <span>{gapCount} open questions</span>
          </>
        )}
        <span className="text-muted-foreground/40">&#183;</span>
        <span>Triage: <span className="font-medium text-muted-foreground">{data.triage}</span></span>
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

      {/* SCQA — always expanded (core overview) */}
      {data.scqa && (++sectionIdx, true) && <SCQASection scqa={data.scqa} />}

      {/* Confidence Assessment — collapsed by default */}
      {data.confidence_assessment && (
        <div>
          <CollapsibleSection label="Confidence assessment">
            <ConfidenceSection assessment={data.confidence_assessment} />
          </CollapsibleSection>
        </div>
      )}

      {/* Themes — always expanded (core section) */}
      {themeCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Patterns & Insights" accentColor="bg-purple-500" count={themeCount} sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.themes.map(t => `${t.label}: ${t.description}`).join('\n\n')} sectionTitle="Patterns & Insights" />
          </div>
          <div className="mt-4 space-y-4">
            {data.themes.map(theme => (
              <ThemeCard key={theme.theme_id} theme={theme} keyPoints={data.key_points || []} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Tensions — always expanded (important for creators) */}
      {tensionCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Conflicting Views" accentColor="bg-red-500" count={tensionCount} sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.tensions.map(t => `${t.label}: ${t.description}`).join('\n\n')} sectionTitle="Conflicting Views" />
          </div>
          <div className="mt-4 space-y-4">
            {data.tensions.map(t => (
              <TensionCard key={t.tension_id} tension={t} showDetails={showDetails} />
            ))}
          </div>
        </div>
      )}

      {/* Gaps — collapsed by default (supporting detail) */}
      {gapCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Open Questions" accentColor="bg-amber-500" count={gapCount} sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.gaps.map(g => `${g.label}: ${g.description}`).join('\n\n')} sectionTitle="Open Questions" />
          </div>
          <div className="mt-3">
            <CollapsibleSection label="View open questions" itemCount={gapCount}>
              <div className="space-y-4">
                {data.gaps.map(gap => (
                  <GapCard key={gap.gap_id} gap={gap} showDetails={showDetails} />
                ))}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      )}

      {/* Speculative observations — collapsed by default */}
      {data.speculative_observations?.length > 0 && (
        <div>
          <SectionHeader title="Worth Exploring" accentColor="bg-gray-600" count={data.speculative_observations.length} sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-3">
            <CollapsibleSection label="View speculative observations" itemCount={data.speculative_observations.length}>
              <div className="space-y-3">
                {data.speculative_observations.map((obs, i) => (
                  <CardWrapper key={i} accentColor="bg-gray-600">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground border border-gray-600/30 italic">Speculative</span>
                    </div>
                    <p className="text-[14px] text-muted-foreground leading-relaxed italic">{obs.text}</p>
                    {obs.based_on?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {obs.based_on.map(sid => (
                          <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
                        ))}
                      </div>
                    )}
                  </CardWrapper>
                ))}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      )}
    </div>
  );
}
