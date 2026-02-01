#!/usr/bin/env python3
"""
Test Data Feed
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('oanda_config.env')

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.multi_account_data_feed import get_multi_account_data_feed

def test_data_feed():
    """Test data feed functionality"""
    print("🔍 Testing Data Feed...")
    print("=" * 50)
    
    try:
        # Get data feed
        data_feed = get_multi_account_data_feed()
        
        # Start data feed
        data_feed.start()
        print("✅ Data feed started")
        
        # Wait a moment for data to be fetched
        import time
        time.sleep(3)
        
        # Get market data for all accounts
        all_market_data = data_feed.get_all_market_data()
        print(f"📊 Market data for {len(all_market_data)} accounts")
        
        for account_id, market_data in all_market_data.items():
            print(f"\n🏦 Account: {account_id}")
            print(f"   Instruments: {len(market_data)}")
            
            for instrument, data in market_data.items():
                if data:
                    print(f"   {instrument}: {data.bid} / {data.ask} (spread: {data.spread:.5f})")
                    print(f"      Volatility: {data.volatility_score:.3f}, Regime: {data.regime}")
                    print(f"      Age: {data.last_update_age}s, Live: {data.is_live}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data feed test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_data_feed()
    if success:
        print("\n✅ Data feed test passed!")
    else:
        print("\n❌ Data feed test failed!")
