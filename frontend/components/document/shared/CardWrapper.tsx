/**
 * CardWrapper — Shared card container with optional left accent bar.
 *
 * Consistent styling across all typed document renderers.
 */

import type { ReactNode } from 'react';

interface CardWrapperProps {
  children: ReactNode;
  accentColor?: string; // Tailwind bg class, e.g. 'bg-blue-500'
  className?: string;
}

export function CardWrapper({ children, accentColor, className = '' }: CardWrapperProps) {
  return (
    <div className={`relative bg-gray-800/40 rounded-lg border border-gray-700/40 p-3 sm:p-5 overflow-hidden ${className}`}>
      {accentColor && (
        <div className={`absolute top-0 left-0 bottom-0 w-1 rounded-l-lg ${accentColor}`} />
      )}
      <div className={accentColor ? 'pl-2 sm:pl-3' : ''}>
        {children}
      </div>
    </div>
  );
}
