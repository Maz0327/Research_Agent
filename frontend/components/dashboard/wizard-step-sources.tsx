'use client';

/**
 * Wizard Step 2 — Source inputs.
 * Dynamic list of URL/text sources. Minimum 0 (auto-search mode).
 */
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export interface SourceEntry {
  id: string;
  type: 'youtube' | 'article' | 'text';
  url: string;
  text: string;
}

interface WizardStepSourcesProps {
  sources: SourceEntry[];
  onChange: (sources: SourceEntry[]) => void;
}

function makeEntry(): SourceEntry {
  return { id: crypto.randomUUID(), type: 'article', url: '', text: '' };
}

export function WizardStepSources({ sources, onChange }: WizardStepSourcesProps) {
  const add = () => onChange([...sources, makeEntry()]);

  const remove = (id: string) => onChange(sources.filter((s) => s.id !== id));

  const update = (id: string, patch: Partial<SourceEntry>) =>
    onChange(sources.map((s) => (s.id === id ? { ...s, ...patch } : s)));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-[#f5f5f5] mb-1">Add sources (optional)</h2>
        <p className="text-sm text-[#71717a]">Leave empty to let the system auto-discover sources.</p>
      </div>

      {sources.map((src) => (
        <div key={src.id} className="flex flex-col gap-2 p-3 rounded-lg border border-[#27272a] bg-[#1a1a25]">
          <div className="flex items-center gap-2">
            <select
              value={src.type}
              onChange={(e) => update(src.id, { type: e.target.value as SourceEntry['type'] })}
              className="text-xs bg-[#12121a] border border-[#27272a] text-[#a1a1aa] rounded px-2 py-1"
            >
              <option value="youtube">YouTube</option>
              <option value="article">Article</option>
              <option value="text">Text</option>
            </select>
            <button
              onClick={() => remove(src.id)}
              className="ml-auto text-xs text-[#71717a] hover:text-red-400 transition-colors cursor-pointer"
              aria-label="Remove source"
            >
              Remove
            </button>
          </div>

          {src.type === 'text' ? (
            <textarea
              value={src.text}
              onChange={(e) => update(src.id, { text: e.target.value })}
              placeholder="Paste text content here…"
              rows={3}
              className="text-sm bg-[#12121a] border border-[#27272a] text-[#f5f5f5] placeholder:text-[#3f3f46] rounded px-3 py-2 resize-none"
            />
          ) : (
            <Input
              value={src.url}
              onChange={(e) => update(src.id, { url: e.target.value })}
              placeholder={src.type === 'youtube' ? 'https://youtube.com/watch?v=…' : 'https://example.com/article'}
              className="bg-[#12121a] border-[#27272a] text-[#f5f5f5] placeholder:text-[#3f3f46]"
            />
          )}
        </div>
      ))}

      <Button variant="outline" size="sm" onClick={add} className="self-start border-[#27272a] text-[#a1a1aa]">
        + Add source
      </Button>
    </div>
  );
}
