#!/usr/bin/env python3
"""
Migrate Credentials to Google Cloud Secret Manager
Securely moves all credentials from .env files to Google Cloud Secret Manager
for mobile access and better security
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the google-cloud-trading-system to path
sys.path.insert(0, str(Path(__file__).parent / "google-cloud-trading-system"))

from src.core.secret_manager import SecretManager


def load_env_files():
    """Load all .env files from the project"""
    env_files = [
        "google-cloud-trading-system/oanda_config.env",
        "google-cloud-trading-system/news_api_config.env",
    ]
    
    for env_file in env_files:
        env_path = Path(__file__).parent / env_file
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"✓ Loaded {env_file}")
        else:
            print(f"⚠ {env_file} not found")


def get_sensitive_credentials():
    """
    Get all sensitive credentials that should be stored in Secret Manager
    
    Returns:
        Dictionary of {credential_name: value}
    """
    credentials = {
        # OANDA Trading
        'oanda-api-key': os.getenv('OANDA_API_KEY'),
        
        # Telegram
        'telegram-token': os.getenv('TELEGRAM_TOKEN'),
        'telegram-chat-id': os.getenv('TELEGRAM_CHAT_ID'),
        
        # News APIs
        'alpha-vantage-api-key': os.getenv('ALPHA_VANTAGE_API_KEY'),
        'marketaux-api-key': os.getenv('MARKETAUX_API_KEY'),
        'newsdata-api-key': os.getenv('NEWSDATA_API_KEY'),
        'fmp-api-key': os.getenv('FMP_API_KEY'),
        'polygon-api-key': os.getenv('POLYGON_API_KEY'),
        'twelve-data-api-key': os.getenv('TWELVE_DATA_API_KEY'),
        'newsapi-key': os.getenv('NEWSAPI_KEY'),
        'gemini-api-key': os.getenv('GEMINI_API_KEY'),
        
        # Flask
        'flask-secret-key': os.getenv('FLASK_SECRET_KEY'),
    }
    
    # Remove None values and empty strings
    return {k: v for k, v in credentials.items() if v and v.strip() and 'your_' not in v}


def migrate_to_secret_manager(project_id: str, dry_run: bool = False):
    """
    Migrate credentials to Google Cloud Secret Manager
    
    Args:
        project_id: Google Cloud project ID
        dry_run: If True, just show what would be done without actually doing it
    """
    print("\n" + "="*70)
    print("MIGRATING CREDENTIALS TO GOOGLE CLOUD SECRET MANAGER")
    print("="*70)
    
    # Load environment variables from .env files
    print("\n[1/4] Loading credentials from .env files...")
    load_env_files()
    
    # Get credentials
    print("\n[2/4] Extracting sensitive credentials...")
    credentials = get_sensitive_credentials()
    print(f"Found {len(credentials)} credentials to migrate:")
    for name in sorted(credentials.keys()):
        print(f"  • {name}")
    
    if not credentials:
        print("\n✗ No credentials found to migrate!")
        return False
    
    if dry_run:
        print("\n[DRY RUN MODE] - No changes will be made")
        print("\nRun without --dry-run to actually migrate credentials")
        return True
    
    # Initialize Secret Manager
    print(f"\n[3/4] Connecting to Google Cloud Secret Manager (Project: {project_id})...")
    try:
        secret_manager = SecretManager(project_id=project_id)
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure you have:")
        print("  1. Installed: pip install google-cloud-secret-manager")
        print("  2. Authenticated: gcloud auth application-default login")
        print("  3. Enabled Secret Manager API in your Google Cloud project")
        return False
    
    # Migrate each credential
    print(f"\n[4/4] Migrating credentials to Secret Manager...")
    success_count = 0
    fail_count = 0
    
    for secret_name, secret_value in credentials.items():
        try:
            # Check if secret already exists
            existing_secrets = secret_manager.list_secrets()
            
            if secret_name in existing_secrets:
                print(f"  Updating existing secret: {secret_name}")
                secret_manager.update_secret(secret_name, secret_value)
            else:
                print(f"  Creating new secret: {secret_name}")
                secret_manager.create_secret(
                    secret_name,
                    secret_value,
                    labels={'source': 'env-migration', 'system': 'trading'}
                )
            
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Failed to migrate {secret_name}: {e}")
            fail_count += 1
    
    # Summary
    print("\n" + "="*70)
    print("MIGRATION COMPLETE")
    print("="*70)
    print(f"✓ Successfully migrated: {success_count} credentials")
    if fail_count > 0:
        print(f"✗ Failed to migrate: {fail_count} credentials")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. TEST the integration:")
    print("   python test_secret_manager.py")
    
    print("\n2. UPDATE your code to use Secret Manager:")
    print("   from src.core.secret_manager import get_credentials_manager")
    print("   credentials = get_credentials_manager()")
    print("   api_key = credentials.get('OANDA_API_KEY')")
    
    print("\n3. SET environment variable for your Google Cloud project:")
    print(f"   export GOOGLE_CLOUD_PROJECT={project_id}")
    print("   (Add this to your shell profile: ~/.zshrc or ~/.bashrc)")
    
    print("\n4. FOR MOBILE ACCESS:")
    print("   • Your credentials are now securely stored in Google Cloud")
    print("   • Access from anywhere using the Secret Manager API")
    print("   • No need to sync .env files to mobile devices")
    
    print("\n5. SECURITY:")
    print("   • KEEP your .env files as backup (but don't commit to git)")
    print("   • ADD .env files to .gitignore")
    print("   • Consider deleting local .env files after testing")
    
    return success_count > 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate credentials to Google Cloud Secret Manager"
    )
    parser.add_argument(
        '--project-id',
        required=True,
        help='Google Cloud project ID'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    success = migrate_to_secret_manager(
        project_id=args.project_id,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


