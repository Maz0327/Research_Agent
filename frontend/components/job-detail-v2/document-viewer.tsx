'use client';

/**
 * DocumentViewer — Dispatcher rendering document content by type.
 * Phase 5: Wires typed renderers from document-v2/ for all doc types.
 */

import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { SourceLedgerRenderer } from '@/components/document-v2/source-ledger-renderer';
import { JumpStartRenderer } from '@/components/document-v2/jump-start-renderer';
import { SemanticBriefRenderer } from '@/components/document-v2/semantic-brief-renderer';
import { CreatorBriefRenderer } from '@/components/document-v2/creator-brief-renderer';
import { ScriptRenderer } from '@/components/document-v2/script-renderer';
import { SocialKitRenderer } from '@/components/document-v2/social-kit-renderer';
import { BlogPostRenderer } from '@/components/document-v2/blog-post-renderer';
import type { Job } from '@/store/jobs';

const DOC_META: Record<number, { label: string; subtitle: string }> = {
  0: { label: 'Source Ledger',   subtitle: 'What was analyzed' },
  1: { label: 'Jump-Start',      subtitle: 'Where to go next' },
  2: { label: 'Semantic Brief',  subtitle: 'What sources reveal' },
  3: { label: 'Creator Brief',   subtitle: 'Your hero document' },
  4: { label: 'Producer Packet', subtitle: 'Production-ready package' },
  5: { label: 'Script',          subtitle: 'Script draft' },
  6: { label: 'Social Kit',      subtitle: 'Social media content' },
  7: { label: 'Blog Post',       subtitle: 'Long-form article' },
};

/** Extract structured JSON data for a given doc type from job artifacts */
function getDocData(job: Job, docType: number): Record<string, unknown> | null {
  const a = job.artifacts;
  if (!a) return null;
  const aa = a as any;
  switch (docType) {
    case 0: return (aa.source_ledger?.data ?? null) as Record<string, unknown> | null;
    case 1: return (aa.jump_start?.data ?? null) as Record<string, unknown> | null;
    case 2: return (aa.semantic_brief?.data ?? null) as Record<string, unknown> | null;
    case 3:
      // Prefer structured data path; fall back to markdown wrapper
      if (aa.doc_3_data) return aa.doc_3_data;
      if (a.creator_brief_md) return { markdown: a.creator_brief_md } as any;
      return null;
    case 5:
      return aa.script ?? null;
    case 6:
      return aa.social_kit ?? null;
    case 7:
      return aa.blog_post ?? null;
    default:
      return null;
  }
}

/** Render the correct typed renderer for a doc type */
function DocRenderer({ docType, content }: { docType: number; content: Record<string, unknown> }) {
  switch (docType) {
    case 0: return <SourceLedgerRenderer content={content} />;
    case 1: return <JumpStartRenderer content={content} />;
    case 2: return <SemanticBriefRenderer content={content} />;
    case 3: return <CreatorBriefRenderer content={content} />;
    case 5: return <ScriptRenderer content={content} />;
    case 6: return <SocialKitRenderer content={content} />;
    case 7: return <BlogPostRenderer content={content} />;
    default:
      return (
        <pre className="whitespace-pre-wrap text-xs text-foreground/80 font-mono leading-relaxed break-words">
          {JSON.stringify(content, null, 2)}
        </pre>
      );
  }
}

interface DocumentViewerProps {
  docType: number;
  job: Job;
}

export function DocumentViewer({ docType, job }: DocumentViewerProps) {
  const meta = DOC_META[docType] ?? { label: `Document ${docType}`, subtitle: '' };
  const content = getDocData(job, docType);

  return (
    <div className="flex flex-col h-full min-h-[400px]">
      {/* Doc header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <div>
          <h2 className="text-sm font-semibold text-foreground">{meta.label}</h2>
          <p className="text-xs text-muted-foreground">{meta.subtitle}</p>
        </div>
        <Badge variant="outline" className="text-xs border-border text-muted-foreground">
          Doc {docType}
        </Badge>
      </div>

      {/* Content area */}
      <Card className="flex-1 bg-card border-border">
        <ScrollArea className="h-[calc(100vh-280px)] min-h-[300px]">
          <CardContent className="p-4">
            {content ? (
              <DocRenderer docType={docType} content={content} />
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="h-10 w-10 rounded-full bg-secondary flex items-center justify-center mb-3">
                  <span className="text-lg text-muted-foreground">📄</span>
                </div>
                <p className="text-sm font-medium text-muted-foreground">{meta.label} not yet generated</p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  Complete the pipeline to generate this document
                </p>
              </div>
            )}
          </CardContent>
        </ScrollArea>
      </Card>
    </div>
  );
}
