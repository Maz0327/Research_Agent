/**
 * VideoSourceForm - Input form for adding YouTube video URLs.
 * Supports single or multiple URLs (one per line).
 */
import { useState } from 'react';

interface VideoSourceFormProps {
  onAdd: (urls: string[]) => void;
  onCancel: () => void;
}

export function VideoSourceForm({ onAdd, onCancel }: VideoSourceFormProps) {
  const [urls, setUrls] = useState('');

  // Parse video URLs from textarea
  const parseVideoUrls = (text: string): string[] => {
    return text
      .split(/[\n,]/)
      .map((url) => url.trim())
      .filter((url) => url.length > 0 && (url.includes('youtube.com') || url.includes('youtu.be')));
  };

  const validUrls = parseVideoUrls(urls);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validUrls.length > 0) {
      onAdd(validUrls);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="videoUrls" className="mb-1.5 block text-sm font-medium text-gray-300">
          YouTube URLs
          {validUrls.length > 0 && (
            <span className="ml-2 text-purple-400">({validUrls.length} valid)</span>
          )}
        </label>
        <textarea
          id="videoUrls"
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder={`Paste YouTube URLs (one per line)\n\nhttps://youtube.com/watch?v=...\nhttps://youtu.be/...`}
          rows={4}
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 font-mono text-sm transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
        />
        <p className="mt-1.5 text-xs text-gray-500">
          Supports multiple videos. Each will be processed for quotes and key moments.
        </p>
      </div>

      <div className="flex gap-3 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-300 transition"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={validUrls.length === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add {validUrls.length > 0 ? `${validUrls.length} Video${validUrls.length > 1 ? 's' : ''}` : 'Video'}
        </button>
      </div>
    </form>
  );
}

export default VideoSourceForm;
