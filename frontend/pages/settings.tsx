/**
 * User settings page with dark mode design.
 * Modularized into separate section components.
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import {
  AccountSection,
  DisplaySection,
  NotificationsSection,
  PipelineSection,
} from '../components/settings';
import {
  useSettingsStore,
  PipelineType,
  SortOrder,
  DriveFolder,
} from '../store/settings';

function SettingsSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-gray-800 bg-gray-900 p-6 animate-pulse"
        >
          <div className="h-6 w-32 rounded bg-gray-800 mb-4" />
          <div className="space-y-3">
            <div className="h-10 rounded bg-gray-800" />
            <div className="h-10 w-2/3 rounded bg-gray-800" />
          </div>
        </div>
      ))}
    </div>
  );
}

function SettingsContent() {
  const { user } = useAuth();
  const {
    settings,
    isLoading,
    isSaving,
    error,
    saveSuccess,
    folderValidation,
    isValidatingFolder,
    usernameCheck,
    isCheckingUsername,
    fetchSettings,
    updateSettings,
    validateFolder,
    checkUsername,
    addFolder,
    removeFolder,
    setDefaultFolder,
    clearError,
  } = useSettingsStore();

  // Local form state
  const [username, setUsername] = useState('');
  const [folderUrl, setFolderUrl] = useState('');
  const [driveFolders, setDriveFolders] = useState<DriveFolder[]>([]);
  const [defaultPipeline, setDefaultPipeline] =
    useState<PipelineType>('investigation');
  const [autoExtractClaims, setAutoExtractClaims] = useState(true);
  const [maxSources, setMaxSources] = useState(25);
  const [emailOnComplete, setEmailOnComplete] = useState(true);
  const [emailOnFailure, setEmailOnFailure] = useState(true);
  const [emailSummary, setEmailSummary] = useState(false);
  const [jobsPerPage, setJobsPerPage] = useState(10);
  const [defaultSort, setDefaultSort] = useState<SortOrder>('newest');
  const [showProgressDetails, setShowProgressDetails] = useState(true);

  // Load settings on mount
  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // Sync local state with loaded settings
  useEffect(() => {
    if (settings) {
      setUsername(settings.username || '');
      setDriveFolders(settings.drive_folders || []);
      setDefaultPipeline(settings.default_pipeline);
      setAutoExtractClaims(settings.auto_extract_claims);
      setMaxSources(settings.max_sources);
      setEmailOnComplete(settings.email_on_complete);
      setEmailOnFailure(settings.email_on_failure);
      setEmailSummary(settings.email_summary);
      setJobsPerPage(settings.jobs_per_page);
      setDefaultSort(settings.default_sort);
      setShowProgressDetails(settings.show_progress_details);
    }
  }, [settings]);

  // Debounced username check
  useEffect(() => {
    if (username.length >= 3 && username !== settings?.username) {
      const timer = setTimeout(() => {
        checkUsername(username);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [username, settings?.username, checkUsername]);

  const handleValidateFolder = async () => {
    if (!folderUrl.trim()) return;
    const result = await validateFolder(folderUrl.trim());
    if (result.valid) {
      addFolder(result);
      setFolderUrl('');
    }
  };

  const handleRemoveFolder = (folderId: string) => {
    removeFolder(folderId);
    setDriveFolders((prev) => prev.filter((f) => f.folder_id !== folderId));
  };

  const handleSetDefaultFolder = (folderId: string) => {
    setDefaultFolder(folderId);
    setDriveFolders((prev) =>
      prev.map((f) => ({ ...f, is_default: f.folder_id === folderId }))
    );
  };

  const handleSave = async () => {
    const updates: Record<string, unknown> = {
      default_pipeline: defaultPipeline,
      auto_extract_claims: autoExtractClaims,
      max_sources: maxSources,
      email_on_complete: emailOnComplete,
      email_on_failure: emailOnFailure,
      email_summary: emailSummary,
      jobs_per_page: jobsPerPage,
      default_sort: defaultSort,
      show_progress_details: showProgressDetails,
    };

    if (username && username !== settings?.username) {
      if (usernameCheck?.available || username === settings?.username) {
        updates.username = username;
      }
    }

    if (settings?.drive_folders) {
      updates.drive_folders = settings.drive_folders.map((f) => ({
        folder_id: f.folder_id,
        folder_name: f.folder_name,
        is_default: f.is_default,
        added_at: f.added_at,
      }));
      updates.default_folder_id = settings.default_folder_id;
    }

    await updateSettings(updates);
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="mx-auto max-w-3xl">
          <div className="mb-8">
            <div className="h-8 w-32 rounded bg-gray-800 animate-pulse" />
            <div className="mt-2 h-5 w-64 rounded bg-gray-800 animate-pulse" />
          </div>
          <SettingsSkeleton />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Settings
          </h1>
          <p className="mt-2 text-gray-400">
            Manage your account and research preferences
          </p>
        </motion.div>

        {/* Success Message */}
        {saveSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="mb-6 rounded-xl border border-green-500/30 bg-green-900/30 p-4"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500/20">
                <svg
                  className="h-5 w-5 text-green-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <p className="text-sm text-green-300">
                Settings saved successfully!
              </p>
            </div>
          </motion.div>
        )}

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className="mb-6 rounded-xl border border-red-500/30 bg-red-900/30 p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500/20">
                  <svg
                    className="h-5 w-5 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </div>
                <p className="text-sm text-red-300">{error}</p>
              </div>
              <button
                onClick={clearError}
                className="rounded-lg p-1 text-red-400 hover:bg-red-900/50 transition"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </motion.div>
        )}

        {/* Settings Sections */}
        <div className="space-y-6">
          <AccountSection
            user={user}
            username={username}
            setUsername={setUsername}
            isCheckingUsername={isCheckingUsername}
            usernameCheck={usernameCheck}
            currentUsername={settings?.username}
          />

          <PipelineSection
            defaultPipeline={defaultPipeline}
            setDefaultPipeline={setDefaultPipeline}
            autoExtractClaims={autoExtractClaims}
            setAutoExtractClaims={setAutoExtractClaims}
            maxSources={maxSources}
            setMaxSources={setMaxSources}
          />

          <NotificationsSection
            emailOnComplete={emailOnComplete}
            setEmailOnComplete={setEmailOnComplete}
            emailOnFailure={emailOnFailure}
            setEmailOnFailure={setEmailOnFailure}
            emailSummary={emailSummary}
            setEmailSummary={setEmailSummary}
          />

          <DisplaySection
            jobsPerPage={jobsPerPage}
            setJobsPerPage={setJobsPerPage}
            defaultSort={defaultSort}
            setDefaultSort={setDefaultSort}
            showProgressDetails={showProgressDetails}
            setShowProgressDetails={setShowProgressDetails}
          />
        </div>

        {/* Save Button */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-8 flex justify-end gap-4"
        >
          <button
            onClick={() => fetchSettings()}
            disabled={isLoading}
            className="rounded-lg border border-gray-700 bg-gray-800 px-6 py-2.5 text-sm font-medium text-gray-300 transition hover:bg-gray-700 hover:text-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {isSaving ? (
              <>
                <svg
                  className="animate-spin h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        </motion.div>
      </div>
    </Layout>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  );
}
