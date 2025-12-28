/**
 * Google Drive output folder settings section.
 * Handles folder validation, addition, and removal.
 */
import SettingsSection from './SettingsSection';
import { DriveFolder } from '../../store/settings';

interface DriveSectionProps {
  driveFolders: DriveFolder[];
  folderUrl: string;
  setFolderUrl: (value: string) => void;
  folderValidation: { valid: boolean; error?: string | null } | null;
  isValidatingFolder: boolean;
  onValidateFolder: () => void;
  onRemoveFolder: (folderId: string) => void;
  onSetDefaultFolder: (folderId: string) => void;
}

export function DriveSection({
  driveFolders,
  folderUrl,
  setFolderUrl,
  folderValidation,
  isValidatingFolder,
  onValidateFolder,
  onRemoveFolder,
  onSetDefaultFolder,
}: DriveSectionProps) {
  return (
    <SettingsSection
      title="Google Drive Output"
      description="Add up to 3 folders where your research documents can be saved. Select a default folder for new jobs."
      delay={0.2}
    >
      <div className="space-y-4">
        {/* Existing folders */}
        {driveFolders && driveFolders.length > 0 && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-400">
              Your Folders
            </label>
            {driveFolders.map((folder) => (
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
                    onChange={() => onSetDefaultFolder(folder.folder_id)}
                    className="h-4 w-4 text-blue-500 bg-gray-800 border-gray-600 focus:ring-blue-500 focus:ring-offset-gray-900"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      {folder.folder_name || 'Unnamed Folder'}
                      {folder.is_default && (
                        <span className="ml-2 text-xs text-blue-400">
                          (Default)
                        </span>
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
                  onClick={() => onRemoveFolder(folder.folder_id)}
                  className="rounded-lg p-2 text-gray-500 hover:bg-gray-700 hover:text-red-400 transition"
                  title="Remove folder"
                >
                  <svg
                    className="h-5 w-5"
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
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add new folder */}
        {(!driveFolders || driveFolders.length < 3) && (
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-400">
              Add Folder{' '}
              {driveFolders?.length
                ? `(${3 - driveFolders.length} remaining)`
                : ''}
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
                onClick={onValidateFolder}
                disabled={isValidatingFolder || !folderUrl.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isValidatingFolder ? (
                  <span className="flex items-center gap-2">
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
              Create a folder in Google Drive and paste the URL here. Make sure
              the folder is shared with our service account.
            </p>
          </div>
        )}

        {driveFolders?.length === 3 && (
          <p className="text-sm text-gray-500">
            Maximum 3 folders reached. Remove a folder to add a new one.
          </p>
        )}
      </div>
    </SettingsSection>
  );
}

export default DriveSection;
