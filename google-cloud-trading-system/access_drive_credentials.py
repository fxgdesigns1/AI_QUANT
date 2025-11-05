#!/usr/bin/env python3
"""
🔐 Access Google Drive Credentials for AI Quant Trading System
=============================================================

This script accesses your specific Google Drive folder and downloads
all the credentials needed for your AI quant trading system.

Target Folder: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT
"""

import os
import json
import yaml
import base64
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
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
    print("❌ Google APIs not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DriveCredentialAccessor:
    """Accesses credentials from your specific Google Drive folder."""
    
    # Your specific Google Drive folder ID
    FOLDER_ID = "1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT"
    
    # Google Drive API scopes
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
        
        # Expected credential files
        self.expected_files = [
            'accounts.yaml',
            'google_cloud_credentials.json',
            'oanda_config.env',
            'news_api_config.env',
            'telegram_config.env',
            'strategy_config.yaml',
            'config.yaml'
        ]
    
    def setup_oauth_credentials(self) -> bool:
        """Set up OAuth credentials for Google Drive API."""
        logger.info("🔧 Setting up Google Drive OAuth credentials...")
        
        creds_file = self.credentials_dir / 'gdrive_oauth_credentials.json'
        token_file = self.credentials_dir / 'gdrive_token.json'
        
        # Create OAuth credentials template
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
        logger.info("\n📋 To complete setup:")
        logger.info("1. Go to: https://console.cloud.google.com/")
        logger.info("2. Create a new project or select existing")
        logger.info("3. Enable Google Drive API")
        logger.info("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client ID'")
        logger.info("5. Choose 'Desktop application'")
        logger.info("6. Download the JSON file")
        logger.info("7. Replace the template in: credentials/gdrive_oauth_credentials.json")
        logger.info("8. Run: python access_drive_credentials.py --download")
        
        return False
    
    def authenticate_google_drive(self) -> Optional[Any]:
        """Authenticate with Google Drive API."""
        if not GOOGLE_APIS_AVAILABLE:
            return None
        
        creds = None
        token_file = self.credentials_dir / 'gdrive_token.json'
        oauth_file = self.credentials_dir / 'gdrive_oauth_credentials.json'
        
        # Load existing token
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not oauth_file.exists():
                    logger.error("❌ OAuth credentials file not found. Run --setup first.")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(str(oauth_file), self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
        
        return creds
    
    def list_folder_contents(self, service) -> List[Dict]:
        """List all files in the target Google Drive folder."""
        try:
            results = service.files().list(
                q=f"'{self.FOLDER_ID}' in parents",
                fields="files(id, name, mimeType, modifiedTime, size)",
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📁 Found {len(files)} files in your Google Drive folder:")
            
            for file in files:
                name = file['name']
                file_type = file.get('mimeType', 'Unknown')
                modified = file.get('modifiedTime', 'Unknown')
                size = file.get('size', 'Unknown')
                logger.info(f"  📄 {name} ({file_type}, {size} bytes, Modified: {modified})")
            
            return files
            
        except HttpError as e:
            logger.error(f"❌ Error listing folder contents: {e}")
            return []
    
    def download_file(self, service, file_id: str, filename: str) -> bool:
        """Download a specific file from Google Drive."""
        try:
            # Get file metadata
            file_metadata = service.files().get(fileId=file_id).execute()
            file_name = file_metadata.get('name', filename)
            
            # Download file content
            request = service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            # Determine local filename
            local_filename = self._determine_local_filename(file_name)
            local_path = self.credentials_dir / local_filename
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"✅ Downloaded: {file_name} → {local_filename}")
            return True
            
        except HttpError as e:
            logger.error(f"❌ Error downloading file {filename}: {e}")
            return False
    
    def _determine_local_filename(self, drive_filename: str) -> str:
        """Determine the local filename based on the Google Drive filename."""
        filename_lower = drive_filename.lower()
        
        # Map common Google Drive filenames to expected local names
        if 'account' in filename_lower and filename_lower.endswith('.yaml'):
            return 'accounts.yaml'
        elif 'google' in filename_lower and 'cloud' in filename_lower and filename_lower.endswith('.json'):
            return 'google_cloud_credentials.json'
        elif 'oanda' in filename_lower and filename_lower.endswith('.env'):
            return 'oanda_config.env'
        elif 'news' in filename_lower and filename_lower.endswith('.env'):
            return 'news_api_config.env'
        elif 'telegram' in filename_lower and filename_lower.endswith('.env'):
            return 'telegram_config.env'
        elif 'strategy' in filename_lower and filename_lower.endswith('.yaml'):
            return 'strategy_config.yaml'
        elif filename_lower.endswith('.yaml') and 'config' in filename_lower:
            return 'config.yaml'
        else:
            # Keep original name for unknown files
            return drive_filename
    
    def download_all_credentials(self) -> bool:
        """Download all credentials from your Google Drive folder."""
        if not GOOGLE_APIS_AVAILABLE:
            logger.error("❌ Google APIs not available")
            return False
        
        logger.info(f"📥 Downloading credentials from Google Drive folder: {self.FOLDER_ID}")
        
        # Authenticate
        creds = self.authenticate_google_drive()
        if not creds:
            return False
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # List folder contents
        files = self.list_folder_contents(service)
        if not files:
            logger.error("❌ No files found in the target folder")
            return False
        
        # Download each file
        success_count = 0
        total_files = len(files)
        
        for file in files:
            file_id = file['id']
            filename = file['name']
            
            if self.download_file(service, file_id, filename):
                success_count += 1
        
        # Create symbolic links
        if success_count > 0:
            self._create_symlinks()
            logger.info(f"✅ Successfully downloaded {success_count}/{total_files} files")
            
            # Test credentials
            self._test_credentials()
            return True
        else:
            logger.error("❌ No files were downloaded")
            return False
    
    def _create_symlinks(self):
        """Create symbolic links to make credentials accessible to the trading system."""
        try:
            # Link accounts.yaml
            accounts_src = self.credentials_dir / "accounts.yaml"
            accounts_dst = self.project_root / "accounts.yaml"
            
            if accounts_src.exists():
                if accounts_dst.exists() or accounts_dst.is_symlink():
                    accounts_dst.unlink()
                accounts_dst.symlink_to(accounts_src)
                logger.info("✅ Linked accounts.yaml")
            
            # Link strategy_config.yaml if it exists
            strategy_src = self.credentials_dir / "strategy_config.yaml"
            strategy_dst = self.project_root / "strategy_config.yaml"
            
            if strategy_src.exists():
                if strategy_dst.exists() or strategy_dst.is_symlink():
                    strategy_dst.unlink()
                strategy_dst.symlink_to(strategy_src)
                logger.info("✅ Linked strategy_config.yaml")
            
            # Link config.yaml if it exists
            config_src = self.credentials_dir / "config.yaml"
            config_dst = self.project_root / "config.yaml"
            
            if config_src.exists():
                if config_dst.exists() or config_dst.is_symlink():
                    config_dst.unlink()
                config_dst.symlink_to(config_src)
                logger.info("✅ Linked config.yaml")
            
            # Create .env file from individual env files
            self._create_env_file()
            
        except Exception as e:
            logger.error(f"❌ Error creating symbolic links: {e}")
    
    def _create_env_file(self):
        """Create a combined .env file from individual environment files."""
        env_content = f"""# AI Quant Trading System - Environment Credentials
# Generated from Google Drive on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        # Read individual env files and combine them
        env_files = ['oanda_config.env', 'news_api_config.env', 'telegram_config.env']
        
        for env_file in env_files:
            env_path = self.credentials_dir / env_file
            if env_path.exists():
                with open(env_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        env_content += f"# From {env_file}\n{content}\n\n"
        
        # Write combined .env file
        env_file = self.credentials_dir / ".env"
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        # Link .env file
        env_dst = self.project_root / ".env"
        if env_dst.exists() or env_dst.is_symlink():
            env_dst.unlink()
        env_dst.symlink_to(env_file)
        logger.info("✅ Created and linked .env file")
    
    def _test_credentials(self):
        """Test if the downloaded credentials are valid."""
        logger.info("🧪 Testing downloaded credentials...")
        
        tests = []
        
        # Test accounts.yaml
        accounts_file = self.credentials_dir / "accounts.yaml"
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as f:
                    accounts_data = yaml.safe_load(f)
                    if 'accounts' in accounts_data and accounts_data['accounts']:
                        tests.append(("accounts.yaml", True, f"Found {len(accounts_data['accounts'])} account(s)"))
                    else:
                        tests.append(("accounts.yaml", False, "No accounts found"))
            except Exception as e:
                tests.append(("accounts.yaml", False, f"Error: {e}"))
        else:
            tests.append(("accounts.yaml", False, "File not found"))
        
        # Test Google Cloud credentials
        gcp_file = self.credentials_dir / "google_cloud_credentials.json"
        if gcp_file.exists():
            try:
                with open(gcp_file, 'r') as f:
                    gcp_data = json.load(f)
                    if 'type' in gcp_data and gcp_data['type'] == 'service_account':
                        tests.append(("Google Cloud JSON", True, "Valid service account"))
                    else:
                        tests.append(("Google Cloud JSON", False, "Invalid format"))
            except Exception as e:
                tests.append(("Google Cloud JSON", False, f"Error: {e}"))
        else:
            tests.append(("Google Cloud JSON", False, "File not found"))
        
        # Test .env file
        env_file = self.project_root / ".env"
        if env_file.exists():
            tests.append((".env file", True, "Environment file created"))
        else:
            tests.append((".env file", False, "File not found"))
        
        # Display test results
        logger.info("📊 Credential Test Results:")
        for test_name, passed, message in tests:
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {test_name}: {message}")
        
        all_passed = all(passed for _, passed, _ in tests)
        if all_passed:
            logger.info("🎉 All credential tests passed!")
        else:
            logger.warning("⚠️  Some credential tests failed. Check the results above.")
        
        return all_passed
    
    def show_folder_info(self):
        """Show information about the target Google Drive folder."""
        logger.info(f"📁 Target Google Drive Folder:")
        logger.info(f"   ID: {self.FOLDER_ID}")
        logger.info(f"   URL: https://drive.google.com/drive/folders/{self.FOLDER_ID}")
        logger.info(f"   Expected files: {', '.join(self.expected_files)}")

def main():
    parser = argparse.ArgumentParser(description='Access Google Drive Credentials for AI Quant Trading')
    parser.add_argument('--setup', action='store_true', help='Set up Google Drive OAuth credentials')
    parser.add_argument('--download', action='store_true', help='Download all credentials from Google Drive')
    parser.add_argument('--list', action='store_true', help='List files in the Google Drive folder')
    parser.add_argument('--info', action='store_true', help='Show folder information')
    
    args = parser.parse_args()
    
    accessor = DriveCredentialAccessor()
    
    if args.setup:
        accessor.setup_oauth_credentials()
    elif args.download:
        accessor.download_all_credentials()
    elif args.list:
        if GOOGLE_APIS_AVAILABLE:
            creds = accessor.authenticate_google_drive()
            if creds:
                service = build('drive', 'v3', credentials=creds)
                accessor.list_folder_contents(service)
        else:
            logger.error("❌ Google APIs not available")
    elif args.info:
        accessor.show_folder_info()
    else:
        print("\n🔐 AI Quant Trading System - Google Drive Credential Access")
        print("=" * 70)
        print(f"Target Folder: https://drive.google.com/drive/folders/{accessor.FOLDER_ID}")
        print("\nAvailable commands:")
        print("  --setup     Set up Google Drive OAuth credentials")
        print("  --download  Download all credentials from Google Drive")
        print("  --list      List files in the Google Drive folder")
        print("  --info      Show folder information")
        print("\nRecommended workflow:")
        print("1. python access_drive_credentials.py --setup")
        print("2. python access_drive_credentials.py --download")

if __name__ == "__main__":
    main()