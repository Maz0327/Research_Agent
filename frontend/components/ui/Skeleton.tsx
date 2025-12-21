/**
 * Skeleton loading component for content placeholders.
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
      className={`bg-gray-200 dark:bg-gray-700 ${roundedClasses[rounded]} ${className}`}
      style={{ width, height }}
      animate={{ opacity: [0.5, 1, 0.5] }}
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
    <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
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
