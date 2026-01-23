/**
 * TaskBadges - Mini chip badges for active/completed secondary tasks
 * Shows status of booster, producer, and iteration tasks on dashboard cards.
 */
import { motion } from 'framer-motion';

export interface TaskBadgesProps {
  /** Booster execution status */
  boosterStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** Booster progress percentage (0-100) */
  boosterProgressPercent?: number;
  /** Iteration execution status */
  iterationStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** Current iteration ID when running */
  iterationId?: string;
  /** Iteration progress percentage (0-100) */
  iterationProgressPercent?: number;
  /** Number of completed iterations */
  iterationCount?: number;
  /** Whether Doc 3 (Producer Packet) exists */
  hasProducerPacket?: boolean;
}

export function TaskBadges({
  boosterStatus,
  boosterProgressPercent = 0,
  iterationStatus,
  iterationId,
  iterationProgressPercent = 0,
  iterationCount = 0,
  hasProducerPacket = false,
}: TaskBadgesProps) {
  const badges: React.ReactNode[] = [];

  // Booster badge
  if (boosterStatus === 'running' || boosterStatus === 'queued') {
    badges.push(
      <motion.span
        key="booster-running"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-900/50 text-indigo-300 border border-indigo-700/50"
      >
        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
        {boosterStatus === 'running' ? `${boosterProgressPercent}%` : 'Queued'}
      </motion.span>
    );
  } else if (boosterStatus === 'completed') {
    badges.push(
      <span
        key="booster-done"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-900/30 text-indigo-400 border border-indigo-800/30"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
        Deep Research
      </span>
    );
  } else if (boosterStatus === 'failed') {
    badges.push(
      <span
        key="booster-failed"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-900/30 text-red-400 border border-red-800/30"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
        Booster Failed
      </span>
    );
  }

  // Iteration badge
  if (iterationStatus === 'running' || iterationStatus === 'queued') {
    badges.push(
      <motion.span
        key="iteration-running"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-900/50 text-purple-300 border border-purple-700/50"
      >
        <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse" />
        {iterationId ? `${iterationId.slice(-4)} ` : ''}
        {iterationStatus === 'running' ? `${iterationProgressPercent}%` : 'Queued'}
      </motion.span>
    );
  } else if (iterationCount > 0) {
    badges.push(
      <span
        key="iterations-count"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-900/30 text-purple-400 border border-purple-800/30"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {iterationCount} iteration{iterationCount > 1 ? 's' : ''}
      </span>
    );
  } else if (iterationStatus === 'failed') {
    badges.push(
      <span
        key="iteration-failed"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-900/30 text-red-400 border border-red-800/30"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
        Iteration Failed
      </span>
    );
  }

  // Producer Packet badge
  if (hasProducerPacket) {
    badges.push(
      <span
        key="producer"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-900/30 text-amber-400 border border-amber-800/30"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
        Doc 3
      </span>
    );
  }

  if (badges.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2">
      {badges}
    </div>
  );
}

export default TaskBadges;
