/**
 * Screenshot source form with file upload and OCR preview.
 * Converts image to base64 for API submission.
 */
import { useState, useRef, useCallback } from 'react';
import Image from 'next/image';
import { SCREENSHOT_PLATFORM_HINTS } from '../../../lib/constants';

interface ScreenshotSourceFormProps {
  onAdd: (data: { file: File; base64: string; platformHint: string }) => void;
  onCancel: () => void;
}

// Max file size: 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif'];

export function ScreenshotSourceForm({ onAdd, onCancel }: ScreenshotSourceFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [platformHint, setPlatformHint] = useState('other');
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (error) => reject(error);
    });
  };

  // Validate and process file
  const processFile = useCallback(async (selectedFile: File) => {
    setError(null);

    // Validate type
    if (!ALLOWED_TYPES.includes(selectedFile.type)) {
      setError('Invalid file type. Please upload PNG, JPEG, WebP, or GIF.');
      return;
    }

    // Validate size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File too large. Maximum size is 10MB.');
      return;
    }

    // Create preview
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreview(objectUrl);
    setFile(selectedFile);
  }, []);

  // Handle file input change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  // Handle drag and drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      processFile(droppedFile);
    }
  };

  // Handle submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an image file.');
      return;
    }

    try {
      const base64 = await fileToBase64(file);
      onAdd({ file, base64, platformHint });
    } catch (err) {
      setError('Failed to process image. Please try again.');
    }
  };

  // Clear selected file
  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Drop zone / File input */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-border hover:border-border'
        }`}
      >
        {preview ? (
          <div className="space-y-3">
            <div className="relative h-48 w-full">
              <Image
                src={preview}
                alt="Preview"
                fill
                className="rounded-lg object-contain"
                unoptimized  // Required for blob URLs from createObjectURL
              />
            </div>
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <span>{file?.name}</span>
              <span className="text-muted-foreground/60">•</span>
              <span>{file ? (file.size / 1024).toFixed(1) : 0} KB</span>
            </div>
            <button
              type="button"
              onClick={handleClear}
              className="text-sm text-red-400 hover:text-red-300"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <svg
              className="mx-auto h-12 w-12 text-muted-foreground/70"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <p className="text-muted-foreground">
              Drag and drop an image, or{' '}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="text-blue-400 hover:text-blue-300"
              >
                browse
              </button>
            </p>
            <p className="text-xs text-muted-foreground/70">PNG, JPEG, WebP, GIF up to 10MB</p>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Platform hint selector */}
      <div>
        <label className="block text-sm font-medium text-muted-foreground mb-2">
          Screenshot Source (helps OCR accuracy)
        </label>
        <select
          value={platformHint}
          onChange={(e) => setPlatformHint(e.target.value)}
          className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        >
          {SCREENSHOT_PLATFORM_HINTS.map((hint) => (
            <option key={hint.value} value={hint.value}>
              {hint.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground hover:text-muted-foreground"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!file}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add Screenshot
        </button>
      </div>
    </form>
  );
}

export default ScreenshotSourceForm;
