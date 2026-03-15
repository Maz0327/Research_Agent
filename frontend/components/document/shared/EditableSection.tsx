/**
 * EditableSection — Wrapper that makes document sections inline-editable.
 *
 * On click: highlights with blue border, shows InlineEditBar.
 * Calls iterateJob with mode='inline_edit' on submit.
 */

import { useState, useCallback, type ReactNode } from 'react';
import { InlineEditBar } from './InlineEditBar';
import { API_URL } from '@/lib/constants';
import { getAccessToken } from '@/lib/supabase';

export interface EditableSectionProps {
  children: ReactNode;
  sectionId: string;
  docType: string;
  jobId: string;
}

export function EditableSection({ children, sectionId, docType, jobId }: EditableSectionProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = useCallback(() => {
    if (!isEditing && !isLoading) {
      setIsEditing(true);
    }
  }, [isEditing, isLoading]);

  const handleSubmit = useCallback(async (instruction: string) => {
    setIsLoading(true);
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/iterate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          mode: 'inline_edit',
          doc_type: docType,
          section_id: sectionId,
          edit_instruction: instruction,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Inline edit failed:', errorData);
      }
    } catch (error) {
      console.error('Inline edit error:', error);
    } finally {
      setIsLoading(false);
      setIsEditing(false);
    }
  }, [jobId, docType, sectionId]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
  }, []);

  return (
    <div className="relative group">
      <div
        onClick={handleClick}
        className={`
          transition-all duration-200 rounded-lg
          ${isEditing
            ? 'ring-2 ring-blue-500/40 bg-blue-500/[0.03]'
            : 'hover:ring-1 hover:ring-white/[0.08] cursor-pointer'
          }
        `}
      >
        {children}
      </div>

      {/* Edit indicator on hover */}
      {!isEditing && !isLoading && (
        <div className="absolute -right-1 -top-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.08] text-white/30 border border-white/[0.06]">
            Edit
          </span>
        </div>
      )}

      {/* Inline edit bar */}
      {isEditing && (
        <div className="mt-2">
          <InlineEditBar
            jobId={jobId}
            docType={docType}
            sectionId={sectionId}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isLoading={isLoading}
          />
        </div>
      )}
    </div>
  );
}
