/**
 * UnifiedInputPanel - Main component for multi-source research job creation.
 *
 * Supports adding multiple sources of different types (video, text, article, screenshot)
 * to a single research job with a unified topic.
 */
import { useState, useCallback } from 'react';
import { SourceCard, Source, SourceType } from './SourceCard';
import { AddSourceModal } from './AddSourceModal';

// Text input data structure
interface TextInputData {
  title: string;
  content: string;
  platform_hint?: string;
}

// Screenshot data structure
interface ScreenshotInputData {
  filename: string;
  base64: string;
  platformHint: string;
}

// Internal source data stored alongside display info
interface SourceData {
  videoUrls: string[];
  articleUrls: string[];
  textInputs: TextInputData[];
  screenshots: ScreenshotInputData[];
}

interface UnifiedInputPanelProps {
  onSubmit: (data: {
    topic: string;
    videoUrls: string[];
    articleUrls: string[];
    textInputs: TextInputData[];
    screenshots: ScreenshotInputData[];
  }) => Promise<void>;
  isSubmitting?: boolean;
}

export function UnifiedInputPanel({ onSubmit, isSubmitting = false }: UnifiedInputPanelProps) {
  const [topic, setTopic] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceData, setSourceData] = useState<SourceData>({
    videoUrls: [],
    articleUrls: [],
    textInputs: [],
    screenshots: [],
  });
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Generate unique ID for sources
  const generateId = () => `src_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

  // Extract domain from URL for display
  const getDomain = (url: string): string => {
    try {
      const domain = new URL(url).hostname.replace('www.', '');
      return domain.length > 30 ? domain.substring(0, 27) + '...' : domain;
    } catch {
      return url.substring(0, 30);
    }
  };

  // Add video sources
  const handleAddVideos = useCallback((urls: string[]) => {
    const newSources: Source[] = urls.map((url) => ({
      id: generateId(),
      type: 'video' as SourceType,
      label: getDomain(url),
      detail: url,
    }));

    setSources((prev) => [...prev, ...newSources]);
    setSourceData((prev) => ({
      ...prev,
      videoUrls: [...prev.videoUrls, ...urls],
    }));
  }, []);

  // Add text source
  const handleAddText = useCallback((data: TextInputData) => {
    const newSource: Source = {
      id: generateId(),
      type: 'text',
      label: data.title,
      detail: `${data.content.length.toLocaleString()} characters`,
    };

    setSources((prev) => [...prev, newSource]);
    setSourceData((prev) => ({
      ...prev,
      textInputs: [...prev.textInputs, data],
    }));
  }, []);

  // Add article sources
  const handleAddArticles = useCallback((urls: string[]) => {
    const newSources: Source[] = urls.map((url) => ({
      id: generateId(),
      type: 'article' as SourceType,
      label: getDomain(url),
      detail: url,
    }));

    setSources((prev) => [...prev, ...newSources]);
    setSourceData((prev) => ({
      ...prev,
      articleUrls: [...prev.articleUrls, ...urls],
    }));
  }, []);

  // Add screenshot source
  const handleAddScreenshot = useCallback((data: { file: File; base64: string; platformHint: string }) => {
    const newSource: Source = {
      id: generateId(),
      type: 'screenshot',
      label: data.file.name,
      detail: `${(data.file.size / 1024).toFixed(1)} KB • ${data.platformHint}`,
    };

    setSources((prev) => [...prev, newSource]);
    setSourceData((prev) => ({
      ...prev,
      screenshots: [...prev.screenshots, {
        filename: data.file.name,
        base64: data.base64,
        platformHint: data.platformHint,
      }],
    }));
  }, []);

  // Remove source by ID
  const handleRemoveSource = useCallback((id: string) => {
    setSources((prev) => {
      const sourceToRemove = prev.find((s) => s.id === id);
      if (!sourceToRemove) return prev;

      // Also remove from source data
      setSourceData((prevData) => {
        const newData = { ...prevData };

        if (sourceToRemove.type === 'video' && sourceToRemove.detail) {
          newData.videoUrls = prevData.videoUrls.filter((url) => url !== sourceToRemove.detail);
        } else if (sourceToRemove.type === 'article' && sourceToRemove.detail) {
          newData.articleUrls = prevData.articleUrls.filter((url) => url !== sourceToRemove.detail);
        } else if (sourceToRemove.type === 'text') {
          // Find index based on matching label (title)
          const idx = prevData.textInputs.findIndex((t) => t.title === sourceToRemove.label);
          if (idx >= 0) {
            newData.textInputs = [...prevData.textInputs.slice(0, idx), ...prevData.textInputs.slice(idx + 1)];
          }
        } else if (sourceToRemove.type === 'screenshot') {
          // Find index based on matching label (filename)
          const idx = prevData.screenshots.findIndex((s) => s.filename === sourceToRemove.label);
          if (idx >= 0) {
            newData.screenshots = [...prevData.screenshots.slice(0, idx), ...prevData.screenshots.slice(idx + 1)];
          }
        }

        return newData;
      });

      return prev.filter((s) => s.id !== id);
    });
  }, []);

  // Submit handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || sources.length === 0) return;

    await onSubmit({
      topic: topic.trim(),
      videoUrls: sourceData.videoUrls,
      articleUrls: sourceData.articleUrls,
      textInputs: sourceData.textInputs,
      screenshots: sourceData.screenshots,
    });

    // Clear form on success
    setTopic('');
    setSources([]);
    setSourceData({ videoUrls: [], articleUrls: [], textInputs: [], screenshots: [] });
  };

  const totalSources = sources.length;
  const canSubmit = topic.trim().length > 0 && totalSources > 0 && !isSubmitting;

  return (
    <div className="space-y-5">
      {/* Research Topic */}
      <div>
        <label htmlFor="researchTopic" className="mb-1.5 block text-sm font-medium text-gray-300">
          Research Topic <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          id="researchTopic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What are you researching? e.g., AI safety concerns, SpaceX Starship development"
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          disabled={isSubmitting}
          maxLength={500}
        />
        <p className="mt-1 text-xs text-gray-500">
          This topic will be used to focus analysis across all sources.
        </p>
      </div>

      {/* Sources List */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">
            Sources
            {totalSources > 0 && (
              <span className="ml-2 text-gray-500">({totalSources})</span>
            )}
          </label>
          {totalSources >= 20 && (
            <span className="text-xs text-yellow-400">Maximum 20 sources</span>
          )}
        </div>

        {sources.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-700 p-6 text-center">
            <p className="text-sm text-gray-500">
              No sources added yet. Click below to add videos, text, or articles.
            </p>
          </div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {sources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                onRemove={handleRemoveSource}
              />
            ))}
          </div>
        )}
      </div>

      {/* Add Source Button */}
      {totalSources < 20 && (
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          disabled={isSubmitting}
          className="w-full rounded-lg border border-dashed border-gray-600 py-3 text-sm font-medium text-gray-400 hover:border-gray-500 hover:text-gray-300 hover:bg-gray-800/50 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="inline-flex items-center gap-2">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Source
          </span>
        </button>
      )}

      {/* Submit Section - stack on mobile */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 sm:pt-2">
        <div className="text-xs sm:text-sm text-gray-500 order-2 sm:order-1">
          {totalSources > 0 ? (
            <>
              <span className="text-purple-400">{sourceData.videoUrls.length}</span> video
              {sourceData.videoUrls.length !== 1 ? 's' : ''},{' '}
              <span className="text-green-400">{sourceData.textInputs.length}</span> text,{' '}
              <span className="text-blue-400">{sourceData.articleUrls.length}</span> article
              {sourceData.articleUrls.length !== 1 ? 's' : ''},{' '}
              <span className="text-amber-400">{sourceData.screenshots.length}</span> screenshot
              {sourceData.screenshots.length !== 1 ? 's' : ''}
            </>
          ) : (
            'Add at least one source to continue'
          )}
        </div>

        {/* Full-width on mobile */}
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full sm:w-auto order-1 sm:order-2 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3.5 sm:py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-purple-500 hover:shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none min-h-[48px] sm:min-h-0 touch-manipulation"
        >
          {isSubmitting ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Creating Job...
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Start Research
            </>
          )}
        </button>
      </div>

      {/* Add Source Modal */}
      <AddSourceModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onAddVideos={handleAddVideos}
        onAddText={handleAddText}
        onAddArticles={handleAddArticles}
        onAddScreenshot={handleAddScreenshot}
      />
    </div>
  );
}

export default UnifiedInputPanel;
