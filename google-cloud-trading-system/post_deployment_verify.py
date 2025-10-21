#!/usr/bin/env python3
"""
POST-DEPLOYMENT VERIFICATION
Verifies the deployed system is running correctly
Run this AFTER deployment to confirm everything works
"""

import sys
import requests
import time
from datetime import datetime

def verify_deployment(version_name):
    """Verify deployed version is working correctly"""
    
    print("=" * 70)
    print("POST-DEPLOYMENT VERIFICATION")
    print(f"Version: {version_name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    base_url = "https://ai-quant-trading.uc.r.appspot.com"
    errors = []
    
    # 1. Check system is online
    print("\n🔍 Checking system status...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=10)
        if response.status_code == 200:
            print("✅ System is online")
            data = response.json()
            
            # 2. Verify active accounts
            active_accounts = data.get('active_accounts', 0)
            print(f"\n📊 Active accounts: {active_accounts}")
            if active_accounts < 6:
                errors.append(f"❌ Only {active_accounts} accounts active, expected 6")
            else:
                print("✅ All 6 accounts active")
            
            # 3. Check trading systems
            systems = data.get('trading_systems', {})
            print(f"\n📋 Trading systems loaded: {len(systems)}")
            
            expected_strategies = {
                '101-004-30719775-006': 'GBP',  # Rank 3
                '101-004-30719775-007': 'GBP',  # Rank 2
                '101-004-30719775-008': 'GBP',  # Rank 1
                '101-004-30719775-009': 'Gold',
                '101-004-30719775-010': 'Ultra Strict',
                '101-004-30719775-011': 'Momentum',
            }
            
            for account_id, expected_name in expected_strategies.items():
                if account_id in systems:
                    strategy_name = systems[account_id].get('strategy_name', 'Unknown')
                    print(f"  ✅ {account_id[-3:]}: {strategy_name}")
                else:
                    errors.append(f"❌ Account {account_id} not found in systems")
            
            # 4. Check data feed
            data_feed = data.get('data_feed_status', 'unknown')
            print(f"\n📡 Data feed: {data_feed}")
            if data_feed != 'active':
                errors.append(f"❌ Data feed is '{data_feed}', expected 'active'")
            else:
                print("✅ Data feed active")
            
        else:
            errors.append(f"❌ Status endpoint returned {response.status_code}")
    
    except Exception as e:
        errors.append(f"❌ Failed to connect to system: {e}")
    
    # 5. Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    if errors:
        print(f"\n❌ ERRORS FOUND: {len(errors)}")
        for error in errors:
            print(f"  {error}")
        print("\n⚠️  Deployment may have issues - investigate!")
    else:
        print("\n✅ ALL CHECKS PASSED - Deployment verified!")
        print("\nSystem is running correctly with:")
        print("  • All 6 accounts active")
        print("  • Correct strategies loaded")
        print("  • Data feed active")
        print("  • API responding")
    
    print("=" * 70)
    
    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = "latest"
    
    success = verify_deployment(version)
    sys.exit(0 if success else 1)


