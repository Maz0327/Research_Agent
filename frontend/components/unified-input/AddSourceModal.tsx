/**
 * AddSourceModal - Modal for selecting and adding source type.
 * Includes batch URL paste for adding multiple URLs at once.
 */
import { useState, useEffect } from 'react';
import { VideoSourceForm, TextSourceForm, ArticleSourceForm, ScreenshotSourceForm } from './source-forms';

type SourceFormType = 'video' | 'text' | 'article' | 'screenshot' | 'batch' | null;

interface TextInputData {
  title: string;
  content: string;
  platform_hint?: string;
}

interface ScreenshotData {
  file: File;
  base64: string;
  platformHint: string;
}

interface AddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddVideos: (urls: string[]) => void;
  onAddText: (data: TextInputData) => void;
  onAddArticles: (urls: string[]) => void;
  onAddScreenshot: (data: ScreenshotData) => void;
}

/** Inline batch URL form */
function BatchUrlForm({ onAddVideos, onAddArticles, onCancel }: {
  onAddVideos: (urls: string[]) => void;
  onAddArticles: (urls: string[]) => void;
  onCancel: () => void;
}) {
  const [batchText, setBatchText] = useState('');

  const parsedUrls = batchText
    .split(/[\n,]/)
    .map((u) => u.trim())
    .filter((u) => u.startsWith('http'));

  const videoUrls = parsedUrls.filter((u) => u.includes('youtube.com') || u.includes('youtu.be'));
  const articleUrls = parsedUrls.filter((u) => !u.includes('youtube.com') && !u.includes('youtu.be'));

  const handleAdd = () => {
    if (videoUrls.length > 0) onAddVideos(videoUrls);
    if (articleUrls.length > 0) onAddArticles(articleUrls);
  };

  return (
    <div className="space-y-3">
      <textarea
        value={batchText}
        onChange={(e) => setBatchText(e.target.value)}
        placeholder="Paste multiple URLs here (one per line or comma-separated)"
        rows={6}
        className="w-full rounded-lg border border-border bg-card px-4 py-3 text-sm text-foreground placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        style={{ fontSize: '16px' }}
        autoFocus
      />
      {parsedUrls.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          {videoUrls.length > 0 && (
            <span className="px-2 py-1 rounded-full bg-purple-900/30 text-purple-300 border border-purple-700/40">
              {videoUrls.length} video{videoUrls.length !== 1 ? 's' : ''}
            </span>
          )}
          {articleUrls.length > 0 && (
            <span className="px-2 py-1 rounded-full bg-blue-900/30 text-blue-300 border border-blue-700/40">
              {articleUrls.length} article{articleUrls.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}
      <div className="flex gap-3">
        <button onClick={onCancel} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition">
          Cancel
        </button>
        <button
          onClick={handleAdd}
          disabled={parsedUrls.length === 0}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add {parsedUrls.length} URL{parsedUrls.length !== 1 ? 's' : ''}
        </button>
      </div>
    </div>
  );
}

export function AddSourceModal({ isOpen, onClose, onAddVideos, onAddText, onAddArticles, onAddScreenshot }: AddSourceModalProps) {
  const [activeForm, setActiveForm] = useState<SourceFormType>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setActiveForm(null); onClose(); }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleClose = () => {
    setActiveForm(null);
    onClose();
  };

  const handleAddVideos = (urls: string[]) => {
    onAddVideos(urls);
    handleClose();
  };

  const handleAddText = (data: TextInputData) => {
    onAddText(data);
    handleClose();
  };

  const handleAddArticles = (urls: string[]) => {
    onAddArticles(urls);
    handleClose();
  };

  const handleAddScreenshot = (data: ScreenshotData) => {
    onAddScreenshot(data);
    handleClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-labelledby="add-source-modal-title">
      <div className="w-full max-w-lg rounded-xl border border-border bg-background shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 id="add-source-modal-title" className="text-lg font-semibold text-foreground">
            {activeForm === 'batch' ? 'Paste Multiple URLs' : activeForm ? `Add ${activeForm.charAt(0).toUpperCase() + activeForm.slice(1)}` : 'Add Source'}
          </h3>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-muted-foreground hover:bg-card transition"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {!activeForm ? (
            // Source type selection
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <button
                onClick={() => setActiveForm('video')}
                className="flex flex-col items-center gap-2 rounded-lg border border-purple-700/50 bg-purple-900/20 p-4 text-purple-300 hover:bg-purple-900/30 transition"
              >
                <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium">Video</span>
                <span className="text-xs text-muted-foreground/70">YouTube URLs</span>
              </button>

              <button
                onClick={() => setActiveForm('text')}
                className="flex flex-col items-center gap-2 rounded-lg border border-green-700/50 bg-green-900/20 p-4 text-green-300 hover:bg-green-900/30 transition"
              >
                <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-sm font-medium">Text</span>
                <span className="text-xs text-muted-foreground/70">Paste content</span>
              </button>

              <button
                onClick={() => setActiveForm('article')}
                className="flex flex-col items-center gap-2 rounded-lg border border-blue-700/50 bg-blue-900/20 p-4 text-blue-300 hover:bg-blue-900/30 transition"
              >
                <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                <span className="text-sm font-medium">Article</span>
                <span className="text-xs text-muted-foreground/70">Fetch URL</span>
              </button>

              <button
                onClick={() => setActiveForm('screenshot')}
                className="flex flex-col items-center gap-2 rounded-lg border border-amber-700/50 bg-amber-900/20 p-4 text-amber-300 hover:bg-amber-900/30 transition"
              >
                <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span className="text-sm font-medium">Screenshot</span>
                <span className="text-xs text-muted-foreground/70">Upload image</span>
              </button>

              <button
                onClick={() => setActiveForm('batch')}
                className="flex flex-col items-center gap-2 rounded-lg border border-teal-700/50 bg-teal-900/20 p-4 text-teal-300 hover:bg-teal-900/30 transition"
              >
                <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span className="text-sm font-medium">Batch</span>
                <span className="text-xs text-muted-foreground/70">Multiple URLs</span>
              </button>
            </div>
          ) : activeForm === 'video' ? (
            <VideoSourceForm
              onAdd={handleAddVideos}
              onCancel={() => setActiveForm(null)}
            />
          ) : activeForm === 'text' ? (
            <TextSourceForm
              onAdd={handleAddText}
              onCancel={() => setActiveForm(null)}
            />
          ) : activeForm === 'article' ? (
            <ArticleSourceForm
              onAdd={handleAddArticles}
              onCancel={() => setActiveForm(null)}
            />
          ) : activeForm === 'screenshot' ? (
            <ScreenshotSourceForm
              onAdd={handleAddScreenshot}
              onCancel={() => setActiveForm(null)}
            />
          ) : activeForm === 'batch' ? (
            <BatchUrlForm
              onAddVideos={handleAddVideos}
              onAddArticles={handleAddArticles}
              onCancel={() => setActiveForm(null)}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default AddSourceModal;
