-- Migration: Cleanup redundant fields
-- Description: Remove topic and result columns that duplicate data in config_json
-- Date: 2025-12-18

ALTER TABLE jobs DROP COLUMN IF EXISTS topic;
ALTER TABLE jobs DROP COLUMN IF EXISTS result;
