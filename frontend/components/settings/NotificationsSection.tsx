/**
 * Email notification settings section.
 * Controls when users receive email notifications.
 */
import SettingsSection from './SettingsSection';

interface NotificationsSectionProps {
  emailOnComplete: boolean;
  setEmailOnComplete: (value: boolean) => void;
  emailOnFailure: boolean;
  setEmailOnFailure: (value: boolean) => void;
  emailSummary: boolean;
  setEmailSummary: (value: boolean) => void;
}

export function NotificationsSection({
  emailOnComplete,
  setEmailOnComplete,
  emailOnFailure,
  setEmailOnFailure,
  emailSummary,
  setEmailSummary,
}: NotificationsSectionProps) {
  return (
    <SettingsSection title="Notifications" delay={0.4}>
      <div className="space-y-3">
        <div className="flex items-center">
          <input
            type="checkbox"
            id="emailOnComplete"
            checked={emailOnComplete}
            onChange={(e) => setEmailOnComplete(e.target.checked)}
            className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <label htmlFor="emailOnComplete" className="ml-3 text-sm text-gray-300">
            Email me when a job completes
          </label>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="emailOnFailure"
            checked={emailOnFailure}
            onChange={(e) => setEmailOnFailure(e.target.checked)}
            className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <label htmlFor="emailOnFailure" className="ml-3 text-sm text-gray-300">
            Email me when a job fails
          </label>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="emailSummary"
            checked={emailSummary}
            onChange={(e) => setEmailSummary(e.target.checked)}
            className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
          />
          <label htmlFor="emailSummary" className="ml-3 text-sm text-gray-300">
            Send daily summary of completed jobs
          </label>
        </div>
      </div>
    </SettingsSection>
  );
}

export default NotificationsSection;
