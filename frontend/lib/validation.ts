/**
 * Form validation utilities for consistent validation across the frontend.
 */

import { VALIDATION_LIMITS } from './constants';

/** Validation result with error message */
export interface ValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validate research topic/prompt.
 */
export function validatePrompt(prompt: string): ValidationResult {
  const trimmed = prompt.trim();

  if (!trimmed) {
    return { valid: false, error: 'Research topic is required' };
  }

  if (trimmed.length > VALIDATION_LIMITS.MAX_PROMPT_LENGTH) {
    return {
      valid: false,
      error: `Topic must be ${VALIDATION_LIMITS.MAX_PROMPT_LENGTH} characters or less`,
    };
  }

  return { valid: true };
}

/**
 * Validate username.
 */
export function validateUsername(username: string): ValidationResult {
  const trimmed = username.trim();

  if (!trimmed) {
    return { valid: false, error: 'Username is required' };
  }

  if (trimmed.length < VALIDATION_LIMITS.MIN_USERNAME_LENGTH) {
    return {
      valid: false,
      error: `Username must be at least ${VALIDATION_LIMITS.MIN_USERNAME_LENGTH} characters`,
    };
  }

  if (trimmed.length > VALIDATION_LIMITS.MAX_USERNAME_LENGTH) {
    return {
      valid: false,
      error: `Username must be ${VALIDATION_LIMITS.MAX_USERNAME_LENGTH} characters or less`,
    };
  }

  // Only allow alphanumeric, underscores, and hyphens
  if (!/^[a-zA-Z0-9_-]+$/.test(trimmed)) {
    return {
      valid: false,
      error: 'Username can only contain letters, numbers, underscores, and hyphens',
    };
  }

  return { valid: true };
}

/**
 * Validate Google Drive folder URL.
 */
export function validateDriveFolderUrl(url: string): ValidationResult {
  const trimmed = url.trim();

  if (!trimmed) {
    return { valid: false, error: 'Folder URL is required' };
  }

  // Check if it's a valid Google Drive folder URL
  const driveUrlPattern = /^https:\/\/drive\.google\.com\/drive\/folders\/[a-zA-Z0-9_-]+/;
  if (!driveUrlPattern.test(trimmed)) {
    return {
      valid: false,
      error: 'Please enter a valid Google Drive folder URL',
    };
  }

  return { valid: true };
}

/**
 * Validate email address.
 */
export function validateEmail(email: string): ValidationResult {
  const trimmed = email.trim();

  if (!trimmed) {
    return { valid: false, error: 'Email is required' };
  }

  // Basic email pattern validation
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(trimmed)) {
    return { valid: false, error: 'Please enter a valid email address' };
  }

  return { valid: true };
}

/**
 * Generic required field validation.
 */
export function validateRequired(value: string, fieldName: string): ValidationResult {
  if (!value.trim()) {
    return { valid: false, error: `${fieldName} is required` };
  }
  return { valid: true };
}

/**
 * Validate a field with max length.
 */
export function validateMaxLength(
  value: string,
  maxLength: number,
  fieldName: string
): ValidationResult {
  if (value.length > maxLength) {
    return {
      valid: false,
      error: `${fieldName} must be ${maxLength} characters or less`,
    };
  }
  return { valid: true };
}
