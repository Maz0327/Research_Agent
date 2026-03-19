'use client';

/**
 * SettingsContent — tab shell for settings page.
 * Tabs: General | Usage & Billing | API Keys | Notifications
 * Delegates each tab to a focused sub-component.
 */
import { useEffect, useState } from 'react';
import { useSettingsStore, PipelineType } from '@/store/settings';
import { supabase } from '@/lib/supabase';
import { SettingsGeneralTab } from './settings-general-tab';
import { SettingsToggleRow } from './settings-toggle-row';

type Tab = 'general' | 'usage' | 'api-keys' | 'notifications';

const TABS: { id: Tab; label: string }[] = [
  { id: 'general', label: 'General' },
  { id: 'usage', label: 'Usage & Billing' },
  { id: 'api-keys', label: 'API Keys' },
  { id: 'notifications', label: 'Notifications' },
];

export function SettingsContent() {
  const {
    settings, isLoading, isSaving, error, saveSuccess,
    usernameCheck, isCheckingUsername,
    fetchSettings, updateSettings, checkUsername, clearError,
  } = useSettingsStore();

  const [activeTab, setActiveTab] = useState<Tab>('general');
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [defaultPipeline, setDefaultPipeline] = useState<PipelineType>('investigation');
  const [maxSources, setMaxSources] = useState(25);
  const [autoExtractClaims, setAutoExtractClaims] = useState(true);
  const [emailOnComplete, setEmailOnComplete] = useState(true);
  const [emailOnFailure, setEmailOnFailure] = useState(true);
  const [autoProducerPacket, setAutoProducerPacket] = useState(false);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUserEmail(data.user?.email ?? null));
    fetchSettings();
  }, [fetchSettings]);

  useEffect(() => {
    if (settings) {
      setUsername(settings.username || '');
      setDefaultPipeline(settings.default_pipeline);
      setAutoExtractClaims(settings.auto_extract_claims);
      setMaxSources(settings.max_sources);
      setEmailOnComplete(settings.email_on_complete);
      setEmailOnFailure(settings.email_on_failure);
    }
  }, [settings]);

  useEffect(() => {
    if (username.length >= 3 && username !== settings?.username) {
      const timer = setTimeout(() => checkUsername(username), 500);
      return () => clearTimeout(timer);
    }
  }, [username, settings?.username, checkUsername]);

  const handleSave = async () => {
    const updates: Record<string, unknown> = {
      default_pipeline: defaultPipeline,
      auto_extract_claims: autoExtractClaims,
      max_sources: maxSources,
      email_on_complete: emailOnComplete,
      email_on_failure: emailOnFailure,
    };
    if (username && username !== settings?.username && usernameCheck?.available) {
      updates.username = username;
    }
    await updateSettings(updates);
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-5 animate-pulse">
            <div className="h-4 w-28 rounded bg-muted mb-4" />
            <div className="h-9 rounded bg-muted mb-3" />
            <div className="h-9 w-2/3 rounded bg-muted" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-lg font-bold mb-1">Settings</h1>
      <p className="text-xs text-muted-foreground mb-6">Manage your account, API keys, and preferences</p>

      {/* Tab bar */}
      <div className="border-b border-border mb-6">
        <div className="flex items-center gap-6 text-sm">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 transition-colors cursor-pointer ${
                activeTab === tab.id
                  ? 'border-b-2 border-accent-blue text-foreground font-medium'
                  : 'border-b-2 border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Banners */}
      {saveSuccess && (
        <div className="mb-6 rounded-xl border border-accent-green/30 bg-accent-green/10 p-4 flex items-center gap-3">
          <svg className="h-4 w-4 text-accent-green flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-sm text-accent-green">Settings saved successfully!</p>
        </div>
      )}
      {error && (
        <div className="mb-6 rounded-xl border border-destructive/30 bg-destructive/10 p-4 flex items-center justify-between">
          <p className="text-sm text-destructive">{error}</p>
          <button onClick={clearError} className="text-destructive/70 hover:text-destructive ml-3">
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}

      {/* Tab panels */}
      {activeTab === 'general' && (
        <SettingsGeneralTab
          userEmail={userEmail}
          username={username}
          setUsername={setUsername}
          usernameCheck={usernameCheck}
          isCheckingUsername={isCheckingUsername}
          defaultPipeline={defaultPipeline}
          setDefaultPipeline={setDefaultPipeline}
          maxSources={maxSources}
          setMaxSources={setMaxSources}
          autoExtractClaims={autoExtractClaims}
          setAutoExtractClaims={setAutoExtractClaims}
          emailOnComplete={emailOnComplete}
          setEmailOnComplete={setEmailOnComplete}
          emailOnFailure={emailOnFailure}
          setEmailOnFailure={setEmailOnFailure}
          autoProducerPacket={autoProducerPacket}
          setAutoProducerPacket={setAutoProducerPacket}
          isSaving={isSaving}
          onSave={handleSave}
        />
      )}
      {activeTab === 'usage' && (
        <div className="text-sm text-muted-foreground">
          Usage & Billing details are shown on the{' '}
          <a href="/usage" className="text-accent-blue hover:underline">Usage page</a>.
        </div>
      )}
      {activeTab === 'api-keys' && (
        <div className="bg-card border border-border rounded-xl p-5 text-sm text-muted-foreground">
          API key management coming soon.
        </div>
      )}
      {activeTab === 'notifications' && (
        <div className="bg-card border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold">Notification Preferences</h2>
          <SettingsToggleRow
            label="Email on job complete"
            description="Receive email when a research job finishes"
            checked={emailOnComplete}
            onChange={setEmailOnComplete}
          />
          <SettingsToggleRow
            label="Email on job failure"
            description="Receive email when a research job fails"
            checked={emailOnFailure}
            onChange={setEmailOnFailure}
          />
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2 rounded-lg bg-accent-blue hover:bg-accent-blue/90 text-white text-sm font-medium transition-colors disabled:opacity-50"
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
