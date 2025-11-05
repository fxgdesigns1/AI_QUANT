#!/usr/bin/env python3
"""
UNIFIED CREDENTIAL LOADER - FIXES PERSISTENT CREDENTIAL ISSUES
Loads credentials from multiple sources with proper fallbacks
STOPS THE FALSE ALARMS about missing credentials
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Credential cache to avoid repeated file reads
_credential_cache: Dict[str, Optional[str]] = {}
_cache_initialized = False

def _load_credentials_from_file(file_path: Path) -> Dict[str, str]:
    """Load credentials from a file"""
    credentials = {}
    
    if not file_path.exists():
        return credentials
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    credentials[key] = value
    except Exception as e:
        logger.debug(f"Could not read {file_path}: {e}")
    
    return credentials

def _load_credentials_from_env_files() -> Dict[str, str]:
    """Load credentials from all possible .env file locations"""
    credentials = {}
    
    # Check multiple possible locations
    env_file_paths = [
        Path('google-cloud-trading-system/oanda_config.env'),
        Path('google-cloud-trading-system/.env'),
        Path('.env'),
        Path('oanda_config.env'),
        Path(os.path.expanduser('~/.oanda_config.env')),
    ]
    
    for env_file in env_file_paths:
        if env_file.exists():
            logger.debug(f"Loading credentials from: {env_file}")
            file_creds = _load_credentials_from_file(env_file)
            credentials.update(file_creds)
            break  # Use first found file
    
    return credentials

def _load_credentials_from_hardcoded() -> Dict[str, str]:
    """Load credentials from hardcoded values in system files"""
    credentials = {}
    
    # Check known files with hardcoded credentials
    hardcoded_files = [
        Path('automated_trading_system.py'),
        Path('ai_trading_system.py'),
        Path('working_trading_system.py'),
    ]
    
    for file_path in hardcoded_files:
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    # Look for OANDA_API_KEY = "value"
                    if 'OANDA_API_KEY' in content:
                        import re
                        # Match: OANDA_API_KEY = "value"
                        match = re.search(r'OANDA_API_KEY\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            credentials['OANDA_API_KEY'] = match.group(1)
                    
                    # Look for OANDA_ACCOUNT_ID = "value"
                    if 'OANDA_ACCOUNT_ID' in content:
                        import re
                        match = re.search(r'OANDA_ACCOUNT_ID\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            credentials['OANDA_ACCOUNT_ID'] = match.group(1)
                    
                    # Also check for PRIMARY_ACCOUNT
                    if 'PRIMARY_ACCOUNT' in content:
                        import re
                        match = re.search(r'PRIMARY_ACCOUNT\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            credentials['PRIMARY_ACCOUNT'] = match.group(1)
            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")
    
    return credentials

def _initialize_credential_cache():
    """Initialize credential cache from all sources"""
    global _credential_cache, _cache_initialized
    
    if _cache_initialized:
        return
    
    # Priority order:
    # 1. Environment variables (highest priority)
    # 2. .env files
    # 3. Hardcoded values in files
    
    # Start with environment variables
    _credential_cache = {
        'OANDA_API_KEY': os.getenv('OANDA_API_KEY'),
        'OANDA_ACCOUNT_ID': os.getenv('OANDA_ACCOUNT_ID') or os.getenv('PRIMARY_ACCOUNT'),
        'PRIMARY_ACCOUNT': os.getenv('PRIMARY_ACCOUNT'),
        'OANDA_ENVIRONMENT': os.getenv('OANDA_ENVIRONMENT', 'practice'),
    }
    
    # Load from .env files (if not already set)
    if not _credential_cache.get('OANDA_API_KEY'):
        env_creds = _load_credentials_from_env_files()
        _credential_cache.update(env_creds)
    
    # Load from hardcoded files (if still not set)
    if not _credential_cache.get('OANDA_API_KEY'):
        hardcoded_creds = _load_credentials_from_hardcoded()
        for key, value in hardcoded_creds.items():
            if not _credential_cache.get(key):
                _credential_cache[key] = value
    
    # Set fallback values if found
    if _credential_cache.get('OANDA_API_KEY'):
        os.environ['OANDA_API_KEY'] = _credential_cache['OANDA_API_KEY']
    
    if _credential_cache.get('OANDA_ACCOUNT_ID'):
        os.environ['OANDA_ACCOUNT_ID'] = _credential_cache['OANDA_ACCOUNT_ID']
        if not os.getenv('PRIMARY_ACCOUNT'):
            os.environ['PRIMARY_ACCOUNT'] = _credential_cache['OANDA_ACCOUNT_ID']
    
    _cache_initialized = True
    
    # Log what we found (without exposing full values)
    if _credential_cache.get('OANDA_API_KEY'):
        logger.info(f"✅ Credentials loaded: API_KEY={_credential_cache['OANDA_API_KEY'][:10]}...{_credential_cache['OANDA_API_KEY'][-4:]}")
    if _credential_cache.get('OANDA_ACCOUNT_ID'):
        logger.info(f"✅ Account ID loaded: {_credential_cache['OANDA_ACCOUNT_ID']}")

def get_oanda_api_key() -> Optional[str]:
    """Get OANDA API key from any available source"""
    _initialize_credential_cache()
    return _credential_cache.get('OANDA_API_KEY')

def get_oanda_account_id() -> Optional[str]:
    """Get OANDA account ID from any available source"""
    _initialize_credential_cache()
    return _credential_cache.get('OANDA_ACCOUNT_ID') or _credential_cache.get('PRIMARY_ACCOUNT')

def get_oanda_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Get both API key and account ID"""
    return get_oanda_api_key(), get_oanda_account_id()

def ensure_credentials_loaded():
    """Ensure credentials are loaded and set in environment"""
    _initialize_credential_cache()
    
    # Set in environment if found
    if _credential_cache.get('OANDA_API_KEY'):
        os.environ['OANDA_API_KEY'] = _credential_cache['OANDA_API_KEY']
    
    if _credential_cache.get('OANDA_ACCOUNT_ID'):
        os.environ['OANDA_ACCOUNT_ID'] = _credential_cache['OANDA_ACCOUNT_ID']
        if not os.getenv('PRIMARY_ACCOUNT'):
            os.environ['PRIMARY_ACCOUNT'] = _credential_cache['OANDA_ACCOUNT_ID']
    
    return _credential_cache.get('OANDA_API_KEY') is not None and _credential_cache.get('OANDA_ACCOUNT_ID') is not None

def get_credential_status() -> Dict[str, any]:
    """Get status of credential loading"""
    _initialize_credential_cache()
    
    api_key = _credential_cache.get('OANDA_API_KEY')
    account_id = _credential_cache.get('OANDA_ACCOUNT_ID') or _credential_cache.get('PRIMARY_ACCOUNT')
    
    return {
        'api_key_loaded': api_key is not None,
        'api_key_preview': f"{api_key[:10]}...{api_key[-4:]}" if api_key and len(api_key) > 14 else "***" if api_key else None,
        'account_id_loaded': account_id is not None,
        'account_id': account_id,
        'environment': _credential_cache.get('OANDA_ENVIRONMENT', 'practice'),
        'all_credentials_present': api_key is not None and account_id is not None
    }

# Auto-initialize on import
ensure_credentials_loaded()
