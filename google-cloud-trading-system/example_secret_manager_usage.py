#!/usr/bin/env python3
"""
Example: Using Secret Manager in Your Trading System

This shows how to update your existing code to use Secret Manager
instead of .env files, with automatic fallback.
"""

# EXAMPLE 1: Basic Usage
# =====================
from src.core.secret_manager import get_credentials_manager

# Initialize credentials manager (do this once at startup)
credentials = get_credentials_manager()

# Get individual credentials
oanda_api_key = credentials.get('OANDA_API_KEY')
telegram_token = credentials.get('TELEGRAM_TOKEN')
telegram_chat_id = credentials.get('TELEGRAM_CHAT_ID')

print(f"OANDA API Key: {oanda_api_key[:10]}...")
print(f"Telegram Token: {telegram_token[:10]}...")


# EXAMPLE 2: Initialize OANDA Client
# ==================================
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()

# Replace this old code:
# from dotenv import load_dotenv
# load_dotenv('oanda_config.env')
# api_key = os.getenv('OANDA_API_KEY')

# With this new code:
api_key = credentials.get('OANDA_API_KEY')
environment = credentials.get('OANDA_ENVIRONMENT', 'practice')
base_url = credentials.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')

print(f"✓ OANDA configured: {environment}")


# EXAMPLE 3: Initialize Telegram Notifier
# =======================================
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()

# Get Telegram credentials
telegram_config = {
    'token': credentials.get('TELEGRAM_TOKEN'),
    'chat_id': credentials.get('TELEGRAM_CHAT_ID'),
}

print(f"✓ Telegram configured for chat: {telegram_config['chat_id']}")


# EXAMPLE 4: Get All Credentials at Once
# ======================================
from src.core.secret_manager import get_credentials_manager

credentials = get_credentials_manager()

# Get everything in one call
all_creds = credentials.get_all_trading_credentials()

print(f"✓ Loaded {len(all_creds)} credentials")
print(f"Available: {', '.join(all_creds.keys())}")


# EXAMPLE 5: Force Fallback to .env (for testing)
# ===============================================
from src.core.secret_manager import get_credentials_manager

# Disable Secret Manager, use only .env files
credentials = get_credentials_manager(use_secret_manager=False)

api_key = credentials.get('OANDA_API_KEY')
print(f"✓ Using .env file: {api_key[:10]}...")


# EXAMPLE 6: Use Specific Google Cloud Project
# ============================================
from src.core.secret_manager import get_credentials_manager

# For multi-project setups
prod_credentials = get_credentials_manager(
    use_secret_manager=True,
    project_id='my-production-project'
)

dev_credentials = get_credentials_manager(
    use_secret_manager=True,
    project_id='my-development-project'
)


# EXAMPLE 7: Direct Secret Manager Access (Advanced)
# ==================================================
from src.core.secret_manager import SecretManager

# Create direct client for advanced operations
sm = SecretManager(project_id='your-project-id')

# Create a new secret
sm.create_secret('my-new-credential', 'secret-value')

# Update existing secret
sm.update_secret('oanda-api-key', 'new-api-key')

# Get a secret directly
value = sm.get_secret('oanda-api-key')

# List all secrets
secrets = sm.list_secrets()
print(f"Total secrets: {len(secrets)}")

# Delete a secret
sm.delete_secret('unused-credential')


# EXAMPLE 8: Integration with Existing Classes
# ============================================
"""
In your existing files, replace:

    import os
    from dotenv import load_dotenv
    
    load_dotenv('oanda_config.env')
    self.api_key = os.getenv('OANDA_API_KEY')

With:

    from src.core.secret_manager import get_credentials_manager
    
    credentials = get_credentials_manager()
    self.api_key = credentials.get('OANDA_API_KEY')
"""


# EXAMPLE 9: Error Handling
# =========================
from src.core.secret_manager import get_credentials_manager

try:
    credentials = get_credentials_manager()
    api_key = credentials.get('OANDA_API_KEY')
    
    if not api_key:
        print("⚠ Warning: OANDA_API_KEY not found")
        print("  Check Secret Manager or .env files")
    else:
        print(f"✓ API Key loaded: {api_key[:10]}...")
        
except Exception as e:
    print(f"✗ Error loading credentials: {e}")
    print("  Falling back to default configuration")


# EXAMPLE 10: Configuration Class Pattern
# =======================================
from src.core.secret_manager import get_credentials_manager

class TradingConfig:
    """Trading system configuration using Secret Manager"""
    
    def __init__(self):
        self.credentials = get_credentials_manager()
        self._load_config()
    
    def _load_config(self):
        """Load all configuration"""
        # OANDA
        self.oanda_api_key = self.credentials.get('OANDA_API_KEY')
        self.oanda_environment = self.credentials.get('OANDA_ENVIRONMENT', 'practice')
        self.oanda_base_url = self.credentials.get('OANDA_BASE_URL')
        
        # Telegram
        self.telegram_token = self.credentials.get('TELEGRAM_TOKEN')
        self.telegram_chat_id = self.credentials.get('TELEGRAM_CHAT_ID')
        
        # News APIs
        self.alpha_vantage_key = self.credentials.get('ALPHA_VANTAGE_API_KEY')
        self.marketaux_key = self.credentials.get('MARKETAUX_API_KEY')
        
    def is_valid(self):
        """Check if all required credentials are present"""
        required = [
            self.oanda_api_key,
            self.telegram_token,
            self.telegram_chat_id,
        ]
        return all(required)
    
    def __repr__(self):
        return f"TradingConfig(oanda={self.oanda_environment}, valid={self.is_valid()})"


# Usage
config = TradingConfig()
if config.is_valid():
    print(f"✓ {config}")
else:
    print("✗ Invalid configuration - missing credentials")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SECRET MANAGER EXAMPLES")
    print("="*70)
    print("\nRun this file to see examples of using Secret Manager")
    print("Copy these patterns into your own code!")
    print("\n" + "="*70)


