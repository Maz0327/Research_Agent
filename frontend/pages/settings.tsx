/**
 * User settings page with dark mode design.
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import {
  useSettingsStore,
  PIPELINE_OPTIONS,
  SORT_OPTIONS,
  PipelineType,
  SortOrder,
  DriveFolder,
} from '../store/settings';

// Skeleton loader for settings sections
function SettingsSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="rounded-xl border border-gray-800 bg-gray-900 p-6 animate-pulse">
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
  const [defaultPipeline, setDefaultPipeline] = useState<PipelineType>('investigation');
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
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Settings
          </h1>
          <p className="mt-2 text-gray-400">Manage your account and research preferences</p>
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
                <svg className="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm text-green-300">Settings saved successfully!</p>
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
                  <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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

        {/* Account Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-100">Account</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400">Username</label>
              <div className="mt-1.5 flex gap-2">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                  placeholder="Choose a username"
                  maxLength={30}
                  className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                {isCheckingUsername && (
                  <span className="flex items-center text-sm text-gray-500">
                    <svg className="animate-spin h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Checking...
                  </span>
                )}
              </div>
              {username.length >= 3 && usernameCheck && (
                <p className={`mt-1.5 text-sm ${usernameCheck.available ? 'text-green-400' : 'text-red-400'}`}>
                  {usernameCheck.available ? 'Username available' : usernameCheck.error || 'Username taken'}
                </p>
              )}
              {username.length > 0 && username.length < 3 && (
                <p className="mt-1.5 text-sm text-gray-500">Username must be at least 3 characters</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400">Email</label>
              <p className="mt-1 text-gray-200">{user?.email || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400">User ID</label>
              <p className="mt-1 font-mono text-sm text-gray-500">{user?.id || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400">Last Sign In</label>
              <p className="mt-1 text-gray-200">
                {user?.last_sign_in_at
                  ? new Date(user.last_sign_in_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Unknown'}
              </p>
            </div>
          </div>
        </motion.div>

        {/* Google Drive Output Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-100">Google Drive Output</h2>
          <p className="mb-4 text-sm text-gray-400">
            Add up to 3 folders where your research documents can be saved. Select a default folder for new jobs.
          </p>

          <div className="space-y-4">
            {/* Existing folders */}
            {settings?.drive_folders && settings.drive_folders.length > 0 && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-400">Your Folders</label>
                {settings.drive_folders.map((folder) => (
                  <div
                    key={folder.folder_id}
                    className={`flex items-center justify-between rounded-lg border p-3 transition-all ${
                      folder.is_default
                        ? 'border-blue-500/50 bg-blue-900/20'
                        : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="defaultFolder"
                        checked={folder.is_default}
                        onChange={() => handleSetDefaultFolder(folder.folder_id)}
                        className="h-4 w-4 text-blue-500 bg-gray-800 border-gray-600 focus:ring-blue-500 focus:ring-offset-gray-900"
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-200">
                          {folder.folder_name || 'Unnamed Folder'}
                          {folder.is_default && (
                            <span className="ml-2 text-xs text-blue-400">(Default)</span>
                          )}
                        </p>
                        <a
                          href={folder.folder_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-400 hover:text-blue-300 transition"
                        >
                          Open in Drive
                        </a>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveFolder(folder.folder_id)}
                      className="rounded-lg p-2 text-gray-500 hover:bg-gray-700 hover:text-red-400 transition"
                      title="Remove folder"
                    >
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add new folder */}
            {(!settings?.drive_folders || settings.drive_folders.length < 3) && (
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-400">
                  Add Folder {settings?.drive_folders?.length ? `(${3 - settings.drive_folders.length} remaining)` : ''}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={folderUrl}
                    onChange={(e) => setFolderUrl(e.target.value)}
                    placeholder="https://drive.google.com/drive/folders/..."
                    className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleValidateFolder}
                    disabled={isValidatingFolder || !folderUrl.trim()}
                    className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isValidatingFolder ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Adding...
                      </span>
                    ) : (
                      'Add Folder'
                    )}
                  </button>
                </div>

                {folderValidation && !folderValidation.valid && (
                  <div className="rounded-lg border border-red-500/30 bg-red-900/30 p-3 text-sm text-red-300">
                    {folderValidation.error}
                  </div>
                )}

                <p className="text-xs text-gray-500">
                  Create a folder in Google Drive and paste the URL here. Make sure the folder is
                  shared with our service account.
                </p>
              </div>
            )}

            {settings?.drive_folders?.length === 3 && (
              <p className="text-sm text-gray-500">Maximum 3 folders reached. Remove a folder to add a new one.</p>
            )}
          </div>
        </motion.div>

        {/* Default Pipeline Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-100">Default Pipeline</h2>
          <p className="mb-4 text-sm text-gray-400">
            When creating new research jobs, use this pipeline by default.
          </p>

          <div className="space-y-4">
            <div>
              <select
                value={defaultPipeline}
                onChange={(e) => setDefaultPipeline(e.target.value as PipelineType)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {PIPELINE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-sm text-gray-500">
                {PIPELINE_OPTIONS.find((o) => o.value === defaultPipeline)?.description}
              </p>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="autoExtractClaims"
                checked={autoExtractClaims}
                onChange={(e) => setAutoExtractClaims(e.target.checked)}
                className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <label htmlFor="autoExtractClaims" className="ml-3 text-sm text-gray-300">
                Auto-extract claims from sources
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400">
                Maximum sources per job
              </label>
              <div className="mt-1.5 flex items-center gap-3">
                <input
                  type="number"
                  min={5}
                  max={50}
                  value={maxSources}
                  onChange={(e) => setMaxSources(Math.min(50, Math.max(5, parseInt(e.target.value) || 25)))}
                  className="w-24 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-500">(5-50)</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Notifications Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-100">Notifications</h2>

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
        </motion.div>

        {/* Display Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-100">Display</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400">Jobs per page</label>
              <div className="mt-1.5 flex items-center gap-3">
                <input
                  type="number"
                  min={5}
                  max={25}
                  value={jobsPerPage}
                  onChange={(e) => setJobsPerPage(Math.min(25, Math.max(5, parseInt(e.target.value) || 10)))}
                  className="w-24 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-500">(5-25)</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400">Default sort</label>
              <select
                value={defaultSort}
                onChange={(e) => setDefaultSort(e.target.value as SortOrder)}
                className="mt-1.5 w-48 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="showProgressDetails"
                checked={showProgressDetails}
                onChange={(e) => setShowProgressDetails(e.target.checked)}
                className="h-4 w-4 rounded bg-gray-800 border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
              />
              <label htmlFor="showProgressDetails" className="ml-3 text-sm text-gray-300">
                Show detailed progress during jobs
              </label>
            </div>
          </div>
        </motion.div>

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
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
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
