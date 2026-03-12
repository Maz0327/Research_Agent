/**
 * ArtifactCard - Individual card for each artifact type (Doc 0/1/2/3, Booster, Iterations)
 * Displays visual state (not_available, ready, queued, running, completed, failed)
 * with appropriate actions and progress indicators.
 */
import { motion } from 'framer-motion';

/** Artifact card visual states */
export type ArtifactState =
  | 'not_available'
  | 'ready'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

/** Artifact types supported by the card */
export type ArtifactType =
  | 'doc_0'
  | 'doc_1'
  | 'doc_2'
  | 'doc_3'
  | 'doc_4'
  | 'booster'
  | 'iteration'
  | 'claims_doc';

/** Configuration for each artifact type */
const ARTIFACT_CONFIG: Record<ArtifactType, {
  title: string;
  subtitle: string;
  icon: string;
  readyLabel: string;
}> = {
  doc_0: {
    title: 'Doc 0',
    subtitle: 'Source Ledger',
    icon: '📋',
    readyLabel: 'View Sources'
  },
  doc_1: {
    title: 'Doc 1',
    subtitle: 'Jump-Start',
    icon: '🚀',
    readyLabel: 'View Directions'
  },
  doc_2: {
    title: 'Doc 2',
    subtitle: 'Semantic Brief',
    icon: '📊',
    readyLabel: 'View Brief'
  },
  doc_3: {
    title: 'Doc 3',
    subtitle: 'Creator Brief',
    icon: '✨',
    readyLabel: 'View Brief'
  },
  doc_4: {
    title: 'Doc 4',
    subtitle: 'Producer Packet',
    icon: '🎬',
    readyLabel: 'Generate'
  },
  booster: {
    title: 'Deep Research',
    subtitle: 'Expanded Analysis',
    icon: '🔬',
    readyLabel: 'Start Analysis'
  },
  iteration: {
    title: 'Iterations',
    subtitle: 'Additional Passes',
    icon: '🔄',
    readyLabel: 'Run New Pass'
  },
  claims_doc: {
    title: 'Claims Document',
    subtitle: 'Extracted Claims',
    icon: '📝',
    readyLabel: 'View Claims'
  },
};

/** State-based styling */
const STATE_STYLES: Record<ArtifactState, {
  border: string;
  bg: string;
  text: string;
  cursor: string;
}> = {
  not_available: {
    border: 'border-gray-700 border-dashed',
    bg: 'bg-gray-900/50',
    text: 'text-gray-500',
    cursor: 'cursor-not-allowed',
  },
  ready: {
    border: 'border-blue-600 hover:border-blue-500',
    bg: 'bg-gray-900 hover:bg-gray-800',
    text: 'text-blue-400',
    cursor: 'cursor-pointer',
  },
  queued: {
    border: 'border-yellow-600 animate-pulse',
    bg: 'bg-gray-900',
    text: 'text-yellow-400',
    cursor: 'cursor-wait',
  },
  running: {
    border: 'border-blue-500',
    bg: 'bg-gray-900',
    text: 'text-blue-400',
    cursor: 'cursor-wait',
  },
  completed: {
    border: 'border-green-600 hover:border-green-500',
    bg: 'bg-gray-900 hover:bg-gray-800',
    text: 'text-green-400',
    cursor: 'cursor-pointer',
  },
  failed: {
    border: 'border-red-600 hover:border-red-500',
    bg: 'bg-red-900/20 hover:bg-red-900/30',
    text: 'text-red-400',
    cursor: 'cursor-pointer',
  },
};

export interface ArtifactCardProps {
  /** Type of artifact */
  type: ArtifactType;
  /** Current state of the artifact */
  state: ArtifactState;
  /** Progress percentage (0-100) for running state */
  progressPercent?: number;
  /** Error message for failed state */
  error?: string;
  /** Iteration count (for iteration type) */
  iterationCount?: number;
  /** Current iteration ID (for iteration type when running) */
  iterationId?: string;
  /** Click handler for primary action */
  onClick: () => void;
  /** Retry handler for failed state */
  onRetry?: () => void;
}

export function ArtifactCard({
  type,
  state,
  progressPercent = 0,
  error,
  iterationCount = 0,
  iterationId,
  onClick,
  onRetry,
}: ArtifactCardProps) {
  const config = ARTIFACT_CONFIG[type];
  const styles = STATE_STYLES[state];

  // Narrated status descriptions for running state
  const getRunningDescription = () => {
    switch (type) {
      case 'doc_0':
        return 'Cataloging your sources…';
      case 'doc_1':
        return 'Finding research directions…';
      case 'doc_2':
        return 'Synthesizing themes and insights…';
      case 'doc_3':
        return 'Distilling hooks and core facts…';
      case 'doc_4':
        return 'Generating production notes…';
      case 'booster':
        return 'Exploring new directions…';
      case 'iteration':
        return 'Running additional analysis…';
      case 'claims_doc':
        return 'Extracting claims…';
      default:
        return 'Processing…';
    }
  };

  // Determine action label based on state
  const getActionLabel = () => {
    switch (state) {
      case 'not_available':
        return 'Not Available';
      case 'ready':
        return config.readyLabel;
      case 'queued':
        return 'Queued - waiting to start...';
      case 'running':
        return `${progressPercent}% - ${getRunningDescription()}`;
      case 'completed':
        if (type === 'iteration' && iterationCount > 0) {
          return `${iterationCount} iteration${iterationCount > 1 ? 's' : ''}`;
        }
        return 'View';
      case 'failed':
        return 'Retry';
      default:
        return '';
    }
  };

  // Handle click based on state
  const handleClick = () => {
    if (state === 'not_available' || state === 'queued' || state === 'running') {
      return;
    }
    if (state === 'failed' && onRetry) {
      onRetry();
    } else {
      onClick();
    }
  };

  return (
    <motion.div
      whileHover={state !== 'not_available' && state !== 'queued' && state !== 'running' ? { scale: 1.02 } : {}}
      whileTap={state !== 'not_available' && state !== 'queued' && state !== 'running' ? { scale: 0.98 } : {}}
      onClick={handleClick}
      className={`
        relative rounded-xl border-2 p-4 transition-all duration-200
        ${styles.border} ${styles.bg} ${styles.cursor}
      `}
    >
      {/* Icon and title */}
      <div className="flex items-start gap-3">
        <span className="text-2xl">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className={`font-semibold ${styles.text}`}>{config.title}</h3>
          <p className="text-sm text-gray-400 truncate">{config.subtitle}</p>
        </div>

        {/* Status indicator */}
        <div className="flex-shrink-0">
          {state === 'completed' && (
            <span className="text-green-400">✓</span>
          )}
          {state === 'failed' && (
            <span className="text-red-400">✗</span>
          )}
          {state === 'running' && (
            <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          )}
          {state === 'queued' && (
            <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
          )}
        </div>
      </div>

      {/* Progress bar for running state */}
      {state === 'running' && (
        <div className="mt-3">
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              className="h-full bg-blue-500 rounded-full"
              transition={{ duration: 0.3 }}
            />
          </div>
          {iterationId && (
            <p className="text-xs text-gray-400 mt-1">{iterationId}</p>
          )}
        </div>
      )}

      {/* Action label */}
      <div className="mt-3">
        <span className={`text-sm font-medium ${styles.text}`}>
          {getActionLabel()}
        </span>
      </div>

      {/* Error preview for failed state */}
      {state === 'failed' && error && (
        <p className="mt-2 text-xs text-red-300 line-clamp-2">{error}</p>
      )}
    </motion.div>
  );
}

export default ArtifactCard;
