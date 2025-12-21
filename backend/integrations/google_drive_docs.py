"""Google Drive and Docs integration for research packet outputs."""
import json

from io import BytesIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from loguru import logger

from backend.config import require_google_oauth, MissingRequiredSettingError

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

# Document names to create
DOC_NAMES = [
    "00_MASTER_INDEX",
    "01_RESEARCH_MAP",
    "02_SOURCE_SHORTLIST",
    "03_YOUTUBE_INDEX",
    "04_TRANSCRIPTS",
    "05_WEB_EXTRACTS",
    "06_QUOTE_BANK",
    "07_CLAIMS_LEDGER",
    "08_EVIDENCE_TABLE",
    "09_MISSING_ANGLES",
]


def build_oauth_credentials(settings) -> Credentials:
    """
    Build and refresh Google OAuth2 credentials using refresh token.
    
    IMPORTANT: Always refreshes credentials before returning them.
    Do not check validity before refreshing, as credentials are created with token=None.
    
    Args:
        settings: Settings object with Google OAuth config
        
    Returns:
        Credentials object with valid access token
        
    Raises:
        RuntimeError: If credential refresh fails (includes the underlying exception message)
    """
    creds = Credentials(
        token=None,
        refresh_token=settings.google_oauth_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=SCOPES,
    )
    
    # IMPORTANT: refresh before any validity checks
    try:
        creds.refresh(Request())
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Failed to refresh Google OAuth token: {error_msg}")
        raise RuntimeError(f"Failed to refresh OAuth token: {error_msg}") from e
    
    return creds


# Backward compatibility alias
def _get_credentials(settings) -> Credentials:
    """
    Get Google OAuth2 credentials using refresh token.

    Deprecated: Use build_oauth_credentials() instead.
    Kept for backward compatibility.
    """
    return build_oauth_credentials(settings)


def validate_oauth_config() -> tuple[bool, str]:
    """
    Check if Google OAuth is properly configured and credentials are valid.

    Returns:
        Tuple of (is_valid, message) where message explains the status or error
    """
    from backend.config import get_settings

    settings = get_settings()

    # Check required settings
    if not settings.google_oauth_client_id:
        return False, "GOOGLE_OAUTH_CLIENT_ID not configured"
    if not settings.google_oauth_client_secret:
        return False, "GOOGLE_OAUTH_CLIENT_SECRET not configured"
    if not settings.google_oauth_refresh_token:
        return False, "GOOGLE_OAUTH_REFRESH_TOKEN not configured"

    # Try to refresh credentials
    try:
        creds = build_oauth_credentials(settings)
        if creds.valid:
            return True, "Google Drive connected successfully"
        else:
            return False, "OAuth credentials exist but are invalid"
    except Exception as e:
        error_msg = str(e)
        if "invalid_grant" in error_msg.lower():
            return False, "OAuth refresh token expired. Please re-authorize."
        elif "invalid_client" in error_msg.lower():
            return False, "OAuth client credentials are invalid."
        else:
            return False, f"OAuth error: {type(e).__name__}"


def _get_drive_service(creds: Credentials):
    """Get Google Drive API service."""
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_docs_service(creds: Credentials):
    """Get Google Docs API service."""
    return build("docs", "v1", credentials=creds, cache_discovery=False)


