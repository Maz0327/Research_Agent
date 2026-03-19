'use client';

/**
 * Local UI preferences store with localStorage persistence.
 * These preferences are client-side only and don't sync with backend.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type JobListView = 'card' | 'table';

export interface UIPreferences {
  // Dashboard preferences
  createPanelCollapsed: boolean;
  jobListView: JobListView;
}

interface UIPreferencesState extends UIPreferences {
  setCreatePanelCollapsed: (collapsed: boolean) => void;
  toggleCreatePanel: () => void;
  setJobListView: (view: JobListView) => void;
}

const defaultPreferences: UIPreferences = {
  // ADHD-friendly: Panel collapsed by default so users see their jobs first
  createPanelCollapsed: true,
  jobListView: 'card',
};

export const useUIPreferences = create<UIPreferencesState>()(
  persist(
    (set) => ({
      ...defaultPreferences,

      setCreatePanelCollapsed: (collapsed) => set({ createPanelCollapsed: collapsed }),
      toggleCreatePanel: () => set((state) => ({ createPanelCollapsed: !state.createPanelCollapsed })),
      setJobListView: (view) => set({ jobListView: view }),
    }),
    {
      name: 'research-agent-ui-preferences',
      partialize: (state) => ({
        createPanelCollapsed: state.createPanelCollapsed,
        jobListView: state.jobListView,
      }),
    }
  )
);
