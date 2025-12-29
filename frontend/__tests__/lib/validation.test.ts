/**
 * Unit tests for validation utilities.
 */
import {
  validatePrompt,
  validateUsername,
  validateEmail,
  validateDriveFolderUrl,
  validateRequired,
  validateMaxLength,
} from '../../lib/validation';

describe('Validation Utilities', () => {
  describe('validatePrompt', () => {
    it('should reject empty prompts', () => {
      const result = validatePrompt('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('required');
    });

    it('should reject whitespace-only prompts', () => {
      const result = validatePrompt('   ');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('required');
    });

    it('should accept valid prompts', () => {
      const result = validatePrompt('Research AI ethics in healthcare');
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should reject prompts exceeding max length', () => {
      const longPrompt = 'a'.repeat(600);
      const result = validatePrompt(longPrompt);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('500');
    });

    it('should accept prompts at max length', () => {
      const maxPrompt = 'a'.repeat(500);
      const result = validatePrompt(maxPrompt);
      expect(result.valid).toBe(true);
    });
  });

  describe('validateUsername', () => {
    it('should reject empty usernames', () => {
      const result = validateUsername('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('required');
    });

    it('should reject short usernames', () => {
      const result = validateUsername('ab');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('at least 3');
    });

    it('should reject long usernames', () => {
      const result = validateUsername('a'.repeat(31));
      expect(result.valid).toBe(false);
      expect(result.error).toContain('30');
    });

    it('should reject invalid characters', () => {
      const result = validateUsername('user@name!');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('letters, numbers');
    });

    it('should accept valid usernames', () => {
      expect(validateUsername('valid_user-123').valid).toBe(true);
      expect(validateUsername('john_doe').valid).toBe(true);
      expect(validateUsername('User123').valid).toBe(true);
    });

    it('should accept usernames with underscores and hyphens', () => {
      expect(validateUsername('user_name').valid).toBe(true);
      expect(validateUsername('user-name').valid).toBe(true);
      expect(validateUsername('user_name-123').valid).toBe(true);
    });
  });

  describe('validateEmail', () => {
    it('should reject empty emails', () => {
      const result = validateEmail('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('required');
    });

    it('should reject invalid email formats', () => {
      expect(validateEmail('notanemail').valid).toBe(false);
      expect(validateEmail('missing@domain').valid).toBe(false);
      expect(validateEmail('@nodomain.com').valid).toBe(false);
    });

    it('should accept valid emails', () => {
      expect(validateEmail('user@example.com').valid).toBe(true);
      expect(validateEmail('user.name@example.co.uk').valid).toBe(true);
      expect(validateEmail('user+tag@example.com').valid).toBe(true);
    });
  });

  describe('validateDriveFolderUrl', () => {
    it('should reject empty URLs', () => {
      const result = validateDriveFolderUrl('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('required');
    });

    it('should reject non-Google Drive URLs', () => {
      const result = validateDriveFolderUrl('https://example.com/folder');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Google Drive');
    });

    it('should accept valid Google Drive folder URLs', () => {
      const validUrl = 'https://drive.google.com/drive/folders/1abc123DEF456';
      const result = validateDriveFolderUrl(validUrl);
      expect(result.valid).toBe(true);
    });

    it('should reject Google Drive file URLs', () => {
      const fileUrl = 'https://drive.google.com/file/d/1abc123/view';
      const result = validateDriveFolderUrl(fileUrl);
      expect(result.valid).toBe(false);
    });
  });

  describe('validateRequired', () => {
    it('should reject empty values', () => {
      const result = validateRequired('', 'Field name');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Field name');
      expect(result.error).toContain('required');
    });

    it('should reject whitespace-only values', () => {
      const result = validateRequired('   ', 'Topic');
      expect(result.valid).toBe(false);
    });

    it('should accept non-empty values', () => {
      const result = validateRequired('some value', 'Field');
      expect(result.valid).toBe(true);
    });
  });

  describe('validateMaxLength', () => {
    it('should accept values under max length', () => {
      const result = validateMaxLength('short', 100, 'Field');
      expect(result.valid).toBe(true);
    });

    it('should accept values at max length', () => {
      const result = validateMaxLength('12345', 5, 'Field');
      expect(result.valid).toBe(true);
    });

    it('should reject values exceeding max length', () => {
      const result = validateMaxLength('too long', 5, 'Field');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('5');
    });
  });
});
