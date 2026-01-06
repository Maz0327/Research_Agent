/**
 * L-016: Shared CopyButton component to reduce duplication across views.
 * Handles clipboard copy with fallback and visual feedback.
 */
import { useState, useCallback } from 'react';

interface CopyButtonProps {
  /** Text content to copy */
  text: string;
  /** Button label (default: "Copy") */
  label?: string;
  /** Label shown after successful copy (default: "Copied!") */
  copiedLabel?: string;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Additional CSS classes */
  className?: string;
}

/**
 * A reusable copy-to-clipboard button with visual feedback.
 * Uses modern Clipboard API with textarea fallback.
 */
export function CopyButton({
  text,
  label = 'Copy',
  copiedLabel = 'Copied!',
  size = 'sm',
  className = '',
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers or non-secure contexts
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-999999px';
      textarea.style.top = '-999999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        console.error('Failed to copy text');
      }
      document.body.removeChild(textarea);
    }
  }, [text]);

  const sizeClasses = size === 'sm' 
    ? 'px-1.5 py-0.5 text-xs'
    : 'px-2 py-1 text-sm';

  return (
    <button
      onClick={handleCopy}
      className={`inline-flex items-center gap-1 rounded transition ${sizeClasses} ${
        copied
          ? 'bg-green-600 text-white'
          : 'bg-gray-700 text-gray-400 hover:bg-gray-600 hover:text-gray-300'
      } ${className}`}
      aria-label={copied ? `${copiedLabel}` : `${label} to clipboard`}
      title={copied ? copiedLabel : label}
    >
      {copied ? (
        <>
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{copiedLabel}</span>
        </>
      ) : (
        <>
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
            />
          </svg>
          <span>{label}</span>
        </>
      )}
    </button>
  );
}

export default CopyButton;



