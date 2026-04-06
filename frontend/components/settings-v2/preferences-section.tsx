'use client';

/**
 * PreferencesSection — default pipeline, auto-extract claims, max sources, email notifications.
 * Part of the settings-v2 module for App Router.
 */
import { PIPELINE_OPTIONS, PipelineType } from '@/store/settings';

interface PreferencesSectionProps {
  defaultPipeline: PipelineType;
  setDefaultPipeline: (v: PipelineType) => void;
  autoExtractClaims: boolean;
  setAutoExtractClaims: (v: boolean) => void;
  maxSources: number;
  setMaxSources: (v: number) => void;
  emailOnComplete: boolean;
  setEmailOnComplete: (v: boolean) => void;
  emailOnFailure: boolean;
  setEmailOnFailure: (v: boolean) => void;
}

export function PreferencesSection({
  defaultPipeline,
  setDefaultPipeline,
  autoExtractClaims,
  setAutoExtractClaims,
  maxSources,
  setMaxSources,
  emailOnComplete,
  setEmailOnComplete,
  emailOnFailure,
  setEmailOnFailure,
}: PreferencesSectionProps) {
  const selectedPipeline = PIPELINE_OPTIONS.find((o) => o.value === defaultPipeline);

  const handleMaxSources = (value: string) => {
    const num = parseInt(value) || 25;
    setMaxSources(Math.min(50, Math.max(5, num)));
  };

  return (
    <div className="rounded-xl border border-border bg-background p-6">
      <div className="flex items-center gap-2 mb-4">
        <svg className="h-4 w-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <h2 className="text-lg font-semibold text-foreground">Preferences</h2>
      </div>

      <div className="space-y-5">
        {/* Default pipeline */}
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1.5">Default Pipeline</label>
          <select
            value={defaultPipeline}
            onChange={(e) => setDefaultPipeline(e.target.value as PipelineType)}
            className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-sm text-foreground transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {PIPELINE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {selectedPipeline && (
            <p className="mt-1.5 text-sm text-muted-foreground/70">{selectedPipeline.description}</p>
          )}
        </div>

        {/* Max sources */}
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1.5">Maximum sources per job</label>
          <div className="flex items-center gap-3">
            <input
              type="number"
              min={5}
              max={50}
              value={maxSources}
              onChange={(e) => handleMaxSources(e.target.value)}
              className="w-24 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <span className="text-sm text-muted-foreground/70">(5–50)</span>
          </div>
        </div>

        {/* Toggles */}
        <div className="space-y-3 pt-1">
          <Toggle
            id="autoExtract"
            checked={autoExtractClaims}
            onChange={setAutoExtractClaims}
            label="Auto-extract claims from sources"
          />
          <Toggle
            id="emailComplete"
            checked={emailOnComplete}
            onChange={setEmailOnComplete}
            label="Email me when a job completes"
          />
          <Toggle
            id="emailFailure"
            checked={emailOnFailure}
            onChange={setEmailOnFailure}
            label="Email me when a job fails"
          />
        </div>
      </div>
    </div>
  );
}

function Toggle({
  id,
  checked,
  onChange,
  label,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        type="checkbox"
        id={id}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded bg-card border-border text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
      />
      <label htmlFor={id} className="text-sm text-muted-foreground cursor-pointer">{label}</label>
    </div>
  );
}
