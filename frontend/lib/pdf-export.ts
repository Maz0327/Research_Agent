/**
 * PDF export utility for markdown content.
 * Extracts PDF generation logic for reuse across components.
 *
 * Uses presentation layer formatting to display user-friendly labels
 * (e.g., "Source 1" instead of "SRC_1") without modifying stored JSON.
 */
import DOMPurify from 'dompurify';
import { transformMarkdownForDisplay } from './document-formatters';

/**
 * Convert markdown to PDF and trigger download.
 * @param markdown - Markdown content to convert
 * @param filename - Output filename (without extension)
 */
export async function exportToPdf(markdown: string, filename: string): Promise<void> {
  try {
    // Dynamic import html2pdf.js for client-side only
    const html2pdf = (await import('html2pdf.js')).default;

    // Create a styled HTML element for PDF rendering
    const element = document.createElement('div');

    // Apply presentation layer transformation before converting to HTML
    const displayMarkdown = transformMarkdownForDisplay(markdown);

    // Convert markdown to simple HTML
    const rawContent = displayMarkdown
      .replace(/^### (.*$)/gm, '<h3 style="margin-top:16px;margin-bottom:8px;font-size:14px;font-weight:600;">$1</h3>')
      .replace(/^## (.*$)/gm, '<h2 style="margin-top:20px;margin-bottom:10px;font-size:16px;font-weight:700;">$1</h2>')
      .replace(/^# (.*$)/gm, '<h1 style="margin-top:24px;margin-bottom:12px;font-size:20px;font-weight:700;">$1</h1>')
      .replace(/^\* (.*$)/gm, '<li style="margin-left:20px;">$1</li>')
      .replace(/^- (.*$)/gm, '<li style="margin-left:20px;">$1</li>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p style="margin-bottom:8px;">')
      .replace(/\n/g, '<br/>');

    // Sanitize HTML to prevent XSS attacks
    const sanitizedContent = DOMPurify.sanitize(rawContent);

    element.innerHTML = `
      <div style="padding:20px;font-family:system-ui,-apple-system,sans-serif;max-width:800px;font-size:14px;line-height:1.6;color:#1a1a1a;">
        <div style="margin-bottom:8px;">${sanitizedContent}</div>
      </div>
    `;

    // Sanitize filename
    const safeFilename = filename.replace(/[^a-zA-Z0-9-_]/g, '-');

    // Generate PDF
    await html2pdf()
      .set({
        margin: 10,
        filename: `${safeFilename}.pdf`,
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      })
      .from(element)
      .save();
  } catch (err) {
    console.error('PDF generation failed:', err);
    throw new Error('Failed to generate PDF. Please try downloading as Markdown instead.');
  }
}
