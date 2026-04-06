/**
 * creator-brief-renderer — Doc 3 (Creator Brief) main orchestrator.
 * Splits into: StoryCoreSection, AnglesSection, HooksSection, plus inline sub-sections.
 * Hero document — most important renderer in the suite.
 */

import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from '@/components/ui/accordion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SectionHeader } from './shared/section-header';
import { CitationPill } from './shared/citation-pill';
import { StoryCoreSection, WhyItMattersSection } from './creator-brief-story-core';
import { HooksSection } from './creator-brief-hooks';
import { AnglesSection } from './creator-brief-angles';
import type { ProducerPacketData, KeyMoment, TitleOption, ThumbnailConcept } from '@/types/documents';

// ── Supporting sub-components (small enough to inline) ────────────────────────

function TitleOptionCard({ option }: { option: TitleOption }) {
  return (
    <div className="bg-card/30 rounded-lg p-3 border border-border">
      <p className="text-body font-medium text-foreground">{option.title}</p>
      {option.subtitle && <p className="text-body-sm text-muted-foreground mt-0.5">{option.subtitle}</p>}
      {option.tone && <span className="text-caption text-muted-foreground/70 italic mt-1 inline-block">{option.tone}</span>}
    </div>
  );
}

function KeyMomentRow({ moment }: { moment: KeyMoment }) {
  return (
    <div className="flex gap-3 items-start py-2 border-b border-border last:border-0">
      <div className="flex-shrink-0 w-14 text-right">
        {moment.timestamp
          ? <span className="text-caption font-mono text-blue-400/70">{moment.timestamp}</span>
          : <span className="text-caption text-muted-foreground/60">—</span>}
      </div>
      <div className="w-px bg-border self-stretch flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-foreground leading-relaxed">{moment.moment}</p>
        <p className="text-caption text-muted-foreground/70 mt-0.5">{moment.why_compelling}</p>
        <div className="flex items-center gap-2 mt-1">
          <CitationPill id={moment.source_id} />
          {moment.potential_use && <span className="text-caption text-muted-foreground/60">Use: {moment.potential_use}</span>}
        </div>
      </div>
    </div>
  );
}

