'use client';

/**
 * StyleGuidesSection — list, create, delete style guides using useStyleGuideStore.
 * Part of settings-v2 for App Router. Reuses store from components/settings/StyleGuideSection.
 */
import { useEffect, useState } from 'react';
import { useStyleGuideStore, type TemplateInfo } from '@/store/style-guides';

export function StyleGuidesSection() {
  const {
    guides,
    templates,
    isLoading,
    error,
    fetchGuides,
    fetchTemplates,
    createGuide,
    deleteGuide,
    setDefault,
  } = useStyleGuideStore();

  const [showCreate, setShowCreate] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [newName, setNewName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchGuides();
    fetchTemplates();
  }, [fetchGuides, fetchTemplates]);

  const handleCreate = async () => {
    if (!selectedTemplate || !newName.trim()) return;
    setIsCreating(true);
    const guide = await createGuide({
      name: newName.trim(),
      template_base: selectedTemplate,
      is_default: guides.length === 0,
    });
    if (guide) {
      setShowCreate(false);
      setSelectedTemplate('');
      setNewName('');
    }
    setIsCreating(false);
  };

  const templateEntries = Object.entries(templates) as [string, TemplateInfo][];

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
      <div className="flex items-center gap-2 mb-4">
        <svg className="h-4 w-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h2 className="text-lg font-semibold text-gray-100">Style Guides</h2>
      </div>
      <p className="text-sm text-gray-400 mb-5">
        Choose a content style that shapes your hooks, tone, and narrative structure.
      </p>

      {/* Existing guides */}
      {guides.length > 0 && (
        <div className="mb-5 space-y-2">
          {guides.map((guide) => (
            <div
              key={guide.id}
              className={`flex items-center justify-between gap-3 rounded-lg border p-3 ${
                guide.is_default
                  ? 'border-blue-500/40 bg-blue-900/10'
                  : 'border-gray-700/40 bg-gray-800/30'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm font-medium text-gray-200 truncate">{guide.name}</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-700/50 text-gray-500 flex-shrink-0">
                  {guide.template_base.replace(/_/g, ' ')}
                </span>
                {guide.is_default && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-blue-900/40 text-blue-400 border border-blue-800/30 flex-shrink-0">
                    Default
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {!guide.is_default && (
                  <button
                    onClick={() => setDefault(guide.id)}
                    className="text-xs px-2 py-1 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-700/40 transition"
                  >
                    Set default
                  </button>
                )}
                <button
                  onClick={() => deleteGuide(guide.id)}
                  className="text-xs px-2 py-1 rounded text-red-500/60 hover:text-red-400 hover:bg-red-900/20 transition"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create new */}
      {!showCreate ? (
        <button
          onClick={() => setShowCreate(true)}
          disabled={guides.length >= 10}
          className="w-full rounded-lg border border-dashed border-gray-700 p-4 text-sm text-gray-500 hover:text-gray-300 hover:border-gray-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {guides.length >= 10 ? 'Maximum 10 style guides reached' : '+ Create a new style guide'}
        </button>
      ) : (
        <div className="rounded-lg border border-gray-700/50 bg-gray-800/30 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Choose a template</p>
            <button
              onClick={() => { setShowCreate(false); setSelectedTemplate(''); setNewName(''); }}
              className="text-xs text-gray-500 hover:text-gray-400 transition"
            >
              Cancel
            </button>
          </div>

          <div className="grid gap-2">
            {templateEntries.map(([key, tmpl]) => (
              <button
                key={key}
                onClick={() => setSelectedTemplate(key)}
                className={`w-full text-left rounded-lg border p-3 transition-all ${
                  selectedTemplate === key
                    ? 'border-blue-500/60 ring-1 ring-blue-500/30 bg-blue-900/10'
                    : 'border-gray-700/50 bg-gray-800/40 hover:border-gray-600/60'
                }`}
              >
                <p className="text-sm font-semibold text-gray-100">{tmpl.name}</p>
                <p className="text-xs text-gray-400 mt-0.5">{tmpl.description}</p>
              </button>
            ))}
            <button
              onClick={() => setSelectedTemplate('custom')}
              className={`w-full text-left rounded-lg border p-3 transition-all ${
                selectedTemplate === 'custom'
                  ? 'border-blue-500/60 ring-1 ring-blue-500/30 bg-blue-900/10'
                  : 'border-gray-700/50 bg-gray-800/40 hover:border-gray-600/60'
              }`}
            >
              <p className="text-sm font-semibold text-gray-100">Custom</p>
              <p className="text-xs text-gray-400 mt-0.5">Start from scratch with your own voice and style.</p>
            </button>
          </div>

          {selectedTemplate && (
            <div className="flex gap-3 pt-1">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Guide name (e.g., 'My YouTube Style')"
                className="flex-1 rounded-lg border border-gray-700 bg-gray-800/60 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500/50"
                maxLength={100}
              />
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || isCreating}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
            </div>
          )}
        </div>
      )}

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </div>
  );
}
