/**
 * prose-block — Thin wrapper around MarkdownRenderer with prose-sm prose-invert styling.
 */

import MarkdownRenderer from '@/components/common/MarkdownRenderer';
import { cn } from '@/lib/utils';

interface ProseBlockProps {
  content: string;
  className?: string;
}

export function ProseBlock({ content, className }: ProseBlockProps) {
  return (
    <div className={cn('prose prose-sm prose-invert max-w-none', className)}>
      <MarkdownRenderer content={content} />
    </div>
  );
}
