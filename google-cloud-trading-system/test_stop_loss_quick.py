#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.oanda_client import get_oanda_client

def test_stop_loss():
    try:
        oanda = get_oanda_client()
        
        # Test order with stop-loss
        order = oanda.place_market_order(
            instrument="EUR_USD",
            units=1000,
            stop_loss=1.0450,
            take_profit=1.0600
        )
        
        if order and hasattr(order, 'stop_loss') and order.stop_loss:
            print("✅ Stop-loss orders working correctly")
            return True
        else:
            print("❌ Stop-loss orders not working")
            return False
    except Exception as e:
        print(f"❌ Stop-loss test failed: {e}")
        return False

if __name__ == "__main__":
    test_stop_loss()
