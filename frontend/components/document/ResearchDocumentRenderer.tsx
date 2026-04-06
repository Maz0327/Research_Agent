/**
 * ResearchDocumentRenderer — Routes typed JSON data to purpose-built renderers.
 *
 * Detects document type from `data.document_type` and renders with the
 * appropriate typed component. Falls back to MarkdownRenderer for legacy
 * jobs or documents without typed data.
 */

import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { transformMarkdownWithDetails } from '@/lib/document-formatters';
import type {
  SourceLedgerData,
  JumpStartData,
  SemanticBriefData,
  ProducerPacketData,
  BlogPostData,
  ScriptData,
  SocialKitData,
} from '@/types/documents';
import { SourceLedgerRenderer } from './SourceLedgerRenderer';
import { JumpStartRenderer } from './JumpStartRenderer';
import { SemanticBriefRenderer } from './SemanticBriefRenderer';
import { CreatorBriefRenderer } from './CreatorBriefRenderer';
import { CreatorBriefView } from '@/components/creator-brief/CreatorBriefView';
import { BlogPostRenderer } from './BlogPostRenderer';
import { ScriptRenderer } from './ScriptRenderer';
import { SocialKitRenderer } from './SocialKitRenderer';

export interface ResearchDocumentRendererProps {
  docNumber: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 'B';
  data: Record<string, unknown>;
  markdown?: string;
  showDetails?: boolean;
}

/** Check if data has a recognized document_type with actual content. */
function hasTypedData(data: Record<string, unknown>): boolean {
  if (!data || Object.keys(data).length === 0) return false;
  const docType = data.document_type;
  return (
    docType === 'source_ledger' ||
    docType === 'jump_start' ||
    docType === 'semantic_brief' ||
    docType === 'producer_packet' ||
    docType === 'creator_brief' ||
    docType === 'blog_post' ||
    docType === 'script' ||
    docType === 'social_kit'
  );
}

export function ResearchDocumentRenderer({
  docNumber,
  data,
  markdown,
  showDetails = false,
}: ResearchDocumentRendererProps) {
  // Route to typed renderer if we have structured data
  if (hasTypedData(data)) {
    switch (data.document_type) {
      case 'source_ledger':
        return <SourceLedgerRenderer data={data as unknown as SourceLedgerData} showDetails={showDetails} />;
      case 'jump_start':
        return <JumpStartRenderer data={data as unknown as JumpStartData} showDetails={showDetails} />;
      case 'semantic_brief':
        return <SemanticBriefRenderer data={data as unknown as SemanticBriefData} showDetails={showDetails} />;
      case 'producer_packet':
        return <CreatorBriefRenderer data={data as unknown as ProducerPacketData} showDetails={showDetails} />;
      case 'creator_brief':
        // Use CreatorBriefView with pre-loaded data (skip its internal fetch)
        return (
          <CreatorBriefView
            jobId={data.job_id as string || ''}
            data={data as any}
          />
        );
      case 'blog_post':
        return <BlogPostRenderer data={data as unknown as BlogPostData} showDetails={showDetails} jobId={data.job_id as string} />;
      case 'script':
        return <ScriptRenderer data={data as unknown as ScriptData} showDetails={showDetails} jobId={data.job_id as string} />;
      case 'social_kit':
        return <SocialKitRenderer data={data as unknown as SocialKitData} showDetails={showDetails} jobId={data.job_id as string} />;
    }
  }

  // Fallback: existing markdown rendering path
  if (markdown) {
    return (
      <div className="max-w-none">
        <MarkdownRenderer content={transformMarkdownWithDetails(markdown, showDetails)} />
      </div>
    );
  }

  // Last resort: raw JSON
  return (
    <pre className="text-sm text-muted-foreground font-mono whitespace-pre-wrap bg-card/50 rounded-lg p-4 overflow-x-auto">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export default ResearchDocumentRenderer;
