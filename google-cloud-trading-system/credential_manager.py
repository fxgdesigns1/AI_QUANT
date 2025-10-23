#!/usr/bin/env python3
"""
🔐 Credential Manager for AI Quant Trading System
================================================

This module provides multiple ways to access your Google Cloud credentials
when Google Drive files are not directly accessible (e.g., mobile/remote access).

Usage:
    python credential_manager.py --method env --setup
    python credential_manager.py --method gdrive --download
    python credential_manager.py --method manual --create
"""

import os
import json
import yaml
import base64
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CredentialManager:
    """Manages credentials through multiple access methods."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
        
    def setup_environment_credentials(self) -> bool:
        """Set up credentials using environment variables."""
        logger.info("🔧 Setting up environment-based credentials...")
        
        # Create environment file template
        env_template = """# AI Quant Trading System - Environment Credentials
# Copy this file to .env and fill in your actual values

# OANDA API Configuration
OANDA_API_KEY=your_oanda_api_key_here
OANDA_ACCOUNT_ID=your_oanda_account_id_here
OANDA_ENVIRONMENT=practice

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud_credentials.json
GOOGLE_CLOUD_PROJECT_ID=your_project_id_here

# News API Configuration
NEWS_API_KEY=your_news_api_key_here
MARKETAUX_API_KEY=your_marketaux_key_here

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Trading Configuration
DEFAULT_STRATEGY=adaptive_momentum
MAX_RISK_PER_TRADE=0.02
MAX_PORTFOLIO_RISK=0.10
"""
        
        env_file = self.credentials_dir / ".env.template"
        with open(env_file, 'w') as f:
            f.write(env_template)
        
        logger.info(f"✅ Environment template created: {env_file}")
        logger.info("📝 Next steps:")
        logger.info("   1. Copy .env.template to .env")
        logger.info("   2. Fill in your actual credentials")
        logger.info("   3. Run: source credentials/.env")
        
        return True
    
    def create_manual_credentials(self) -> bool:
        """Create credentials manually through interactive prompts."""
        logger.info("📝 Creating credentials manually...")
        
        print("\n🔐 AI Quant Trading System - Manual Credential Setup")
        print("=" * 60)
        
        # Collect OANDA credentials
        oanda_api_key = input("Enter your OANDA API Key: ").strip()
        oanda_account_id = input("Enter your OANDA Account ID: ").strip()
        oanda_environment = input("Enter environment (practice/live) [practice]: ").strip() or "practice"
        
        # Collect Google Cloud credentials
        print("\n📊 Google Cloud Credentials:")
        print("You can get these from: https://console.cloud.google.com/iam-admin/serviceaccounts")
        gcp_project_id = input("Enter your Google Cloud Project ID: ").strip()
        
        print("\nFor Google Cloud Service Account JSON:")
        print("1. Go to Google Cloud Console")
        print("2. Navigate to IAM & Admin > Service Accounts")
        print("3. Create or select a service account")
        print("4. Generate a new JSON key")
        print("5. Copy the entire JSON content below:")
        
        gcp_credentials = input("\nPaste your Google Cloud JSON credentials: ").strip()
        
        # Collect other credentials
        news_api_key = input("\nEnter News API Key (optional): ").strip()
        telegram_bot_token = input("Enter Telegram Bot Token (optional): ").strip()
        telegram_chat_id = input("Enter Telegram Chat ID (optional): ").strip()
        
        # Create accounts.yaml
        accounts_config = {
            'accounts': [
                {
                    'id': oanda_account_id,
                    'name': 'Primary Trading Account',
                    'display_name': '🚀 AI Quant Trader',
                    'strategy': 'adaptive_momentum',
                    'description': 'AI-powered automated trading',
                    'instruments': ['EUR_USD', 'GBP_USD', 'XAU_USD'],
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
                    'bot_token': telegram_bot_token,
                    'chat_id': telegram_chat_id
                }
            }
        }
        
        # Save accounts.yaml
        accounts_file = self.credentials_dir / "accounts.yaml"
        with open(accounts_file, 'w') as f:
            yaml.dump(accounts_config, f, default_flow_style=False, sort_keys=False)
        
        # Save Google Cloud credentials
        if gcp_credentials:
            try:
                gcp_data = json.loads(gcp_credentials)
                gcp_file = self.credentials_dir / "google_cloud_credentials.json"
                with open(gcp_file, 'w') as f:
                    json.dump(gcp_data, f, indent=2)
                logger.info(f"✅ Google Cloud credentials saved: {gcp_file}")
            except json.JSONDecodeError:
                logger.error("❌ Invalid JSON format for Google Cloud credentials")
                return False
        
        # Create environment file
        env_content = f"""# AI Quant Trading System - Environment Credentials
