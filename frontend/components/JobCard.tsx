/**
 * Job card component for displaying job status in the dashboard.
 */
import Link from 'next/link';

interface JobCardProps {
  id: string;
  prompt: string;
  pipeline: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  createdAt: string;
  artifacts?: {
    drive_folder_url?: string;
    doc_urls?: string[];
  };
}

const statusConfig = {
  queued: {
    label: 'Queued',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    dotColor: 'bg-gray-400',
  },
  running: {
    label: 'Running',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    dotColor: 'bg-blue-400',
  },
  completed: {
    label: 'Completed',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    dotColor: 'bg-green-400',
  },
  failed: {
    label: 'Failed',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
    dotColor: 'bg-red-400',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-700',
    dotColor: 'bg-orange-400',
  },
};

const pipelineLabels: Record<string, string> = {
  quick: 'Quick',
  full: 'Full',
  breaking_news: 'Breaking News',
  investigation: 'Investigation',
  profile: 'Profile',
  controversy: 'Controversy',
};

export default function JobCard({
  id,
  prompt,
  pipeline,
  status,
  progress,
  createdAt,
  artifacts,
}: JobCardProps) {
  const config = statusConfig[status];
  const pipelineLabel = pipelineLabels[pipeline] || pipeline;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Link
            href={`/jobs/${id}`}
            className="text-lg font-medium text-gray-900 hover:text-blue-600"
          >
            {prompt.length > 60 ? prompt.substring(0, 60) + '...' : prompt}
          </Link>
          <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
            <span>{pipelineLabel}</span>
            <span>&middot;</span>
            <span>{formatDate(createdAt)}</span>
          </div>
        </div>

        {/* Status badge */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${config.bgColor} ${config.textColor}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${config.dotColor}`}></span>
          {config.label}
        </span>
      </div>

      {/* Progress bar (only show for running jobs) */}
      {status === 'running' && (
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-gray-600">Progress</span>
            <span className="font-medium text-gray-900">{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-3">
        <Link
          href={`/jobs/${id}`}
          className="text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          View Details
        </Link>
        {artifacts?.drive_folder_url && (
          <a
            href={artifacts.drive_folder_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-gray-600 hover:text-gray-800"
          >
            Open in Drive
          </a>
        )}
      </div>
    </div>
  );
}
