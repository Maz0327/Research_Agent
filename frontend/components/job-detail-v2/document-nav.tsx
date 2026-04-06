'use client';

/**
 * DocumentNav — Vertical tab-style nav listing available documents for a job.
 * Only shows docs that exist in job.artifacts.
 * Active doc highlighted with accent-blue bg.
 */
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { JobArtifacts } from '@/store/jobs';

export interface DocNavItem {
  docType: number;
  label: string;
  subtitle: string;
  accentClass: string;
}

const DOC_DEFINITIONS: DocNavItem[] = [
  { docType: 0, label: 'Your Sources',    subtitle: 'What was analyzed',       accentClass: 'text-muted-foreground' },
  { docType: 1, label: 'Research Gaps',   subtitle: 'Where to go next',        accentClass: 'text-blue-400' },
  { docType: 2, label: 'Key Findings',    subtitle: 'What sources reveal',      accentClass: 'text-purple-400' },
  { docType: 3, label: 'Story Angles',    subtitle: 'Your hero document',       accentClass: 'text-amber-400' },
  { docType: 4, label: 'Producer Guide',  subtitle: 'Production-ready package', accentClass: 'text-green-400' },
  { docType: 5, label: 'Script',          subtitle: 'Script draft',             accentClass: 'text-sky-400' },
  { docType: 6, label: 'Social Kit',      subtitle: 'Social media content',     accentClass: 'text-pink-400' },
  { docType: 7, label: 'Blog Post',       subtitle: 'Long-form article',        accentClass: 'text-teal-400' },
];

/** Check whether a doc type exists in artifacts */
function docExists(artifacts: JobArtifacts | undefined, docType: number): boolean {
  if (!artifacts) return false;
  switch (docType) {
    case 0: return !!(artifacts.doc_0_path || artifacts.source_ledger);
    case 1: return !!(artifacts.doc_1_path || artifacts.jump_start);
    case 2: return !!(artifacts.doc_2_path || artifacts.semantic_brief);
    case 3: return !!(artifacts.doc_3_path || artifacts.creator_brief_md);
    case 4: return !!(artifacts.doc_4_path || artifacts.producer_packet_md);
    default: return false;
  }
}

interface DocumentNavProps {
  artifacts: JobArtifacts | undefined;
  selectedDoc: number;
  onSelectDoc: (docType: number) => void;
}

export function DocumentNav({ artifacts, selectedDoc, onSelectDoc }: DocumentNavProps) {
  const available = DOC_DEFINITIONS.filter((d) => docExists(artifacts, d.docType));

  if (!available.length) {
    return (
      <p className="text-xs text-muted-foreground py-2">No documents available yet.</p>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
        Documents
      </p>
      {available.map((doc) => {
        const isActive = selectedDoc === doc.docType;
        return (
          <button
            key={doc.docType}
            onClick={() => onSelectDoc(doc.docType)}
            className={cn(
              'w-full text-left rounded-md px-3 py-2 transition-colors',
              isActive
                ? 'bg-blue-600/20 border border-blue-600/40'
                : 'hover:bg-secondary border border-transparent'
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className={cn('text-xs font-medium truncate', isActive ? 'text-blue-300' : 'text-foreground')}>
                  {doc.label}
                </p>
                <p className="text-caption text-muted-foreground truncate">{doc.subtitle}</p>
              </div>
              <Badge
                variant="outline"
                className={cn('text-caption px-1 py-0 flex-shrink-0 border-border', doc.accentClass)}
              >
                v1
              </Badge>
            </div>
          </button>
        );
      })}
    </div>
  );
}
