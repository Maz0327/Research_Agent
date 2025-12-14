"""Test script for Google Drive and Docs integration."""
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import config first to trigger dotenv load
from backend.config import require_google_oauth, MissingRequiredSettingError
from backend.integrations.google_drive_docs import build_oauth_credentials

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger



def main():
    """Test Google Drive and Docs write functionality."""
    print("🔍 Checking Google OAuth configuration...")
    
    # Validate Google OAuth settings
    # require_google_oauth() will raise MissingRequiredSettingError with clear messages
    try:
        settings = require_google_oauth()
    except MissingRequiredSettingError as e:
        print("\n❌ Error: Missing required Google OAuth environment variables")
        print(f"\n{e}")
        print("\nPlease set the required variables in your .env file.")
        sys.exit(1)
    
    # Generate timestamped folder name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"TEST__google_write__{timestamp}"
    
    print(f"✅ Google OAuth configuration valid")
    print(f"\n📁 Creating folder: {folder_name}")
    
    if settings.google_drive_root_folder_id:
        print(f"   Parent folder ID: {settings.google_drive_root_folder_id}")
    else:
        print(f"   Parent folder: root")
    
    try:
        # Get and refresh credentials (build_oauth_credentials handles refresh)
        creds = build_oauth_credentials(settings)
        
        # Get services
        drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)
        
        # Determine parent folder
        parent_folder_id = settings.google_drive_root_folder_id or "root"
        
        # Create folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        
        if parent_folder_id != "root":
            folder_metadata["parents"] = [parent_folder_id]
        
        print("   Creating folder in Google Drive...")
        try:
            folder = drive_service.files().create(
                body=folder_metadata,
                fields="id, webViewLink",
            ).execute()
        except HttpError as e:
            # Check if it's a folder ID error (only when using a custom parent folder)
            if parent_folder_id != "root":
                # HttpError from googleapiclient has resp.status attribute
                try:
                    error_code = e.resp.status
                except (AttributeError, TypeError):
                    # Fallback if resp structure is different
                    error_code = None
                    error_str = str(e).lower()
                    if "404" in error_str or "not found" in error_str:
                        error_code = 404
                    elif "403" in error_str or "permission" in error_str or "forbidden" in error_str:
                        error_code = 403
                
                if error_code == 404:
                    print(f"\n❌ Error: Parent folder ID '{parent_folder_id}' not found")
                    print(f"   Please check that GOOGLE_DRIVE_ROOT_FOLDER_ID is correct")
                    print(f"   The folder ID must exist and be accessible with your credentials")
                    sys.exit(1)
                elif error_code == 403:
                    print(f"\n❌ Error: Permission denied for folder ID '{parent_folder_id}'")
                    print(f"   Please check that GOOGLE_DRIVE_ROOT_FOLDER_ID is correct")
                    print(f"   Your credentials must have write access to this folder")
                    sys.exit(1)
            # Re-raise if it's not a folder ID error or we're using root
            raise
        
        folder_id = folder.get("id")
        folder_url = folder.get("webViewLink")
        
        print(f"   ✅ Folder created")
        
        # Create single document: 00_MASTER_INDEX
        doc_name = "00_MASTER_INDEX"
        doc_metadata = {
            "name": doc_name,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [folder_id],
        }
        
        print(f"   Creating document: {doc_name}...")
        doc = drive_service.files().create(
            body=doc_metadata,
            fields="id, webViewLink",
        ).execute()
        
        doc_id = doc.get("id")
        doc_url = doc.get("webViewLink")
        
        # Insert text "hello world"
        print(f"   Inserting text into document...")
        text_content = "hello world"
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": text_content,
                }
            }
        ]
        
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
        
        print(f"   ✅ Document created and text inserted")
        
        # Print results
        print("\n" + "=" * 60)
        print("✅ Successfully created Google Drive folder and document")
        print("=" * 60)
        print(f"\n📁 Folder URL: {folder_url}")
        print(f"\n📄 Document URL:")
        print(f"  {doc_name}: {doc_url}")
        print()
        
    except HttpError as e:
        # This catches any other HttpErrors not handled above
        try:
            error_code = e.resp.status
        except (AttributeError, TypeError):
            error_code = "unknown"
        
        logger.exception(f"Google API error: {e}")
        print(f"\n❌ Error: Google API error (HTTP {error_code})")
        print(f"   {e}")
        sys.exit(1)
    except RuntimeError as e:
        # Handle OAuth credential errors with clear messages
        if "Failed to refresh OAuth token" in str(e):
            logger.exception(f"OAuth credential error: {e}")
            print(f"\n❌ Error: Failed to refresh Google OAuth credentials")
            print(f"   {type(e).__name__}: {e}")
            print(f"\n   Please check that your OAuth credentials are correct:")
            print(f"   - GOOGLE_OAUTH_CLIENT_ID")
            print(f"   - GOOGLE_OAUTH_CLIENT_SECRET")
            print(f"   - GOOGLE_OAUTH_REFRESH_TOKEN")
            sys.exit(1)
        else:
            # Re-raise other RuntimeErrors
            raise
    except Exception as e:
        logger.exception(f"Failed to create Google Drive folder/document: {e}")
        print(f"\n❌ Error: Failed to create Google Drive folder/document")
        print(f"   {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

