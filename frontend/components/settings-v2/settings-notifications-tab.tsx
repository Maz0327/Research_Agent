'use client';

/**
 * SettingsNotificationsTab — notification preferences panel.
 * Toggles: Job Completed, Job Failed, Weekly Digest, Pipeline Alerts.
 * Method selector: Email | In-App | Both.
 */
import { useState } from 'react';
import { SettingsToggleRow } from './settings-toggle-row';

type NotifMethod = 'email' | 'in-app' | 'both';

const METHODS: { id: NotifMethod; label: string }[] = [
  { id: 'email', label: 'Email' },
  { id: 'in-app', label: 'In-App' },
  { id: 'both', label: 'Both' },
];

interface SettingsNotificationsTabProps {
  /** Whether a save operation is in progress */
  isSaving: boolean;
  /** Persist handler called with current toggle values */
  onSave: (prefs: NotificationPrefs) => void;
  /** Initial values (optional — defaults to all on, method 'both') */
  initialPrefs?: Partial<NotificationPrefs>;
}

export interface NotificationPrefs {
  jobCompleted: boolean;
  jobFailed: boolean;
  weeklyDigest: boolean;
  pipelineAlerts: boolean;
  method: NotifMethod;
}

export function SettingsNotificationsTab({
  isSaving,
  onSave,
  initialPrefs = {},
}: SettingsNotificationsTabProps) {
  const [jobCompleted, setJobCompleted] = useState(initialPrefs.jobCompleted ?? true);
  const [jobFailed, setJobFailed] = useState(initialPrefs.jobFailed ?? true);
  const [weeklyDigest, setWeeklyDigest] = useState(initialPrefs.weeklyDigest ?? false);
  const [pipelineAlerts, setPipelineAlerts] = useState(initialPrefs.pipelineAlerts ?? false);
  const [method, setMethod] = useState<NotifMethod>(initialPrefs.method ?? 'both');

  const handleSave = () => {
    onSave({ jobCompleted, jobFailed, weeklyDigest, pipelineAlerts, method });
  };

  return (
    <div className="space-y-4">
      {/* Toggle section */}
      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-foreground">Notification Events</h2>

        <SettingsToggleRow
          label="Job Completed"
          description="Get notified when a research job finishes"
          checked={jobCompleted}
          onChange={setJobCompleted}
        />

        <SettingsToggleRow
          label="Job Failed"
          description="Get notified when a job encounters an error"
          checked={jobFailed}
          onChange={setJobFailed}
        />

        <SettingsToggleRow
          label="Weekly Digest"
          description="Receive a weekly summary of your research activity"
          checked={weeklyDigest}
          onChange={setWeeklyDigest}
        />

        <SettingsToggleRow
          label="Pipeline Alerts"
          description="Get notified about pipeline warnings and retries"
          checked={pipelineAlerts}
          onChange={setPipelineAlerts}
        />
      </div>

      {/* Method selector */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-foreground mb-3">Notification Method</h2>
        <div className="flex items-center gap-3">
          {METHODS.map((m) => (
            <button
              key={m.id}
              onClick={() => setMethod(m.id)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors cursor-pointer ${
                method === m.id
                  ? 'bg-accent-blue text-white border-accent-blue'
                  : 'bg-transparent text-muted-foreground border-border hover:border-accent-blue/50 hover:text-foreground'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-caption text-muted-foreground">
          Choose how you want to receive notifications
        </p>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-5 py-2 rounded-lg bg-accent-blue hover:bg-accent-blue/90 text-white text-sm font-medium transition-colors disabled:opacity-50 cursor-pointer"
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
}
