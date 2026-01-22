/**
 * Tests for document presentation layer formatters.
 */
import {
  formatInternalId,
  formatIdWithRef,
  formatTimestamp,
  transformMarkdownForDisplay,
  getConfidenceDisplay,
  getSourceTypeDisplay,
} from '@/lib/document-formatters';

describe('formatInternalId', () => {
  it('converts SRC_1 to "Source 1"', () => {
    expect(formatInternalId('SRC_1')).toBe('Source 1');
  });

  it('converts KP_12 to "Key Point 12"', () => {
    expect(formatInternalId('KP_12')).toBe('Key Point 12');
  });

  it('converts GAP_3 to "Open Question 3"', () => {
    expect(formatInternalId('GAP_3')).toBe('Open Question 3');
  });

  it('converts THEME_2 to "Theme 2"', () => {
    expect(formatInternalId('THEME_2')).toBe('Theme 2');
  });

  it('converts CLM_5 to "Claim 5"', () => {
    expect(formatInternalId('CLM_5')).toBe('Claim 5');
  });

  it('converts QT_7 to "Quote 7"', () => {
    expect(formatInternalId('QT_7')).toBe('Quote 7');
  });

  it('converts TEN_1 to "Tension 1"', () => {
    expect(formatInternalId('TEN_1')).toBe('Tension 1');
  });

  it('passes through unknown IDs unchanged', () => {
    expect(formatInternalId('unknown')).toBe('unknown');
    expect(formatInternalId('UNKNOWN_1')).toBe('UNKNOWN_1');
    expect(formatInternalId('')).toBe('');
  });
});

describe('formatIdWithRef', () => {
  it('shows both friendly label and internal ID', () => {
    expect(formatIdWithRef('SRC_1')).toBe('Source 1 (SRC_1)');
    expect(formatIdWithRef('KP_5')).toBe('Key Point 5 (KP_5)');
  });

  it('passes through unknown IDs unchanged', () => {
    expect(formatIdWithRef('unknown')).toBe('unknown');
  });
});

describe('formatTimestamp', () => {
  it('formats valid ISO date string', () => {
    const result = formatTimestamp('2026-01-15T10:30:00Z');
    expect(result).toMatch(/Jan 15, 2026/);
  });

  it('returns empty string for null/undefined', () => {
    expect(formatTimestamp(null)).toBe('');
    expect(formatTimestamp(undefined)).toBe('');
  });

  it('returns empty string for invalid date', () => {
    expect(formatTimestamp('not-a-date')).toBe('');
  });
});

describe('transformMarkdownForDisplay', () => {
  it('replaces SRC_1 with Source 1 in markdown', () => {
    const input = '## Sources\n\n**SRC_1** - Video title\n\nSee SRC_2 for more.';
    const result = transformMarkdownForDisplay(input);
    expect(result).toContain('Source 1');
    expect(result).toContain('Source 2');
    expect(result).not.toContain('SRC_1');
    expect(result).not.toContain('SRC_2');
  });

  it('replaces KP_1 with Key Point 1', () => {
    const input = 'As noted in KP_1, the main argument...';
    const result = transformMarkdownForDisplay(input);
    expect(result).toContain('Key Point 1');
    expect(result).not.toContain('KP_1');
  });

  it('replaces GAP_1 with Open Question 1', () => {
    const input = 'GAP_1: What is the impact?';
    const result = transformMarkdownForDisplay(input);
    expect(result).toContain('Open Question 1');
    expect(result).not.toContain('GAP_1');
  });

  it('normalizes section headings', () => {
    const input = '## Key Points\n\nSome content\n\n## Research Gaps\n\nMore content';
    const result = transformMarkdownForDisplay(input);
    expect(result).toContain('Key Takeaways');
    expect(result).toContain('Open Questions');
  });

  it('does not modify URLs containing IDs', () => {
    const input = 'See https://example.com/SRC_1/details for more.';
    const result = transformMarkdownForDisplay(input);
    // URL should be preserved (ID within URL path should not be transformed)
    expect(result).toContain('https://example.com/SRC_1/details');
  });

  it('handles empty/null input gracefully', () => {
    expect(transformMarkdownForDisplay('')).toBe('');
    expect(transformMarkdownForDisplay(null as unknown as string)).toBe(null);
  });
});

describe('getConfidenceDisplay', () => {
  it('returns correct display for high confidence', () => {
    const result = getConfidenceDisplay('high');
    expect(result.label).toBe('High Confidence');
    expect(result.color).toContain('green');
  });

  it('returns correct display for medium confidence', () => {
    const result = getConfidenceDisplay('medium');
    expect(result.label).toBe('Medium Confidence');
    expect(result.color).toContain('yellow');
  });

  it('returns correct display for low confidence', () => {
    const result = getConfidenceDisplay('low');
    expect(result.label).toBe('Low Confidence');
    expect(result.color).toContain('orange');
  });

  it('handles case insensitivity', () => {
    expect(getConfidenceDisplay('HIGH').label).toBe('High Confidence');
    expect(getConfidenceDisplay('Medium').label).toBe('Medium Confidence');
  });
});

describe('getSourceTypeDisplay', () => {
  it('returns correct display for youtube', () => {
    const result = getSourceTypeDisplay('youtube');
    expect(result.label).toBe('Video');
    expect(result.icon).toBe('video');
  });

  it('returns correct display for article', () => {
    const result = getSourceTypeDisplay('article');
    expect(result.label).toBe('Article');
    expect(result.icon).toBe('document');
  });

  it('returns correct display for reddit', () => {
    const result = getSourceTypeDisplay('reddit');
    expect(result.label).toBe('Reddit');
    expect(result.icon).toBe('chat');
  });
});
