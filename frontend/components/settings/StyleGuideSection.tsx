/**
 * StyleGuideSection — Settings page section for managing personal style guides.
 *
 * Shows saved style guides, template selector for creating new ones,
 * and inline override editor.
 */

import { useEffect, useState } from 'react';
import { SettingsSection } from './SettingsSection';
import { TemplateCard } from './TemplateCard';
import {
  useStyleGuideStore,
  type StyleGuide,
  type TemplateInfo,
} from '../../store/style-guides';

export function StyleGuideSection() {
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
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
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
      is_default: guides.length === 0, // First guide auto-default
    });
    if (guide) {
      setShowCreate(false);
      setSelectedTemplate('');
      setNewName('');
    }
    setIsCreating(false);
  };

  const handleDelete = async (id: string) => {
    await deleteGuide(id);
  };

  const handleSetDefault = async (id: string) => {
    await setDefault(id);
  };

  const templateEntries = Object.entries(templates) as [string, TemplateInfo][];

  return (
    <SettingsSection
      title="Style Guides"
      description="Choose a content style that shapes your hooks, tone, and narrative structure."
      delay={0.5}
    >
      {/* Saved Guides */}
      {guides.length > 0 && (
        <div className="mb-6">
          <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider mb-3">
            Your Guides
          </p>
          <div className="space-y-2">
            {guides.map((guide) => (
              <div
                key={guide.id}
                className={`
                  flex items-center justify-between gap-3 rounded-lg border p-3
                  ${guide.is_default
                    ? 'border-blue-500/40 bg-blue-900/10'
                    : 'border-gray-700/40 bg-gray-800/30'
                  }
                `}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-medium text-gray-200 truncate">{guide.name}</span>
                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-gray-700/50 text-gray-500">
                      {guide.template_base.replace(/_/g, ' ')}
                    </span>
                    {guide.is_default && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/40 text-blue-400 border border-blue-800/30">
                        Default
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {!guide.is_default && (
                    <button
                      type="button"
                      onClick={() => handleSetDefault(guide.id)}
                      className="text-[11px] px-2 py-1 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-700/40 transition"
                    >
                      Set default
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(guide.id)}
                    className="text-[11px] px-2 py-1 rounded text-red-500/60 hover:text-red-400 hover:bg-red-900/20 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create New */}
      {!showCreate ? (
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          disabled={guides.length >= 10}
          className="w-full rounded-lg border border-dashed border-gray-700 p-4 text-[13px] text-gray-500 hover:text-gray-300 hover:border-gray-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {guides.length >= 10
            ? 'Maximum 10 style guides reached'
            : '+ Create a new style guide'
          }
        </button>
      ) : (
        <div className="rounded-lg border border-gray-700/50 bg-gray-800/30 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-medium text-gray-500 uppercase tracking-wider">
              Choose a template
            </p>
            <button
              type="button"
              onClick={() => { setShowCreate(false); setSelectedTemplate(''); setNewName(''); }}
              className="text-[11px] text-gray-500 hover:text-gray-400 transition"
            >
              Cancel
            </button>
          </div>

          {/* Template Grid */}
          <div className="grid grid-cols-1 gap-3">
            {templateEntries.map(([key, tmpl]) => (
              <TemplateCard
                key={key}
                templateKey={key}
                name={tmpl.name}
                description={tmpl.description}
                creatorReferences={tmpl.creator_references}
                exampleTone={tmpl.example_tone}
                isSelected={selectedTemplate === key}
                onSelect={setSelectedTemplate}
              />
            ))}
            {/* Custom option */}
            <button
              type="button"
              onClick={() => setSelectedTemplate('custom')}
              className={`
                w-full text-left rounded-lg border p-4 transition-all duration-200
                ${selectedTemplate === 'custom'
                  ? 'border-blue-500/60 ring-1 ring-blue-500/30 bg-blue-900/10'
                  : 'border-gray-700/50 bg-gray-800/40 hover:border-gray-600/60'
                }
              `}
            >
              <h3 className="text-[15px] font-semibold text-gray-100">Custom</h3>
              <p className="text-[13px] text-gray-400 mt-0.5">Start from scratch with your own voice and style.</p>
            </button>
          </div>

          {/* Name input + Create button */}
          {selectedTemplate && (
            <div className="flex gap-3 pt-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Guide name (e.g., 'My YouTube Style')"
                className="flex-1 rounded-lg border border-gray-700 bg-gray-800/60 px-3 py-2 text-[14px] text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500/50"
                maxLength={100}
              />
              <button
                type="button"
                onClick={handleCreate}
                disabled={!newName.trim() || isCreating}
                className="rounded-lg bg-blue-600 px-4 py-2 text-[13px] font-medium text-white hover:bg-blue-500 transition disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Error display */}
      {error && (
        <p className="mt-3 text-[12px] text-red-400">{error}</p>
      )}
    </SettingsSection>
  );
}
