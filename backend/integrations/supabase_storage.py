"""Supabase Storage client for file uploads.

Handles screenshot uploads to Supabase Storage with user isolation.
Replaces local temp file storage for cloud-compatible deployment.

Based on: Plan 260116-2336 Storage Bucket Setup
"""
from pathlib import Path
from typing import Optional
import uuid

from loguru import logger


class SupabaseStorageClient:
    """Client for Supabase Storage operations.

    Uploads files to the 'screenshots' bucket with user-based folder isolation.
    Files are stored under {user_id}/{uuid}.{ext} for RLS policy enforcement.
    """

    def __init__(self, supabase_url: str, service_role_key: str):
        """Initialize storage client.

        Args:
            supabase_url: Supabase project URL
            service_role_key: Service role key for backend access
        """
        # Lazy import to avoid dependency issues
        from supabase import create_client

        self._client = create_client(supabase_url, service_role_key)
        self._bucket = "screenshots"

    def upload_screenshot(
        self,
        file_content: bytes,
        user_id: str,
        file_extension: str = ".png"
    ) -> str:
        """Upload screenshot to Supabase Storage.

        Args:
            file_content: Raw file bytes
            user_id: User ID for folder isolation
            file_extension: File extension (.png, .jpg, .webp)

        Returns:
            Storage path (e.g., "user123/abc-def-123.png")

        Raises:
            Exception: If upload fails
        """
        # Generate unique filename under user's folder
        clean_ext = file_extension.lstrip('.')
        filename = f"{user_id}/{uuid.uuid4()}.{clean_ext}"

        # Determine content type
        content_type_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }
        content_type = content_type_map.get(clean_ext.lower(), "image/png")

        try:
            # Upload to Supabase Storage
            self._client.storage.from_(self._bucket).upload(
                path=filename,
                file=file_content,
                file_options={"content-type": content_type}
            )

            logger.info(f"Uploaded screenshot: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to upload screenshot: {e}")
            raise

    def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for temporary access.

        Args:
            path: Storage path
            expires_in: URL expiry in seconds (default 1 hour)

        Returns:
            Signed URL string
        """
        result = self._client.storage.from_(self._bucket).create_signed_url(
            path=path,
            expires_in=expires_in
        )
        return result.get("signedURL", "")

    def download(self, path: str) -> bytes:
        """Download file content.

        Args:
            path: Storage path

        Returns:
            File content as bytes
        """
        result = self._client.storage.from_(self._bucket).download(path)
        return result

    def delete(self, path: str) -> bool:
        """Delete file from storage.

        Args:
            path: Storage path

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self._client.storage.from_(self._bucket).remove([path])
            logger.info(f"Deleted screenshot: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete screenshot: {e}")
            return False


# Singleton instance
_storage_client: Optional[SupabaseStorageClient] = None


def get_storage_client() -> Optional[SupabaseStorageClient]:
    """Get or create storage client singleton.

    Returns:
        SupabaseStorageClient instance or None if not configured
    """
    global _storage_client
    if _storage_client is None:
        # Import settings here to avoid circular imports
        from backend.config import settings

        if not settings.supabase_url or not settings.supabase_service_role_key:
            logger.warning("Supabase not configured - storage client unavailable")
            return None

        _storage_client = SupabaseStorageClient(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    return _storage_client
