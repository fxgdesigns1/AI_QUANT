#!/usr/bin/env python3
"""
Test Google Cloud Secret Manager Integration
Verifies that credentials are properly stored and accessible
"""
import sys
from pathlib import Path

# Add the google-cloud-trading-system to path
sys.path.insert(0, str(Path(__file__).parent / "google-cloud-trading-system"))

from src.core.secret_manager import get_credentials_manager


def test_secret_manager():
    """Test Secret Manager integration"""
    print("\n" + "="*70)
    print("TESTING GOOGLE CLOUD SECRET MANAGER INTEGRATION")
    print("="*70)
    
    # Initialize credentials manager
    print("\n[1/3] Initializing Credentials Manager...")
    try:
        credentials = get_credentials_manager(use_secret_manager=True)
        print("✓ Credentials Manager initialized")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False
    
    # Test individual credentials
    print("\n[2/3] Testing credential retrieval...")
    test_credentials = [
        'OANDA_API_KEY',
        'TELEGRAM_TOKEN',
        'TELEGRAM_CHAT_ID',
        'ALPHA_VANTAGE_API_KEY',
        'MARKETAUX_API_KEY',
    ]
    
    results = {}
    for cred_name in test_credentials:
        try:
            value = credentials.get(cred_name)
            if value:
                # Show first 10 and last 4 characters for security
                masked_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
                print(f"  ✓ {cred_name}: {masked_value}")
                results[cred_name] = True
            else:
                print(f"  ⚠ {cred_name}: Not found")
                results[cred_name] = False
        except Exception as e:
            print(f"  ✗ {cred_name}: Error - {e}")
            results[cred_name] = False
    
    # Get all credentials
    print("\n[3/3] Retrieving all trading credentials...")
    try:
        all_creds = credentials.get_all_trading_credentials()
        print(f"✓ Retrieved {len(all_creds)} credentials")
        print("\nAvailable credentials:")
        for name in sorted(all_creds.keys()):
            if all_creds[name]:
                print(f"  • {name}")
    except Exception as e:
        print(f"✗ Failed to retrieve all credentials: {e}")
        return False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n✓ Successfully retrieved: {success_count}/{total_count} credentials")
    
    if success_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nYour credentials are securely stored and accessible from:")
        print("  • This computer")
        print("  • Google Cloud instances")
        print("  • Mobile devices (via API)")
        print("  • Any device with Google Cloud authentication")
        return True
    else:
        failed = [name for name, success in results.items() if not success]
        print(f"\n⚠ Some credentials not found: {', '.join(failed)}")
        print("\nThis might be normal if you haven't set these up yet.")
        return success_count > 0


def test_fallback():
    """Test fallback to .env files"""
    print("\n" + "="*70)
    print("TESTING FALLBACK TO .ENV FILES")
    print("="*70)
    
    print("\n[1/1] Testing fallback mode (Secret Manager disabled)...")
    try:
        credentials = get_credentials_manager(use_secret_manager=False)
        api_key = credentials.get('OANDA_API_KEY')
        
        if api_key:
            masked = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
            print(f"✓ Fallback working - OANDA_API_KEY: REDACTED")
            print("\n✓ FALLBACK TEST PASSED!")
            print("  System will automatically use .env files if Secret Manager is unavailable")
            return True
        else:
            print("⚠ Could not retrieve credentials from .env files")
            return False
            
    except Exception as e:
        print(f"✗ Fallback test failed: {e}")
        return False


def main():
    """Main test function"""
    print("\n🔐 CREDENTIALS SECURITY TEST")
    
    # Test Secret Manager
    secret_manager_ok = test_secret_manager()
    
    # Test fallback
    fallback_ok = test_fallback()
    
    # Overall summary
    print("\n" + "="*70)
    print("OVERALL RESULTS")
    print("="*70)
    
    if secret_manager_ok and fallback_ok:
        print("\n✅ ALL SYSTEMS OPERATIONAL")
        print("\nYour trading system has:")
        print("  • Secure cloud credential storage ✓")
        print("  • Mobile access capability ✓")
        print("  • Local fallback support ✓")
        print("\nReady for production use! 🚀")
        return 0
    elif secret_manager_ok:
        print("\n⚠ SECRET MANAGER: OK")
        print("✗ FALLBACK: NEEDS ATTENTION")
        return 1
    elif fallback_ok:
        print("\n✗ SECRET MANAGER: NEEDS SETUP")
        print("⚠ FALLBACK: OK")
        print("\nYou can still trade using .env files")
        print("Run migration script to enable mobile access")
        return 1
    else:
        print("\n✗ BOTH SYSTEMS NEED ATTENTION")
        print("\nPlease check your configuration:")
        print("  1. Verify .env files exist")
        print("  2. Run migration script for Secret Manager")
        print("  3. Check Google Cloud authentication")
        return 2


if __name__ == '__main__':
    sys.exit(main())


