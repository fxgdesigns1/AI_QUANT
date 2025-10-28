#!/usr/bin/env python3
"""
🔐 Simple Credential Setup for AI Quant Trading System
=====================================================

This script provides a simple way to set up credentials without interactive prompts.
Perfect for accessing your Google Drive credentials.

Target Folder: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT
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

class SimpleCredentialSetup:
    """Simple credential setup without interactive prompts."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.credentials_dir = self.project_root / "credentials"
        self.credentials_dir.mkdir(exist_ok=True)
    
    def create_template_credentials(self) -> bool:
        """Create template credential files that you can edit."""
        logger.info("📝 Creating template credential files...")
        
        # Create accounts.yaml template
        accounts_template = {
            'accounts': [
                {
                    'id': 'YOUR-OANDA-ACCOUNT-ID',
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
                    'api_key': 'YOUR-OANDA-API-KEY',
                    'account_id': 'YOUR-OANDA-ACCOUNT-ID',
                    'environment': 'practice'
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
                    'enabled': False,
                    'bot_token': 'YOUR-TELEGRAM-BOT-TOKEN',
                    'chat_id': 'YOUR-TELEGRAM-CHAT-ID'
                }
            }
        }
        
        # Save accounts.yaml template
        accounts_file = self.credentials_dir / "accounts.yaml.template"
        with open(accounts_file, 'w') as f:
            yaml.dump(accounts_template, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"✅ Created accounts.yaml template: {accounts_file}")
        
        # Create Google Cloud credentials template
        gcp_template = {
            "type": "service_account",
            "project_id": "YOUR-PROJECT-ID",
            "private_key_id": "YOUR-PRIVATE-KEY-ID",
            "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY\n-----END PRIVATE KEY-----\n",
            "client_email": "YOUR-SERVICE-ACCOUNT@YOUR-PROJECT.iam.gserviceaccount.com",
            "client_id": "YOUR-CLIENT-ID",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/YOUR-SERVICE-ACCOUNT%40YOUR-PROJECT.iam.gserviceaccount.com"
        }
        
        gcp_file = self.credentials_dir / "google_cloud_credentials.json.template"
        with open(gcp_file, 'w') as f:
            json.dump(gcp_template, f, indent=2)
        
        logger.info(f"✅ Created Google Cloud template: {gcp_file}")
        
        # Create environment template
        env_template = """# AI Quant Trading System - Environment Credentials
# Copy this file to .env and fill in your actual values

# OANDA Configuration
OANDA_API_KEY=your_oanda_api_key_here
OANDA_ACCOUNT_ID=your_oanda_account_id_here
OANDA_ENVIRONMENT=practice

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud_credentials.json
GOOGLE_CLOUD_PROJECT_ID=your_project_id_here

# Optional APIs
NEWS_API_KEY=your_news_api_key_here
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
        
        logger.info(f"✅ Created environment template: {env_file}")
        
        # Create setup instructions
        instructions = f"""# AI Quant Trading System - Credential Setup Instructions
========================================================

## Your Google Drive Folder
Target: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT

## Setup Steps

### Step 1: Copy Template Files
```bash
cd /workspace/google-cloud-trading-system
cp credentials/accounts.yaml.template credentials/accounts.yaml
cp credentials/google_cloud_credentials.json.template credentials/google_cloud_credentials.json
cp credentials/.env.template credentials/.env
```

### Step 2: Edit Your Credentials

#### Edit accounts.yaml:
- Replace 'YOUR-OANDA-ACCOUNT-ID' with your actual OANDA account ID
- Replace 'YOUR-OANDA-API-KEY' with your actual OANDA API key
- Adjust trading instruments and risk settings as needed

#### Edit google_cloud_credentials.json:
- Replace all placeholder values with your actual Google Cloud service account credentials
- Get these from: https://console.cloud.google.com/iam-admin/serviceaccounts

#### Edit .env:
- Fill in all your API keys and configuration values

### Step 3: Create Symbolic Links
```bash
python3 simple_credential_setup.py --create-links
```

