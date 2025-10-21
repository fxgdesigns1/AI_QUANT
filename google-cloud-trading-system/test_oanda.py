#!/usr/bin/env python3
"""
Test OANDA Connection
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('oanda_config.env')

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.oanda_client import OandaClient

def test_oanda_connection():
    """Test OANDA API connection"""
    print("🔍 Testing OANDA Connection...")
    print("=" * 50)
    
    try:
        # Test primary account
        print(f"📊 Testing Primary Account: {os.getenv('PRIMARY_ACCOUNT')}")
        client = OandaClient(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=os.getenv('PRIMARY_ACCOUNT'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
        # Test connection
        account_info = client.get_account_info()
        print(f"✅ Primary Account Connected")
        print(f"   Balance: {account_info.balance}")
        print(f"   Currency: {account_info.currency}")
        print(f"   Margin Used: {account_info.margin_used}")
        print(f"   Unrealized P&L: {account_info.unrealized_pl}")
        
        # Test market data
        print(f"\n📈 Testing Market Data...")
        instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'XAU_USD']
        try:
            prices = client.get_current_prices(instruments)
            for instrument, price in prices.items():
                print(f"   {instrument}: {price.bid} / {price.ask}")
        except Exception as e:
            print(f"   ❌ Market data error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == '__main__':
    success = test_oanda_connection()
    if success:
        print("\n✅ OANDA connection test passed!")
    else:
        print("\n❌ OANDA connection test failed!")
