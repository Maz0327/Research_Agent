'use client';

/**
 * CircularGauge — SVG donut-style circular progress indicator.
 * Uses stroke-dasharray trick on a radius-16 circle (viewBox 0 0 36 36).
 * Circumference ≈ 100.53, so stroke-dasharray values map ~1:1 to percentage.
 *
 * Props:
 *   value   — 0-100 integer
 *   label   — optional centre text override (default: value + "%")
 *   size    — 'sm' (64px) | 'md' (80px) | 'lg' (96px)
 *   color   — accent palette key
 */

import { cn } from '@/lib/utils';

type GaugeSize = 'sm' | 'md' | 'lg';
type GaugeColor = 'blue' | 'purple' | 'green' | 'orange' | 'red' | 'amber';

interface CircularGaugeProps {
  value: number;
  label?: string;
  size?: GaugeSize;
  color?: GaugeColor;
  className?: string;
}

const SIZE_PX: Record<GaugeSize, number> = { sm: 64, md: 80, lg: 96 };

const STROKE_COLORS: Record<GaugeColor, string> = {
  blue:   '#3b82f6',
  purple: '#8b5cf6',
  green:  '#22c55e',
  orange: '#f97316',
  red:    '#ef4444',
  amber:  '#f59e0b',
};

const TEXT_CLASSES: Record<GaugeColor, string> = {
  blue:   'text-accent-blue',
  purple: 'text-accent-purple',
  green:  'text-accent-green',
  orange: 'fill-orange-500',
  red:    'fill-destructive',
  amber:  'fill-amber-500',
};

// SVG constants — radius 16, centre 18,18
const R = 16;
const CX = 18;
const CY = 18;
// Circumference = 2πr ≈ 100.53 → we treat 100 units as full circle
const CIRC = 2 * Math.PI * R; // ~100.53

export function CircularGauge({
  value,
  label,
  size = 'md',
  color = 'blue',
  className,
}: CircularGaugeProps) {
  const clamped = Math.min(100, Math.max(0, value));
  const px = SIZE_PX[size];
  const strokeColor = STROKE_COLORS[color];

  // Map 0-100 value to dasharray on actual circumference
  const filled = (clamped / 100) * CIRC;
  const empty = CIRC - filled;

  // Font size scales with container
  const fontSize = size === 'sm' ? '7' : size === 'md' ? '8' : '9';

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: px, height: px }}
      role="img"
      aria-label={`${label ?? `${clamped}%`} gauge`}
    >
      <svg
        viewBox="0 0 36 36"
        width={px}
        height={px}
        className="block"
        aria-hidden="true"
      >
        {/* Track ring */}
        <circle
          cx={CX}
          cy={CY}
          r={R}
          fill="none"
          stroke="#222230"
          strokeWidth="3"
        />

        {/* Progress arc — starts from top (offset -25 = quarter turn back) */}
        <circle
          cx={CX}
          cy={CY}
          r={R}
          fill="none"
          stroke={strokeColor}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${empty}`}
          strokeDashoffset={CIRC * 0.25} /* start from 12 o'clock */
          className="transition-all duration-500 ease-out"
          style={{ transformOrigin: 'center', transform: 'rotate(-90deg)' }}
        />

        {/* Centre label */}
        <text
          x={CX}
          y={CY}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={fontSize}
          fontWeight="600"
          fill={strokeColor}
          fontFamily="inherit"
        >
          {label ?? `${clamped}%`}
        </text>
      </svg>
    </div>
  );
}