### Step 4: Test Your Setup
```bash
python3 simple_credential_setup.py --test
```

## Alternative: Use Mobile Web Interface

If you prefer a web interface:

1. Start the mobile interface:
   ```bash
   python3 mobile_credential_uploader.py --host 0.0.0.0 --port 8080
   ```

2. Open your browser and go to: http://YOUR_IP:8080

3. Upload your credential files or enter them manually

## Files Created

- credentials/accounts.yaml.template - OANDA account configuration
- credentials/google_cloud_credentials.json.template - Google Cloud credentials
- credentials/.env.template - Environment variables
- credentials/setup_instructions.md - This file

## Next Steps

After setting up credentials:

1. Test your configuration:
   ```bash
   python3 src/main.py --test
   ```

2. Start trading:
   ```bash
   python3 src/main.py
   ```

3. View dashboard:
   ```bash
   python3 scripts/dashboard.py
   ```

## Support

If you need help:
1. Check the template files for examples
2. Verify all placeholder values are replaced
3. Test your configuration before trading
4. Check logs for any errors

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        instructions_file = self.credentials_dir / "setup_instructions.md"
        with open(instructions_file, 'w') as f:
            f.write(instructions)
        
        logger.info(f"✅ Created setup instructions: {instructions_file}")
        
        print("\n🎉 Template files created successfully!")
        print("=" * 50)
        print("📁 Files created in credentials/ directory:")
        print("  - accounts.yaml.template")
        print("  - google_cloud_credentials.json.template")
        print("  - .env.template")
        print("  - setup_instructions.md")
        print("\n📋 Next steps:")
        print("1. Copy the template files to remove .template extension")
        print("2. Edit the files with your actual credentials")
        print("3. Run: python3 simple_credential_setup.py --create-links")
        print("4. Run: python3 simple_credential_setup.py --test")
        
        return True
    
    def create_symbolic_links(self) -> bool:
        """Create symbolic links to make credentials accessible."""
        logger.info("🔗 Creating symbolic links...")
        
        try:
            # Link accounts.yaml
            accounts_src = self.credentials_dir / "accounts.yaml"
            accounts_dst = self.project_root / "accounts.yaml"
            
            if accounts_src.exists():
                if accounts_dst.exists() or accounts_dst.is_symlink():
                    accounts_dst.unlink()
                accounts_dst.symlink_to(accounts_src)
                logger.info("✅ Linked accounts.yaml")
            else:
                logger.warning("⚠️  accounts.yaml not found - copy from template first")
            
            # Link Google Cloud credentials
            gcp_src = self.credentials_dir / "google_cloud_credentials.json"
            gcp_dst = self.project_root / "google_cloud_credentials.json"
            
            if gcp_src.exists():
                if gcp_dst.exists() or gcp_dst.is_symlink():
                    gcp_dst.unlink()
                gcp_dst.symlink_to(gcp_src)
                logger.info("✅ Linked google_cloud_credentials.json")
            else:
                logger.warning("⚠️  google_cloud_credentials.json not found - copy from template first")
            
            # Link .env file
            env_src = self.credentials_dir / ".env"
            env_dst = self.project_root / ".env"
            
            if env_src.exists():
                if env_dst.exists() or env_dst.is_symlink():
                    env_dst.unlink()
                env_dst.symlink_to(env_src)
                logger.info("✅ Linked .env")
            else:
                logger.warning("⚠️  .env not found - copy from template first")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating symbolic links: {e}")
            return False
    
    def test_credentials(self) -> bool:
        """Test if credentials are properly configured."""
        logger.info("🧪 Testing credentials...")
        
        tests = []
        
        # Test accounts.yaml
        accounts_file = self.credentials_dir / "accounts.yaml"
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as f:
                    accounts_data = yaml.safe_load(f)
                    if 'accounts' in accounts_data and accounts_data['accounts']:
                        # Check if placeholders are replaced
                        first_account = accounts_data['accounts'][0]
                        if 'YOUR-OANDA-ACCOUNT-ID' in str(first_account):
                            tests.append(("accounts.yaml", False, "Contains placeholder values - edit the file"))
                        else:
                            tests.append(("accounts.yaml", True, f"Found {len(accounts_data['accounts'])} account(s)"))
                    else:
                        tests.append(("accounts.yaml", False, "No accounts found"))
            except Exception as e:
                tests.append(("accounts.yaml", False, f"Error: {e}"))
        else:
            tests.append(("accounts.yaml", False, "File not found - copy from template"))
        
        # Test Google Cloud credentials
        gcp_file = self.credentials_dir / "google_cloud_credentials.json"
        if gcp_file.exists():
            try:
                with open(gcp_file, 'r') as f:
                    gcp_data = json.load(f)
                    if 'YOUR-PROJECT-ID' in str(gcp_data):
                        tests.append(("Google Cloud JSON", False, "Contains placeholder values - edit the file"))
                    elif 'type' in gcp_data and gcp_data['type'] == 'service_account':
                        tests.append(("Google Cloud JSON", True, "Valid service account"))
                    else:
                        tests.append(("Google Cloud JSON", False, "Invalid format"))
            except Exception as e:
                tests.append(("Google Cloud JSON", False, f"Error: {e}"))
        else:
            tests.append(("Google Cloud JSON", False, "File not found - copy from template"))
        
        # Test .env file
        env_file = self.credentials_dir / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                if 'your_oanda_api_key_here' in content:
                    tests.append((".env file", False, "Contains placeholder values - edit the file"))
                else:
                    tests.append((".env file", True, "Environment file configured"))
        else:
            tests.append((".env file", False, "File not found - copy from template"))
        
        # Display test results
        logger.info("📊 Credential Test Results:")
        for test_name, passed, message in tests:
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {test_name}: {message}")
        
        all_passed = all(passed for _, passed, _ in tests)
        if all_passed:
            logger.info("🎉 All credential tests passed! Your system is ready to trade.")
        else:
            logger.warning("⚠️  Some credential tests failed. Please edit the files and try again.")
        
        return all_passed
    
    def show_status(self):
        """Show current credential status."""
        logger.info("📊 Current Credential Status:")
        
        files_to_check = [
            ("accounts.yaml", self.credentials_dir / "accounts.yaml"),
            ("google_cloud_credentials.json", self.credentials_dir / "google_cloud_credentials.json"),
            (".env", self.credentials_dir / ".env"),
            ("accounts.yaml (linked)", self.project_root / "accounts.yaml"),
            (".env (linked)", self.project_root / ".env")
        ]
        
        for name, path in files_to_check:
            if path.exists():
                if path.is_symlink():
                    logger.info(f"  ✅ {name}: Linked")
                else:
                    logger.info(f"  ✅ {name}: Exists")
            else:
                logger.info(f"  ❌ {name}: Missing")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Credential Setup for AI Quant Trading')
    parser.add_argument('--create-templates', action='store_true', help='Create template credential files')
    parser.add_argument('--create-links', action='store_true', help='Create symbolic links')
    parser.add_argument('--test', action='store_true', help='Test credentials')
    parser.add_argument('--status', action='store_true', help='Show credential status')
    
    args = parser.parse_args()
    
    setup = SimpleCredentialSetup()
    
    if args.create_templates:
        setup.create_template_credentials()
    elif args.create_links:
        setup.create_symbolic_links()
    elif args.test:
        setup.test_credentials()
    elif args.status:
        setup.show_status()
    else:
        print("\n🔐 AI Quant Trading System - Simple Credential Setup")
        print("=" * 60)
        print("Target Google Drive Folder: https://drive.google.com/drive/folders/1fhKX5LOUrrvyUNuX0UUr_PfBh_0QogCT")
        print("\nAvailable commands:")
        print("  --create-templates  Create template credential files")
        print("  --create-links      Create symbolic links")
        print("  --test              Test credentials")
        print("  --status            Show credential status")
        print("\nQuick start:")
        print("  python3 simple_credential_setup.py --create-templates")

if __name__ == "__main__":
    main()