def _escape_drive_query(value: str) -> str:
    """
    Escape a string for use in Google Drive query strings.

    Single quotes must be escaped with a backslash in Drive API queries.
    See: https://developers.google.com/drive/api/v3/search-files

    Args:
        value: The string to escape

    Returns:
        Escaped string safe for use in Drive queries
    """
    # Escape backslashes first, then single quotes
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _get_or_create_user_folder(
    drive_service,
    user_id: str,
    parent_folder_id: str,
) -> str:
    """
    Get or create a user-specific subfolder in Google Drive.

    Args:
        drive_service: Google Drive API service
        user_id: User ID (first 8 chars used for folder name)
        parent_folder_id: ID of parent folder ("root" for root)

    Returns:
        Folder ID of the user folder
    """
    user_folder_name = f"user-{user_id[:8]}"
    escaped_name = _escape_drive_query(user_folder_name)

    # Build query with properly escaped name
    query = f"name='{escaped_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id != "root":
        query += f" and '{parent_folder_id}' in parents"

    results = drive_service.files().list(
        q=query,
        fields="files(id, webViewLink)",
        pageSize=1,
    ).execute()

    existing_folders = results.get("files", [])
    if existing_folders:
        folder_id = existing_folders[0].get("id")
        logger.info(f"Using existing user folder: {existing_folders[0].get('webViewLink')}")
        return folder_id

    # Create new user folder
    user_folder_metadata = {
        "name": user_folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_folder_id != "root":
        user_folder_metadata["parents"] = [parent_folder_id]

    logger.info(f"Creating user folder for user_id: {user_id[:8]}")
    user_folder = drive_service.files().create(
        body=user_folder_metadata,
        fields="id, webViewLink",
    ).execute()

    logger.info(f"Created user folder: {user_folder.get('webViewLink')}")
    return user_folder.get("id")


def create_research_packet(
    folder_name: str,
    doc_contents: dict[str, str],
    user_email: str | None = None,
    user_id: str | None = None,
) -> dict[str, str]:
    """
    Create a research packet in Google Drive with documents.

    Args:
        folder_name: Name of the folder to create
        doc_contents: Dict mapping doc names to markdown/text content
                      Keys should match DOC_NAMES (e.g., "00_MASTER_INDEX")
        user_email: Optional user email to share folder with
        user_id: Optional user ID to organize folders by user

    Returns:
        Dict with:
        - "folder_url": URL of the created folder
        - "doc_urls": Dict mapping doc names to URLs
        - "manifest_url": URL of manifest.json file

    Raises:
        MissingRequiredSettingError: If Google OAuth credentials are missing
        RuntimeError: If API operations fail
    """
    try:
        settings = require_google_oauth()
    except MissingRequiredSettingError as e:
        logger.warning(f"Google OAuth not configured: {e}")
        raise
    
    try:
        creds = _get_credentials(settings)
        drive_service = _get_drive_service(creds)
        docs_service = _get_docs_service(creds)

        # Determine parent folder
        parent_folder_id = settings.google_drive_root_folder_id or "root"

        # Create per-user subfolder if user_id provided
        if user_id:
            parent_folder_id = _get_or_create_user_folder(
                drive_service, user_id, parent_folder_id
            )

        # Create research folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_folder_id != "root":
            folder_metadata["parents"] = [parent_folder_id]

        logger.info(f"Creating folder '{folder_name}' in Drive")
        folder = drive_service.files().create(
            body=folder_metadata,
            fields="id, webViewLink",
        ).execute()

        folder_id = folder.get("id")
        folder_url = folder.get("webViewLink")

        logger.info(f"Created folder: {folder_url}")

        # Share folder with user if email provided
        if user_email:
            try:
                permission = {
                    "type": "user",
                    "role": "writer",  # User can edit documents
                    "emailAddress": user_email,
                }
                drive_service.permissions().create(
                    fileId=folder_id,
                    body=permission,
                    sendNotificationEmail=True,  # Notify user
                ).execute()
                logger.info(f"Shared folder with {user_email}")
            except HttpError as e:
                logger.warning(f"Failed to share folder with {user_email}: {e}")
                # Continue even if sharing fails
        
        # Create documents
        doc_urls: dict[str, str] = {}
        
        for doc_name in DOC_NAMES:
            # Create document
            doc_title = doc_name
            doc_metadata = {
                "name": doc_title,
                "mimeType": "application/vnd.google-apps.document",
                "parents": [folder_id],
            }
            
            logger.info(f"Creating document: {doc_title}")
            doc = drive_service.files().create(
                body=doc_metadata,
                fields="id, webViewLink",
            ).execute()
            
            doc_id = doc.get("id")
            doc_url = doc.get("webViewLink")
            doc_urls[doc_name] = doc_url
            
            # Insert content if provided
            content = doc_contents.get(doc_name, "")
            if content:
                # Convert markdown-ish formatting to plain text (Docs API doesn't handle markdown directly)
                # For now, insert as plain text
                text_content = content
                
                # Insert text at index 1 (after the default empty paragraph)
                requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": text_content,
                        }
                    }
                ]
                
                try:
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={"requests": requests},
                    ).execute()
                    logger.info(f"Inserted content into {doc_title}")
                except HttpError as e:
                    logger.warning(f"Failed to insert content into {doc_title}: {e}")
                    # Continue even if content insertion fails
        
        # Create manifest.json
        manifest = {
            "folder_name": folder_name,
            "folder_id": folder_id,
            "folder_url": folder_url,
            "documents": {
                doc_name: {
                    "url": doc_url,
                    "content_length": len(doc_contents.get(doc_name, "")),
                }
                for doc_name, doc_url in doc_urls.items()
            },
            "created_at": None,  # Could add timestamp if needed
        }
        
        # Upload manifest.json
        manifest_json = json.dumps(manifest, indent=2)
        manifest_metadata = {
            "name": "manifest.json",
            "parents": [folder_id],
            "mimeType": "application/json",
        }
        
        manifest_file = BytesIO(manifest_json.encode("utf-8"))
        media = MediaIoBaseUpload(manifest_file, mimetype="application/json", resumable=True)
        
        logger.info("Uploading manifest.json")
        manifest_doc = drive_service.files().create(
            body=manifest_metadata,
            media_body=media,
            fields="id, webViewLink",
        ).execute()
        
        manifest_url = manifest_doc.get("webViewLink")
        
        logger.info(f"Created research packet: {folder_url}")
        
        return {
            "folder_url": folder_url,
            "doc_urls": doc_urls,
            "manifest_url": manifest_url,
        }
    
    except HttpError as e:
        logger.exception(f"Google API error: {e}")
        raise RuntimeError(f"Google API error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error creating research packet: {e}")
        raise


