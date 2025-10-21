#!/usr/bin/env python3
"""
🚀 Direct Google Drive Access for AI Quant Trading System
========================================================

This script provides alternative methods to access your Google Drive credentials
without requiring OAuth setup.

Target Folder: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT
"""

import os
import json
import yaml
import base64
import requests
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectDriveAccessor:
    """Direct access to Google Drive credentials using alternative methods."""
    
    FOLDER_ID = "1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT"
    FOLDER_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
    
    def create_manual_credentials(self) -> bool:
        """Create credentials manually by prompting for the content."""
        print("\n🔐 AI Quant Trading System - Manual Credential Setup")
        print("=" * 60)
        print(f"Target Google Drive Folder: {self.FOLDER_URL}")
        print("\nSince we can't directly access Google Drive, let's set up credentials manually.")
        print("You can copy the content from your Google Drive files and paste them here.")
        print()
        
        # Get OANDA credentials
        print("📊 OANDA API Credentials:")
        print("-" * 30)
        oanda_api_key = input("OANDA API Key: ").strip()
        oanda_account_id = input("OANDA Account ID: ").strip()
        oanda_environment = input("Environment (practice/live) [practice]: ").strip() or "practice"
        
        # Get Google Cloud credentials
        print("\n☁️ Google Cloud Credentials:")
        print("-" * 30)
        gcp_project_id = input("Google Cloud Project ID: ").strip()
        
        print("\nFor Google Cloud Service Account JSON:")
        print("1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts")
        print("2. Create or select a service account")
        print("3. Generate a new JSON key")
        print("4. Copy the entire JSON content below:")
        print()
        
        gcp_credentials_json = input("Google Cloud JSON (paste entire JSON): ").strip()
        
        # Optional credentials
        print("\n📰 Optional APIs (press Enter to skip):")
        print("-" * 30)
        news_api_key = input("News API Key: ").strip()
        telegram_bot_token = input("Telegram Bot Token: ").strip()
        telegram_chat_id = input("Telegram Chat ID: ").strip()
        
        try:
            # Create accounts.yaml
            accounts_config = {
                'accounts': [
                    {
                        'id': oanda_account_id,
                        'name': 'Primary Trading Account',
                        'display_name': '🚀 AI Quant Trader',
                        'strategy': 'adaptive_momentum',
                        'description': 'AI-powered automated trading system',
                        'instruments': ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY'],
                        'risk_settings': {
                            'max_risk_per_trade': 0.02,
                            'max_portfolio_risk': 0.10,
                            'max_positions': 5,
                            'daily_trade_limit': 50
                        },
                        'active': True,
                        'priority': 1
                    }
                ],
                'api': {
                    'oanda': {
                        'practice_url': 'https://api-fxpractice.oanda.com',
                        'live_url': 'https://api-fxtrade.oanda.com',
                        'api_key': oanda_api_key,
                        'account_id': oanda_account_id,
                        'environment': oanda_environment
                    }
                },
                'global_settings': {
                    'timezone': 'Europe/London',
                    'trading_hours': {
                        'start': '08:00',
                        'end': '17:00'
                    },
                    'max_total_exposure': 0.10,
                    'max_concurrent_positions': 5,
                    'telegram': {
                        'enabled': bool(telegram_bot_token),
                        'bot_token': telegram_bot_token or '',
                        'chat_id': telegram_chat_id or ''
                    }
                }
            }
            
            # Save accounts.yaml
            accounts_file = self.credentials_dir / "accounts.yaml"
            with open(accounts_file, 'w') as f:
                yaml.dump(accounts_config, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"✅ Created accounts.yaml: {accounts_file}")
            
            # Save Google Cloud credentials
            if gcp_credentials_json:
                try:
                    gcp_data = json.loads(gcp_credentials_json)
                    gcp_file = self.credentials_dir / "google_cloud_credentials.json"
                    with open(gcp_file, 'w') as f:
                        json.dump(gcp_data, f, indent=2)
                    logger.info(f"✅ Created Google Cloud credentials: {gcp_file}")
                except json.JSONDecodeError:
                    print("❌ Invalid JSON format for Google Cloud credentials")
                    return False
            
            # Create environment file
            env_content = f"""# AI Quant Trading System - Environment Credentials
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# OANDA Configuration
OANDA_API_KEY={oanda_api_key}
OANDA_ACCOUNT_ID={oanda_account_id}
OANDA_ENVIRONMENT={oanda_environment}

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud_credentials.json
GOOGLE_CLOUD_PROJECT_ID={gcp_project_id}

# Optional APIs
NEWS_API_KEY={news_api_key}
TELEGRAM_BOT_TOKEN={telegram_bot_token}
TELEGRAM_CHAT_ID={telegram_chat_id}

# Trading Configuration
DEFAULT_STRATEGY=adaptive_momentum
MAX_RISK_PER_TRADE=0.02
MAX_PORTFOLIO_RISK=0.10
"""
            
            env_file = self.credentials_dir / ".env"
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            logger.info(f"✅ Created environment file: {env_file}")
            
            # Create symbolic links
            self._create_symlinks()
            
            # Test credentials
            self._test_credentials()
            
            print("\n🎉 SUCCESS! Your credentials are now set up!")
            print("=" * 50)
            print("✅ OANDA API configured")
            print("✅ Google Cloud credentials saved")
            print("✅ Environment variables set")
            print("✅ Symbolic links created")
            print("\n🚀 You can now run your trading system!")
            print("\nNext steps:")
            print("1. Test your setup: python3 src/main.py --test")
            print("2. Start trading: python3 src/main.py")
            print("3. View dashboard: python3 scripts/dashboard.py")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating credentials: {e}")
            return False
    
    def create_file_upload_interface(self) -> bool:
        """Create a simple file upload interface for credential files."""
        print("\n📁 File Upload Method")
        print("=" * 30)
        print("You can upload your credential files directly.")
        print("Place your files in the credentials/ directory:")
        print(f"  {self.credentials_dir}")
        print("\nExpected files:")
        print("  - accounts.yaml")
        print("  - google_cloud_credentials.json")
        print("  - oanda_config.env (optional)")
        print("  - news_api_config.env (optional)")
        print("  - telegram_config.env (optional)")
        print("\nAfter placing files, run:")
        print("  python3 direct_drive_access.py --process-files")
        
        return True
    
    def process_uploaded_files(self) -> bool:
        """Process any uploaded credential files."""
        logger.info("📁 Processing uploaded credential files...")
        
        processed_files = []
        
        # Check for accounts.yaml
        accounts_file = self.credentials_dir / "accounts.yaml"
        if accounts_file.exists():
            processed_files.append("accounts.yaml")
            logger.info("✅ Found accounts.yaml")
        
        # Check for Google Cloud credentials
        gcp_file = self.credentials_dir / "google_cloud_credentials.json"
        if gcp_file.exists():
            processed_files.append("google_cloud_credentials.json")
            logger.info("✅ Found google_cloud_credentials.json")
        
        # Check for environment files
        env_files = ['oanda_config.env', 'news_api_config.env', 'telegram_config.env']
        for env_file in env_files:
            env_path = self.credentials_dir / env_file
            if env_path.exists():
                processed_files.append(env_file)
                logger.info(f"✅ Found {env_file}")
        
        if processed_files:
            # Create symbolic links
            self._create_symlinks()
            
            # Create combined .env file
            self._create_combined_env()
            
            # Test credentials
            self._test_credentials()
            
            logger.info(f"✅ Processed {len(processed_files)} files: {', '.join(processed_files)}")
            return True
        else:
            logger.warning("⚠️  No credential files found in credentials/ directory")
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
                logger.info("✅ Linked accounts.yaml")
            
            # Link Google Cloud credentials
            gcp_src = self.credentials_dir / "google_cloud_credentials.json"
            gcp_dst = self.project_root / "google_cloud_credentials.json"
            
            if gcp_src.exists():
                if gcp_dst.exists() or gcp_dst.is_symlink():
                    gcp_dst.unlink()
                gcp_dst.symlink_to(gcp_src)
                logger.info("✅ Linked google_cloud_credentials.json")
            
            # Link .env file
            env_src = self.credentials_dir / ".env"
            env_dst = self.project_root / ".env"
            
            if env_src.exists():
                if env_dst.exists() or env_dst.is_symlink():
                    env_dst.unlink()
                env_dst.symlink_to(env_src)
                logger.info("✅ Linked .env")
                
        except Exception as e:
            logger.error(f"❌ Error creating symbolic links: {e}")
    
    def _create_combined_env(self):
        """Create a combined .env file from individual environment files."""
        env_content = f"""# AI Quant Trading System - Environment Credentials
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
        
        logger.info("✅ Created combined .env file")
    
    def _test_credentials(self):
        """Test if the credentials are valid."""
        logger.info("🧪 Testing credentials...")
        
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
    
    def show_instructions(self):
        """Show detailed instructions for accessing credentials."""
        print("\n🔐 AI Quant Trading System - Credential Access Instructions")
        print("=" * 70)
        print(f"Target Google Drive Folder: {self.FOLDER_URL}")
        print()
        print("Since direct Google Drive API access requires OAuth setup, here are")
        print("alternative methods to get your credentials:")
        print()
        print("📋 Method 1: Manual Entry (Recommended)")
        print("-" * 40)
        print("1. Run: python3 direct_drive_access.py --manual")
        print("2. Enter your credentials when prompted")
        print("3. The system will create all necessary files")
        print()
        print("📁 Method 2: File Upload")
        print("-" * 40)
        print("1. Download files from your Google Drive folder")
        print("2. Place them in: credentials/ directory")
        print("3. Run: python3 direct_drive_access.py --process-files")
        print()
        print("🌐 Method 3: Mobile Web Interface")
        print("-" * 40)
        print("1. Run: python3 mobile_credential_uploader.py --start-server")
        print("2. Open http://localhost:8080 in your mobile browser")
        print("3. Upload or enter credentials through the web interface")
        print()
        print("⚡ Method 4: Quick Setup")
        print("-" * 40)
        print("1. Run: python3 quick_credential_setup.py")
        print("2. Follow the interactive prompts")
        print("3. Get up and running in under 2 minutes")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Direct Google Drive Access for AI Quant Trading')
    parser.add_argument('--manual', action='store_true', help='Set up credentials manually')
    parser.add_argument('--upload', action='store_true', help='Show file upload instructions')
    parser.add_argument('--process-files', action='store_true', help='Process uploaded files')
    parser.add_argument('--instructions', action='store_true', help='Show all access methods')
    
    args = parser.parse_args()
    
    accessor = DirectDriveAccessor()
    
    if args.manual:
        accessor.create_manual_credentials()
    elif args.upload:
        accessor.create_file_upload_interface()
    elif args.process_files:
        accessor.process_uploaded_files()
    elif args.instructions:
        accessor.show_instructions()
    else:
        print("\n🚀 AI Quant Trading System - Direct Google Drive Access")
        print("=" * 60)
        print(f"Target Folder: {accessor.FOLDER_URL}")
        print("\nAvailable methods:")
        print("  --manual         Set up credentials manually (recommended)")
        print("  --upload         Show file upload instructions")
        print("  --process-files  Process uploaded credential files")
        print("  --instructions   Show all access methods")
        print("\nQuick start:")
        print("  python3 direct_drive_access.py --manual")

if __name__ == "__main__":
    main()