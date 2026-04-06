/**
 * BoldFirstSentence — Utility component for ADHD-friendly text formatting.
 *
 * Bolds the first sentence of a text block to create a scannable anchor.
 * Splits at the first ". " within 150 characters. If no period found
 * within that window, bolds the entire text (it's already short enough).
 */

interface BoldFirstSentenceProps {
  text: string;
  className?: string;
}

export function BoldFirstSentence({ text, className = '' }: BoldFirstSentenceProps) {
  if (!text) return null;

  // Find first sentence boundary within 150 chars
  const periodIndex = text.indexOf('. ');
  const shouldSplit = periodIndex > 0 && periodIndex <= 150;

  if (!shouldSplit) {
    // Short enough or no clear sentence boundary — render as-is with emphasis
    return <p className={className}>{text}</p>;
  }

  const firstSentence = text.slice(0, periodIndex + 1);
  const rest = text.slice(periodIndex + 2);

  return (
    <p className={className}>
      <strong className="text-foreground">{firstSentence}</strong>{' '}
      {rest}
    </p>
  );
}
