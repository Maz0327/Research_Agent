/**
 * CreatorBriefRenderer — Typed renderer for Doc 3 (Creator Brief / Producer Packet).
 *
 * Renders story core, narrative angles, opening hooks, key moments,
 * title options, thumbnail concepts, and risk assessment.
 */

import { useState } from 'react';
import type {
  ProducerPacketData,
  NarrativeAngle,
  OpeningHook,
  KeyMoment,
  TitleOption,
  ThumbnailConcept,
  StructureOption,
} from '@/types/documents';
import { SectionHeader } from './shared/SectionHeader';
import { CardWrapper } from './shared/CardWrapper';
import { CitationPill } from './shared/CitationPill';
import { CollapsibleSection } from './shared/CollapsibleSection';
import { HookOptionCard } from './HookOptionCard';
import { StoryArcCard } from './StoryArcCard';
import { SectionActions } from './SectionActions';
import { formatInternalId } from '@/lib/document-formatters';

interface CreatorBriefRendererProps {
  data: ProducerPacketData;
  showDetails?: boolean;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function StoryCoreSection({ data }: { data: ProducerPacketData }) {
  const core = data.story_core;
  if (!core) return null;

  return (
    <CardWrapper accentColor="bg-amber-500">
      <p className="text-[11px] font-medium text-amber-400 uppercase tracking-wider mb-3">Story Core</p>
      <div className="space-y-3">
        <div>
          <p className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">Central Question</p>
          <p className="text-[16px] font-medium text-gray-100 leading-relaxed mt-0.5">{core.central_question}</p>
        </div>
        <div>
          <p className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">One-Sentence Pitch</p>
          <p className="text-[15px] text-gray-200 leading-relaxed mt-0.5 italic">{core.one_sentence_pitch}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div>
            <p className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">Target Audience</p>
            <p className="text-[14px] text-gray-300 mt-0.5">{core.target_audience}</p>
          </div>
          <div>
            <p className="text-[12px] font-semibold text-gray-500 uppercase tracking-wider">Emotional Arc</p>
            <p className="text-[14px] text-gray-300 mt-0.5">{core.emotional_arc}</p>
          </div>
        </div>
      </div>
    </CardWrapper>
  );
}

function AngleCard({ angle, isRecommended, showDetails }: { angle: NarrativeAngle; isRecommended: boolean; showDetails: boolean }) {
  return (
    <CardWrapper accentColor={isRecommended ? 'bg-amber-500' : 'bg-gray-600'}>
      <div className="flex items-center gap-2 mb-2">
        {showDetails && (
          <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">
            {formatInternalId(angle.angle_id)} ({angle.angle_id})
          </span>
        )}
        {isRecommended && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/40 text-amber-400 border border-amber-800/30 font-medium">
            Recommended
          </span>
        )}
        {angle.confidence && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-700/60 text-gray-400">
            {angle.confidence}
          </span>
        )}
      </div>
      <h3 className="text-[16px] font-semibold text-gray-100 mb-1">{angle.title}</h3>
      <p className="text-[14px] text-gray-400 leading-relaxed mb-3">{angle.description}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {angle.strengths?.length > 0 && (
          <div>
            <p className="text-[11px] font-medium text-green-500 uppercase tracking-wider mb-1">Strengths</p>
            <ul className="space-y-1">
              {angle.strengths.map((s, i) => (
                <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                  <span className="text-green-500/50 flex-shrink-0">+</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {angle.weaknesses?.length > 0 && (
          <div>
            <p className="text-[11px] font-medium text-red-500 uppercase tracking-wider mb-1">Weaknesses</p>
            <ul className="space-y-1">
              {angle.weaknesses.map((w, i) => (
                <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                  <span className="text-red-500/50 flex-shrink-0">-</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {angle.best_for && (
        <p className="text-[12px] text-gray-500 mt-2 pt-2 border-t border-gray-700/30">
          <span className="text-gray-600">Best for:</span> {angle.best_for}
        </p>
      )}

      {angle.key_sources?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {angle.key_sources.map(sid => (
            <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
          ))}
        </div>
      )}
    </CardWrapper>
  );
}

// HookCard removed — replaced by HookOptionCard (Task 2E)

function WhyItMattersSection({ text }: { text: string }) {
  if (!text) return null;

  return (
    <div className="relative bg-gray-800/40 rounded-lg border border-amber-700/30 p-4 sm:p-5 overflow-hidden">
      {/* Amber accent bar */}
      <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-lg bg-amber-500" />
      <div className="pl-2 sm:pl-3">
        <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-2">
          What this means for your audience
        </p>
        <p className="text-[16px] text-gray-100 leading-relaxed font-medium">
          {text}
        </p>
      </div>
    </div>
  );
}

function KeyMomentCard({ moment, showDetails }: { moment: KeyMoment; showDetails: boolean }) {
  return (
    <div className="flex gap-3 items-start py-2">
      <div className="flex-shrink-0 w-12 sm:w-16 text-right">
        {moment.timestamp ? (
          <span className="text-[12px] font-mono text-blue-400/70">{moment.timestamp}</span>
        ) : (
          <span className="text-[12px] text-gray-600">-</span>
        )}
      </div>
      <div className="w-px bg-gray-700 self-stretch flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[14px] text-gray-200 leading-relaxed">{moment.moment}</p>
        <p className="text-[12px] text-gray-500 mt-0.5">{moment.why_compelling}</p>
        <div className="flex items-center gap-2 mt-1">
          <CitationPill sourceId={moment.source_id} showDetails={showDetails} />
          {moment.potential_use && (
            <span className="text-[11px] text-gray-600">Use: {moment.potential_use}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function TitleOptionCard({ option }: { option: TitleOption }) {
  return (
    <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/30">
      <p className="text-[15px] font-medium text-gray-100">{option.title}</p>
      {option.subtitle && (
        <p className="text-[13px] text-gray-400 mt-0.5">{option.subtitle}</p>
      )}
      {option.tone && (
        <span className="text-[10px] text-gray-500 italic mt-1 inline-block">{option.tone}</span>
      )}
    </div>
  );
}

function ThumbnailConceptCard({ concept }: { concept: ThumbnailConcept }) {
  return (
    <CardWrapper>
      <p className="text-[14px] font-medium text-gray-200 mb-2">{concept.concept}</p>
      {concept.visual_elements?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {concept.visual_elements.map((el, i) => (
            <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-gray-700/50 text-gray-400 border border-gray-600/30">
              {el}
            </span>
          ))}
        </div>
      )}
      {concept.text_overlay && (
        <p className="text-[12px] text-gray-500">Overlay: &ldquo;{concept.text_overlay}&rdquo;</p>
      )}
      <p className="text-[12px] text-gray-500 italic mt-1">{concept.emotional_appeal}</p>
    </CardWrapper>
  );
}

function StructureOptionCard({ option }: { option: StructureOption }) {
  return (
    <CardWrapper>
      <h4 className="text-[14px] font-semibold text-gray-200 mb-1">{option.structure_type}</h4>
      <p className="text-[13px] text-gray-400 leading-relaxed mb-2">{option.description}</p>

      {option.section_breakdown?.length > 0 && (
        <div className="mb-2">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Sections</p>
          <ol className="space-y-0.5">
            {option.section_breakdown.map((s, i) => (
              <li key={i} className="text-[13px] text-gray-300 flex gap-2">
                <span className="text-gray-600 flex-shrink-0 w-4 text-right">{i + 1}.</span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[12px]">
        {option.pros?.length > 0 && (
          <div>
            {option.pros.map((p, i) => (
              <p key={i} className="text-green-400/70 flex gap-1"><span>+</span>{p}</p>
            ))}
          </div>
        )}
        {option.cons?.length > 0 && (
          <div>
            {option.cons.map((c, i) => (
              <p key={i} className="text-red-400/70 flex gap-1"><span>-</span>{c}</p>
            ))}
          </div>
        )}
      </div>
    </CardWrapper>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function CreatorBriefRenderer({ data, showDetails = false }: CreatorBriefRendererProps) {
  const [selectedHookIndex, setSelectedHookIndex] = useState<number>(-1);
  const angleCount = data.narrative_angles?.length || 0;
  const hookCount = data.opening_hooks?.length || 0;
  const momentCount = data.key_moments?.length || 0;

  // Count visible sections for progress indicator
  const sections: string[] = [];
  if (data.story_core) sections.push('Story Core');
  if (angleCount > 0) sections.push('Narrative Angles');
  if (hookCount > 0) sections.push('Opening Hooks');
  if (data.structure_options?.length) sections.push('Structure Options');
  if (data.suggested_structure) sections.push('Suggested Structure');
  if (momentCount > 0) sections.push('Key Moments');
  if (data.story_core?.why_this_matters) sections.push('Why It Matters');
  if (data.title_options?.length) sections.push('Title Options');
  if (data.thumbnail_concepts?.length) sections.push('Thumbnail Concepts');
  if (data.interview_suggestions) sections.push('Interview Suggestions');
  if (data.b_roll_suggestions?.length) sections.push('B-Roll Suggestions');
  if (data.risk_assessment) sections.push('Risk Assessment');
  const totalSections = sections.length;
  let sectionIdx = 0;

  return (
    <div className="space-y-6 sm:space-y-10">
      {/* Story Core — always expanded */}
      {data.story_core && (++sectionIdx, true) && <StoryCoreSection data={data} />}

      {/* Recommendation reasoning */}
      {data.recommendation_reasoning && (
        <div className="text-[14px] text-gray-400 leading-relaxed bg-gray-800/20 rounded-lg px-3 sm:px-5 py-3 sm:py-4 border border-gray-700/20">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">Recommendation</p>
          <p>{data.recommendation_reasoning}</p>
        </div>
      )}

      {/* Narrative Angles — always expanded (core creative section) */}
      {angleCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Narrative Angles" accentColor="bg-amber-500" count={angleCount} sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.narrative_angles.map(a => `${a.title}: ${a.description}`).join('\n\n')} sectionTitle="Narrative Angles" />
          </div>
          <div className="mt-4 space-y-4">
            {data.narrative_angles.map(angle => (
              <AngleCard
                key={angle.angle_id}
                angle={angle}
                isRecommended={angle.angle_id === data.recommended_angle_id}
                showDetails={showDetails}
              />
            ))}
          </div>
        </div>
      )}

      {/* Opening Hooks — always expanded (core creative section) */}
      {hookCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Opening Hooks" accentColor="bg-blue-500" count={hookCount} subtitle="Tap to select your favorite" sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.opening_hooks.map(h => h.content).join('\n\n')} sectionTitle="Opening Hooks" />
          </div>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.opening_hooks.map((hook, i) => (
              <HookOptionCard
                key={i}
                hook={hook}
                index={i}
                isSelected={selectedHookIndex === i}
                onSelect={(idx) => setSelectedHookIndex(idx === selectedHookIndex ? -1 : idx)}
                showDetails={showDetails}
              />
            ))}
          </div>
        </div>
      )}

      {/* Structure Options — collapsed by default (supporting detail) */}
      {data.structure_options?.length > 0 && (
        <div>
          <SectionHeader title="Structure Options" accentColor="bg-green-500" count={data.structure_options.length} sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-3">
            <CollapsibleSection label="View structure options" itemCount={data.structure_options.length}>
              <div className="space-y-4">
                {data.structure_options.map((opt, i) => (
                  <StructureOptionCard key={i} option={opt} />
                ))}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      )}

      {/* Suggested Structure — Phase 3B story arc suggestion */}
      {data.suggested_structure && (
        <div>
          <SectionHeader title="Suggested Structure" accentColor="bg-teal-500" sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-4">
            <StoryArcCard arc={data.suggested_structure} />
          </div>
        </div>
      )}

      {/* Key Moments — collapsed by default (supporting detail) */}
      {momentCount > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Key Moments" accentColor="bg-purple-500" count={momentCount} sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.key_moments.map(m => m.moment).join('\n\n')} sectionTitle="Key Moments" />
          </div>
          <div className="mt-3">
            <CollapsibleSection label="View key moments" itemCount={momentCount}>
              <div className="divide-y divide-gray-800/50">
                {data.key_moments.map((m, i) => (
                  <KeyMomentCard key={i} moment={m} showDetails={showDetails} />
                ))}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      )}

      {/* Why It Matters — elevated standalone section (Task 2D), always visible */}
      {data.story_core?.why_this_matters && (++sectionIdx, true) && (
        <WhyItMattersSection text={data.story_core.why_this_matters} />
      )}

      {/* Title Options — always expanded (quick-scan section) */}
      {data.title_options?.length > 0 && (
        <div className="group">
          <div className="flex items-center justify-between">
            <SectionHeader title="Title Options" accentColor="bg-blue-500" count={data.title_options.length} sectionIndex={++sectionIdx} totalSections={totalSections} />
            <SectionActions content={data.title_options.map(t => t.title + (t.subtitle ? ` — ${t.subtitle}` : '')).join('\n')} sectionTitle="Title Options" />
          </div>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.title_options.map((opt, i) => (
              <TitleOptionCard key={i} option={opt} />
            ))}
          </div>
        </div>
      )}

      {/* Thumbnail Concepts — collapsed by default (supporting detail) */}
      {data.thumbnail_concepts?.length > 0 && (
        <div>
          <SectionHeader title="Thumbnail Concepts" accentColor="bg-pink-500" count={data.thumbnail_concepts.length} sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-3">
            <CollapsibleSection label="View thumbnail concepts" itemCount={data.thumbnail_concepts.length}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {data.thumbnail_concepts.map((concept, i) => (
                  <ThumbnailConceptCard key={i} concept={concept} />
                ))}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      )}

      {/* Interview Suggestions — collapsed by default */}
      {data.interview_suggestions && (
        <div>
          <SectionHeader title="Interview Suggestions" accentColor="bg-teal-500" sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-3">
            <CollapsibleSection label="View interview suggestions">
              <CardWrapper>
                {data.interview_suggestions.suggested_guests?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">Suggested Guests</p>
                    <div className="space-y-2">
                      {data.interview_suggestions.suggested_guests.map((guest, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className="text-teal-500/50 flex-shrink-0 mt-0.5">&#8226;</span>
                          <div>
                            <span className="text-[14px] font-medium text-gray-200">{guest.name}</span>
                            <p className="text-[12px] text-gray-500">{guest.why}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {data.interview_suggestions.key_questions?.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">Key Questions</p>
                    <ul className="space-y-1">
                      {data.interview_suggestions.key_questions.map((q, i) => (
                        <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                          <span className="text-teal-500/50 flex-shrink-0">?</span>
                          <span>{q}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardWrapper>
            </CollapsibleSection>
          </div>
        </div>
      )}

      {/* B-Roll Suggestions — collapsed by default */}
      {data.b_roll_suggestions && data.b_roll_suggestions.length > 0 && (
        <div>
          <SectionHeader title="B-Roll Suggestions" accentColor="bg-cyan-500" count={data.b_roll_suggestions.length} sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-3">
            <CollapsibleSection label="View B-roll suggestions" itemCount={data.b_roll_suggestions.length}>
              <div className="space-y-2">
                {data.b_roll_suggestions.map((b, i) => (
                  <div key={i} className="flex items-start gap-2.5 py-2 sm:py-1.5">
                    <span className="text-cyan-500/50 flex-shrink-0 mt-0.5">&#9654;</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-[13px] text-gray-300">{b.description}</span>
                      {b.visual_type && (
                        <span className="text-[11px] text-gray-600 ml-2">({b.visual_type})</span>
                      )}
                      {b.source_id && (
                        <span className="ml-2"><CitationPill sourceId={b.source_id} showDetails={showDetails} /></span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      )}

      {/* Risk Assessment — collapsed by default */}
      {data.risk_assessment && (
        <div>
          <SectionHeader title="Risk Assessment" accentColor="bg-red-500" sectionIndex={++sectionIdx} totalSections={totalSections} />
          <div className="mt-3">
            <CollapsibleSection label="View risk assessment">
              <CardWrapper accentColor="bg-red-500/60">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">Sensitivity</span>
                  <span className="text-[12px] font-medium text-red-400">{data.risk_assessment.sensitivity_level}</span>
                </div>

                {data.risk_assessment.potential_issues?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Potential Issues</p>
                    <ul className="space-y-1">
                      {data.risk_assessment.potential_issues.map((issue, i) => (
                        <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                          <span className="text-red-500/50 flex-shrink-0">&#8226;</span>
                          <span>{issue}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.risk_assessment.mitigation_suggestions?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Mitigation</p>
                    <ul className="space-y-1">
                      {data.risk_assessment.mitigation_suggestions.map((s, i) => (
                        <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                          <span className="text-green-500/50 flex-shrink-0">→</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.risk_assessment.legal_considerations?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Legal</p>
                    <ul className="space-y-1">
                      {data.risk_assessment.legal_considerations.map((l, i) => (
                        <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                          <span className="text-yellow-500/50 flex-shrink-0">&#8226;</span>
                          <span>{l}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.risk_assessment.ethical_considerations?.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Ethical</p>
                    <ul className="space-y-1">
                      {data.risk_assessment.ethical_considerations.map((e, i) => (
                        <li key={i} className="text-[13px] text-gray-300 flex gap-1.5">
                          <span className="text-purple-500/50 flex-shrink-0">&#8226;</span>
                          <span>{e}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardWrapper>
            </CollapsibleSection>
          </div>
        </div>
      )}
    </div>
  );
}
