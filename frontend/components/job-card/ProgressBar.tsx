/**
 * Progress bar component for displaying job progress.
 * Simplified design with minimal visual noise.
 */
import { motion } from 'framer-motion';

interface ProgressBarProps {
  progress: number;
  /** Optional stage description for human-readable status */
  stageDescription?: string;
}

export function ProgressBar({ progress, stageDescription }: ProgressBarProps) {
  return (
    <div className="mt-5 space-y-3">
      {/* Progress bar - clean and minimal */}
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
        <motion.div
          className="h-full rounded-full bg-blue-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
      {/* Single line status - human readable */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-300">
          {stageDescription || `Processing... ${progress}%`}
        </span>
        <span className="text-blue-400 font-medium tabular-nums">{progress}%</span>
      </div>
    </div>
  );
}

export default ProgressBar;
