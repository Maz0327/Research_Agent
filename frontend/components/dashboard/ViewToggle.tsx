/**
 * ViewToggle - Toggle between card and table view for job list.
 */
import { JobListView } from '../../store/ui-preferences';

interface ViewToggleProps {
  view: JobListView;
  onChange: (view: JobListView) => void;
}

export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="flex items-center gap-1 bg-card rounded-lg p-1">
      <button
        onClick={() => onChange('card')}
        className={`p-1.5 sm:p-2 rounded-md transition-all touch-manipulation ${
          view === 'card'
            ? 'bg-muted text-blue-400'
            : 'text-muted-foreground/70 hover:text-muted-foreground'
        }`}
        title="Card view"
        aria-label="Card view"
        aria-pressed={view === 'card'}
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
          />
        </svg>
      </button>
      <button
        onClick={() => onChange('table')}
        className={`p-1.5 sm:p-2 rounded-md transition-all touch-manipulation ${
          view === 'table'
            ? 'bg-muted text-blue-400'
            : 'text-muted-foreground/70 hover:text-muted-foreground'
        }`}
        title="Table view"
        aria-label="Table view"
        aria-pressed={view === 'table'}
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 10h16M4 14h16M4 18h16"
          />
        </svg>
      </button>
    </div>
  );
}

export default ViewToggle;