function ThumbnailCard({ concept }: { concept: ThumbnailConcept }) {
  return (
    <Card className="bg-background/40 border-border">
      <CardContent className="p-3 space-y-1.5">
        <p className="text-body-sm font-medium text-foreground">{concept.concept}</p>
        {concept.visual_elements?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {concept.visual_elements.map((el, i) => (
              <Badge key={i} variant="outline" className="text-caption px-1.5 py-0 text-muted-foreground border-border/30 bg-muted/50">
                {el}
              </Badge>
            ))}
          </div>
        )}
        {concept.text_overlay && <p className="text-caption text-muted-foreground/70">Overlay: &ldquo;{concept.text_overlay}&rdquo;</p>}
        {concept.emotional_appeal && <p className="text-caption text-muted-foreground/70 italic">{concept.emotional_appeal}</p>}
      </CardContent>
    </Card>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface CreatorBriefRendererProps {
  content: any;
}

export function CreatorBriefRenderer({ content }: CreatorBriefRendererProps) {
  const data = content as ProducerPacketData;
  const angles = data?.narrative_angles ?? [];
  const hooks = data?.opening_hooks ?? [];
  const moments = data?.key_moments ?? [];
  const titles = data?.title_options ?? [];
  const thumbnails = data?.thumbnail_concepts ?? [];

  return (
    <div className="space-y-8">
      {/* Story Core — always visible, hero section */}
      <StoryCoreSection data={data} />

      {/* Recommendation reasoning */}
      {data?.recommendation_reasoning && (
        <div className="text-body-sm text-muted-foreground leading-relaxed bg-card/20 rounded-lg px-4 py-3 border border-border">
          <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-1.5">Recommendation</p>
          <p>{data.recommendation_reasoning}</p>
        </div>
      )}

      {/* Narrative Angles */}
      {angles.length > 0 && (
        <div>
          <SectionHeader title="Narrative Angles" count={angles.length} className="mb-3" />
          <AnglesSection angles={angles} recommendedAngleId={data?.recommended_angle_id ?? undefined} />
        </div>
      )}

      {/* Opening Hooks */}
      {hooks.length > 0 && (
        <div>
          <SectionHeader title="Opening Hooks" count={hooks.length} className="mb-3" />
          <HooksSection hooks={hooks} />
        </div>
      )}

      {/* Why It Matters */}
      {data?.story_core?.why_this_matters && (
        <WhyItMattersSection text={data.story_core.why_this_matters} />
      )}

      {/* Title Options */}
      {titles.length > 0 && (
        <div>
          <SectionHeader title="Title Options" count={titles.length} className="mb-3" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {titles.map((opt, i) => <TitleOptionCard key={i} option={opt} />)}
          </div>
        </div>
      )}

      {/* Collapsible sections */}
      <Accordion type="multiple" className="space-y-2">
        {/* Key Moments */}
        {moments.length > 0 && (
          <AccordionItem value="moments" className="border-0">
            <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
              <SectionHeader title="Key Moments" count={moments.length} />
            </AccordionTrigger>
            <AccordionContent className="pt-0 pb-0">
              <div className="border border-t-0 border-border rounded-b-lg px-4 divide-y divide-border">
                {moments.map((m, i) => <KeyMomentRow key={i} moment={m} />)}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Thumbnail Concepts */}
        {thumbnails.length > 0 && (
          <AccordionItem value="thumbnails" className="border-0">
            <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
              <SectionHeader title="Thumbnail Concepts" count={thumbnails.length} />
            </AccordionTrigger>
            <AccordionContent className="pt-0 pb-0">
              <div className="border border-t-0 border-border rounded-b-lg p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {thumbnails.map((c, i) => <ThumbnailCard key={i} concept={c} />)}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Interview Suggestions */}
        {data?.interview_suggestions && (
          <AccordionItem value="interview" className="border-0">
            <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
              <SectionHeader title="Interview Suggestions" />
            </AccordionTrigger>
            <AccordionContent className="pt-0 pb-0">
              <div className="border border-t-0 border-border rounded-b-lg p-4 space-y-3">
                {data.interview_suggestions.suggested_guests?.length > 0 && (
                  <div>
                    <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-2">Suggested Guests</p>
                    <ul className="space-y-2">
                      {data.interview_suggestions.suggested_guests.map((g: any, i: number) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-teal-500/50 flex-shrink-0 mt-0.5">•</span>
                          <div>
                            <span className="text-body-sm font-medium text-foreground">{g.name}</span>
                            <p className="text-caption text-muted-foreground/70">{g.why}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.interview_suggestions.key_questions?.length > 0 && (
                  <div>
                    <p className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider mb-2">Key Questions</p>
                    <ul className="space-y-1">
                      {data.interview_suggestions.key_questions.map((q: string, i: number) => (
                        <li key={i} className="text-body-sm text-muted-foreground flex gap-1.5">
                          <span className="text-teal-500/50 flex-shrink-0">?</span><span>{q}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Risk Assessment */}
        {data?.risk_assessment && (
          <AccordionItem value="risk" className="border-0">
            <AccordionTrigger className="rounded-lg bg-background/40 border border-border px-4 py-2.5 hover:bg-background/60 hover:no-underline [&[data-state=open]]:rounded-b-none">
              <SectionHeader title="Risk Assessment" />
            </AccordionTrigger>
            <AccordionContent className="pt-0 pb-0">
              <div className="border border-t-0 border-border rounded-b-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-caption text-muted-foreground/70 uppercase tracking-wider">Sensitivity</span>
                  <span className="text-body-sm font-medium text-red-400">{data.risk_assessment.sensitivity_level}</span>
                </div>
                {data.risk_assessment.potential_issues?.length > 0 && (
                  <div>
                    <p className="text-caption font-medium text-muted-foreground/70 uppercase mb-1">Potential Issues</p>
                    {data.risk_assessment.potential_issues.map((issue: string, i: number) => (
                      <p key={i} className="text-body-sm text-muted-foreground flex gap-1.5"><span className="text-red-500/50">•</span>{issue}</p>
                    ))}
                  </div>
                )}
                {data.risk_assessment.mitigation_suggestions?.length > 0 && (
                  <div>
                    <p className="text-caption font-medium text-muted-foreground/70 uppercase mb-1">Mitigation</p>
                    {data.risk_assessment.mitigation_suggestions.map((s: string, i: number) => (
                      <p key={i} className="text-body-sm text-muted-foreground flex gap-1.5"><span className="text-green-500/50">→</span>{s}</p>
                    ))}
                  </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}
      </Accordion>
    </div>
  );
}
