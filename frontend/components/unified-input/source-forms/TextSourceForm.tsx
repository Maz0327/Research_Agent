/**
 * TextSourceForm - Input form for adding user-provided text content.
 */
import { useState } from 'react';
import { VALIDATION_LIMITS, PLATFORM_HINTS } from '../../../lib/constants';

interface TextSourceData {
  title: string;
  content: string;
  platform_hint?: string;
}

interface TextSourceFormProps {
  onAdd: (data: TextSourceData) => void;
  onCancel: () => void;
}

export function TextSourceForm({ onAdd, onCancel }: TextSourceFormProps) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [platformHint, setPlatformHint] = useState('article');

  const isValid = title.trim().length >= 1 && content.length >= VALIDATION_LIMITS.MIN_TEXT_CONTENT_LENGTH;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValid) {
      onAdd({
        title: title.trim(),
        content: content,
        platform_hint: platformHint !== 'other' ? platformHint : undefined,
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <div>
        <label htmlFor="textTitle" className="mb-1.5 block text-sm font-medium text-gray-300">
          Source Title <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          id="textTitle"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., WSJ Article, Internal Email, Forum Post"
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
          maxLength={200}
        />
      </div>

      {/* Content */}
      <div>
        <label htmlFor="textContent" className="mb-1.5 block text-sm font-medium text-gray-300">
          Content <span className="text-red-400">*</span>
          <span className="ml-2 text-gray-500">
            ({content.length.toLocaleString()} / {VALIDATION_LIMITS.MAX_TEXT_CONTENT_LENGTH.toLocaleString()})
          </span>
        </label>
        <textarea
          id="textContent"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste the article, email, forum post, or other text content..."
          rows={6}
          maxLength={VALIDATION_LIMITS.MAX_TEXT_CONTENT_LENGTH}
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 font-mono text-sm transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Min {VALIDATION_LIMITS.MIN_TEXT_CONTENT_LENGTH} characters. Quotes extracted will be marked as unverified.
        </p>
      </div>

      {/* Platform Hint */}
      <div>
        <label htmlFor="textPlatform" className="mb-1.5 block text-sm font-medium text-gray-300">
          Platform <span className="text-gray-500">(optional)</span>
        </label>
        <select
          id="textPlatform"
          value={platformHint}
          onChange={(e) => setPlatformHint(e.target.value)}
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500 cursor-pointer"
        >
          {PLATFORM_HINTS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.icon} {p.label}
            </option>
          ))}
        </select>
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
          disabled={!isValid}
          className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Text
        </button>
      </div>
    </form>
  );
}

export default TextSourceForm;
