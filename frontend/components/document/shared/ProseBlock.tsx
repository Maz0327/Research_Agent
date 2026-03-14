/**
 * ProseBlock — Constrained typography wrapper for narrative markdown content.
 *
 * Uses MarkdownRenderer with readable typography constraints.
 */

import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';

interface ProseBlockProps {
  content: string;
  compact?: boolean;
}

export function ProseBlock({ content, compact = false }: ProseBlockProps) {
  if (!content) return null;

  return (
    <div className="max-w-none sm:max-w-[720px] text-[14px] sm:text-[15px] leading-[1.75]">
      <MarkdownRenderer content={content} compact={compact} />
    </div>
  );
}
