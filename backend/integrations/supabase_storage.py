"""Supabase Storage client for file uploads.

Handles screenshot uploads to Supabase Storage with user isolation.
Also handles document storage (Doc 0/1/2/3) for research jobs.
Replaces local temp file storage for cloud-compatible deployment.

Based on: Plan 260116-2336 Storage Bucket Setup
Updated: 260117 - Added documents bucket for Doc 0/1/2/3 storage
"""
import json
from pathlib import Path
from typing import Optional
import uuid

from loguru import logger

# Bucket names
SCREENSHOTS_BUCKET = "screenshots"
DOCUMENTS_BUCKET = "documents"


class SupabaseStorageClient:
    """Client for Supabase Storage operations.

    Handles two buckets:
    - 'screenshots': User uploads with folder isolation {user_id}/{uuid}.{ext}
    - 'documents': Research job documents stored as {job_id}/doc_{n}.json
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
        self._screenshots_bucket = SCREENSHOTS_BUCKET
        self._documents_bucket = DOCUMENTS_BUCKET

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
            self._client.storage.from_(self._screenshots_bucket).upload(
                path=filename,
                file=file_content,
                file_options={"content-type": content_type}
            )

            logger.info(f"Uploaded screenshot: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to upload screenshot: {e}")
            raise

    def get_signed_url(self, path: str, expires_in: int = 3600, bucket: str | None = None) -> str:
        """Get a signed URL for temporary access.

        Args:
            path: Storage path
            expires_in: URL expiry in seconds (default 1 hour)
            bucket: Bucket name (defaults to screenshots)

        Returns:
            Signed URL string
        """
        target_bucket = bucket or self._screenshots_bucket
        result = self._client.storage.from_(target_bucket).create_signed_url(
            path=path,
            expires_in=expires_in
        )
        return result.get("signedURL", "")

    def download(self, path: str, bucket: str | None = None) -> bytes:
        """Download file content.

        Args:
            path: Storage path
            bucket: Bucket name (defaults to screenshots)

        Returns:
            File content as bytes
        """
        target_bucket = bucket or self._screenshots_bucket
        result = self._client.storage.from_(target_bucket).download(path)
        return result

    def delete(self, path: str, bucket: str | None = None) -> bool:
        """Delete file from storage.

        Args:
            path: Storage path
            bucket: Bucket name (defaults to screenshots)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            target_bucket = bucket or self._screenshots_bucket
            self._client.storage.from_(target_bucket).remove([path])
            logger.info(f"Deleted file: {path} from {target_bucket}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    # =========================================================================
    # Document Storage Methods (Doc 0/1/2/3)
    # =========================================================================

    def upload_document(self, job_id: str, doc_type: str, content: dict) -> str:
        """Upload document JSON to 'documents' bucket.

        Args:
            job_id: Job UUID
            doc_type: Document type ("doc_0", "doc_1", "doc_2", "doc_3")
            content: Document data as dict

        Returns:
            Storage path: "{job_id}/{doc_type}.json"

        Raises:
            Exception: If upload fails
        """
        filename = f"{job_id}/{doc_type}.json"
        json_content = json.dumps(content, indent=2, default=str)

        try:
            self._client.storage.from_(self._documents_bucket).upload(
                path=filename,
                file=json_content.encode("utf-8"),
                file_options={"content-type": "application/json"}
            )
            logger.info(f"Uploaded document: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to upload document {filename}: {e}")
            raise

    def get_document_url(self, path: str, expires_in: int = 3600) -> str:
        """Get signed URL for document from 'documents' bucket.

        Args:
            path: Storage path (e.g., "{job_id}/doc_0.json")
            expires_in: URL expiry in seconds (default 1 hour)

        Returns:
            Signed URL string
        """
        return self.get_signed_url(path, expires_in, bucket=self._documents_bucket)

    def download_document(self, path: str) -> dict:
        """Download and parse document JSON from 'documents' bucket.

        Args:
            path: Storage path (e.g., "{job_id}/doc_0.json")

        Returns:
            Parsed document data as dict
        """
        content = self.download(path, bucket=self._documents_bucket)
        return json.loads(content.decode("utf-8"))


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
        from backend.config import get_settings
        settings = get_settings()

        if not settings.supabase_url or not settings.supabase_service_role_key:
            logger.warning("Supabase not configured - storage client unavailable")
            return None

        _storage_client = SupabaseStorageClient(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    return _storage_client
