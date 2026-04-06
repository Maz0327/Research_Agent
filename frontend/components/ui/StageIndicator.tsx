/**
 * Stage indicator component for visualizing pipeline progress.
 */
import { motion } from 'framer-motion';

export interface Stage {
  id: string;
  label: string;
  description?: string;
}

interface StageIndicatorProps {
  stages: Stage[];
  currentStage: string;
  completedStages: string[];
  className?: string;
}

const PIPELINE_STAGES: Stage[] = [
  { id: 'init', label: 'Initializing', description: 'Setting up the research job' },
  { id: 'planning', label: 'Planning', description: 'AI is planning research approach' },
  { id: 'mapping', label: 'Research Mapping', description: 'Identifying angles and key terms' },
  { id: 'discovery', label: 'Source Discovery', description: 'Finding relevant sources' },
  { id: 'youtube', label: 'YouTube Search', description: 'Finding video content' },
  { id: 'transcripts', label: 'Transcripts', description: 'Extracting video transcripts' },
  { id: 'capture', label: 'Web Capture', description: 'Capturing web content' },
  { id: 'extraction', label: 'Claim Extraction', description: 'Extracting key claims' },
  { id: 'validation', label: 'Validation', description: 'Validating claims with evidence' },
  { id: 'documents', label: 'Documents', description: 'Creating output documents' },
];

export { PIPELINE_STAGES };

export default function StageIndicator({
  stages = PIPELINE_STAGES,
  currentStage,
  completedStages,
  className = '',
}: StageIndicatorProps) {
  const currentIndex = stages.findIndex((s) => s.id === currentStage);

  return (
    <div className={`space-y-2 ${className}`}>
      {stages.map((stage, index) => {
        const isCompleted = completedStages.includes(stage.id);
        const isCurrent = stage.id === currentStage;
        const isPending = !isCompleted && !isCurrent;

        return (
          <motion.div
            key={stage.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-colors ${
              isCurrent
                ? 'bg-blue-50 dark:bg-blue-900/20'
                : isCompleted
                ? 'bg-green-50 dark:bg-green-900/20'
                : 'bg-card'
            }`}
          >
            {/* Status icon */}
            <div
              className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full ${
                isCompleted
                  ? 'bg-green-500 text-white'
                  : isCurrent
                  ? 'bg-blue-500 text-white'
                  : 'bg-secondary'
              }`}
            >
              {isCompleted ? (
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : isCurrent ? (
                <motion.div
                  className="h-2 w-2 rounded-full bg-white"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              ) : (
                <span className="text-xs font-medium text-muted-foreground">
                  {index + 1}
                </span>
              )}
            </div>

            {/* Stage info */}
            <div className="flex-1 min-w-0">
              <p
                className={`text-sm font-medium ${
                  isCurrent
                    ? 'text-blue-300'
                    : isCompleted
                    ? 'text-green-300'
                    : 'text-muted-foreground'
                }`}
              >
                {stage.label}
              </p>
              {isCurrent && stage.description && (
                <p className="text-xs text-muted-foreground truncate">
                  {stage.description}
                </p>
              )}
            </div>

            {/* Current stage spinner */}
            {isCurrent && (
              <motion.div
                className="h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              />
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

// Compact version for inline display
export function StageIndicatorCompact({
  currentStage,
  progress,
}: {
  currentStage: string;
  progress: number;
}) {
  const stage = PIPELINE_STAGES.find((s) => s.id === currentStage);

  return (
    <div className="flex items-center gap-2">
      <motion.div
        className="h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent"
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
      <span className="text-sm text-muted-foreground/60 dark:text-muted-foreground">
        {stage?.label || currentStage} ({progress}%)
      </span>
    </div>
  );
}
