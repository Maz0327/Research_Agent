/**
 * SourceCard - Displays an individual source with type icon and remove button.
 */

export type SourceType = 'video' | 'text' | 'article' | 'screenshot';

export interface Source {
  id: string;
  type: SourceType;
  label: string;
  detail?: string;
}

interface SourceCardProps {
  source: Source;
  onRemove: (id: string) => void;
}

// Type-specific configuration
const typeConfig: Record<SourceType, { icon: React.ReactNode; color: string; bgColor: string }> = {
  video: {
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30 border-purple-700/50',
  },
  text: {
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    color: 'text-green-400',
    bgColor: 'bg-green-900/30 border-green-700/50',
  },
  article: {
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30 border-blue-700/50',
  },
  screenshot: {
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    color: 'text-amber-400',
    bgColor: 'bg-amber-900/30 border-amber-700/50',
  },
};

export function SourceCard({ source, onRemove }: SourceCardProps) {
  const config = typeConfig[source.type];

  return (
    <div className={`flex items-center gap-3 rounded-lg border p-3 ${config.bgColor}`}>
      {/* Type icon */}
      <div className={`flex-shrink-0 ${config.color}`}>
        {config.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium uppercase ${config.color}`}>
            {source.type}
          </span>
        </div>
        <p className="text-sm text-gray-200 truncate" title={source.label}>
          {source.label}
        </p>
        {source.detail && (
          <p className="text-xs text-gray-500 truncate" title={source.detail}>
            {source.detail}
          </p>
        )}
      </div>

      {/* Remove button */}
      <button
        type="button"
        onClick={() => onRemove(source.id)}
        className="flex-shrink-0 p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-900/20 transition"
        aria-label={`Remove ${source.label}`}
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export default SourceCard;
