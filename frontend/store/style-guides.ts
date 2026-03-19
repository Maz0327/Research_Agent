'use client';

/**
 * Zustand store for managing personal creator style guides.
 *
 * Handles CRUD operations + template fetching via the /style-guides API.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface StyleGuideOverrides {
  voice?: string;
  audience?: string;
  vocabulary_use?: string[];
  vocabulary_avoid?: string[];
  structure?: string;
  hook_style?: string;
  inspirations?: string[];
}

export interface SectionPreference {
  section_key: string;
  enabled: boolean;
  order: number;
}

export interface StyleGuide {
  id: string;
  name: string;
  template_base: string;
  overrides: StyleGuideOverrides;
  section_preferences: SectionPreference[];
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TemplateInfo {
  name: string;
  description: string;
  creator_references: string;
  voice: string;
  audience: string;
  vocabulary_use: string[];
  vocabulary_avoid: string[];
  structure: string;
  hook_style: string;
  example_tone: string;
}

export interface StyleGuideCreateData {
  name: string;
  template_base: string;
  overrides?: StyleGuideOverrides;
  section_preferences?: SectionPreference[];
  is_default?: boolean;
}

export interface StyleGuideUpdateData {
  name?: string;
  template_base?: string;
  overrides?: StyleGuideOverrides;
  section_preferences?: SectionPreference[];
  is_default?: boolean;
}

// ─── Store ───────────────────────────────────────────────────────────────────

interface StyleGuideStore {
  // State
  guides: StyleGuide[];
  templates: Record<string, TemplateInfo>;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchGuides: () => Promise<void>;
  fetchTemplates: () => Promise<void>;
  createGuide: (data: StyleGuideCreateData) => Promise<StyleGuide | null>;
  updateGuide: (id: string, data: StyleGuideUpdateData) => Promise<StyleGuide | null>;
  deleteGuide: (id: string) => Promise<boolean>;
  setDefault: (id: string) => Promise<void>;
  getDefaultGuide: () => StyleGuide | undefined;
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export const useStyleGuideStore = create<StyleGuideStore>((set, get) => ({
  guides: [],
  templates: {},
  isLoading: false,
  error: null,

  fetchGuides: async () => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const res = await fetch(`${API_URL}/style-guides`, { headers });
      if (!res.ok) throw new Error(`Failed to fetch style guides: ${res.status}`);
      const guides = await res.json();
      set({ guides, isLoading: false });
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },

  fetchTemplates: async () => {
    try {
      const res = await fetch(`${API_URL}/style-guides/templates`);
      if (!res.ok) throw new Error(`Failed to fetch templates: ${res.status}`);
      const data = await res.json();
      set({ templates: data.templates });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  createGuide: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const res = await fetch(`${API_URL}/style-guides`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to create: ${res.status}`);
      }
      const guide = await res.json();
      // Refresh full list to get updated is_default states
      await get().fetchGuides();
      return guide;
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
      return null;
    }
  },

  updateGuide: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const res = await fetch(`${API_URL}/style-guides/${id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to update: ${res.status}`);
      }
      const guide = await res.json();
      await get().fetchGuides();
      return guide;
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
      return null;
    }
  },

  deleteGuide: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const res = await fetch(`${API_URL}/style-guides/${id}`, {
        method: 'DELETE',
        headers,
      });
      if (!res.ok) throw new Error(`Failed to delete: ${res.status}`);
      await get().fetchGuides();
      return true;
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
      return false;
    }
  },

  setDefault: async (id) => {
    await get().updateGuide(id, { is_default: true });
  },

  getDefaultGuide: () => {
    return get().guides.find(g => g.is_default);
  },
}));
