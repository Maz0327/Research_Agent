'use client';

/**
 * SettingsToggleRow — label + optional description + animated toggle switch.
 * Used across settings tabs for boolean preferences.
 */
interface SettingsToggleRowProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

export function SettingsToggleRow({ label, description, checked, onChange }: SettingsToggleRowProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-foreground/80">{label}</p>
        {description && <p className="text-caption text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer flex-shrink-0 ml-4 ${
          checked ? 'bg-accent-blue' : 'bg-border'
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  );
}
