/**
 * CollapsibleSection — Progressive disclosure wrapper for document sections.
 *
 * ADHD-friendly: non-essential sections start collapsed to reduce overwhelm.
 * Clicking the header toggles visibility with a smooth transition.
 */

import { useState, type ReactNode } from 'react';

interface CollapsibleSectionProps {
  children: ReactNode;
  defaultOpen?: boolean;
  label?: string;
  itemCount?: number;
}

export function CollapsibleSection({
  children,
  defaultOpen = false,
  label,
  itemCount,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-[12px] text-gray-500 hover:text-gray-400 transition-colors py-1 group w-full text-left"
      >
        <svg
          className={`w-3 h-3 flex-shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="uppercase tracking-wider font-medium">
          {label || (isOpen ? 'Hide details' : 'Show details')}
        </span>
        {itemCount !== undefined && !isOpen && (
          <span className="text-gray-600">({itemCount} items)</span>
        )}
      </button>
      {isOpen && (
        <div className="mt-2">
          {children}
        </div>
      )}
    </div>
  );
}
