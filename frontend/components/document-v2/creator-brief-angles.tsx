/**
 * creator-brief-angles — Narrative Angles section for Creator Brief (Doc 3).
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CitationPill } from './shared/citation-pill';
import type { NarrativeAngle } from '@/types/documents';

interface AngleCardProps {
  angle: NarrativeAngle;
  isRecommended: boolean;
}

function AngleCard({ angle, isRecommended }: AngleCardProps) {
  return (
    <Card className={`border-l-2 border-border bg-background/60 ${isRecommended ? 'border-l-amber-500' : 'border-l-zinc-600/40'}`}>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {isRecommended && (
            <Badge variant="outline" className="text-caption px-1.5 py-0 bg-amber-900/40 text-amber-400 border-amber-800/30 font-medium">
              Recommended
            </Badge>
          )}
          {angle.confidence && (
            <Badge variant="outline" className="text-caption px-1.5 py-0 bg-muted/60 text-muted-foreground">
              {angle.confidence}
            </Badge>
          )}
        </div>
        <h3 className="text-body-lg font-semibold text-foreground">{angle.title}</h3>
        <p className="text-body-sm text-muted-foreground leading-relaxed">{angle.description}</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          {angle.strengths?.length > 0 && (
            <div>
              <p className="text-caption font-medium text-green-500 uppercase tracking-wider mb-1">Strengths</p>
              <ul className="space-y-0.5">
                {angle.strengths.map((s, i) => (
                  <li key={i} className="text-body-sm text-muted-foreground flex gap-1.5">
                    <span className="text-green-500/50 flex-shrink-0">+</span><span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {angle.weaknesses?.length > 0 && (
            <div>
              <p className="text-caption font-medium text-red-500 uppercase tracking-wider mb-1">Weaknesses</p>
              <ul className="space-y-0.5">
                {angle.weaknesses.map((w, i) => (
                  <li key={i} className="text-body-sm text-muted-foreground flex gap-1.5">
                    <span className="text-red-500/50 flex-shrink-0">-</span><span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {angle.best_for && (
          <p className="text-caption text-muted-foreground/70 pt-1 border-t border-border">
            <span className="text-muted-foreground/60">Best for:</span> {angle.best_for}
          </p>
        )}
        {angle.key_sources?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {angle.key_sources.map((sid) => <CitationPill key={sid} id={sid} />)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface AnglesSectionProps {
  angles: NarrativeAngle[];
  recommendedAngleId?: string;
}

export function AnglesSection({ angles, recommendedAngleId }: AnglesSectionProps) {
  if (!angles?.length) return null;
  return (
    <div className="space-y-3">
      {angles.map((angle) => (
        <AngleCard
          key={angle.angle_id}
          angle={angle}
          isRecommended={angle.angle_id === recommendedAngleId}
        />
      ))}
    </div>
  );
}
