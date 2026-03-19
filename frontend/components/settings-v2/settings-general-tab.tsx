'use client';

/**
 * SettingsGeneralTab — Profile, Research Defaults, and Preferences sections.
 * Matches the General tab in the 07-settings.html mockup.
 */
import { PIPELINE_OPTIONS, PipelineType } from '@/store/settings';
import { SettingsToggleRow } from './settings-toggle-row';

interface SettingsGeneralTabProps {
  userEmail: string | null;
  username: string;
  setUsername: (v: string) => void;
  usernameCheck: { available: boolean; error?: string | null } | null;
  isCheckingUsername: boolean;
  defaultPipeline: PipelineType;
  setDefaultPipeline: (v: PipelineType) => void;
  maxSources: number;
  setMaxSources: (v: number) => void;
  autoExtractClaims: boolean;
  setAutoExtractClaims: (v: boolean) => void;
  emailOnComplete: boolean;
  setEmailOnComplete: (v: boolean) => void;
  emailOnFailure: boolean;
  setEmailOnFailure: (v: boolean) => void;
  autoProducerPacket: boolean;
  setAutoProducerPacket: (v: boolean) => void;
  isSaving: boolean;
  onSave: () => void;
}

export function SettingsGeneralTab({
  userEmail,
  username,
  setUsername,
  usernameCheck,
  isCheckingUsername,
  defaultPipeline,
  setDefaultPipeline,
  maxSources,
  setMaxSources,
  autoExtractClaims,
  setAutoExtractClaims,
  emailOnComplete,
  setEmailOnComplete,
  emailOnFailure,
  setEmailOnFailure,
  autoProducerPacket,
  setAutoProducerPacket,
  isSaving,
  onSave,
}: SettingsGeneralTabProps) {
  return (
    <div className="space-y-6">
      {/* Profile */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-4">Profile</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Display Name</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
              placeholder="Choose a username"
              className="w-full bg-secondary text-sm rounded-lg px-3 py-2 border border-border focus:border-accent-blue focus:outline-none transition-colors"
            />
            {username.length >= 3 && usernameCheck && !isCheckingUsername && (
              <p className={`mt-1 text-xs ${usernameCheck.available ? 'text-accent-green' : 'text-destructive'}`}>
                {usernameCheck.available ? 'Username available' : usernameCheck.error || 'Username taken'}
              </p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Email</label>
            <input
              type="email"
              value={userEmail ?? ''}
              disabled
              className="w-full bg-secondary text-sm rounded-lg px-3 py-2 border border-border text-muted-foreground cursor-not-allowed"
            />
          </div>
        </div>
      </div>

      {/* Research Defaults */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-4">Research Defaults</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Default Research Mode</label>
            <select
              value={defaultPipeline}
              onChange={(e) => setDefaultPipeline(e.target.value as PipelineType)}
              className="w-full bg-secondary text-sm rounded-lg px-3 py-2 border border-border focus:border-accent-blue focus:outline-none cursor-pointer"
            >
              {PIPELINE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Max Sources per Job</label>
            <input
              type="number"
              min={5}
              max={50}
              value={maxSources}
              onChange={(e) => setMaxSources(Math.min(50, Math.max(5, parseInt(e.target.value) || 25)))}
              className="w-full bg-secondary text-sm rounded-lg px-3 py-2 border border-border focus:border-accent-blue focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Preferences toggles */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-4">Preferences</h2>
        <div className="space-y-4">
          <SettingsToggleRow
            label="Auto-extract claims from sources"
            description="Automatically extract key claims during research"
            checked={autoExtractClaims}
            onChange={setAutoExtractClaims}
          />
          <SettingsToggleRow
            label="Email notifications"
            description="Get notified when jobs complete"
            checked={emailOnComplete}
            onChange={setEmailOnComplete}
          />
          <SettingsToggleRow
            label="Email on failure"
            description="Get notified when a job fails"
            checked={emailOnFailure}
            onChange={setEmailOnFailure}
          />
          <SettingsToggleRow
            label="Auto-generate Producer Packet"
            description="Requires 4+ sources, 1+ HIGH source"
            checked={autoProducerPacket}
            onChange={setAutoProducerPacket}
          />
        </div>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        <button
          onClick={onSave}
          disabled={isSaving}
          className="px-5 py-2 rounded-lg bg-accent-blue hover:bg-accent-blue/90 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
}
