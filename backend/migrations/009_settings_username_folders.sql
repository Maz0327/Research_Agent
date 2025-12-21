-- Migration: Add username and multi-folder support to user_settings
-- Created: 2024-12-20

-- Add username column with unique constraint
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS username VARCHAR(30) UNIQUE;
CREATE INDEX IF NOT EXISTS idx_user_settings_username ON user_settings(username);

-- Add multi-folder support
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS drive_folders JSONB DEFAULT '[]'::jsonb;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS default_folder_id VARCHAR(100);

-- Add is_banned flag for user moderation
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT false;
CREATE INDEX IF NOT EXISTS idx_user_settings_is_banned ON user_settings(is_banned) WHERE is_banned = true;

-- Migrate existing single folder to array (run once, safe to re-run)
UPDATE user_settings
SET drive_folders = jsonb_build_array(
    jsonb_build_object(
        'folder_id', drive_folder_id,
        'folder_name', NULL,
        'is_default', true,
        'added_at', NOW()
    )
),
default_folder_id = drive_folder_id
WHERE drive_folder_id IS NOT NULL
  AND drive_folder_id != ''
  AND (drive_folders IS NULL OR drive_folders = '[]'::jsonb);
