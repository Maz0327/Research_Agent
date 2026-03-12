/**
 * DOCX export utility for markdown content.
 *
 * Converts markdown to a Word document using the docx library.
 * Produces a clean, readable .docx with proper heading hierarchy,
 * bullet lists, tables, and styled text.
 */
import { transformMarkdownForDisplay } from './document-formatters';

/** Strip markdown formatting characters for plain text */
function stripMarkdownFormatting(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/<[^>]+>/g, '');
}

/** Strip HTML tags */
function stripHtmlTags(text: string): string {
  return text.replace(/<[^>]+>/g, '');
}

/**
 * Convert markdown to DOCX and trigger download.
 * @param markdown - Markdown content to convert
 * @param filename - Output filename (without extension)
 */
export async function exportToDocx(markdown: string, filename: string): Promise<void> {
  try {
    // Dynamic import docx for client-side only
    const docx = await import('docx');
    const {
      Document, Packer, Paragraph, TextRun, HeadingLevel,
      AlignmentType, BorderStyle, Table, TableRow, TableCell, WidthType,
    } = docx;

    /**
     * Parse inline markdown formatting into TextRun instances.
     * Must be inside exportToDocx so TextRun constructor is available.
     */
    const makeTextRuns = (text: string): any[] => {
      const stripped = stripHtmlTags(text);
      const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
      const runs: any[] = [];
      let lastIdx = 0;
      let match: RegExpExecArray | null;

      while ((match = pattern.exec(stripped)) !== null) {
        if (match.index > lastIdx) {
          runs.push(new TextRun({ text: stripped.slice(lastIdx, match.index), size: 20 }));
        }
        const token = match[0];
        if (token.startsWith('**')) {
          runs.push(new TextRun({ text: token.slice(2, -2), bold: true, size: 20 }));
        } else if (token.startsWith('*')) {
          runs.push(new TextRun({ text: token.slice(1, -1), italics: true, size: 20 }));
        } else if (token.startsWith('`')) {
          runs.push(new TextRun({ text: token.slice(1, -1), font: 'Courier New', size: 18, color: '666666' }));
        } else if (token.startsWith('[')) {
          const linkMatch = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
          if (linkMatch) {
            runs.push(new TextRun({ text: `${linkMatch[1]} (${linkMatch[2]})`, color: '2266CC', underline: {}, size: 20 }));
          }
        }
        lastIdx = match.index + match[0].length;
      }

      if (lastIdx < stripped.length) {
        runs.push(new TextRun({ text: stripped.slice(lastIdx), size: 20 }));
      }
      if (runs.length === 0) {
        runs.push(new TextRun({ text: stripped || ' ', size: 20 }));
      }
      return runs;
    };

    // Apply presentation layer transformation
    const displayMarkdown = transformMarkdownForDisplay(markdown);

    // Parse markdown into document elements
    const children: any[] = [];
    const lines = displayMarkdown.split('\n');
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Skip empty lines
      if (line.trim() === '') {
        i++;
        continue;
      }

      // Skip HTML tags (details/summary, etc.)
      if (/^<\/?(?:details|summary)/.test(line.trim())) {
        i++;
        continue;
      }

      // Code blocks
      if (line.trim().startsWith('```')) {
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        i++;
        children.push(
          new Paragraph({
            children: [
              new TextRun({ text: codeLines.join('\n'), font: 'Courier New', size: 18, color: '444444' }),
            ],
            spacing: { before: 100, after: 100 },
            shading: { type: docx.ShadingType.SOLID, fill: 'F5F5F5', color: 'F5F5F5' },
          })
        );
        continue;
      }

      // Headers
      const h1Match = line.match(/^# (.+)$/);
      if (h1Match) {
        children.push(new Paragraph({
          text: stripMarkdownFormatting(h1Match[1]),
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 300, after: 150 },
        }));
        i++;
        continue;
      }

      const h2Match = line.match(/^## (.+)$/);
      if (h2Match) {
        children.push(new Paragraph({
          text: stripMarkdownFormatting(h2Match[1]),
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 250, after: 120 },
        }));
        i++;
        continue;
      }

      const h3Match = line.match(/^### (.+)$/);
      if (h3Match) {
        children.push(new Paragraph({
          text: stripMarkdownFormatting(h3Match[1]),
          heading: HeadingLevel.HEADING_3,
          spacing: { before: 200, after: 100 },
        }));
        i++;
        continue;
      }

      const h4Match = line.match(/^#### (.+)$/);
      if (h4Match) {
        children.push(new Paragraph({
          text: stripMarkdownFormatting(h4Match[1]),
          heading: HeadingLevel.HEADING_4,
          spacing: { before: 150, after: 80 },
        }));
        i++;
        continue;
      }

      // Horizontal rule
      if (line.trim() === '---') {
        children.push(new Paragraph({
          children: [],
          border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' } },
          spacing: { before: 200, after: 200 },
        }));
        i++;
        continue;
      }

      // Blockquotes / GitHub alerts
      if (line.startsWith('> ')) {
        const quoteLines: string[] = [];
        while (i < lines.length && lines[i].startsWith('> ')) {
          quoteLines.push(lines[i].replace(/^> ?/, ''));
          i++;
        }
        const quoteText = quoteLines.filter(l => !l.startsWith('[!')).join(' ').trim();
        if (quoteText) {
          children.push(new Paragraph({
            children: makeTextRuns(quoteText),
            indent: { left: 400 },
            border: { left: { style: BorderStyle.SINGLE, size: 3, color: '4488CC' } },
            spacing: { before: 100, after: 100 },
          }));
        }
        continue;
      }

      // Bullet lists
      if (line.startsWith('- ')) {
        children.push(new Paragraph({
          children: makeTextRuns(line.slice(2)),
          bullet: { level: 0 },
          spacing: { before: 40, after: 40 },
        }));
        i++;
        continue;
      }

      // Numbered lists
      const numMatch = line.match(/^\d+\. (.+)$/);
      if (numMatch) {
        children.push(new Paragraph({
          children: makeTextRuns(numMatch[1]),
          numbering: { reference: 'default-numbering', level: 0 },
          spacing: { before: 40, after: 40 },
        }));
        i++;
        continue;
      }

      // Table blocks
      if (line.startsWith('|')) {
        const tableRows: string[] = [];
        while (i < lines.length && lines[i].startsWith('|')) {
          tableRows.push(lines[i]);
          i++;
        }
        const dataRows = tableRows.filter(r => !/^\|[\s-:|]+\|$/.test(r));
        if (dataRows.length > 0) {
          const docxRows = dataRows.map((row, rowIdx) => {
            const cells = row.split('|').filter((c, ci, arr) => ci > 0 && ci < arr.length - 1);
            return new TableRow({
              children: cells.map(cell =>
                new TableCell({
                  children: [
                    new Paragraph({
                      children: [new TextRun({
                        text: stripMarkdownFormatting(cell.trim()),
                        bold: rowIdx === 0,
                        size: rowIdx === 0 ? 20 : 18,
                        color: rowIdx === 0 ? '222222' : '444444',
                      })],
                    }),
                  ],
                  width: { size: Math.floor(100 / cells.length), type: WidthType.PERCENTAGE },
                  shading: rowIdx === 0
                    ? { type: docx.ShadingType.SOLID, fill: 'E8E8E8', color: 'E8E8E8' }
                    : rowIdx % 2 === 0
                      ? { type: docx.ShadingType.SOLID, fill: 'F9F9F9', color: 'F9F9F9' }
                      : undefined,
                })
              ),
            });
          });
          children.push(new Table({ rows: docxRows, width: { size: 100, type: WidthType.PERCENTAGE } }));
          children.push(new Paragraph({ children: [], spacing: { before: 100 } }));
        }
        continue;
      }

      // Regular paragraph
      children.push(new Paragraph({
        children: makeTextRuns(line),
        spacing: { before: 60, after: 60 },
      }));
      i++;
    }

    // Build document
    const doc = new Document({
      numbering: {
        config: [{
          reference: 'default-numbering',
          levels: [{
            level: 0,
            format: docx.LevelFormat.DECIMAL,
            text: '%1.',
            alignment: AlignmentType.START,
          }],
        }],
      },
      sections: [{
        properties: {
          page: {
            margin: { top: 1000, right: 1200, bottom: 1000, left: 1200 },
          },
        },
        children,
      }],
    });

    // Generate and download
    const buffer = await Packer.toBlob(doc);
    const safeFilename = filename.replace(/[^a-zA-Z0-9-_]/g, '-');
    const url = URL.createObjectURL(buffer);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeFilename}.docx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('DOCX generation failed:', err);
    throw new Error('Failed to generate DOCX. Please try downloading as PDF instead.');
  }
}
