/**
 * User settings page.
 */
import { useEffect, useState } from 'react';
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
    // Update local state
    setDriveFolders((prev) => prev.filter((f) => f.folder_id !== folderId));
  };

  const handleSetDefaultFolder = (folderId: string) => {
    setDefaultFolder(folderId);
    // Update local state
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

    // Include username if changed and valid
    if (username && username !== settings?.username) {
      if (usernameCheck?.available || username === settings?.username) {
        updates.username = username;
      }
    }

    // Include drive folders from settings store (managed via addFolder/removeFolder)
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
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-gray-600">Manage your account and research preferences</p>
        </div>

        {/* Success/Error Messages */}
        {saveSuccess && (
          <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4">
            <p className="text-sm text-green-800">Settings saved successfully!</p>
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-red-800">{error}</p>
              <button
                onClick={clearError}
                className="text-red-600 hover:text-red-800"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Account Section */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-900">Account</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Username</label>
              <div className="mt-1 flex gap-2">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                  placeholder="Choose a username"
                  maxLength={30}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                {isCheckingUsername && (
                  <span className="flex items-center text-sm text-gray-500">Checking...</span>
                )}
              </div>
              {username.length >= 3 && usernameCheck && (
                <p className={`mt-1 text-sm ${usernameCheck.available ? 'text-green-600' : 'text-red-600'}`}>
                  {usernameCheck.available ? 'Username available' : usernameCheck.error || 'Username taken'}
                </p>
              )}
              {username.length > 0 && username.length < 3 && (
                <p className="mt-1 text-sm text-gray-500">Username must be at least 3 characters</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <p className="mt-1 text-gray-900">{user?.email || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">User ID</label>
              <p className="mt-1 font-mono text-sm text-gray-500">{user?.id || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Last Sign In</label>
              <p className="mt-1 text-gray-900">
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
        </div>

        {/* Google Drive Output Section */}
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-900">Google Drive Output</h2>
          <p className="mb-4 text-sm text-gray-600">
            Add up to 3 folders where your research documents can be saved. Select a default folder for new jobs.
          </p>

          <div className="space-y-4">
            {/* Existing folders */}
            {settings?.drive_folders && settings.drive_folders.length > 0 && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Your Folders</label>
                {settings.drive_folders.map((folder) => (
                  <div
                    key={folder.folder_id}
                    className={`flex items-center justify-between rounded-lg border p-3 ${
                      folder.is_default ? 'border-blue-200 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="defaultFolder"
                        checked={folder.is_default}
                        onChange={() => handleSetDefaultFolder(folder.folder_id)}
                        className="h-4 w-4 text-blue-600"
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {folder.folder_name || 'Unnamed Folder'}
                          {folder.is_default && (
                            <span className="ml-2 text-xs text-blue-600">(Default)</span>
                          )}
                        </p>
                        <a
                          href={folder.folder_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Open in Drive
                        </a>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveFolder(folder.folder_id)}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
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
                <label className="block text-sm font-medium text-gray-700">
                  Add Folder {settings?.drive_folders?.length ? `(${3 - settings.drive_folders.length} remaining)` : ''}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={folderUrl}
                    onChange={(e) => setFolderUrl(e.target.value)}
                    placeholder="https://drive.google.com/drive/folders/..."
                    className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleValidateFolder}
                    disabled={isValidatingFolder || !folderUrl.trim()}
                    className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isValidatingFolder ? 'Adding...' : 'Add Folder'}
                  </button>
                </div>

                {folderValidation && !folderValidation.valid && (
                  <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
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
        </div>

        {/* Default Pipeline Section */}
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-900">Default Pipeline</h2>
          <p className="mb-4 text-sm text-gray-600">
            When creating new research jobs, use this pipeline by default.
          </p>

          <div className="space-y-4">
            <div>
              <select
                value={defaultPipeline}
                onChange={(e) => setDefaultPipeline(e.target.value as PipelineType)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                className="h-4 w-4 rounded text-blue-600"
              />
              <label htmlFor="autoExtractClaims" className="ml-2 text-sm text-gray-700">
                Auto-extract claims from sources
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Maximum sources per job
              </label>
              <input
                type="number"
                min={5}
                max={50}
                value={maxSources}
                onChange={(e) => setMaxSources(Math.min(50, Math.max(5, parseInt(e.target.value) || 25)))}
                className="mt-1 w-24 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-500">(5-50)</span>
            </div>
          </div>
        </div>

        {/* Notifications Section */}
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-900">Notifications</h2>

          <div className="space-y-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="emailOnComplete"
                checked={emailOnComplete}
                onChange={(e) => setEmailOnComplete(e.target.checked)}
                className="h-4 w-4 rounded text-blue-600"
              />
              <label htmlFor="emailOnComplete" className="ml-2 text-sm text-gray-700">
                Email me when a job completes
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="emailOnFailure"
                checked={emailOnFailure}
                onChange={(e) => setEmailOnFailure(e.target.checked)}
                className="h-4 w-4 rounded text-blue-600"
              />
              <label htmlFor="emailOnFailure" className="ml-2 text-sm text-gray-700">
                Email me when a job fails
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="emailSummary"
                checked={emailSummary}
                onChange={(e) => setEmailSummary(e.target.checked)}
                className="h-4 w-4 rounded text-blue-600"
              />
              <label htmlFor="emailSummary" className="ml-2 text-sm text-gray-700">
                Send daily summary of completed jobs
              </label>
            </div>
          </div>
        </div>

        {/* Display Section */}
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-900">Display</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Jobs per page</label>
              <input
                type="number"
                min={5}
                max={25}
                value={jobsPerPage}
                onChange={(e) => setJobsPerPage(Math.min(25, Math.max(5, parseInt(e.target.value) || 10)))}
                className="mt-1 w-24 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-500">(5-25)</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Default sort</label>
              <select
                value={defaultSort}
                onChange={(e) => setDefaultSort(e.target.value as SortOrder)}
                className="mt-1 w-48 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                className="h-4 w-4 rounded text-blue-600"
              />
              <label htmlFor="showProgressDetails" className="ml-2 text-sm text-gray-700">
                Show detailed progress during jobs
              </label>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-8 flex justify-end gap-4">
          <button
            onClick={() => fetchSettings()}
            disabled={isLoading}
            className="rounded-md border border-gray-300 bg-white px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
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
