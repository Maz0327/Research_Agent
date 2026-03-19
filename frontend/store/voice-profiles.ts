'use client';

/**
 * Voice Profiles Zustand store — follows style-guides.ts pattern.
 * CRUD operations for voice profiles used in script generation.
 */

import { create } from 'zustand';
import { API_URL } from '@/lib/constants';
import { getAccessToken } from '@/lib/supabase';

export interface VoiceProfile {
  id: string;
  user_id: string;
  creator_name: string;
  style_profile: Record<string, unknown>;
  sentence_rhythm: Record<string, unknown>;
  transition_patterns: { from_context: string; phrase: string; frequency: string }[];
  opening_patterns: string[];
  closing_patterns: string[];
  emphasis_patterns: Record<string, unknown>;
  source_video_urls: string[];
  source_video_count: number;
  created_at: string;
  updated_at: string;
}

interface VoiceProfileStore {
  profiles: VoiceProfile[];
  isLoading: boolean;
  error: string | null;

  fetchProfiles: () => Promise<void>;
  createProfile: (creatorName: string, videoUrls: string[]) => Promise<{ id: string } | null>;
  deleteProfile: (id: string) => Promise<boolean>;
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export const useVoiceProfileStore = create<VoiceProfileStore>((set) => ({
  profiles: [],
  isLoading: false,
  error: null,

  fetchProfiles: async () => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const response = await fetch(`${API_URL}/voice-profiles`, { headers });
      if (!response.ok) throw new Error('Failed to fetch voice profiles');
      const data = await response.json();
      set({ profiles: data.profiles || [], isLoading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', isLoading: false });
    }
  },

  createProfile: async (creatorName: string, videoUrls: string[]) => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const response = await fetch(`${API_URL}/voice-profiles`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ creator_name: creatorName, video_urls: videoUrls }),
      });
      if (!response.ok) throw new Error('Failed to create voice profile');
      const data = await response.json();

      // Refresh full list
      const listResponse = await fetch(`${API_URL}/voice-profiles`, { headers });
      if (listResponse.ok) {
        const listData = await listResponse.json();
        set({ profiles: listData.profiles || [], isLoading: false });
      } else {
        set({ isLoading: false });
      }

      return data;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', isLoading: false });
      return null;
    }
  },

  deleteProfile: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = await authHeaders();
      const response = await fetch(`${API_URL}/voice-profiles/${id}`, {
        method: 'DELETE',
        headers,
      });
      if (!response.ok) throw new Error('Failed to delete voice profile');

      // Refresh full list
      const listResponse = await fetch(`${API_URL}/voice-profiles`, { headers });
      if (listResponse.ok) {
        const listData = await listResponse.json();
        set({ profiles: listData.profiles || [], isLoading: false });
      } else {
        set({ isLoading: false });
      }

      return true;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', isLoading: false });
      return false;
    }
  },
}));
