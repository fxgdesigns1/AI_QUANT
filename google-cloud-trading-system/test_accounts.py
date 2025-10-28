#!/usr/bin/env python3
"""
Test Account Manager
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('oanda_config.env')

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.account_manager import get_account_manager

def test_account_manager():
    """Test account manager functionality"""
    print("🔍 Testing Account Manager...")
    print("=" * 50)
    
    try:
        # Get account manager
        account_manager = get_account_manager()
        
        # Get active accounts
        active_accounts = account_manager.get_active_accounts()
        print(f"📊 Active Accounts: {len(active_accounts)}")
        
        for account_id in active_accounts:
            print(f"\n🏦 Account: {account_id}")
            
            # Get account config
            config = account_manager.get_account_config(account_id)
            if config:
                print(f"   Name: {config.account_name}")
                print(f"   Strategy: {config.strategy_name}")
                print(f"   Instruments: {config.instruments}")
                print(f"   Risk Settings: {config.risk_settings}")
            
            # Get account status
            status = account_manager.get_account_status(account_id)
            if status:
                print(f"   Balance: {status.get('balance', 'N/A')}")
                print(f"   Currency: {status.get('currency', 'N/A')}")
                print(f"   Margin Used: {status.get('margin_used', 'N/A')}")
                print(f"   Unrealized P&L: {status.get('unrealized_pl', 'N/A')}")
                print(f"   Open Trades: {status.get('open_trade_count', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Account manager test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_account_manager()
    if success:
        print("\n✅ Account manager test passed!")
    else:
        print("\n❌ Account manager test failed!")
