'use client';

/**
 * editable-section — View/edit toggle for document sections.
 * View mode: renders ProseBlock. Edit mode: textarea + save/cancel buttons.
 */

import { useState, useCallback } from 'react';
import { ProseBlock } from './prose-block';
import { cn } from '@/lib/utils';

interface EditableSectionProps {
  content: string;
  sectionId: string;
  onSave?: (sectionId: string, newContent: string) => void;
  editable?: boolean;
  className?: string;
}

export function EditableSection({ content, sectionId, onSave, editable = true, className }: EditableSectionProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(content);

  const handleSave = useCallback(() => {
    onSave?.(sectionId, draft);
    setIsEditing(false);
  }, [sectionId, draft, onSave]);

  const handleCancel = useCallback(() => {
    setDraft(content);
    setIsEditing(false);
  }, [content]);

  if (!editable) {
    return <ProseBlock content={content} className={className} />;
  }

  return (
    <div className={cn('group relative', className)}>
      {!isEditing ? (
        <>
          <ProseBlock content={content} />
          <button
            onClick={() => setIsEditing(true)}
            className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/40 hover:text-zinc-200"
            title="Edit section"
          >
            Edit
          </button>
        </>
      ) : (
        <div className="space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full min-h-[120px] text-sm text-zinc-200 bg-zinc-900 border border-blue-500/40 rounded-md p-3 resize-y focus:outline-none focus:ring-1 focus:ring-blue-500/40"
            autoFocus
          />
          <div className="flex gap-2 justify-end">
            <button
              onClick={handleCancel}
              className="text-xs px-3 py-1 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/40 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="text-xs px-3 py-1 rounded bg-blue-600 text-white border border-blue-500/40 hover:bg-blue-500 transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
