/**
 * ArticleSourceForm - Input form for adding article URLs to fetch and analyze.
 */
import { useState } from 'react';

interface ArticleSourceFormProps {
  onAdd: (urls: string[]) => void;
  onCancel: () => void;
}

export function ArticleSourceForm({ onAdd, onCancel }: ArticleSourceFormProps) {
  const [urls, setUrls] = useState('');

  // Parse article URLs from textarea
  const parseArticleUrls = (text: string): string[] => {
    const urlPattern = /^https?:\/\/(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?$/;
    return text
      .split(/[\n,]/)
      .map((url) => url.trim())
      .filter((url) => url.length > 0 && urlPattern.test(url) && !url.includes('youtube.com') && !url.includes('youtu.be'));
  };

  const validUrls = parseArticleUrls(urls);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validUrls.length > 0) {
      onAdd(validUrls);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="articleUrls" className="mb-1.5 block text-sm font-medium text-muted-foreground">
          Article URLs
          {validUrls.length > 0 && (
            <span className="ml-2 text-blue-400">({validUrls.length} valid)</span>
          )}
        </label>
        <textarea
          id="articleUrls"
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder={`Paste article URLs (one per line)\n\nhttps://example.com/article\nhttps://news.site.com/story`}
          rows={4}
          className="w-full rounded-lg border border-border bg-card px-4 py-3 text-foreground placeholder-gray-500 font-mono text-sm transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1.5 text-xs text-muted-foreground/70">
          Articles will be fetched and analyzed. Paywalled content may not extract properly.
        </p>
      </div>

      <div className="flex gap-3 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground hover:text-muted-foreground transition"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={validUrls.length === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add {validUrls.length > 0 ? `${validUrls.length} Article${validUrls.length > 1 ? 's' : ''}` : 'Article'}
        </button>
      </div>
    </form>
  );
}

export default ArticleSourceForm;
