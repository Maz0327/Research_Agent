/**
 * Progress bar component for displaying job progress.
 */
import { motion } from 'framer-motion';

interface ProgressBarProps {
  progress: number;
}

export function ProgressBar({ progress }: ProgressBarProps) {
  return (
    <div className="mt-4">
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-gray-500">Progress</span>
        <span className="font-medium text-gray-300">{progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-800">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
