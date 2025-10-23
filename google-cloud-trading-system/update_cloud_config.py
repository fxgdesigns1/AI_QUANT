#!/usr/bin/env python3
"""
Update Cloud Configuration Script
This script will update the cloud system with our new TOP 3 strategies
"""

import requests
import json
import yaml

def update_cloud_config():
    """Update the cloud system with new configuration"""
    
    # Read our updated accounts.yaml
    with open('accounts.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Extract the new TOP 3 accounts
    new_accounts = []
    for account in config['accounts']:
        if 'demo_' in account['id']:
            new_accounts.append(account)
    
    print(f"📊 Found {len(new_accounts)} TOP 3 strategy accounts to deploy:")
    for account in new_accounts:
        print(f"   ✅ {account['display_name']} - {account['account_id']}")
    
    # Try to add accounts via API
    base_url = "https://ai-quant-trading.uc.r.appspot.com"
    
    for account in new_accounts:
        try:
            # Add account via API
            response = requests.post(
                f"{base_url}/api/config/add-account",
                json=account,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully added {account['display_name']}")
            else:
                print(f"❌ Failed to add {account['display_name']}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error adding {account['display_name']}: {e}")
    
    print("\n🎯 Cloud configuration update complete!")

if __name__ == "__main__":
    update_cloud_config()
