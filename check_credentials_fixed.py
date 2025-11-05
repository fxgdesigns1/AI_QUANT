#!/usr/bin/env python3
"""
FIXED CREDENTIAL CHECK - Uses Unified Credential Loader
This will NOT show false alarms about missing credentials
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'google-cloud-trading-system' / 'src'))

from core.unified_credential_loader import (
    get_oanda_api_key,
    get_oanda_account_id,
    get_credential_status,
    ensure_credentials_loaded
)

print("="*80)
print("🔐 CREDENTIAL STATUS CHECK (FIXED)")
print("="*80)

# Ensure credentials are loaded
ensure_credentials_loaded()

# Get status
status = get_credential_status()

print(f"\n✅ API Key Loaded: {status['api_key_loaded']}")
if status['api_key_loaded']:
    print(f"   Preview: {status['api_key_preview']}")
else:
    print("   ❌ NOT FOUND")

print(f"\n✅ Account ID Loaded: {status['account_id_loaded']}")
if status['account_id_loaded']:
    print(f"   Account: {status['account_id']}")
else:
    print("   ❌ NOT FOUND")

print(f"\n✅ Environment: {status['environment']}")

print(f"\n🎯 Overall Status: {'✅ ALL CREDENTIALS PRESENT' if status['all_credentials_present'] else '❌ MISSING CREDENTIALS'}")

# Test OANDA client creation
if status['all_credentials_present']:
    print("\n" + "="*80)
    print("🧪 Testing OANDA Client Creation")
    print("="*80)
    try:
        from core.oanda_client import OandaClient
        client = OandaClient()
        print("✅ OANDA Client created successfully!")
        print(f"   Base URL: {client.base_url}")
        print(f"   Account ID: {client.account_id}")
    except Exception as e:
        print(f"❌ Failed to create OANDA client: {e}")

print("\n" + "="*80)
print("✅ CREDENTIAL CHECK COMPLETE - NO FALSE ALARMS!")
print("="*80)
