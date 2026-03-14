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
    <SettingsSection title="Notifications" delay={0.4} icon={
      <svg className="h-4 w-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    }>
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
