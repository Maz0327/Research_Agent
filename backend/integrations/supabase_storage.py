"""Supabase Storage client for file uploads.

Handles screenshot uploads to Supabase Storage with user isolation.
Also handles document storage (Doc 0/1/2/3) for research jobs.
Replaces local temp file storage for cloud-compatible deployment.

Based on: Plan 260116-2336 Storage Bucket Setup
Updated: 260117 - Added documents bucket for Doc 0/1/2/3 storage
Updated: 260119 - Added attachments storage for exports 12-17 and PDF
"""
import json
from pathlib import Path
from typing import Optional, TypedDict
import uuid

from loguru import logger

# Bucket names
SCREENSHOTS_BUCKET = "screenshots"
DOCUMENTS_BUCKET = "documents"

# Content type mapping for attachments
ATTACHMENT_CONTENT_TYPES = {
    ".json": "application/json",
    ".bib": "application/x-bibtex",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


class AttachmentUploadResult(TypedDict):
    """Result of attachment upload."""
    storage_path: str
    signed_url: str
    bucket: str


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
    # Generic File Storage Methods (used by version_manager)
    # =========================================================================

    def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        bucket: str | None = None,
    ) -> str:
        """Upload raw bytes to an arbitrary storage path.

        Unlike upload_document() which builds paths from job_id/doc_type,
        this method accepts a pre-built path. Used by version_manager for
        versioned document storage.

        Args:
            path: Full storage path (e.g., "research-jobs/{job_id}/doc_3/v1.json").
            content: Raw file bytes.
            content_type: MIME content type.
            bucket: Bucket name (defaults to documents bucket).

        Returns:
            The storage path that was written.

        Raises:
            Exception: If upload fails.
        """
        target_bucket = bucket or self._documents_bucket
        try:
            self._client.storage.from_(target_bucket).upload(
                path=path,
                file=content,
                file_options={"content-type": content_type},
            )
            logger.info(f"Uploaded file: {path} to {target_bucket}")
            return path
        except Exception as e:
            logger.error(f"Failed to upload file {path}: {e}")
            raise

    def delete_file(self, path: str, bucket: str | None = None) -> bool:
        """Delete a file at an arbitrary storage path.

        Unlike delete() which defaults to the screenshots bucket,
        this method defaults to the documents bucket. Used by
        version_manager for rolling window cleanup.

        Args:
            path: Full storage path to delete.
            bucket: Bucket name (defaults to documents bucket).

        Returns:
            True if deleted successfully, False otherwise.
        """
        target_bucket = bucket or self._documents_bucket
        try:
            self._client.storage.from_(target_bucket).remove([path])
            logger.info(f"Deleted file: {path} from {target_bucket}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
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

    # =========================================================================
    # Attachment Storage Methods (Exports 12-17, PDF)
    # =========================================================================

    def upload_attachment(
        self,
        job_id: str,
        filename: str,
        content: str | bytes,
        expires_in: int = 3600,
    ) -> AttachmentUploadResult:
        """Upload attachment to 'documents' bucket under research/{job_id}/attachments/.

        Args:
            job_id: Job UUID
            filename: Filename (e.g., "12_RESEARCH_DATA.json", "download.pdf")
            content: File content as string or bytes
            expires_in: Signed URL expiry in seconds (default 1 hour)

        Returns:
            AttachmentUploadResult with storage_path, signed_url, bucket

        Raises:
            Exception: If upload fails
        """
        # Build deterministic storage path
        storage_path = f"research/{job_id}/attachments/{filename}"

        # Determine content type from extension
        ext = Path(filename).suffix.lower()
        content_type = ATTACHMENT_CONTENT_TYPES.get(ext, "application/octet-stream")

        # Convert string to bytes if needed
        if isinstance(content, str):
            file_bytes = content.encode("utf-8")
        else:
            file_bytes = content

        try:
            # Upload to documents bucket
            self._client.storage.from_(self._documents_bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            logger.info(f"Uploaded attachment: {storage_path}")

            # Generate signed URL
            signed_url = self.get_signed_url(
                storage_path,
                expires_in=expires_in,
                bucket=self._documents_bucket
            )

            return AttachmentUploadResult(
                storage_path=storage_path,
                signed_url=signed_url,
                bucket=self._documents_bucket,
            )

        except Exception as e:
            logger.error(f"Failed to upload attachment {storage_path}: {e}")
            raise

    def get_attachment_url(
        self,
        job_id: str,
        filename: str,
        expires_in: int = 3600,
    ) -> str:
        """Get signed URL for attachment.

        Args:
            job_id: Job UUID
            filename: Filename (e.g., "12_RESEARCH_DATA.json")
            expires_in: URL expiry in seconds (default 1 hour)

        Returns:
            Signed URL string
        """
        storage_path = f"research/{job_id}/attachments/{filename}"
        return self.get_signed_url(storage_path, expires_in, bucket=self._documents_bucket)

    def attachment_exists(self, job_id: str, filename: str) -> bool:
        """Check if attachment exists in storage.

        Args:
            job_id: Job UUID
            filename: Filename to check

        Returns:
            True if exists, False otherwise
        """
        storage_path = f"research/{job_id}/attachments/{filename}"
        try:
            # Try to get metadata (list with prefix)
            result = self._client.storage.from_(self._documents_bucket).list(
                path=f"research/{job_id}/attachments",
                options={"search": filename}
            )
            return any(f.get("name") == filename for f in result)
        except Exception:
            return False

    def download_attachment(self, job_id: str, filename: str) -> bytes:
        """Download attachment content.

        Args:
            job_id: Job UUID
            filename: Filename to download

        Returns:
            File content as bytes
        """
        storage_path = f"research/{job_id}/attachments/{filename}"
        return self.download(storage_path, bucket=self._documents_bucket)


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
