/**
 * JobCard configuration constants.
 */

export const statusConfig = {
  queued: {
    label: 'Queued',
    bgColor: 'bg-gray-800',
    textColor: 'text-gray-300',
    dotColor: 'bg-gray-400',
    borderColor: 'border-gray-700',
  },
  running: {
    label: 'Running',
    bgColor: 'bg-blue-900/50',
    textColor: 'text-blue-300',
    dotColor: 'bg-blue-400',
    borderColor: 'border-blue-500/50',
  },
  completed: {
    label: 'Completed',
    bgColor: 'bg-green-900/50',
    textColor: 'text-green-300',
    dotColor: 'bg-green-400',
    borderColor: 'border-green-500/50',
  },
  completed_with_warnings: {
    label: 'Completed',
    bgColor: 'bg-yellow-900/50',
    textColor: 'text-yellow-300',
    dotColor: 'bg-yellow-400',
    borderColor: 'border-yellow-500/50',
  },
  failed: {
    label: 'Failed',
    bgColor: 'bg-red-900/50',
    textColor: 'text-red-300',
    dotColor: 'bg-red-400',
    borderColor: 'border-red-500/50',
  },
  failed_insufficient: {
    label: 'Insufficient Data',
    bgColor: 'bg-orange-900/50',
    textColor: 'text-orange-300',
    dotColor: 'bg-orange-400',
    borderColor: 'border-orange-500/50',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-orange-900/50',
    textColor: 'text-orange-300',
    dotColor: 'bg-orange-400',
    borderColor: 'border-orange-500/50',
  },
  disambiguating: {
    label: 'Needs Input',
    bgColor: 'bg-yellow-900/50',
    textColor: 'text-yellow-300',
    dotColor: 'bg-yellow-400',
    borderColor: 'border-yellow-500/50',
  },
} as const;

export const pipelineLabels: Record<string, string> = {
  quick: 'Quick',
  full: 'Full',
  breaking_news: 'Breaking News',
  investigation: 'Investigation',
  profile: 'Profile',
  controversy: 'Controversy',
  video_analysis: 'Video Analysis',
};

export type JobStatus = keyof typeof statusConfig;
export type StatusConfig = (typeof statusConfig)[JobStatus];
