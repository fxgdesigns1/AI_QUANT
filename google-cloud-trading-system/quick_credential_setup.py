#!/usr/bin/env python3
"""
⚡ Quick Credential Setup for AI Quant Trading System
====================================================

This script provides the fastest way to set up credentials when you can't
access Google Drive files directly.

Usage:
    python quick_credential_setup.py
"""

import os
import json
import yaml
import base64
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_quick_credentials():
    """Create credentials quickly with minimal input."""
    
    print("\n🚀 AI Quant Trading System - Quick Credential Setup")
    print("=" * 60)
    print("This will create your trading credentials in under 2 minutes!")
    print()
    
    # Get essential credentials
    print("📋 Essential Credentials (Required):")
    print("-" * 40)
    
    oanda_api_key = input("🔑 OANDA API Key: ").strip()
    if not oanda_api_key:
        print("❌ OANDA API Key is required!")
        return False
    
    oanda_account_id = input("🆔 OANDA Account ID: ").strip()
    if not oanda_account_id:
        print("❌ OANDA Account ID is required!")
        return False
    
    oanda_environment = input("🌍 Environment (practice/live) [practice]: ").strip() or "practice"
    
    print("\n☁️ Google Cloud Credentials:")
    print("-" * 40)
    gcp_project_id = input("📊 Google Cloud Project ID: ").strip()
    
    print("\nFor Google Cloud Service Account JSON:")
    print("1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("2. Create or select a service account")
    print("3. Generate a new JSON key")
    print("4. Copy the entire JSON content below:")
    print()
    
    gcp_credentials_json = input("🔐 Google Cloud JSON (paste entire JSON): ").strip()
    
    # Optional credentials
    print("\n📰 Optional APIs (press Enter to skip):")
    print("-" * 40)
    news_api_key = input("📰 News API Key: ").strip()
    telegram_bot_token = input("📱 Telegram Bot Token: ").strip()
    telegram_chat_id = input("💬 Telegram Chat ID: ").strip()
    
    # Create credentials directory
    project_root = Path(__file__).parent
    credentials_dir = project_root / "credentials"
    credentials_dir.mkdir(exist_ok=True)
    
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
        accounts_file = credentials_dir / "accounts.yaml"
        with open(accounts_file, 'w') as f:
            yaml.dump(accounts_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"✅ Created accounts.yaml: {accounts_file}")
        
        # Save Google Cloud credentials
        if gcp_credentials_json:
            try:
                gcp_data = json.loads(gcp_credentials_json)
                gcp_file = credentials_dir / "google_cloud_credentials.json"
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
        
        env_file = credentials_dir / ".env"
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"✅ Created environment file: {env_file}")
        
        # Create symbolic links
        create_symlinks(project_root, credentials_dir)
        
        # Test credentials
        test_credentials(project_root)
        
        print("\n🎉 SUCCESS! Your credentials are now set up!")
        print("=" * 50)
        print("✅ OANDA API configured")
        print("✅ Google Cloud credentials saved")
        print("✅ Environment variables set")
        print("✅ Symbolic links created")
        print("\n🚀 You can now run your trading system!")
        print("\nNext steps:")
        print("1. Test your setup: python src/main.py --test")
        print("2. Start trading: python src/main.py")
        print("3. View dashboard: python scripts/dashboard.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating credentials: {e}")
        return False

def create_symlinks(project_root: Path, credentials_dir: Path):
    """Create symbolic links to make credentials accessible."""
    try:
        # Link accounts.yaml
        accounts_src = credentials_dir / "accounts.yaml"
        accounts_dst = project_root / "accounts.yaml"
        
        if accounts_src.exists():
            if accounts_dst.exists() or accounts_dst.is_symlink():
                accounts_dst.unlink()
            accounts_dst.symlink_to(accounts_src)
            logger.info("✅ Linked accounts.yaml")
        
        # Link .env file
        env_src = credentials_dir / ".env"
        env_dst = project_root / ".env"
        
        if env_src.exists():
            if env_dst.exists() or env_dst.is_symlink():
                env_dst.unlink()
            env_dst.symlink_to(env_src)
            logger.info("✅ Linked .env")
            
    except Exception as e:
        logger.error(f"❌ Error creating symbolic links: {e}")

def test_credentials(project_root: Path):
    """Test if credentials are properly configured."""
    print("\n🧪 Testing credentials...")
    
    # Check if files exist
    accounts_file = project_root / "accounts.yaml"
    env_file = project_root / ".env"
    gcp_file = project_root / "credentials" / "google_cloud_credentials.json"
    
    tests = [
        ("accounts.yaml", accounts_file.exists()),
        (".env file", env_file.exists()),
        ("Google Cloud JSON", gcp_file.exists()),
    ]
    
    all_passed = True
    for test_name, passed in tests:
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("🎉 All credential tests passed!")
    else:
        print("⚠️  Some credential tests failed. Check the files above.")
    
    return all_passed

def create_encrypted_backup():
    """Create an encrypted backup of credentials for easy sharing."""
    print("\n🔒 Creating encrypted backup...")
    
    project_root = Path(__file__).parent
    credentials_dir = project_root / "credentials"
    
    # Collect all credential files
    credential_files = [
        "accounts.yaml",
        "google_cloud_credentials.json",
        ".env"
    ]
    
    backup_data = {}
    for filename in credential_files:
        file_path = credentials_dir / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                backup_data[filename] = f.read()
    
    if backup_data:
        # Create base64 encoded backup
        backup_json = json.dumps(backup_data, indent=2)
        backup_encoded = base64.b64encode(backup_json.encode()).decode()
        
        backup_file = credentials_dir / "credentials_backup.txt"
        with open(backup_file, 'w') as f:
            f.write(f"# AI Quant Trading System - Encrypted Credentials Backup\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# To restore: python quick_credential_setup.py --restore\n\n")
            f.write(backup_encoded)
        
        print(f"✅ Encrypted backup created: {backup_file}")
        print("💡 You can share this file securely or store it as a backup")
        return True
    else:
        print("❌ No credential files found to backup")
        return False

def restore_from_backup(backup_file: str):
    """Restore credentials from encrypted backup."""
    print(f"\n🔄 Restoring from backup: {backup_file}")
    
    try:
        with open(backup_file, 'r') as f:
            content = f.read()
        
        # Skip header lines
        lines = content.split('\n')
        encoded_data = None
        for line in lines:
            if not line.startswith('#') and line.strip():
                encoded_data = line.strip()
                break
        
        if not encoded_data:
            print("❌ No encoded data found in backup file")
            return False
        
        # Decode and parse
        decoded_data = base64.b64decode(encoded_data.encode()).decode()
        backup_data = json.loads(decoded_data)
        
        # Restore files
        project_root = Path(__file__).parent
        credentials_dir = project_root / "credentials"
        credentials_dir.mkdir(exist_ok=True)
        
        restored_count = 0
        for filename, content in backup_data.items():
            file_path = credentials_dir / filename
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Restored: {filename}")
            restored_count += 1
        
        # Create symbolic links
        create_symlinks(project_root, credentials_dir)
        
        print(f"🎉 Successfully restored {restored_count} files!")
        return True
        
    except Exception as e:
        print(f"❌ Error restoring backup: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Quant Quick Credential Setup')
    parser.add_argument('--backup', action='store_true', help='Create encrypted backup')
    parser.add_argument('--restore', type=str, help='Restore from backup file')
    
    args = parser.parse_args()
    
    if args.backup:
        create_encrypted_backup()
    elif args.restore:
        restore_from_backup(args.restore)
    else:
        create_quick_credentials()

if __name__ == "__main__":
    main()