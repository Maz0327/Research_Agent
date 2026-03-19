'use client';

/**
 * Zustand store for managing user settings.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL, UI_TIMING, VALIDATION_LIMITS } from '../lib/constants';

export type PipelineType = 'quick' | 'full' | 'breaking_news' | 'investigation' | 'profile' | 'controversy';
export type SortOrder = 'newest' | 'oldest' | 'status';

export interface DriveFolder {
  folder_id: string;
  folder_name: string | null;
  folder_url: string;
  is_default: boolean;
  added_at: string | null;
}

export interface UserSettings {
  // Profile Settings
  username: string | null;

  // Google Drive Settings - Multi-folder support
  drive_folders: DriveFolder[];
  default_folder_id: string | null;

  // Legacy fields (kept for backwards compatibility)
  drive_folder_id: string | null;
  drive_folder_url: string | null;
  use_custom_folder: boolean;

  // Pipeline Settings
  default_pipeline: PipelineType;
  auto_extract_claims: boolean;
  max_sources: number;

  // Notification Settings
  email_on_complete: boolean;
  email_on_failure: boolean;
  email_summary: boolean;

  // Display Settings
  jobs_per_page: number;
  default_sort: SortOrder;
  show_progress_details: boolean;
}

export interface FolderValidation {
  valid: boolean;
  folder_id: string | null;
  folder_name: string | null;
  accessible: boolean;
  error: string | null;
}

export interface UsernameCheck {
  available: boolean;
  username: string;
  error: string | null;
}

interface SettingsState {
  settings: UserSettings | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  saveSuccess: boolean;
  folderValidation: FolderValidation | null;
  isValidatingFolder: boolean;
  usernameCheck: UsernameCheck | null;
  isCheckingUsername: boolean;

  fetchSettings: () => Promise<void>;
  updateSettings: (updates: Partial<UserSettings>) => Promise<void>;
  validateFolder: (folderUrl: string) => Promise<FolderValidation>;
  checkUsername: (username: string) => Promise<UsernameCheck>;
  addFolder: (folder: FolderValidation) => Promise<void>;
  removeFolder: (folderId: string) => Promise<void>;
  setDefaultFolder: (folderId: string) => Promise<void>;
  clearError: () => void;
  clearSaveSuccess: () => void;
}

// Track saveSuccess timeout to prevent memory leaks
let saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null = null;

// Default settings
const defaultSettings: UserSettings = {
  username: null,
  drive_folders: [],
  default_folder_id: null,
  drive_folder_id: null,
  drive_folder_url: null,
  use_custom_folder: false,
  default_pipeline: 'investigation',
  auto_extract_claims: true,
  max_sources: 25,
  email_on_complete: true,
  email_on_failure: true,
  email_summary: false,
  jobs_per_page: 10,
  default_sort: 'newest',
  show_progress_details: true,
};

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: null,
  isLoading: false,
  isSaving: false,
  error: null,
  saveSuccess: false,
  folderValidation: null,
  isValidatingFolder: false,
  usernameCheck: null,
  isCheckingUsername: false,

  fetchSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      if (!token) {
        set({ settings: defaultSettings, isLoading: false });
        return;
      }

      const response = await fetch(`${API_URL}/settings`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          set({ settings: defaultSettings, isLoading: false });
          return;
        }
        throw new Error('Failed to fetch settings');
      }

      const data = await response.json();
      set({ settings: data, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch settings',
        settings: defaultSettings,
        isLoading: false,
      });
    }
  },

  updateSettings: async (updates: Partial<UserSettings>) => {
    set({ isSaving: true, error: null, saveSuccess: false });
    try {
      const token = await getAccessToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await fetch(`${API_URL}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save settings');
      }

      const data = await response.json();
      set({ settings: data, isSaving: false, saveSuccess: true });

      // Clear any existing timeout to prevent memory leaks
      if (saveSuccessTimeoutId) {
        clearTimeout(saveSuccessTimeoutId);
      }

      // Clear success message after configured duration
      saveSuccessTimeoutId = setTimeout(() => {
        set({ saveSuccess: false });
        saveSuccessTimeoutId = null;
      }, UI_TIMING.TOAST_DURATION);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to save settings',
        isSaving: false,
      });
    }
  },

  validateFolder: async (folderUrl: string) => {
    set({ isValidatingFolder: true, folderValidation: null });
    try {
      const token = await getAccessToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await fetch(`${API_URL}/settings/validate-folder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ folder_url: folderUrl }),
      });

      if (!response.ok) {
        throw new Error('Failed to validate folder');
      }

      const data: FolderValidation = await response.json();
      set({ folderValidation: data, isValidatingFolder: false });
      return data;
    } catch (error) {
      const validation: FolderValidation = {
        valid: false,
        folder_id: null,
        folder_name: null,
        accessible: false,
        error: error instanceof Error ? error.message : 'Failed to validate folder',
      };
      set({ folderValidation: validation, isValidatingFolder: false });
      return validation;
    }
  },

  checkUsername: async (username: string) => {
    set({ isCheckingUsername: true, usernameCheck: null });
    try {
      const token = await getAccessToken();
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await fetch(
        `${API_URL}/settings/check-username?username=${encodeURIComponent(username)}`,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to check username');
      }

      const data: UsernameCheck = await response.json();
      set({ usernameCheck: data, isCheckingUsername: false });
      return data;
    } catch (error) {
      const check: UsernameCheck = {
        available: false,
        username: username,
        error: error instanceof Error ? error.message : 'Failed to check username',
      };
      set({ usernameCheck: check, isCheckingUsername: false });
      return check;
    }
  },

  addFolder: async (folder: FolderValidation) => {
    const { settings, updateSettings } = get();
    if (!settings || !folder.valid || !folder.folder_id) return;

    // Check if we already have maximum folders
    if (settings.drive_folders.length >= VALIDATION_LIMITS.MAX_DRIVE_FOLDERS) {
      set({ error: `Maximum ${VALIDATION_LIMITS.MAX_DRIVE_FOLDERS} folders allowed` });
      return;
    }

    // Check if folder already exists
    if (settings.drive_folders.some((f) => f.folder_id === folder.folder_id)) {
      set({ error: 'Folder already added' });
      return;
    }

    const isFirst = settings.drive_folders.length === 0;
    const newFolder: DriveFolder = {
      folder_id: folder.folder_id,
      folder_name: folder.folder_name,
      folder_url: `https://drive.google.com/drive/folders/${folder.folder_id}`,
      is_default: isFirst, // First folder is default
      added_at: new Date().toISOString(),
    };

    const newFolders = [...settings.drive_folders, newFolder];
    const newDefaultId = isFirst ? folder.folder_id : settings.default_folder_id;

    // Persist to backend
    await updateSettings({
      drive_folders: newFolders,
      default_folder_id: newDefaultId,
    });

    set({ folderValidation: null });
  },

  removeFolder: async (folderId: string) => {
    const { settings, updateSettings } = get();
    if (!settings) return;

    const updatedFolders = settings.drive_folders.filter((f) => f.folder_id !== folderId);

    // If removing the default folder, set the first remaining folder as default
    let newDefaultId = settings.default_folder_id;
    if (settings.default_folder_id === folderId) {
      newDefaultId = updatedFolders[0]?.folder_id || null;
      // Update is_default flags
      updatedFolders.forEach((f) => {
        f.is_default = f.folder_id === newDefaultId;
      });
    }

    // Persist to backend
    await updateSettings({
      drive_folders: updatedFolders,
      default_folder_id: newDefaultId,
    });
  },

  setDefaultFolder: async (folderId: string) => {
    const { settings, updateSettings } = get();
    if (!settings) return;

    const updatedFolders = settings.drive_folders.map((f) => ({
      ...f,
      is_default: f.folder_id === folderId,
    }));

    // Persist to backend
    await updateSettings({
      drive_folders: updatedFolders,
      default_folder_id: folderId,
    });
  },

  clearError: () => set({ error: null }),
  clearSaveSuccess: () => set({ saveSuccess: false }),
}));

// Pipeline display names and descriptions
export const PIPELINE_OPTIONS: { value: PipelineType; label: string; description: string }[] = [
  {
    value: 'quick',
    label: 'Quick',
    description: 'Fast turnaround, fewer sources (5-10 min)',
  },
  {
    value: 'full',
    label: 'Full',
    description: 'Comprehensive research (15-20 min)',
  },
  {
    value: 'breaking_news',
    label: 'Breaking News',
    description: 'Current events, rapid coverage',
  },
  {
    value: 'investigation',
    label: 'Investigation',
    description: 'Deep-dive investigative reporting',
  },
  {
    value: 'profile',
    label: 'Profile',
    description: 'Character-driven biographical research',
  },
  {
    value: 'controversy',
    label: 'Controversy',
    description: 'Balanced multi-perspective analysis',
  },
];

export const SORT_OPTIONS: { value: SortOrder; label: string }[] = [
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
  { value: 'status', label: 'By status' },
];
