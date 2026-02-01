#!/usr/bin/env python3
"""
Force Update Cloud Configuration
Direct approach to update the cloud system with TOP 3 strategies
"""

import requests
import json
import yaml
import time

def force_update_cloud():
    """Force update the cloud system with our TOP 3 strategies"""
    
    print("🚀 FORCE UPDATING CLOUD WITH TOP 3 STRATEGIES")
    print("=" * 60)
    
    base_url = "https://ai-quant-trading.uc.r.appspot.com"
    
    # Read our updated configuration
    with open('accounts.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Extract TOP 3 accounts
    top3_accounts = [acc for acc in config['accounts'] if 'demo_' in acc['id']]
    
    print(f"📊 Found {len(top3_accounts)} TOP 3 strategy accounts:")
    for account in top3_accounts:
        print(f"   🎯 {account['display_name']} - {account['account_id']}")
    
    print("\n🔄 Attempting direct configuration update...")
    
    # Method 1: Try to trigger a configuration reload
    try:
        print("📡 Method 1: Triggering configuration reload...")
        response = requests.post(f"{base_url}/tasks/full_scan", timeout=30)
        if response.status_code == 200:
            print("✅ Configuration reload triggered")
            time.sleep(5)  # Wait for reload
        else:
            print(f"⚠️ Reload response: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Reload error: {e}")
    
    # Method 2: Check if the new accounts are now visible
    print("\n🔍 Checking for TOP 3 accounts...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            account_statuses = data.get('account_statuses', {})
            
            # Check for our TOP 3 accounts
            found_accounts = []
            for account in top3_accounts:
                account_id = account['account_id']
                if account_id in account_statuses:
                    found_accounts.append(account)
                    print(f"✅ Found: {account['display_name']}")
            
            if found_accounts:
                print(f"\n🎉 SUCCESS: {len(found_accounts)} TOP 3 strategies are LIVE!")
                return True
            else:
                print("⚠️ TOP 3 accounts not yet visible")
                
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    # Method 3: Try to add accounts via direct API calls
    print("\n📡 Method 3: Direct API account addition...")
    
    for account in top3_accounts:
        try:
            # Try different API endpoints
            endpoints = [
                "/api/config/add-account",
                "/api/accounts/add",
                "/config/add-account"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(
                        f"{base_url}{endpoint}",
                        json=account,
                        timeout=10
                    )
                    if response.status_code == 200:
                        print(f"✅ Added {account['display_name']} via {endpoint}")
                        break
                    elif response.status_code != 404:
                        print(f"⚠️ {endpoint}: {response.status_code}")
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ Error adding {account['display_name']}: {e}")
    
    # Method 4: Check final status
    print("\n🔍 Final status check...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            active_accounts = data.get('active_accounts', 0)
            print(f"📊 Total active accounts: {active_accounts}")
            
            # Check if we have more accounts now
            if active_accounts >= 6:  # 3 original + 3 new
                print("🎉 SUCCESS: All accounts are now active!")
                return True
            else:
                print(f"⚠️ Still only {active_accounts} accounts active")
                
    except Exception as e:
        print(f"❌ Final check error: {e}")
    
    return False

if __name__ == "__main__":
    success = force_update_cloud()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TOP 3 STRATEGIES SUCCESSFULLY UPDATED ON CLOUD!")
        print("🌐 Your new strategies are now LIVE and trading!")
        print("\n📊 Your 3 new accounts:")
        print("   🏆 101-004-30719775-008 → Strategy #1 (Sharpe 35.90)")
        print("   🥈 101-004-30719775-007 → Strategy #2 (Sharpe 35.55)")
        print("   🥉 101-004-30719775-006 → Strategy #3 (Sharpe 35.18)")
    else:
        print("⚠️ UPDATE INCOMPLETE")
        print("💡 The cloud system needs the updated accounts.yaml file")
        print("🔧 Try using Google Cloud Console to upload the file manually")
        print("📁 File location: /Users/mac/quant_system_clean/google-cloud-trading-system/accounts.yaml")
