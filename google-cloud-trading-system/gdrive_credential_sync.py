#!/usr/bin/env python3
"""
☁️ Google Drive Credential Sync for AI Quant Trading System
==========================================================

This script provides direct access to your Google Drive credentials
without needing to manually download files.

Usage:
    python gdrive_credential_sync.py --setup
    python gdrive_credential_sync.py --download
    python gdrive_credential_sync.py --upload
"""

import os
import json
import yaml
import base64
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Google Drive API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    print("⚠️  Google APIs not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleDriveCredentialSync:
    """Syncs credentials with Google Drive."""
    
    # Google Drive API scopes
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
        
        # Google Drive folder path (update this to match your actual path)
        self.gdrive_folder_path = "AI Trading/Gits/AI_QUANT_credentials"
        
        # File mappings
        self.file_mappings = {
            'accounts.yaml': 'accounts.yaml',
            'google_cloud_credentials.json': 'google_cloud_credentials.json',
            'oanda_config.env': 'oanda_config.env',
            'news_api_config.env': 'news_api_config.env',
            'telegram_config.env': 'telegram_config.env'
        }
    
    def setup_google_drive_api(self) -> bool:
        """Set up Google Drive API authentication."""
        if not GOOGLE_APIS_AVAILABLE:
            logger.error("❌ Google APIs not available. Please install required packages.")
            return False
        
        logger.info("🔧 Setting up Google Drive API...")
        
        # Create credentials directory
        creds_file = self.credentials_dir / 'gdrive_credentials.json'
        token_file = self.credentials_dir / 'gdrive_token.json'
        
        # Check if we already have credentials
        if creds_file.exists() and token_file.exists():
            logger.info("✅ Google Drive API already configured")
            return True
        
        # Create OAuth credentials file template
        oauth_template = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        with open(creds_file, 'w') as f:
            json.dump(oauth_template, f, indent=2)
        
        logger.info(f"✅ OAuth template created: {creds_file}")
        logger.info("\n📋 Next steps to complete Google Drive API setup:")
        logger.info("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        logger.info("2. Create a new project or select existing one")
        logger.info("3. Enable Google Drive API")
        logger.info("4. Create OAuth 2.0 credentials (Desktop application)")
        logger.info("5. Download the JSON file and replace the template")
        logger.info("6. Run: python gdrive_credential_sync.py --download")
        
        return False
    
    def authenticate_google_drive(self) -> Optional[Any]:
        """Authenticate with Google Drive API."""
        if not GOOGLE_APIS_AVAILABLE:
            return None
        
        creds = None
        token_file = self.credentials_dir / 'gdrive_token.json'
        creds_file = self.credentials_dir / 'gdrive_credentials.json'
        
        # Load existing token
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_file.exists():
                    logger.error("❌ Google Drive credentials file not found. Run --setup first.")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
        
        return creds
    
    def find_folder_id(self, service, folder_name: str) -> Optional[str]:
        """Find Google Drive folder ID by name."""
        try:
            # Search for folders with the exact name
            results = service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name, parents)"
            ).execute()
            
            folders = results.get('files', [])
            
            if not folders:
                logger.error(f"❌ Folder '{folder_name}' not found in Google Drive")
                return None
            
            # If multiple folders found, try to find the one in the right path
            if len(folders) > 1:
                logger.warning(f"⚠️  Multiple folders named '{folder_name}' found. Using the first one.")
            
            return folders[0]['id']
            
        except HttpError as e:
            logger.error(f"❌ Error searching for folder: {e}")
            return None
    
    def find_file_in_folder(self, service, folder_id: str, filename: str) -> Optional[str]:
        """Find file ID within a specific folder."""
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and name='{filename}'",
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            return files[0]['id'] if files else None
            
        except HttpError as e:
            logger.error(f"❌ Error searching for file '{filename}': {e}")
            return None
    
    def download_file_from_drive(self, service, file_id: str, local_path: Path) -> bool:
        """Download a file from Google Drive."""
        try:
            # Get file metadata
            file_metadata = service.files().get(fileId=file_id).execute()
            file_name = file_metadata.get('name', 'unknown')
            
            # Download file content
            request = service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"✅ Downloaded: {file_name} -> {local_path}")
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error downloading file: {e}")
            return False
    
    def upload_file_to_drive(self, service, local_path: Path, folder_id: str) -> bool:
        """Upload a file to Google Drive."""
        try:
            file_name = local_path.name
            
            # Check if file already exists
            existing_file_id = self.find_file_in_folder(service, folder_id, file_name)
            
            # Prepare file metadata
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            # Upload file
            with open(local_path, 'rb') as f:
                file_content = f.read()
            
            if existing_file_id:
                # Update existing file
                service.files().update(
                    fileId=existing_file_id,
                    body=file_metadata,
                    media_body=file_content
                ).execute()
                logger.info(f"✅ Updated: {file_name}")
            else:
                # Create new file
                service.files().create(
                    body=file_metadata,
                    media_body=file_content
                ).execute()
                logger.info(f"✅ Uploaded: {file_name}")
            
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error uploading file: {e}")
            return False
    
    def download_credentials(self) -> bool:
        """Download all credentials from Google Drive."""
        if not GOOGLE_APIS_AVAILABLE:
            logger.error("❌ Google APIs not available")
            return False
        
        logger.info("📥 Downloading credentials from Google Drive...")
        
        # Authenticate
        creds = self.authenticate_google_drive()
        if not creds:
            return False
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # Find the credentials folder
        folder_id = self.find_folder_id(service, "AI_QUANT_credentials")
        if not folder_id:
            logger.error("❌ AI_QUANT_credentials folder not found in Google Drive")
            logger.info("💡 Make sure the folder exists and is named exactly 'AI_QUANT_credentials'")
            return False
        
        # Download each file
        success_count = 0
        total_files = len(self.file_mappings)
        
        for local_name, drive_name in self.file_mappings.items():
            file_id = self.find_file_in_folder(service, folder_id, drive_name)
            
            if file_id:
                local_path = self.credentials_dir / local_name
                if self.download_file_from_drive(service, file_id, local_path):
                    success_count += 1
            else:
                logger.warning(f"⚠️  File '{drive_name}' not found in Google Drive")
        
        # Create symbolic links
        if success_count > 0:
            self._create_symlinks()
            logger.info(f"✅ Downloaded {success_count}/{total_files} files successfully")
            return True
        else:
            logger.error("❌ No files were downloaded")
            return False
    
    def upload_credentials(self) -> bool:
        """Upload all credentials to Google Drive."""
        if not GOOGLE_APIS_AVAILABLE:
            logger.error("❌ Google APIs not available")
            return False
        
        logger.info("📤 Uploading credentials to Google Drive...")
        
        # Authenticate
        creds = self.authenticate_google_drive()
        if not creds:
            return False
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # Find or create the credentials folder
        folder_id = self.find_folder_id(service, "AI_QUANT_credentials")
        if not folder_id:
            logger.info("📁 Creating AI_QUANT_credentials folder...")
            try:
                folder_metadata = {
                    'name': 'AI_QUANT_credentials',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder.get('id')
                logger.info(f"✅ Created folder: AI_QUANT_credentials")
            except HttpError as e:
                logger.error(f"❌ Error creating folder: {e}")
                return False
        
        # Upload each file
        success_count = 0
        total_files = 0
        
        for local_name, drive_name in self.file_mappings.items():
            local_path = self.credentials_dir / local_name
            if local_path.exists():
                total_files += 1
                if self.upload_file_to_drive(service, local_path, folder_id):
                    success_count += 1
        
        if success_count > 0:
            logger.info(f"✅ Uploaded {success_count}/{total_files} files successfully")
            return True
        else:
            logger.error("❌ No files were uploaded")
            return False
    
    def _create_symlinks(self):
        """Create symbolic links to make credentials accessible."""
        try:
            # Link accounts.yaml
            accounts_src = self.credentials_dir / "accounts.yaml"
            accounts_dst = self.project_root / "accounts.yaml"
            
            if accounts_src.exists():
                if accounts_dst.exists() or accounts_dst.is_symlink():
                    accounts_dst.unlink()
                accounts_dst.symlink_to(accounts_src)
                logger.info(f"✅ Linked accounts.yaml")
            
            # Link .env file if it exists
            env_src = self.credentials_dir / ".env"
            env_dst = self.project_root / ".env"
            
            if env_src.exists():
                if env_dst.exists() or env_dst.is_symlink():
                    env_dst.unlink()
                env_dst.symlink_to(env_src)
                logger.info(f"✅ Linked .env")
                
        except Exception as e:
            logger.error(f"❌ Error creating symbolic links: {e}")
    
    def list_drive_files(self) -> bool:
        """List files in the Google Drive credentials folder."""
        if not GOOGLE_APIS_AVAILABLE:
            logger.error("❌ Google APIs not available")
            return False
        
        logger.info("📋 Listing files in Google Drive...")
        
        # Authenticate
        creds = self.authenticate_google_drive()
        if not creds:
            return False
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # Find the credentials folder
        folder_id = self.find_folder_id(service, "AI_QUANT_credentials")
        if not folder_id:
            logger.error("❌ AI_QUANT_credentials folder not found")
            return False
        
        # List files in folder
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                logger.info(f"📁 Files in AI_QUANT_credentials folder:")
                for file in files:
                    name = file['name']
                    modified = file.get('modifiedTime', 'Unknown')
                    size = file.get('size', 'Unknown')
                    logger.info(f"  📄 {name} (Modified: {modified}, Size: {size} bytes)")
            else:
                logger.info("📁 No files found in AI_QUANT_credentials folder")
            
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error listing files: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='AI Quant Google Drive Credential Sync')
    parser.add_argument('--setup', action='store_true', help='Set up Google Drive API')
    parser.add_argument('--download', action='store_true', help='Download credentials from Google Drive')
    parser.add_argument('--upload', action='store_true', help='Upload credentials to Google Drive')
    parser.add_argument('--list', action='store_true', help='List files in Google Drive folder')
    
    args = parser.parse_args()
    
    sync = GoogleDriveCredentialSync()
    
    if args.setup:
        sync.setup_google_drive_api()
    elif args.download:
        sync.download_credentials()
    elif args.upload:
        sync.upload_credentials()
    elif args.list:
        sync.list_drive_files()
    else:
        print("\n☁️ AI Quant Google Drive Credential Sync")
        print("=" * 50)
        print("Available commands:")
        print("  --setup     Set up Google Drive API authentication")
        print("  --download  Download credentials from Google Drive")
        print("  --upload    Upload credentials to Google Drive")
        print("  --list      List files in Google Drive folder")
        print("\nRecommended workflow:")
        print("1. python gdrive_credential_sync.py --setup")
        print("2. python gdrive_credential_sync.py --download")

if __name__ == "__main__":
    main()