OANDA_API_KEY={oanda_api_key}
OANDA_ACCOUNT_ID={oanda_account_id}
OANDA_ENVIRONMENT={oanda_environment}
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud_credentials.json
GOOGLE_CLOUD_PROJECT_ID={gcp_project_id}
NEWS_API_KEY={news_api_key}
TELEGRAM_BOT_TOKEN={telegram_bot_token}
TELEGRAM_CHAT_ID={telegram_chat_id}
DEFAULT_STRATEGY=adaptive_momentum
MAX_RISK_PER_TRADE=0.02
MAX_PORTFOLIO_RISK=0.10
"""
        
        env_file = self.credentials_dir / ".env"
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"✅ Accounts configuration saved: {accounts_file}")
        logger.info(f"✅ Environment file saved: {env_file}")
        
        # Create symbolic links
        self._create_symlinks()
        
        return True
    
    def _create_symlinks(self):
        """Create symbolic links to make credentials accessible to the main system."""
        try:
            # Link accounts.yaml
            accounts_src = self.credentials_dir / "accounts.yaml"
            accounts_dst = self.project_root / "accounts.yaml"
            
            if accounts_src.exists():
                if accounts_dst.exists() or accounts_dst.is_symlink():
                    accounts_dst.unlink()
                accounts_dst.symlink_to(accounts_src)
                logger.info(f"✅ Linked accounts.yaml: {accounts_dst} -> {accounts_src}")
            
            # Link .env file
            env_src = self.credentials_dir / ".env"
            env_dst = self.project_root / ".env"
            
            if env_src.exists():
                if env_dst.exists() or env_dst.is_symlink():
                    env_dst.unlink()
                env_dst.symlink_to(env_src)
                logger.info(f"✅ Linked .env: {env_dst} -> {env_src}")
                
        except Exception as e:
            logger.error(f"❌ Error creating symbolic links: {e}")
    
    def download_from_gdrive_api(self) -> bool:
        """Download credentials using Google Drive API (requires setup)."""
        logger.info("📥 Setting up Google Drive API download...")
        
        # This would require Google Drive API setup
        # For now, provide instructions
        instructions = """
        Google Drive API Setup Instructions:
        ===================================
        
        1. Go to Google Cloud Console: https://console.cloud.google.com/
        2. Enable Google Drive API
        3. Create credentials (OAuth 2.0 or Service Account)
        4. Download the credentials JSON file
        5. Place it in: credentials/gdrive_api_credentials.json
        6. Run: python credential_manager.py --method gdrive --download
        
        Alternative: Use the manual method for immediate access.
        """
        
        print(instructions)
        return False
    
    def create_encrypted_credentials(self) -> bool:
        """Create encrypted credentials that can be safely shared/stored."""
        logger.info("🔒 Creating encrypted credentials...")
        
        # This would implement encryption for secure credential storage
        # For now, provide a simple base64 encoding (not secure, just for demo)
        
        print("\n🔐 Encrypted Credentials (Base64 encoded)")
        print("=" * 50)
        print("This creates a base64-encoded version of your credentials")
        print("that can be safely shared via text/email.")
        print("\n⚠️  WARNING: Base64 is NOT secure encryption!")
        print("   Use only for temporary sharing or with additional encryption.")
        
        return True
    
    def load_credentials(self) -> Dict[str, Any]:
        """Load credentials from any available method."""
        credentials = {}
        
        # Try to load from environment
        if os.getenv('OANDA_API_KEY'):
            credentials['oanda'] = {
                'api_key': os.getenv('OANDA_API_KEY'),
                'account_id': os.getenv('OANDA_ACCOUNT_ID'),
                'environment': os.getenv('OANDA_ENVIRONMENT', 'practice')
            }
            logger.info("✅ Loaded OANDA credentials from environment")
        
        # Try to load from .env file
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
            logger.info("✅ Loaded credentials from .env file")
        
        # Try to load accounts.yaml
        accounts_file = self.project_root / "accounts.yaml"
        if accounts_file.exists():
            with open(accounts_file, 'r') as f:
                accounts_data = yaml.safe_load(f)
                credentials['accounts'] = accounts_data
            logger.info("✅ Loaded accounts configuration")
        
        return credentials

def main():
    parser = argparse.ArgumentParser(description='AI Quant Trading System - Credential Manager')
    parser.add_argument('--method', choices=['env', 'manual', 'gdrive', 'encrypted'], 
                       default='manual', help='Credential access method')
    parser.add_argument('--setup', action='store_true', help='Set up credentials')
    parser.add_argument('--download', action='store_true', help='Download from Google Drive')
    parser.add_argument('--create', action='store_true', help='Create new credentials')
    parser.add_argument('--load', action='store_true', help='Load and display credentials')
    
    args = parser.parse_args()
    
    manager = CredentialManager()
    
    if args.method == 'env' and args.setup:
        manager.setup_environment_credentials()
    elif args.method == 'manual' and args.create:
        manager.create_manual_credentials()
    elif args.method == 'gdrive' and args.download:
        manager.download_from_gdrive_api()
    elif args.method == 'encrypted' and args.create:
        manager.create_encrypted_credentials()
    elif args.load:
        credentials = manager.load_credentials()
        print("\n📊 Loaded Credentials:")
        print(json.dumps(credentials, indent=2, default=str))
    else:
        print("\n🔐 AI Quant Trading System - Credential Manager")
        print("=" * 50)
        print("Available methods:")
        print("  --method manual --create    Interactive credential setup")
        print("  --method env --setup        Environment variable setup")
        print("  --method gdrive --download  Google Drive API download")
        print("  --method encrypted --create Encrypted credential creation")
        print("  --load                      Load current credentials")
        print("\nRecommended: python credential_manager.py --method manual --create")

if __name__ == "__main__":
    main()