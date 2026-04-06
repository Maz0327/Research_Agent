/**
 * ActiveTaskBanner - Progress banner for active secondary tasks
 * Shows when booster, iteration, or producer is running.
 */
import { motion } from 'framer-motion';

/** Task types that can be shown in the banner */
export type TaskType = 'booster' | 'iteration' | 'producer';

/** Task status */
export type TaskStatus = 'queued' | 'running';

/** Configuration for each task type */
const TASK_CONFIG: Record<TaskType, {
  label: string;
  icon: string;
  color: string;
}> = {
  booster: {
    label: 'Deep Research',
    icon: '🔬',
    color: 'blue',
  },
  iteration: {
    label: 'Iteration',
    icon: '🔄',
    color: 'purple',
  },
  producer: {
    label: 'Producer Packet',
    icon: '🎬',
    color: 'green',
  },
};

export interface ActiveTaskBannerProps {
  /** Type of task running */
  taskType: TaskType;
  /** Current status */
  status: TaskStatus;
  /** Progress percentage (0-100) */
  progressPercent: number;
  /** Iteration ID (for iteration tasks) */
  iterationId?: string;
  /** Cancel handler (optional - some tasks may not be cancellable) */
  onCancel?: () => void;
}

export function ActiveTaskBanner({
  taskType,
  status,
  progressPercent,
  iterationId,
  onCancel,
}: ActiveTaskBannerProps) {
  const config = TASK_CONFIG[taskType];

  // Color classes based on task type
  const colorMap = {
    blue: {
      bg: 'bg-blue-900/30',
      border: 'border-blue-700',
      progress: 'bg-blue-500',
      text: 'text-blue-300',
    },
    purple: {
      bg: 'bg-purple-900/30',
      border: 'border-purple-700',
      progress: 'bg-purple-500',
      text: 'text-purple-300',
    },
    green: {
      bg: 'bg-green-900/30',
      border: 'border-green-700',
      progress: 'bg-green-500',
      text: 'text-green-300',
    },
  };
  const colorClasses = colorMap[config.color as keyof typeof colorMap];

  const statusText = status === 'queued'
    ? 'Queued...'
    : `${progressPercent}%`;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`
        rounded-xl border p-4 mb-6
        ${colorClasses.bg} ${colorClasses.border}
      `}
    >
      <div className="flex items-center justify-between gap-4">
        {/* Task info */}
        <div className="flex items-center gap-3">
          <span className="text-xl">{config.icon}</span>
          <div>
            <p className={`font-medium ${colorClasses.text}`}>
              {config.label} {status === 'running' ? 'in progress...' : 'starting...'}
            </p>
            {iterationId && (
              <p className="text-sm text-muted-foreground">{iterationId}</p>
            )}
          </div>
        </div>

        {/* Status and cancel */}
        <div className="flex items-center gap-4">
          <span className={`text-sm font-mono ${colorClasses.text}`}>
            {statusText}
          </span>
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-3 py-1 text-sm text-muted-foreground hover:text-white hover:bg-muted rounded transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {status === 'running' && (
        <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.3 }}
            className={`h-full ${colorClasses.progress} rounded-full`}
          />
        </div>
      )}

      {/* Pulsing indicator for queued */}
      {status === 'queued' && (
        <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
          <motion.div
            animate={{ x: ['-100%', '200%'] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            className={`h-full w-1/3 ${colorClasses.progress} rounded-full`}
          />
        </div>
      )}
    </motion.div>
  );
}

export default ActiveTaskBanner;
