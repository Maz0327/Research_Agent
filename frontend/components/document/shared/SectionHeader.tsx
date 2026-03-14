/**
 * SectionHeader — Consistent section heading with optional count badge.
 *
 * Renders an H2 or H3 with left accent bar, subtitle, and optional count.
 */

import type { ReactNode } from 'react';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  count?: number;
  accentColor?: string; // Tailwind bg class, e.g. 'bg-blue-500'
  icon?: ReactNode;
  level?: 2 | 3;
}

export function SectionHeader({
  title,
  subtitle,
  count,
  accentColor = 'bg-blue-500',
  icon,
  level = 2,
}: SectionHeaderProps) {
  const Tag = level === 2 ? 'h2' : 'h3';
  const titleSize = level === 2 ? 'text-lg font-semibold' : 'text-base font-semibold';

  return (
    <div className="flex items-start gap-2 sm:gap-3">
      <div className={`w-1 self-stretch rounded-full ${accentColor} flex-shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 sm:gap-2.5 flex-wrap">
          {icon && <span className="text-gray-400 flex-shrink-0">{icon}</span>}
          <Tag className={`${titleSize} text-gray-100`}>{title}</Tag>
          {count !== undefined && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-700/60 text-gray-400">
              {count}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="text-sm text-gray-500 mt-0.5 ml-0">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