def create_transcript_doc(
    title: str,
    content: str,
    user_email: str | None = None,
    user_id: str | None = None,
) -> dict[str, str]:
    """
    Create a Google Doc with transcript content.

    Creates a folder and a single document with the provided content.

    Args:
        title: Title for the document
        content: Plain text content to insert
        user_email: Optional user email to share folder with
        user_id: Optional user ID to organize folders by user

    Returns:
        Dict with:
        - "folder_url": URL of the created folder
        - "doc_url": URL of the created document

    Raises:
        MissingRequiredSettingError: If Google OAuth credentials are missing
        RuntimeError: If API operations fail
    """
    try:
        settings = require_google_oauth()
    except MissingRequiredSettingError as e:
        logger.warning(f"Google OAuth not configured: {e}")
        raise

    try:
        creds = _get_credentials(settings)
        drive_service = _get_drive_service(creds)
        docs_service = _get_docs_service(creds)

        # Determine parent folder
        parent_folder_id = settings.google_drive_root_folder_id or "root"

        # Create per-user subfolder if user_id provided
        if user_id:
            parent_folder_id = _get_or_create_user_folder(
                drive_service, user_id, parent_folder_id
            )

        # Create folder with timestamp
        from datetime import datetime
        folder_name = f"Transcripts - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_folder_id != "root":
            folder_metadata["parents"] = [parent_folder_id]

        logger.info(f"Creating folder '{folder_name}' in Drive")
        folder = drive_service.files().create(
            body=folder_metadata,
            fields="id, webViewLink",
        ).execute()

        folder_id = folder.get("id")
        folder_url = folder.get("webViewLink")

        logger.info(f"Created folder: {folder_url}")

        # Share folder with user if email provided
        if user_email:
            try:
                permission = {
                    "type": "user",
                    "role": "writer",
                    "emailAddress": user_email,
                }
                drive_service.permissions().create(
                    fileId=folder_id,
                    body=permission,
                    sendNotificationEmail=True,
                ).execute()
                logger.info(f"Shared folder with {user_email}")
            except HttpError as e:
                logger.warning(f"Failed to share folder with {user_email}: {e}")

        # Create document
        doc_metadata = {
            "name": title,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [folder_id],
        }

        logger.info(f"Creating document: {title}")
        doc = drive_service.files().create(
            body=doc_metadata,
            fields="id, webViewLink",
        ).execute()

        doc_id = doc.get("id")
        doc_url = doc.get("webViewLink")

        # Insert content
        if content:
            requests = [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": content,
                    }
                }
            ]

            try:
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": requests},
                ).execute()
                logger.info(f"Inserted content into {title}")
            except HttpError as e:
                logger.warning(f"Failed to insert content into {title}: {e}")

        logger.info(f"Created transcript doc: {doc_url}")

        return {
            "folder_url": folder_url,
            "doc_url": doc_url,
        }

    except HttpError as e:
        logger.exception(f"Google API error: {e}")
        raise RuntimeError(f"Google API error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error creating transcript doc: {e}")
        raise
