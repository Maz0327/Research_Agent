/**
 * Shared spinner component to replace inline SVG spinners.
 *
 * Extracted from 24+ locations across the frontend (Audit Fix 14.1).
 *
 * Usage:
 *   <Spinner />                    // default size (h-4 w-4)
 *   <Spinner size="sm" />          // h-3 w-3
 *   <Spinner size="lg" />          // h-6 w-6
 *   <Spinner className="h-8 w-8" /> // custom size
 */

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'h-3 w-3',
  md: 'h-4 w-4',
  lg: 'h-6 w-6',
};

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizeClass = className || sizeClasses[size];

  return (
    <svg
      className={`animate-spin ${sizeClass}`}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
