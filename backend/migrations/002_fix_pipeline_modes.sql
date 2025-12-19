-- Migration: Fix pipeline modes constraint
-- Description: Update pipeline constraint to support 4 documentary modes
-- Date: 2025-12-18

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_pipeline_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_pipeline_check
  CHECK (pipeline IN ('breaking_news', 'investigation', 'profile', 'controversy'));
