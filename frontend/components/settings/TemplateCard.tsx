/**
 * TemplateCard — Displays a style guide template option.
 *
 * Shows template name, description, creator references, and example tone.
 * Supports selected state with colored border and checkmark.
 */

interface TemplateCardProps {
  templateKey: string;
  name: string;
  description: string;
  creatorReferences: string;
  exampleTone: string;
  isSelected: boolean;
  onSelect: (key: string) => void;
}

export function TemplateCard({
  templateKey,
  name,
  description,
  creatorReferences,
  exampleTone,
  isSelected,
  onSelect,
}: TemplateCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(templateKey)}
      className={`
        w-full text-left rounded-lg border p-4 transition-all duration-200
        ${isSelected
          ? 'border-blue-500/60 ring-1 ring-blue-500/30 bg-blue-900/10'
          : 'border-border/50 bg-card/40 hover:border-border/60 hover:bg-card/60'
        }
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-body-lg font-semibold text-foreground">{name}</h3>
          <p className="text-body-sm text-muted-foreground mt-0.5">{description}</p>
          <p className="text-caption text-muted-foreground/60 mt-1">{creatorReferences}</p>
        </div>
        {isSelected && (
          <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center mt-0.5">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      {/* Example tone preview */}
      <div className="mt-3 pt-3 border-t border-border/30">
        <p className="text-caption text-muted-foreground/60 uppercase tracking-wider mb-1">Example tone</p>
        <p className="text-body-sm text-muted-foreground italic leading-relaxed line-clamp-2">
          &ldquo;{exampleTone}&rdquo;
        </p>
      </div>
    </button>
  );
}
