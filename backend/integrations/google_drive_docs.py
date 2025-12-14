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


def _get_credentials(settings) -> Credentials:
    """
    Get Google OAuth2 credentials using refresh token.
    
    Args:
        settings: Settings object with Google OAuth config
        
    Returns:
        Credentials object
        
    Raises:
        MissingRequiredSettingError: If OAuth credentials are missing
    """
    creds = Credentials(
        token=None,
        refresh_token=settings.google_oauth_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=SCOPES,
    )
    
    # Refresh the token if needed
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh Google OAuth token: {e}")
                raise RuntimeError(f"Failed to refresh OAuth token: {e}")
        else:
            raise RuntimeError("Invalid OAuth credentials")
    
    return creds


def _get_drive_service(creds: Credentials):
    """Get Google Drive API service."""
    return build("drive", "v3", credentials=creds)


def _get_docs_service(creds: Credentials):
    """Get Google Docs API service."""
    return build("docs", "v1", credentials=creds)


def create_research_packet(
    folder_name: str,
    doc_contents: dict[str, str],
) -> dict[str, str]:
    """
    Create a research packet in Google Drive with documents.
    
    Args:
        folder_name: Name of the folder to create
        doc_contents: Dict mapping doc names to markdown/text content
                      Keys should match DOC_NAMES (e.g., "00_MASTER_INDEX")
        
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
        
        # Create folder
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

