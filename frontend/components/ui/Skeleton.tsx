/**
 * Skeleton loading component for content placeholders.
 * Dark mode styling with shimmer effect.
 */
import { motion } from 'framer-motion';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full';
}

const roundedClasses = {
  none: '',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

export default function Skeleton({
  className = '',
  width,
  height,
  rounded = 'md',
}: SkeletonProps) {
  return (
    <motion.div
      className={`bg-gray-800 ${roundedClasses[rounded]} ${className}`}
      style={{ width, height }}
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={16}
          width={i === lines - 1 ? '60%' : '100%'}
        />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton height={24} width="70%" className="mb-2" />
          <Skeleton height={16} width="40%" />
        </div>
        <Skeleton height={28} width={80} rounded="full" />
      </div>
      <div className="mt-4">
        <Skeleton height={8} className="mb-2" rounded="full" />
        <div className="flex justify-between">
          <Skeleton height={14} width={60} />
          <Skeleton height={14} width={40} />
        </div>
      </div>
    </div>
  );
}
